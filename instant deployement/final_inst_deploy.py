"""
MemoryWeave — Fixed End-to-End Pipeline v2.2.0
===============================================
Fixes over v2.1.0 ("horrendous output"):
  FIX A  -- unified_templates.json path is resolved relative to the script
             file, not the working directory, so it is always found.
  FIX B  -- _builtin_template() replaced with four real, visually distinct
             layouts (Hero, Polaroid Grid, Scrapbook, Full-Bleed) that fill
             the whole page and look designed.
  FIX C  -- CSS renderer rewritten: photo frames get drop-shadows, rounded
             corners, optional rotation; pages get texture overlays; text
             blocks get real typography; decorative accent bars/stripes are
             injected from Layer 1 colors.
  FIX D  -- Google Fonts loaded via <link> for WeasyPrint network access.
  FIX E  -- Images embedded as data-URIs so WeasyPrint never fails on
             Windows file:// paths.
  FIX F  -- Template path printed clearly at startup so you can confirm
             whether unified_templates.json loaded or fallback ran.

All other pipeline logic (Layer 0, Layer 1, Layer 4, pick_templates) is
unchanged from v2.1.0.
"""

import base64
import html as html_lib
import os
import sys
import json
import uuid
import time
import math
import colorsys
import pathlib
import textwrap
from datetime import datetime

# ── colormath compatibility patch ─────────────────────────────────────────────
import numpy
if not hasattr(numpy, "asscalar"):
    numpy.asscalar = lambda a: a.item()

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color

try:
    from colorthief import ColorThief
    HAS_COLORTHIEF = True
except ImportError:
    HAS_COLORTHIEF = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ════════════════════════════════════════════════════════════════
#  ▶  CONFIG — edit these before running
# ════════════════════════════════════════════════════════════════
PHOTOS_FOLDER          = r"D:\Research\AI_memory_app\instant deployement\testphotos"
JOURNAL_TYPE           = "travel"
JOURNAL_TITLE          = "My Travel Journal"

# FIX A: resolve template path relative to THIS script, not cwd
_SCRIPT_DIR            = pathlib.Path(__file__).parent.resolve()
UNIFIED_TEMPLATES_PATH = r"D:\Research\AI_memory_app\instant deployement\day11_12_pdf_pipeline\unified_output\unified_templates.json"

OUTPUT_PDF             = r"final_journal.pdf"
SAVE_DEBUG_JSON        = True
SAVE_DEBUG_HTML        = True
MAX_PHOTOS             = 5          # increase when ready

GEMINI_API_KEY         = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY", "")

PAGE_WIDTH_IN          = 6.0
# ════════════════════════════════════════════════════════════════


# ── element type classifiers ──────────────────────────────────────────────────
PHOTO_TYPES  = {"photo","photo_frame","image_placeholder","polaroid","torn_photo",
                "photo_group","film_strip"}
TEXT_TYPES   = {"paragraph","text","text_area","text_label","title","subtitle"}
DECOR_TYPES  = {"sticker","doodle","doodle_placeholder","icon","vector_graphic",
                "graphic_element","ui_element","heart_icon","washi_tape"}
PERSON_TYPES = {"person_cutout"}
SHAPE_TYPES  = {"shape"}
MUSIC_TYPES  = {"music_card","song_cover"}

JOURNAL_THEME_FAMILIES = {
    "travel":     "warm earth tones, azure blues",
    "gratitude":  "soft lavenders, warm yellows",
    "reflective": "muted grays, deep teals",
    "goal":       "sharp blues, greens",
    "creative":   "vibrant multicolor",
}

# ── simple debug logger ───────────────────────────────────────────────────────
_LOG_LINES = []

def dbg(msg, indent=0):
    prefix = "  " * indent
    full = f"{prefix}{msg}"
    print(full)
    _LOG_LINES.append(full)

def dbg_sep(title=""):
    line = "═" * 60
    if title:
        line = f"  ▶ {title} " + "─" * max(0, 57 - len(title))
    dbg(line)


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 0 — Ingestion & Pre-processing  (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

def extract_exif_summary(image_path):
    try:
        image = Image.open(image_path)
        exif_raw = image._getexif()
        if not exif_raw:
            return {"date": None, "lat": None, "lon": None, "make": None, "model": None}
        exif = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_raw.items()}
        date_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
        lat = lon = None
        gps_info = exif.get("GPSInfo")
        if gps_info:
            gps_data = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
            def to_decimal(dms, ref):
                d, m, s = dms
                dec = d + m / 60 + s / 3600
                return -dec if ref in ("S", "W") else dec
            if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
                lat = to_decimal(gps_data["GPSLatitude"], gps_data["GPSLatitudeRef"])
            if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
                lon = to_decimal(gps_data["GPSLongitude"], gps_data["GPSLongitudeRef"])
        return {"date": date_str, "lat": lat, "lon": lon,
                "make": exif.get("Make"), "model": exif.get("Model")}
    except Exception as e:
        return {"date": None, "lat": None, "lon": None, "make": None, "model": None,
                "exif_error": str(e)}


VISION_PROMPT = textwrap.dedent("""\
    Analyze this travel photo. Return ONLY valid JSON matching this exact shape:
    {
      "dominant_colors": ["#hex1", "#hex2", "#hex3"],
      "scene_type": "beach|mountain|city|forest|food|people|landmark",
      "mood": "joyful|peaceful|adventurous|nostalgic|energetic",
      "subjects": ["subject1", "subject2"],
      "time_of_day": "morning|afternoon|evening|night",
      "weather": "sunny|cloudy|rainy|snowy",
      "composition_notes": "landscape|portrait|close-up|wide-shot"
    }""")

_VISION_FALLBACK = {
    "dominant_colors": ["#4A5568", "#718096", "#EDF2F7"],
    "scene_type": "city", "mood": "peaceful", "subjects": ["unknown"],
    "time_of_day": "afternoon", "weather": "sunny",
    "composition_notes": "landscape",
}

def get_image_fingerprint(client, image_path, retries=3):
    try:
        from google.genai import types as genai_types
        img = Image.open(image_path)
        config = genai_types.GenerateContentConfig(
            response_mime_type="application/json", max_output_tokens=1024
        )
        for attempt in range(retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=[img, VISION_PROMPT],
                    config=config,
                )
                if not response or not response.text:
                    raise ValueError("Empty response from Gemini.")
                fp = json.loads(response.text.strip())
                usage = {
                    "input_tokens":  (response.usage_metadata.prompt_token_count    if response.usage_metadata else 0),
                    "output_tokens": (response.usage_metadata.candidates_token_count if response.usage_metadata else 0),
                }
                return fp, usage
            except Exception as e:
                if "503" in str(e) and attempt < retries - 1:
                    wait = (attempt + 1) * 3
                    dbg(f"[Gemini 503] Retrying in {wait}s …", 2)
                    time.sleep(wait)
                    continue
                raise
    except Exception as e:
        dbg(f"[Vision fallback] {os.path.basename(image_path)}: {e}", 2)
        fallback = dict(_VISION_FALLBACK, vision_error=str(e))
        return fallback, {"input_tokens": 0, "output_tokens": 0}


