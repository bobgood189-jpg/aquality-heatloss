"""Runtime configuration. All secrets come from environment variables so the same
image runs locally and on Railway/Render/any VPS."""
import os


def _load_dotenv():
    """Minimal .env loader (no dependency): populate os.environ from bot/.env if
    present, without overriding values already set in the real environment."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.split("#", 1)[0].strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except FileNotFoundError:
        pass


_load_dotenv()

# Telegram bot token from @BotFather — REQUIRED.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Owner / admin. Leads are forwarded here and /admin is gated to them.
# Username is used for display + as fallback; numeric id (preferred) lets the bot
# push leads proactively. The owner can run /myid to discover their numeric id.
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "ibrokh1movv7").lstrip("@")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")

# Where the SQLite DB lives (mount a volume here in production for persistence).
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aquality_bot.db"))

# ── Платный доступ (подписка) ──────────────────────────────────────────────
# Выключено по умолчанию: полный расчёт доступен всем. Включить, когда готовы
# принимать оплату и активировать подписки: PAYWALL=1 в bot/.env.
PAYWALL = os.getenv("PAYWALL", "0").strip().lower() in ("1", "true", "yes", "on")

# Тарифы: id → (месяцы, цена в сумах, дней доступа).
PLANS = {
    "m1":  {"months": 1,  "price": 100000,  "days": 30},
    "m6":  {"months": 6,  "price": 550000,  "days": 182},
    "m12": {"months": 12, "price": 1000000, "days": 365},
}

# Telegram владельца для оплаты (без @) + реквизиты перевода.
PAY_TG = os.getenv("PAY_TG", "aqualityHL").lstrip("@")
PAY_REQUISITES = os.getenv("PAY_REQUISITES", "").strip()

# ── Telegram bot public username (shown in linking instructions on the website) ──
BOT_USERNAME = os.getenv("BOT_USERNAME", "aqualityHL_bot").strip().lstrip("@")

# ── Supabase (общая БД с сайтом) ──────────────────────────────────────────
# SUPABASE_URL уже задан (проект uhyomjdsswasmlycpoyh).
# SUPABASE_SERVICE_KEY: Supabase Dashboard → Settings → API → service_role.
# Когда оба заданы, бот использует Supabase как основную БД для пользователей
# и подписок (те же таблицы, что и сайт). SQLite — только для lang-прeференций.
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://uhyomjdsswasmlycpoyh.supabase.co").strip().rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
SB_CONFIGURED = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)
BOT_SYNC_SECRET = os.getenv("BOT_SYNC_SECRET", "").strip()

# ── Website URL (shown in bot messages so users can open the site) ──────────
SITE_URL = os.getenv("SITE_URL", "https://aquality-hl.netlify.app").strip().rstrip("/")

# Business contact details (mirrors CONTACT in index.html).
CONTACT = {
    "whatsapp": "998772941555",
    "phone": "+998 77-294-15-55",
    "phone2": "+998 91-116-01-01",
    "tg": "https://t.me/aquality_call_center",
    "instagram": "https://www.instagram.com/aquality_global",
    "address": "Tadbirkorlar ko'chasi 277 (польский базар, магазин 27)",
}


def require_token():
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN is not set. Create a bot via @BotFather, then:\n"
            "  export BOT_TOKEN='123456:ABC...'   (or put it in bot/.env)\n"
            "and run again."
        )
    return BOT_TOKEN
