"""
Bot settings. Read from environment variables first (use this on Render / Koyeb),
falling back to the values written here (handy for local testing).

Start message, reply message and the reply auto-delete timer are NOT here:
the owner edits them inside the bot (/settings).
"""
import os

# ---------- REQUIRED ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")            # from @BotFather
OWNER_ID = int(os.getenv("OWNER_ID", "0"))        # your numeric Telegram user id (get it from @userinfobot)
MONGO_URI = os.getenv("MONGO_URI", "")            # mongodb+srv://user:pass@cluster/...
DB_NAME = os.getenv("DB_NAME", "telegram_bot")

# ---------- HOSTING ----------
# Render / Koyeb need a web port open for health checks.
PORT = int(os.getenv("PORT", "8080"))

# Seconds to wait between broadcast messages (avoids Telegram flood limits)
BROADCAST_DELAY = float(os.getenv("BROADCAST_DELAY", "0.05"))
