import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import BOT_TOKEN
from app.logger import logger
from app.db.session import init_db
from app.handlers import user as user_handlers
from app.handlers import admin as admin_handlers


async def main():
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

