from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from io import BytesIO

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from madina.config import settings
from madina.db import ChatMessage, clear_history, get_or_create_user, get_recent_history, init_db, set_voice_mode, update_user_language
from madina.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_UZ = """Siz Madina, samimiy, o'zbek tilida muloqot qiluvchi shaxsiy AI yordamchisiz. Foydalanuvchiga professional, qulay, muloyim va xushmuomalalik bilan javob bering. Qisqa, aniq va tushunarli gaplar ishlating. Agar ma'lumot yetishmasa, muammo haqida aniq va foydali yo'l ko'rsating. Har doim o'zbek tilida javob bering. Yordamchi savollarda rus va ingliz tillarida ham tushunib, kerak bo'lganda ularda javob berishingiz mumkin."""
SYSTEM_PROMPT_RU = """Вы Мадина, дружелюбный личный AI-ассистент, общаетесь по-русски. Отвечайте спокойно, профессионально и понятно. Используйте вежливый и человеческий тон."""
SYSTEM_PROMPT_EN = """You are Madina, a friendly personal AI assistant. Answer clearly, warmly, and professionally in English."""


async def ensure_allowed(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return False
    if settings.is_user_allowed(user_id):
        return True
    await update.message.reply_text("Kechirasiz, bu bot faqat egasiga ochiq. Keyinchalik ruxsatni sozlash mumkin.")
    return False


async def localized_system_prompt(language: str) -> str:
    language = (language or "uz").lower()
    if language == "ru":
        return SYSTEM_PROMPT_RU
    if language == "en":
        return SYSTEM_PROMPT_EN
    return SYSTEM_PROMPT_UZ


def build_history_messages(history: list[dict[str, str]], language: str) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT_UZ if language in {"uz", "uzbek"} else SYSTEM_PROMPT_RU if language == "ru" else SYSTEM_PROMPT_EN}]
    for item in history:
        role = item["role"]
        if role in {"user", "assistant"}:
            messages.append({"role": role, "content": item["content"]})
    return messages