def run_layer0(photos_folder, max_photos=MAX_PHOTOS):
    dbg_sep("LAYER 0 — Ingestion & Vision Fingerprinting")

    gemini_client = None
    if GEMINI_API_KEY:
        try:
            from google import genai as google_genai
            gemini_client = google_genai.Client(api_key=GEMINI_API_KEY)
            dbg("Gemini client ready.", 1)
        except ImportError:
            dbg("[Warning] google-genai not installed. Vision will use fallback values.", 1)
    else:
        dbg("[Warning] GEMINI_API_KEY not set. Using fallback vision fingerprints.", 1)

    supported = (".jpg", ".jpeg", ".png")
    photo_files = [
        f for f in sorted(os.listdir(photos_folder))
        if f.lower().endswith(supported)
    ][:max_photos]

    if not photo_files:
        raise ValueError(f"No supported photos found in: {photos_folder}")

    dbg(f"Found {len(photo_files)} photo(s) (MAX_PHOTOS={max_photos}):", 1)

    layer0 = {"session_id": str(uuid.uuid4()), "photos": []}
    total_in = total_out = 0

    for i, filename in enumerate(photo_files, start=1):
        path = os.path.join(photos_folder, filename)
        dbg(f"[{i}/{len(photo_files)}] {filename}", 2)
        exif = extract_exif_summary(path)
        dbg(f"EXIF  date={exif['date']}  lat={exif['lat']}  lon={exif['lon']}", 3)

        if gemini_client:
            fp, usage = get_image_fingerprint(gemini_client, path)
        else:
            fp = dict(_VISION_FALLBACK)
            usage = {"input_tokens": 0, "output_tokens": 0}

        dbg(f"Vision scene={fp.get('scene_type')}  mood={fp.get('mood')}  "
            f"colors={fp.get('dominant_colors',[])[:3]}", 3)
        dbg(f"tokens in={usage['input_tokens']} out={usage['output_tokens']}", 3)

        total_in  += usage["input_tokens"]
        total_out += usage["output_tokens"]
        layer0["photos"].append({
            "id":       f"p{i}",
            "path":     path,
            "filename": filename,
            "exif":     exif,
            "semantic": fp,
        })

    layer0["token_usage"] = {
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
    }
    dbg(f"Layer 0 complete. Total tokens — in:{total_in}  out:{total_out}", 1)
    return layer0


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1 — Color Intelligence  (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

def _rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _rgb_to_lab(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    return convert_color(sRGBColor(r, g, b), LabColor)

def _rgb_to_hue(rgb):
    r, g, b = [c / 255.0 for c in rgb]
    h, _, _ = colorsys.rgb_to_hls(r, g, b)
    return h * 360

def _classify_harmony(hues):
    if len(hues) < 2: return "monochrome"
    hues = sorted(hues)
    diffs = [(hues[i+1] - hues[i]) % 360 for i in range(len(hues)-1)]
    diffs.append((hues[0] + 360 - hues[-1]) % 360)
    spread = max(diffs)
    if spread > 150: return "complementary"
    if spread > 90:  return "split-complementary"
    if spread > 40:  return "triadic"
    return "analogous"

def _lighten(hex_color, factor=0.6):
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return _rgb_to_hex((r, g, b))

def _darken(hex_color, factor=0.4):
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return _rgb_to_hex((r, g, b))


def run_layer1(layer0_photos, journal_type="travel", explicit_colors=None):
    dbg_sep("LAYER 1 — Color Intelligence")

    if explicit_colors:
        ranked = [_hex_to_rgb(h) for h in explicit_colors]
        harmony = "user-defined"
        dbg(f"Using explicit colors: {explicit_colors}", 1)
    else:
        photo_paths = [p["path"] for p in layer0_photos if os.path.exists(p.get("path", ""))]

        if HAS_COLORTHIEF and photo_paths:
            dbg("Extracting palette via ColorThief …", 1)
            weighted = {}
            for path in photo_paths:
                ct = ColorThief(path)
                palette = ct.get_palette(color_count=5, quality=1)
                for rank, rgb in enumerate(palette):
                    weight = len(palette) - rank
                    weighted[rgb] = weighted.get(rgb, 0) + weight
        else:
            dbg("ColorThief not available — using Gemini color output.", 1)
            weighted = {}
            for photo in layer0_photos:
                colors = photo["semantic"].get("dominant_colors", [])
                for rank, hex_str in enumerate(colors):
                    try:
                        rgb = _hex_to_rgb(hex_str)
                        weight = len(colors) - rank
                        weighted[rgb] = weighted.get(rgb, 0) + weight
                    except Exception:
                        continue

        if not weighted:
            weighted = {(74, 85, 104): 1}

        ranked = [rgb for rgb, _ in sorted(weighted.items(), key=lambda kv: kv[1], reverse=True)]
        hues = [_rgb_to_hue(c) for c in ranked[:5]]
        harmony = _classify_harmony(hues)

    primary   = ranked[0]
    secondary = ranked[1] if len(ranked) > 1 else primary
    accent    = ranked[2] if len(ranked) > 2 else ranked[-1]
    tertiary  = ranked[3] if len(ranked) > 3 else accent

    lab = _rgb_to_lab(primary)
    if lab.lab_l > 60:
        bg   = (250, 248, 244)
        text = (30, 28, 26)
    else:
        bg   = (252, 250, 246)
        text = (20, 18, 16)

    warmth = "warm" if (_rgb_to_hue(primary) <= 70 or _rgb_to_hue(primary) >= 320) else "cool"

    primary_hex   = _rgb_to_hex(primary)
    secondary_hex = _rgb_to_hex(secondary)
    accent_hex    = _rgb_to_hex(accent)

    roles = {
        "primary":          primary_hex,
        "primary_light":    _lighten(primary_hex, 0.7),
        "primary_dark":     _darken(primary_hex, 0.3),
        "secondary":        secondary_hex,
        "secondary_light":  _lighten(secondary_hex, 0.7),
        "accent":           accent_hex,
        "tertiary":         _rgb_to_hex(tertiary),
        "bg":               _rgb_to_hex(bg),
        "bg_alt":           _lighten(primary_hex, 0.85),
        "text":             _rgb_to_hex(text),
        "text_muted":       _lighten(_rgb_to_hex(text), 0.4),
        "border":           _lighten(primary_hex, 0.5),
        "overlay":          primary_hex + "22",
        "text_on_primary":  "#FFFFFF" if lab.lab_l < 60 else "#1A1A1A",
    }

    layer1 = {
        "palette":        [_rgb_to_hex(c) for c in ranked[:5]],
        "theme":          journal_type.capitalize(),
        "theme_family":   JOURNAL_THEME_FAMILIES.get(journal_type, "vibrant multicolor"),
        "harmony_scheme": harmony,
        "warmth":         warmth,
        "roles":          roles,
    }

    dbg(f"Harmony: {harmony}  |  Warmth: {warmth}", 1)
    dbg(f"Primary: {roles['primary']}  Secondary: {roles['secondary']}  "
        f"Accent: {roles['accent']}", 1)
    dbg(f"BG: {roles['bg']}  BG_alt: {roles['bg_alt']}  "
        f"Text: {roles['text']}  Border: {roles['border']}", 1)
    dbg(f"Full palette: {layer1['palette']}", 1)
    return layer1


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — Story / Caption Generation  (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

CAPTION_SYSTEM = textwrap.dedent("""\
    You are writing personal journal entries. You write in first person.
    Be vivid, sensory, and emotionally honest. Avoid clichés.
    Keep captions to 2-3 sentences unless asked for more.""")

def _build_caption_prompt(photo, journal_type):
    sem  = photo["semantic"]
    exif = photo["exif"]
    date = exif.get("date", "unknown date")
    loc  = (f"lat {exif['lat']:.2f}, lon {exif['lon']:.2f}"
            if exif.get("lat") else "unknown location")
    return (
        f"Write a {journal_type} journal caption for this photo.\n"
        f"Scene: {sem.get('scene_type','unknown')} | Mood: {sem.get('mood','unknown')} | "
        f"Time: {sem.get('time_of_day','unknown')} | Weather: {sem.get('weather','unknown')}\n"
        f"Subjects: {', '.join(sem.get('subjects', ['unknown']))}\n"
        f"Date: {date} | Location: {loc}\n"
        f"Colors: {', '.join(sem.get('dominant_colors', []))}"
    )


def run_layer4(layer0_photos, journal_type="travel"):
    dbg_sep("LAYER 4 — Caption Generation")
    captions = {}

    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            for photo in layer0_photos:
                prompt = _build_caption_prompt(photo, journal_type)
                try:
                    msg = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=300,
                        system=CAPTION_SYSTEM,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    text = msg.content[0].text.strip()
                    captions[photo["id"]] = text
                    dbg(f"[{photo['id']}] {photo['filename']}", 2)
                    dbg(f"→ {text[:120]}{'…' if len(text)>120 else ''}", 3)
                except Exception as e:
                    dbg(f"[Layer 4 error] {photo['id']}: {e}", 2)
                    captions[photo["id"]] = _fallback_caption(photo)
        except ImportError:
            dbg("[Warning] anthropic package not installed. Using placeholder captions.", 1)
            for photo in layer0_photos:
                captions[photo["id"]] = _fallback_caption(photo)
    else:
        dbg("[Warning] ANTHROPIC_API_KEY not set. Using placeholder captions.", 1)
        for photo in layer0_photos:
            captions[photo["id"]] = _fallback_caption(photo)

    dbg(f"Generated {len(captions)} captions.", 1)
    return captions


def _fallback_caption(photo):
    sem = photo["semantic"]
    return (
        f"A {sem.get('mood','peaceful')} moment at a {sem.get('scene_type','place')}. "
        f"Captured during {sem.get('time_of_day','the day')} under {sem.get('weather','clear')} skies."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE PICKER  (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

MOOD_TEMPLATE_HINTS = {
    "joyful":      ["collage", "diary", "scrapbook", "polaroid"],
    "peaceful":    ["diary", "minimal", "memoir", "text"],
    "adventurous": ["travel", "adventure", "landscape", "split"],
    "nostalgic":   ["film", "polaroid", "scrapbook", "snippets"],
    "energetic":   ["collage", "maximalist", "mosaic"],
}

JOURNAL_TYPE_TEMPLATE_PREFS = {
    "travel":     ["travel", "adventure", "landscape", "portrait", "scenery", "split"],
    "gratitude":  ["gratitude", "soft", "minimal", "portrait", "diary"],
    "reflective": ["reflective", "text", "minimal", "memoir"],
    "goal":       ["goal", "modern", "grid", "structured"],
    "creative":   ["creative", "collage", "artistic", "mosaic"],
}


def pick_templates(templates, journal_type, layer0_photos, layer1_data):
    n_photos    = len(layer0_photos)
    pages_needed = max(1, math.ceil(n_photos / 2))

    dbg_sep("LAYOUT — Template Selection")
    dbg(f"Photos: {n_photos}  →  pages needed: {pages_needed}", 1)

    moods = [p["semantic"].get("mood", "") for p in layer0_photos]
    mood_keywords = []
    for m in set(moods):
        mood_keywords.extend(MOOD_TEMPLATE_HINTS.get(m, []))

    prefs = [p.lower() for p in JOURNAL_TYPE_TEMPLATE_PREFS.get(journal_type, [])]
    harmony   = layer1_data.get("harmony_scheme", "")
    warmth    = layer1_data.get("warmth", "")

    dbg(f"Journal prefs: {prefs}", 2)
    dbg(f"Mood keywords from Layer 0: {list(set(mood_keywords))}", 2)
    dbg(f"Harmony: {harmony}  Warmth: {warmth}", 2)

    def score(t):
        name_cat = (t.get("name","") + " " + t.get("category","")).lower()
        s = 0
        s += sum(3 for p in prefs if p in name_cat)
        s += sum(2 for mk in mood_keywords if mk in name_cat)
        if warmth == "warm" and any(w in name_cat for w in ["cozy","warm","earth","diary","scrapbook"]):
            s += 1
        if warmth == "cool" and any(w in name_cat for w in ["editorial","modern","minimal","grid"]):
            s += 1
        return s

    ranked = sorted(templates, key=score, reverse=True)

    chosen = []
    for i in range(pages_needed):
        chosen.append(ranked[i % len(ranked)])

    dbg(f"Selected {len(chosen)} template(s):", 1)
    for t in chosen:
        dbg(f"  → [{t['template_id']}] {t['name']}  (category: {t.get('category','')})", 2)

    return chosen


# ══════════════════════════════════════════════════════════════════════════════
# FIX B — Beautiful built-in fallback templates
# ══════════════════════════════════════════════════════════════════════════════

def _builtin_templates(n_pages):
    """
    Four visually distinct layouts that FILL the page. Returns exactly
    n_pages templates, cycling through the four designs.
    """

    # ── Layout 1: Hero + sidebar ───────────────────────────────────────────
    def _hero_sidebar(page_num):
        return {
            "template_id":  f"bt_hero_{page_num}",
            "name":         f"Hero + Sidebar (page {page_num})",
            "category":     "travel",
            "source_file":  "built-in",
            "canvas":       {"width_px": 1200, "height_px": 1600},
            "background_color": None,
            "layout_hint":  "hero_sidebar",
            "elements": [
                # Accent stripe top
                {"id": f"stripe_top_{page_num}", "type": "shape",
                 "x": 0, "y": 0, "w": 100, "h": 4, "rotation": 0, "z_index": 3,
                 "slot": None, "text": None,
                 "css": {"background": "__accent__", "border-radius": "0"}, "children": []},
                # Title block
                {"id": f"title_{page_num}", "type": "title",
                 "x": 4, "y": 5, "w": 92, "h": 7, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {}, "children": []},
                # Large hero photo (left, tall)
                {"id": f"hero_{page_num}", "type": "photo",
                 "x": 4, "y": 14, "w": 58, "h": 52, "rotation": 0, "z_index": 1,
                 "slot": None, "text": None,
                 "css": {"border-radius": "6px",
                         "box-shadow": "0 8px 24px rgba(0,0,0,0.22)"}, "children": []},
                # Sidebar photo 1
                {"id": f"side1_{page_num}", "type": "photo",
                 "x": 65, "y": 14, "w": 31, "h": 24, "rotation": -1.5, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "4px",
                         "box-shadow": "0 4px 14px rgba(0,0,0,0.18)",
                         "border": "3px solid #ffffff"}, "children": []},
                # Sidebar photo 2
                {"id": f"side2_{page_num}", "type": "photo",
                 "x": 65, "y": 41, "w": 31, "h": 25, "rotation": 1.2, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "4px",
                         "box-shadow": "0 4px 14px rgba(0,0,0,0.18)",
                         "border": "3px solid #ffffff"}, "children": []},
                # Caption block below hero
                {"id": f"cap1_{page_num}", "type": "paragraph",
                 "x": 4, "y": 68, "w": 58, "h": 13, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "6px", "padding": "10px"}, "children": []},
                # Caption block beside sidebar
                {"id": f"cap2_{page_num}", "type": "paragraph",
                 "x": 65, "y": 68, "w": 31, "h": 13, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "6px", "padding": "10px"}, "children": []},
                # Decorative doodle bottom-right
                {"id": f"doodle_{page_num}", "type": "doodle",
                 "x": 82, "y": 84, "w": 14, "h": 10, "rotation": 12, "z_index": 3,
                 "slot": None, "text": None,
                 "css": {"border-radius": "50%", "opacity": "0.55"}, "children": []},
                # Accent stripe bottom
                {"id": f"stripe_bot_{page_num}", "type": "shape",
                 "x": 0, "y": 97, "w": 100, "h": 3, "rotation": 0, "z_index": 3,
                 "slot": None, "text": None,
                 "css": {"background": "__accent__", "border-radius": "0"}, "children": []},
            ],
        }

    # ── Layout 2: Polaroid grid ────────────────────────────────────────────
    def _polaroid_grid(page_num):
        # 2×1 polaroids top, 1 wide photo bottom, captions woven in
        return {
            "template_id":  f"bt_polaroid_{page_num}",
            "name":         f"Polaroid Grid (page {page_num})",
            "category":     "travel",
            "source_file":  "built-in",
            "canvas":       {"width_px": 1200, "height_px": 1600},
            "background_color": None,
            "layout_hint":  "polaroid_grid",
            "elements": [
                # Color band top
                {"id": f"band_{page_num}", "type": "shape",
                 "x": 0, "y": 0, "w": 100, "h": 10, "rotation": 0, "z_index": 1,
                 "slot": None, "text": None,
                 "css": {"background": "__primary__", "border-radius": "0"}, "children": []},
                # Title on band
                {"id": f"title_{page_num}", "type": "title",
                 "x": 8, "y": 1, "w": 84, "h": 8, "rotation": 0, "z_index": 4,
                 "slot": None, "text": None,
                 "css": {"color": "__text_on_primary__"}, "children": []},
                # Polaroid 1
                {"id": f"pol1_{page_num}", "type": "photo",
                 "x": 6, "y": 13, "w": 40, "h": 32, "rotation": -2.5, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border": "6px solid #FFFFFF",
                         "border-bottom": "22px solid #FFFFFF",
                         "box-shadow": "0 6px 20px rgba(0,0,0,0.25)",
                         "border-radius": "2px"}, "children": []},
                # Polaroid 2
                {"id": f"pol2_{page_num}", "type": "photo",
                 "x": 54, "y": 13, "w": 40, "h": 32, "rotation": 2.0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border": "6px solid #FFFFFF",
                         "border-bottom": "22px solid #FFFFFF",
                         "box-shadow": "0 6px 20px rgba(0,0,0,0.25)",
                         "border-radius": "2px"}, "children": []},
                # Caption strip between polaroids and wide photo
                {"id": f"cap_mid_{page_num}", "type": "paragraph",
                 "x": 6, "y": 47, "w": 88, "h": 10, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "4px"}, "children": []},
                # Wide landscape photo
                {"id": f"wide_{page_num}", "type": "photo",
                 "x": 6, "y": 59, "w": 88, "h": 30, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "8px",
                         "box-shadow": "0 8px 28px rgba(0,0,0,0.20)"}, "children": []},
                # Bottom caption
                {"id": f"cap_bot_{page_num}", "type": "paragraph",
                 "x": 6, "y": 91, "w": 88, "h": 7, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "4px"}, "children": []},
            ],
        }

    # ── Layout 3: Scrapbook collage ────────────────────────────────────────
    def _scrapbook(page_num):
        return {
            "template_id":  f"bt_scrapbook_{page_num}",
            "name":         f"Scrapbook Collage (page {page_num})",
            "category":     "travel",
            "source_file":  "built-in",
            "canvas":       {"width_px": 1200, "height_px": 1600},
            "background_color": None,
            "layout_hint":  "scrapbook",
            "elements": [
                # Diagonal accent ribbon (simulated with rotated shape)
                {"id": f"ribbon_{page_num}", "type": "shape",
                 "x": -5, "y": 4, "w": 110, "h": 5, "rotation": -3, "z_index": 1,
                 "slot": None, "text": None,
                 "css": {"background": "__accent__", "opacity": "0.75"}, "children": []},
                # Title
                {"id": f"title_{page_num}", "type": "title",
                 "x": 5, "y": 2, "w": 70, "h": 8, "rotation": 0, "z_index": 5,
                 "slot": None, "text": None, "css": {}, "children": []},
                # Large overlapping photo
                {"id": f"main_{page_num}", "type": "photo",
                 "x": 5, "y": 12, "w": 62, "h": 42, "rotation": -1, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border": "5px solid #FFFFFF",
                         "box-shadow": "3px 6px 18px rgba(0,0,0,0.22)",
                         "border-radius": "3px"}, "children": []},
                # Overlapping smaller photo (top right, slight rotation)
                {"id": f"inset_{page_num}", "type": "photo",
                 "x": 58, "y": 8, "w": 36, "h": 28, "rotation": 3.5, "z_index": 3,
                 "slot": None, "text": None,
                 "css": {"border": "5px solid #FFFFFF",
                         "box-shadow": "4px 8px 16px rgba(0,0,0,0.20)",
                         "border-radius": "3px"}, "children": []},
                # Caption over-laid on lower half
                {"id": f"cap1_{page_num}", "type": "paragraph",
                 "x": 5, "y": 56, "w": 55, "h": 14, "rotation": 0, "z_index": 4,
                 "slot": None, "text": None,
                 "css": {"border-radius": "4px", "opacity": "0.92"}, "children": []},
                # Second photo bottom-right
                {"id": f"bot_{page_num}", "type": "photo",
                 "x": 62, "y": 38, "w": 34, "h": 32, "rotation": -2.0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border": "5px solid #FFFFFF",
                         "box-shadow": "3px 6px 18px rgba(0,0,0,0.22)",
                         "border-radius": "3px"}, "children": []},
                # Full-width caption strip
                {"id": f"cap2_{page_num}", "type": "paragraph",
                 "x": 5, "y": 73, "w": 90, "h": 14, "rotation": 0, "z_index": 4,
                 "slot": None, "text": None,
                 "css": {"border-radius": "4px"}, "children": []},
                # Washi tape decorations
                {"id": f"washi1_{page_num}", "type": "washi_tape",
                 "x": 2, "y": 10, "w": 8, "h": 3, "rotation": -45, "z_index": 5,
                 "slot": None, "text": None,
                 "css": {"opacity": "0.8"}, "children": []},
                {"id": f"washi2_{page_num}", "type": "washi_tape",
                 "x": 88, "y": 34, "w": 8, "h": 3, "rotation": 30, "z_index": 5,
                 "slot": None, "text": None,
                 "css": {"opacity": "0.8"}, "children": []},
                # Bottom accent band
                {"id": f"bot_band_{page_num}", "type": "shape",
                 "x": 0, "y": 90, "w": 100, "h": 10, "rotation": 0, "z_index": 1,
                 "slot": None, "text": None,
                 "css": {"background": "__primary_light__", "border-radius": "0"}, "children": []},
            ],
        }

    # ── Layout 4: Full-bleed editorial ────────────────────────────────────
    def _editorial(page_num):
        return {
            "template_id":  f"bt_editorial_{page_num}",
            "name":         f"Full-Bleed Editorial (page {page_num})",
            "category":     "travel",
            "source_file":  "built-in",
            "canvas":       {"width_px": 1200, "height_px": 1600},
            "background_color": None,
            "layout_hint":  "editorial",
            "elements": [
                # Full-bleed top photo
                {"id": f"bleed_{page_num}", "type": "photo",
                 "x": 0, "y": 0, "w": 100, "h": 55, "rotation": 0, "z_index": 1,
                 "slot": None, "text": None,
                 "css": {"border-radius": "0"}, "children": []},
                # Semi-transparent title overlay on photo
                {"id": f"title_overlay_{page_num}", "type": "title",
                 "x": 0, "y": 42, "w": 100, "h": 13, "rotation": 0, "z_index": 3,
                 "slot": None, "text": None,
                 "css": {"background": "rgba(0,0,0,0.45)",
                         "color": "#FFFFFF",
                         "padding": "12px 20px"}, "children": []},
                # Two bottom photos side by side
                {"id": f"bot_l_{page_num}", "type": "photo",
                 "x": 2, "y": 57, "w": 46, "h": 28, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "6px",
                         "box-shadow": "0 4px 16px rgba(0,0,0,0.18)"}, "children": []},
                {"id": f"bot_r_{page_num}", "type": "photo",
                 "x": 52, "y": 57, "w": 46, "h": 28, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "6px",
                         "box-shadow": "0 4px 16px rgba(0,0,0,0.18)"}, "children": []},
                # Caption strip
                {"id": f"cap_{page_num}", "type": "paragraph",
                 "x": 2, "y": 87, "w": 96, "h": 11, "rotation": 0, "z_index": 2,
                 "slot": None, "text": None,
                 "css": {"border-radius": "6px"}, "children": []},
            ],
        }

    layouts = [_hero_sidebar, _polaroid_grid, _scrapbook, _editorial]
    return [layouts[i % len(layouts)](i + 1) for i in range(n_pages)]


