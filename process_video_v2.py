"""
Video Processing Pipeline v2 for Workflow Memory
Instead of uploading the full 441MB video, we:
1. Extract audio (small mp3) via ffmpeg
2. Extract frames every 20s via ffmpeg
3. Upload audio to Gemini for transcript + step extraction
4. Much more reliable on slow networks

Usage: venv/bin/python process_video_v2.py
"""
import os
import sys
import json
import time
import subprocess
import base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(timeout=600_000),
)
MODEL = "gemini-3.1-pro-preview"

VIDEO_PATH = "demovideo.mp4"
OUTPUT_DIR = Path("playbook_data")
FRAMES_DIR = OUTPUT_DIR / "frames"
AUDIO_PATH = OUTPUT_DIR / "audio.mp3"

OUTPUT_DIR.mkdir(exist_ok=True)
FRAMES_DIR.mkdir(exist_ok=True)


def extract_audio():
    """Extract audio track from video as mp3 (much smaller than full video)."""
    print(f"\n{'='*60}")
    print("STEP 1a: Extracting audio from video")
    print(f"{'='*60}")
    
    if AUDIO_PATH.exists():
        size_mb = AUDIO_PATH.stat().st_size / 1024 / 1024
        print(f"Audio already extracted ({size_mb:.1f} MB), skipping...")
        return
    
    cmd = [
        "ffmpeg", "-y", "-i", VIDEO_PATH,
        "-vn",  # no video
        "-acodec", "libmp3lame",
        "-ab", "64k",  # low bitrate = smaller file, still good for speech
        "-ar", "16000",  # 16kHz sample rate (fine for speech)
        "-ac", "1",  # mono
        str(AUDIO_PATH)
    ]
    
    print("Running ffmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: ffmpeg failed: {result.stderr[-500:]}")
        sys.exit(1)
    
    size_mb = AUDIO_PATH.stat().st_size / 1024 / 1024
    print(f"Audio extracted: {size_mb:.1f} MB (vs {os.path.getsize(VIDEO_PATH)/1024/1024:.0f} MB video)")


def extract_periodic_frames():
    """Extract frames every 20 seconds for visual reference."""
    print(f"\n{'='*60}")
    print("STEP 1b: Extracting frames every 20 seconds")
    print(f"{'='*60}")
    
    # Get video duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", VIDEO_PATH],
        capture_output=True, text=True
    )
    duration = int(float(probe.stdout.strip()))
    print(f"Video duration: {duration}s ({duration//60}m {duration%60}s)")
    
    timestamps = list(range(0, duration, 20))  # every 20 seconds
    print(f"Extracting {len(timestamps)} frames...")
    
    extracted = []
    for i, sec in enumerate(timestamps):
        mm = sec // 60
        ss = sec % 60
        ts_str = f"{mm:02d}_{ss:02d}"
        frame_name = f"frame_{ts_str}.png"
        frame_path = FRAMES_DIR / frame_name
        
        if frame_path.exists():
            extracted.append({"timestamp_sec": sec, "timestamp": f"{mm:02d}:{ss:02d}", "file": frame_name})
            continue
        
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}",
            "-i", VIDEO_PATH,
            "-frames:v", "1",
            "-q:v", "2",
            str(frame_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and frame_path.exists():
            extracted.append({"timestamp_sec": sec, "timestamp": f"{mm:02d}:{ss:02d}", "file": frame_name})
        
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(timestamps)} frames extracted...")
    
    print(f"Extracted {len(extracted)} frames total")
    
    # Save frame index
    with open(OUTPUT_DIR / "frame_index.json", "w") as f:
        json.dump(extracted, f, indent=2)
    
    return extracted


