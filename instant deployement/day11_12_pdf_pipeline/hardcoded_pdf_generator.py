"""
Layer 5 - first PDF render (hardcoded data, no live AI pipeline yet)
Day 11-12 deliverable: take canonical layout templates + hardcoded photos/captions
and render a real, multi-page PDF through WeasyPrint.

This reads from unified_templates.json (the canonical shape from the unify_and_render.py
step) - so it works the same way regardless of which raw schema a template came from.
Day 13-14 is where these hardcoded PHOTOS/CAPTIONS dicts get replaced by the real
Layer 0/1/3/4 outputs.

Usage:
    Edit the CONFIG block below, then run:
    python hardcoded_pdf_generator.py

Setup:
    pip install weasyprint
"""

import os
import json
import weasyprint
import pathlib  # Added to handle Windows file paths properly for HTML

# ---- EDIT THESE FOR YOUR SETUP ----
UNIFIED_TEMPLATES_PATH = "D:\\Research\\AI_memory_app\\instant deployement\\day11_12_pdf_pipeline\\day11_12_pdf_pipeline\\unified_output\\unified_templates.json"
OUTPUT_PDF = "D:\\Research\\AI_memory_app\\instant deployement\\day11_12_pdf_pipeline\\day11_12_pdf_pipeline\\final_output_instant_deployement.pdf"
PAGE_WIDTH_IN = 6.0   # physical print width per page; height follows each template's own aspect ratio

# Which templates go in this PDF, in page order. Mix sources on purpose here to prove
# the canonical renderer works the same regardless of which raw JSON schema fed it.
TEMPLATE_IDS = ["mw_portrait_06_pet_plate_diary", "mw_portrait_3_page_1"]

# Hardcoded photos for this test run, keyed by element id within each template.
PHOTOS = {
    "p_q1": "instant deployement/day11_12_pdf_pipeline/day11_12_pdf_pipeline/hardcoded_photos/1.jpg",
    "p_q2": "instant deployement/day11_12_pdf_pipeline/day11_12_pdf_pipeline/hardcoded_photos/2.jpeg",
    "p_q3": "instant deployement/day11_12_pdf_pipeline/day11_12_pdf_pipeline/hardcoded_photos/3.jpg",
    "p_q_coll": "instant deployement/day11_12_pdf_pipeline/day11_12_pdf_pipeline/hardcoded_photos/4.jpg",
    "photo_polaroid_top_left": "instant deployement/day11_12_pdf_pipeline/day11_12_pdf_pipeline/hardcoded_photos/5.jpg",
    "photo_polaroid_center_right": "instant deployement/day11_12_pdf_pipeline/day11_12_pdf_pipeline/hardcoded_photos/1.jpg",
    "photo_polaroid_bottom_center": "instant deployement/day11_12_pdf_pipeline/day11_12_pdf_pipeline/hardcoded_photos/2.jpeg",
}

# Hardcoded captions, keyed by element id. Falls back to any text already baked
# into the template JSON (some Schema-B templates ship with placeholder copy).
CAPTIONS = {
    "diary_long_box": ("Biscuit discovered the ocean today and immediately regretted it. "
                        "Three minutes of barking at the waves, then back to napping in the sand."),
}
# ------------------------------------

PHOTO_TYPES = {"photo", "photo_frame", "image_placeholder", "polaroid", "torn_photo",
               "photo_group", "film_strip"}
TEXT_TYPES = {"paragraph", "text", "text_area", "text_label", "title", "subtitle"}
DECOR_TYPES = {"sticker", "doodle", "doodle_placeholder", "icon", "vector_graphic",
                "graphic_element", "ui_element", "heart_icon", "washi_tape"}
PERSON_TYPES = {"person_cutout"}
SHAPE_TYPES = {"shape"}
MUSIC_TYPES = {"music_card", "song_cover"}


