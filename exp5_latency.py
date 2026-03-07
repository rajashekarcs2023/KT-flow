"""
Experiment 5: Image Generation Latency Tests
- Compare 1K vs 2K generation times
- Test SVG sketch generation speed (Gemini 3.1)
- Test parallel SVG + Image generation
- Test if we can generate a "fast draft" then "full render"
"""
import os
import time
import json
import base64
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

SCENE = "A rainy Tokyo street at 2am, neon signs reflecting off wet pavement, a lone figure walking with an umbrella, steam rising from a ramen shop. Cinematic, moody."


def save_image(response, filename):
    for part in response.candidates[0].content.parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            img_data = part.inline_data.data
            if isinstance(img_data, str):
                img_data = base64.b64decode(img_data)
            with open(filename, "wb") as f:
                f.write(img_data)
            return True
    return False


def test_image_latency():
    """Compare image generation at different sizes."""
    print("="*60)
    print("TEST 1: Image Size vs Latency")
    print("="*60)

    for size in ["1K", "2K"]:
        print(f"\n  Generating at {size}...")
        t0 = time.time()
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=SCENE,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size=size
                ),
            )
        )
        elapsed = time.time() - t0
        saved = save_image(response, f"output/latency_{size}.png")
        file_size = os.path.getsize(f"output/latency_{size}.png") / 1024 if saved else 0
        print(f"  ✅ {size}: {elapsed:.1f}s, {file_size:.0f} KB")


def test_svg_sketch_speed():
    """How fast can Gemini 3.1 generate an SVG sketch of a scene?"""
    print("\n" + "="*60)
    print("TEST 2: SVG Sketch Speed (Gemini 3.1 Pro)")
    print("="*60)

    prompt = f"""Generate a minimal SVG sketch (line art, simple shapes) of this scene:
"{SCENE}"
Use simple paths, no complex gradients. Make it 800x450.
Include CSS animations that make the lines appear to draw themselves (stroke-dasharray animation).
Use a dark background (#0a0a0f) with glowing colored strokes (#ff6b9d for neon, #4ecdc4 for reflections, #ffe66d for lights).
Return ONLY the SVG code."""

    t0 = time.time()
    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.7)
    )
    elapsed = time.time() - t0

    svg = response.text
    if "```" in svg:
        lines = svg.split("\n")
        svg = "\n".join(l for l in lines if not l.strip().startswith("```"))

    with open("output/latency_sketch.svg", "w") as f:
        f.write(svg)
    print(f"  ✅ SVG sketch: {elapsed:.1f}s, {len(svg)} chars")


def test_flash_lite_speed():
    """Test if gemini-3.1-flash-lite is faster for quick analysis."""
    print("\n" + "="*60)
    print("TEST 3: Flash-Lite vs Pro Analysis Speed")
    print("="*60)

    analysis_prompt = f"""Analyze this scene and return JSON with: mood, energy (0-1), colors (3 hex), music_genre, bpm.
Scene: "{SCENE}"
Return ONLY JSON."""

    for model in ["gemini-3.1-flash-lite", "gemini-3.1-pro-preview"]:
        t0 = time.time()
        try:
            response = client.models.generate_content(
                model=model,
                contents=analysis_prompt,
                config=types.GenerateContentConfig(temperature=0.2)
            )
            elapsed = time.time() - t0
            print(f"  {model}: {elapsed:.1f}s")
            print(f"    Response: {response.text[:200]}")
        except Exception as e:
            print(f"  {model}: ERROR - {e}")


def test_parallel_sketch_and_image():
    """Simulate the parallel pipeline: SVG sketch + full image generation."""
    import concurrent.futures
    print("\n" + "="*60)
    print("TEST 4: Parallel Pipeline Timing")
    print("="*60)

    def generate_svg():
        prompt = f"""Generate a minimal animated SVG sketch of: "{SCENE}"
800x450, dark bg, neon colored lines, stroke-dasharray draw animation. ONLY SVG code."""
        t0 = time.time()
        resp = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return time.time() - t0, "svg"

    def generate_image():
        t0 = time.time()
        resp = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=SCENE,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
            )
        )
        save_image(resp, "output/latency_parallel_full.png")
        return time.time() - t0, "image"

    def analyze_scene():
        prompt = f"""Analyze: "{SCENE}" Return JSON: mood, energy, music prompts for Lyria, bpm, density, brightness. ONLY JSON."""
        t0 = time.time()
        resp = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return time.time() - t0, "analysis"

    print("  Running SVG + Image + Analysis in parallel...")
    total_t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(analyze_scene),
            executor.submit(generate_svg),
            executor.submit(generate_image),
        ]
        for future in concurrent.futures.as_completed(futures):
            elapsed, name = future.result()
            wall_time = time.time() - total_t0
            print(f"  ✅ {name} done: {elapsed:.1f}s (wall: {wall_time:.1f}s)")

    total = time.time() - total_t0
    print(f"\n  📊 TOTAL wall time (parallel): {total:.1f}s")
    print("  This is the time from user input to ALL outputs ready")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    test_image_latency()
    test_svg_sketch_speed()
    test_flash_lite_speed()
    test_parallel_sketch_and_image()
    print("\n" + "="*60)
    print("LATENCY EXPERIMENTS COMPLETE")
    print("="*60)
