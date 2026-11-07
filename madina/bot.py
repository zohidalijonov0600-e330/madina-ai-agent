from __future__ import annotations

import logging
import mimetypes
import os
import tempfile
from io import BytesIO
from pathlib import Path

from telegram import Update
from telegram.constants import ChatType
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from madina.config import settings
from madina.db import (
    SessionLocal,
    clear_history,
    get_or_create_user,
    get_recent_history,
    get_user,
    init_db,
    save_message,
    set_voice_mode,
    update_user_language,
)
from madina.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

WELCOME = (
    "Assalomu alaykum! Men Madinaman. Sizning shaxsiy AI yordamchingizman. "
    "Men bilan o'zbek tilida yozishishingiz yoki ovozli xabar orqali "
    "gaplashishingiz mumkin. Sizga qanday yordam beray?"
)
SYSTEM_PROMPTS = {
    "uz": "Siz Madina, samimiy, professional va muloyim o'zbek tilidagi shaxsiy AI yordamchisiz. Aniq va tushunarli javob bering. Foydalanuvchi boshqa tilda yozsa, o'sha tilda javob bering.",
    "ru": "Вы Мадина, дружелюбный и профессиональный личный AI-помощник. Отвечайте ясно и вежливо.",
    "en": "You are Madina, a friendly and professional personal AI assistant. Answer clearly and warmly.",
}


def _allowed(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    return bool(
        user
        and chat
        and chat.type == ChatType.PRIVATE
        and settings.is_user_allowed(user.id)
    )


async def _guard(update: Update) -> bool:
    if _allowed(update):
        return True
    if update.effective_message:
        await update.effective_message.reply_text(
            "Kechirasiz, bot faqat egasining shaxsiy chatida ishlaydi."
        )
    return False


def _user_for_update(update: Update, db):
    user = update.effective_user
    return get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)


def _make_messages(history: list[dict[str, str]], language: str) -> list[dict[str, str]]:
    prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["uz"])
    return [{"role": "system", "content": prompt}, *history]


async def _send_reply(update: Update, answer: str, voice_enabled: bool, client: OpenRouterClient) -> None:
    message = update.effective_message
    if not message:
        return
    # Telegram text messages are limited to 4096 characters.
    for start in range(0, len(answer), 4000):
        await message.reply_text(answer[start : start + 4000])
    if voice_enabled and client.tts_model:
        try:
            audio = await client.text_to_speech(answer[:4000])
            buffer = BytesIO(audio)
            buffer.name = "madina_reply.mp3"
            await message.reply_audio(buffer, title="Madina javobi", performer="Madina")
        except Exception:
            logger.exception("TTS failed; text reply was still sent")


async def _answer(update: Update, text: str, client: OpenRouterClient) -> None:
    with SessionLocal() as db:
        profile = _user_for_update(update, db)
        save_message(db, profile.telegram_user_id, "user", text)
        history = get_recent_history(db, profile.telegram_user_id, limit=12)
        messages = _make_messages(history, profile.language or "uz")
        try:
            answer = await client.generate_chat_completion(messages)
        except Exception:
            logger.exception("OpenRouter chat request failed")
            await update.effective_message.reply_text(
                "Kechirasiz, hozir AI xizmatiga ulanishda muammo bor. Birozdan keyin qayta urinib ko'ring."
            )
            return
        save_message(db, profile.telegram_user_id, "assistant", answer)
        voice_enabled = bool(profile.voice_enabled)
    await _send_reply(update, answer, voice_enabled, client)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    with SessionLocal() as db:
        _user_for_update(update, db)
    await update.effective_message.reply_text(WELCOME)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await update.effective_message.reply_text(
        "Buyruqlar:\n/start — boshlash\n/help — yordam\n"
        "/voice_on — ovozli javobni yoqish\n/voice_off yoki /text — o'chirish\n"
        "/language uz|ru|en — tilni tanlash\n/clear — suhbat tarixini o'chirish\n"
        "/status — ulanish holati"
    )


async def voice_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    enabled = update.effective_message.text.startswith("/voice_on")
    with SessionLocal() as db:
        profile = _user_for_update(update, db)
        set_voice_mode(db, profile.telegram_user_id, enabled)
    await update.effective_message.reply_text(
        "Ovozli javob yoqildi." if enabled else "Faqat matnli javob beraman."
    )


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    if not context.args or context.args[0].lower() not in {"uz", "ru", "en"}:
        await update.effective_message.reply_text("Tilni tanlang: /language uz, /language ru yoki /language en")
        return
    lang = context.args[0].lower()
    with SessionLocal() as db:
        update_user_language(db, update.effective_user.id, lang)
    await update.effective_message.reply_text(f"Til sozlandi: {lang}")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    with SessionLocal() as db:
        clear_history(db, update.effective_user.id)
    await update.effective_message.reply_text("Suhbat tarixi tozalandi.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    client: OpenRouterClient = context.application.bot_data["openrouter"]
    try:
        await client.check_api()
        api_status = "ulangan"
    except Exception:
        logger.exception("OpenRouter status check failed")
        api_status = "ulanmadi — API kaliti yoki internetni tekshiring"
    await update.effective_message.reply_text(
        f"Bot ishlayapti.\nOpenRouter: {api_status}\nModel: {settings.gemini_model}"
    )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    await _answer(update, update.effective_message.text, context.application.bot_data["openrouter"])


async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _guard(update):
        return
    client: OpenRouterClient = context.application.bot_data["openrouter"]
    if not client.stt_model:
        await update.effective_message.reply_text("Ovozdan matnga aylantirish modeli sozlanmagan.")
        return

    voice = update.effective_message.voice
    telegram_file = await context.bot.get_file(voice.file_id)
    suffix = ".ogg"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as audio:
            temp_path = audio.name
        await telegram_file.download_to_drive(custom_path=temp_path)
        with SessionLocal() as db:
            profile = _user_for_update(update, db)
            language_code = profile.language or "uz"
        transcript = await client.transcribe_audio(temp_path, language=language_code)
        if not transcript.strip():
            await update.effective_message.reply_text("Ovozni tushuna olmadim. Iltimos, yana bir bor yuboring.")
            return
        await _answer(update, transcript, client)
    except Exception:
        logger.exception("Voice message processing failed")
        await update.effective_message.reply_text(
            "Ovozli xabarni qayta ishlashda muammo yuz berdi. Keyinroq qayta urinib ko'ring yoki matn yozing."
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled Telegram handler error", exc_info=context.error)


def build_application() -> Application:
    init_db()
    client = OpenRouterClient()
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["openrouter"] = client
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["voice_on", "voice_off", "text"], voice_mode))
    app.add_handler(CommandHandler("language", language))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    app.add_handler(MessageHandler(filters.VOICE, voice_message))
    app.add_error_handler(error_handler)
    return app
