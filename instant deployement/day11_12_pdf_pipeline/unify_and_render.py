"""
Layer 2 - Layout Intelligence Layer
Follow-up to Day 8-10: collapse both JSON schemas into ONE canonical shape,
resolve the Template 1 / Template 2 overlap, and re-render from the canonical
shape to prove nothing visually changed.

Decisions baked in (the "easy fix" discussed in chat):
  1. Template 2.json is treated as canonical for the 4 templates it shares
     with Template 1.json (it's the superset - same 4 plus 5 new pet templates).
  2. The one template where they'd actually diverged (mw_portrait_02_music_heavy)
     has its Template-1-only version preserved separately in an "archived"
     file, NOT deleted - so nothing is silently lost.
  3. Every template, regardless of which raw schema it came from, is converted
     into one shared shape: { x, y, w, h, rotation, z_index, css, children }.
     Downstream code (Layer 4, Layer 5) only ever needs to learn this one shape.

Usage:
    Edit INPUT_FOLDER / OUTPUT_FOLDER below, then run:
    python unify_and_render.py

Setup:
    No extra installs needed - uses only the Python standard library.
"""

import os
import json
import re

# ---- EDIT THESE FOR YOUR SETUP ----
INPUT_FOLDER = "journal_templates"
OUTPUT_FOLDER = "unified_output"
DISPLAY_WIDTH_PX = 480
DEFAULT_SIZE_PCT = 10.0   # fallback box size when a source element has no width/height
DECO_SIZE_PCT = 12.0      # default size for anchor-positioned decorations (washi tape etc.)
# ------------------------------------

PHOTO_TYPES = {"photo", "photo_frame", "image_placeholder", "polaroid", "torn_photo",
               "photo_group", "film_strip"}
TEXT_TYPES = {"paragraph", "text", "text_area", "text_label", "title", "subtitle"}
DECOR_TYPES = {"sticker", "doodle", "doodle_placeholder", "icon", "vector_graphic",
                "graphic_element", "ui_element", "heart_icon", "washi_tape"}
PERSON_TYPES = {"person_cutout"}
GROUP_TYPES = {"composite_group"}
MUSIC_TYPES = {"music_card", "song_cover"}
SHAPE_TYPES = {"shape"}

# Anchor keywords resolved to plain x/y percentages once, here - so nothing
# downstream ever has to know "top_center" / "bottom_right" exist as concepts.
def resolve_anchor(anchor, size=DECO_SIZE_PCT):
    half = size / 2
    table = {
        "top_center":    (50 - half, -half),
        "bottom_center": (50 - half, 100 - half),
        "top_right":     (100 - half, -half),
        "top_left":      (-half, -half),
        "bottom_right":  (100 - half, 100 - half),
        "bottom_left":   (-half, 100 - half),
    }
    return table.get(anchor, table["top_right"])


def classify(type_name):
    t = (type_name or "").lower()
    if t in PHOTO_TYPES: return "photo"
    if t in TEXT_TYPES: return "text"
    if t in DECOR_TYPES: return "decor"
    if t in PERSON_TYPES: return "person"
    if t in GROUP_TYPES: return "group"
    if t in MUSIC_TYPES: return "music"
    if t in SHAPE_TYPES: return "shape"
    return "other"


def camel_to_kebab(key):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", key).lower()


def slugify(name):
    return re.sub(r"\W+", "_", name.lower()).strip("_")


