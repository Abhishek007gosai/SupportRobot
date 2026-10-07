# Telegram Relay Bot

Users message the bot -> you receive it. Users get an auto reply. Edit messages live, see user count, broadcast without forward tag.

## Setup
1. Create a bot with @BotFather -> `BOT_TOKEN`
2. Get your numeric id from @userinfobot -> `OWNER_ID`
3. Create a free MongoDB Atlas cluster -> `MONGO_URI` (Network Access: allow 0.0.0.0/0)

Token, owner id and database are in `config.py` (read from environment variables, so set them on the host).
Start message, reply message and the reply timer are edited inside the bot with /settings (owner only).

## Owner panel (all inside Telegram)
Send `/settings` (or tap the Settings button in your /start) :

- **Start message** and **Reply message** buttons, each with Change, Preview, Remove, Default.
- **Reply message > Auto-delete timer**: choose Off / 10s / 30s / 60s / 5 min / 1 hour or a custom number of seconds. The reply is deleted from the user's chat after that time.
- Placeholders: `{first_name}`, `{user_id}`. HTML formatting works.

| Command | What it does |
|---|---|
| `/settings` | open the settings buttons |
| `/stats` | total users (MongoDB) |
| `/broadcast` | reply to any message with it to send to all users, no forward tag |

Reply to a user's message in your chat and it is sent to that user.

## Deploy on Render
New -> Web Service -> connect your GitHub repo.
Build: `pip install -r requirements.txt` | Start: `python bot.py`
Add env vars `BOT_TOKEN`, `OWNER_ID`, `MONGO_URI`.
Free plan sleeps after 15 min without traffic: ping your Render URL every 5-10 min with UptimeRobot.

## Deploy on Koyeb
Create Service -> GitHub -> builder: Dockerfile (or buildpack with the Procfile).
Service type: Web, exposed port `8000`, health check path `/`.
Add env vars `BOT_TOKEN`, `OWNER_ID`, `MONGO_URI`, and `PORT=8000`.

Run only one instance at a time (Render and Koyeb together with the same token will conflict).

## Local run
```
pip install -r requirements.txt
export BOT_TOKEN=... OWNER_ID=... MONGO_URI=...
python bot.py
```
