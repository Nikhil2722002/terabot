import sys
import logging
from pathlib import Path

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import (
    BOT_TOKEN,
    WEBHOOK_URL,
    PORT,
    WEBHOOK_PATH,
    LOG_LEVEL,
    LOG_FILE,
    TELEGRAM_FILE_LIMIT,
    TEMP_DIR,
)
from services.link_router import extract_urls, route_urls, LinkType
from services.direct_link_service import DirectLinkService
from utils.file_utils import cleanup_temp_dir, is_video_file


# ─── Logging Setup ─────────────────────────────────────────
def setup_logging() -> None:
    """Configure structured logging to console and file."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    try:
        log_dir = Path(LOG_FILE).parent
        if str(log_dir) != ".":
            log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))
    except Exception:
        pass  # File logging optional; console always works

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=handlers,
    )


setup_logging()
logger = logging.getLogger(__name__)

# ─── Service Instances ─────────────────────────────────────
direct_service = DirectLinkService()


# ─── /start ────────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome = (
        "🤖 *File Processing Bot*\n\n"
        "Send me:\n"
        "• A direct file link (mp4, zip, pdf …)\n"
        "• Multiple links (one per line)\n"
        "• A `.txt` file containing download URLs\n\n"
        "I'll download them and send the files back!\n\n"
        "⚠️ Max file size: 50 MB per file\n"
        "📦 Multiple files are zipped automatically"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")


# ─── Text Messages (URLs) ─────────────────────────────────
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages containing one or more URLs."""
    text = update.message.text.strip()
    urls = extract_urls(text)

    if not urls:
        await update.message.reply_text(
            "❌ No valid URLs found in your message.\n"
            "Send a direct download link or upload a .txt file."
        )
        return

    await _process_urls(urls, update, context)


# ─── Document Upload (.txt) ───────────────────────────────
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle uploaded .txt files containing URLs."""
    document = update.message.document

    if not document.file_name.lower().endswith(".txt"):
        await update.message.reply_text(
            "❌ Please upload a `.txt` file containing URLs."
        )
        return

    status = await update.message.reply_text("📄 Reading uploaded file…")

    try:
        tg_file = await document.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        content = file_bytes.decode("utf-8", errors="ignore")

        urls = extract_urls(content)

        if not urls:
            await status.edit_text("❌ No valid URLs found in the uploaded file.")
            return

        await status.edit_text(f"🔗 Found {len(urls)} URL(s). Starting downloads…")
        await _process_urls(urls, update, context, existing_status=status)

    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        await _safe_edit(status, f"❌ Error reading file: {str(e)[:200]}")


# ─── Core Processing Pipeline ─────────────────────────────
async def _process_urls(
    urls: list[str],
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    existing_status=None,
) -> None:
    """Download → (zip) → send pipeline."""
    chat_id = update.effective_chat.id
    status = existing_status or await update.message.reply_text(
        f"🔗 Found {len(urls)} URL(s). Starting download…"
    )

    session_id: str | None = None

    try:
        # Route URLs by type
        routed = route_urls(urls)
        direct_urls = [url for url, link_type in routed if link_type == LinkType.DIRECT]

        if not direct_urls:
            await _safe_edit(status, "❌ No supported download URLs found.")
            return

        # Download all files via direct-link service
        result = await direct_service.process(
            urls=direct_urls,
            status_message=status,
            chat_id=chat_id,
        )

        if result is None:
            return

        file_path, session_id = result

        # Verify Telegram size limit
        file_size = file_path.stat().st_size
        if file_size > TELEGRAM_FILE_LIMIT:
            await _safe_edit(
                status,
                f"❌ Result is too large for Telegram "
                f"({file_size / (1024 * 1024):.1f} MB, limit {TELEGRAM_FILE_LIMIT // (1024 * 1024)} MB).",
            )
            return

        # Upload to Telegram
        await _safe_edit(status, "📤 Uploading to Telegram…")

        with open(file_path, "rb") as f:
            if is_video_file(file_path.name):
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    filename=file_path.name,
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                )
            else:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    filename=file_path.name,
                    read_timeout=120,
                    write_timeout=120,
                )

        await _safe_edit(status, f"✅ Done! Sent `{file_path.name}`", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in _process_urls: {e}", exc_info=True)
        await _safe_edit(status, f"❌ An error occurred: {str(e)[:200]}")
    finally:
        if session_id:
            cleanup_temp_dir(session_id)


# ─── Helpers ───────────────────────────────────────────────
async def _safe_edit(message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except Exception:
        pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler — logs all unhandled exceptions."""
    logger.error("Unhandled exception:", exc_info=context.error)


async def post_init(application: Application) -> None:
    """Runs once after the application is initialized."""
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot and see instructions"),
    ])
    logger.info("Bot commands registered.")


# ─── Entry Point ───────────────────────────────────────────
def main() -> None:
    if not BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not set. Exiting.")
        sys.exit(1)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register handlers (order matters — Document before Text)
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)

    if WEBHOOK_URL:
        logger.info(f"Starting webhook on port {PORT}: {WEBHOOK_URL}{WEBHOOK_PATH}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        )
    else:
        logger.info("Starting polling mode…")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
