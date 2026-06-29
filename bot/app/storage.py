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
