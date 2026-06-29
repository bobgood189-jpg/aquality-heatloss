"""SQLite persistence for leads, funnel events and per-user language preference.
Mirrors the website's aq_leads_v1 / aq_events_v1 localStorage modules."""
import sqlite3
import json
import time
from contextlib import contextmanager

from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,
    tg_user_id  INTEGER,
    tg_username TEXT,
    name        TEXT,
    phone       TEXT,
    city        TEXT,
    result_kw   REAL,
    payload     TEXT
);
CREATE TABLE IF NOT EXISTS events (
    name  TEXT PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users (
    tg_user_id INTEGER PRIMARY KEY,
    lang       TEXT,
    last_seen  INTEGER
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_user_id INTEGER NOT NULL,
    plan       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'active',
    started_ts INTEGER NOT NULL,
    expires_ts INTEGER NOT NULL,
    amount     REAL,
    promo_code TEXT,
    source     TEXT DEFAULT 'manual'
);
CREATE TABLE IF NOT EXISTS promo_codes (
    code       TEXT PRIMARY KEY,
    discount   INTEGER NOT NULL,
    max_uses   INTEGER,
    used_count INTEGER NOT NULL DEFAULT 0,
    expires_ts INTEGER,
    active     INTEGER NOT NULL DEFAULT 1,
    created_ts INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS promo_redemptions (
    code       TEXT NOT NULL,
    tg_user_id INTEGER NOT NULL,
    discount   INTEGER,
    used_ts    INTEGER NOT NULL,
    PRIMARY KEY (code, tg_user_id)
);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.executescript(_SCHEMA)


def save_lead(tg_user_id, tg_username, name, phone, city, result_kw, payload):
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO leads(ts,tg_user_id,tg_username,name,phone,city,result_kw,payload) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (int(time.time()), tg_user_id, tg_username, name, phone, city,
             result_kw, json.dumps(payload, ensure_ascii=False)),
        )
        return cur.lastrowid


def list_leads(limit=20):
    with _conn() as con:
        rows = con.execute("SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def count_leads():
    with _conn() as con:
        return con.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]


def log_event(name):
    with _conn() as con:
        con.execute(
            "INSERT INTO events(name,count) VALUES(?,1) "
            "ON CONFLICT(name) DO UPDATE SET count=count+1", (name,))


def get_event_counts():
    with _conn() as con:
        rows = con.execute("SELECT name,count FROM events").fetchall()
        return {r["name"]: r["count"] for r in rows}


def set_user_lang(tg_user_id, lang):
    with _conn() as con:
        con.execute(
            "INSERT INTO users(tg_user_id,lang,last_seen) VALUES(?,?,?) "
            "ON CONFLICT(tg_user_id) DO UPDATE SET lang=excluded.lang, last_seen=excluded.last_seen",
            (tg_user_id, lang, int(time.time())))


def get_user_lang(tg_user_id):
    with _conn() as con:
        row = con.execute("SELECT lang FROM users WHERE tg_user_id=?", (tg_user_id,)).fetchone()
        return row["lang"] if row and row["lang"] else None


def all_user_ids():
    with _conn() as con:
        rows = con.execute("SELECT tg_user_id FROM users").fetchall()
        return [r["tg_user_id"] for r in rows]


# ── Подписки (Фаза 1: ручная активация владельцем) ─────────────────────────
def get_active_sub(tg_user_id):
    """Активная подписка пользователя (status='active' и не истекла) или None."""
    now = int(time.time())
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM subscriptions WHERE tg_user_id=? AND status='active' "
            "AND expires_ts>? ORDER BY expires_ts DESC LIMIT 1", (tg_user_id, now)).fetchone()
        return dict(row) if row else None