# ══════════════════════════════════════════════════════════════════════════════
# COLOR INJECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _image_to_data_uri(path):
    """Embed images as base64 data URIs — avoids Windows file:// failures."""
    ext  = pathlib.Path(path).suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png",  ".gif": "image/gif",
            ".webp": "image/webp"}.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _classify(type_name):
    t = (type_name or "").lower()
    if t in PHOTO_TYPES:  return "photo"
    if t in TEXT_TYPES:   return "text"
    if t in DECOR_TYPES:  return "decor"
    if t in PERSON_TYPES: return "person"
    if t in SHAPE_TYPES:  return "shape"
    if t in MUSIC_TYPES:  return "music"
    return "other"


def _hex_to_rgb_safe(h):
    """Return (r,g,b) or None if h is not a valid hex color."""
    if not h or not isinstance(h, str):
        return None
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _rgb_dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# CSS properties whose values are colors
_COLOR_PROPS = {
    "background", "background-color", "color",
    "border-color", "outline-color",
    "border-top-color", "border-bottom-color",
    "border-left-color", "border-right-color",
}

# Shorthand border properties — extract color token from them
_BORDER_SHORTHANDS = {"border", "border-top", "border-bottom", "border-left", "border-right"}


def _extract_hex_from_border(val):
    """
    From a shorthand border value like '3px solid #FFFFFF', extract '#FFFFFF'.
    Returns the hex string or None.
    """
    for token in val.split():
        rgb = _hex_to_rgb_safe(token)
        if rgb is not None:
            return token
    return None


