"""Async Supabase client for the bot. Uses httpx + service_role key.

All public functions return None / empty dict when SB_CONFIGURED is False
so callers need no extra guards.
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

_TIMEOUT = httpx.Timeout(12.0, connect=5.0)


async def _rpc(fn: str, payload: dict) -> Optional[dict]:
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/rest/v1/rpc/{fn}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(url, json=payload, headers=_HEADERS)
            if r.status_code == 200:
                return r.json()
            log.warning("rpc %s → %s %s", fn, r.status_code, r.text[:300])
            # Surface the actual HTTP status instead of collapsing everything into a
            # generic "rpc_error" — callers do `res or {"ok": False, "reason": "rpc_error"}",
            # and this dict is truthy, so it flows straight through as the real reason
            # (e.g. "http_300" for an ambiguous overloaded RPC name, "http_401" for a
            # bad/rotated service key, "http_404" for a function PostgREST can't see).
            return {"ok": False, "reason": f"http_{r.status_code}"}
    except Exception as e:
        log.error("rpc %s error: %s", fn, e)
    return None


# ── Profile ──────────────────────────────────────────────────────────────────

async def get_profile(tg_id: int) -> Optional[dict]:
    """Profile + active sub in one call. Returns dict or None."""
    res = await _rpc("bot_get_profile", {"p_telegram_id": tg_id})
    return res if res and res.get("ok") else None


async def upsert_user(email: str, tg_id: int,
                      name: str = "", phone: str = "",
                      username: str = "") -> dict:
    """Atomic: find existing profile by telegram_id or email and link it.
    Returns {ok, status, user_id, email} or {ok:False, reason}.
    """
    res = await _rpc("bot_upsert_user", {
        "p_telegram_id": tg_id,
        "p_email":       email.lower().strip(),
        "p_name":        name,
        "p_phone":       phone,
        "p_username":    username,
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def create_auth_user(email: str, tg_id: int,
                           name: str = "", phone: str = "") -> Optional[str]:
    """Create Supabase Auth user via Admin API. Returns user_id or None."""
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    payload = {
        "email": email.lower().strip(),
        "email_confirm": True,
        "user_metadata": {
            "full_name":   name,
            "phone":       phone,
            "telegram_id": tg_id,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(url, json=payload, headers=_HEADERS)
            if r.status_code in (200, 201):
                return r.json().get("id")
            if r.status_code == 422:
                log.info("create_auth_user: already exists — %s", email)
                return None
            log.warning("create_auth_user %s → %s %s", email, r.status_code, r.text[:200])
    except Exception as e:
        log.error("create_auth_user error: %s", e)
    return None


async def find_auth_user_by_email(email: str) -> Optional[str]:
    """Lookup existing auth user by email. Returns user_id or None."""
    if not SB_CONFIGURED:
        return None
    url = f"{SUPABASE_URL}/auth/v1/admin/users"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.get(url, params={"filter": f"email:{email.lower().strip()}"},
                            headers=_HEADERS)
            if r.status_code == 200:
                users = r.json().get("users") or []
                return users[0].get("id") if users else None
    except Exception as e:
        log.error("find_auth_user_by_email error: %s", e)
    return None


async def set_user_password(user_id: str, password: str) -> bool:
    """Set a new password for an auth user via the Admin API. Returns True on success.

    Powers the bot's /resetpass flow so a user who is already verified in Telegram
    (their telegram_id is linked to the profile) can recover access WITHOUT any
    email — bypassing Supabase's rate-limited auth email on the free tier.
    """
    if not SB_CONFIGURED or not user_id:
        return False
    url = f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.put(url, json={"password": password}, headers=_HEADERS)
            if r.status_code == 200:
                return True
            log.warning("set_user_password %s → %s %s", user_id, r.status_code, r.text[:200])
    except Exception as e:
        log.error("set_user_password error: %s", e)
    return False


async def create_profile(user_id: str, tg_id: int, email: str,
                         name: str = "", phone: str = "",
                         username: str = "") -> bool:
    """Create or merge profile row after auth user was created. Returns True on success."""
    res = await _rpc("bot_create_profile", {
        "p_user_id":     user_id,
        "p_telegram_id": tg_id,
        "p_email":       email,
        "p_name":        name,
        "p_phone":       phone,
        "p_username":    username,
    })
    return bool(res and res.get("ok"))


async def update_profile(tg_id: int, name: str = "", phone: str = "") -> bool:
    """Update name/phone on existing profile by telegram_id."""
    if not SB_CONFIGURED:
        return False
    if not name and not phone:
        return True
    url = f"{SUPABASE_URL}/rest/v1/profiles"
    payload = {}
    if name:
        payload["full_name"] = name
    if phone:
        payload["phone"] = phone
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.patch(url, json=payload,
                              params={"telegram_id": f"eq.{tg_id}"},
                              headers=_HEADERS)
            return r.status_code in (200, 204)
    except Exception as e:
        log.error("update_profile error: %s", e)
    return False


# ── Subscriptions ─────────────────────────────────────────────────────────────

async def get_active_sub(tg_id: int) -> Optional[dict]:
    """Returns active subscription dict or None."""
    res = await _rpc("bot_get_active_sub", {"p_telegram_id": tg_id})
    return res if res and res.get("ok") else None


async def activate_sub(tg_id: int, plan: str, amount=None,
                       promo: str = None, source: str = "telegram",
                       actor_tg: int = None, months: int = None,
                       email: str = None) -> dict:
    """Activate subscription. Returns {ok, sub_id, expires_at, plan}.

    months: explicit duration for the new pro_mN/max_mN plan ids (bypasses
    plan_months() parsing on the DB side).
    email: fallback lookup when the buyer's telegram_id isn't linked to a
    profile yet — the RPC links it to the profile matching this email.
    """
    res = await _rpc("bot_activate_sub", {
        "p_telegram_id": tg_id,
        "p_plan":        plan,
        "p_amount":      amount,
        "p_promo":       promo,
        "p_source":      source,
        "p_actor_tg":    actor_tg,
        "p_months":      months,
        "p_email":       email,
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def set_just_activated(sub_id: str) -> bool:
    """Set just_activated=true on subscription so the site shows the congrats modal."""
    if not SB_CONFIGURED or not sub_id:
        return False
    url = f"{SUPABASE_URL}/rest/v1/subscriptions"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.patch(url, json={"just_activated": True},
                              params={"id": f"eq.{sub_id}"},
                              headers={**_HEADERS, "Prefer": "return=minimal"})
            return r.status_code in (200, 204)
    except Exception as e:
        log.error("set_just_activated error: %s", e)
    return False


# ── Promo codes ───────────────────────────────────────────────────────────────

async def validate_promo(tg_id: int, code: str) -> dict:
    """Validate promo code without redeeming. Returns {ok, discount, reason}."""
    res = await _rpc("bot_validate_promo", {
        "p_telegram_id": tg_id,
        "p_code":        code.strip().upper(),
    })
    return res or {"ok": False, "reason": "rpc_error"}


# ── Token linking ─────────────────────────────────────────────────────────────

async def link_by_token(tg_id: int, username: str, token: str) -> dict:
    """Claim a one-time website token to link Telegram account."""
    res = await _rpc("link_tg_account", {
        "p_token":       token.strip().upper(),
        "p_telegram_id": tg_id,
        "p_username":    username or "",
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def unlink_by_telegram(tg_id: int) -> dict:
    """Unlink Telegram from the profile bound to tg_id — bot-initiated (the
    site's unlink_tg_account RPC needs auth.uid(), so it can't be called from
    here). Powers the "Отвязать Telegram" button on the account screen."""
    res = await _rpc("bot_unlink_telegram", {"p_telegram_id": tg_id})
    return res or {"ok": False, "reason": "rpc_error"}


# ── Password reset codes (Telegram OTP for the site's forgot-password flow) ───

async def list_pending_reset_codes() -> list:
    """Reset codes awaiting delivery to the user's Telegram chat."""
    res = await _rpc("bot_list_pending_reset_codes", {})
    return res or []


