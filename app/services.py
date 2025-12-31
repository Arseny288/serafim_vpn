from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from .repo import UsersRepo, DepositsRepo
from .keyboards import main_kb, profile_kb

class KeyService:
    async def gen_key(self, user_id: int) -> str:
        # TODO: позже подключишь x-ui / панель генерации
        return f"vless://uuid-{user_id}@premium.node:443?security=reality&sni=google.com#FlashVPN_{user_id}"

class SubscriptionService:
    def __init__(self, users: UsersRepo, keysvc: KeyService):
        self.users = users
        self.keysvc = keysvc

    async def can_use(self, user_id: int) -> tuple[bool, str]:
        u = await self.users.get(user_id)
        if not u:
            return False, "no_user"
        if u.is_banned:
            return False, "banned"
        if not u.is_active:
            return False, "paused"
        if not u.active_until:
            return False, "no_until"
        if u.active_until < datetime.utcnow():
            return False, "expired"
        return True, "ok"

    async def activate(self, user_id: int, days: int):
        u = await self.users.get(user_id)
        if not u:
            return
        if not u.vpn_key:
            key = await self.keysvc.gen_key(user_id)
            await self.users.set_key(user_id, key)
        await self.users.set_active(user_id, True)
        await self.users.extend_until(user_id, days)

    async def pause(self, user_id: int):
        await self.users.set_active(user_id, False)

class PaymentService:
    def __init__(self, users: UsersRepo, deposits: DepositsRepo):
        self.users = users
        self.deposits = deposits

    async def create_deposit(self, user_id: int, amount: float) -> int:
        dr = await self.deposits.create(user_id, amount)
        return dr.id

    async def approve(self, dep_id: int):
        dr = await self.deposits.get(dep_id)
        if not dr or dr.status != "pending":
            return None
        await self.deposits.set_status(dep_id, "approved")
        await self.users.add_balance(dr.user_id, dr.amount)
        return dr

    async def reject(self, dep_id: int):
        dr = await self.deposits.get(dep_id)
        if not dr or dr.status != "pending":
            return None
        await self.deposits.set_status(dep_id, "rejected")
        return dr

# добавлено: UiService
class UiService:
    def __init__(self, bot: Bot, users: UsersRepo):
        self.bot = bot
        self.users = users

    async def ensure_menu_message(self, user_id: int, chat_id: int) -> int:
        msg_id = await self.users.get_menu_message_id(user_id)
        if msg_id:
            try:
                # проверка, что сообщение живое
                await self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="⚡️ Меню (обновление)...")
                return msg_id
            except:
                # если удалено или ошибка — сброс
                msg_id = None
        if not msg_id:
            msg = await self.bot.send_message(chat_id=chat_id, text="⚡️ Меню:")
            msg_id = msg.message_id
            await self.users.set_menu_message_id(user_id, msg_id)
        return msg_id

    async def render(self, user_id: int, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None):
        msg_id = await self.ensure_menu_message(user_id, chat_id)
        parse_mode = "HTML" if "<code>" in text else None
        await self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

    async def show_main_menu(self, user_id: int, chat_id: int):
        text = "⚡️ Меню:"
        kb = main_kb()
        await self.render(user_id, chat_id, text, kb)

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
        kb = profile_kb(u.is_active, u.is_banned)
        await self.render(user_id, chat_id, text, kb)

    def _days_left(self, active_until):
        if not active_until:
            return 0
        diff = (active_until - datetime.utcnow()).total_seconds()
        return max(0, int(diff // 86400))