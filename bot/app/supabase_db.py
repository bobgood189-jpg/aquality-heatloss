"""Async Supabase client for the bot. Uses httpx + service_role key.

All public functions are safe to call even when SB_CONFIGURED is False —
they simply return None / empty dict so callers don't need guards everywhere.
"""
import logging
from typing import Optional

import httpx

from .config import SUPABASE_URL, SUPABASE_SERVICE_KEY, SB_CONFIGURED

log = logging.getLogger("aquality-bot.sb")

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


async def _rpc(fn: str, payload: dict) -> Optional[dict]:
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn}"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, json=payload, headers=_HEADERS)
            if r.status_code == 200:
                return r.json()
            log.warning("rpc %s → %s %s", fn, r.status_code, r.text[:200])
    except Exception as e:
        log.error("rpc %s error: %s", fn, e)
    return None


async def get_profile(tg_id: int) -> Optional[dict]:
    """Returns profile dict if telegram_id is linked, else None."""
    res = await _rpc("bot_get_profile", {"p_telegram_id": tg_id})
    if res and res.get("ok"):
        return res
    return None


async def link_telegram(email: str, tg_id: int, name: str = "", phone: str = "") -> dict:
    """Link telegram_id to an existing account found by email, or report not_found."""
    res = await _rpc("bot_link_telegram", {
        "p_email": email.lower().strip(),
        "p_telegram_id": tg_id,
        "p_name": name,
        "p_phone": phone,
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def create_auth_user(email: str, tg_id: int, name: str = "", phone: str = "") -> Optional[str]:
    """Create a new Supabase Auth user. Returns user_id or None on failure."""
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    payload = {
        "email": email.lower().strip(),
        "email_confirm": True,
        "user_metadata": {"full_name": name, "phone": phone, "telegram_id": tg_id},
    }
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, json=payload, headers=_HEADERS)
            if r.status_code in (200, 201):
                data = r.json()
                return data.get("id")
            if r.status_code == 422:
                log.info("create_auth_user: email already exists — %s", email)
                return None
            log.warning("create_auth_user %s → %s %s", email, r.status_code, r.text[:200])
    except Exception as e:
        log.error("create_auth_user error: %s", e)
    return None


async def find_auth_user_by_email(email: str) -> Optional[str]:
    """Look up an existing auth.users row by email. Returns user_id or None."""
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    params = {"filter": f"email:{email.lower().strip()}"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params, headers=_HEADERS)
            if r.status_code == 200:
                data = r.json()
                users = data.get("users") or []
                if users:
                    return users[0].get("id")
    except Exception as e:
        log.error("find_auth_user_by_email error: %s", e)
    return None


async def upsert_profile(user_id: str, tg_id: int, email: str,
                         name: str = "", phone: str = "") -> bool:
    """Insert or merge a profile row. Returns True on success."""
    if not SB_CONFIGURED:
        return False
    url = f"{SUPABASE_URL}/rest/v1/profiles"
    payload = {
        "id": user_id,
        "telegram_id": tg_id,
        "email": email.lower().strip(),
        "full_name": name or None,
        "phone": phone or None,
    }
    hdrs = {**_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(url, json=payload, headers=hdrs)
            return r.status_code in (200, 201, 204)
    except Exception as e:
        log.error("upsert_profile error: %s", e)
    return False


async def update_profile(tg_id: int, name: str = "", phone: str = "") -> bool:
    """Update name/phone on an existing profile by telegram_id."""
    if not SB_CONFIGURED:
        return False
    url = f"{SUPABASE_URL}/rest/v1/profiles"
    params = {"telegram_id": f"eq.{tg_id}"}
    payload = {}
    if name:
        payload["full_name"] = name
    if phone:
        payload["phone"] = phone
    if not payload:
        return True
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.patch(url, json=payload, params=params, headers=_HEADERS)
            return r.status_code in (200, 204)
    except Exception as e:
        log.error("update_profile error: %s", e)
    return False


async def get_active_sub(tg_id: int) -> Optional[dict]:
    """Returns subscription dict if active, else None."""
    res = await _rpc("bot_get_active_sub", {"p_telegram_id": tg_id})
    if res and res.get("ok"):
        return res
    return None


async def activate_sub(tg_id: int, plan: str, amount=None,
                       promo: str = None, source: str = "telegram") -> dict:
    """Activate a subscription plan for a telegram user. Returns {ok, sub_id, expires_at, plan}."""
    res = await _rpc("bot_activate_sub", {
        "p_telegram_id": tg_id,
        "p_plan": plan,
        "p_amount": amount,
        "p_promo": promo,
        "p_source": source,
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def validate_promo(tg_id: int, code: str) -> dict:
    """Validate a promo code for a telegram user. Returns {ok, discount, reason}."""
    res = await _rpc("bot_validate_promo", {
        "p_telegram_id": tg_id,
        "p_code": code.strip().upper(),
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def link_by_token(tg_id: int, username: str, token: str) -> dict:
    """Claim a one-time token from the website to link this Telegram account."""
    res = await _rpc("link_tg_account", {
        "p_token": token.strip().upper(),
        "p_telegram_id": tg_id,
        "p_username": username or "",
    })
    return res or {"ok": False, "reason": "rpc_error"}
