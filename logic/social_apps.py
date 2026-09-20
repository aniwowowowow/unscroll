"""
Fixed list of app names that count as "social media" for the purposes of
summing social_minutes from a top-apps screenshot breakdown.

Matching is done case-insensitively and via substring match (so
"Instagram" matches whether OCR reads it as "Instagram", "instagram",
or even slightly mangled text that still contains this substring).

Edit this list any time to add/remove apps -- no other code changes
needed elsewhere.
"""

SOCIAL_APPS = [
    "instagram",
    "tiktok",
    "youtube",
    "snapchat",
    "facebook",
    "twitter",
    "reddit",
    "discord",
    "telegram",
    "pinterest",
]


def is_social_app(app_name: str) -> bool:
    """
    Returns True if the given app name (as read from OCR) matches one of
    the known social apps.
    """
    normalized = app_name.strip().lower()
    return any(social_app in normalized for social_app in SOCIAL_APPS)