def parse_deg(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    v = str(value).strip().lower().replace("deg", "").strip()
    try:
        return float(v)
    except ValueError:
        return 0.0


def pct_num(value, default):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    v = str(value).strip().rstrip("%")
    try:
        return float(v)
    except ValueError:
        return default


# ---------- Converting Schema A (Template 1/2 style) into the canonical shape ----------

def canon_element_a(item):
    style = item.get("style") or {}
    css = {camel_to_kebab(k): v for k, v in style.items()}
    return {
        "id": item.get("id"),
        "type": item.get("type"),
        "slot": item.get("slot"),
        "text": None,
        "x": pct_num(item.get("x"), 0), "y": pct_num(item.get("y"), 0),
        "w": pct_num(item.get("width"), DEFAULT_SIZE_PCT),
        "h": pct_num(item.get("height"), DEFAULT_SIZE_PCT),
        "rotation": parse_deg(item.get("rotation")),
        "z_index": item.get("zIndex", 1),
        "css": css,
        "style_preset": None,
        "children": [],
    }


def canon_template_a(template, source_file):
    canvas = template.get("canvas", {}) or {}
    w, h = canvas.get("width", 1080), canvas.get("height", 1350)
    bg = ((template.get("background") or {}).get("default") or {}).get("color", "#FFFFFF")
    name = template.get("templateName") or template.get("templateId") or "Untitled"
    return {
        "template_id": template.get("templateId") or slugify(name),
        "name": name,
        "category": template.get("category") or "Uncategorized",
        "source_file": source_file,
        "canvas": {"width_px": w, "height_px": h},
        "background_color": bg,
        "elements": [canon_element_a(it) for it in template.get("layout", [])],
    }


# ---------- Converting Schema B (Template 3/4/5 style) into the canonical shape ----------

def canon_inner_b(inner):
    coords = inner.get("coordinates") or {}
    css = {}
    if inner.get("color") and "image" in (inner.get("type") or ""):
        css["background-color"] = inner["color"]
    return {
        "id": inner.get("id"), "type": inner.get("type"), "slot": None,
        "text": inner.get("text_content") or inner.get("label"),
        "x": pct_num(coords.get("left"), 0), "y": pct_num(coords.get("top"), 0),
        "w": pct_num(coords.get("width"), DEFAULT_SIZE_PCT),
        "h": pct_num(coords.get("height"), DEFAULT_SIZE_PCT),
        "rotation": 0.0, "z_index": 1, "css": css, "style_preset": None, "children": [],
    }


def canon_decoration_b(deco):
    anchor = deco.get("position") or "top_right"
    x, y = resolve_anchor(anchor)
    return {
        "id": f"deco_{anchor}", "type": deco.get("type"), "slot": None, "text": None,
        "x": x, "y": y, "w": DECO_SIZE_PCT, "h": DECO_SIZE_PCT,
        "rotation": parse_deg(deco.get("rotation")),
        "z_index": deco.get("zIndex", 9),
        "css": {"background-color": deco.get("color", "#333")},
        "style_preset": None, "children": [],
    }


def canon_element_b(item):
    coords = item.get("coordinates") or {}
    css = {}
    if item.get("frame_color"):
        css["background-color"] = item["frame_color"]
    children = [canon_inner_b(i) for i in (item.get("inner_elements") or [])]
    children += [canon_decoration_b(d) for d in (item.get("decorations") or [])]
    style = item.get("style")
    return {
        "id": item.get("id"), "type": item.get("type"), "slot": None,
        "text": item.get("placeholder_text"),
        "x": pct_num(coords.get("left"), 0), "y": pct_num(coords.get("top"), 0),
        "w": pct_num(coords.get("width"), DEFAULT_SIZE_PCT),
        "h": pct_num(coords.get("height"), DEFAULT_SIZE_PCT),
        "rotation": 0.0, "z_index": item.get("zIndex", 1), "css": css,
        "style_preset": style if isinstance(style, str) else None,
        "children": children,
    }


def canon_template_b(template, source_file, category):
    canvas = template.get("canvas", {}) or {}
    w, h = canvas.get("width_px", 1200), canvas.get("height_px", 1600)
    bg = (template.get("background") or {}).get("color", "#FFFFFF")
    name = template.get("name") or template.get("id") or "Untitled"
    return {
        "template_id": template.get("id") or slugify(name),
        "name": name,
        "category": category or "Uncategorized",
        "source_file": source_file,
        "canvas": {"width_px": w, "height_px": h},
        "background_color": bg,
        "elements": [canon_element_b(it) for it in template.get("layout_elements", [])],
    }


# ---------- Step 1: build the canonical set, applying the dedup decision ----------

def build_canonical_set():
    t1_path = os.path.join(INPUT_FOLDER, "Template 1.json")
    t2_path = os.path.join(INPUT_FOLDER, "Template 2.json")

    with open(t1_path) as f:
        t1_raw = {t["templateId"]: t for t in json.load(f)["templates"]}
    with open(t2_path) as f:
        t2_raw = {t["templateId"]: t for t in json.load(f)["templates"]}

    canonical = []
    archived = []

    # Template 2 is canonical for everything it contains (it's the superset).
    for tid, t in t2_raw.items():
        canonical.append(canon_template_a(t, "Template 2.json"))

    # Anything in Template 1 that ISN'T in Template 2 would be unique - keep it active too.
    for tid, t in t1_raw.items():
        if tid not in t2_raw:
            canonical.append(canon_template_a(t, "Template 1.json"))

    # Anything that exists in BOTH but with different content: don't lose it,
    # archive Template 1's version separately for manual comparison.
    for tid in set(t1_raw) & set(t2_raw):
        if t1_raw[tid] != t2_raw[tid]:
            archived_version = canon_template_a(t1_raw[tid], "Template 1.json (ARCHIVED - diverged from Template 2.json)")
            archived_version["template_id"] += "__archived_v1"
            archived.append(archived_version)

    # Template 3/4/5 only have one schema each - convert directly, no dedup needed.
    for filename in ["Template 3.json", "Template 4.json", "Template 5.json"]:
        path = os.path.join(INPUT_FOLDER, filename)
        with open(path) as f:
            data = json.load(f)
        category = data.get("file_reference")
        for t in data["templates"]:
            canonical.append(canon_template_b(t, filename, category))

    return canonical, archived


# ---------- Step 2: ONE render path for the canonical shape (no more branching) ----------

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


def render_element(el):
    css = "; ".join(f"{k}: {v}" for k, v in el.get("css", {}).items())
    transform = f"transform: rotate({el['rotation']}deg);" if el.get("rotation") else ""
    box = (f"left:{el['x']}%; top:{el['y']}%; width:{el['w']}%; height:{el['h']}%; "
           f"z-index:{el.get('z_index', 1)}; {transform} {css}")
    cls = classify(el.get("type"))
    label = el.get("text") or el.get("slot") or el.get("id") or el.get("type") or "?"
    children_html = "".join(render_element(c) for c in el.get("children", []))
    return (f'<div class="ph-el ph-{cls}" style="{box}" title="{el.get("type")}">'
            f'<span class="ph-label">{label}</span>{children_html}</div>')


def render_template(t):
    w, h = t["canvas"]["width_px"], t["canvas"]["height_px"]
    display_height = round(DISPLAY_WIDTH_PX * (h / w))
    elements_html = "".join(render_element(el) for el in t["elements"])
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{t['name']}</title><style>{CSS}</style></head>
<body>
  <h1>{t['name']}</h1>
  <div class="meta">{t['category']} &middot; source: {t['source_file']} &middot; canonical schema &middot; {w}x{h}</div>
  <div class="canvas" style="width:{DISPLAY_WIDTH_PX}px; height:{display_height}px; background:{t['background_color']};">
    {elements_html}
  </div>
</body></html>"""
    return html


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    render_dir = os.path.join(OUTPUT_FOLDER, "rendered")
    os.makedirs(render_dir, exist_ok=True)

    canonical, archived = build_canonical_set()

    with open(os.path.join(OUTPUT_FOLDER, "unified_templates.json"), "w") as f:
        json.dump(canonical, f, indent=2)
    with open(os.path.join(OUTPUT_FOLDER, "archived_diverged_templates.json"), "w") as f:
        json.dump(archived, f, indent=2)

    index_rows = []
    for t in canonical:
        out_name = f"{t['source_file'].split('.')[0].replace(' ', '_')}__{t['template_id']}.html"
        with open(os.path.join(render_dir, out_name), "w") as f:
            f.write(render_template(t))
        index_rows.append((t["name"], t["category"], t["source_file"], out_name))

    index_html = ["<!doctype html><html><head><meta charset='utf-8'><title>Unified Template Gallery</title>",
                  "<style>body{font-family:-apple-system,sans-serif;max-width:800px;margin:40px auto;}",
                  "table{width:100%;border-collapse:collapse;} td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left;}",
                  "a{color:#2A6F97;text-decoration:none;} a:hover{text-decoration:underline;}</style></head><body>",
                  f"<h1>{len(canonical)} canonical templates ({len(archived)} archived separately)</h1><table>",
                  "<tr><th>#</th><th>Name</th><th>Category</th><th>Source</th></tr>"]
    for i, (name, category, src, out_name) in enumerate(index_rows, start=1):
        index_html.append(f"<tr><td>{i}</td><td><a href='rendered/{out_name}'>{name}</a></td>"
                           f"<td>{category}</td><td>{src}</td></tr>")
    index_html.append("</table></body></html>")
    with open(os.path.join(OUTPUT_FOLDER, "index.html"), "w") as f:
        f.write("\n".join(index_html))

    print(f"Canonical templates: {len(canonical)}")
    print(f"Archived (diverged) templates: {len(archived)}")
    print(f"Wrote {OUTPUT_FOLDER}/unified_templates.json")
    print(f"Wrote {OUTPUT_FOLDER}/archived_diverged_templates.json")
    print(f"Rendered previews in {OUTPUT_FOLDER}/rendered/  ->  open {OUTPUT_FOLDER}/index.html")


if __name__ == "__main__":
    main()