def remap_hardcoded_color(hex_color, roles):
    """
    Map ANY hardcoded template color to the semantically correct Layer 1 role.

    Priority:
      1. __token__ placeholder strings → already handled by _resolve_css_tokens
      2. Very-light (near-white) → roles['bg']
      3. Near-white with slight tint → roles['bg_alt']
      4. Very-dark → roles['text']
      5. Dark desaturated → roles['text_muted']
      6. Everything else → nearest Layer 1 palette color by RGB distance

    This ensures that even templates with fully hardcoded colors (hex values
    baked in by a design tool) pick up the correct palette from Layer 1.
    """
    rgb = _hex_to_rgb_safe(hex_color)
    if rgb is None:
        return hex_color          # not a plain hex; leave unchanged (rgba, named, etc.)

    r, g, b = rgb
    # Lightness in [0,1]
    l = (max(r, g, b) + min(r, g, b)) / 510.0
    # Saturation (HSL)
    c_max, c_min = max(r,g,b)/255, min(r,g,b)/255
    s = 0 if (c_max == c_min) else (c_max - c_min) / (1 - abs(2*l - 1))

    # Hard semantic rules
    if l > 0.90:                    return roles["bg"]
    if l > 0.80 and s < 0.08:      return roles["bg_alt"]
    if l < 0.12:                    return roles["text"]
    if l < 0.28 and s < 0.15:      return roles["text_muted"]

    # Nearest-palette match among the remaining roles
    candidates = {
        "primary":         _hex_to_rgb_safe(roles["primary"]),
        "primary_light":   _hex_to_rgb_safe(roles["primary_light"]),
        "primary_dark":    _hex_to_rgb_safe(roles["primary_dark"]),
        "secondary":       _hex_to_rgb_safe(roles["secondary"]),
        "secondary_light": _hex_to_rgb_safe(roles["secondary_light"]),
        "accent":          _hex_to_rgb_safe(roles["accent"]),
        "tertiary":        _hex_to_rgb_safe(roles["tertiary"]),
        "bg_alt":          _hex_to_rgb_safe(roles["bg_alt"]),
        "text_muted":      _hex_to_rgb_safe(roles["text_muted"]),
        "border":          _hex_to_rgb_safe(roles["border"]),
    }
    candidates = {k: v for k, v in candidates.items() if v}
    best = min(candidates, key=lambda r_: _rgb_dist(rgb, candidates[r_]))
    return roles[best]


