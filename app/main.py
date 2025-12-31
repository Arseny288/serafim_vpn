# app/main.py
import asyncio
from aiogram import Bot, Dispatcher

from .config import load_settings
from .db import Db
from .models import Base
from .handlers import router
from .middlewares import DbSessionMiddleware


async def create_tables(db: Db):
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    settings = load_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    db = Db(settings.db_dsn)
    if settings.db_dsn.startswith("sqlite"):
        await db.init_sqlite_pragmas()
    await create_tables(db)

    dp.update.outer_middleware(DbSessionMiddleware(db, settings, bot))

    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
