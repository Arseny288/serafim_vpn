from __future__ import annotations

from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict

from .db import Db
from .repo import UsersRepo, DepositsRepo
from .services import SubscriptionService, PaymentService
from .ui import UiService
from .xui import XuiPanel
from .config import Config


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, db: Db, settings, bot):
        self.db = db
        self.settings = settings
        self.bot = bot

    async def __call__(self, handler, event, data: Dict[str, Any]) -> Any:
        data["settings"] = self.settings

        async with self.db.sessionmaker() as s:
            users = UsersRepo(s)
            deposits = DepositsRepo(s)

            data["users"] = users
            data["deposits"] = deposits

            xui = XuiPanel(Config.XUI_URL, Config.XUI_USER, Config.XUI_PASS)

            data["subs"] = SubscriptionService(users, xui)
            data["pay"] = PaymentService(users, deposits)
            data["ui"] = UiService(self.bot, users)

            try:
                result = await handler(event, data)
                await s.commit()
                return result
            except Exception:
                await s.rollback()
                raise