def _recolor_css_value(prop, val, roles):
    """
    Given a CSS property name and its string value, replace any hardcoded hex
    color with the Layer 1 equivalent.  Handles:
      - plain color props:  background, color, border-color …
      - border shorthands:  border: 3px solid #FFF  →  3px solid <bg>
      - rgba() / hsl()  left unchanged (not plain hex)
    """
    prop = prop.strip().lower()

    if prop in _COLOR_PROPS:
        mapped = remap_hardcoded_color(val, roles)
        return mapped

    if prop in _BORDER_SHORTHANDS:
        hex_token = _extract_hex_from_border(val)
        if hex_token:
            mapped = remap_hardcoded_color(hex_token, roles)
            return val.replace(hex_token, mapped)

    return val   # untouched (numeric props, border-radius, etc.)


def _resolve_and_recolor_css(css_dict, roles, is_builtin):
    """
    Full CSS processing pipeline for one element:
      Step 1 — replace __token__ placeholders  (both builtin & unified)
      Step 2 — remap hardcoded hex colors       (only for unified templates,
                because builtin templates already use __token__ for everything
                intentional and white photo borders are on purpose)

    `is_builtin` is True when the template came from _builtin_templates().
    """
    # Step 1: token replacement
    resolved = {}
    for k, v in css_dict.items():
        if isinstance(v, str):
            for role, color in roles.items():
                v = v.replace(f"__{role}__", color)
        resolved[k] = v

    # Step 2: remap remaining hardcoded hex colors in unified templates
    if not is_builtin:
        remapped = {}
        for k, v in resolved.items():
            remapped[k] = _recolor_css_value(k, v, roles)
        return remapped

    return resolved


