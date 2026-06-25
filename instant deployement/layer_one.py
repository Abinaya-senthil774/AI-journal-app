"""
Layer 1 - Color Intelligence Layer
Day 5-7 deliverable: Color palette extractor (ColorThief) + harmonizer (colormath / Lab space)
*Includes HTML Visual Debugger*
"""

import os
import sys
import json
import colorsys

# ---- EDIT THESE THREE LINES FOR YOUR SETUP ----
PHOTOS_FOLDER = r"D:\Research\AI_memory_app\instant deployement\testphotos"
JOURNAL_TYPE = "travel"              # travel / gratitude / reflective / goal / creative
EXPLICIT_COLORS = None               # e.g. ["#0A2342", "#2A6F97", "#A9D6E5"]
# ------------------------------------------------

import numpy
if not hasattr(numpy, "asscalar"):
    numpy.asscalar = lambda a: a.item()

from colorthief import ColorThief
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color

JOURNAL_THEME_FAMILIES = {
    "travel": "warm earth tones, azure blues",
    "gratitude": "soft lavenders, warm yellows",
    "reflective": "muted grays, deep teals",
    "goal": "sharp blues, greens",
    "creative": "vibrant multicolor",
}

def rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)

def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def extract_palette(image_path, color_count=5):
    ct = ColorThief(image_path)
    return ct.get_palette(color_count=color_count, quality=1)

