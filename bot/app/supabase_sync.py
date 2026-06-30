"""Supabase sync — calls the telegram-webhook edge function via stdlib HTTP.
No external dependencies required.

Set SUPABASE_URL and BOT_SYNC_SECRET in bot/.env to enable.
If not configured, all functions return {"ok": False, "reason": "not_configured"}
and log a debug message — the bot continues working normally without sync.
"""
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .config import SUPABASE_URL, BOT_SYNC_SECRET

log = logging.getLogger("aquality-bot.sync")

_WEBHOOK = f"{SUPABASE_URL}/functions/v1/telegram-webhook" if SUPABASE_URL else ""


def _call(payload: dict) -> dict:
    if not _WEBHOOK or not BOT_SYNC_SECRET:
        log.debug("Supabase sync skipped — SUPABASE_URL or BOT_SYNC_SECRET not set")
        return {"ok": False, "reason": "not_configured"}
    body = json.dumps(payload).encode()
    req = Request(
        _WEBHOOK,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-bot-secret": BOT_SYNC_SECRET,
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        log.warning("Supabase sync HTTP %s: %s", e.code, e.read())
        return {"ok": False, "reason": f"http_{e.code}"}
    except URLError as e:
        log.warning("Supabase sync URL error: %s", e)
        return {"ok": False, "reason": "network"}
    except Exception as e:
        log.exception("Supabase sync error: %s", e)
        return {"ok": False, "reason": str(e)}


def link_account(tg_user_id: int, tg_username: str, token: str) -> dict:
    """Link a Telegram user to a Supabase profile using a token generated on the site."""
    return _call({
        "action":       "link",
        "tg_user_id":   tg_user_id,
        "tg_username":  tg_username or "",
        "token":        token.strip().upper(),
    })


def activate_sub(tg_user_id: int, plan: str, days: int,
                 amount=None, promo=None) -> dict:
    """Activate/extend a subscription for the Supabase profile linked to this Telegram user."""
    return _call({
        "action":       "activate_sub",
        "tg_user_id":   tg_user_id,
        "plan":         plan,
        "days":         days,
        "amount":       amount,
        "promo":        promo,
    })
