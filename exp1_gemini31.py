"""
Experiment 1: Gemini 3.1 Pro Preview
Tests:
  A) Structured output — can it output JSON schema for mood/emotion analysis?
  B) Image understanding — analyze an image and extract structured mood descriptors
  C) Search grounding — research a topic and return structured findings
  D) Code generation — generate animated SVG from a concept
  E) Multi-step reasoning — complex chain-of-thought task
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.1-pro-preview"


def test_a_structured_mood_analysis():
    """Can Gemini output structured JSON describing mood/emotion from a text scene?"""
    print("\n" + "="*60)
    print("TEST A: Structured Mood Analysis from Text")
    print("="*60)

    prompt = """Analyze the following scene and return a JSON object with these exact fields:
- mood: string (primary mood)
- energy: float 0.0-1.0
- valence: float -1.0 to 1.0 (negative=sad, positive=happy)
- genres: list of 3 music genres that match this mood
- instruments: list of 5 instruments that would fit
- bpm_range: [min, max]
- colors: list of 3 hex color codes that represent this mood
- visual_style: string describing the visual aesthetic

Scene: "A lone figure stands at the edge of a cliff at golden hour, 
wind whipping through their hair, overlooking a vast ocean. 
Seagulls circle overhead. The sky is painted in oranges and purples."

Return ONLY valid JSON, no markdown."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
        )
    )
    print(response.text)
    try:
        parsed = json.loads(response.text)
        print("\n✅ Successfully parsed as JSON")
        print(json.dumps(parsed, indent=2))
    except json.JSONDecodeError as e:
        print(f"\n⚠️ JSON parse failed: {e}")
        print("Raw response:", response.text[:500])


def test_b_search_grounding():
    """Can Gemini use search grounding to get real-time info and structure it?"""
    print("\n" + "="*60)
    print("TEST B: Search Grounding + Structured Output")
    print("="*60)

    prompt = """Search for the latest breakthroughs in AI music generation in 2025-2026. 
Return a structured JSON with:
- top_3_developments: [{name, description, date, significance}]
- current_state: string summary
- open_problems: list of strings

Return ONLY valid JSON."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        )
    )
    print(response.text)


def test_c_svg_animation():
    """Can Gemini generate working animated SVG code?"""
    print("\n" + "="*60)
    print("TEST C: Animated SVG Generation")
    print("="*60)

    prompt = """Generate a complete, self-contained SVG with CSS animations that shows:
A musical waveform visualization - colorful bars that animate up and down 
like an audio equalizer. Use vibrant gradient colors (purple to cyan).
Make it 800x400px. The animation should loop infinitely.
Return ONLY the SVG code, no explanation."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
        )
    )
    svg_code = response.text
    # Strip markdown code fences if present
    if "```" in svg_code:
        lines = svg_code.split("\n")
        svg_lines = []
        in_code = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                svg_lines.append(line)
        svg_code = "\n".join(svg_lines)

    with open("output/test_c_animation.svg", "w") as f:
        f.write(svg_code)
    print(f"✅ SVG saved to output/test_c_animation.svg ({len(svg_code)} chars)")
    print("Preview first 500 chars:")
    print(svg_code[:500])


def test_d_multimodal_pipeline_reasoning():
    """Can Gemini take a complex multi-step instruction and produce a pipeline plan?"""
    print("\n" + "="*60)
    print("TEST D: Multi-Step Pipeline Reasoning")
    print("="*60)

    prompt = """You are designing an AI pipeline that takes a user's photo as input 
and produces a personalized multimedia experience. The pipeline has access to:
1. An image analysis model (can understand photos)
2. A text reasoning model (you)
3. A real-time music generation model (steerable via text prompts + BPM/density/brightness params)
4. An image generation model (can create images from text, with search grounding)

Design a detailed pipeline that:
- Analyzes the input photo
- Extracts mood, setting, objects, time of day, cultural context
- Generates SPECIFIC parameters for the music model (exact prompt words, BPM number, density float, brightness float)
- Generates a SPECIFIC prompt for the image model to create a "dream version" of the scene
- The music and image should feel synesthetic — like they belong together

Return as JSON with fields: 
{
  "analysis_step": {description, outputs},
  "music_params": {prompts: [{text, weight}], bpm, density, brightness, scale, mood_reasoning},
  "image_prompt": {full_prompt, aspect_ratio, style_reasoning},
  "experience_narrative": string describing what the user would feel
}

Input photo description (simulating): "A busy Tokyo street at night, neon signs reflecting on wet pavement, 
a person with an umbrella walking alone, steam rising from a ramen shop."

Return ONLY valid JSON."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.5,
        )
    )
    print(response.text[:2000])
    try:
        parsed = json.loads(response.text)
        print("\n✅ Successfully parsed as JSON")
        print(f"Music BPM: {parsed.get('music_params', {}).get('bpm')}")
        print(f"Music prompts: {parsed.get('music_params', {}).get('prompts')}")
        print(f"Image prompt length: {len(parsed.get('image_prompt', {}).get('full_prompt', ''))}")
    except Exception as e:
        print(f"\n⚠️ Parse issue: {e}")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    test_a_structured_mood_analysis()
    test_b_search_grounding()
    test_c_svg_animation()
    test_d_multimodal_pipeline_reasoning()
    print("\n" + "="*60)
    print("ALL GEMINI 3.1 EXPERIMENTS COMPLETE")
    print("="*60)
