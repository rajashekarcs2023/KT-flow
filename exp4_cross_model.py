"""
Experiment 4: Cross-Model Pipeline
Tests the KEY innovation — chaining models together:
  A) Image → Gemini 3.1 analysis → Lyria music params (image-to-music pipeline)
  B) Text scene → Gemini 3.1 reasoning → Nano Banana image + Lyria music (full synesthetic pipeline)
  C) Measure latency of the full chain
"""
import asyncio
import os
import json
import time
import wave
import base64
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

client_standard = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
client_lyria = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={'api_version': 'v1alpha'}
)

SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2


def save_wav(filename, audio_data):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data)
    print(f"  ✅ Saved {filename}")


def save_image_from_response(response, filename):
    for part in response.candidates[0].content.parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            img_data = part.inline_data.data
            if isinstance(img_data, str):
                img_data = base64.b64decode(img_data)
            with open(filename, "wb") as f:
                f.write(img_data)
            print(f"  ✅ Saved {filename}")
            return True
        elif hasattr(part, 'text') and part.text:
            print(f"  📝 Text: {part.text[:200]}")
    return False


def step1_analyze_scene(scene_description):
    """Use Gemini 3.1 to analyze a scene and extract structured music + image params."""
    print("\n  📊 Step 1: Analyzing scene with Gemini 3.1...")
    t0 = time.time()

    prompt = f"""You are the brain of a synesthetic AI. Given a scene description, you must output 
EXACT parameters for two downstream models:

1. A MUSIC model that accepts: 
   - prompts: list of {{text: string, weight: float}} (music genres, instruments, moods)
   - bpm: int (60-200)
   - density: float (0.0-1.0) 
   - brightness: float (0.0-1.0)
   - scale: one of [C_MAJOR_A_MINOR, D_MAJOR_B_MINOR, E_FLAT_MAJOR_C_MINOR, F_MAJOR_D_MINOR, G_MAJOR_E_MINOR, A_FLAT_MAJOR_F_MINOR, B_FLAT_MAJOR_G_MINOR]

2. An IMAGE model that accepts a text prompt to generate a "dream version" or "emotional amplification" of the scene.

Scene: "{scene_description}"

Return ONLY this JSON:
{{
  "scene_analysis": {{
    "primary_mood": "string",
    "energy_level": 0.0-1.0,
    "emotional_valence": -1.0 to 1.0,
    "time_of_day": "string",
    "key_elements": ["list", "of", "elements"],
    "cultural_context": "string"
  }},
  "music_params": {{
    "prompts": [{{"text": "string", "weight": 1.0}}],
    "bpm": 120,
    "density": 0.5,
    "brightness": 0.5,
    "scale": "C_MAJOR_A_MINOR",
    "reasoning": "why these params match the scene"
  }},
  "image_prompt": {{
    "prompt": "A detailed prompt for generating a dream/amplified version of this scene...",
    "aspect_ratio": "16:9",
    "reasoning": "why this visual treatment"
  }}
}}"""

    response = client_standard.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3)
    )

    elapsed = time.time() - t0
    print(f"  ⏱️  Analysis took {elapsed:.1f}s")

    raw = response.text.strip()
    # Strip markdown fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(l for l in lines if not l.strip().startswith("```"))

    try:
        params = json.loads(raw)
        print(f"  ✅ Parsed: mood={params['scene_analysis']['primary_mood']}, "
              f"bpm={params['music_params']['bpm']}, "
              f"density={params['music_params']['density']}")
        return params, elapsed
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON parse error: {e}")
        print(f"  Raw: {raw[:500]}")
        return None, elapsed


