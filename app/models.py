from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, DateTime, Boolean, ForeignKey, func
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    active_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # старое поле можно оставить для совместимости
    vpn_key: Mapped[str | None] = mapped_column(String, nullable=True)

    # ✅ новые поля для реального x-ui клиента
    vpn_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vpn_email: Mapped[str | None] = mapped_column(String(128), nullable=True)

    menu_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class DepositRequest(Base):
    __tablename__ = "deposit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
