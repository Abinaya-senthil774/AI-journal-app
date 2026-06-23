# AI-journal-app
**An AI-powered Memory Operating System that transforms unstructured travel experiences into personalized, emotionally-aware visual stories.**

MemoryWeave is a multi-modal AI pipeline that takes raw travel photos and minimal user context and outputs a beautifully designed, emotionally intelligent PDF journal — complete with iterative editing, personalization memory, and social-sharing outputs.

It is built as a **layered generative AI system**, where each design component (color, layout, decoration, text, timeline) is independently regenerable via NLP-classified edit intent — so a user can change "the doodles" or "the tone of the text" without regenerating the entire journal.

---

## Table of Contents

- [Competitor Gap We Fill](#competitor-gap-we-fill)
- [App Features](#app-features)
- [Patent Ideas](#patent-ideas)
- [Making it Unique in Market](#making-it-unique-in-market)
- [Architectural Overview](#architectural-overview)
- [Research Phase](#research-phase)
- [Deployment Plan](#deployment-plan)
  - [Phase 2: Instant Backbone Deployment](#phase-2-instant-backbone-deployment)
  - [Phase 3: Detailed Step-by-Step Deployment](#phase-3-detailed-step-by-step-deployment)
- [The Layers](#the-layers)
  - [Layer 0 — Ingestion & Pre-processing](#layer-0--ingestion-and-pre-processing)
  - [Layer 1 — Color Intelligence Layer](#layer-1--color-intelligence-layer)
  - [Layer 2 — Layout Intelligence Layer](#layer-2--layout-intelligence-layer)
  - [Layer 3 — Decorative Element Layer](#layer-3--decorative-element-layer)
  - [Layer 4 — Story Generation Layer](#layer-4--story-generation-layer)
  - [Layer 5 — Timeline Engine Layer](#layer-5--timeline-engine-layer)
- [Requirements & Logic](#requirements--logic)
- [Tech Stack](#tech-stack)

---

## Competitor Gap We Fill

| Competitor | Gap |
|---|---|
| **Day One / Journey** | No AI-generated journaling; relies on manual entry and organization. |
| **Canva** | Generic design templates; lacks photo-story understanding and narrative generation. |
| **Google Photos Memories** | Creates memory highlights but does not generate journal entries, reflections, or stories. |
| **Notion AI** | Strong text generation capabilities but lacks visual layout intelligence and photo integration. |
| **Polarsteps** | Focused on travel maps and trip tracking; lacks narrative AI, emotional storytelling, and PDF journal generation. |
| **MemoryWeave** | Fully automated multimodal travel journal platform that transforms photos, locations, and memories into personalized stories, reflections, social-ready content, and beautifully designed journal layouts using layered AI and targeted editing. |

---

## App Features

**Novelty:** A layered, keyword-mapped generative canvas where each AI layer is independently queryable and re-runnable, enabling precise, targeted editing without regenerating the whole journal.

### Overview — Multimodal, State-Tracking Generative UI Pipeline

- **Isolated Layer Dependency Graph for Generative UI** — Standard LLMs struggle with spatial reasoning. The novelty here is converting a prompt into an isolated, mutable JSON state-tree where layers can be re-run independently without breaking adjacent layout vectors.
- **Legacy Journal Style Cloning (Anisotropic Transfer)** — Gives users the ability to upload old handwritten journals. Vision-LLMs extract not just text, but the analog layout aesthetic.
- **Aesthetic Cohesion Engine via Color Theorem** — Instead of arbitrary color generation, an algorithmic constraint layer governs palette choices.

---
## Making it Unique in Market

### Tech Angle

1. **Multimodal AI** — combines vision + text + generative image (extremely hot in 2024–2026).
2. **Agentic AI workflow** — each layer is an AI agent with defined inputs/outputs.
3. **RAG for personalization** — user history keywords used as retrieval context for new journals.
4. **Human-in-the-loop design AI** — user iterates with AI, not just accepts output.
5. **Edge AI potential** — Layer 1 and Layer 3 can run on-device (roadmap item).

### Market Angle

1. **Emotional Intelligence** — journals feel personal because the AI understands photo mood, not just content.
2. **Surgical Editability** — users change ONE thing; the rest is preserved (no "regenerate everything" frustration).
3. **Narrative Authorship** — the app positions the user as the author, AI as the assistant (important for emotional ownership).

---
## Architectural Overview

### Overall Plan

```
Step 1: User Uploads
Step 2: Photo Understanding Engine
Step 3: Emotion & Intent Understanding Engine
Step 4: Layout Recommendation Engine
Step 5: Decorative Asset Generation Engine
Step 6: Story Generation Engine
Step 7: Journal Assembly Engine
Step 8: Feedback Learning Engine
Step 9: PDF + Social Content Export
```

### Pipeline Diagram

```
User Input (Photos + Meta + Preferences)
        │
        ▼
INGESTION & PARSING LAYER          ← Pre-processing: EXIF, NLP on text
        │
        ▼
LAYERED GENERATION ENGINE
  Layer 1: Color & Theme Resolver
  Layer 2: Layout Composer (Photo + Text Zones)
  Layer 3: Decorative Element Generator
  Layer 4: Text & Caption AI
  Layer 5: Timeline Stitcher & Finalizer
        │
        ▼
KEYWORD-MAPPED CANVAS DB           ← Stores layout decisions as keyword graphs
        │
        ▼
VARIATION ENGINE (3 outputs)       ← Generates 3 structurally different outputs
        │
        ▼
PDF RENDERER                       ← ReportLab / Puppeteer / WeasyPrint
        │
        ▼
ITERATION & EDIT ENGINE            ← NLP → Layer Router → Re-run only dirty layers
```

---

## Research Phase

**For the AI** — understanding photos, computer vision topics:
- CLIP, BLIP, Florence 2, GPT Vision, Image Captioning, Scene Recognition

**For understanding text** — NLP topics:
- Sentence Transformers, BERT, DistilBERT, Emotion Detection

**For recommendation systems:**
- Collaborative filtering, content-based recommendation

### Research Segments

**Segment 1: Computational Creativity in Document Design**
- LayoutGAN: Generating Graphic Layouts with Wireframe Discriminators (Li et al., 2019)
- Canvasformer: Autoregressive Modeling for Layout Generation (2023)
- CLAY: Learning to Denoise Text-Conditioned Layout Generation (2023)

**Segment 2: Multimodal Emotion Understanding**
- Sentiment Analysis of Visual Content — IEEE
- EmotionCLIP: Grounding Image Emotions (2023)
- Datasets: EmoSet, SentiBank

**Segment 3: Color Psychology in UX**
- Color and Emotion — Johansson et al.
- Adobe Color Theory documentation
- itten.de — Johannes Itten's color theory foundations

**Segment 4: Personal Narrative Generation**
- Automated Diary Generation from Lifelog Data — ACM Multimedia
- StoryBrush: Telling Visual Stories with Location Data — CHI 2022

**Segment 5: PDF/Document Generation**
- WeasyPrint docs: weasyprint.org
- ReportLab user guide: reportlab.com/documentation

---

## Deployment Plan

### Phase 2: Instant Backbone Deployment

| Days | Task |
|---|---|
| Day 1–2 | Set up GitHub repo, write README with architecture diagram |
| Day 3–4 | Build EXIF extractor + Claude Vision API call → get JSON fingerprint for 5 test photos |
| Day 5–7 | Build color palette extractor (colorthief + colormath harmonizer) |
| Day 8–10 | Write 5 base layout templates in JSON format, render to HTML |
| Day 11–12 | Generate first WeasyPrint PDF with hardcoded data |
| Day 13–14 | Connect the pipeline end-to-end (photos → fingerprint → palette → layout → PDF) |

### Phase 3: Detailed Step-by-Step Deployment

**Phase 0: Research & Foundation (Month 1–2)**
- Deep dive research on layout generation papers (LayoutGAN, CLAY)
- Study multimodal LLM APIs (Claude Vision, GPT-4V)
- Prototype EXIF extraction + reverse geocoding pipeline
- Set up development environment (Docker, FastAPI, Next.js)
- File Provisional Patent Application
- Define 20 base layout templates (Figma)
- Curate initial SVG decoration library (100 elements)

**Phase 1: Core ML Pipeline (Month 3–4)**
- Build Layer 0: Ingestion + EXIF + Vision AI fingerprinting
- Build Layer 1: Color resolver + palette harmonizer
- Build Layer 2: Layout manifest generator (rule-based + LLM)
- Build Layer 3: SVG decoration selector (tag-matching system)
- Test pipeline end-to-end with 20 sample photo sets

**Phase 2: Text & PDF Generation (Month 5–6)**
- Build Layer 4: LLM caption & text generator
- Build Layer 5: PDF renderer (WeasyPrint)
- Implement timestamp + user text direct-paste flow
- Generate first full end-to-end journal PDF
- User testing with 10 beta users

**Phase 3: Variation Engine & Canvas DB (Month 7–8)**
- Implement Keyword-Mapped Canvas DB (Redis + PostgreSQL)
- Build 3-variant generation with structural blocking
- Implement NLP edit-intent classifier (emotion-to-layer router)
- Build edit iteration flow ("not satisfied? describe changes")
- User preference history system + scoring

**Phase 4: Frontend & UX (Month 9–10)**
- Build full Next.js frontend
- Photo upload flow with drag-and-drop
- 3-variant preview carousel
- PDF download + social sharing export
- User dashboard with journaling insights

**Phase 5: Personalization & Scale (Month 11–12)**
- Train/fine-tune DistilBERT emotion classifier on journal data
- Stable Diffusion integration for custom decorations
- Add social-ready export formats (Instagram, Stories)
- Performance optimization (caching, async generation)
- Load testing + deployment
- Launch MVP on Product Hunt

---

## The Layers

### Layer 0 — Ingestion and Pre-processing

Reads every input signal before any generation begins.

**Inputs:**
- Photos → EXIF metadata (GPS coords, timestamp, camera model)
- User text inputs (timestamps, captions, free-form descriptions)
- Journal type selection (Gratitude / Reflective / Goal / Creative / Travel)
- Checkbox: timestamps enabled
- "Describe what you want" free-text
- Uploaded prior journals (image format)

**Implementation:**

1. **EXIF Extraction**
   - Library: `Pillow` (Python) or `exifread`
   - Extract: `GPS IFD`, `DateTimeOriginal`, `Make`, `Model`
   - Reverse geocode GPS → human-readable location via `geopy` + `Nominatim` (free) or Google Maps Geocoding API

2. **Image Understanding (Vision AI)**
   - Use Claude (claude-sonnet-4-6) Vision API (or GPT-4 Vision / Google Gemini Vision)
   - Prompt template:
     ```
     Analyze this travel photo. Return JSON with:
     - dominant_colors: [hex list]
     - scene_type: (beach/mountain/city/forest/food/people/landmark)
     - mood: (joyful/peaceful/adventurous/nostalgic/energetic)
     - subjects: [list of main subjects]
     - time_of_day: (morning/afternoon/evening/night)
     - weather: (sunny/cloudy/rainy/snowy)
     - composition_notes: (landscape/portrait/close-up/wide-shot)
     ```
   - This JSON becomes the image **semantic fingerprint**, stored per photo.

3. **Prior Journal OCR** (if uploaded)
   - Use `pytesseract` or `EasyOCR` for handwritten/printed text extraction
   - Extract writing style cues → feed into Layer 4 text generation

4. **NLP on "Describe what you want"**
   - Use `spaCy` + custom NER to extract:
     - Color preferences → Layer 1
     - Layout preferences → Layer 2
     - Mood/emotion cues → Layers 3 & 4
     - Decoration preferences → Layer 3
   - Sentiment analysis: `VADER` or `transformers (DistilBERT)`

**Output (Layer 0 data structure):**

```json
{
  "session_id": "uuid",
  "photos": [
    {
      "id": "p1",
      "path": "...",
      "exif": { "date": "2024-12-10", "lat": 13.08, "lon": 80.27 },
      "location_name": "Marina Beach, Chennai",
      "semantic": {
        "dominant_colors": ["#F4A261", "#E76F51", "#2A9D8F"],
        "scene_type": "beach",
        "mood": "joyful",
        "time_of_day": "evening"
      }
    }
  ],
  "user_intent": {
    "journal_type": "travel",
    "timestamps_enabled": true,
    "description_parsed": {
      "color_pref": null,
      "mood_pref": "warm and nostalgic",
      "layout_pref": "minimalist",
      "decoration_pref": "botanical elements"
    }
  }
}
```

---

### Layer 1 — Color Intelligence Layer

Produces a coherent color palette for the journal.

- **Input:** photos, theme, description
- **Analyze:** dominant colors, mood, theme
- **Use:** ColorThief, OpenCV, K-Means clustering
- **Extract:** warm, cold, vintage, earthy, pastel

**Logic flow:**

```
IF user explicitly named colors in description
  → Use those colors directly (bypass AI)
ELSE
  → Extract dominant colors from ALL photos (weighted average)
  → Map to journal_type theme family:
      Travel     → warm earth tones, azure blues
      Gratitude  → soft lavenders, warm yellows
      Reflective → muted grays, deep teals
      Goal       → sharp blues, greens
      Creative   → vibrant multicolor
  → Harmonize using color theory rules (60-30-10 rule)
  → Output: primary, secondary, accent, background, text colors
```

**Implementation:**

- **Step 1:** When images are uploaded, run a K-Means Clustering algorithm via OpenCV/Python on the image batch to extract the top 5 dominant colors. `colorthief` extracts top colors per image; `colormath` converts to Lab color space for perceptual harmony calculation.
- **Step 2:** If the user selects "Travel Journaling" but their photos are dominated by deep ocean blues and sandy beiges, the engine automatically selects an Analogous or Split-Complementary palette based on those hex codes. A custom palette harmonizer applies Adobe's color harmony rules (complementary, analogous, triadic).

**Output:**
```
{ primary: "#hex", secondary: "#hex", accent: "#hex", bg: "#hex", text: "#hex" }
{"layer_1": {"palette": ["#0A2342", "#2A6F97", "#A9D6E5"], "theme": "Travel"}}
```

---

### Layer 2 — Layout Intelligence Layer

Decides **where** photos and text blocks go on each page.

- **Input:** Photo count, aspect ratio, theme, mood
- **Output:** Templates A, B, C
- **Easy version:** JSON templates → React Konva, FabricJS
- **Advanced version:** Layout Transformer → LayoutLM, Canva AI layout papers

**Logic:**

- For first-time users: default layout templates per `journal_type`
  - Gratitude → soft single-column with wide margins
  - Travel → dynamic multi-column, photo-forward
  - Creative → asymmetric freeform grids
- For returning users — **AI Scoring System:** generate 5 layout variations and score them. First-time users get a cold-start heuristic based on journal type (e.g., Reflective gets higher text-to-image spatial ratios; Creative gets overlapping/asymmetric layouts). Returning users get their historical favorite template vectors retrieved from a Vector Database (ChromaDB / Pinecone), ranked via cosine similarity to the top 3 templates.
  - Load history keywords: `{ "travel_minimalist_2col": 0.87, "travel_grid_fullbleed": 0.43 }`
  - Score candidate layouts against historical preference vector
  - Select top 3 layouts (for the 3-variant output)

**Implementation:**

Do not rely on raw LLMs to guess X/Y coordinates. Use a **Constraint-Based Grid Engine** (CSS Grid principles converted to PDF coordinate space).

| Option | Technology | Pros | Cons |
|---|---|---|---|
| A. Rule-based Template Engine | Jinja2 + CSS Grid specs | Predictable, fast, easy to maintain | Less layout variety/creativity |
| B. ML Layout Predictor | Small CNN on journal image datasets | Learns from user feedback, adaptive | Requires training data + maintenance |
| C. LLM Layout Planner | GPT/Claude generates layout JSON | Flexible, creative, customizable | Slower, higher API cost |
| **D. Hybrid (Recommended)** | Rule-based structure + LLM for micro-decisions | Combines consistency with creativity, balanced | Medium implementation complexity |

**Recommended approach (D):**
- Maintain 20–30 base layout templates as JSON specs
- LLM adjusts: photo sizing ratios, text-to-photo balance, column decisions

**Output (Layout Manifest JSON):**

```json
{
  "pages": [
    {
      "page_num": 1,
      "layout_type": "hero_single",
      "zones": [
        { "type": "photo", "photo_id": "p1", "position": { "x": 0, "y": 0, "w": 100, "h": 60 }, "unit": "%" },
        { "type": "title_text", "position": { "x": 10, "y": 62, "w": 80, "h": 10 } },
        { "type": "body_text", "position": { "x": 10, "y": 74, "w": 80, "h": 20 } }
      ]
    }
  ]
}
```

---

### Layer 3 — Decorative Element Layer

Adds small artistic elements — botanical drawings, icons, borders, stamps, doodles — that match journal type, location, and mood.

**Generate:** Travel stickers, maps, vintage stamps, doodles, ticket stubs, polaroid frames.

**Element categories:**
- Location-based: palm trees (beach), mountains (trekking), Eiffel Tower silhouette (Paris)
- Journal-type: compass rose (travel), heart (gratitude), target (goal)
- Mood-based: sun rays (joyful), soft waves (peaceful), scattered leaves (nostalgic)
- Date-based: season indicators (winter snowflake, summer sun)

**Logic:** If the metadata reads "Paris, France" and the theme is "Gratitude", the prompt engine synthesizes a minimalist, line-art vector of the Eiffel Tower or a small coffee cup doodle.

**Output:** Small PNG assets with absolute coordinate placements:
```json
{"layer_3": {"decorations": [{"asset_id": "doodle_01", "x": 120, "y": 450}]}}
```

**Implementation options:**

1. **SVG Icon Library** — Curate 200+ SVG illustrations tagged by location, mood, season, journal_type. Resources: `undraw.co`, `storyset.com`, custom Figma set.
2. **Text-to-Image Generation** — Stable Diffusion (local, via `diffusers`) with a style LoRA fine-tuned on watercolor/sketch journal art. Prompt example: *"small watercolor sketch of a coconut palm tree, journal decoration, transparent background, minimal"*. Size: 150×150px thumbnails only.
3. **Hybrid (Recommended)** — SVG library for standard elements + Stable Diffusion for custom user-requested art (from "describe what you want").

Decoration placement is decided by Layer 3 and written to the Keyword Canvas DB.

**Tools:** Stable Diffusion, FLUX, DALL·E, SDXL
**Store:** dictionaries

---

### Layer 4 — Story Generation Layer

Fills all text zones — titles, captions, body paragraphs, timestamps — with meaningful, emotionally resonant content.

**Input:** location, date, photos, theme, user notes

**Logic:**

```
FOR each text zone in Layout Manifest:
  IF user provided direct text for this zone:
    → Insert verbatim (no AI intervention)
  ELSE:
    → Construct generation prompt from:
        - Photo semantic fingerprint (scene, mood, subjects)
        - Location name (reverse geocoded)
        - Date / time of day
        - Journal type
        - User's emotional tone from "describe what you want"
    → Generate text via LLM (Claude / GPT)
    → Apply journal-type voice:
        Travel     → vivid storytelling, sensory language
        Gratitude  → warm, appreciative, introspective
        Reflective → thoughtful, question-posing
        Goal       → structured, achievement-focused
        Creative   → playful, experimental
```

**Sample caption-generation prompt:**

```
You are writing a personal travel journal entry.
Photo context: A sunset at Marina Beach, Chennai. Subjects: waves, silhouettes
of people, orange sky. Mood: nostalgic, peaceful. Time: evening.
Journal type: Travel Journaling.
User emotional tone: "warm and nostalgic".
Write a 2-3 sentence journal caption in first person. Be vivid and personal.
No clichés.
```

**NLP Emotion Mapping for edit requests:**
- "make it more poetic" → temperature increase + style vector shift
- BERT fine-tuned on emotion classification classifies edit intent:
  - Tone change → re-run Layer 4 only
  - Layout change → re-run Layer 2 only
  - Color change → re-run Layer 1 only

**Models:** GPT, Claude, Gemini, Llama 3

---

### Layer 5 — Timeline Engine Layer

Assembles all layers into the final PDF pages. Groups photos by time, location, weather, and emotion.

**Implementation:**

1. **Page Assembly Engine**
   - Takes Layout Manifest + color palette + decoration positions + text content
   - Renders using `ReportLab` (Python), `WeasyPrint` (HTML→PDF), or `Puppeteer` (headless Chrome, HTML→PDF)
   - **Recommended:** WeasyPrint — most design-friendly (CSS-based)

2. **Photo Placement**
   - Mood-based filters (warm tone overlay for nostalgic, high contrast for adventurous)
   - `Pillow` for image processing
   - Rounded corners, shadow effects, polaroid frame option

3. **Timeline Ordering**
   - Sort photos by `DateTimeOriginal` EXIF (primary sort)
   - Group by location clusters (haversine distance < 1km) (secondary grouping)
   - Each cluster = one journal "chapter" / page spread

4. **Three-Variant Output**
   - Generate 3 PDFs with the same content but different:
     - Layout structures (different template families)
     - Typography pairings (Serif/Sans/Handwritten)
     - Decoration density (minimal / balanced / rich)
   - Present as side-by-side thumbnails for user selection

**Keyword-Mapped Canvas Database**

Instead of storing the full journal, store a semantic graph of decisions:

```python
canvas_map = {
    "session_id": "abc123",
    "keywords": {
        "layout": ["hero_single", "2col_photo_text", "full_bleed"],
        "colors": ["warm_earth", "azure", "palette_resonance"],
        "mood": ["nostalgic", "joyful", "adventure"],
        "decorations": ["palm_svg", "compass_rose", "sunset_watercolor"],
        "text_style": ["vivid_storytelling", "first_person", "sensory"],
        "journal_type": "travel",
        "locations": ["marina_beach_chennai", "mahabalipuram"],
        "seasons": ["winter"],
        "time_of_day": ["evening", "morning"]
    },
    "layer_states": {
        "layer1": { "status": "complete", "output_ref": "palette_v1" },
        "layer2": { "status": "complete", "output_ref": "layout_manifest_v1" },
        "layer3": { "status": "complete", "output_ref": "decorations_v1" },
        "layer4": { "status": "complete", "output_ref": "texts_v1" },
        "layer5": { "status": "complete", "output_ref": "pdf_v1" }
    }
}
```

**On edit request:**
1. NLP classifies which layer the edit targets
2. Mark that layer as "dirty"
3. Re-run ONLY that layer with new constraints
4. The Variation Engine ensures the 3 new variants differ structurally (blocking keywords used in previous variants)

**How the layer-targeted "edit" works** — example: *"Can you change the doodles to something more retro and make the text sound less formal?"*

1. An NLP Intent Classifier reads the edit string.
2. It identifies that "retro doodles" modifies Layer 3 and "less formal text" modifies Layer 4.
3. The system locks the states of Layer 1, 2, and 5 (layout, colors, and raw photos stay exactly where they are).
4. It modifies the prompts only for the sub-services handling Layers 3 and 4, swaps out those specific JSON objects, and pushes the updated schema to the frontend canvas re-compiler (using tools like ReportLab or PyMuPDF to instantly bake the new PDF).

---

## Requirements & Logic

### Storage

- **Redis** — fast keyword lookup
- **PostgreSQL** — relational user history
- **S3 / MinIO** — PDFs and images

### State Database Schema

Store each generated journal as a structured document in a NoSQL database (e.g., MongoDB) or a Graph Database (e.g., Neo4j) to map relationships between assets:

```json
{
  "journal_id": "user123_paris_2026",
  "genre": "Travel",
  "keywords": ["beach", "sunset", "architecture", "peaceful"],
  "layers": {
    "layer_1": { "colors": ["#FFF", "#000"] },
    "layer_2": { "layout_matrix": "grid_v2" },
    "layer_3": { "doodles": [] },
    "layer_4": { "text_blocks": [] }
  }
}
```

### Dashboard, Memory Mapping & Journal Regeneration

```json
{
  "theme": "travel",
  "color": "earthy",
  "layout": "polaroid",
  "decor": "minimal",
  "mood": "nostalgic"
}
```

- Use vector embeddings, stored in Pinecone, Chroma, or Weaviate
- User history becomes: *Travel, Vintage, Earth Tones, Reflective Writing*

**Trending Insights Dashboard Concept:** Instead of just a list of past journals, show an "Emotional & Aesthetic Footprint Analytics" board, e.g.:
- *"Your Travel Sentiment over the last 3 months has leaned 70% towards 'Gratitude' and peace."*
- *"Your favorite visual aesthetic this season is Pastel Minimalist with dominant warm earthy tones."*

---

## Tech Stack

### Backend

| Component | Technology |
|---|---|
| API Framework | FastAPI (Python) |
| Task Queue | Celery + Redis |
| Image Processing | Pillow, OpenCV |
| Metadata Extraction | EXIFRead, Pillow |
| Optical Character Recognition (OCR) | EasyOCR |
| Natural Language Processing (NLP) | spaCy, Hugging Face Transformers |
| Emotion Classification | Fine-tuned DistilBERT |
| Large Language Model (LLM) | Claude API (Anthropic) |
| AI Image Generation | Stable Diffusion (Diffusers) |
| Color Analysis & Processing | ColorThief, ColorMath |
| PDF Generation | WeasyPrint / ReportLab |
| Reverse Geocoding | GeoPy + Nominatim |

### Frontend

| Component | Technology |
|---|---|
| Framework | Next.js (React) |
| Styling | Tailwind CSS |
| PDF Preview & Rendering | React-PDF |
| File Upload Management | React-Dropzone |
| State Management | Zustand / Redux Toolkit |
| Animations & Interactions | Framer Motion |

### Infrastructure & Deployment

| Component | Technology |
|---|---|
| Database | PostgreSQL |
| Cache Layer | Redis |
| File Storage | AWS S3 / Cloudflare R2 |
| Deployment Platform | Docker + AWS ECS / Railway |
| Authentication | Supabase Auth / Auth0 |
| Monitoring & Error Tracking | Sentry + Datadog |

### Summary

| Layer | Technologies |
|---|---|
| Frontend | Next.js, Tailwind CSS, React-PDF, Framer Motion |
| Backend | FastAPI, Celery, Redis, OpenCV, EasyOCR, spaCy |
| AI/ML | Claude API, DistilBERT, Stable Diffusion, Hugging Face |
| Data Storage | PostgreSQL, AWS S3 / Cloudflare R2 |
| Deployment | Docker, AWS ECS, Railway |
| Monitoring | Sentry, Datadog |
