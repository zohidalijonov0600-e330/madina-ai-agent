from __future__ import annotations

from madina.config import settings
from madina.db import init_db


def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing; add it to your .env file.")
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing; add it to your .env file.")
    init_db()
    import asyncio
    from madina.bot import main as _async_main

    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