def upload_audio_and_extract(frame_index):
    """Upload audio + periodic frames to Gemini for MULTIMODAL analysis.
    
    This is critical: the speaker says things like 'click here', 'as you can see',
    'this field' — Gemini needs BOTH the audio AND the screen frames to understand
    what those references mean.
    """
    print(f"\n{'='*60}")
    print("STEP 2: Uploading audio + frames to Gemini (multimodal)")
    print(f"{'='*60}")
    
    size_mb = AUDIO_PATH.stat().st_size / 1024 / 1024
    print(f"Uploading audio ({size_mb:.1f} MB)...")
    
    start = time.time()
    
    # Upload audio file
    for attempt in range(1, 4):
        try:
            audio_file = client.files.upload(file=str(AUDIO_PATH))
            print(f"Upload complete. File: {audio_file.name}, State: {audio_file.state}")
            break
        except Exception as e:
            print(f"Upload attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(10 * attempt)
            else:
                print("All upload attempts failed!")
                sys.exit(1)
    
    # Wait for processing
    while audio_file.state.name == "PROCESSING":
        elapsed = time.time() - start
        print(f"  Processing audio... ({elapsed:.0f}s)")
        time.sleep(5)
        audio_file = client.files.get(name=audio_file.name)
    
    if audio_file.state.name == "FAILED":
        print("ERROR: Audio processing failed!")
        sys.exit(1)
    
    print(f"Audio ready! ({time.time()-start:.0f}s)")
    
    # Prepare frame images as inline parts (every 30s to keep request manageable)
    # Pick every other frame from our 20s interval = effectively 40s intervals
    # This gives ~64 frames for a 43-min video — well within Gemini's limits
    print(f"\nPreparing screen frames for visual context...")
    frame_parts = []
    frames_used = 0
    for i, frame in enumerate(frame_index):
        if i % 2 != 0:  # every other frame = ~40s intervals
            continue
        frame_path = FRAMES_DIR / frame["file"]
        if not frame_path.exists():
            continue
        
        with open(frame_path, "rb") as f:
            img_bytes = f.read()
        
        # Add timestamp label, then the image
        frame_parts.append(
            types.Part.from_text(text=f"[SCREEN at {frame['timestamp']}]")
        )
        frame_parts.append(
            types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        )
        frames_used += 1
    
    print(f"Including {frames_used} screen frames as visual context")
    
    # Build the multimodal prompt
    prompt = """You are an expert workflow analyst. You have been given:
1. The FULL AUDIO recording of a knowledge transfer / workflow demonstration
2. PERIODIC SCREEN CAPTURES taken every ~40 seconds, labeled with their timestamps

Your job is to extract a COMPLETE, STRUCTURED operational playbook by analyzing BOTH the audio AND the screen frames together. This playbook will be used by engineers to reproduce the workflow WITHOUT rewatching the video.

CRITICAL: The speaker often says things like "click here", "as you can see", "this field", "this button" — use the screen frames to understand WHAT they are referring to. Combine what you HEAR with what you SEE on screen.

IMPORTANT RULES:
- Analyze the ENTIRE recording — do NOT skip or summarize loosely
- Extract EVERY procedural step, not just the major ones
- Capture EXACT commands — look for them both in the audio AND visible on screen in terminal/IDE frames
- Note precise timestamps (MM:SS format) for every step
- When the speaker says "click here" or "this", look at the nearby screen frame to identify WHAT they clicked or referenced
- Capture file names, config values, URLs, namespaces, environment names, service names — from both audio and screen
- Distinguish between: command execution, config editing, UI navigation, verification, explanation
- For commands visible on screen but not spoken, still extract them

Return a JSON object with this EXACT structure:

{
  "workflow_title": "descriptive title of the overall workflow",
  "workflow_summary": "2-3 sentence summary of what this KT covers",
  "speaker_name": "name of the person giving the KT if mentioned",
  "total_duration_minutes": <number>,
  "tools_used": ["list", "of", "all", "tools", "mentioned", "or", "visible"],
  "environments": ["list of environments/clusters/namespaces mentioned or visible"],
  "steps": [
    {
      "step_id": <sequential number starting from 1>,
      "title": "short descriptive title",
      "summary": "1-2 sentence description of what happens in this step",
      "step_type": "command|config_edit|verification|navigation|explanation|setup|deployment|debugging",
      "commands": ["exact commands used — from audio OR screen"],
      "files_modified": ["file paths mentioned or visible on screen"],
      "config_changes": ["specific config values changed"],
      "tool_context": "terminal|browser|IDE|dashboard|other",
      "what_is_on_screen": "describe what is actually visible on the screen frame nearest this step",
      "timestamp_start": "MM:SS",
      "timestamp_end": "MM:SS",
      "transcript_snippet": "key verbatim quote from the speaker during this step",
      "dependencies": [<list of step_ids this depends on>],
      "verification": "how to verify this step succeeded, if mentioned or visible",
      "keywords": ["relevant", "keywords"],
      "important_visual_moment": true or false,
      "visual_description": "if important, describe what the key visual element is on screen"
    }
  ],
  "all_commands": ["complete ordered list of every command used in the workflow"],
  "key_timestamps_for_frames": [
    {
      "timestamp": "MM:SS",
      "reason": "why this moment is visually important",
      "step_id": <which step>
    }
  ],
  "transcript_segments": [
    {
      "timestamp_start": "MM:SS",
      "timestamp_end": "MM:SS", 
      "text": "transcript text for this segment"
    }
  ]
}

Be EXHAUSTIVE. It is better to have too many steps than too few. Every command, every config change, every click, every navigation action should be its own step.

Return ONLY valid JSON, no markdown formatting, no code blocks."""

    # Build the content parts: audio first, then frames interleaved, then prompt
    content_parts = [
        # Audio
        types.Part.from_uri(file_uri=audio_file.uri, mime_type=audio_file.mime_type),
        types.Part.from_text(text="\n--- SCREEN CAPTURES FROM THE RECORDING ---\n"),
    ]
    # Add all frame parts
    content_parts.extend(frame_parts)
    # Add the extraction prompt last
    content_parts.append(types.Part.from_text(text="\n--- EXTRACTION TASK ---\n" + prompt))
    
    print(f"\nSending multimodal request to Gemini (audio + {frames_used} frames)...")
    print("This may take 2-5 minutes for a 43-min recording...")
    
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(role="user", parts=content_parts)
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=65536,
        ),
    )
    
    elapsed = time.time() - start
    print(f"Extraction complete! ({elapsed:.0f}s)")
    
    raw_text = response.text.strip()
    
    # Clean markdown code blocks if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]
    raw_text = raw_text.strip()
    
    # Save raw response
    (OUTPUT_DIR / "raw_response.txt").write_text(raw_text)
    
    try:
        playbook = json.loads(raw_text)
        print(f"Parsed playbook: {playbook.get('workflow_title', 'N/A')}")
        print(f"  Steps: {len(playbook.get('steps', []))}")
        print(f"  Commands: {len(playbook.get('all_commands', []))}")
        return playbook
    except json.JSONDecodeError as e:
        print(f"WARNING: JSON parse failed: {e}")
        print(f"Raw response saved to {OUTPUT_DIR}/raw_response.txt")
        print("Attempting to fix JSON...")
        start_idx = raw_text.find("{")
        end_idx = raw_text.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            try:
                playbook = json.loads(raw_text[start_idx:end_idx])
                print("Fixed! Extracted valid JSON.")
                return playbook
            except:
                pass
        print("Could not fix JSON. Please check raw_response.txt")
        return None


