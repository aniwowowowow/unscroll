"""
Wraps boto3 S3 operations used by the app: uploading a screenshot, and
generating a temporary signed URL to view one later (since the bucket
blocks all public access, we can't just link to objects directly).
"""

import os
import uuid
from datetime import datetime

import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# boto3 automatically picks up AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
# from the environment (loaded above via dotenv), so we don't need to
# pass them explicitly here.
s3_client = boto3.client("s3", region_name=AWS_REGION)


def upload_screenshot(file_bytes: bytes, user_id: str, screenshot_type: str) -> str:
    """
    Uploads a screenshot to S3 and returns the S3 object key (not a public
    URL, since the bucket is private -- use get_screenshot_url() later to
    view it).

    screenshot_type should be "total" or "apps", matching which of the
    two daily screenshots this is.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    unique_id = uuid.uuid4().hex[:8]
    key = f"screenshots/{user_id}/{today}_{screenshot_type}_{unique_id}.png"

    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType="image/png",
    )

    return key


def get_screenshot_url(object_key: str, expires_in_seconds: int = 300) -> str | None:
    """
    Generates a temporary signed URL that allows viewing a private S3
    object for a limited time (default 5 minutes). Returns None if the
    object no longer exists (e.g. it's past the 7-day lifecycle expiry).
    """
    try:
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=object_key)
    except s3_client.exceptions.ClientError:
        return None  # object doesn't exist (likely expired)

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": object_key},
        ExpiresIn=expires_in_seconds,
    )
    return url