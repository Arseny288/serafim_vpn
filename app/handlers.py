# app/handlers.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder  # ✅ ВАЖНО

from .keyboards import main_kb, profile_kb, admin_deposit_kb
from .services import SubscriptionService, PaymentService
from .ui import UiService
from .repo import UsersRepo

router = Router()


@router.message(Command("start"))
async def start(m: Message, ui: UiService, users: UsersRepo):
    await users.add_if_missing(m.from_user.id, m.from_user.username)
    # ✅ всегда создаём новое меню, чтобы после очистки чата всё оживало
    await ui.reset_menu(m.from_user.id, m.chat.id)


@router.callback_query(F.data == "main_menu")
async def main_menu(cq: CallbackQuery, ui: UiService):
    await cq.answer()
    await ui.show_main_menu(cq.from_user.id, cq.message.chat.id)


@router.callback_query(F.data == "support")
async def support(cq: CallbackQuery, ui: UiService):
    await cq.answer()
    text = "🆘 Support: @admin_username"
    b = InlineKeyboardBuilder()
    b.button(text="Назад", callback_data="main_menu")
    await ui.render(cq.from_user.id, cq.message.chat.id, text, b.as_markup())


@router.callback_query(F.data == "connect")
async def connect(cq: CallbackQuery, ui: UiService):
    await cq.answer()
    text = (
        "📡 Инструкция по подключению:\n"
        "1. Скачайте приложение (V2Ray / etc.)\n"
        "2. Импортируйте ключ из профиля.\n"
        "3. Подключитесь."
    )
    b = InlineKeyboardBuilder()
    b.button(text="Назад", callback_data="main_menu")
    await ui.render(cq.from_user.id, cq.message.chat.id, text, b.as_markup())


@router.callback_query(F.data == "profile")
async def profile(cq: CallbackQuery, ui: UiService, users: UsersRepo):
    await cq.answer()
    await users.add_if_missing(cq.from_user.id, cq.from_user.username)
    await ui.show_profile(cq.from_user.id, cq.message.chat.id)


@router.callback_query(F.data == "topup")
async def topup(cq: CallbackQuery, ui: UiService):
    await cq.answer()
    text = "Введите сумму (число), например: 150\nКоманда: /dep 150"
    b = InlineKeyboardBuilder()
    b.button(text="Назад", callback_data="main_menu")
    await ui.render(cq.from_user.id, cq.message.chat.id, text, b.as_markup())


@router.message(Command("dep"))
async def dep_create(m: Message, pay: PaymentService, settings, ui: UiService):
    try:
        amount = float(m.text.split(maxsplit=1)[1])
    except Exception:
        await m.answer("Формат: /dep 150")
        return

    dep_id = await pay.create_deposit(m.from_user.id, amount)
    await m.answer("✅ Заявка создана. Ждите подтверждения.")
    try:
        await m.delete()
    except Exception:
        pass

    # админу
    try:
        await m.bot.send_message(
            settings.admin_id,
            f"💳 Deposit #{dep_id}\nUser: {m.from_user.id}\nAmount: {amount}",
            reply_markup=admin_deposit_kb(dep_id),
        )
    except Exception:
        pass

    await ui.show_main_menu(m.from_user.id, m.chat.id)
# ----------------- ADMIN ACTIONS -----------------

@router.callback_query(F.data.startswith("adm_dep_ok:"))
async def adm_ok(cq: CallbackQuery, pay: PaymentService, settings):
    # админ-check
    if cq.from_user.id != settings.admin_id:
        await cq.answer("Ты не админ", show_alert=True)
        return

    await cq.answer()
    dep_id = int(cq.data.split(":")[1])

    dr = await pay.approve(dep_id)
    if not dr:
        try:
            await cq.message.edit_text("⚠️ Already handled")
        except Exception:
            pass
        return

    # важно: не даём исключениям откатывать commit
    try:
        await cq.message.edit_text("✅ Approved")
    except Exception:
        pass

    try:
        await cq.bot.send_message(dr.user_id, f"✅ Оплата принята на {dr.amount}")
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_dep_no:"))
async def adm_no(cq: CallbackQuery, pay: PaymentService, settings):
    if cq.from_user.id != settings.admin_id:
        await cq.answer("Ты не админ", show_alert=True)
        return

    await cq.answer()
    dep_id = int(cq.data.split(":")[1])

    dr = await pay.reject(dep_id)
    if not dr:
        try:
            await cq.message.edit_text("⚠️ Already handled")
        except Exception:
            pass
        return

    try:
        await cq.message.edit_text("❌ Rejected")
    except Exception:
        pass

    try:
        await cq.bot.send_message(dr.user_id, "❌ Оплата отклонена")
    except Exception:
        pass