def activate_sub(tg_user_id, plan, days, amount=None, promo=None, source="manual"):
    """Создать/продлить подписку. Продление считается от текущего срока, если он
    ещё не истёк. Если задан промокод — фиксируем погашение и увеличиваем счётчик."""
    now = int(time.time())
    cur = get_active_sub(tg_user_id)
    base = cur["expires_ts"] if cur and cur["expires_ts"] > now else now
    expires = base + days * 86400
    promo = (promo or "").strip().upper() or None
    with _conn() as con:
        con.execute(
            "INSERT INTO subscriptions(tg_user_id,plan,status,started_ts,expires_ts,amount,promo_code,source) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (tg_user_id, plan, "active", now, expires, amount, promo, source))
        if promo:
            row = con.execute("SELECT discount FROM promo_codes WHERE code=?", (promo,)).fetchone()
            disc = row["discount"] if row else None
            con.execute(
                "INSERT OR IGNORE INTO promo_redemptions(code,tg_user_id,discount,used_ts) VALUES(?,?,?,?)",
                (promo, tg_user_id, disc, now))
            con.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (promo,))
    return expires


def cancel_sub(tg_user_id):
    with _conn() as con:
        con.execute("UPDATE subscriptions SET status='canceled' WHERE tg_user_id=? AND status='active'",
                    (tg_user_id,))


def list_active_subs(limit=50):
    now = int(time.time())
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM subscriptions WHERE status='active' AND expires_ts>? "
            "ORDER BY expires_ts DESC LIMIT ?", (now, limit)).fetchall()
        return [dict(r) for r in rows]


def get_expiring_subs(within_days=3):
    """Активные подписки, истекающие в течение N дней (ещё не истекли)."""
    now = int(time.time())
    deadline = now + within_days * 86400
    with _conn() as con:
        rows = con.execute(
            "SELECT s.*, u.lang FROM subscriptions s "
            "LEFT JOIN users u ON u.tg_user_id=s.tg_user_id "
            "WHERE s.status='active' AND s.expires_ts>? AND s.expires_ts<=? "
            "ORDER BY s.expires_ts ASC", (now, deadline)).fetchall()
        return [dict(r) for r in rows]


def get_expired_subs_unnotified():
    """Подписки, которые только что истекли (последние 25 часов, не отменённые)."""
    now = int(time.time())
    cutoff = now - 25 * 3600
    with _conn() as con:
        rows = con.execute(
            "SELECT s.*, u.lang FROM subscriptions s "
            "LEFT JOIN users u ON u.tg_user_id=s.tg_user_id "
            "WHERE s.status='active' AND s.expires_ts<=? AND s.expires_ts>=? "
            "ORDER BY s.expires_ts DESC", (now, cutoff)).fetchall()
        return [dict(r) for r in rows]


# ── Промокоды ──────────────────────────────────────────────────────────────
def validate_promo(code, tg_user_id):
    """Проверка кода для пользователя (не списывает). {ok, discount, reason}."""
    code = (code or "").strip().upper()
    if not code:
        return {"ok": False, "reason": "empty"}
    now = int(time.time())
    with _conn() as con:
        row = con.execute("SELECT * FROM promo_codes WHERE code=?", (code,)).fetchone()
        if not row or not row["active"]:
            return {"ok": False, "reason": "invalid"}
        if row["expires_ts"] and row["expires_ts"] < now:
            return {"ok": False, "reason": "invalid"}
        if row["max_uses"] is not None and row["used_count"] >= row["max_uses"]:
            return {"ok": False, "reason": "exhausted"}
        used = con.execute(
            "SELECT 1 FROM promo_redemptions WHERE code=? AND tg_user_id=?",
            (code, tg_user_id)).fetchone()
        if used:
            return {"ok": False, "reason": "already_used"}
        return {"ok": True, "discount": row["discount"]}


def add_promo(code, discount, max_uses=None, expires_ts=None):
    code = (code or "").strip().upper()
    with _conn() as con:
        con.execute(
            "INSERT INTO promo_codes(code,discount,max_uses,used_count,expires_ts,active,created_ts) "
            "VALUES(?,?,?,0,?,1,?) "
            "ON CONFLICT(code) DO UPDATE SET discount=excluded.discount, "
            "max_uses=excluded.max_uses, expires_ts=excluded.expires_ts, active=1",
            (code, int(discount), max_uses, expires_ts, int(time.time())))


def del_promo(code):
    with _conn() as con:
        con.execute("DELETE FROM promo_codes WHERE code=?", ((code or "").strip().upper(),))


def list_promos():
    with _conn() as con:
        rows = con.execute("SELECT * FROM promo_codes ORDER BY created_ts DESC").fetchall()
        return [dict(r) for r in rows]
