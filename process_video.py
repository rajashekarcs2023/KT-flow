"""
Video Processing Pipeline for Workflow Memory
1. Upload video to Gemini File API
2. Extract structured playbook (transcript, steps, commands, timestamps)
3. Extract frames at key timestamps using ffmpeg
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

from google import genai
from google.genai import types

# Create client with extended timeout for large file uploads
client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options=types.HttpOptions(
        timeout=600_000,  # 10 minutes timeout
    ),
)
MODEL = "gemini-3.1-pro-preview"

VIDEO_PATH = "demovideo.mp4"
OUTPUT_DIR = Path("playbook_data")
FRAMES_DIR = OUTPUT_DIR / "frames"

# Create output directories
OUTPUT_DIR.mkdir(exist_ok=True)
FRAMES_DIR.mkdir(exist_ok=True)

EXTRACTION_PROMPT = """You are an expert workflow analyst. You are watching a complete screen-recorded knowledge transfer / workflow demonstration video.

Your job is to extract a COMPLETE, STRUCTURED operational playbook from this video. This playbook will be used by engineers to reproduce the workflow WITHOUT rewatching the video.

IMPORTANT RULES:
- Watch the ENTIRE video carefully — do NOT skip or summarize loosely
- Extract EVERY procedural step, not just the major ones
- Capture EXACT commands as they appear on screen or are spoken
- Note precise timestamps (MM:SS format) for every step
- Capture file names, config values, URLs, namespaces, environment names, service names
- Distinguish between: command execution, config editing, UI navigation, verification, explanation
- For each step, note what's visible on screen (terminal, browser, IDE, etc.)
- If the speaker mentions something important but doesn't show it, still capture it

Return a JSON object with this EXACT structure:

