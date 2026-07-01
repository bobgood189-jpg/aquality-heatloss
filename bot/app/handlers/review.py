"""Admin review callbacks for subscription orders.

Callback data format:
  review:ok:<order_id>       — confirm order, activate sub
  review:nok:<order_id>      — show rejection reason menu
  review:rej:<order_id>:<r>  — reject with reason code r
"""
import time
import logging
from datetime import date, timedelta

from aiogram import Router, F
from aiogram.types import CallbackQuery

from .. import storage
from ..config import SHOP_PLANS, SB_CONFIGURED, SITE_URL, OWNER_USERNAME
from .. import keyboards as K
from .util import is_owner

router = Router()
log = logging.getLogger("aquality-bot.review")

_REASONS = {
    "sum":    "Сумма не совпадает — нужна точная сумма из заказа",
    "norecv": "Платёж ещё не поступил на счёт",
    "bad":    "На скриншоте не видно суммы или даты",
    "other":  "Другая причина — свяжитесь с администратором",
}


def _fmt(n: int) -> str:
    return f"{int(round(n)):,}".replace(",", " ") + " сум"


def _guard(cb: CallbackQuery) -> bool:
    if not is_owner(cb.from_user):
        cb.answer("Только для администратора.", show_alert=True)
        return False
    return True


# ── Confirm ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("review:ok:"))
async def cb_review_ok(cb: CallbackQuery):
    if not is_owner(cb.from_user):
        return await cb.answer("Только для администратора.", show_alert=True)

    order_id = int(cb.data.split(":")[-1])
    order = storage.get_order(order_id)
    if not order:
        return await cb.answer("Заказ не найден.", show_alert=True)
    if order["status"] == "completed":
        return await cb.answer("Уже подтверждён.", show_alert=True)

    oid_str = storage.order_id_str(order_id)

    plan     = order["plan"]
    months   = order["months"]
    days     = SHOP_PLANS[plan]["durations"][months]["days"]
    tg_id    = order["tg_user_id"]
    p        = SHOP_PLANS[plan]
    plan_id  = f"{plan}_m{months}"   # canonical id matching site's AQ_PLANS

    activated = False
    if SB_CONFIGURED:
        from .. import supabase_db as _sb
        res = await _sb.activate_sub(tg_id, plan_id,
                                     amount=order["final_price"],
                                     promo=order.get("promo_code"),
                                     source="screenshot",
                                     months=months,
                                     email=order["email"])
        activated = bool(res.get("ok"))
        if activated and res.get("sub_id"):
            await _sb.set_just_activated(str(res["sub_id"]))
        elif not activated:
            log.error("Activation failed for order %s: %s", order_id, res.get("reason"))
    else:
        storage.activate_sub(tg_id, plan, days,
                             amount=order["final_price"],
                             promo=order.get("promo_code"),
                             source="screenshot")
        activated = True

    if not activated:
        # Оплата подтверждена админом, но активация подписки не удалась —
        # НЕ поздравляем клиента (иначе он решит, что доступ уже открыт).
        storage.update_order(order_id, status="under_review")
        suffix = f"\n\n⚠️ <b>ОШИБКА АКТИВАЦИИ</b> {oid_str}: {res.get('reason', 'unknown')}"
        try:
            old = cb.message.caption or ""
            await cb.message.edit_caption(old + suffix, reply_markup=K.admin_review_kb(order_id))
        except Exception:
            try:
                await cb.message.edit_text(
                    (cb.message.text or oid_str) + suffix, reply_markup=K.admin_review_kb(order_id))
            except Exception:
                pass
        return await cb.answer(
            f"⚠️ Оплата принята, но активация не удалась ({res.get('reason', 'unknown')}). "
            "Проверьте привязку аккаунта клиента к сайту.", show_alert=True)

    storage.update_order(order_id, status="completed", confirmed_ts=int(time.time()))

    expires_str = (date.today() + timedelta(days=days)).strftime("%d.%m.%Y")
    plan_label  = f"{p['emoji']} {p['name_ru']}"

    try:
        await cb.bot.send_message(
            tg_id,
            f"🎉 <b>Оплата подтверждена!</b> Тариф {plan_label} "
            f"на {months} мес. активирован.\n\n"
            f"🔓 Доступ открыт для: <code>{order['email']}</code>\n"
            f"📅 Действует до: <b>{expires_str}</b>\n\n"
            "Как начать:\n"
            f"1️⃣ Зайдите на сайт: {SITE_URL}\n"
            f"2️⃣ Войдите через указанную почту\n"
            f"3️⃣ Готово — все функции {p['name_ru']} доступны!\n\n"
            "Спасибо, что выбрали Aquality! 💙"
        )
    except Exception as e:
        log.warning("Client notify failed for order %s: %s", order_id, e)

    suffix = f"\n\n✅ <b>ПОДТВЕРЖДЁН</b> {oid_str} → {expires_str}"
    try:
        old = cb.message.caption or ""
        await cb.message.edit_caption(old + suffix, reply_markup=None)
    except Exception:
        try:
            await cb.message.edit_text(
                (cb.message.text or oid_str) + suffix, reply_markup=None)
        except Exception:
            pass

    await cb.answer(f"✅ {oid_str} подтверждён, доступ выдан.")


