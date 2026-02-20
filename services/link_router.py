"""
Link Router — detects URL types and routes them to the appropriate service.

To add a new service (e.g., YouTube, Google Drive):
    1. Add a new LinkType enum value.
    2. Add classification logic in classify_url().
    3. Create a new service class in services/.
    4. Wire it into main.py's _process_urls().
"""

import re
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# Matches any http/https URL in text
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"')\]]+",
    re.IGNORECASE,
)

DIRECT_FILE_EXTENSIONS = frozenset({
    ".mp4", ".mkv", ".avi", ".mov", ".webm",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp3", ".wav", ".flac", ".ogg",
    ".apk", ".exe", ".dmg",
    ".csv", ".json", ".xml",
})


class LinkType(Enum):
    """Supported link types — extend this enum for new services."""
    DIRECT = "direct"
    UNKNOWN = "unknown"
    # Future: YOUTUBE = "youtube"
    # Future: GDRIVE  = "gdrive"


def extract_urls(text: str) -> list[str]:
    """Extract all http/https URLs from arbitrary text."""
    raw = URL_PATTERN.findall(text)
    cleaned: list[str] = []
    for url in raw:
        url = url.rstrip(".,;:!?)")
        if url and len(url) > 10:
            cleaned.append(url)
    logger.info(f"Extracted {len(cleaned)} URL(s) from input text")
    return cleaned


def classify_url(url: str) -> LinkType:
    """Classify a single URL into a LinkType."""
    path_lower = url.lower().split("?")[0]
    for ext in DIRECT_FILE_EXTENSIONS:
        if path_lower.endswith(ext):
            return LinkType.DIRECT

    # Default: attempt direct download for unknown URLs
    return LinkType.DIRECT


def route_urls(urls: list[str]) -> list[tuple[str, LinkType]]:
    """Classify every URL and return (url, type) pairs."""
    routed = []
    for url in urls:
        link_type = classify_url(url)
        routed.append((url, link_type))
        logger.debug(f"Classified {url} → {link_type.value}")
    return routed
