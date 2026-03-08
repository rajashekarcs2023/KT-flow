"""
Lyria music generation bridge.
Called from Next.js API routes via subprocess.
Usage: python generate_music.py --params '{"prompts":[{"text":"jazz","weight":1.0}],"bpm":90,"density":0.5,"brightness":0.5}' --duration 15 --output /tmp/music.wav
"""
import asyncio
import argparse
import json
import os
import sys
import wave
import time

# Add parent dir for .env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from google import genai
from google.genai import types

SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2


async def generate(params: dict, duration: int, output_path: str):
    client = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options={'api_version': 'v1alpha'}
    )

    prompts = [
        types.WeightedPrompt(text=p["text"], weight=p.get("weight", 1.0))
        for p in params.get("prompts", [{"text": "ambient", "weight": 1.0}])
    ]

    config = types.LiveMusicGenerationConfig(
        bpm=params.get("bpm", 90),
        density=params.get("density", 0.5),
        brightness=params.get("brightness", 0.5),
        temperature=1.0,
    )

    audio_buffer = bytearray()
    start_time = None

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
            client.aio.live.music.connect(model='models/lyria-realtime-exp') as session,
            asyncio.TaskGroup() as tg,
        ):
            tg.create_task(receive_audio(session))
            await session.set_weighted_prompts(prompts=prompts)
            await session.set_music_generation_config(config=config)
            await session.play()
            await asyncio.sleep(duration + 2)
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)

    if audio_buffer:
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(bytes(audio_buffer))
        print(json.dumps({"ok": True, "path": output_path, "bytes": len(audio_buffer)}))
    else:
        print(json.dumps({"error": "No audio captured"}))
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", required=True, help="JSON music params")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    params = json.loads(args.params)

    # Handle SSL on macOS
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except ImportError:
        pass

    asyncio.run(generate(params, args.duration, args.output))
