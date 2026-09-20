"""
Debug script: shows the RAW response Gemini returns, before we try to
parse it as JSON.
"""

import os
from google import genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

image = Image.open("test_images/total_example.png")

prompt = (
    "This is a phone screentime summary screenshot. Find the figure "
    "that represents the TOTAL screen time for the day (not a chart "
    "axis label, not an individual app's time, not a notification "
    "count). Respond with ONLY raw JSON, no markdown, no explanation, "
    'in exactly this format: {"total_minutes": <integer or null>, '
    '"confidence": <integer 0-100>}. Convert hours+minutes to total '
    'minutes (e.g. "2h 15m" = 135). If you cannot find a clear total '
    "screen time figure, set total_minutes to null and confidence to 0."
)

try:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[prompt, image],
    )
    print("RAW RESPONSE TEXT:")
    print(repr(response.text))
except Exception as e:
    print("EXCEPTION OCCURRED:")
    print(type(e), e)