class MadinaBot:
    def __init__(self, app: Application, client: OpenRouterClient) -> None:
        self.app = app
        self.client = client

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        user = update.effective_user
        db = context.bot_data.get("db")
        if db is not None:
            from madina.db import get_or_create_user
            get_or_create_user(db, user.id, user.first_name, user.last_name, user.username)
        await update.message.reply_text(
            "Assalomu alaykum! Men Madinaman. Sizning shaxsiy AI yordamchingizman. Men bilan o'zbek tilida yozishishingiz yoki ovozli xabar orqali gaplashishingiz mumkin. Sizga qanday yordam beray?"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        await update.message.reply_text(
            "Buyruqlar:\n"
            "/start - botni ishga tushirish\n"
            "/help - yordam\n"
            "/voice_on - ovozli javoblarni yoqish\n"
            "/voice_off - ovozli javoblarni o'chirish\n"
            "/text - faqat matnli javob\n"
            "/language uz|ru|en - tilni tanlash\n"
            "/clear - suhbat tarixini tozalash\n"
            "/status - bot va API holatini tekshirish"
        )

    async def voice_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        db = context.bot_data.get("db")
        if db is not None:
            from madina.db import set_voice_mode
            set_voice_mode(db, update.effective_user.id, True)
        await update.message.reply_text("Ovozli javoblar yoqildi.")

    async def voice_off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        db = context.bot_data.get("db")
        if db is not None:
            from madina.db import set_voice_mode
            set_voice_mode(db, update.effective_user.id, False)
        await update.message.reply_text("Ovozli javoblar o'chirildi.")

    async def text_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        db = context.bot_data.get("db")
        if db is not None:
            from madina.db import set_voice_mode
            set_voice_mode(db, update.effective_user.id, False)
        await update.message.reply_text("Endi faqat matnli javob beraman.")

    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        db = context.bot_data.get("db")
        if not context.args:
            await update.message.reply_text("Tilni tanlang: /language uz, /language ru, /language en")
            return
        lang = context.args[0].lower()
        if lang not in {"uz", "ru", "en"}:
            await update.message.reply_text("Noto'g'ri til kodi. Faqat uz, ru yoki en kiriting.")
            return
        if db is not None:
            from madina.db import update_user_language
            update_user_language(db, update.effective_user.id, lang)
        await update.message.reply_text(f"Til sozlandi: {lang}")

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        db = context.bot_data.get("db")
        if db is not None:
            from madina.db import clear_history
            clear_history(db, update.effective_user.id)
        await update.message.reply_text("Suhbat konteksti tozalandi.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        api_ok = False
        try:
            await self.client.check_api()
            api_ok = True
        except Exception as exc:  # pragma: no cover - runtime guard
            logger.exception("API status check failed")
            api_ok = False
        await update.message.reply_text(
            f"Bot holati: tayyor\n"
            f"OpenRouter API: {'ishlayapti' if api_ok else 'nosoz'}\n"
            f"DB: SQLite ishlayapti\n"
            f"Model: {settings.gemini_model}"
        )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        text = update.message.text or ""
        if not text:
            return
        db = context.bot_data.get("db")
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.first_name, update.effective_user.last_name, update.effective_user.username)
        from madina.db import save_message, get_recent_history
        save_message(db, user.telegram_user_id, "user", text)

        history = get_recent_history(db, user.telegram_user_id, limit=12)
        lang = user.language or "uz"
        messages = build_history_messages(history, lang)
        try:
            answer = await self.client.generate_chat_completion(messages)
        except Exception as exc:
            logger.exception("Chat completion failed")
            answer = "Kechirasiz, hozir javob olishda muammo yuz berdi. Bir ozdan keyin qayta urinib ko'ring."

        save_message(db, user.telegram_user_id, "assistant", answer)
        await update.message.reply_text(answer)

        user_profile = context.bot_data.get("db")
        if user_profile is not None:
            from madina.db import get_user
            profile = get_user(db, update.effective_user.id)
            if profile and profile.voice_enabled:
                try:
                    audio = await self.client.text_to_speech(answer)
                    buffer = BytesIO(audio)
                    buffer.name = "madina_reply.mp3"
                    await update.message.reply_audio(buffer, title="Madina javobi", performer="Madina")
                except Exception as exc:  # pragma: no cover - runtime guard
                    logger.exception("Voice response failed")

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await ensure_allowed(update):
            return
        voice = update.message.voice
        if voice is None:
            return
        file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            temp_path = tmp.name
        await file.download_to_drive(custom_path=temp_path)

        converted_path = None
        if os.path.exists(temp_path):
            converted_path = temp_path + ".wav"
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                temp_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                converted_path,
            ]
            try:
                subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except (FileNotFoundError, subprocess.CalledProcessError):
                converted_path = temp_path

        audio_file = converted_path or temp_path
        db = context.bot_data.get("db")
        user = get_or_create_user(db, update.effective_user.id, update.effective_user.first_name, update.effective_user.last_name, update.effective_user.username)
        try:
            transcript = await self.client.transcribe_audio(audio_file, language=user.language or "uz")
            if not transcript.strip():
                transcript = "Ovozli xabarni tushuna olmadim. Iltimos, qayta ayting."
            await self.handle_text_message_from_user(update, transcript, user)
        finally:
            for path in {temp_path, converted_path}:
                if path and os.path.exists(path):
                    os.remove(path)

    async def handle_text_message_from_user(self, update: Update, text: str, user) -> None:
        db = update._bot_data.get("db")
        from madina.db import save_message, get_recent_history
        save_message(db, user.telegram_user_id, "user", text)
        history = get_recent_history(db, user.telegram_user_id, limit=12)
        messages = build_history_messages(history, user.language or "uz")
        try:
            answer = await self.client.generate_chat_completion(messages)
        except Exception:
            answer = "Kechirasiz, hozir javob olishda muammo yuz berdi."
        save_message(db, user.telegram_user_id, "assistant", answer)
        await update.message.reply_text(answer)

        if user.voice_enabled:
            try:
                audio = await self.client.text_to_speech(answer)
                buffer = BytesIO(audio)
                buffer.name = "madina_reply.mp3"
                await update.message.reply_audio(buffer, title="Madina javobi", performer="Madina")
            except Exception as exc:  # pragma: no cover - runtime guard
                logger.exception("Voice response failed")

    async def add_handlers(self) -> None:
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("voice_on", self.voice_on_command))
        self.app.add_handler(CommandHandler("voice_off", self.voice_off_command))
        self.app.add_handler(CommandHandler("text", self.text_command))
        self.app.add_handler(CommandHandler("language", self.language_command))
        self.app.add_handler(CommandHandler("clear", self.clear_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.app.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))


async def create_app() -> Application:
    init_db()
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["db"] = None
    app.bot_data["db"] = __import__("madina.db", fromlist=["SessionLocal"]).SessionLocal()
    client = OpenRouterClient()
    bot = MadinaBot(app, client)
    await bot.add_handlers()
    return app


async def main() -> None:
    missing = settings.validate()
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    app = await create_app()
    await app.initialize()
    await app.start()
    await app.run_polling(allowed_updates=["message"])
