"""
Layer 2 - Layout Intelligence Layer
Day 8-10 deliverable: render JSON layout templates to HTML so you can eyeball them in a browser.

Your 5 uploaded files actually contain 23 templates total, split across TWO different
JSON schemas (see the chat explanation for why). This script detects which schema each
template uses and renders both the same way: one HTML file per template, plus an
index.html that links to all of them.

Usage:
    Edit INPUT_FOLDER / OUTPUT_FOLDER below, then run:
    python render_templates.py

Setup:
    No extra installs needed - uses only the Python standard library.
"""

import os
import json
import re

# ---- EDIT THESE FOR YOUR SETUP ----
INPUT_FOLDER = r"D:\\Research\\AI_memory_app\\instant deployement\\journal_templates"      # folder containing Template N.json files
OUTPUT_FOLDER = r"D:\\Research\\AI_memory_app\\instant deployement\\output"   # where the generated HTML files will go
DISPLAY_WIDTH_PX = 480                  # how wide each rendered preview canvas is on screen
# ------------------------------------

PHOTO_TYPES = {"photo", "photo_frame", "image_placeholder", "polaroid", "torn_photo",
               "photo_group", "film_strip"}
TEXT_TYPES = {"paragraph", "text", "text_area", "text_label", "title", "subtitle"}
DECOR_TYPES = {"sticker", "doodle", "doodle_placeholder", "icon", "vector_graphic",
                "graphic_element", "ui_element"}
PERSON_TYPES = {"person_cutout"}
GROUP_TYPES = {"composite_group"}
MUSIC_TYPES = {"music_card", "song_cover"}
SHAPE_TYPES = {"shape"}

ANCHOR_RULES = {
    "top_center": {"top": "-6%", "left": "50%", "transform": "translateX(-50%)"},
    "bottom_center": {"bottom": "-6%", "left": "50%", "transform": "translateX(-50%)"},
    "top_right": {"top": "-6%", "right": "-6%"},
    "top_left": {"top": "-6%", "left": "-6%"},
    "bottom_right": {"bottom": "-6%", "right": "-6%"},
    "bottom_left": {"bottom": "-6%", "left": "-6%"},
}

CSS = """
body { font-family: -apple-system, Helvetica, sans-serif; background:#f1efe9; margin:0;
       padding:32px; display:flex; flex-direction:column; align-items:center; }
h1 { font-size: 16px; color:#333; margin: 0 0 4px; }
.meta { font-size: 12px; color:#888; margin-bottom: 16px; }
.canvas { position:relative; background:#fff; box-shadow:0 6px 24px rgba(0,0,0,0.18); overflow:hidden; }
.ph-el { position:absolute; box-sizing:border-box; display:flex; align-items:center;
         justify-content:center; text-align:center; overflow:hidden; }
.ph-label { font-size:10px; color:#444; padding:2px; line-height:1.2; }
.ph-photo  { background: repeating-linear-gradient(45deg,#d9d9d9,#d9d9d9 8px,#c8c8c8 8px,#c8c8c8 16px); border:2px solid #999; }
.ph-text   { background: rgba(255,255,255,0.65); border:1px dashed #8b6f47; }
.ph-decor  { background:#ffd9ec; border-radius:50%; color:#5a2d44; font-size:9px; }
.ph-person { background:#cfe8d8; border:2px dashed #4a8a63; }
.ph-group  { background:transparent; border:2px dotted #999; }
.ph-music  { background:#cdd6f6; border:1px solid #5566aa; }
.ph-shape  { background:#fff3c4; border:1px solid #c9a227; }
.ph-other  { background:#eee; border:1px solid #bbb; }
"""


def classify(type_name):
    t = (type_name or "").lower()
    if t in PHOTO_TYPES:
        return "photo"
    if t in TEXT_TYPES:
        return "text"
    if t in DECOR_TYPES:
        return "decor"
    if t in PERSON_TYPES:
        return "person"
    if t in GROUP_TYPES:
        return "group"
    if t in MUSIC_TYPES:
        return "music"
    if t in SHAPE_TYPES:
        return "shape"
    return "other"


def camel_to_kebab(key): # convert camelCase to kebab-case for CSS property names
    return re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower() # insert hyphen before capital letters, then lowercase


