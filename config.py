"""
All bot settings live here.
Values are read from environment variables first (use this on Render / Koyeb),
and fall back to the defaults written below (handy for local testing).
"""
import os

# ---------- REQUIRED ----------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")            # from @BotFather
OWNER_ID = int(os.getenv("OWNER_ID", "0"))        # your numeric Telegram user id (get it from @userinfobot)
MONGO_URI = os.getenv("MONGO_URI", "")            # mongodb+srv://user:pass@cluster/...
DB_NAME = os.getenv("DB_NAME", "telegram_bot")

# ---------- DEFAULT MESSAGES ----------
# You can change these in this file OR live from inside the bot with
# /setstart and /setreply (saved in MongoDB, overrides these defaults).
# HTML is supported: <b>bold</b>, <i>italic</i>, <a href="https://x.com">link</a>
# Placeholders: {first_name}, {user_id}
START_MESSAGE = os.getenv(
    "START_MESSAGE",
    "👋 Hello <b>{first_name}</b>!\n\nSend me your message and I will get back to you soon.",
)

REPLY_TO_USER = os.getenv(
    "REPLY_TO_USER",
    "✅ Thanks! Your message has been received. I'll reply as soon as possible.",
)

# Seconds after which the auto reply is deleted from the user's chat.
# 0 = never delete. You can change this from inside the bot (Settings > Reply message).
REPLY_DELETE_SECONDS = int(os.getenv("REPLY_DELETE_SECONDS", "0"))

# ---------- HOSTING ----------
# Render / Koyeb need a web port open for health checks.
PORT = int(os.getenv("PORT", "8080"))

# Seconds to wait between broadcast messages (avoids Telegram flood limits)
BROADCAST_DELAY = float(os.getenv("BROADCAST_DELAY", "0.05"))
