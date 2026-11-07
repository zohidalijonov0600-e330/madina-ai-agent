from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from madina.config import Settings
from madina.bot import _make_messages


class SettingsTests(unittest.TestCase):
    def test_owner_is_parsed_and_only_owner_is_allowed(self):
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "example-token",
            "OPENROUTER_API_KEY": "example-key",
            "OWNER_TELEGRAM_ID": "12345",
            "ALLOWED_TELEGRAM_IDS": "67890",
        }, clear=False):
            settings = Settings.from_env()
        self.assertTrue(settings.is_user_allowed(12345))
        self.assertTrue(settings.is_user_allowed(67890))
        self.assertFalse(settings.is_user_allowed(1))

    def test_missing_config_is_reported(self):
        settings = Settings(telegram_bot_token="", openrouter_api_key="", owner_telegram_id=None)
        self.assertEqual(set(settings.validate()), {"TELEGRAM_BOT_TOKEN", "OPENROUTER_API_KEY", "OWNER_TELEGRAM_ID"})

    def test_prompt_and_history_are_constructed(self):
        messages = _make_messages([{"role": "user", "content": "Salom"}], "uz")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["content"], "Salom")


if __name__ == "__main__":
    unittest.main()