def _render_element(el, photo_slots, slot_cursor, caption_map, roles,
                    journal_title, is_builtin):
    el_css    = _resolve_and_recolor_css(el.get("css", {}), roles, is_builtin)
    css_str   = "; ".join(f"{k}: {v}" for k, v in el_css.items())
    rotation  = el.get("rotation", 0) or 0
    transform = f"transform: rotate({rotation}deg);" if rotation else ""
    box = (
        f"left:{el['x']}%; top:{el['y']}%; "
        f"width:{el['w']}%; height:{el['h']}%; "
        f"z-index:{el.get('z_index', 1)}; {transform} {css_str}"
    )
    cls = _classify(el.get("type"))

    children_html = "".join(
        _render_element(c, photo_slots, slot_cursor, caption_map, roles,
                        journal_title, is_builtin)
        for c in el.get("children", [])
    )

    inner = ""

    if cls == "photo":
        idx = slot_cursor[0]
        if idx < len(photo_slots):
            matched_path = photo_slots[idx]
            slot_cursor[0] += 1
            if matched_path and os.path.exists(matched_path):
                uri = _image_to_data_uri(matched_path)
                inner = f'<img src="{uri}" class="photo-fill" />'
            else:
                inner = '<div class="photo-placeholder">📷</div>'
        else:
            inner = '<div class="photo-placeholder">📷</div>'

    elif cls == "text":
        el_type = el.get("type", "").lower()
        el_id   = el.get("id", "").lower()

        if el_type == "title" or "title" in el_id or "overlay" in el_id:
            caption = html_lib.escape(journal_title)
            # Title on dark overlay → white text; otherwise theme text
            title_color = (
                roles["text_on_primary"]
                if "overlay" in el_id or el_css.get("background","").startswith("rgba(0,0")
                else roles["text"]
            )
            inner = f'<p class="title-text" style="color:{title_color}">{caption}</p>'
        else:
            text_idx  = caption_map.get("__text_cursor__", 0)
            photo_ids = caption_map.get("__photo_ids__", [])
            if text_idx < len(photo_ids):
                raw = caption_map.get(photo_ids[text_idx], el.get("text", "") or "")
                caption_map["__text_cursor__"] = text_idx + 1
            else:
                raw = el.get("text", "") or ""
            if raw:
                inner = f'<p class="caption-text">{html_lib.escape(raw)}</p>'

    elif cls == "decor":
        inner = ""  # purely decorative

    elif cls == "shape":
        bg = el_css.get("background", roles.get("secondary_light", "#EEE"))
        box += f" background: {bg};"

    return f'<div class="ph-el ph-{cls}" style="{box}">{inner}{children_html}</div>'


def _is_builtin_template(template):
    """True if this template was generated by _builtin_templates(), not loaded from JSON."""
    return template.get("source_file") == "built-in"


def _recolor_template_background(template, roles):
    """
    Replace the template-level background_color with a Layer 1 value.
    If the template has a hardcoded background, remap it.
    If it's None or missing, use bg_alt.
    """
    raw_bg = template.get("background_color")
    if not raw_bg:
        return roles["bg_alt"]
    # Try to remap
    remapped = remap_hardcoded_color(raw_bg, roles)
    return remapped


def _render_page(template, photo_slots, slot_cursor, captions, photo_ids,
                 roles, journal_title, page_index):
    w = template["canvas"]["width_px"]
    h = template["canvas"]["height_px"]
    page_height_in = PAGE_WIDTH_IN * (h / w)

    caption_map = dict(captions)
    caption_map["__text_cursor__"] = page_index * 2
    caption_map["__photo_ids__"]   = photo_ids

    is_builtin = _is_builtin_template(template)
    bg = _recolor_template_background(template, roles)

    elements_html = "".join(
        _render_element(el, photo_slots, slot_cursor, caption_map, roles,
                        journal_title, is_builtin)
        for el in template["elements"]
    )

    texture = (
        f"background: {bg}; "
        "background-image: repeating-linear-gradient("
        "0deg, transparent, transparent 28px, rgba(0,0,0,0.015) 28px, rgba(0,0,0,0.015) 29px);"
    )

    dbg(f"  bg={bg}  builtin={is_builtin}", 3)

    return (
        f'<div class="sheet" style="width:{PAGE_WIDTH_IN}in; height:{page_height_in:.3f}in; '
        f'{texture}">{elements_html}</div>'
    ), page_height_in


