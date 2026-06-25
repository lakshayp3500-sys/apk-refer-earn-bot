# 📱 APK Refer & Earn Bot

A Telegram bot where users earn points by referring friends and redeem them for APKs — fully automatic delivery.

---

## 🚀 Deploy on Railway (Recommended)

### Step 1 — Database (Neon.tech)
1. Go to [neon.tech](https://neon.tech) → Sign up (free)
2. Create a new project
3. Copy the **Connection String** (looks like `postgresql://user:pass@host/db`)

### Step 2 — Deploy on Railway
1. Go to [railway.app](https://railway.app) → Login with GitHub
2. Click **New Project → Deploy from GitHub repo**
3. Select `apk-refer-earn-bot`
4. Go to your service → **Variables** tab → Add these:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | Your bot token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Your Telegram user ID |
| `DATABASE_URL` | Connection string from Neon.tech |
| `BOT_USERNAME` | Your bot's username (without @) |
| `NOTIFY_ID` | (Optional) Secondary Telegram ID for notifications |

5. Railway will auto-detect and deploy — **done!**

---

## ⚙️ Bot Setup After Deploy

Once deployed, message your bot:

1. `/start` — verify it's running
2. `/admin` — open admin panel
3. Add force-join channels via **📡 Channels → ➕ Add Channel**
4. Add APKs via **📱 APK Manager → ➕ Add APK** (name + password + point cost)
5. Set referral reward via `/setreward 1`

---

## 📋 Admin Commands

| Command | Description |
|---|---|
| `/admin` | Open admin panel |
| `/setreward N` | Set points earned per referral |
| `/block USER_ID` | Block a user |
| `/unblock USER_ID` | Unblock a user |
| `/addpts USER_ID N` | Add points to user |
| `/rmpts USER_ID N` | Remove points from user |
| `/userinfo USER_ID` | View user details |

---

## 🌟 Features

- **Force Join** — users must join channels before accessing the bot
- **Referral System** — earn points for every friend who joins
- **APK Redemption** — automatic delivery of APK name + password on redemption
- **Admin Panel** — full management via inline buttons
- **Broadcast** — send messages to all users or channels
- **Keep-Alive** — auto pings to prevent sleep on Render free tier

---

## 🔧 Local Development

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values
python run_bot.py
```
