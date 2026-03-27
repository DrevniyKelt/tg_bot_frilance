from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import router
from app.core.config import get_settings
from app.db.session import close_engine, init_db


async def run_bot() -> None:
    settings = get_settings()
    if not settings.telegram.bot_token:
        raise RuntimeError("APP_TELEGRAM_BOT_TOKEN or telegram.bot_token must be configured to run the bot.")

    await init_db()
    bot = Bot(settings.telegram.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await close_engine()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
