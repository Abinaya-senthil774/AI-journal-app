"""
Integrated AI Journal Pipeline: Layer 0 (Ingestion) + Layer 1 (Color)
Generates downstream-ready contract JSON and a unified visual debugger.

Requirements:
    pip install pillow google-genai python-dotenv colormath numpy
"""

import os
import sys
import json
import uuid
import time
import colorsys
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environmental variables (.env)
load_dotenv()

# ---- CONFIGURATION ----
PHOTOS_FOLDER = r"D:\Research\AI_memory_app\instant deployement\testphotos"
JOURNAL_TYPE = "travel"  # Options: travel / gratitude / reflective / goal / creative
# -----------------------

# --- colormath compatibility patch ---
import numpy
if not hasattr(numpy, "asscalar"):
    numpy.asscalar = lambda a: a.item()

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color

JOURNAL_THEME_FAMILIES = {
    "travel": "warm earth tones, azure blues",
    "gratitude": "soft lavenders, warm yellows",
    "reflective": "muted grays, deep teals",
    "goal": "sharp blues, greens",
    "creative": "vibrant multicolor",
}

# --- UTILITIES ---
def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)

def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def rgb_to_lab(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    return convert_color(sRGBColor(r, g, b), LabColor)

def rgb_to_hue(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360

def is_warm(hue):
    return hue <= 70 or hue >= 320

def classify_harmony(hues):
    if len(hues) < 2: return "monochrome"
    hues = sorted(hues)
    diffs = [(hues[i + 1] - hues[i]) % 360 for i in range(len(hues) - 1)]
    diffs.append((hues[0] + 360 - hues[-1]) % 360)
    spread = max(diffs)
    if spread > 150: return "complementary"
    elif spread > 90: return "split-complementary"
    elif spread > 40: return "triadic"
    return "analogous"

# --- LAYER 0: EXIF & VISION API ---
def extract_exif_summary(image_path):
    """Extract dates, hardware specs, and decimal GPS configurations."""
    try:
        image = Image.open(image_path)
        exif_raw = image._getexif()
        if not exif_raw:
            return {"date": None, "lat": None, "lon": None, "make": None, "model": None}
        
        exif = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_raw.items()}
        date_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
        
        # GPS Decimal Conversion
        lat = lon = None
        gps_info = exif.get("GPSInfo")
        if gps_info:
            gps_data = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
            def to_decimal(dms, ref):
                degrees, minutes, seconds = dms
                decimal = degrees + minutes / 60 + seconds / 3600
                return -decimal if ref in ("S", "W") else decimal
            
            if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
                lat = to_decimal(gps_data["GPSLatitude"], gps_data["GPSLatitudeRef"])
            if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
                lon = to_decimal(gps_data["GPSLongitude"], gps_data["GPSLongitudeRef"])

        return {"date": date_str, "lat": lat, "lon": lon, "make": exif.get("Make"), "model": exif.get("Model")}
    except Exception as e:
        return {"error": f"EXIF failed: {str(e)}", "date": None, "lat": None, "lon": None, "make": None, "model": None}

VISION_PROMPT = """Analyze this travel photo. Return ONLY valid JSON matching this exact shape:
{
  "dominant_colors": ["#hex", "#hex", "#hex"],
  "scene_type": "beach|mountain|city|forest|food|people|landmark",
  "mood": "joyful|peaceful|adventurous|nostalgic|energetic",
  "subjects": ["subject1", "subject2"],
  "time_of_day": "morning|afternoon|evening|night",
  "weather": "sunny|cloudy|rainy|snowy",
  "composition_notes": "landscape|portrait|close-up|wide-shot"
}"""

def get_image_fingerprint(client, image_path, retries=3):
    """Queries Gemini vision models with built-in backoff logic."""
    try:
        img = Image.open(image_path)
        config = types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=1024)
        
        for attempt in range(retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite", contents=[img, VISION_PROMPT], config=config
                )
                if not response or not response.text:
                    raise ValueError("Empty endpoint response returned.")
                
                fingerprint = json.loads(response.text.strip())
                usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                }
                return fingerprint, usage
            except Exception as e:
                if "503" in str(e) and attempt < retries - 1:
                    time.sleep((attempt + 1) * 3)
                    continue
                raise e
    except Exception as e:
        # Graceful degradation fallback if API fails / offline
        fallback = {
            "dominant_colors": ["#4A5568", "#718096", "#EDF2F7"],
            "scene_type": "city", "mood": "peaceful", "subjects": ["unknown"],
            "time_of_day": "afternoon", "weather": "sunny", "composition_notes": "landscape",
            "api_error": str(e)
        }
        return fallback, {"input_tokens": 0, "output_tokens": 0}