async def mark_reset_code_notified(code_id: str) -> None:
    await _rpc("bot_mark_reset_code_notified", {"p_id": code_id})


# ── Analytics & audit ─────────────────────────────────────────────────────────

async def log_event(tg_id: int, event: str, data: dict = None) -> None:
    """Fire-and-forget: log a bot event to bot_events table."""
    await _rpc("bot_log_event", {
        "p_tg_id": tg_id,
        "p_event": event,
        "p_data":  data,
    })


async def get_stats() -> Optional[dict]:
    """Return admin stats dict: users, subs, revenue, leads."""
    return await _rpc("bot_get_stats", {})


# ── Site payments (paywall на сайте, подтверждение владельцем в Telegram) ─────

async def list_pending_site_payments() -> list:
    """Pending payments created via the site's paywall, not yet notified."""
    res = await _rpc("bot_list_pending_site_payments", {})
    return res or []


async def mark_site_payment_notified(payment_id: str) -> None:
    await _rpc("bot_mark_site_payment_notified", {"p_payment_id": payment_id})


async def activate_site_payment(payment_id: str, actor_tg: int = None) -> dict:
    """Confirm a site payment: activates the subscription, marks payment paid.
    Returns {ok, sub_id, user_id, email, full_name, telegram_id, plan, amount, expires_at}."""
    res = await _rpc("bot_activate_site_payment", {
        "p_payment_id": payment_id,
        "p_actor_tg":   actor_tg,
    })
    return res or {"ok": False, "reason": "rpc_error"}


async def reject_site_payment(payment_id: str, actor_tg: int = None) -> dict:
    res = await _rpc("bot_reject_site_payment", {
        "p_payment_id": payment_id,
        "p_actor_tg":   actor_tg,
    })
    return res or {"ok": False, "reason": "rpc_error"}
