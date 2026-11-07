from __future__ import annotations

import logging

from madina.bot import build_application
from madina.config import settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    missing = settings.validate()
    if missing:
        raise SystemExit(
            "Quyidagi sozlamalar .env faylida to'ldirilmagan: " + ", ".join(missing)
        )
    # run_polling handles Telegram initialization, polling, shutdown and restart cleanup.
    build_application().run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
