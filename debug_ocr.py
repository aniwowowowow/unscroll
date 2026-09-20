"""
Debug script: shows the RAW text Tesseract reads from your screenshots,
before any parsing logic is applied.
"""

import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TOTAL_SCREENSHOT_PATH = "test_images/total_example.png"
APPS_SCREENSHOT_PATH = "test_images/apps_example.png"

print("=" * 50)
print("TOTAL SCREENSHOT - raw OCR text:")
print("=" * 50)
image = Image.open(TOTAL_SCREENSHOT_PATH)
print(pytesseract.image_to_string(image))

print("=" * 50)
print("APPS SCREENSHOT - raw OCR text:")
print("=" * 50)
image2 = Image.open(APPS_SCREENSHOT_PATH)
print(pytesseract.image_to_string(image2))