# --- LAYER 1: COLOR INTEGRATION ---
def process_layer1_colors(layer0_photos, journal_type):
    """Processes colors extracted from Layer 0 data instead of raw disk re-reads."""
    weighted = {}
    for photo in layer0_photos:
        colors = photo["semantic"].get("dominant_colors", [])
        for rank, hex_str in enumerate(colors):
            try:
                rgb = hex_to_rgb(hex_str)
                weight = len(colors) - rank
                weighted[rgb] = weighted.get(rgb, 0) + weight
            except Exception:
                continue

    if not weighted:
        weighted[(74, 85, 104)] = 1 # Absolute fallback fallback slate-gray

    ranked_colors = [rgb for rgb, _ in sorted(weighted.items(), key=lambda kv: kv[1], reverse=True)]
    
    primary = ranked_colors[0]
    secondary = ranked_colors[1] if len(ranked_colors) > 1 else primary
    accent = ranked_colors[2] if len(ranked_colors) > 2 else ranked_colors[-1]
    
    # Text accessibility contrast calculations via Lab Lightness
    lab = rgb_to_lab(primary)
    bg, text = ((250, 248, 244), (30, 28, 26)) if lab.lab_l > 60 else ((252, 250, 246), (20, 18, 16))
    
    hues = [rgb_to_hue(c) for c in ranked_colors[:5]]
    
    return {
        "palette": [rgb_to_hex(c) for c in ranked_colors[:5]],
        "theme": journal_type.capitalize(),
        "theme_family": JOURNAL_THEME_FAMILIES.get(journal_type, "vibrant multicolor"),
        "harmony_scheme": classify_harmony(hues),
        "warmth": "warm" if is_warm(rgb_to_hue(primary)) else "cool",
        "roles": {
            "primary": rgb_to_hex(primary), "secondary": rgb_to_hex(secondary), "accent": rgb_to_hex(accent),
            "bg": rgb_to_hex(bg), "text": rgb_to_hex(text)
        }
    }