def map_frames_to_steps(playbook, frame_index):
    """Map extracted frames to playbook steps based on timestamps."""
    print(f"\n{'='*60}")
    print("STEP 3: Mapping frames to steps")
    print(f"{'='*60}")
    
    def ts_to_sec(ts):
        parts = ts.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0
    
    for step in playbook.get("steps", []):
        step_sec = ts_to_sec(step.get("timestamp_start", "00:00"))
        
        # Find closest frame
        best_frame = None
        best_diff = float("inf")
        for frame in frame_index:
            diff = abs(frame["timestamp_sec"] - step_sec)
            if diff < best_diff:
                best_diff = diff
                best_frame = frame
        
        if best_frame:
            step["frame_file"] = best_frame["file"]
        step["enhanced_visual"] = None
    
    # Also try to extract frames at exact step timestamps if we don't have them
    for step in playbook.get("steps", []):
        ts_start = step.get("timestamp_start", "")
        if not ts_start:
            continue
        sec = ts_to_sec(ts_start)
        mm = sec // 60
        ss = sec % 60
        exact_name = f"frame_{mm:02d}_{ss:02d}.png"
        exact_path = FRAMES_DIR / exact_name
        
        if not exact_path.exists():
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}",
                "-i", VIDEO_PATH,
                "-frames:v", "1", "-q:v", "2",
                str(exact_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and exact_path.exists():
                step["frame_file"] = exact_name
    
    print(f"Mapped frames to {len(playbook.get('steps', []))} steps")
    return playbook


def save_playbook(playbook):
    """Save the final playbook JSON."""
    print(f"\n{'='*60}")
    print("STEP 4: Saving playbook")
    print(f"{'='*60}")
    
    playbook_path = OUTPUT_DIR / "playbook.json"
    with open(playbook_path, "w") as f:
        json.dump(playbook, f, indent=2)
    print(f"Saved: {playbook_path}")
    
    # Also save compact version
    compact = {
        "workflow_title": playbook.get("workflow_title"),
        "workflow_summary": playbook.get("workflow_summary"),
        "steps": playbook.get("steps", []),
        "all_commands": playbook.get("all_commands", []),
    }
    compact_path = OUTPUT_DIR / "playbook_compact.json"
    with open(compact_path, "w") as f:
        json.dump(compact, f, indent=2)
    print(f"Saved: {compact_path}")
    
    return playbook_path


def main():
    print("=" * 60)
    print("WORKFLOW MEMORY — Video Processing Pipeline v2")
    print("(Audio extraction approach — more reliable)")
    print("=" * 60)
    
    # Step 1a: Extract audio (fast, local)
    extract_audio()
    
    # Step 1b: Extract frames every 20s (fast, local)
    frame_index = extract_periodic_frames()
    
    # Step 2: Upload audio + frames to Gemini for multimodal analysis
    playbook = upload_audio_and_extract(frame_index)
    
    if not playbook:
        print("\nERROR: Could not extract playbook. Check raw_response.txt")
        sys.exit(1)
    
    # Step 3: Map frames to steps + extract exact frames
    playbook = map_frames_to_steps(playbook, frame_index)
    
    # Step 4: Save
    save_playbook(playbook)
    
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE!")
    print(f"{'='*60}")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"  playbook.json — full structured playbook")
    print(f"  frames/ — {len(frame_index)}+ extracted frames")
    print(f"\nSteps found: {len(playbook.get('steps', []))}")
    print(f"Commands found: {len(playbook.get('all_commands', []))}")


if __name__ == "__main__":
    main()
