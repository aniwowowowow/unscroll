"""
Test the OCR pipeline against real screenshot files on your computer.
"""

from logic.ocr_utils import extract_total_minutes, extract_social_minutes

TOTAL_SCREENSHOT_PATH = "test_images/total_example.png"
APPS_SCREENSHOT_PATH = "test_images/apps_example.png"

with open(TOTAL_SCREENSHOT_PATH, "rb") as f:
    total_bytes = f.read()

with open(APPS_SCREENSHOT_PATH, "rb") as f:
    apps_bytes = f.read()

total_minutes, total_confident = extract_total_minutes(total_bytes)
print(f"Total minutes: {total_minutes} (confident: {total_confident})")

social_minutes, social_confident = extract_social_minutes(apps_bytes)
print(f"Social minutes: {social_minutes} (confident: {social_confident})")