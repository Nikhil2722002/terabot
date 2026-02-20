"""
Real-time Progress Tracker
- Edits a Telegram message with a visual progress bar
- Throttled updates to avoid Telegram rate-limits
"""

import time
import logging

from telegram import Message

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks bytes downloaded and periodically edits a Telegram
    message to show a visual progress bar.

    Usage:
        tracker = ProgressTracker(msg, "video.mp4", update_interval=3.0)
        await tracker.update(downloaded_bytes, total_bytes)
        await tracker.complete()
    """

    def __init__(
        self,
        message: Message,
        filename: str,
        update_interval: float = 3.0,
    ) -> None:
        self.message = message
        self.filename = filename
        self.update_interval = update_interval
        self._last_update: float = 0.0
        self._last_text: str = ""

    # ── public API ──────────────────────────────────────────

    async def update(self, downloaded: int, total: int) -> None:
        """Called after every chunk. Only edits message if interval elapsed."""
        now = time.monotonic()
        if now - self._last_update < self.update_interval:
            return
        self._last_update = now

        if total > 0:
            pct = min(int(downloaded / total * 100), 100)
            bar = self._bar(pct)
            dl_mb = downloaded / 1_048_576
            tot_mb = total / 1_048_576
            text = (
                f"⬇️ `{self.filename}`\n"
                f"{bar} {pct}%\n"
                f"{dl_mb:.1f} / {tot_mb:.1f} MB"
            )
        else:
            dl_mb = downloaded / 1_048_576
            text = f"⬇️ `{self.filename}` — {dl_mb:.1f} MB downloaded…"

        await self._edit(text)

    async def complete(self) -> None:
        await self._edit(f"✅ `{self.filename}` downloaded")

    async def error(self, reason: str) -> None:
        await self._edit(f"❌ `{self.filename}` — {reason}")

    # ── internals ───────────────────────────────────────────

    async def _edit(self, text: str) -> None:
        if text == self._last_text:
            return
        self._last_text = text
        try:
            await self.message.edit_text(text, parse_mode="Markdown")
        except Exception as exc:
            logger.debug(f"Progress edit failed: {exc}")

    @staticmethod
    def _bar(pct: int, width: int = 20) -> str:
        filled = int(width * pct / 100)
        return "[" + "█" * filled + "░" * (width - filled) + "]"