# --- PIPELINE BUILDER & VISUAL GENERATOR ---
def generate_combined_debugger(pipeline_data, out_path="pipeline_debug_dashboard.html"):
    """Creates a unified HTML verification layout for internal pipeline validation."""
    l0 = pipeline_data["layer_0"]
    l1 = pipeline_data["layer_1"]
    
    html = [
        "<html><head><title>Pipeline Debug Dashboard</title><style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; padding: 30px; margin: 0; color: #1e293b; }",
        ".section { background: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }",
        "h1, h2, h3 { margin-top: 0; color: #0f172a; }",
        ".photo-card { display: flex; border-bottom: 1px solid #e2e8f0; padding: 15px 0; gap: 20px; }",
        ".photo-card:last-child { border-0; }",
        ".swatch { display: inline-block; width: 45px; height: 45px; margin-right: 8px; border-radius: 6px; border: 1px solid #cbd5e1; vertical-align: middle; }",
        ".role-box { display: inline-block; width: 120px; text-align: center; margin-right: 15px; font-size: 12px; font-weight: bold; }",
        ".role-circle { width: 80px; height: 80px; border-radius: 50%; margin: 0 auto 8px; border: 2px solid #e2e8f0; }",
        "pre { background: #1e1e2e; color: #cdd6f4; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 13px; }",
        "grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }",
        "</style></head><body>",
        f"<h1>System Pipeline Visual Debugger (Session: {l0['session_id']})</h1>"
    ]
    
    # Layer 0 Visuals
    html.append("<div class='section'><h2>Layer 0: Ingestion & Pre-processing Verification</h2>")
    for p in l0["photos"]:
        html.append(f"<div class='photo-card'>")
        html.append(f"<div style='flex: 1;'><strong>File:</strong> {os.path.basename(p['path'])}<br>")
        html.append(f"<small>📅 EXIF Date: {p['exif']['date']} | 📍 GPS: {p['exif']['lat']}, {p['exif']['lon']}</small></div>")
        html.append(f"<div style='flex: 1;'><strong>Semantic Signature:</strong><br>")
        html.append(f"🏷️ Type: {p['semantic']['scene_type']} | ✨ Mood: {p['semantic']['mood']}<br>👥 Subjects: {', '.join(p['semantic']['subjects'])}</div>")
        html.append("<div style='flex: 1;'><strong>Extracted Dominant Hexes:</strong><br>")
        for hex_c in p['semantic']['dominant_colors']:
            html.append(f"<div class='swatch' style='background: {hex_c}' title='{hex_c}'></div>")
        html.append("</div></div>")
    html.append(f"<p><small>Token Footprint: Input: {l0['token_usage']['total_input_tokens']} | Output: {l0['token_usage']['total_output_tokens']}</small></p></div>")
    
    # Layer 1 Visuals
    html.append("<div class='section'><h2>Layer 1: Color Intelligence & Architecture Output</h2>")
    html.append(f"<p><strong>Theme Family Chosen:</strong> {l1['theme']} ({l1['theme_family']})</p>")
    html.append(f"<p><strong>Evaluated Rules:</strong> Harmony Scheme: <code>{l1['harmony_scheme']}</code> | Structural Temperature: <code>{l1['warmth']}</code></p>")
    
    html.append("<h3>Determined UI Asset Roles</h3><div>")
    for role, hex_val in l1["roles"].items():
        html.append(f"<div class='role-box'><div class='role-circle' style='background: {hex_val}'></div>{role.upper()}<br><code>{hex_val}</code></div>")
    html.append("</div></div>")
    
    # Downstream Mock Output Previews
    html.append("<div class='section'><h2>Downstream Layer Handshakes (Contract API Preview)</h2>")
    contract_preview = {
        "L2_Layout": {"family_trigger": l1["theme"]},
        "L3_Decorations": {"scene_type_context": [p["semantic"]["scene_type"] for p in l0["photos"]], "color_warmth_rule": l1["warmth"]},
        "L4_Storytelling": {"mood_context": [p["semantic"]["mood"] for p in l0["photos"]], "gps_stamps": [p["exif"]["date"] for p in l0["photos"]]},
        "L5_Rendering": {"css_injections": l1["roles"]}
    }
    html.append(f"<pre>{json.dumps(contract_preview, indent=2)}</pre></div>")
    
    html.append("</body></html>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    return out_path

def run_pipeline(photos_folder, journal_type):
    print("🚀 Initializing Layer 0 Ingestion...")
    client = genai.Client()
    
    supported = (".jpg", ".jpeg", ".png")
    photo_files = [f for f in sorted(os.listdir(photos_folder)) if f.lower().endswith(supported)][:5]
    
    if not photo_files:
        raise ValueError(f"No usable asset targets found in path: {photos_folder}")
        
    l0_data = {"session_id": str(uuid.uuid4()), "photos": []}
    total_in = total_out = 0
    
    for i, filename in enumerate(photo_files, start=1):
        path = os.path.join(photos_folder, filename)
        print(f" -> Processing Asset [{i}/{len(photo_files)}]: {filename}")
        
        exif = extract_exif_summary(path)
        fingerprint, usage = get_image_fingerprint(client, path)
        
        total_in += usage["input_tokens"]
        total_out += usage["output_tokens"]
        
        l0_data["photos"].append({"id": f"p{i}", "path": path, "exif": exif, "semantic": fingerprint})
        
    l0_data["token_usage"] = {"total_input_tokens": total_in, "total_output_tokens": total_out}
    
    print("\n🎨 Initializing Layer 1 Structural Calculations (Reading directly from Layer 0 output)...")
    l1_data = process_layer1_colors(l0_data["photos"], journal_type)
    
    # Combined cleanly to serve as a uniform single data model input source
    pipeline_output = {
        "session_meta": {"timestamp": time.time(), "pipeline_version": "1.0.0"},
        "layer_0": l0_data,
        "layer_1": l1_data
    }
    
    # Build visual debug tools
    debug_path = generate_combined_debugger(pipeline_output)
    print(f"✨ Visual debugging report written to: {debug_path}")
    
    return pipeline_output

if __name__ == "__main__":
    if not os.path.exists(PHOTOS_FOLDER):
        print(f"Error: Targeted track folder missing -> {PHOTOS_FOLDER}")
        sys.exit(1)
        
    master_json = run_pipeline(PHOTOS_FOLDER, JOURNAL_TYPE)
    
    # Save contract data file
    output_filename = "integrated_pipeline_output.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(master_json, f, indent=2)
        
    print(f"💾 Master integration JSON saved as: {output_filename}")