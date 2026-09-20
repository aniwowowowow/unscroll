"""
OCR pipeline using the Gemini API (new google-genai SDK), which reads
screenshots with actual visual/contextual understanding rather than
blind character transcription.

Two entry points:
  - extract_total_minutes(image_bytes) -- for the "total screentime" screenshot
  - extract_social_minutes(image_bytes) -- for the "top apps" screenshot

Both return (minutes, confident).
"""

import os
import io
import json

from google import genai
from PIL import Image
from dotenv import load_dotenv

from logic.social_apps import is_social_app

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

CONFIDENCE_THRESHOLD = 60


def _bytes_to_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes))


def _ask_gemini(image: Image.Image, prompt: str) -> dict | None:
    """
    Sends the image + prompt to Gemini, asking for a strict JSON response,
    and parses it. Returns None if the response wasn't valid JSON.
    """
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, image],
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        return json.loads(text)
    except Exception:
        return None


def extract_total_minutes(image_bytes: bytes) -> tuple[int | None, bool]:
    """
    Asks Gemini to identify the total screentime figure shown on the
    screenshot, explicitly ignoring chart axis labels or other unrelated
    numbers. Returns (minutes, confident).
    """
    image = _bytes_to_image(image_bytes)

    prompt = (
        "This is a phone screentime summary screenshot. Find the figure "
        "that represents the TOTAL screen time for the day. The real "
        "total is usually the LARGEST, most prominent number on the "
        "screen, positioned closest to a label like 'Total screen time' "
        "or 'Screen time today'. Do NOT use smaller numbers such as "
        "chart axis/gridline labels (e.g. small '3h' or '8h' marks next "
        "to a bar chart), individual app usage times, or notification "
        "counts -- those are usually smaller and further from the total "
        "label. Respond with ONLY raw JSON, no markdown, no explanation, "
        'in exactly this format: {"total_minutes": <integer or null>, '
        '"confidence": <integer 0-100>}. Convert hours+minutes to total '
        'minutes (e.g. "2h 15m" = 135). If you cannot find a clear, '
        "large, prominent total screen time figure, set total_minutes "
        "to null and confidence to 0."
    )

    result = _ask_gemini(image, prompt)
    if result is None:
        return None, False

    minutes = result.get("total_minutes")
    confidence = result.get("confidence", 0)

    confident = confidence >= CONFIDENCE_THRESHOLD and minutes is not None
    return minutes, confident


def extract_social_minutes(image_bytes: bytes) -> tuple[int | None, bool]:
    """
    Asks Gemini to list every app and its screentime shown on the
    breakdown screenshot, then sums the ones matching our own
    SOCIAL_APPS list.
    """
    image = _bytes_to_image(image_bytes)

    prompt = (
        "This is a phone screentime app breakdown screenshot, showing a "
        "list of apps and how long each was used. Respond with ONLY raw "
        "JSON, no markdown, no explanation, in exactly this format: "
        '{"apps": [{"name": "<app name>", "minutes": <integer>}, ...], '
        '"confidence": <integer 0-100>}. Convert hours+minutes to total '
        'minutes per app (e.g. "1h 5m" = 65). List every app you can see.'
    )

    result = _ask_gemini(image, prompt)
    if result is None:
        return None, False

    apps = result.get("apps", [])
    confidence = result.get("confidence", 0)

    total_social_minutes = 0
    any_match_found = False

    for app in apps:
        name = app.get("name", "")
        minutes = app.get("minutes")
        if minutes is not None and is_social_app(name):
            total_social_minutes += minutes
            any_match_found = True

    if not any_match_found:
        return None, False

    confident = confidence >= CONFIDENCE_THRESHOLD
    return total_social_minutes, confident