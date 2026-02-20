"""
Async Streaming Downloader
- Chunked writes (never holds entire file in RAM)
- Configurable retries with exponential back-off
- Timeout protection
- Max-size guard (both header check + streaming check)
- Progress callback support
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Awaitable
from urllib.parse import urlparse, unquote

import aiohttp

from config import CHUNK_SIZE, MAX_FILE_SIZE, MAX_RETRIES, DOWNLOAD_TIMEOUT
from utils.file_utils import sanitize_filename

logger = logging.getLogger(__name__)

# Type alias for the progress callback
ProgressCallback = Callable[[int, int], Awaitable[None]]


async def download_file(
    url: str,
    dest_dir: Path,
    progress_callback: Optional[ProgressCallback] = None,
    max_size: int = MAX_FILE_SIZE,
    retries: int = MAX_RETRIES,
    timeout: int = DOWNLOAD_TIMEOUT,
) -> Optional[Path]:
    """
    Download a file with retries. Returns the local Path on success, None on failure.
    """
    filename = _extract_filename(url)
    dest_path = dest_dir / filename

    # Avoid name collisions inside the same session directory
    counter = 1
    original_stem = dest_path.stem
    while dest_path.exists():
        dest_path = dest_dir / f"{original_stem}_{counter}{dest_path.suffix}"
        counter += 1

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"[{attempt}/{retries}] Downloading {url}")
            result = await _stream_download(url, dest_path, progress_callback, max_size, timeout)
            if result:
                size = result.stat().st_size
                logger.info(f"Downloaded {filename} ({size:,} bytes)")
                return result
        except asyncio.TimeoutError:
            logger.warning(f"[{attempt}/{retries}] Timeout for {url}")
        except aiohttp.ClientError as exc:
            logger.warning(f"[{attempt}/{retries}] Client error for {url}: {exc}")
        except Exception as exc:
            logger.error(f"[{attempt}/{retries}] Unexpected error for {url}: {exc}", exc_info=True)

        # Exponential back-off before next retry
        if attempt < retries:
            delay = 2 ** attempt
            logger.info(f"Retrying in {delay}s…")
            await asyncio.sleep(delay)

    logger.error(f"All {retries} attempts failed for {url}")
    # Clean partial file
    dest_path.unlink(missing_ok=True)
    return None


# ─── Internal ──────────────────────────────────────────────

async def _stream_download(
    url: str,
    dest_path: Path,
    progress_callback: Optional[ProgressCallback],
    max_size: int,
    timeout: int,
) -> Optional[Path]:
    """Low-level streamed download."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.get(url, allow_redirects=True) as resp:
            if resp.status != 200:
                logger.error(f"HTTP {resp.status} for {url}")
                return None

            content_length = int(resp.headers.get("Content-Length", 0))

            # Pre-flight size check
            if content_length and content_length > max_size:
                logger.error(
                    f"File too large ({content_length:,} B > {max_size:,} B)"
                )
                return None

            downloaded = 0

            with open(dest_path, "wb") as fp:
                async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                    downloaded += len(chunk)

                    if downloaded > max_size:
                        logger.error("Max size exceeded during streaming")
                        dest_path.unlink(missing_ok=True)
                        return None

                    fp.write(chunk)

                    if progress_callback:
                        await progress_callback(downloaded, content_length)

    return dest_path


def _extract_filename(url: str) -> str:
    """Derive a safe filename from a URL."""
    parsed = urlparse(url)
    raw_name = Path(unquote(parsed.path)).name

    if not raw_name or raw_name == "/":
        raw_name = "downloaded_file"

    return sanitize_filename(raw_name)
