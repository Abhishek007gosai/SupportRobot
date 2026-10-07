"""
Bot settings. Read from environment variables first (use this on Render / Koyeb),
falling back to the values written here (handy for local testing).

Start message, reply message and the reply auto-delete timer are NOT here:
the owner edits them inside the bot (/settings).
"""
import os


def _int(name: str, default: int = 0) -> int:
    """Read an int env var; empty/missing -> default, garbage -> clear error."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Environment variable {name} must be a number, got: {raw!r}")


# ---------- REQUIRED ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()    # from @BotFather
OWNER_ID = _int("OWNER_ID")                       # your numeric Telegram user id (@userinfobot)
MONGO_URI = os.getenv("MONGO_URI", "").strip()    # mongodb+srv://user:pass@cluster/...
DB_NAME = os.getenv("DB_NAME", "telegram_bot")

# ---------- TELEGRAM API (my.telegram.org) ----------
# Not used by python-telegram-bot; kept for Pyrogram/Telethon-style code.
API_ID = _int("API_ID")                           # number from my.telegram.org
API_HASH = os.getenv("API_HASH", "").strip()      # string from my.telegram.org

# ---------- HOSTING ----------
# Render / Koyeb need a web port open for health checks.
PORT = _int("PORT", 8080)

# Seconds to wait between broadcast messages (avoids Telegram flood limits)
BROADCAST_DELAY = float(os.getenv("BROADCAST_DELAY", "0.05") or "0.05")


def missing_required() -> list:
    """Names of required variables that are not set."""
    values = {"BOT_TOKEN": BOT_TOKEN, "OWNER_ID": OWNER_ID, "MONGO_URI": MONGO_URI}
    return [k for k, v in values.items() if not v]
