"""
File Utilities
- Filename sanitization (path-traversal safe)
- Temp-directory management
- Extension helpers
"""

import re
import shutil
import logging
from pathlib import Path

from config import TEMP_DIR, VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """
    Make a filename safe for local storage:
    - Strip path separators and null bytes
    - Remove leading dots/spaces
    - Replace reserved characters
    - Truncate to 200 chars
    """
    name = name.replace("/", "_").replace("\\", "_").replace("\x00", "")
    name = name.lstrip(". ")
    name = re.sub(r'[<>:"|?*]', "_", name)

    if len(name) > 200:
        stem = Path(name).stem[:180]
        ext = Path(name).suffix
        name = stem + ext

    return name or "unnamed_file"


def get_temp_dir(session_id: str) -> Path:
    """Create and return a per-session temp directory."""
    path = TEMP_DIR / session_id
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Temp dir ready: {path}")
    return path


def cleanup_temp_dir(session_id: str) -> None:
    """Remove the entire session temp directory tree."""
    path = TEMP_DIR / session_id
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
        logger.info(f"Cleaned temp dir: {path}")
    except Exception as exc:
        logger.error(f"Cleanup failed for {path}: {exc}")


def get_file_extension(name: str) -> str:
    return Path(name).suffix.lower()


def is_video_file(name: str) -> bool:
    return get_file_extension(name) in VIDEO_EXTENSIONS
