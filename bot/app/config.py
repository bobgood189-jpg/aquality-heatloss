"""Runtime configuration. All secrets come from environment variables so the same
image runs locally and on Railway/Render/any VPS."""
import os

# Telegram bot token from @BotFather — REQUIRED.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Owner / admin. Leads are forwarded here and /admin is gated to them.
# Username is used for display + as fallback; numeric id (preferred) lets the bot
# push leads proactively. The owner can run /myid to discover their numeric id.
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "ibrokh1movv7").lstrip("@")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or "0")

# Where the SQLite DB lives (mount a volume here in production for persistence).
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aquality_bot.db"))

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
