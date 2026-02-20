import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ─── Bot Settings ──────────────────────────────────────────
BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ─── Download Settings ─────────────────────────────────────
MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))  # 50 MB
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", str(8192)))  # 8 KB
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))  # 5 minutes

# ─── Progress Settings ─────────────────────────────────────
PROGRESS_UPDATE_INTERVAL: float = float(os.getenv("PROGRESS_UPDATE_INTERVAL", "3.0"))

# ─── Path Settings ─────────────────────────────────────────
TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "/tmp/telegram_bot"))

# ─── Logging ───────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")

# ─── Webhook / Render Deployment ───────────────────────────
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
PORT: int = int(os.getenv("PORT", "8443"))
WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")

# ─── Telegram Limits ──────────────────────────────────────
TELEGRAM_FILE_LIMIT: int = 50 * 1024 * 1024  # 50 MB (Bot API limit)

# ─── Allowed File Extensions ──────────────────────────────
ALLOWED_EXTENSIONS: set = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp3", ".wav", ".flac", ".ogg",
    ".apk", ".exe", ".dmg",
    ".txt", ".csv", ".json", ".xml",
}

VIDEO_EXTENSIONS: set = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
