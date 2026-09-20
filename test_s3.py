"""
One-off script to confirm S3 upload and signed-URL retrieval actually
work against the real bucket. Safe to delete once confirmed working.
"""

from aws.s3_client import upload_screenshot, get_screenshot_url

fake_image_bytes = b"this is a test file, not a real screenshot"
test_user_id = "test-user-123"

print("Uploading test file to S3...")
key = upload_screenshot(fake_image_bytes, test_user_id, "total")
print("Uploaded! Object key:", key)

print("\nGenerating a signed URL to view it...")
url = get_screenshot_url(key)
print("Signed URL (valid 5 minutes):", url)

print("\nOpen that URL in your browser -- you should see the raw text download/display.")