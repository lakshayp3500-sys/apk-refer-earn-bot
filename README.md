# 📱 APK Refer & Earn Bot

A Telegram bot where users earn points by referring friends and redeem them for APKs — fully automatic delivery.

---

## 🚀 Deploy on Railway — 3 Steps Only

### Step 1 — Railway pe Project Banao
1. **[railway.app](https://railway.app)** → Login with GitHub
2. **"New Project"** → **"Deploy from GitHub repo"** → **`apk-refer-earn-bot`** select karo
3. Service deploy hogi → wait karo

### Step 2 — Database Add Karo (1 Click)
1. Apne Railway project mein **"+ New"** click karo
2. **"Database"** → **"Add PostgreSQL"** select karo
3. **Done!** `DATABASE_URL` automatically set ho jaata hai ✅

### Step 3 — Sirf 2 Variables Add Karo
1. Apni bot service pe jao → **"Variables"** tab
2. Sirf ye 2 add karo:

| Variable | Value | Kahan se milega |
|---|---|---|
| `BOT_TOKEN` | `123456:ABCdef...` | [@BotFather](https://t.me/BotFather) se |
| `ADMIN_ID` | `123456789` | [@userinfobot](https://t.me/userinfobot) se |

3. **Optional (referral links ke liye):**

| Variable | Value |
|---|---|
| `BOT_USERNAME` | Bot ka username (@ ke bina) |

4. Variables save karo → **Bot live ho jaega!** 🎉

---

## ⚙️ Bot Setup (Deploy ke Baad)

Bot start hone ke baad apne bot pe jao:

1. `/start` — bot check karo
2. `/admin` — admin panel kholo
3. **📡 Channels** → **➕ Add Channel** — force join channels add karo
4. **📱 APK Manager** → **➕ Add APK** — (naam → password → points) step by step
5. `/setreward 1` — har referral pe kitne points milenge set karo

---

## 📋 Admin Commands

| Command | Description |
|---|---|
| `/admin` | Admin panel kholna |
| `/setreward N` | Referral reward points set karna |
| `/block USER_ID` | User block karna |
| `/unblock USER_ID` | User unblock karna |
| `/addpts USER_ID N` | User ko points add karna |
| `/rmpts USER_ID N` | User ke points hatana |
| `/userinfo USER_ID` | User ki details dekhna |

---

## 🌟 Features

- ✅ **Force Join** — channels join karne ke baad hi bot use hoga
- 🎯 **Referral System** — dosto ko refer karo, points kamao
- 📱 **APK Redemption** — automatic naam + password delivery
- 🛡 **Admin Panel** — full control via buttons
- 📢 **Broadcast** — saare users ya channels ko message bhejo
- 🔁 **Bulk Point Update** — sab APK ke points ek baar mein set karo
