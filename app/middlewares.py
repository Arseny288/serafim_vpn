# app/middlewares.py
from __future__ import annotations

from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict

from .db import Db
from .repo import UsersRepo, DepositsRepo
from .services import KeyService, SubscriptionService, PaymentService
from .ui import UiService


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, db: Db, settings, bot):
        self.db = db
        self.settings = settings
        self.bot = bot

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["settings"] = self.settings

        async with self.db.sessionmaker() as s:
            data["users"] = UsersRepo(s)
            data["deposits"] = DepositsRepo(s)

            keysvc = KeyService()
            data["subs"] = SubscriptionService(data["users"], keysvc)
            data["pay"] = PaymentService(data["users"], data["deposits"])
            data["ui"] = UiService(self.bot, data["users"])

            try:
                result = await handler(event, data)
                await s.commit()
                return result
            except Exception:
                await s.rollback()
                raise
