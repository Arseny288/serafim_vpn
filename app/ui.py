# app/ui.py
from __future__ import annotations

from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from .repo import UsersRepo
from .keyboards import main_kb, profile_kb


class UiService:
    def __init__(self, bot: Bot, users: UsersRepo):
        self.bot = bot
        self.users = users

    async def reset_menu(self, user_id: int, chat_id: int):
        """
        Всегда создаёт новое меню-сообщение (для /start).
        """
        await self.users.set_menu_message_id(user_id, None)
        msg = await self.bot.send_message(chat_id=chat_id, text="⚡️ Меню:")
        await self.users.set_menu_message_id(user_id, msg.message_id)
        # сразу покажем главное меню
        await self.show_main_menu(user_id, chat_id)

    async def ensure_menu_message(self, user_id: int, chat_id: int) -> int:
        """
        Гарантирует существование живого menu message.
        Если старое удалили (chat очистили) — создаёт новое автоматически.
        """
        msg_id = await self.users.get_menu_message_id(user_id)
        if msg_id:
            try:
                # тест-редактирование (если сообщение удалено — будет исключение)
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="⚡️ Меню (обновление)...",
                )
                return msg_id
            except Exception:
                # сообщение удалили/чат очистили → сбрасываем и создаём новое
                await self.users.set_menu_message_id(user_id, None)
                msg_id = None

        msg = await self.bot.send_message(chat_id=chat_id, text="⚡️ Меню:")
        await self.users.set_menu_message_id(user_id, msg.message_id)
        return msg.message_id

    async def render(
        self,
        user_id: int,
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ):
        msg_id = await self.ensure_menu_message(user_id, chat_id)
        parse_mode = "HTML" if "<code>" in text else None
        await self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )

    async def show_main_menu(self, user_id: int, chat_id: int):
        await self.render(user_id, chat_id, "⚡️ Меню:", main_kb())

    async def show_profile(self, user_id: int, chat_id: int):
        u = await self.users.get(user_id)
        if not u:
            return

        st = "🚫 BANNED" if u.is_banned else ("🟢 ACTIVE" if u.is_active else "🟠 PAUSED")
        dl = self._days_left(u.active_until)

        text = (
            f"👤 ID: <code>{u.user_id}</code>\n"
            f"💳 Balance: <code>{round(u.balance, 2)}</code>\n"
            f"📌 Status: {st}\n"
            f"⏳ Days left: <code>{dl}</code>\n"
            f"🗓 Until: <code>{u.active_until or '-'}</code>"
        )
        await self.render(user_id, chat_id, text, profile_kb(u.is_active, u.is_banned))

    def _days_left(self, active_until):
        if not active_until:
            return 0
        diff = (active_until - datetime.utcnow()).total_seconds()
        return max(0, int(diff // 86400))
