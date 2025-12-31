from datetime import datetime
from .repo import UsersRepo, DepositsRepo

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
