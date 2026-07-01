"""Subscription purchase wizard (PRO/MAX × 1/3/6/12 months).

Flow:
  /buy or menu:buy
    → choosing_plan → choosing_duration → asking_promo
    → [entering_promo] → entering_email → confirming_order
    → awaiting_screenshot → (admin review via review.py)
"""
import re
import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .. import storage
from ..config import (SHOP_PLANS, PAY_CARD_NUMBER, PAY_CARD_NAME,
                      ADMIN_CHAT_ID, OWNER_USERNAME, SITE_URL, SB_CONFIGURED)
from ..states import Purchase
from .. import keyboards as K
from .util import is_owner

router = Router()
log = logging.getLogger("aquality-bot.shop")

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(n: int) -> str:
    return f"{int(round(n)):,}".replace(",", " ") + " сум"


def _months_ru(m: int) -> str:
    return {1: "1 месяц", 3: "3 месяца", 6: "6 месяцев", 12: "12 месяцев"}[m]


def _duration_list(plan: str) -> str:
    p = SHOP_PLANS[plan]
    lines = []
    for m, d in p["durations"].items():
        tag = ""
        if d["disc"]:
            tag = f" (−{d['disc']}%)"
            if m == 12:
                tag += " 🔥"
        lines.append(f"• <b>{_months_ru(m)}</b> — {_fmt(d['price'])}{tag}")
    return "\n".join(lines)


async def _clear_state(state: FSMContext, user_id: int):
    lang = storage.get_user_lang(user_id) or "ru"
    await state.clear()
    await state.update_data(lang=lang)


# ── Entry point ───────────────────────────────────────────────────────────────

def _fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d.%m.%Y")
    except Exception:
        return iso[:10]


async def start_shop(target, state: FSMContext):
    """Works from both Message and the .message of a CallbackQuery."""
    user_id = target.from_user.id

    if SB_CONFIGURED:
        from .. import supabase_db as _sb
        sub = await _sb.get_active_sub(user_id)
        if sub:
            date_str = _fmt_date(sub.get("expires_at", ""))
            await target.answer(
                f"⚠️ Подписка уже активна до <b>{date_str}</b>.\n"
                "Для продления обратитесь к администратору."
            )
            return

    pending = storage.get_pending_order(user_id)
    if pending and pending["status"] in ("awaiting_screenshot", "under_review", "rejected"):
        oid_str = storage.order_id_str(pending["id"])
        if pending["status"] == "under_review":
            await target.answer(
                f"⏳ Заказ <b>{oid_str}</b> уже отправлен на проверку.\n"
                "Администратор проверит и напишет вам в ближайшие 30 минут."
            )
            return
        await target.answer(
            f"У вас есть незавершённый заказ <b>{oid_str}</b>.\n\n"
            "Продолжить или начать новый?",
            reply_markup=K.shop_resume_kb(oid_str, pending["id"])
        )
        return

    await state.set_state(Purchase.choosing_plan)
    await target.answer(
        "👋 <b>Подписка Aquality</b>\n\n"
        "Демо открыто всем. Полный расчёт — по подписке.\n\n"
        "Выберите тариф:",
        reply_markup=K.shop_plans_kb()
    )


@router.message(Command("buy"))
async def cmd_buy(message: Message, state: FSMContext):
    await start_shop(message, state)


@router.callback_query(F.data == "menu:buy")
async def cb_menu_buy(cb: CallbackQuery, state: FSMContext):
    await start_shop(cb.message, state)
    await cb.answer()


# ── Step 1: choose plan ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy:plan:"), StateFilter(Purchase.choosing_plan))
async def cb_choose_plan(cb: CallbackQuery, state: FSMContext):
    plan = cb.data.split(":")[-1]
    if plan not in SHOP_PLANS:
        return await cb.answer()
    await state.update_data(shop_plan=plan)
    await state.set_state(Purchase.choosing_duration)
    p = SHOP_PLANS[plan]
    await cb.message.edit_text(
        f"{p['emoji']} <b>{p['name_ru']}</b>\n\n"
        "Выберите срок подписки:\n\n"
        f"{_duration_list(plan)}",
        reply_markup=K.shop_duration_kb()
    )
    await cb.answer()


# ── Step 2: choose duration ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("buy:dur:"), StateFilter(Purchase.choosing_duration))
async def cb_choose_duration(cb: CallbackQuery, state: FSMContext):
    months = int(cb.data.split(":")[-1])
    if months not in (1, 3, 6, 12):
        return await cb.answer()
    await state.update_data(shop_months=months)
    await state.set_state(Purchase.asking_promo)
    await cb.message.edit_text(
        "🎟 У вас есть промокод?",
        reply_markup=K.shop_promo_kb()
    )
    await cb.answer()


