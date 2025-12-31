from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👤 Профиль", callback_data="profile")
    b.button(text="🚀 VPN / Подключение", callback_data="connect")
    b.button(text="💳 Пополнить", callback_data="topup")
    b.button(text="🆘 Support", callback_data="support")
    b.adjust(1)
    return b.as_markup()

def profile_kb(is_active: bool, is_banned: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_banned:
        b.button(text="🚫 Заблокирован", callback_data="noop")
    else:
        b.button(text=("⏸ Пауза" if is_active else "▶️ Активировать"), callback_data=("pause" if is_active else "activate"))
    b.button(text="🔑 Получить ключ", callback_data="get_key")
    b.button(text="🔙 Назад", callback_data="back")
    b.adjust(1)
    return b.as_markup()

def admin_deposit_kb(dep_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять", callback_data=f"adm_dep_ok:{dep_id}")
    b.button(text="❌ Отклонить", callback_data=f"adm_dep_no:{dep_id}")
    b.adjust(2)
    return b.as_markup()
