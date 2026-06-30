"""Async Supabase client for the bot.

Uses httpx to call PostgREST (RPC) and the Auth Admin API with the
service_role key. Falls back gracefully when not configured.

All functions return None or {} on error — callers must handle gracefully.
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=_HEADERS, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        log.error("SB RPC %s failed: %s", fn, e)
        return None


# ── Profile ────────────────────────────────────────────────────────────────

async def get_profile(tg_id: int) -> Optional[dict]:
    """Returns profile dict if telegram_id is registered, else None."""
    res = await _rpc("bot_get_profile", {"p_telegram_id": tg_id})
    return res if (res and res.get("ok")) else None


async def link_telegram(email: str, tg_id: int,
                        name: str = "", phone: str = "") -> dict:
    """Link telegram_id to Supabase account by email.

    Returns {ok, user_id?, email?, existed?, reason?}.
    reason='email_not_found' means we must create a new auth user first.
    """
    res = await _rpc("bot_link_telegram", {
        "p_email": email.lower().strip(),
        "p_telegram_id": tg_id,
        "p_name": name,
        "p_phone": phone,
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def create_auth_user(email: str, tg_id: int,
                           name: str = "", phone: str = "") -> Optional[str]:
    """Create a new Supabase auth user via Admin API.

    Returns Supabase user UUID on success, None if email already exists or on error.
    The handle_new_user trigger auto-creates the profile with telegram_id.
    """
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    body = {
        "email": email.lower().strip(),
        "email_confirm": True,
        "user_metadata": {
            "full_name": name,
            "phone": phone,
            "telegram_id": tg_id,
            "source": "telegram_bot",
        },
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=_HEADERS, json=body)
            if r.status_code == 422:
                # Email already exists in auth.users
                return None
            r.raise_for_status()
            return r.json().get("id")
    except Exception as e:
        log.error("create_auth_user failed: %s", e)
        return None


async def find_auth_user_by_email(email: str) -> Optional[str]:
    """Search auth.users by email. Returns UUID or None."""
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    params = {"filter": f"email:{email.lower().strip()}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=_HEADERS, params=params)
            r.raise_for_status()
            users = r.json().get("users", [])
            for u in users:
                if u.get("email", "").lower() == email.lower().strip():
                    return u.get("id")
    except Exception as e:
        log.error("find_auth_user_by_email: %s", e)
    return None


async def upsert_profile(user_id: str, tg_id: int, email: str,
                         name: str = "", phone: str = "") -> bool:
    """Insert or update profile row (used when auth user exists but profile doesn't)."""
    if not SB_CONFIGURED:
        return False
    url = f"{SUPABASE_URL}/rest/v1/profiles"
    body = {
        "id": user_id,
        "telegram_id": tg_id,
        "email": email.lower().strip(),
        "full_name": name or None,
        "phone": phone or None,
        "role": "user",
        "client_type": "client",
    }
    headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            return True
    except Exception as e:
        log.error("upsert_profile: %s", e)
        return False


async def update_profile(tg_id: int, name: str = "", phone: str = "") -> bool:
    """Update name/phone for an already-registered telegram user."""
    profile = await get_profile(tg_id)
    if not profile:
        return False
    if not (name or phone):
        return True
    user_id = profile["user_id"]
    url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}"
    body = {}
    if name:
        body["full_name"] = name
    if phone:
        body["phone"] = phone
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.patch(url, headers=_HEADERS, json=body)
            r.raise_for_status()
            return True
    except Exception as e:
        log.error("update_profile: %s", e)
        return False


# ── Subscriptions ──────────────────────────────────────────────────────────

async def get_active_sub(tg_id: int) -> Optional[dict]:
    """Returns active subscription dict {ok, plan, expires_at, role, ...} or None."""
    res = await _rpc("bot_get_active_sub", {"p_telegram_id": tg_id})
    return res if (res and res.get("ok")) else None


async def activate_sub(tg_id: int, plan: str, amount: float = None,
                       promo: str = None, source: str = "telegram") -> dict:
    """Activate subscription for telegram user. Returns {ok, expires_at?, reason?}."""
    res = await _rpc("bot_activate_sub", {
        "p_telegram_id": tg_id,
        "p_plan": plan,
        "p_amount": amount,
        "p_promo": promo,
        "p_source": source,
    })
    return res or {"ok": False, "reason": "rpc_error"}


# ── Promo codes ────────────────────────────────────────────────────────────

async def validate_promo(tg_id: int, code: str) -> dict:
    """Validate promo code for telegram user. Returns {ok, discount?, reason?}."""
    res = await _rpc("bot_validate_promo", {
        "p_telegram_id": tg_id,
        "p_code": code,
    })
    return res or {"ok": False, "reason": "rpc_error"}
