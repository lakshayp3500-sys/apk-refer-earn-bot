# 📱 APK Refer & Earn Bot

A Telegram bot where users earn points by referring friends and redeem them for APKs — fully automatic delivery.

---

## 🚀 Deploy on Render — Blueprint (Automatic Setup)

### Step 1 — Bot Token Lo
1. **[@BotFather](https://t.me/BotFather)** → `/newbot` → token copy karo

### Step 2 — Admin ID Lo
1. **[@userinfobot](https://t.me/userinfobot)** → `/start` → "Id:" wala number copy karo

### Step 3 — Render pe Deploy Karo
1. **[render.com](https://render.com)** → Login / Sign up
2. **"New"** → **"Blueprint"** click karo
3. GitHub repo connect karo → **`apk-refer-earn-bot`** select karo
4. Render automatically `render.yaml` detect karega
5. **Database aur Service dono automatically ban jayenge** ✅
6. Sirf ye 2 fields fill karo:
   - `BOT_TOKEN` → Step 1 ka token
   - `ADMIN_ID` → Step 2 ka ID
7. **"Apply"** click karo → Deploy shuru! 🚀

> `DATABASE_URL` aur `RENDER_URL` automatically set ho jaate hain — kuch karna nahi!

---

## ⚙️ Bot Setup (Deploy ke Baad)

1. `/admin` — admin panel
2. **📡 Channels** → **➕ Add Channel** — force join channels add karo
3. **📱 APK Manager** → **➕ Add APK** — naam, password, points
4. `/setreward 1` — referral reward set karo

---

## 📋 Admin Commands

| Command | Description |
|---|---|
| `/admin` | Admin panel |
| `/setreward N` | Referral reward points set karna |
| `/block USER_ID` | User block karna |
| `/unblock USER_ID` | User unblock karna |
| `/addpts USER_ID N` | Points add karna |
| `/rmpts USER_ID N` | Points hatana |
| `/userinfo USER_ID` | User details dekhna |

---

## 🌟 Features

- ✅ **Force Join** — channels join karne ke baad hi bot use hoga
- 🎯 **Referral System** — dosto ko refer karo, points kamao
- 📱 **APK Redemption** — automatic naam + password delivery
- 🛡 **Admin Panel** — full control via buttons
- 📢 **Broadcast** — saare users ya channels ko message bhejo
- ⏰ **Keep-Alive** — har 10 min mein auto ping, bot kabhi nahi sota
