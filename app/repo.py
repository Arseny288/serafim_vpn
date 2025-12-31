from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
from .models import User, DepositRequest

class UsersRepo:
    def __init__(self, s: AsyncSession):
        self.s = s

    async def get(self, user_id: int) -> User | None:
        res = await self.s.execute(select(User).where(User.user_id == user_id))
        return res.scalar_one_or_none()

    async def add_if_missing(self, user_id: int, username: str | None) -> User:
        u = await self.get(user_id)
        if u:
            # обновим username, если поменялся
            if username and u.username != username:
                u.username = username
            return u
        u = User(user_id=user_id, username=username)
        self.s.add(u)
        await self.s.flush()
        return u

    async def set_ban(self, user_id: int, banned: bool):
        await self.s.execute(update(User).where(User.user_id == user_id).values(is_banned=banned))

    async def add_balance(self, user_id: int, amount: float):
        await self.s.execute(update(User).where(User.user_id == user_id).values(balance=User.balance + amount))

    async def set_active(self, user_id: int, active: bool):
        await self.s.execute(update(User).where(User.user_id == user_id).values(is_active=active))

    async def set_key(self, user_id: int, key: str):
        await self.s.execute(update(User).where(User.user_id == user_id).values(vpn_key=key))

    async def extend_until(self, user_id: int, days: int):
        u = await self.get(user_id)
        base = u.active_until if u and u.active_until and u.active_until > datetime.utcnow() else datetime.utcnow()
        new_until = base + timedelta(days=days)
        await self.s.execute(update(User).where(User.user_id == user_id).values(active_until=new_until))

class DepositsRepo:
    def __init__(self, s: AsyncSession):
        self.s = s

    async def create(self, user_id: int, amount: float) -> DepositRequest:
        dr = DepositRequest(user_id=user_id, amount=amount, status="pending")
        self.s.add(dr)
        await self.s.flush()
        return dr

    async def get(self, dep_id: int) -> DepositRequest | None:
        res = await self.s.execute(select(DepositRequest).where(DepositRequest.id == dep_id))
        return res.scalar_one_or_none()

    async def set_status(self, dep_id: int, status: str):
        await self.s.execute(
            update(DepositRequest).where(DepositRequest.id == dep_id).values(status=status)
        )
