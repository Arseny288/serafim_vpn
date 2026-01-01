# app/handlers.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder  # ✅ ВАЖНО
from .services import SubscriptionService, PaymentService
from .keyboards import main_kb, profile_kb, admin_deposit_kb
from .ui import UiService
from .repo import UsersRepo
from app.config import Config
from app.utils.vless import build_vless_link

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

@router.callback_query(F.data == "activate")
async def activate(cq: CallbackQuery, ui: UiService, subs: SubscriptionService):
    await cq.answer()
    try:
        await subs.activate(cq.from_user.id, days=30)
        await ui.show_profile(cq.from_user.id, cq.message.chat.id)
    except Exception as e:
        error_msg = str(e)
        await cq.answer(f"Ошибка активации: {error_msg}", show_alert=True)
        # Still show profile even if activation failed
        await ui.show_profile(cq.from_user.id, cq.message.chat.id)


@router.callback_query(F.data == "pause")
async def pause(cq: CallbackQuery, ui: UiService, subs: SubscriptionService):
    await cq.answer()
    await subs.pause(cq.from_user.id)
    await ui.show_profile(cq.from_user.id, cq.message.chat.id)


@router.callback_query(F.data == "get_key")
async def get_key(cq: CallbackQuery, ui: UiService, users: UsersRepo, subs: SubscriptionService):
    await cq.answer()

    ok, reason = await subs.can_use(cq.from_user.id)
    if not ok:
        msg = {
            "paused": "Профиль на паузе — нажмите «Активировать».",
            "expired": "Подписка истекла — пополните и активируйте.",
            "no_until": "Подписка не активирована.",
            "banned": "Аккаунт заблокирован.",
            "no_user": "Пользователь не найден.",
        }.get(reason, "Недоступно.")
        await cq.answer(msg, show_alert=True)
        return

    u = await users.get(cq.from_user.id)
    if not u or not u.vpn_uuid or not u.vpn_email:
        await cq.answer("Ключ ещё не создан. Нажмите «Активировать».", show_alert=True)
        return

    link = build_vless_link(vpn_uuid=u.vpn_uuid, email=u.vpn_email)

    text = (
        "🔑 <b>Ваш VPN-ключ</b>\n\n"
        f"<code>{link}</code>\n\n"
        "⚠️ Не делитесь ключом. Он персональный.\n"
        "⚠️ Работает только при активной подписке"
    )

    await ui.render(
        cq.from_user.id,
        cq.message.chat.id,
        text,
        reply_markup=profile_kb(u.is_active, u.is_banned),
    )
