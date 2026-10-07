import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from NEXUS import database as db
from server import start_web_server

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger(__name__)

OWNER = filters.User(user_id=config.OWNER_ID)
HTML = ParseMode.HTML

KEY_START = "START_MESSAGE"
KEY_REPLY = "REPLY_TO_USER"
KEY_TIMER = "REPLY_DELETE_SECONDS"
MAX_TIMER = 86400  # 24 hours

# Built-in fallback texts, used only until the owner sets their own in /settings
DEFAULT_START = "👋 Hello <b>{first_name}</b>!\n\nSend me your message and I will get back to you soon."
DEFAULT_REPLY = "✅ Thanks! Your message has been received. I'll reply as soon as possible."

# short name used in button data -> (db key, title, default text)
MESSAGES = {
    "start": (KEY_START, "Start message", DEFAULT_START),
    "reply": (KEY_REPLY, "Reply message", DEFAULT_REPLY),
}

OWNER_HELP = (
    "<b>Owner panel</b>\n\n"
    "/settings - edit start message, reply message and reply timer\n"
    "/stats - total users\n"
    "/broadcast - reply to any message with this to send it to all users (no forward tag)\n\n"
    "Tip: reply to a user's message here and your reply goes to that user.\n"
    "Placeholders in messages: {first_name}, {user_id}. HTML tags are supported."
)


def btn(text, data):
    return InlineKeyboardButton(text, callback_data=data)


def fill(template: str, user) -> str:
    return template.replace("{first_name}", user.first_name or "").replace(
        "{user_id}", str(user.id)
    )


def fmt_seconds(sec: int) -> str:
    if sec <= 0:
        return "Off (never deleted)"
    if sec % 3600 == 0:
        return f"{sec // 3600} hour(s)"
    if sec % 60 == 0:
        return f"{sec // 60} minute(s)"
    return f"{sec} seconds"


async def get_timer() -> int:
    raw = await db.get_setting(KEY_TIMER, "0")
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


async def render(update: Update, text: str, markup=None):
    """Edit the menu message if opened from a button, else send a new one."""
    q = update.callback_query
    if q:
        try:
            await q.edit_message_text(text, parse_mode=HTML, reply_markup=markup)
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                raise
    else:
        await update.effective_message.reply_text(text, parse_mode=HTML, reply_markup=markup)


async def delete_later(message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except TelegramError:
        pass


# ---------------- user side ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_new = await db.add_user(user)

    template = await db.get_setting(KEY_START, DEFAULT_START)
    if template:
        await update.message.reply_text(fill(template, user), parse_mode=HTML)

    if user.id == config.OWNER_ID:
        await update.message.reply_text(
            OWNER_HELP,
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[btn("⚙️ Settings", "menu")]]),
        )
    elif is_new:
        uname = f"@{user.username}" if user.username else "no username"
        await context.bot.send_message(
            config.OWNER_ID,
            f"🆕 New user: {user.full_name} ({uname}) <code>{user.id}</code>",
            parse_mode=HTML,
        )


