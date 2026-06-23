from config import HTTP_API, ALLOWED_USER_IDS
from constants import WHISPER_MODEL, NOTES_DIR

from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import whisper
import os


def is_allowed(update: Update) -> bool:
    """Check if the user is allowed to use the bot."""
    return update.effective_user.id in ALLOWED_USER_IDS


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responds with "pong" to check if the bot is alive."""
    if not is_allowed(update):
        return

    await update.message.reply_text("pong")


def save_message_to_file(message_text: str):
    """Save a message to a text file named YYYY_MM_DD.md."""
    now = datetime.now()
    day = now.strftime("%Y_%m_%d")  # YYYY_MM_DD
    timestamp = now.strftime("%H:%M")  # HH:MM

    notes_dir = Path(NOTES_DIR)
    notes_dir.mkdir(parents=True, exist_ok=True)

    note_path = notes_dir / f"{day}.md"
    is_new_file = not note_path.exists()

    with note_path.open("a", encoding="utf-8") as text_file:
        if is_new_file:
            text_file.write(f"# {day}\n\n")
        # there's one space already before the message text
        text_file.write(f"- [{timestamp}] {message_text}\n")


async def transcribe_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribes the voice message"""
    if not is_allowed(update):
        return

    # Get the voice message from the update
    voice = update.message.voice

    # Download the voice message to a local file
    tg_file = await context.bot.get_file(voice.file_id)

    # Use the unique file ID to create a unique filename for the downloaded audio
    filename = f"{voice.file_unique_id}.ogg"
    await tg_file.download_to_drive(filename)

    try:
        # Transcribe the audio file using the Whisper model stored in bot_data
        model = context.application.bot_data["model"]
        result = model.transcribe(filename)

        # Extract the transcribed text from the result and send it back to the user
        transcription = result["text"]
        await update.message.reply_text(transcription)

        # Save the transcription to the daily markdown note
        save_message_to_file(transcription)

    finally:
        os.remove(filename)


async def store_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores a plain text message."""
    if not is_allowed(update):
        return

    message_text = update.message.text
    save_message_to_file(message_text)


def main():
    print("Loading the bot...")
    app = ApplicationBuilder().token(HTTP_API).build()

    print(f"Loading the Whisper model: {WHISPER_MODEL}...")
    app.bot_data["model"] = whisper.load_model(WHISPER_MODEL)

    # /ping returns "pong" to check if the bot is alive
    app.add_handler(CommandHandler(command="ping", callback=ping))

    # Handle voice messages and transcribe them
    app.add_handler(MessageHandler(filters=filters.VOICE, callback=transcribe_audio))

    # Handle plain text messages, but ignore commands
    app.add_handler(MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=store_text_message))

    print("Bot is running! :)")
    app.run_polling()


if __name__ == "__main__":
    main()
