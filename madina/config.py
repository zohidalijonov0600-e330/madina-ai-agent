from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()


def _as_int(value: str | None, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass
class Settings:
    telegram_bot_token: str = ""
    openrouter_api_key: str = ""
    gemini_model: str = "google/gemini-2.0-flash-001"
    stt_model: str = "google/chirp-3"
    tts_model: str = "google/gemini-2.0-flash-preview-tts"
    owner_telegram_id: int | None = None
    database_url: str = "sqlite:///./madina.db"
    timezone: str = "Asia/Tashkent"
    allowed_telegram_ids: set[int] = field(default_factory=set)

    @classmethod
    def from_env(cls) -> "Settings":
        allowed_raw = os.getenv("ALLOWED_TELEGRAM_IDS", "")
        allowed_ids: set[int] = set()
        for item in allowed_raw.split(","):
            parsed = _as_int(item.strip())
            if parsed is not None:
                allowed_ids.add(parsed)

        owner_raw = os.getenv("OWNER_TELEGRAM_ID")
        owner_id = _as_int(owner_raw)

        settings = cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "google/gemini-2.0-flash-001"),
            stt_model=os.getenv("STT_MODEL", "google/chirp-3"),
            tts_model=os.getenv("TTS_MODEL", "google/gemini-2.0-flash-preview-tts"),
            owner_telegram_id=owner_id,
            database_url=os.getenv("DATABASE_URL", "sqlite:///./madina.db"),
            timezone=os.getenv("TIMEZONE", "Asia/Tashkent"),
            allowed_telegram_ids=allowed_ids,
        )
        return settings

    def is_user_allowed(self, user_id: int) -> bool:
        if self.owner_telegram_id is not None and user_id == self.owner_telegram_id:
            return True
        return user_id in self.allowed_telegram_ids

    def validate(self) -> list[str]:
        missing: list[str] = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.openrouter_api_key:
            missing.append("OPENROUTER_API_KEY")
        if self.owner_telegram_id is None:
            missing.append("OWNER_TELEGRAM_ID")
        return missing


settings = Settings.from_env()
