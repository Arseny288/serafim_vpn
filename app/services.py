from datetime import datetime, timedelta
import uuid

from .repo import UsersRepo, DepositsRepo
from .xui import XuiPanel
from .config import XuiConfig
from .utils.vless import build_vless_link


class SubscriptionService:
    def __init__(self, users: UsersRepo, xui: XuiPanel, xui_config: XuiConfig | None = None):
        self.users = users
        self.xui = xui
        self.xui_config = xui_config

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

    async def activate(self, tg_id: int, days: int = 30, settings=None):
        u = await self.users.get(tg_id)
        if not u:
            return

        # Check balance if settings provided
        if settings:
            required_balance = (settings.monthly_price_rub / 30) * days
            if u.balance < required_balance:
                raise RuntimeError(f"Insufficient balance. Required: {required_balance:.2f}, Available: {u.balance:.2f}")
            # Deduct balance
            await self.users.add_balance(tg_id, -required_balance)

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
                raise RuntimeError("xui login failed - check XUI credentials and connection")

            inbound_id = self.xui_config.inbound_id if self.xui_config else 2
            ok = self.xui.add_client(inbound_id, client)
            if not ok:
                raise RuntimeError(f"xui add_client failed - check XUI panel logs for inbound_id={inbound_id}")

            await self.users.set_vpn(tg_id, vpn_uuid, email)

        else:
            # если uuid уже есть — просто обновим expiry и включение
            if not self.xui.login():
                raise RuntimeError("xui login failed - check XUI credentials and connection")

            inbound_id = self.xui_config.inbound_id if self.xui_config else 2
            ok = self.xui.update_client(inbound_id, u.vpn_uuid, True, expiry_ms)
            if not ok:
                raise RuntimeError(f"xui update_client failed - check XUI panel logs for uuid={u.vpn_uuid}")

    async def pause(self, tg_id: int):
        u = await self.users.get(tg_id)
        if not u or not u.vpn_uuid:
            await self.users.set_active(tg_id, False)
            return

        if not self.xui.login():
            raise RuntimeError("xui login failed - check XUI credentials and connection")

        expiry_ms = int((u.active_until.timestamp() * 1000)) if u.active_until else 0
        inbound_id = self.xui_config.inbound_id if self.xui_config else 2
        ok = self.xui.update_client(inbound_id, u.vpn_uuid, False, expiry_ms)
        if not ok:
            raise RuntimeError(f"xui update_client failed - check XUI panel logs for uuid={u.vpn_uuid}")
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