def classify(type_name):
    t = (type_name or "").lower()
    if t in PHOTO_TYPES: return "photo"
    if t in TEXT_TYPES: return "text"
    if t in DECOR_TYPES: return "decor"
    if t in PERSON_TYPES: return "person"
    if t in SHAPE_TYPES: return "shape"
    if t in MUSIC_TYPES: return "music"
    return "other"


def render_element(el):
    css = "; ".join(f"{k}: {v}" for k, v in el.get("css", {}).items())
    transform = f"transform: rotate({el['rotation']}deg);" if el.get("rotation") else ""
    box = (f"left:{el['x']}%; top:{el['y']}%; width:{el['w']}%; height:{el['h']}%; "
           f"z-index:{el.get('z_index', 1)}; {transform} {css}")
    cls = classify(el.get("type"))
    children_html = "".join(render_element(c) for c in el.get("children", []))

    if cls == "photo" and el["id"] in PHOTOS:
        # THE FIX: Converts path to a standard file:/// URI format that WeasyPrint understands
        img_uri = pathlib.Path(PHOTOS[el["id"]]).resolve().as_uri()
        inner = f'<img src="{img_uri}" class="photo-fill" />'
    elif cls == "text":
        caption = CAPTIONS.get(el["id"]) or el.get("text") or ""
        inner = f'<p class="caption-text">{caption}</p>' if caption else ""
    else:
        inner = ""

    return f'<div class="ph-el ph-{cls}" style="{box}">{inner}{children_html}</div>'


def render_page(template):
    w, h = template["canvas"]["width_px"], template["canvas"]["height_px"]
    page_height_in = PAGE_WIDTH_IN * (h / w)
    elements_html = "".join(render_element(el) for el in template["elements"])
    return f"""
    <div class="sheet" style="width:{PAGE_WIDTH_IN}in; height:{page_height_in:.3f}in;
                               background:{template['background_color']};">
      {elements_html}
    </div>""", page_height_in


def build_pdf():
    with open(UNIFIED_TEMPLATES_PATH) as f:
        all_templates = json.load(f)
    by_id = {t["template_id"]: t for t in all_templates}

    pages_html = []
    max_height_in = PAGE_WIDTH_IN
    for tid in TEMPLATE_IDS:
        if tid not in by_id:
            raise KeyError(f"Template '{tid}' not found in {UNIFIED_TEMPLATES_PATH}")
        page_html, page_height_in = render_page(by_id[tid])
        pages_html.append(page_html)
        max_height_in = max(max_height_in, page_height_in)

    outer_w = PAGE_WIDTH_IN + 0.5
    outer_h = max_height_in + 0.5

    css = f"""
    @page {{ size: {outer_w}in {outer_h}in; margin: 0; }}
    body {{ margin: 0; }}
    .sheet {{
        position: relative; overflow: hidden; margin: 0.25in auto;
        page-break-after: always;
        box-shadow: 0 0 0 1px rgba(0,0,0,0.08);
    }}
    .sheet:last-child {{ page-break-after: avoid; }}
    .ph-el {{ position: absolute; box-sizing: border-box; overflow: hidden;
              display: flex; align-items: center; justify-content: center; }}
    .photo-fill {{ width: 100%; height: 100%; object-fit: cover; }}
    .caption-text {{ margin: 0; padding: 4%; font-family: Georgia, serif; font-size: 11px;
                      line-height: 1.4; color: #2a2a2a; }}
    .ph-photo  {{ background: #ddd; }}
    .ph-text   {{ background: rgba(255,255,255,0.5); }}
    .ph-decor  {{ border-radius: 50%; }}
    .ph-person {{ background: #cfe8d8; }}
    .ph-shape  {{ background: rgba(255,255,255,0.4); border-radius: 6px; }}
    .ph-music  {{ background: #cdd6f6; }}
    .ph-other  {{ background: transparent; }}
    """

    html = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(pages_html)}</body></html>"

    weasyprint.HTML(string=html).write_pdf(OUTPUT_PDF)
    print(f"Wrote {OUTPUT_PDF} ({len(TEMPLATE_IDS)} pages)")


if __name__ == "__main__":
    build_pdf()