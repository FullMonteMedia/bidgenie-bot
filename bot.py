"""
BidGenie AI — Main Bot Entry Point
Ace Plumbing's AI-powered bid proposal generator for Telegram.

Usage:
    python bot.py

Environment:
    TELEGRAM_BOT_TOKEN — Required
    ANTHROPIC_API_KEY  — Required (or OPENAI_API_KEY)
    See .env.example for full configuration.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Import handlers
from src.handlers.command_handlers import (
    cmd_start, cmd_help, cmd_newbid, cmd_upload,
    cmd_settings, cmd_set, cmd_preset, cmd_scope,
    cmd_status, cmd_clear, cmd_rush,
)
from src.handlers.message_handlers import (
    handle_text_message, handle_file_upload,
    handle_generate, handle_export, cmd_export,
    handle_callback_query,
)

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bidgenie.log"),
    ],
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)


# ─── GENERATE COMMAND WRAPPER ────────────────────────────────────────────────

async def cmd_generate(update: Update, context):
    """Wrapper for /generate command."""
    await handle_generate(update, context)


# ─── BOT SETUP ───────────────────────────────────────────────────────────────

def create_application() -> Application:
    """Create and configure the Telegram bot application."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not set. "
            "Copy .env.example to .env and add your bot token."
        )

    app = Application.builder().token(token).build()

    # ── Command Handlers ──────────────────────────────────────────────────
    async def test_start(update: Update, context):
        await update.message.reply_text("Bot is working ✅")
    
    app.add_handler(CommandHandler("start", test_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("newbid", cmd_newbid))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("set", cmd_set))
    app.add_handler(CommandHandler("preset", cmd_preset))
    app.add_handler(CommandHandler("scope", cmd_scope))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("rush", cmd_rush))
    app.add_handler(CommandHandler("generate", cmd_generate))
    app.add_handler(CommandHandler("export", cmd_export))

    # ── File Upload Handlers ──────────────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO,
        handle_file_upload,
    ))

    # ── Text Message Handler ──────────────────────────────────────────────
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message,
    ))

    # ── Callback Query Handler (inline buttons) ───────────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("✅ BidGenie AI bot configured successfully")
    return app


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    """Start the bot."""
    logger.info("=" * 60)
    logger.info("  BidGenie AI — Starting for Ace Plumbing")
    logger.info("=" * 60)

    # Validate required env vars
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in .env file")
        logger.error("   Copy .env.example to .env and fill in your values")
        return

    ai_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not ai_key:
        logger.warning("⚠️  No AI API key found. AI features will use fallback mode.")
        logger.warning("   Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")

    # Create upload/proposal directories
    os.makedirs(os.getenv("UPLOAD_DIR", "uploads"), exist_ok=True)
    os.makedirs(os.getenv("PROPOSALS_DIR", "proposals"), exist_ok=True)

    app = create_application()

    logger.info("🚀 Bot is running. Press Ctrl+C to stop.")
    logger.info(f"   Company: {os.getenv('COMPANY_NAME', 'Ace Plumbing')}")
    logger.info(f"   Upload dir: {os.getenv('UPLOAD_DIR', 'uploads')}")
    logger.info(f"   Proposals dir: {os.getenv('PROPOSALS_DIR', 'proposals')}")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