# ── Reject (step 1: choose reason) ───────────────────────────────────────────

@router.callback_query(F.data.startswith("review:nok:"))
async def cb_review_nok(cb: CallbackQuery):
    if not is_owner(cb.from_user):
        return await cb.answer("Только для администратора.", show_alert=True)
    order_id = int(cb.data.split(":")[-1])
    try:
        await cb.message.edit_reply_markup(
            reply_markup=K.admin_reject_reasons_kb(order_id)
        )
    except Exception:
        pass
    await cb.answer()


# ── Reject (step 2: confirmed reason) ────────────────────────────────────────

@router.callback_query(F.data.startswith("review:rej:"))
async def cb_review_reject(cb: CallbackQuery):
    if not is_owner(cb.from_user):
        return await cb.answer("Только для администратора.", show_alert=True)

    parts       = cb.data.split(":")
    order_id    = int(parts[2])
    reason_code = parts[3] if len(parts) > 3 else "other"
    reason_text = _REASONS.get(reason_code, _REASONS["other"])

    order = storage.get_order(order_id)
    if not order:
        return await cb.answer("Заказ не найден.", show_alert=True)
    if order["status"] in ("completed", "rejected"):
        return await cb.answer("Заказ уже обработан.", show_alert=True)

    storage.update_order(order_id, status="rejected", reject_reason=reason_text)
    oid_str = storage.order_id_str(order_id)
    tg_id   = order["tg_user_id"]

    admin_contact = f"@{OWNER_USERNAME}" if OWNER_USERNAME else "администратору"
    try:
        await cb.bot.send_message(
            tg_id,
            f"⚠️ По заказу <b>{oid_str}</b> пока не удалось подтвердить оплату.\n\n"
            f"Возможная причина: <b>{reason_text}</b>\n\n"
            "Что делать:\n"
            "🔄 Проверьте перевод и пришлите корректный скриншот\n"
            f"💬 Или напишите {admin_contact}\n\n"
            "Заказ сохранён — заново ничего вводить не нужно.",
            reply_markup=K.shop_resume_kb(oid_str, order_id)
        )
    except Exception as e:
        log.warning("Rejection notify failed for order %s: %s", order_id, e)

    suffix = f"\n\n❌ <b>ОТКЛОНЁН</b> {oid_str}: {reason_text}"
    try:
        old = cb.message.caption or ""
        await cb.message.edit_caption(old + suffix, reply_markup=None)
    except Exception:
        try:
            await cb.message.edit_text(
                (cb.message.text or oid_str) + suffix, reply_markup=None)
        except Exception:
            pass

    await cb.answer(f"❌ {oid_str} отклонён.")