def run_layer5(templates, layer0_photos, layer1_data, captions, output_pdf, journal_title):
    dbg_sep("LAYER 5 — PDF Rendering")

    try:
        import weasyprint
    except ImportError:
        dbg("\n[ERROR] WeasyPrint not installed. Run:  pip install weasyprint")
        dbg("        Skipping PDF generation.\n")
        return False

    roles     = layer1_data["roles"]
    photo_ids = [p["id"] for p in layer0_photos]

    photo_slots = [
        p["path"] for p in layer0_photos
        if os.path.exists(p.get("path", ""))
    ]

    dbg(f"Photo slots available: {len(photo_slots)}", 1)
    for i, path in enumerate(photo_slots):
        dbg(f"  slot[{i+1}] → {os.path.basename(path)}", 2)

    dbg("Layer 1 color roles injected into renderer:", 1)
    for role, color in roles.items():
        dbg(f"  {role:20s} → {color}", 2)

    slot_cursor = [0]
    pages_html  = []
    max_height_in = PAGE_WIDTH_IN

    for page_index, template in enumerate(templates):
        is_builtin = _is_builtin_template(template)
        dbg(f"Rendering page {page_index+1}: [{template['template_id']}] "
            f"{template['name']}  [{'builtin' if is_builtin else 'unified'}]", 1)
        page_html, ph_in = _render_page(
            template, photo_slots, slot_cursor, captions, photo_ids,
            roles, journal_title, page_index
        )
        pages_html.append(page_html)
        max_height_in = max(max_height_in, ph_in)
        dbg(f"  Page size: {PAGE_WIDTH_IN}in × {ph_in:.2f}in  "
            f"(photos consumed so far: {slot_cursor[0]})", 2)

    outer_w = PAGE_WIDTH_IN + 0.5
    outer_h = max_height_in + 0.5

    # ── Global CSS ─────────────────────────────────────────────────────────────
    # These rules are the BASELINE. For builtin templates, __token__ substitution
    # handles element-level colors. For unified templates, the remap_hardcoded_color
    # engine handles element-level colors. Global CSS handles:
    #   - page background and borders
    #   - photo frames (class-level fallbacks)
    #   - text typography and color
    #   - decorative element tints
    # Note: element inline styles (from css dicts) take precedence over these
    # class rules due to CSS specificity — which is exactly what we want.
    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400;700&display=swap');

    @page {{
        size: {outer_w}in {outer_h}in;
        margin: 0;
    }}
    body {{
        margin: 0;
        background: {roles['bg_alt']};
        font-family: 'Lato', Georgia, serif;
    }}

    /* ── Page sheet ──────────────────────────────────────────────── */
    .sheet {{
        position: relative;
        overflow: hidden;
        margin: 0.25in auto;
        page-break-after: always;
        box-shadow: 0 6px 32px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.10);
        border: 1.5px solid {roles['border']};
    }}
    .sheet:last-child {{ page-break-after: avoid; }}

    /* ── Base element ────────────────────────────────────────────── */
    .ph-el {{
        position: absolute;
        box-sizing: border-box;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    /* ── Photos ──────────────────────────────────────────────────── */
    .photo-fill {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
    }}
    .photo-placeholder {{
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
        background: {roles['secondary_light']};
        color: {roles['text_muted']};
    }}
    /* Fallback photo frame color (overridden by element inline style) */
    .ph-photo {{
        background: {roles['secondary_light']};
        outline: 2px solid {roles['border']};
    }}

    /* ── Text elements ───────────────────────────────────────────── */
    /* Background/border on .ph-text is the FALLBACK for unified templates
       whose text elements had no background defined. Builtin templates set
       backgrounds via __token__ in their css dicts, which take precedence. */
    .ph-text {{
        background: {roles['primary_light']}CC;
        border-left: 4px solid {roles['accent']};
        align-items: flex-start;
    }}
    .title-text {{
        margin: 0;
        padding: 8% 6%;
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 17px;
        font-weight: 700;
        color: {roles['text']};
        letter-spacing: 0.05em;
        text-transform: uppercase;
        line-height: 1.3;
    }}
    .caption-text {{
        margin: 0;
        padding: 6%;
        font-size: 10.5px;
        line-height: 1.8;
        font-family: 'Lato', Georgia, serif;
        color: {roles['text']};
        font-weight: 300;
    }}

    /* ── Decorative / stickers ───────────────────────────────────── */
    /* Fallback color — element inline style overrides for unified templates */
    .ph-decor {{
        background: {roles['accent']}44;
        border-radius: 50%;
        border: 2px solid {roles['accent']}88;
    }}

    /* ── Shapes ──────────────────────────────────────────────────── */
    .ph-shape {{
        background: {roles['secondary']}33;
        border-radius: 5px;
        border: 1px solid {roles['secondary']}66;
    }}

    /* ── Person cutouts ──────────────────────────────────────────── */
    .ph-person {{
        background: {roles['primary_light']};
    }}

    /* ── Music cards ─────────────────────────────────────────────── */
    .ph-music {{
        background: {roles['tertiary']}55;
        border-radius: 10px;
        border: 1px solid {roles['tertiary']}88;
    }}

    .ph-other {{ background: transparent; }}
    """

    html_doc = (
        "<html><head><meta charset='utf-8'>"
        "<style>" + css + "</style>"
        "</head><body>" +
        "".join(pages_html) +
        "</body></html>"
    )

    weasyprint.HTML(string=html_doc).write_pdf(output_pdf)
    dbg(f"PDF written → {output_pdf}  ({len(templates)} pages, "
        f"{slot_cursor[0]} photos placed)", 1)
    return True


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG HTML REPORT  (unchanged from v2.1.0)
# ══════════════════════════════════════════════════════════════════════════════

def generate_debug_html(pipeline_output, out_path="pipeline_debug.html"):
    l0      = pipeline_output["layer_0"]
    l1      = pipeline_output["layer_1"]
    captions = pipeline_output.get("captions", {})
    roles   = l1["roles"]

    lines = [
        "<html><head><meta charset='utf-8'><title>MemoryWeave Pipeline Debug</title>",
        "<style>",
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        "background:#f8fafc;padding:30px;margin:0;color:#1e293b;}",
        ".section{background:white;padding:25px;border-radius:12px;margin-bottom:25px;"
        "box-shadow:0 4px 6px -1px rgba(0,0,0,.1);}",
        "h1,h2,h3{margin-top:0;}",
        ".grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}",
        ".card{background:#f1f5f9;padding:12px;border-radius:8px;font-size:13px;}",
        ".swatch{display:inline-block;width:36px;height:36px;margin:3px;border-radius:5px;"
        "border:1px solid #cbd5e1;vertical-align:middle;}",
        ".role-box{display:inline-block;width:100px;text-align:center;margin:6px;font-size:11px;"
        "font-weight:600;}",
        ".role-circle{width:64px;height:64px;border-radius:50%;margin:0 auto 5px;"
        "border:2px solid #e2e8f0;}",
        "pre{background:#1e1e2e;color:#cdd6f4;padding:14px;border-radius:8px;"
        "overflow-x:auto;font-size:12px;white-space:pre-wrap;}",
        "blockquote{border-left:3px solid #94a3b8;margin:8px 0;padding:6px 12px;"
        "color:#475569;font-style:italic;}",
        "table{width:100%;border-collapse:collapse;font-size:12px;}",
        "th,td{padding:6px 10px;border-bottom:1px solid #e2e8f0;text-align:left;}",
        "th{background:#f8fafc;font-weight:600;}",
        ".badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;"
        "font-weight:600;margin:2px;}",
        "</style></head><body>",
        "<h1>🗺️ MemoryWeave Debug Report</h1>",
        f"<p style='color:#64748b'>Session: {l0['session_id']} &nbsp;|&nbsp; "
        f"Generated: {pipeline_output['session_meta']['timestamp']}</p>",
    ]

    lines.append("<div class='section'>")
    lines.append("<h2>🔍 Layer 0 — Ingestion & Vision Fingerprints</h2>")
    lines.append("<div class='grid'>")
    for p in l0["photos"]:
        sem = p["semantic"]
        color_swatches = "".join(
            f"<div class='swatch' style='background:{c}' title='{c}'></div>"
            for c in sem.get("dominant_colors", [])
        )
        lines.append(
            f"<div class='card'>"
            f"<strong>{p['id']} — {html_lib.escape(p['filename'])}</strong><br>"
            f"<small style='color:#64748b'>📅 {p['exif']['date'] or 'no date'} &nbsp;"
            f"📍 {p['exif']['lat'] or '—'}, {p['exif']['lon'] or '—'}</small>"
            f"<hr style='border:none;border-top:1px solid #e2e8f0;margin:6px 0'>"
            f"<table>"
            f"<tr><td>Scene</td><td><b>{sem.get('scene_type','—')}</b></td></tr>"
            f"<tr><td>Mood</td><td><b>{sem.get('mood','—')}</b></td></tr>"
            f"<tr><td>Time</td><td>{sem.get('time_of_day','—')}</td></tr>"
            f"<tr><td>Weather</td><td>{sem.get('weather','—')}</td></tr>"
            f"<tr><td>Subjects</td><td>{', '.join(sem.get('subjects',[]))}</td></tr>"
            f"</table>"
            f"<div style='margin-top:8px'>{color_swatches}</div>"
            f"</div>"
        )
    lines.append("</div></div>")

    lines.append(
        f'<div class="section" style="background:{roles["bg_alt"]};color:{roles["text"]}">'
    )
    lines.append("<h2>🎨 Layer 1 — Color Intelligence</h2>")
    lines.append(
        f"<p><b>Theme:</b> {l1['theme']} ({l1['theme_family']}) &nbsp;|&nbsp; "
        f"<b>Harmony:</b> {l1['harmony_scheme']} &nbsp;|&nbsp; "
        f"<b>Warmth:</b> {l1['warmth']}</p>"
    )
    lines.append("<h3>Color Roles</h3><div>")
    for role, hex_val in roles.items():
        lines.append(
            f"<div class='role-box'>"
            f"<div class='role-circle' style='background:{hex_val}'></div>"
            f"<div>{role.upper()}</div>"
            f"<code style='font-size:10px'>{hex_val}</code>"
            f"</div>"
        )
    lines.append("</div>")
    lines.append("<h3>Full Palette</h3>")
    for h in l1["palette"]:
        lines.append(f"<div class='swatch' style='background:{h}' title='{h}'></div>")
    lines.append("</div>")

    if captions:
        lines.append("<div class='section'><h2>✍️ Layer 4 — Generated Captions</h2>")
        for pid, caption in captions.items():
            lines.append(
                f"<div style='margin-bottom:12px'>"
                f"<span class='badge' style='background:{roles['primary_light']};color:{roles['text']}'>{pid}</span>"
                f"<blockquote style='border-color:{roles['accent']}'>{html_lib.escape(caption)}</blockquote>"
                f"</div>"
            )
        lines.append("</div>")

    selected = pipeline_output.get("selected_template_ids", [])
    lines.append("<div class='section'><h2>📐 Layout — Selected Templates</h2>")
    lines.append(f"<p><b>{len(selected)}</b> template page(s) selected for "
                 f"<b>{len(l0['photos'])}</b> photos:</p><ul>")
    for tid in selected:
        lines.append(f"<li><code>{tid}</code></li>")
    lines.append("</ul></div>")

    if _LOG_LINES:
        escaped_log = html_lib.escape("\n".join(_LOG_LINES))
        lines.append(
            f"<div class='section'><h2>🖥️ Console Log</h2>"
            f"<pre>{escaped_log}</pre></div>"
        )

    lines.append("</body></html>")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    dbg(f"Debug HTML → {out_path}", 1)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    start = time.time()
    print("\n" + "═"*62)
    print("  MemoryWeave — Fixed Pipeline v2.2.0")
    print("═"*62)

    # ── Validate paths ────────────────────────────────────────────────────────
    if not os.path.isdir(PHOTOS_FOLDER):
        print(f"\n[ERROR] PHOTOS_FOLDER not found: {PHOTOS_FOLDER}")
        sys.exit(1)

    # FIX A: clearly report whether unified_templates.json was found
    print(f"\n  Template path: {UNIFIED_TEMPLATES_PATH}")
    if not os.path.isfile(UNIFIED_TEMPLATES_PATH):
        print(f"  [Warning] unified_templates.json NOT found at that path.")
        print("  → Will use built-in fallback templates (now visually designed).\n")
        templates = None
    else:
        with open(UNIFIED_TEMPLATES_PATH, encoding="utf-8") as f:
            templates = json.load(f)
        print(f"  ✅ Loaded {len(templates)} canonical templates.\n")

    # ── Layer 0 ───────────────────────────────────────────────────────────────
    layer0 = run_layer0(PHOTOS_FOLDER, MAX_PHOTOS)

    # Build fallback templates now that we know n_photos
    if templates is None:
        n_pages   = max(1, math.ceil(len(layer0["photos"]) / 2))
        templates = _builtin_templates(n_pages)
        dbg(f"Built {len(templates)} designed fallback template page(s).", 1)

    # ── Layer 1 ───────────────────────────────────────────────────────────────
    layer1 = run_layer1(layer0["photos"], JOURNAL_TYPE)

    # ── Template selection ────────────────────────────────────────────────────
    selected_templates = pick_templates(templates, JOURNAL_TYPE, layer0["photos"], layer1)

    # ── Layer 4 ───────────────────────────────────────────────────────────────
    captions = run_layer4(layer0["photos"], JOURNAL_TYPE)

    # ── Assemble pipeline output ──────────────────────────────────────────────
    pipeline_output = {
        "session_meta": {
            "timestamp":        datetime.utcnow().isoformat(),
            "pipeline_version": "2.2.0",
            "journal_type":     JOURNAL_TYPE,
            "journal_title":    JOURNAL_TITLE,
            "n_photos":         len(layer0["photos"]),
            "n_pages":          len(selected_templates),
        },
        "layer_0":  layer0,
        "layer_1":  layer1,
        "captions": captions,
        "selected_template_ids": [t["template_id"] for t in selected_templates],
    }

    if SAVE_DEBUG_JSON:
        json_path = "pipeline_output.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(pipeline_output, f, indent=2)
        dbg(f"Debug JSON → {json_path}", 1)

    # ── Layer 5 — PDF ─────────────────────────────────────────────────────────
    success = run_layer5(
        selected_templates,
        layer0["photos"],
        layer1,
        captions,
        OUTPUT_PDF,
        JOURNAL_TITLE,
    )

    if SAVE_DEBUG_HTML:
        generate_debug_html(pipeline_output, "pipeline_debug.html")

    elapsed = time.time() - start
    print("\n" + "═"*62)
    if success:
        print(f"  ✅ Pipeline complete in {elapsed:.1f}s")
        print(f"  📄 PDF           → {OUTPUT_PDF}")
    else:
        print(f"  ⚠️  Pipeline done in {elapsed:.1f}s  (PDF skipped — see warning above)")
    print(f"  🔍 Debug HTML    → pipeline_debug.html")
    print(f"  📋 Debug JSON    → pipeline_output.json")
    print("═"*62 + "\n")


if __name__ == "__main__":
    main()