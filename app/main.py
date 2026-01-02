# app/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher

from .config import load_settings, load_xui_config
from .db import Db
from .models import Base
from .handlers import router
from .middlewares import DbSessionMiddleware
from .expire_worker import expire_worker
from .repo import UsersRepo, DepositsRepo
from .xui import XuiPanel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

    # Start expire worker in background
    xui_config = load_xui_config()
    xui = XuiPanel(xui_config.url, xui_config.username, xui_config.password)
    
    async def run_expire_worker():
        while True:
            try:
                async with db.sessionmaker() as s:
                    users = UsersRepo(s)
                    expired = await users.get_expired_active()
                    for u in expired:
                        try:
                            if not xui.login():
                                logger.error(f"XUI login failed when disabling expired user {u.user_id}")
                                continue
                            
                            expiry_ms = int(u.active_until.timestamp() * 1000) if u.active_until else 0
                            ok = xui.update_client(xui_config.inbound_id, u.vpn_uuid, False, expiry_ms)
                            if not ok:
                                logger.error(f"Failed to disable client for expired user {u.user_id}")
                            else:
                                await users.set_active(u.user_id, False)
                                await s.commit()
                                logger.info(f"Disabled expired subscription for user {u.user_id}")
                        except Exception as e:
                            logger.error(f"Error processing expired user {u.user_id}: {e}")
                            await s.rollback()
            except Exception as e:
                logger.error(f"Error in expire_worker: {e}")
            await asyncio.sleep(60)
    
    # Start expire worker as background task
    asyncio.create_task(run_expire_worker())
    logger.info("Expire worker started")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