async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A normal user wrote to the bot -> deliver to owner + auto reply."""
    user = update.effective_user
    msg = update.message
    await db.add_user(user)

    uname = f"@{user.username}" if user.username else "no username"
    header = await context.bot.send_message(
        config.OWNER_ID,
        f"📩 <b>{user.full_name}</b> ({uname})\nID: <code>{user.id}</code>",
        parse_mode=HTML,
    )
    copied = await msg.copy(config.OWNER_ID)
    await db.save_map(header.message_id, user.id)
    await db.save_map(copied.message_id, user.id)

    template = await db.get_setting(KEY_REPLY, DEFAULT_REPLY)
    if not template:
        return
    sent = await msg.reply_text(fill(template, user), parse_mode=HTML)

    delay = await get_timer()
    if delay > 0:
        context.application.create_task(delete_later(sent, delay))


# ---------------- settings menus (owner) ----------------
async def owner_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        OWNER_HELP,
        parse_mode=HTML,
        reply_markup=InlineKeyboardMarkup([[btn("⚙️ Settings", "menu")]]),
    )


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting", None)
    await show_main(update)


async def show_main(update: Update):
    markup = InlineKeyboardMarkup(
        [
            [btn("📝 Start message", "open:start"), btn("💬 Reply message", "open:reply")],
            [btn("✖ Close", "close")],
        ]
    )
    await render(update, "⚙️ <b>Settings</b>\n\nChoose what you want to edit:", markup)


async def status_of(key: str) -> str:
    doc = await db.settings.find_one({"_id": key})
    if doc is None:
        return "Default"
    if doc["value"] == "":
        return "Removed (nothing is sent)"
    return "Custom ✅"


async def show_message_menu(update: Update, name: str):
    key, title, _ = MESSAGES[name]
    text = f"<b>{title}</b>\n\nStatus: {await status_of(key)}"
    rows = [
        [btn("✏️ Change", f"chg:{name}"), btn("👁 Preview", f"prev:{name}")],
        [btn("🗑 Remove", f"rm:{name}"), btn("♻️ Default", f"def:{name}")],
    ]
    if name == "reply":
        timer = await get_timer()
        text += f"\nAuto-delete: {fmt_seconds(timer)}"
        rows.append([btn("⏱ Auto-delete timer", "timer")])
    rows.append([btn("« Back", "menu")])
    await render(update, text, InlineKeyboardMarkup(rows))


async def show_timer_menu(update: Update):
    timer = await get_timer()
    text = (
        "⏱ <b>Reply auto-delete timer</b>\n\n"
        f"Current: <b>{fmt_seconds(timer)}</b>\n\n"
        "The reply is deleted from the user's chat this many seconds after it is sent."
    )
    markup = InlineKeyboardMarkup(
        [
            [btn("Off", "t:0"), btn("10s", "t:10"), btn("30s", "t:30"), btn("60s", "t:60")],
            [btn("5 min", "t:300"), btn("1 hour", "t:3600"), btn("✏️ Custom", "tc")],
            [btn("« Back", "open:reply")],
        ]
    )
    await render(update, text, markup)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != config.OWNER_ID:
        await q.answer("Not allowed", show_alert=True)
        return

    action, _, arg = q.data.partition(":")
    toast = None

    if action == "menu":
        context.user_data.pop("awaiting", None)
        await show_main(update)

    elif action == "open":
        context.user_data.pop("awaiting", None)
        await show_message_menu(update, arg)

    elif action == "chg":
        key, title, _ = MESSAGES[arg]
        context.user_data["awaiting"] = key
        await render(
            update,
            f"✏️ Send me the new <b>{title.lower()}</b> as a text message now.\n\n"
            "You can use HTML/Telegram formatting and the placeholders "
            "{first_name} and {user_id}.",
            InlineKeyboardMarkup([[btn("✖ Cancel", f"open:{arg}")]]),
        )

    elif action == "prev":
        key, _, default = MESSAGES[arg]
        template = await db.get_setting(key, default)
        if template:
            await context.bot.send_message(
                config.OWNER_ID, fill(template, q.from_user), parse_mode=HTML
            )
        else:
            toast = "Nothing to preview, this message is removed."

    elif action == "rm":
        key, title, _ = MESSAGES[arg]
        await db.set_setting(key, "")
        toast = f"{title} removed."
        await show_message_menu(update, arg)

    elif action == "def":
        key, title, _ = MESSAGES[arg]
        await db.reset_setting(key)
        toast = f"{title} reset to default."
        await show_message_menu(update, arg)

    elif action == "timer":
        context.user_data.pop("awaiting", None)
        await show_timer_menu(update)

    elif action == "t":
        await db.set_setting(KEY_TIMER, arg)
        toast = "Timer saved."
        await show_timer_menu(update)

    elif action == "tc":
        context.user_data["awaiting"] = KEY_TIMER
        await render(
            update,
            f"⏱ Send the number of <b>seconds</b> (0 = never delete, max {MAX_TIMER}).",
            InlineKeyboardMarkup([[btn("✖ Cancel", "timer")]]),
        )

    elif action == "close":
        await q.message.delete()

    await q.answer(toast)


# ---------------- owner messages ----------------
async def owner_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    awaiting = context.user_data.get("awaiting")

    # 1) owner is typing a new setting value
    if awaiting == KEY_TIMER:
        text = (msg.text or "").strip()
        if not text.isdigit() or int(text) > MAX_TIMER:
            await msg.reply_text(f"Please send a number between 0 and {MAX_TIMER}.")
            return
        await db.set_setting(KEY_TIMER, str(int(text)))
        context.user_data.pop("awaiting")
        await show_timer_menu(update)
        return

    if awaiting in (KEY_START, KEY_REPLY):
        if not msg.text:
            await msg.reply_text("Please send the message as plain text.")
            return
        await db.set_setting(awaiting, msg.text_html)
        context.user_data.pop("awaiting")
        await msg.reply_text("✅ Saved.")
        await show_message_menu(update, "start" if awaiting == KEY_START else "reply")
        return

    # 2) owner replied to a forwarded user message -> send it to that user
    replied = msg.reply_to_message
    if not replied:
        return
    user_id = await db.get_mapped_user(replied.message_id)
    if not user_id:
        return
    try:
        await msg.copy(user_id)
        await msg.reply_text("✅ Sent.", quote=True)
    except Forbidden:
        await msg.reply_text("❌ This user has blocked the bot.")
    except TelegramError as e:
        await msg.reply_text(f"❌ Failed: {e}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = await db.count_users()
    await update.message.reply_text(f"👥 Total users: <b>{total}</b>", parse_mode=HTML)


# ---------------- broadcast (no forward tag) ----------------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = update.message.reply_to_message
    if not source:
        await update.message.reply_text("Reply to the message you want to broadcast with /broadcast")
        return
    status = await update.message.reply_text("📣 Broadcast started...")
    context.application.create_task(_run_broadcast(context, source, status))


async def _run_broadcast(context, source, status):
    sent = failed = removed = 0
    async for uid in db.all_user_ids():
        try:
            await context.bot.copy_message(
                chat_id=uid, from_chat_id=source.chat_id, message_id=source.message_id
            )
            sent += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                await context.bot.copy_message(uid, source.chat_id, source.message_id)
                sent += 1
            except TelegramError:
                failed += 1
        except (Forbidden, BadRequest):
            await db.remove_user(uid)  # blocked the bot / deleted account
            removed += 1
        except TelegramError:
            failed += 1
        await asyncio.sleep(config.BROADCAST_DELAY)

    await status.edit_text(
        f"✅ Broadcast finished\n\nSent: {sent}\nFailed: {failed}\nRemoved (blocked): {removed}"
    )


# ---------------- main ----------------
def main():
    missing = config.missing_required()
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)} (see .env.example)")

    start_web_server()
    app = Application.builder().token(config.BOT_TOKEN).build()

    private = filters.ChatType.PRIVATE

    # owner commands
    app.add_handler(CommandHandler("help", owner_help, filters=OWNER))
    app.add_handler(CommandHandler("settings", settings_cmd, filters=OWNER))
    app.add_handler(CommandHandler("stats", stats, filters=OWNER))
    app.add_handler(CommandHandler("broadcast", broadcast, filters=OWNER))

    # settings buttons
    app.add_handler(CallbackQueryHandler(on_button))

    # everyone
    app.add_handler(CommandHandler("start", start, filters=private))

    # owner's normal messages (new setting text, or reply to a user)
    app.add_handler(MessageHandler(OWNER & private & ~filters.COMMAND, owner_message))

    # all other private messages from users
    app.add_handler(MessageHandler(private & ~OWNER & ~filters.COMMAND, user_message))

    log.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
