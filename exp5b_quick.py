"""Quick latency tests - SVG sketch speed + parallel pipeline timing."""
import os, time, json, base64, concurrent.futures
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
SCENE = "A rainy Tokyo street at 2am, neon signs reflecting off wet pavement, a lone figure walking with an umbrella."
os.makedirs("output", exist_ok=True)

# TEST 1: SVG Sketch speed
print("TEST 1: SVG Sketch Speed")
t0 = time.time()
resp = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents=f'Generate a minimal animated SVG sketch of: "{SCENE}" 800x450, dark bg #0a0a0f, neon colored strokes, stroke-dasharray draw animation. ONLY SVG code, no markdown.',
    config=types.GenerateContentConfig(temperature=0.7)
)
svg_time = time.time() - t0
svg = resp.text
if "```" in svg:
    lines = svg.split("\n")
    svg = "\n".join(l for l in lines if not l.strip().startswith("```"))
with open("output/sketch.svg", "w") as f:
    f.write(svg)
print(f"  SVG: {svg_time:.1f}s, {len(svg)} chars")

# TEST 2: Flash-Lite analysis speed
print("\nTEST 2: Flash-Lite vs Pro analysis speed")
for model in ["gemini-3.1-flash-lite", "gemini-3.1-pro-preview"]:
    t0 = time.time()
    try:
        resp = client.models.generate_content(
            model=model,
            contents=f'Analyze: "{SCENE}" Return JSON: mood, energy(0-1), bpm, density(0-1), brightness(0-1), music_prompts(list). ONLY JSON.',
            config=types.GenerateContentConfig(temperature=0.2)
        )
        print(f"  {model}: {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"  {model}: ERROR - {e}")

# TEST 3: Parallel pipeline
print("\nTEST 3: Parallel Pipeline (analysis + SVG + image all at once)")

def do_analysis():
    t0 = time.time()
    client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=f'Analyze: "{SCENE}" Return JSON: mood, energy, bpm, density, brightness, music_prompts. ONLY JSON.',
        config=types.GenerateContentConfig(temperature=0.2)
    )
    return time.time()-t0, "analysis"

def do_svg():
    t0 = time.time()
    client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=f'Minimal animated SVG of: "{SCENE}" 800x450, dark bg, neon strokes, draw animation. ONLY SVG.',
        config=types.GenerateContentConfig(temperature=0.7)
    )
    return time.time()-t0, "svg_sketch"

def do_image():
    t0 = time.time()
    client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=SCENE,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
        )
    )
    return time.time()-t0, "full_image"

total_t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(do_analysis), executor.submit(do_svg), executor.submit(do_image)]
    for future in concurrent.futures.as_completed(futures):
        elapsed, name = future.result()
        wall = time.time() - total_t0
        print(f"  ✅ {name}: {elapsed:.1f}s (wall: {wall:.1f}s)")

print(f"\n  TOTAL wall time: {time.time()-total_t0:.1f}s")
print("\nDONE")
