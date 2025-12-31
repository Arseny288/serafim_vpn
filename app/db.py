from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

class Db:
    def __init__(self, dsn: str):
        self.engine = create_async_engine(
            dsn,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": 30},  # ждём освобождения файла
        )
        self.sessionmaker = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

    async def init_sqlite_pragmas(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            await conn.execute(text("PRAGMA busy_timeout=30000;"))

    async def dispose(self):
        await self.engine.dispose()
