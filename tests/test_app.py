# Madina AI Agent tests

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from madina.config import Settings
from madina.db import init_db, get_or_create_user, save_message, get_recent_history


class ConfigTests(unittest.TestCase):
    def test_settings_loads_values(self):
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "test_token",
                "OPENROUTER_API_KEY": "test_key",
                "OWNER_TELEGRAM_ID": "123456789",
                "DATABASE_URL": "sqlite:///:memory:",
            },
            clear=False,
        ):
            settings = Settings.from_env()
            self.assertEqual(settings.telegram_bot_token, "test_token")
            self.assertEqual(settings.owner_telegram_id, 123456789)
            self.assertEqual(settings.database_url, "sqlite:///:memory:")

    def test_validation_flags_missing_values(self):
        settings = Settings(
            telegram_bot_token="",
            openrouter_api_key="",
            owner_telegram_id=None,
        )
        self.assertTrue(settings.validate())


class DatabaseTests(unittest.TestCase):
    def test_db_history_round_trip(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
            db_path = f"sqlite:///{temp_db.name}"
            import madina.db as db_module
            db_module.engine = db_module.create_engine(db_path, future=True)
            db_module.SessionLocal = db_module.sessionmaker(bind=db_module.engine, autoflush=False, autocommit=False)
            init_db()
            db = db_module.SessionLocal()
            user = get_or_create_user(db, 111, "Madina", "Test", "madina")
            save_message(db, user.telegram_user_id, "user", "Salom")
            save_message(db, user.telegram_user_id, "assistant", "Salom, qanday yordam kerak?")
            history = get_recent_history(db, user.telegram_user_id, limit=10)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["role"], "user")
            db.close()


if __name__ == "__main__":
    unittest.main()
