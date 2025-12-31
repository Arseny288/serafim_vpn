import asyncio
from aiogram import Bot, Dispatcher
from sqlalchemy import text
from .config import load_settings
from .db import Db
from .models import Base
from .handlers import router
from .repo import UsersRepo, DepositsRepo
from .services import KeyService, SubscriptionService, PaymentService
#i
async def create_tables(db: Db):
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def main():
    settings = load_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    db = Db(settings.db_dsn)
    # SQLite анти-lock:
    if settings.db_dsn.startswith("sqlite"):
        await db.init_sqlite_pragmas()
    await create_tables(db)

    # Middleware: новая сессия на каждый update + прокидываем зависимости
    @dp.update.middleware()
    async def inject(handler, event, data):
        data["settings"] = settings
        async with db.sessionmaker() as s:
            data["users"] = UsersRepo(s)
            data["deposits"] = DepositsRepo(s)
            keysvc = KeyService()
            data["subs"] = SubscriptionService(data["users"], keysvc)
            data["pay"] = PaymentService(data["users"], data["deposits"])

            res = await handler(event, data)

            # commit если были изменения (безопасно: если ничего не менялось — ок)
            try:
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            return res

    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
