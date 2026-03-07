"""
Experiment 2: Lyria RealTime
Tests:
  A) Basic music generation — connect, set prompt, play, capture audio
  B) Real-time steering — change prompts mid-stream and observe transition
  C) Parameter control — test BPM, density, brightness changes
  D) Multi-prompt blending — blend multiple weighted prompts
  E) Save output as WAV file for analysis
"""
import asyncio
import os
import struct
import wave
import time
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"],
    http_options={'api_version': 'v1alpha'}
)

SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2  # 16-bit PCM


def save_wav(filename, audio_data, sample_rate=SAMPLE_RATE, channels=CHANNELS):
    """Save raw PCM bytes as a WAV file."""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)
    size_mb = os.path.getsize(filename) / (1024 * 1024)
    print(f"  ✅ Saved {filename} ({size_mb:.2f} MB)")


async def test_a_basic_generation():
    """Basic: generate 10 seconds of minimal techno."""
    print("\n" + "="*60)
    print("TEST A: Basic Music Generation (10s minimal techno)")
    print("="*60)

    audio_buffer = bytearray()
    duration = 10  # seconds
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

            await session.set_weighted_prompts(
                prompts=[
                    types.WeightedPrompt(text='minimal techno with deep bass', weight=1.0),
                ]
            )
            await session.set_music_generation_config(
                config=types.LiveMusicGenerationConfig(bpm=120, temperature=1.0)
            )
            await session.play()
            print("  ▶️  Playing...")

            # Wait for duration
            await asyncio.sleep(duration + 2)
    except Exception as e:
        print(f"  ⚠️ Session ended: {e}")

    if audio_buffer:
        save_wav("output/test_a_basic_techno.wav", bytes(audio_buffer))
        total_samples = len(audio_buffer) // (SAMPLE_WIDTH * CHANNELS)
        actual_duration = total_samples / SAMPLE_RATE
        print(f"  📊 Captured {actual_duration:.1f}s of audio, {len(audio_buffer)} bytes")
    else:
        print("  ❌ No audio captured")


async def test_b_steering():
    """Steering: start with jazz, transition to electronic mid-stream."""
    print("\n" + "="*60)
    print("TEST B: Real-Time Steering (jazz → electronic)")
    print("="*60)

    audio_buffer = bytearray()
    duration = 15
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

            # Phase 1: Smooth Jazz
            print("  🎷 Phase 1: Smooth Jazz")
            await session.set_weighted_prompts(
                prompts=[
                    types.WeightedPrompt(text='smooth jazz, saxophone, mellow', weight=1.0),
                ]
            )
            await session.set_music_generation_config(
                config=types.LiveMusicGenerationConfig(bpm=85, temperature=1.0, density=0.4, brightness=0.5)
            )
            await session.play()
            await asyncio.sleep(5)

            # Phase 2: Gradual transition — blend jazz + electronic
            print("  🔀 Phase 2: Blending jazz + electronic")
            await session.set_weighted_prompts(
                prompts=[
                    types.WeightedPrompt(text='smooth jazz, saxophone', weight=0.5),
                    types.WeightedPrompt(text='electronic synths, ambient pads', weight=0.5),
                ]
            )
            await asyncio.sleep(5)

            # Phase 3: Full electronic
            print("  🎹 Phase 3: Full electronic")
            await session.set_weighted_prompts(
                prompts=[
                    types.WeightedPrompt(text='electronic ambient, spacey synths, ethereal', weight=1.0),
                ]
            )
            await asyncio.sleep(7)
    except Exception as e:
        print(f"  ⚠️ Session ended: {e}")

    if audio_buffer:
        save_wav("output/test_b_steering.wav", bytes(audio_buffer))
        total_samples = len(audio_buffer) // (SAMPLE_WIDTH * CHANNELS)
        actual_duration = total_samples / SAMPLE_RATE
        print(f"  📊 Captured {actual_duration:.1f}s of audio, {len(audio_buffer)} bytes")
    else:
        print("  ❌ No audio captured")


async def test_c_multi_mood():
    """Generate 3 distinct 8-second clips for different moods to test range."""
    print("\n" + "="*60)
    print("TEST C: Multi-Mood Generation (3 clips)")
    print("="*60)

    moods = [
        {
            "name": "energetic_upbeat",
            "prompts": [types.WeightedPrompt(text="upbeat funk, danceable, funky drums, slap bass", weight=1.0)],
            "config": types.LiveMusicGenerationConfig(bpm=118, density=0.8, brightness=0.7, temperature=1.0)
        },
        {
            "name": "dark_cinematic",
            "prompts": [types.WeightedPrompt(text="dark cinematic, ominous drone, deep cello, tension", weight=1.0)],
            "config": types.LiveMusicGenerationConfig(bpm=70, density=0.3, brightness=0.2, temperature=1.0)
        },
        {
            "name": "peaceful_nature",
            "prompts": [types.WeightedPrompt(text="peaceful acoustic, gentle piano, birdsong, meditation", weight=1.0)],
            "config": types.LiveMusicGenerationConfig(bpm=65, density=0.2, brightness=0.6, temperature=1.0)
        },
    ]

    for mood in moods:
        print(f"\n  🎵 Generating: {mood['name']}")
        audio_buffer = bytearray()
        duration = 8
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
                await session.set_weighted_prompts(prompts=mood["prompts"])
                await session.set_music_generation_config(config=mood["config"])
                await session.play()
                await asyncio.sleep(duration + 2)
        except Exception as e:
            print(f"  ⚠️ Session ended: {e}")

        if audio_buffer:
            filename = f"output/test_c_{mood['name']}.wav"
            save_wav(filename, bytes(audio_buffer))
        else:
            print(f"  ❌ No audio for {mood['name']}")

        # Reset for next mood
        audio_buffer = bytearray()
        start_time = None


async def main():
    os.makedirs("output", exist_ok=True)
    await test_a_basic_generation()
    await test_b_steering()
    await test_c_multi_mood()
    print("\n" + "="*60)
    print("ALL LYRIA EXPERIMENTS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