def rgb_to_lab(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    return convert_color(sRGBColor(r, g, b), LabColor)

def rgb_to_hue(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360

def classify_harmony(hues):
    if len(hues) < 2:
        return "monochrome"
    hues = sorted(hues)
    diffs = [(hues[i + 1] - hues[i]) % 360 for i in range(len(hues) - 1)]
    diffs.append((hues[0] + 360 - hues[-1]) % 360)
    spread = max(diffs)
    if spread > 150:
        return "complementary"
    elif spread > 90:
        return "split-complementary"
    elif spread > 40:
        return "triadic"
    return "analogous"

def is_warm(hue):
    return hue <= 70 or hue >= 320

def weighted_average_palette(photo_palettes):
    weighted = {}
    for palette in photo_palettes:
        for rank, rgb in enumerate(palette):
            weight = len(palette) - rank
            weighted[rgb] = weighted.get(rgb, 0) + weight
    ranked = sorted(weighted.items(), key=lambda kv: kv[1], reverse=True)
    return [rgb for rgb, _ in ranked]

def apply_60_30_10(ranked_colors):
    primary = ranked_colors[0]
    secondary = ranked_colors[1] if len(ranked_colors) > 1 else ranked_colors[0]
    accent = ranked_colors[2] if len(ranked_colors) > 2 else ranked_colors[-1]
    return primary, secondary, accent

def pick_bg_and_text(primary):
    lab = rgb_to_lab(primary)
    if lab.lab_l > 60:
        return (250, 248, 244), (30, 28, 26)
    return (252, 250, 246), (20, 18, 16)

def generate_debug_html(debug_data, out_path="layer1_debug.html"):
    """Generates a visual HTML report of the color extraction pipeline."""
    html = [
        "<html><head><style>",
        "body { font-family: sans-serif; background: #f4f4f9; padding: 20px; color: #333; }",
        ".swatch { display: inline-block; width: 60px; height: 60px; margin: 5px; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        ".role-swatch { display: inline-block; width: 100px; height: 100px; margin: 10px; border-radius: 50%; border: 2px solid #ccc; }",
        ".container { background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }",
        "h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; }",
        "</style></head><body>",
        "<h1>Layer 1: Color Intelligence Debugger</h1>"
    ]
    
    # 1. Individual Image Palettes
    html.append("<div class='container'><h2>Stage 1: Extracted per Image</h2>")
    for img_name, palette in debug_data.get("image_palettes", {}).items():
        html.append(f"<h3>{img_name}</h3><div>")
        for rgb in palette:
            hex_val = rgb_to_hex(rgb)
            html.append(f"<div class='swatch' style='background-color: {hex_val};' title='{hex_val}'></div>")
        html.append("</div>")
    html.append("</div>")

    # 2. Weighted Average Output
    html.append("<div class='container'><h2>Stage 2: Weighted Average Palette (Top 10)</h2><div>")
    for rgb in debug_data.get("ranked_colors", [])[:10]:
        hex_val = rgb_to_hex(rgb)
        html.append(f"<div class='swatch' style='background-color: {hex_val};' title='{hex_val}'></div>")
    html.append("</div></div>")

    # 3. Final Roles & Harmony
    roles = debug_data.get("roles", {})
    html.append(f"<div class='container' style='background-color: {roles.get('bg')}; color: {roles.get('text')};'>")
    html.append("<h2>Stage 3: 60-30-10 Application & Analysis</h2>")
    html.append(f"<p><strong>Harmony Scheme:</strong> {debug_data.get('harmony')}</p>")
    html.append(f"<p><strong>Warmth:</strong> {debug_data.get('warmth')}</p>")
    
    html.append("<div>")
    html.append(f"<div class='role-swatch' style='background-color: {roles.get('primary')};'></div><p style='display:inline-block; vertical-align:top;'>Primary (60%)<br>{roles.get('primary')}</p>")
    html.append(f"<div class='role-swatch' style='background-color: {roles.get('secondary')};'></div><p style='display:inline-block; vertical-align:top;'>Secondary (30%)<br>{roles.get('secondary')}</p>")
    html.append(f"<div class='role-swatch' style='background-color: {roles.get('accent')};'></div><p style='display:inline-block; vertical-align:top;'>Accent (10%)<br>{roles.get('accent')}</p>")
    html.append("</div></div>")

    html.append("</body></html>")
    
    with open(out_path, "w") as f:
        f.write("\n".join(html))
    return out_path

def build_layer1_output(photos_folder, journal_type="travel", explicit_colors=None):
    supported = (".jpg", ".jpeg", ".png")
    photo_files = [
        f for f in sorted(os.listdir(photos_folder))
        if f.lower().endswith(supported)
    ]

    debug_data = {}

    if explicit_colors:
        ranked_colors = [hex_to_rgb(h) for h in explicit_colors]
        harmony = "user-defined"
        debug_data["image_palettes"] = {"User Defined": ranked_colors}
    else:
        photo_palettes = []
        debug_data["image_palettes"] = {}
        for filename in photo_files:
            path = os.path.join(photos_folder, filename)
            print(f"Extracting palette from {filename} ...")
            pal = extract_palette(path)
            photo_palettes.append(pal)
            debug_data["image_palettes"][filename] = pal

        if not photo_palettes:
            raise ValueError(f"No supported photos found in {photos_folder}")

        ranked_colors = weighted_average_palette(photo_palettes)
        hues = [rgb_to_hue(c) for c in ranked_colors[:5]]
        harmony = classify_harmony(hues)

    primary, secondary, accent = apply_60_30_10(ranked_colors)
    bg, text = pick_bg_and_text(primary)
    warmth = "warm" if is_warm(rgb_to_hue(primary)) else "cool"

    roles = {
        "primary": rgb_to_hex(primary),
        "secondary": rgb_to_hex(secondary),
        "accent": rgb_to_hex(accent),
        "bg": rgb_to_hex(bg),
        "text": rgb_to_hex(text),
    }

    # Populate debug data
    debug_data["ranked_colors"] = ranked_colors
    debug_data["harmony"] = harmony
    debug_data["warmth"] = warmth
    debug_data["roles"] = roles

    # Generate the visual HTML report
    debug_html_path = generate_debug_html(debug_data)
    print(f"Generated Visual Debugger at: {debug_html_path}")

    return {
        "layer_1": {
            "palette": [rgb_to_hex(c) for c in ranked_colors[:5]],
            "theme": journal_type.capitalize(),
            "theme_family": JOURNAL_THEME_FAMILIES.get(journal_type, "vibrant multicolor"),
            "harmony_scheme": harmony,
            "warmth": warmth,
            "roles": roles,
        }
    }


if __name__ == "__main__":
    # Fallback if folder doesn't exist to prevent crash during testing
    if not os.path.exists(PHOTOS_FOLDER) and not EXPLICIT_COLORS:
        print(f"Error: {PHOTOS_FOLDER} not found. Please create it or set EXPLICIT_COLORS.")
        sys.exit(1)
        
    result = build_layer1_output(PHOTOS_FOLDER, JOURNAL_TYPE, EXPLICIT_COLORS)

    out_path = "layer1_palette_output.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nDone. Wrote JSON to {out_path}")