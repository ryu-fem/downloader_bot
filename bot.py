"""
Telegram bot that downloads video / audio / images from social media links
(TikTok, Instagram, Facebook, YouTube, Twitter/X, and anything else yt-dlp supports).

How it works:
  1. User sends a link in chat.
  2. Bot uses yt-dlp to fetch info & download the media to a temp folder.
  3. Bot uses format buttons (Video / Audio / Best quality) so the user can choose.
  4. Bot sends the resulting file back and deletes the temp copy.

Requirements: see requirements.txt
Run:          python bot.py   (after setting BOT_TOKEN, see README.md)
"""

import logging
import os
import re
import tempfile
import shutil
from pathlib import Path

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")

# Telegram's own Bot API rejects uploads over this size unless you run a
# local Bot API server (see README.md). Default cloud limit = 50 MB.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

URL_REGEX = re.compile(r"https?://\S+")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory map of "pending link per chat" so the button callback knows
# which URL to act on. For a multi-user production bot, swap this for a
# real cache (redis, sqlite, etc.) since this dict is not persisted.
PENDING_LINKS: dict[int, str] = {}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def build_ydl_opts(mode: str, out_dir: str) -> dict:
    """Return yt-dlp options for the chosen mode: 'video', 'audio', or 'image'."""
    outtmpl = os.path.join(out_dir, "%(title).80s.%(ext)s")

    if mode == "audio":
        return {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "noplaylist": True,
            "quiet": True,
        }

    # 'video' and 'image' (most platforms serve images as a single frame
    # or a photo entry that yt-dlp can also fetch directly) both use the
    # same "grab best available media" approach.
    return {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
    }


def download_media(url: str, mode: str, out_dir: str) -> Path:
    opts = build_ydl_opts(mode, out_dir)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    # If audio postprocessing changed the extension to mp3, find the actual file.
    if mode == "audio":
        candidate = Path(filename).with_suffix(".mp3")
        if candidate.exists():
            return candidate

    return Path(filename)


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send me a link from TikTok, Instagram, Facebook, YouTube, Twitter/X, etc. "
        "and I'll grab the video, audio, or image for you."
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    match = URL_REGEX.search(text)
    if not match:
        await update.message.reply_text("That doesn't look like a link. Send me a URL to download from.")
        return

    url = match.group(0)
    PENDING_LINKS[update.effective_chat.id] = url

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎬 Video", callback_data="video"),
                InlineKeyboardButton("🎵 Audio (MP3)", callback_data="audio"),
                InlineKeyboardButton("🖼 Image", callback_data="image"),
            ]
        ]
    )
    await update.message.reply_text("What would you like to download?", reply_markup=keyboard)


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    url = PENDING_LINKS.get(chat_id)
    if not url:
        await query.edit_message_text("That link expired — send it again.")
        return

    mode = query.data  # "video" / "audio" / "image"
    await query.edit_message_text(f"Downloading ({mode})… this can take a bit for larger files.")

    tmp_dir = tempfile.mkdtemp(prefix="tgmedia_")
    try:
        filepath = download_media(url, mode, tmp_dir)

        if not filepath.exists():
            await context.bot.send_message(chat_id, "Couldn't find the downloaded file. The link may not be supported.")
            return

        size = filepath.stat().st_size
        if size > MAX_UPLOAD_BYTES:
            await context.bot.send_message(
                chat_id,
                f"The file is {size / 1_048_576:.1f} MB, which is over Telegram's "
                f"{MAX_UPLOAD_BYTES / 1_048_576:.0f} MB bot upload limit. "
                "Try audio-only, or run a local Bot API server for larger uploads (see README).",
            )
            return

        with open(filepath, "rb") as f:
            if mode == "audio":
                await context.bot.send_audio(chat_id, f)
            elif mode == "image":
                await context.bot.send_photo(chat_id, f)
            else:
                await context.bot.send_video(chat_id, f)

    except yt_dlp.utils.DownloadError as e:
        logger.exception("yt-dlp failed")
        await context.bot.send_message(chat_id, f"Download failed: {e}")
    except Exception as e:
        logger.exception("Unexpected error")
        await context.bot.send_message(chat_id, f"Something went wrong: {e}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        PENDING_LINKS.pop(chat_id, None)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    if BOT_TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise SystemExit("Set the BOT_TOKEN environment variable before running (see README.md).")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_choice))

    logger.info("Bot started. Waiting for messages...")
    app.run_polling()


if __name__ == "__main__":
    main()
