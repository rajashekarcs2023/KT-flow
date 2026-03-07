"""
Experiment 3: Nano Banana 2 (gemini-3.1-flash-image-preview)
Tests:
  A) Text-to-image — basic generation quality
  B) Search grounding — generate image using real-time web data
  C) Image search grounding — use Google Image Search for reference
  D) Multi-turn editing — generate then modify in conversation
  E) Accurate text rendering — logos, infographics with readable text
  F) Thinking mode — high vs minimal quality comparison
"""
import os
import base64
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.1-flash-image-preview"


def save_image_from_response(response, filename):
    """Extract and save image from a Gemini response."""
    for part in response.candidates[0].content.parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            img_data = part.inline_data.data
            if isinstance(img_data, str):
                img_data = base64.b64decode(img_data)
            with open(filename, "wb") as f:
                f.write(img_data)
            size_kb = os.path.getsize(filename) / 1024
            print(f"  ✅ Saved {filename} ({size_kb:.0f} KB)")
            return True
        elif hasattr(part, 'text') and part.text:
            print(f"  📝 Text: {part.text[:200]}")
    return False


def test_a_basic_generation():
    """Basic text-to-image generation."""
    print("\n" + "="*60)
    print("TEST A: Basic Text-to-Image")
    print("="*60)

    prompt = "A photorealistic aerial view of a bioluminescent bay at night, with kayakers leaving glowing blue trails in the water. Stars reflected on the calm surface. Shot from drone perspective."

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio="16:9",
                image_size="2K"
            ),
        )
    )
    save_image_from_response(response, "output/test_a_basic.png")


def test_b_search_grounded_image():
    """Generate image using Google Search grounding for real-time data."""
    print("\n" + "="*60)
    print("TEST B: Search-Grounded Image Generation")
    print("="*60)

    prompt = "Search for the current top 5 most valuable companies in the world by market cap. Create a beautiful, modern infographic showing their logos, names, and market caps as a clean bar chart with each company's brand color. Title: 'World's Most Valuable Companies 2026'. Professional magazine quality."

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio="3:2",
                image_size="2K"
            ),
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    save_image_from_response(response, "output/test_b_search_grounded.png")

    # Check for grounding metadata
    if response.candidates and response.candidates[0].grounding_metadata:
        gm = response.candidates[0].grounding_metadata
        print(f"  🔍 Grounding metadata present: True")
        if hasattr(gm, 'grounding_chunks') and gm.grounding_chunks:
            print(f"  📚 Sources: {len(gm.grounding_chunks)}")


def test_c_image_search_grounding():
    """Use Google Image Search to ground image generation."""
    print("\n" + "="*60)
    print("TEST C: Image Search Grounding")
    print("="*60)

    prompt = "Use image search to find what a Mandarin Duck looks like. Create a beautiful watercolor painting of this bird sitting on a misty pond at dawn. Capture its exact colorful plumage accurately."

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio="3:2",
                image_size="2K"
            ),
            tools=[
                types.Tool(google_search=types.GoogleSearch(
                    search_types=types.SearchTypes(
                        web_search=types.WebSearch(),
                        image_search=types.ImageSearch()
                    )
                ))
            ]
        )
    )
    save_image_from_response(response, "output/test_c_image_search.png")


def test_d_text_rendering():
    """Test accurate text rendering in generated images."""
    print("\n" + "="*60)
    print("TEST D: Accurate Text Rendering")
    print("="*60)

    prompt = """Create a professional event poster with this exact text layout:

Title (large, bold): "RESONANCE"
Subtitle: "Where Sound Becomes Sight"
Date: "March 15, 2026"
Location: "San Francisco, CA"
Tagline at bottom: "A Synesthetic AI Experience"

Style: Modern, minimalist design with a dark background. 
Use a gradient from deep purple to electric blue. 
Abstract sound wave visualizations in the background.
All text must be perfectly legible and spelled correctly."""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio="2:3",
                image_size="2K"
            ),
        )
    )
    save_image_from_response(response, "output/test_d_text_rendering.png")


def test_e_multi_turn_editing():
    """Test multi-turn conversational image editing."""
    print("\n" + "="*60)
    print("TEST E: Multi-Turn Image Editing")
    print("="*60)

    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
        )
    )

    # Turn 1: Generate base image
    print("  Turn 1: Generate base scene...")
    response = chat.send_message(
        "Create a cozy coffee shop interior, warm lighting, wooden tables, a barista behind the counter. Photorealistic style. afternoon sunlight streaming through windows."
    )
    saved = save_image_from_response(response, "output/test_e_turn1.png")

    if saved:
        # Turn 2: Modify it
        print("  Turn 2: Add rain outside...")
        response = chat.send_message(
            "Now make it raining heavily outside the windows. Add condensation on the glass. Keep everything else the same."
        )
        save_image_from_response(response, "output/test_e_turn2.png")

        # Turn 3: Change mood
        print("  Turn 3: Change to night time...")
        response = chat.send_message(
            "Change it to nighttime. The interior is now lit by warm pendant lamps and candles. The windows show city lights outside in the rain. Keep the same composition."
        )
        save_image_from_response(response, "output/test_e_turn3.png")


def test_f_thinking_levels():
    """Compare minimal vs high thinking for complex prompt."""
    print("\n" + "="*60)
    print("TEST F: Thinking Levels Comparison")
    print("="*60)

    complex_prompt = "An impossible Escher-like architectural scene where water flows uphill through a series of ancient Roman aqueducts that loop back on themselves. Include accurate Latin text carved into stone that reads 'AQUA PERPETUA'. Photorealistic but geometrically impossible. Golden hour lighting."

    for level in ["minimal", "High"]:
        print(f"\n  🧠 Thinking level: {level}")
        response = client.models.generate_content(
            model=MODEL,
            contents=complex_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                    image_size="1K"
                ),
                thinking_config=types.ThinkingConfig(
                    thinking_level=level,
                    include_thoughts=True
                ),
            )
        )
        save_image_from_response(response, f"output/test_f_thinking_{level.lower()}.png")

        # Check for thought content
        thought_count = 0
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'thought') and part.thought:
                thought_count += 1
        print(f"  💭 Thought parts: {thought_count}")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    test_a_basic_generation()
    test_b_search_grounded_image()
    test_c_image_search_grounding()
    test_d_text_rendering()
    test_e_multi_turn_editing()
    test_f_thinking_levels()
    print("\n" + "="*60)
    print("ALL NANO BANANA EXPERIMENTS COMPLETE")
    print("="*60)