# ── Step 3: promo toggle ──────────────────────────────────────────────────────

@router.callback_query(F.data == "buy:promo:yes",
                       StateFilter(Purchase.asking_promo, Purchase.entering_promo))
async def cb_promo_yes(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Purchase.entering_promo)
    await cb.message.edit_text(
        "Введите промокод одним сообщением:",
        reply_markup=K.shop_back_cancel_kb()
    )
    await cb.answer()


@router.callback_query(F.data == "buy:promo:no",
                       StateFilter(Purchase.asking_promo, Purchase.entering_promo))
async def cb_promo_no(cb: CallbackQuery, state: FSMContext):
    await state.update_data(shop_promo=None, shop_promo_disc=0)
    await state.set_state(Purchase.entering_email)
    await cb.message.edit_text(
        "📧 На какую почту оформить доступ?\n\n"
        "Введите email — на него будет привязана подписка.\n"
        "Покупаете в подарок? Укажите почту получателя.",
        reply_markup=K.shop_back_cancel_kb()
    )
    await cb.answer()


# ── Step 4: enter promo ───────────────────────────────────────────────────────

@router.message(StateFilter(Purchase.entering_promo))
async def handle_promo_input(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if SB_CONFIGURED:
        from .. import supabase_db as _sb
        res = await _sb.validate_promo(message.from_user.id, code)
    else:
        res = storage.validate_promo(code, message.from_user.id)

    if res["ok"]:
        data = await state.get_data()
        plan = data.get("shop_plan", "pro")
        restriction = res.get("plan_restriction")
        if restriction and restriction != plan:
            p = SHOP_PLANS[restriction]
            return await message.answer(
                f"⚠️ Промокод <b>{code}</b> действует только для тарифа "
                f"{p['emoji']} <b>{p['name_ru']}</b>.\n\n"
                "Нажмите ◀️ Назад, чтобы сменить тариф, или попробуйте другой код.",
                reply_markup=K.shop_promo_retry_kb()
            )
        disc = res["discount"]
        months = data.get("shop_months", 1)
        base = SHOP_PLANS[plan]["durations"][months]["price"]
        new_price = round(base * (1 - disc / 100))
        await state.update_data(shop_promo=code, shop_promo_disc=disc)
        await state.set_state(Purchase.entering_email)
        await message.answer(
            f"✅ Промокод <b>{code}</b> применён! Скидка −{disc}%.\n"
            f"Новая сумма: <b>{_fmt(new_price)}</b>\n\n"
            "📧 Теперь введите email для оформления доступа:",
            reply_markup=K.shop_back_cancel_kb()
        )
    else:
        reason = res.get("reason", "")
        msgs = {
            "already_used": "⚠️ Этот промокод уже был использован вами.",
            "exhausted":    "⚠️ Промокод исчерпан (лимит использований).",
        }
        err = msgs.get(reason, "⚠️ Промокод недействителен или истёк.")
        await message.answer(
            f"{err}\n\nПопробуйте другой или пропустите этот шаг.",
            reply_markup=K.shop_promo_retry_kb()
        )


# ── Step 5: enter email ───────────────────────────────────────────────────────

@router.message(StateFilter(Purchase.entering_email))
async def handle_email_input(message: Message, state: FSMContext):
    email = message.text.strip()
    if not _EMAIL_RE.match(email):
        return await message.answer(
            "⚠️ Похоже, email введён с ошибкой (пример: name@mail.com).\n"
            "Попробуйте ещё раз.",
            reply_markup=K.shop_back_cancel_kb()
        )

    data = await state.get_data()
    plan     = data.get("shop_plan", "pro")
    months   = data.get("shop_months", 1)
    promo    = data.get("shop_promo")
    promo_d  = data.get("shop_promo_disc", 0) or 0

    dur        = SHOP_PLANS[plan]["durations"][months]
    base_price = dur["price"]
    final      = round(base_price * (1 - promo_d / 100))

    order_id = storage.create_order(
        tg_user_id=message.from_user.id,
        username=message.from_user.username or "",
        plan=plan, months=months,
        base_price=base_price, promo_code=promo,
        promo_disc=promo_d, final_price=final,
        email=email.lower(),
    )
    oid_str = storage.order_id_str(order_id)
    await state.update_data(shop_email=email.lower(), shop_order_id=order_id)
    await state.set_state(Purchase.confirming_order)

    p = SHOP_PLANS[plan]
    dur_tag  = f" (−{dur['disc']}% за срок)" if dur["disc"] else ""
    promo_ln = f"\n• Промокод: <b>{promo}</b> (−{promo_d}%)" if promo else ""

    await message.answer(
        f"📋 <b>Проверьте заказ {oid_str}</b>\n\n"
        f"• Тариф: <b>{p['emoji']} {p['name_ru']}</b>\n"
        f"• Срок: <b>{_months_ru(months)}</b>{dur_tag}\n"
        f"• Email: <b>{email.lower()}</b>{promo_ln}\n"
        "─────────────────\n"
        f"💰 <b>Итого к оплате: {_fmt(final)}</b>\n\n"
        "Всё верно?",
        reply_markup=K.shop_confirm_kb()
    )


# ── Step 6: confirm order ─────────────────────────────────────────────────────

@router.callback_query(F.data == "buy:confirm", StateFilter(Purchase.confirming_order))
async def cb_confirm(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("shop_order_id")
    if not order_id:
        return await cb.answer("Заказ не найден.", show_alert=True)
    storage.update_order(order_id, status="awaiting_payment")
    await _show_payment(cb.message, order_id)
    await state.set_state(Purchase.awaiting_screenshot)
    await cb.answer()


@router.callback_query(F.data == "buy:edit", StateFilter(Purchase.confirming_order))
async def cb_edit(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("shop_order_id")
    if order_id:
        storage.update_order(order_id, status="cancelled")
    await _clear_state(state, cb.from_user.id)
    await state.set_state(Purchase.choosing_plan)
    await cb.message.edit_text("Выберите тариф:", reply_markup=K.shop_plans_kb())
    await cb.answer()


def _payment_text(order: dict, oid_str: str) -> str:
    card_ln = ""
    if PAY_CARD_NUMBER:
        card_ln = f"\n<code>{PAY_CARD_NUMBER}</code>"
        if PAY_CARD_NAME:
            card_ln += f"\nПолучатель: <b>{PAY_CARD_NAME}</b>"
    return (
        f"💳 <b>Оплата заказа {oid_str} — {_fmt(order['final_price'])}</b>\n\n"
        f"Переведите сумму на карту:{card_ln}\n\n"
        f"❗️ Важно: в комментарии к переводу укажите\n"
        f"номер заказа — <b>{oid_str}</b>\n\n"
        "После перевода пришлите сюда скриншот чека 📸"
    )


async def _show_payment(message, order_id: int):
    order   = storage.get_order(order_id)
    oid_str = storage.order_id_str(order_id)
    try:
        await message.edit_text(_payment_text(order, oid_str),
                                reply_markup=K.shop_cancel_kb())
    except Exception:
        await message.answer(_payment_text(order, oid_str),
                             reply_markup=K.shop_cancel_kb())


# ── Step 7: screenshot ────────────────────────────────────────────────────────

@router.message(StateFilter(Purchase.awaiting_screenshot), F.photo | F.document)
async def handle_screenshot(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("shop_order_id")
    if not order_id:
        return

    file_id = (message.photo[-1].file_id if message.photo
               else message.document.file_id)
    storage.update_order(order_id, status="under_review", screenshot_id=file_id)
    oid_str = storage.order_id_str(order_id)

    await message.answer(
        f"✅ Скриншот получен! Заказ <b>{oid_str}</b> передан на проверку.\n\n"
        "⏱ Обычно проверка занимает до 30 минут в рабочее время (9:00–21:00).\n\n"
        "Как только оплата подтвердится — я напишу сюда и открою доступ. "
        "Ждать в чате не обязательно."
    )
    await _notify_admin(message, order_id, file_id)
    await _clear_state(state, message.from_user.id)


@router.message(StateFilter(Purchase.awaiting_screenshot))
async def handle_not_screenshot(message: Message, state: FSMContext):
    await message.answer(
        "📸 Пришлите, пожалуйста, именно скриншот или фото чека.\n\n"
        "Нажмите 📎 → Фото или Файл.",
        reply_markup=K.shop_cancel_kb()
    )


async def _notify_admin(message: Message, order_id: int, file_id: str):
    if not ADMIN_CHAT_ID:
        return
    order   = storage.get_order(order_id)
    oid_str = storage.order_id_str(order_id)
    user    = message.from_user
    p       = SHOP_PLANS.get(order["plan"], {})
    uname   = f"@{user.username}" if user.username else f"id{user.id}"
    promo_ln = (f"\n🎟 Промокод: {order['promo_code']} (−{order['promo_disc']}%)"
                if order.get("promo_code") else "")

    from datetime import datetime
    now = datetime.now().strftime("%d.%m %H:%M")
    caption = (
        f"🔔 <b>Новый заказ на проверку {oid_str}</b>\n\n"
        f"👤 Клиент: {uname} (ID <code>{user.id}</code>)\n"
        f"🔹 Тариф: {p.get('emoji','')} {p.get('name_ru', order['plan'])}, "
        f"{order['months']} мес.\n"
        f"💰 К оплате: <b>{_fmt(order['final_price'])}</b>\n"
        f"📧 Email: <code>{order['email']}</code>{promo_ln}\n"
        f"🕐 Скриншот прислан: {now}"
    )
    kb = K.admin_review_kb(order_id)
    try:
        await message.bot.send_photo(ADMIN_CHAT_ID, photo=file_id,
                                     caption=caption, reply_markup=kb)
    except Exception:
        try:
            await message.bot.send_message(ADMIN_CHAT_ID, caption, reply_markup=kb)
        except Exception as e:
            log.error("Admin notify failed for order %s: %s", order_id, e)


# ── Cancel / back / resume ────────────────────────────────────────────────────

@router.callback_query(F.data == "buy:cancel")
async def cb_cancel(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("shop_order_id")
    if order_id:
        o = storage.get_order(order_id)
        if o and o["status"] in ("draft", "awaiting_payment"):
            storage.update_order(order_id, status="cancelled")
    await _clear_state(state, cb.from_user.id)
    try:
        await cb.message.edit_text("Заказ отменён. Для нового заказа — /buy")
    except Exception:
        await cb.message.answer("Заказ отменён. Для нового заказа — /buy")
    await cb.answer()


@router.callback_query(F.data == "buy:back")
async def cb_back(cb: CallbackQuery, state: FSMContext):
    current = await state.get_state()
    data    = await state.get_data()
    plan    = data.get("shop_plan", "pro")

    if current == Purchase.choosing_duration:
        await state.set_state(Purchase.choosing_plan)
        await cb.message.edit_text("Выберите тариф:", reply_markup=K.shop_plans_kb())
    elif current == Purchase.asking_promo:
        await state.set_state(Purchase.choosing_duration)
        p = SHOP_PLANS[plan]
        await cb.message.edit_text(
            f"{p['emoji']} <b>{p['name_ru']}</b>\n\n"
            f"Выберите срок:\n\n{_duration_list(plan)}",
            reply_markup=K.shop_duration_kb()
        )
    elif current in (Purchase.entering_promo, Purchase.entering_email):
        await state.set_state(Purchase.asking_promo)
        await cb.message.edit_text("🎟 У вас есть промокод?",
                                   reply_markup=K.shop_promo_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("buy:resume:"))
async def cb_resume(cb: CallbackQuery, state: FSMContext):
    order_id = int(cb.data.split(":")[-1])
    order = storage.get_order(order_id)
    if not order or order["tg_user_id"] != cb.from_user.id:
        return await cb.answer("Заказ не найден.", show_alert=True)

    if order["status"] == "under_review":
        return await cb.answer("Заказ уже на проверке — ждите ответа.", show_alert=True)

    storage.update_order(order_id, status="awaiting_payment")
    await state.update_data(shop_order_id=order_id, shop_plan=order["plan"],
                            shop_months=order["months"], shop_email=order["email"])
    await state.set_state(Purchase.awaiting_screenshot)
    await _show_payment(cb.message, order_id)
    await cb.answer()


@router.callback_query(F.data == "buy:new")
async def cb_new_order(cb: CallbackQuery, state: FSMContext):
    await _clear_state(state, cb.from_user.id)
    await start_shop(cb.message, state)
    await cb.answer()


# ── /status command ───────────────────────────────────────────────────────────

_STATUS_LABELS = {
    "draft":               "Черновик",
    "awaiting_payment":    "⏳ Ожидает оплаты",
    "awaiting_screenshot": "⏳ Ожидает скриншота чека",
    "under_review":        "🔎 На проверке (до 30 мин)",
    "rejected":            "⚠️ Требуется повторный скриншот",
    "completed":           "✅ Подтверждён",
    "cancelled":           "❌ Отменён",
}


async def send_status(target, uid):
    """Render the caller's current order status. `target` is the user-facing chat."""
    order = storage.get_pending_order(uid)
    if not order:
        return await target.answer(
            "📋 Активных заказов нет.\n\n🛒 «Купить подписку» — оформить новый.",
            reply_markup=K.back_menu_kb("ru")
        )
    oid_str = storage.order_id_str(order["id"])
    p = SHOP_PLANS.get(order["plan"], {})
    await target.answer(
        f"📋 <b>Заказ {oid_str}</b>\n\n"
        f"Статус: {_STATUS_LABELS.get(order['status'], order['status'])}\n"
        f"Тариф: {p.get('emoji','')} {p.get('name_ru', order['plan'].upper())}, "
        f"{_months_ru(order['months'])}\n"
        f"Email: <code>{order['email']}</code>\n"
        f"К оплате: {_fmt(order['final_price'])}",
        reply_markup=K.back_menu_kb("ru")
    )


@router.message(Command("status"))
async def cmd_status(message: Message, state: FSMContext):
    await send_status(message, message.from_user.id)


@router.callback_query(F.data == "menu:status")
async def cb_status(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await send_status(cb.message, cb.from_user.id)
