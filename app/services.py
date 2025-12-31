from datetime import datetime, timedelta
import uuid

from .repo import UsersRepo, DepositsRepo
from .xui import XuiPanel
from .config import Config
from .utils.vless import build_vless_link

class KeyService:
    async def gen_key(self, user_id: int) -> str:
        # TODO: позже подключишь x-ui / панель генерации
        return f"vless://uuid-{user_id}@premium.node:443?security=reality&sni=google.com#FlashVPN_{user_id}"

class SubscriptionService:
    def __init__(self, users: UsersRepo, xui: XuiPanel):
        self.users = users
        self.xui = xui

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

    async def activate(self, tg_id: int, days: int = 30):
        u = await self.users.get(tg_id)
        if not u:
            return

        # всегда делаем пользователя активным и продлеваем
        await self.users.set_active(tg_id, True)
        await self.users.extend_until(tg_id, days)

        u = await self.users.get(tg_id)
        expires = u.active_until or (datetime.utcnow() + timedelta(days=days))
        expiry_ms = int(expires.timestamp() * 1000)

        # если нет vpn_uuid — создаём клиента в панели
        if not u.vpn_uuid:
            vpn_uuid = str(uuid.uuid4())
            email = f"tg_{tg_id}"

            client = {
                "id": vpn_uuid,
                "email": email,
                "flow": "xtls-rprx-vision",
                "limitIp": 1,
                "totalGB": 0,
                "expiryTime": expiry_ms,
                "enable": True,
            }

            # логинимся и добавляем
            if not self.xui.login():
                raise RuntimeError("xui login failed")

            ok = self.xui.add_client(Config.INBOUND_ID, client)
            if not ok:
                raise RuntimeError("xui add_client failed")

            await self.users.set_vpn(tg_id, vpn_uuid, email)

        else:
            # если uuid уже есть — просто обновим expiry и включение
            if not self.xui.login():
                raise RuntimeError("xui login failed")

            self.xui.update_client(Config.INBOUND_ID, u.vpn_uuid, True, expiry_ms)

    async def pause(self, tg_id: int):
        u = await self.users.get(tg_id)
        if not u or not u.vpn_uuid:
            await self.users.set_active(tg_id, False)
            return

        if not self.xui.login():
            raise RuntimeError("xui login failed")

        expiry_ms = int((u.active_until.timestamp() * 1000)) if u.active_until else 0
        self.xui.update_client(Config.INBOUND_ID, u.vpn_uuid, False, expiry_ms)
        await self.users.set_active(tg_id, False)


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