def style_dict_to_css(style): # convert a camelCase style dict to a CSS string
    if not style or not isinstance(style, dict):
        return ""
    return " ".join(f"{camel_to_kebab(k)}: {v};" for k, v in style.items())


def pct(value, fallback="10%"): # convert a numeric value to a percentage string, or return it as-is if it already ends with '%'
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        return f"{value}%"
    value = str(value)
    return value if value.endswith("%") else f"{value}%"


# ---------- Schema A: Template 1.json / Template 2.json style ----------
# Flat "layout" list, numeric x/y/width/height (% implied), camelCase "style" dict.

def render_element_a(item):
    style_css = style_dict_to_css(item.get("style"))
    rotation = item.get("rotation", 0) or 0
    transform = f"transform: rotate({rotation}deg);" if rotation else ""
    box_css = (
        f"left:{pct(item.get('x'))}; top:{pct(item.get('y'))}; "
        f"width:{pct(item.get('width'))}; height:{pct(item.get('height'))}; "
        f"z-index:{item.get('zIndex', 1)}; {transform} {style_css}"
    )
    cls = classify(item.get("type"))
    label = item.get("slot") or item.get("id") or item.get("type") or "?"
    return (f'<div class="ph-el ph-{cls}" style="{box_css}" title="{item.get("type")}">'
            f'<span class="ph-label">{label}</span></div>')


def get_template_meta_a(template):
    canvas = template.get("canvas", {}) or {}
    w, h = canvas.get("width", 1080), canvas.get("height", 1350)
    bg = ((template.get("background") or {}).get("default") or {}).get("color", "#FFFFFF")
    name = template.get("templateName") or template.get("templateId") or "Untitled"
    tid = template.get("templateId", re.sub(r"\W+", "_", name.lower()))
    elements_html = "".join(render_element_a(it) for it in template.get("layout", []))
    return tid, name, w, h, bg, elements_html


# ---------- Schema B: Template 3/4/5.json style ----------
# "layout_elements" list, coordinates as percentage strings, optional nested
# inner_elements (positioned relative to their parent) and decorations (anchor-positioned).

def render_decoration_b(deco):
    anchor = deco.get("position") or "top_right"
    rules = dict(ANCHOR_RULES.get(anchor, ANCHOR_RULES["top_right"]))
    transform_parts = []
    if "transform" in rules:
        transform_parts.append(rules.pop("transform"))
    rotation = deco.get("rotation")
    if rotation:
        transform_parts.append(f"rotate({rotation})")
    transform_css = f"transform: {' '.join(transform_parts)};" if transform_parts else ""
    pos_css = "; ".join(f"{k}:{v}" for k, v in rules.items())
    color = deco.get("color", "#333")
    label = (deco.get("type") or "deco").replace("_", " ")
    return (f'<div class="ph-el ph-decor" style="position:absolute; {pos_css}; '
            f'{transform_css} background:{color}; z-index:{deco.get("zIndex", 9)};">{label}</div>')


def render_inner_element_b(inner):
    coords = inner.get("coordinates", {}) or {}
    label = inner.get("text_content") or inner.get("label") or inner.get("id") or "?"
    extra = ""
    color = inner.get("color")
    if color and "image" in (inner.get("type") or ""):
        extra = f"background-color:{color};"
    box_css = (
        f"position:absolute; left:{pct(coords.get('left'))}; top:{pct(coords.get('top'))}; "
        f"width:{pct(coords.get('width'), 'auto')}; height:{pct(coords.get('height'), 'auto')}; {extra}"
    )
    cls = classify(inner.get("type"))
    return f'<div class="ph-el ph-{cls}" style="{box_css}" title="{inner.get("type")}"><span class="ph-label">{label}</span></div>'


