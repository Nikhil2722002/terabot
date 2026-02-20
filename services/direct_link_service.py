"""
Direct Link Service — orchestrates downloading, optional zipping, and
returning the final file path for a batch of direct-download URLs.
"""

import uuid
import logging
from pathlib import Path
from typing import Optional

from telegram import Message

from config import PROGRESS_UPDATE_INTERVAL
from utils.downloader import download_file
from utils.zipper import create_zip
from utils.progress import ProgressTracker
from utils.file_utils import get_temp_dir, cleanup_temp_dir

logger = logging.getLogger(__name__)


class DirectLinkService:
    """
    Adapter for direct (CDN) file downloads.

    Usage:
        service = DirectLinkService()
        result  = await service.process(urls, status_message, chat_id)
        # result is (file_path, session_id) or None
    """

    async def process(
        self,
        urls: list[str],
        status_message: Message,
        chat_id: int,
    ) -> Optional[tuple[Path, str]]:
        """
        Download every URL, zip if multiple, return (path, session_id).
        Returns None when nothing was downloaded.
        """
        session_id = uuid.uuid4().hex[:8]
        temp_dir = get_temp_dir(session_id)
        downloaded: list[Path] = []

        try:
            for idx, url in enumerate(urls, 1):
                short_name = url.rsplit("/", 1)[-1].split("?")[0][:50] or "file"

                await self._safe_edit(
                    status_message,
                    f"📥 Downloading file {idx}/{len(urls)}: `{short_name}`…",
                )

                tracker = ProgressTracker(
                    message=status_message,
                    filename=short_name,
                    update_interval=PROGRESS_UPDATE_INTERVAL,
                )

                file_path = await download_file(
                    url=url,
                    dest_dir=temp_dir,
                    progress_callback=tracker.update,
                )

                if file_path is not None:
                    downloaded.append(file_path)
                    await tracker.complete()
                else:
                    await tracker.error("Download failed after retries")

            # ── Nothing downloaded ──────────────────────────
            if not downloaded:
                await self._safe_edit(
                    status_message, "❌ No files were downloaded successfully."
                )
                cleanup_temp_dir(session_id)
                return None

            # ── Single file ─────────────────────────────────
            if len(downloaded) == 1:
                logger.info(f"Single file ready: {downloaded[0].name}")
                return downloaded[0], session_id

            # ── Multiple files → ZIP ───────────────────────
            await self._safe_edit(
                status_message,
                f"🗜 Zipping {len(downloaded)} files…",
            )
            zip_path = temp_dir / f"files_{session_id}.zip"
            create_zip(downloaded, zip_path)
            logger.info(f"ZIP ready: {zip_path.name}")
            return zip_path, session_id

        except Exception as exc:
            logger.error(f"DirectLinkService.process failed: {exc}", exc_info=True)
            cleanup_temp_dir(session_id)
            raise

    # ── internal helper ─────────────────────────────────────
    @staticmethod
    async def _safe_edit(message: Message, text: str) -> None:
        try:
            await message.edit_text(text, parse_mode="Markdown")
        except Exception:
            pass