{
  "workflow_title": "descriptive title of the overall workflow",
  "workflow_summary": "2-3 sentence summary of what this KT covers",
  "speaker_name": "name of the person giving the KT if mentioned",
  "total_duration_minutes": <number>,
  "tools_used": ["list", "of", "all", "tools", "mentioned", "or", "shown"],
  "environments": ["list of environments/clusters/namespaces mentioned"],
  "steps": [
    {
      "step_id": <sequential number starting from 1>,
      "title": "short descriptive title",
      "summary": "1-2 sentence description of what happens in this step",
      "step_type": "command|config_edit|verification|navigation|explanation|setup|deployment|debugging",
      "commands": ["exact commands used, if any"],
      "files_modified": ["file paths mentioned or shown"],
      "config_changes": ["specific config values changed"],
      "tool_context": "terminal|browser|IDE|dashboard|other",
      "what_is_on_screen": "brief description of what's visible on screen during this step",
      "timestamp_start": "MM:SS",
      "timestamp_end": "MM:SS",
      "transcript_snippet": "key quote from the speaker during this step (verbatim if possible)",
      "dependencies": [<list of step_ids this depends on>],
      "verification": "how to verify this step succeeded, if mentioned",
      "keywords": ["relevant", "keywords"],
      "important_visual_moment": true/false,
      "visual_description": "if important_visual_moment is true, describe what should be captured as a frame"
    }
  ],
  "all_commands": ["complete ordered list of every command used in the workflow"],
  "key_timestamps_for_frames": [
    {
      "timestamp": "MM:SS",
      "reason": "why this moment is visually important",
      "step_id": <which step this belongs to>
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

Be EXHAUSTIVE. It is better to have too many steps than too few. Every command, every config change, every navigation action should be its own step. Engineers will use this to reproduce the EXACT workflow.

For key_timestamps_for_frames, include EVERY moment where something visually important happens on screen — commands being typed, config files open, dashboards showing results, terminal output, etc. These will be used to extract screenshot frames from the video.

Return ONLY valid JSON, no markdown formatting, no code blocks, no explanation text."""


def upload_video(max_retries=3):
    """Upload video to Gemini File API and wait for processing."""
    print(f"\n{'='*60}")
    print(f"STEP 1: Uploading video to Gemini File API")
    print(f"Video: {VIDEO_PATH} ({os.path.getsize(VIDEO_PATH) / 1024 / 1024:.0f} MB)")
    print(f"{'='*60}")
    
    start = time.time()
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Uploading... attempt {attempt}/{max_retries} (this may take a few minutes)")
            video_file = client.files.upload(file=VIDEO_PATH)
            print(f"Upload complete. File name: {video_file.name}")
            print(f"State: {video_file.state}")
            break
        except Exception as e:
            print(f"Upload attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait = 10 * attempt
                print(f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print("All upload attempts failed!")
                sys.exit(1)
    
    # Wait for processing
    while video_file.state.name == "PROCESSING":
        elapsed = time.time() - start
        print(f"  Processing... ({elapsed:.0f}s elapsed, waiting 10s)")
        time.sleep(10)
        video_file = client.files.get(name=video_file.name)
    
    if video_file.state.name == "FAILED":
        print(f"ERROR: Video processing failed!")
        sys.exit(1)
    
    elapsed = time.time() - start
    print(f"Video ready! ({elapsed:.0f}s)")
    
    return video_file


def extract_playbook(video_file):
    """Send video to Gemini and extract structured playbook."""
    print(f"\n{'='*60}")
    print(f"STEP 2: Extracting structured playbook with Gemini 3.1 Pro")
    print(f"{'='*60}")
    
    start = time.time()
    
    print("Analyzing video... (this may take 1-3 minutes)")
    
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=video_file.uri,
                        mime_type=video_file.mime_type,
                    ),
                    types.Part.from_text(text=EXTRACTION_PROMPT),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=65536,
        ),
    )
    
    elapsed = time.time() - start
    print(f"Extraction complete! ({elapsed:.0f}s)")
    
    # Parse the JSON response
    raw_text = response.text.strip()
    
    # Clean up potential markdown code blocks
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
    if raw_text.endswith("```"):
        raw_text = raw_text.rsplit("```", 1)[0]
    raw_text = raw_text.strip()
    
    try:
        playbook = json.loads(raw_text)
        print(f"Successfully parsed playbook JSON!")
        print(f"  Title: {playbook.get('workflow_title', 'N/A')}")
        print(f"  Steps: {len(playbook.get('steps', []))}")
        print(f"  Commands: {len(playbook.get('all_commands', []))}")
        print(f"  Frame timestamps: {len(playbook.get('key_timestamps_for_frames', []))}")
    except json.JSONDecodeError as e:
        print(f"WARNING: Failed to parse JSON: {e}")
        print(f"Saving raw response for manual review...")
        raw_path = OUTPUT_DIR / "raw_response.txt"
        raw_path.write_text(raw_text)
        print(f"Saved to {raw_path}")
        # Try to fix common issues
        playbook = None
    
    return playbook, raw_text


def extract_frames(playbook):
    """Extract frames at key timestamps using ffmpeg."""
    print(f"\n{'='*60}")
    print(f"STEP 3: Extracting frames with ffmpeg")
    print(f"{'='*60}")
    
    timestamps = set()
    
    # Collect timestamps from steps
    if playbook and "steps" in playbook:
        for step in playbook["steps"]:
            ts_start = step.get("timestamp_start", "")
            if ts_start:
                timestamps.add(ts_start)
            # Also grab a frame near the middle of the step
            ts_end = step.get("timestamp_end", "")
            if ts_start and ts_end:
                try:
                    start_secs = parse_timestamp(ts_start)
                    end_secs = parse_timestamp(ts_end)
                    mid_secs = (start_secs + end_secs) // 2
                    timestamps.add(format_timestamp(mid_secs))
                except:
                    pass
    
    # Collect from key_timestamps_for_frames
    if playbook and "key_timestamps_for_frames" in playbook:
        for item in playbook["key_timestamps_for_frames"]:
            ts = item.get("timestamp", "")
            if ts:
                timestamps.add(ts)
    
    # Safety net: also extract frames every 60 seconds
    video_duration = 2566  # seconds (from ffprobe)
    for sec in range(0, video_duration, 60):
        timestamps.add(format_timestamp(sec))
    
    sorted_timestamps = sorted(timestamps, key=lambda t: parse_timestamp(t))
    print(f"Extracting {len(sorted_timestamps)} frames...")
    
    extracted = []
    for i, ts in enumerate(sorted_timestamps):
        secs = parse_timestamp(ts)
        ts_ffmpeg = format_ffmpeg_timestamp(secs)
        frame_name = f"frame_{ts.replace(':', '_')}.png"
        frame_path = FRAMES_DIR / frame_name
        
        cmd = [
            "ffmpeg", "-y", "-ss", ts_ffmpeg,
            "-i", VIDEO_PATH,
            "-frames:v", "1",
            "-q:v", "2",
            str(frame_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and frame_path.exists():
            extracted.append({"timestamp": ts, "file": frame_name})
            if (i + 1) % 10 == 0:
                print(f"  Extracted {i+1}/{len(sorted_timestamps)} frames...")
        else:
            print(f"  WARNING: Failed to extract frame at {ts}")
    
    print(f"Successfully extracted {len(extracted)} frames")
    return extracted


def parse_timestamp(ts):
    """Parse MM:SS or HH:MM:SS to total seconds."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def format_timestamp(secs):
    """Format seconds to MM:SS."""
    m = secs // 60
    s = secs % 60
    return f"{m:02d}:{s:02d}"


def format_ffmpeg_timestamp(secs):
    """Format seconds to HH:MM:SS for ffmpeg."""
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def save_playbook(playbook, extracted_frames):
    """Save the final playbook with frame references."""
    print(f"\n{'='*60}")
    print(f"STEP 4: Saving playbook")
    print(f"{'='*60}")
    
    # Map frames to steps
    frame_map = {}
    for frame in extracted_frames:
        frame_map[frame["timestamp"]] = frame["file"]
    
    if playbook and "steps" in playbook:
        for step in playbook["steps"]:
            ts = step.get("timestamp_start", "")
            if ts in frame_map:
                step["frame_file"] = frame_map[ts]
            else:
                # Find closest frame
                step_secs = parse_timestamp(ts) if ts else 0
                closest = None
                min_diff = float("inf")
                for frame_ts, frame_file in frame_map.items():
                    diff = abs(parse_timestamp(frame_ts) - step_secs)
                    if diff < min_diff:
                        min_diff = diff
                        closest = frame_file
                step["frame_file"] = closest
            step["enhanced_visual"] = None  # placeholder for NanoBanana
    
    # Add frame list to playbook
    if playbook:
        playbook["extracted_frames"] = extracted_frames
    
    # Save
    playbook_path = OUTPUT_DIR / "playbook.json"
    with open(playbook_path, "w") as f:
        json.dump(playbook, f, indent=2)
    print(f"Saved playbook to {playbook_path}")
    
    # Also save a compact version for the chat assistant
    if playbook:
        compact = {
            "workflow_title": playbook.get("workflow_title"),
            "workflow_summary": playbook.get("workflow_summary"),
            "steps": playbook.get("steps", []),
            "all_commands": playbook.get("all_commands", []),
        }
        compact_path = OUTPUT_DIR / "playbook_compact.json"
        with open(compact_path, "w") as f:
            json.dump(compact, f, indent=2)
        print(f"Saved compact playbook to {compact_path}")
    
    return playbook_path


def main():
    print("=" * 60)
    print("WORKFLOW MEMORY — Video Processing Pipeline")
    print("=" * 60)
    
    # Step 1: Upload video
    video_file = upload_video()
    
    # Step 2: Extract playbook
    playbook, raw_text = extract_playbook(video_file)
    
    if not playbook:
        print("\nERROR: Could not parse playbook. Check raw_response.txt")
        sys.exit(1)
    
    # Save raw response too
    (OUTPUT_DIR / "raw_response.txt").write_text(raw_text)
    
    # Step 3: Extract frames
    extracted_frames = extract_frames(playbook)
    
    # Step 4: Save everything
    save_playbook(playbook, extracted_frames)
    
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE!")
    print(f"{'='*60}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Playbook: {OUTPUT_DIR}/playbook.json")
    print(f"Frames: {FRAMES_DIR}/ ({len(extracted_frames)} frames)")
    print(f"\nNext: Build the UI and point it at {OUTPUT_DIR}/playbook.json")


if __name__ == "__main__":
    main()
