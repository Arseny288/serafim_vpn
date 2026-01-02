from __future__ import annotations

from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict

from .db import Db
from .repo import UsersRepo, DepositsRepo
from .services import SubscriptionService, PaymentService
from .ui import UiService
from .xui import XuiPanel
from .config import load_xui_config


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

            xui_config = load_xui_config()
            xui = XuiPanel(xui_config.url, xui_config.username, xui_config.password)

            data["subs"] = SubscriptionService(users, xui, xui_config)
            data["xui_config"] = xui_config
            data["pay"] = PaymentService(users, deposits)
            data["ui"] = UiService(self.bot, users)

            try:
                result = await handler(event, data)
                await s.commit()
                return result
            except Exception:
                await s.rollback()
                raise
