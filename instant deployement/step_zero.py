"""
Layer 0 - Ingestion & Pre-processing
Day 3-4 deliverable: EXIF extractor + Gemini Vision API call -> JSON fingerprint

Usage:
    python exif_vision_extractor.py

Setup:
    pip install pillow google-genai python-dotenv
"""

import os
import json
import uuid
import time

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS # for EXIF parsing
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ---------- EXIF EXTRACTION ----------

def get_exif_data(image_path):
    """Pull raw EXIF tags out of a photo using Pillow."""
    image = Image.open(image_path)
    exif_raw = image._getexif()
    if not exif_raw:
        return {}
    exif = {}
    for tag_id, value in exif_raw.items():
        tag = TAGS.get(tag_id, tag_id)
        exif[tag] = value
    return exif


def get_gps_coords(exif):
    """Convert EXIF GPS IFD (degrees/minutes/seconds) into decimal lat/lon."""
    gps_info = exif.get("GPSInfo")
    if not gps_info:
        return None, None

    gps_data = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}

    def to_decimal(dms, ref):
        degrees, minutes, seconds = dms
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal

    lat = lon = None
    if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
        lat = to_decimal(gps_data["GPSLatitude"], gps_data["GPSLatitudeRef"])
    if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
        lon = to_decimal(gps_data["GPSLongitude"], gps_data["GPSLongitudeRef"])
    return lat, lon


def extract_exif_summary(image_path):
    exif = get_exif_data(image_path)
    lat, lon = get_gps_coords(exif)
    date_str = exif.get("DateTimeOriginal") or exif.get("DateTime")
    return {
        "date": date_str,
        "lat": lat,
        "lon": lon,
        "make": exif.get("Make"),
        "model": exif.get("Model"),
    }

# ---------- GEMINI VISION CALL ----------

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
    """Send one photo to Gemini's vision endpoint with automatic retry on 503 errors."""
    img = Image.open(image_path)

    # Output tokens increased to 1024 to prevent the model from cutting off mid-JSON
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        max_output_tokens=1024,
    )

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[img, VISION_PROMPT],
                config=config
            )
            
            # Guard against empty/blocked responses where response.text is None
            if not response or not response.text:
                finish_reason = "Unknown"
                if response and response.candidates and response.candidates[0].finish_reason:
                    finish_reason = response.candidates[0].finish_reason
                raise ValueError(f"Empty response or blocked by safety filters. Finish reason: {finish_reason}")

            raw_text = response.text.strip()
            
            try:
                fingerprint = json.loads(raw_text)
            except json.JSONDecodeError:
                fingerprint = {"error": "Could not parse model output as JSON", "raw": raw_text}
            
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            }
            return fingerprint, usage

        except Exception as e:
            # If the server is overloaded (503), wait and try again
            if "503" in str(e) and attempt < retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"   [Warning] Google servers busy. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            # Catch all other errors gracefully (safety blocks, bad files, 400 errors)
            print(f"   [Error] Failed to process {os.path.basename(image_path)}: {e}")
            fallback_fingerprint = {"error": "Failed during extraction", "details": str(e)}
            fallback_usage = {"input_tokens": 0, "output_tokens": 0}
            return fallback_fingerprint, fallback_usage

# ---------- MAIN PIPELINE ----------

def build_layer0_output(photos_folder):
    # The client will now securely look for GEMINI_API_KEY in the environment
    client = genai.Client()

    supported = (".jpg", ".jpeg", ".png")
    photo_files = [
        f for f in sorted(os.listdir(photos_folder))
        if f.lower().endswith(supported)
    ][:5]  # 5 test photos, per the Day 3-4 plan

    session = {"session_id": str(uuid.uuid4()), "photos": []}
    total_input_tokens = 0
    total_output_tokens = 0

    for i, filename in enumerate(photo_files, start=1):
        path = os.path.join(photos_folder, filename)
        print(f"[{i}/{len(photo_files)}] Processing {filename} ...")

        exif_summary = extract_exif_summary(path)
        fingerprint, usage = get_image_fingerprint(client, path)

        total_input_tokens += usage["input_tokens"]
        total_output_tokens += usage["output_tokens"]

        session["photos"].append({
            "id": f"p{i}",
            "path": path,
            "exif": exif_summary,
            "semantic": fingerprint,
        })

    session["token_usage"] = {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
    }
    return session


if __name__ == "__main__":
    folder = r"D:\Research\AI_memory_app\instant deployement\testphotos"
    
    result = build_layer0_output(folder)

    out_path = "layer0_fingerprint_output.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nDone. Wrote {len(result['photos'])} photo fingerprints to {out_path}")
    print(f"Total tokens used: {result['token_usage']}")