async def step2_generate_music(music_params, duration=10):
    """Use Lyria RealTime to generate music from analyzed params."""
    print(f"\n  🎵 Step 2: Generating {duration}s of music with Lyria...")
    t0 = time.time()
    audio_buffer = bytearray()
    start_time = None

    prompts = [
        types.WeightedPrompt(text=p["text"], weight=p["weight"])
        for p in music_params["prompts"]
    ]

    config = types.LiveMusicGenerationConfig(
        bpm=music_params.get("bpm", 90),
        density=music_params.get("density", 0.5),
        brightness=music_params.get("brightness", 0.5),
        temperature=1.0,
    )

    async def receive_audio(session):
        nonlocal audio_buffer, start_time
        while True:
            async for message in session.receive():
                if start_time is None:
                    start_time = time.time()
                if hasattr(message, 'server_content') and message.server_content:
                    for chunk in message.server_content.audio_chunks:
                        audio_buffer.extend(chunk.data)
                elapsed = time.time() - start_time if start_time else 0
                if elapsed >= duration:
                    return
                await asyncio.sleep(10**-12)

    try:
        async with (
            client_lyria.aio.live.music.connect(model='models/lyria-realtime-exp') as session,
            asyncio.TaskGroup() as tg,
        ):
            tg.create_task(receive_audio(session))
            await session.set_weighted_prompts(prompts=prompts)
            await session.set_music_generation_config(config=config)
            await session.play()
            print(f"  ▶️  Playing: {[p['text'] for p in music_params['prompts']]}")
            print(f"     BPM={music_params['bpm']}, density={music_params['density']}, brightness={music_params['brightness']}")
            await asyncio.sleep(duration + 2)
    except Exception as e:
        print(f"  ⚠️ Session ended: {e}")

    elapsed = time.time() - t0
    print(f"  ⏱️  Music generation took {elapsed:.1f}s")
    return bytes(audio_buffer), elapsed


def step3_generate_image(image_params):
    """Use Nano Banana to generate the dream image."""
    print(f"\n  🖼️  Step 3: Generating image with Nano Banana...")
    t0 = time.time()

    response = client_standard.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=image_params["prompt"],
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=image_params.get("aspect_ratio", "16:9"),
                image_size="2K"
            ),
        )
    )

    elapsed = time.time() - t0
    print(f"  ⏱️  Image generation took {elapsed:.1f}s")
    return response, elapsed


async def test_a_scene_to_music_image():
    """Full pipeline: scene description → analysis → music + image."""
    print("\n" + "="*60)
    print("TEST A: Full Scene-to-Music+Image Pipeline")
    print("="*60)

    scenes = [
        "A rainy Tokyo street at 2am. Neon signs in Japanese reflect off puddles. A lone figure in a trench coat walks past a steaming ramen shop. Jazz plays faintly from an upstairs bar.",
        "A sun-drenched Mediterranean village at midday. White-washed buildings, bright blue doors, bougainvillea everywhere. Children playing in a fountain. The smell of fresh bread.",
        "A vast Icelandic glacier under the northern lights. Complete silence except for the distant crack of ice. Aurora borealis painting green and purple across the sky. A tiny figure stands in awe.",
    ]

    for i, scene in enumerate(scenes):
        print(f"\n{'─'*60}")
        print(f"SCENE {i+1}: {scene[:80]}...")
        print(f"{'─'*60}")

        total_t0 = time.time()

        # Step 1: Analyze
        params, t_analysis = step1_analyze_scene(scene)
        if not params:
            print("  ❌ Analysis failed, skipping")
            continue

        # Step 2: Generate music (run concurrently with image)
        music_task = step2_generate_music(params["music_params"], duration=10)

        # Step 3: Generate image (we'll do sequentially for clarity in output)
        img_response, t_image = step3_generate_image(params["image_prompt"])
        save_image_from_response(img_response, f"output/test_pipeline_scene{i+1}.png")

        # Now get the music
        audio_data, t_music = await music_task

        if audio_data:
            save_wav(f"output/test_pipeline_scene{i+1}.wav", audio_data)

        total_elapsed = time.time() - total_t0
        print(f"\n  📊 SCENE {i+1} TOTAL: {total_elapsed:.1f}s "
              f"(analysis={t_analysis:.1f}s, image={t_image:.1f}s, music={t_music:.1f}s)")
        print(f"  🎨 Image prompt: {params['image_prompt']['prompt'][:100]}...")
        print(f"  🎵 Music: {params['music_params']['prompts']}")
        print(f"  📐 Music params: bpm={params['music_params']['bpm']}, "
              f"density={params['music_params']['density']}, "
              f"brightness={params['music_params']['brightness']}")


async def main():
    os.makedirs("output", exist_ok=True)
    await test_a_scene_to_music_image()
    print("\n" + "="*60)
    print("ALL CROSS-MODEL PIPELINE EXPERIMENTS COMPLETE")
    print("="*60)
    print("\nCheck the output/ folder for generated files:")
    for f in sorted(os.listdir("output")):
        if f.startswith("test_pipeline"):
            size = os.path.getsize(f"output/{f}") / 1024
            print(f"  📁 {f} ({size:.0f} KB)")


if __name__ == "__main__":
    asyncio.run(main())
