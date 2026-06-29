"""Owner-only panel: leads, funnel stats, broadcast. Gated to @ibrokh1movv7
(by username) or OWNER_ID."""
import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from .. import storage
from .util import is_owner

router = Router()

FUNNEL = [("calc_start", "Начато расчётов"), ("calc_complete", "Завершено расчётов"),
          ("demo_run", "Демо-запусков"), ("lead_sent", "Заявок отправлено")]


def _admin_text():
    counts = storage.get_event_counts()
    lines = ["👑 <b>Админ-панель — Aquality Bot</b>\n", "<b>Воронка:</b>"]
    for key, label in FUNNEL:
        lines.append(f"  • {label}: <b>{counts.get(key, 0)}</b>")
    started = counts.get("calc_start", 0)
    done = counts.get("calc_complete", 0)
    if started:
        lines.append(f"  • Конверсия расчёта: {round(done / started * 100)}%")
    lines.append(f"\n<b>Заявок в базе:</b> {storage.count_leads()}")
    leads = storage.list_leads(10)
    if leads:
        lines.append("\n<b>Последние заявки:</b>")
        for lead in leads:
            ago = max(0, int((time.time() - lead["ts"]) / 3600))
            uname = f"@{lead['tg_username']}" if lead["tg_username"] else f"id{lead['tg_user_id']}"
            lines.append(f"  • {lead['name']} · {lead['phone']} · "
                         f"{lead['city'] or '—'} · {lead['result_kw'] or '—'} кВт · "
                         f"{uname} · {ago}ч назад")
    else:
        lines.append("\nПока заявок нет.")
    lines.append("\n/broadcast &lt;текст&gt; — рассылка всем пользователям.")
    return "\n".join(lines)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_owner(message.from_user):
        return
    await message.answer(_admin_text(), disable_web_page_preview=True)


@router.callback_query(F.data == "menu:admin")
async def cb_admin(cb: CallbackQuery):
    if not is_owner(cb.from_user):
        return await cb.answer("Только для владельца.", show_alert=True)
    await cb.message.answer(_admin_text(), disable_web_page_preview=True)
    await cb.answer()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if not is_owner(message.from_user):
        return
    text = message.text.partition(" ")[2].strip()
    if not text:
        return await message.answer("Использование: /broadcast <текст рассылки>")
    sent = failed = 0
    for uid in storage.all_user_ids():
        try:
            await message.bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"📣 Рассылка завершена. Отправлено: {sent}, ошибок: {failed}.")