def render_element_b(item):
    coords = item.get("coordinates", {}) or {}
    cls = classify(item.get("type"))
    extra = ""
    if item.get("frame_color"):
        extra += f"background-color:{item['frame_color']};"
    box_css = (
        f"left:{pct(coords.get('left'))}; top:{pct(coords.get('top'))}; "
        f"width:{pct(coords.get('width'))}; height:{pct(coords.get('height'))}; "
        f"z-index:{item.get('zIndex', 1)}; {extra}"
    )
    label = item.get("placeholder_text") or item.get("id") or item.get("type") or "?"
    children = "".join(render_inner_element_b(i) for i in (item.get("inner_elements") or []))
    children += "".join(render_decoration_b(d) for d in (item.get("decorations") or []))
    return (f'<div class="ph-el ph-{cls}" style="{box_css}" title="{item.get("type")}">'
            f'<span class="ph-label">{label}</span>{children}</div>')


def get_template_meta_b(template):
    canvas = template.get("canvas", {}) or {}
    w = canvas.get("width_px", 1200)
    h = canvas.get("height_px", 1600)
    bg = (template.get("background") or {}).get("color", "#FFFFFF")
    name = template.get("name") or template.get("id") or "Untitled"
    tid = template.get("id", re.sub(r"\W+", "_", name.lower()))
    elements_html = "".join(render_element_b(it) for it in template.get("layout_elements", []))
    return tid, name, w, h, bg, elements_html


# ---------- Shared rendering ----------

def render_template_html(template, schema, source_file, category):
    if schema == "A":
        tid, name, w, h, bg, elements_html = get_template_meta_a(template)
    else:
        tid, name, w, h, bg, elements_html = get_template_meta_b(template)

    display_height = round(DISPLAY_WIDTH_PX * (h / w))

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{name}</title><style>{CSS}</style></head>
<body>
  <h1>{name}</h1>
  <div class="meta">{category} &middot; source: {source_file} &middot; schema {schema} &middot; {w}x{h}</div>
  <div class="canvas" style="width:{DISPLAY_WIDTH_PX}px; height:{display_height}px; background:{bg};">
    {elements_html}
  </div>
</body></html>"""
    return tid, name, html


def detect_schema(template):
    if "layout" in template:
        return "A"
    if "layout_elements" in template:
        return "B"
    return None


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    index_entries = []

    json_files = sorted(f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith(".json"))
    if not json_files:
        raise SystemExit(f"No .json files found in {INPUT_FOLDER}")

    for filename in json_files:
        path = os.path.join(INPUT_FOLDER, filename)
        with open(path) as f:
            data = json.load(f)

        templates = data.get("templates", [])
        meta = data.get("metadata") or data.get("file_reference") or {}
        collection = meta.get("collection") if isinstance(meta, dict) else str(meta)

        for template in templates:
            schema = detect_schema(template)
            if schema is None:
                print(f"  Skipping an item in {filename}: no recognizable layout key")
                continue

            category = template.get("category") or collection or "Uncategorized"
            tid, name, html = render_template_html(template, schema, filename, category)

            out_name = f"{os.path.splitext(filename)[0].replace(' ', '_')}__{tid}.html"
            with open(os.path.join(OUTPUT_FOLDER, out_name), "w") as f:
                f.write(html)

            index_entries.append((filename, schema, category, name, out_name))
            print(f"  Rendered: {filename} -> {out_name}  ({name})")

    index_html = ["<!doctype html><html><head><meta charset='utf-8'>",
                  "<title>Template Gallery</title>",
                  "<style>body{font-family:-apple-system,sans-serif;max-width:800px;margin:40px auto;}",
                  "table{width:100%;border-collapse:collapse;} td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left;}",
                  "a{color:#2A6F97;text-decoration:none;} a:hover{text-decoration:underline;}</style></head><body>",
                  f"<h1>{len(index_entries)} templates rendered</h1><table>",
                  "<tr><th>#</th><th>Name</th><th>Category</th><th>Schema</th><th>Source file</th></tr>"]
    for i, (src, schema, category, name, out_name) in enumerate(index_entries, start=1):
        index_html.append(
            f"<tr><td>{i}</td><td><a href='{out_name}'>{name}</a></td>"
            f"<td>{category}</td><td>{schema}</td><td>{src}</td></tr>"
        )
    index_html.append("</table></body></html>")

    with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w") as f:
        f.write("\n".join(index_html))

    print(f"\nDone. {len(index_entries)} templates rendered to {OUTPUT_FOLDER}/")
    print(f"Open {OUTPUT_FOLDER}/index.html in a browser to review all of them.")


if __name__ == "__main__":
    main()
