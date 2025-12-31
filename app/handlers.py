from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from datetime import datetime
from .keyboards import main_kb, profile_kb, admin_deposit_kb
from .services import SubscriptionService, PaymentService
from .repo import UsersRepo, DepositsRepo

router = Router()

def days_left(active_until):
    if not active_until:
        return 0
    diff = (active_until - datetime.utcnow()).total_seconds()
    return max(0, int(diff // 86400))

@router.message(Command("start"))
async def start(m: Message, users: UsersRepo):
    await users.add_if_missing(m.from_user.id, m.from_user.username)
    await m.answer("⚡️ Меню:", reply_markup=main_kb())

@router.callback_query(F.data == "support")
async def support(cq: CallbackQuery):
    await cq.answer()
    await cq.message.answer("🆘 Support: @admin_username")

@router.callback_query(F.data == "profile")
async def profile(cq: CallbackQuery, users: UsersRepo):
    await cq.answer()
    u = await users.add_if_missing(cq.from_user.id, cq.from_user.username)

    st = "🚫 BANNED" if u.is_banned else ("🟢 ACTIVE" if u.is_active else "🟠 PAUSED")
    dl = days_left(u.active_until)

    text = (
        f"👤 ID: <code>{u.user_id}</code>\n"
        f"💳 Balance: <code>{round(u.balance,2)}</code>\n"
        f"📌 Status: {st}\n"
        f"⏳ Days left: <code>{dl}</code>\n"
        f"🗓 Until: <code>{u.active_until or '-'}</code>"
    )
    await cq.message.answer(text, reply_markup=profile_kb(u.is_active, u.is_banned), parse_mode="HTML")

@router.callback_query(F.data == "get_key")
async def get_key(cq: CallbackQuery, users: UsersRepo, subs: SubscriptionService):
    await cq.answer()
    ok, reason = await subs.can_use(cq.from_user.id)
    if not ok:
        await cq.message.answer(f"⚠️ Нет доступа: <code>{reason}</code>", parse_mode="HTML")
        return
    u = await users.get(cq.from_user.id)
    await cq.message.answer(f"🔑 Ваш ключ:\n<code>{u.vpn_key}</code>", parse_mode="HTML")

@router.callback_query(F.data == "activate")
async def activate(cq: CallbackQuery, users: UsersRepo, subs: SubscriptionService):
    await cq.answer()
    u = await users.get(cq.from_user.id)
    if not u or u.is_banned:
        return

    # простой расчёт: сколько дней купить за баланс
    # (позже можно сделать тарифы/месяц)
    if u.balance <= 0:
        await cq.message.answer("⚠️ Баланс 0. Сначала пополни.")
        return

    daily_price = 5.0  # поставь из settings если хочешь
    days = int(u.balance // daily_price)
    if days <= 0:
        await cq.message.answer("⚠️ Недостаточно средств на 1 день.")
        return

    # списываем сразу за days (минимально честно)
    await users.add_balance(u.user_id, -days * daily_price)
    await subs.activate(u.user_id, days)
    await cq.message.answer(f"✅ Активировано на {days} дней. Открой профиль заново.")

@router.callback_query(F.data == "pause")
async def pause(cq: CallbackQuery, subs: SubscriptionService):
    await cq.answer()
    await subs.pause(cq.from_user.id)
    await cq.message.answer("⏸ Поставлено на паузу. Открой профиль заново.")

# ----------------- TOPUP (очень простой) -----------------
@router.callback_query(F.data == "topup")
async def topup(cq: CallbackQuery):
    await cq.answer()
    await cq.message.answer("Введите сумму (число), например: 150\nКоманда: /dep 150")

@router.message(Command("dep"))
async def dep_create(m: Message, pay: PaymentService, settings):
    try:
        amount = float(m.text.split(maxsplit=1)[1])
    except Exception:
        await m.answer("Формат: /dep 150")
        return

    dep_id = await pay.create_deposit(m.from_user.id, amount)
    await m.answer("✅ Заявка создана. Ждите подтверждения.")

    # админу
    try:
        await m.bot.send_message(
            settings.admin_id,
            f"💳 Deposit #{dep_id}\nUser: {m.from_user.id}\nAmount: {amount}",
            reply_markup=admin_deposit_kb(dep_id),
        )
    except Exception:
        # если админ не нажал /start — будет chat not found, не падаем
        pass

# ----------------- ADMIN ACTIONS -----------------
@router.callback_query(F.data.startswith("adm_dep_ok:"))
async def adm_ok(cq: CallbackQuery, pay: PaymentService, settings):
    await cq.answer()
    if cq.from_user.id != settings.admin_id:
        return
    dep_id = int(cq.data.split(":")[1])
    dr = await pay.approve(dep_id)
    await cq.message.edit_text("✅ Approved" if dr else "⚠️ Already handled")

@router.callback_query(F.data.startswith("adm_dep_no:"))
async def adm_no(cq: CallbackQuery, pay: PaymentService, settings):
    await cq.answer()
    if cq.from_user.id != settings.admin_id:
        return
    dep_id = int(cq.data.split(":")[1])
    dr = await pay.reject(dep_id)
    await cq.message.edit_text("❌ Rejected" if dr else "⚠️ Already handled")

@router.message(Command("ban"))
async def ban(m: Message, users: UsersRepo, settings):
    if m.from_user.id != settings.admin_id:
        return
    parts = m.text.split()
    if len(parts) != 2:
        await m.answer("Формат: /ban USER_ID")
        return
    uid = int(parts[1])
    await users.set_ban(uid, True)
    await m.answer(f"🚫 Banned {uid}")

@router.message(Command("unban"))
async def unban(m: Message, users: UsersRepo, settings):
    if m.from_user.id != settings.admin_id:
        return
    parts = m.text.split()
    if len(parts) != 2:
        await m.answer("Формат: /unban USER_ID")
        return
    uid = int(parts[1])
    await users.set_ban(uid, False)
    await m.answer(f"✅ Unbanned {uid}")
