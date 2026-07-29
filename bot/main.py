import asyncio
import logging
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from bot.config import BOT_TOKEN, ADMIN_ID, RENDER_URL
from bot.database import engine, Base, AsyncSessionLocal
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.handlers import start, user, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PING_INTERVAL = 10 * 60  # 10 minutes

# ── Verification HTML page ─────────────────────────────────────────────────────

VERIFY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blinkit — Device Verification</title>
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
         background:#f0fdf4;min-height:100vh;display:flex;align-items:center;justify-content:center;}
    .card{background:#fff;border-radius:24px;padding:44px 32px;max-width:360px;
          width:92%;text-align:center;box-shadow:0 4px 32px rgba(12,131,31,.12);}
    .logo{font-size:52px;margin-bottom:6px}
    .brand{font-size:26px;font-weight:800;color:#0c831f;letter-spacing:-.5px}
    .tagline{font-size:13px;color:#aaa;margin-bottom:36px;margin-top:2px}
    .spinner{width:52px;height:52px;border:4px solid #dcfce7;border-top-color:#0c831f;
             border-radius:50%;animation:spin .75s linear infinite;margin:0 auto 18px}
    @keyframes spin{to{transform:rotate(360deg)}}
    .icon{font-size:52px;margin-bottom:12px}
    .status{font-size:17px;font-weight:700;color:#1a1a1a;margin-bottom:8px}
    .sub{font-size:13px;color:#666;line-height:1.6}
    .badge{display:inline-block;background:#f0fdf4;color:#0c831f;border:1.5px solid #86efac;
           border-radius:999px;padding:4px 14px;font-size:12px;font-weight:600;margin-bottom:20px}
    .hidden{display:none}
    .warn{color:#b45309}
    .err{color:#dc2626}
  </style>
</head>
<body>
<div class="card">
  <div class="logo">🛒</div>
  <div class="brand">Blinkit</div>
  <div class="tagline">100 off Chocolate — Refer &amp; Earn</div>

  <div id="verifying">
    <div class="badge">🔐 Device Check</div>
    <div class="spinner"></div>
    <div class="status">Verifying your device…</div>
    <div class="sub">Please wait, do not close this page.</div>
  </div>

  <div id="success" class="hidden">
    <div class="icon">✅</div>
    <div class="status" style="color:#0c831f">Device Verified!</div>
    <div class="sub">You're all set! Close this page and return to the bot to get started.</div>
  </div>

  <div id="duplicate" class="hidden">
    <div class="icon">⚠️</div>
    <div class="status warn">Same Device Detected</div>
    <div class="sub">This device is already linked to another Telegram account.<br><br>
    You can still use the bot, but <strong>referral points will not be credited</strong> to your inviter.</div>
  </div>

  <div id="error" class="hidden">
    <div class="icon">❌</div>
    <div class="status err">Verification Failed</div>
    <div class="sub" id="err-msg">Link expired or already used. Send /start in the bot to get a new link.</div>
  </div>
</div>

<script>
const TOKEN = '__TOKEN__';

function fp() {
  const p = [
    navigator.userAgent,
    navigator.language || '',
    screen.width + 'x' + screen.height + 'x' + (screen.colorDepth || 24),
    navigator.platform || '',
    navigator.hardwareConcurrency || 0,
    (Intl.DateTimeFormat().resolvedOptions().timeZone || ''),
    navigator.maxTouchPoints || 0,
  ];
  try {
    const c = document.createElement('canvas');
    const g = c.getContext('2d');
    g.textBaseline = 'top';
    g.font = '14px Arial';
    g.fillStyle = '#0c831f';
    g.fillText('Blinkit100\u{1F6D2}', 2, 2);
    p.push(c.toDataURL().slice(-64));
  } catch(e){}
  // Simple hash
  const s = p.join('|||');
  let h = 0;
  for(let i=0;i<s.length;i++){h=(Math.imul(31,h)+s.charCodeAt(i))|0;}
  return (h>>>0).toString(16) + '_' + s.length;
}

function show(id) {
  ['verifying','success','duplicate','error'].forEach(s=>{
    document.getElementById(s).classList.toggle('hidden', s!==id);
  });
}

async function verify() {
  try {
    const res = await fetch('/verify/submit', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ token: TOKEN, fingerprint: fp() })
    });
    const d = await res.json();
    if (d.success) {
      show(d.is_duplicate ? 'duplicate' : 'success');
    } else {
      document.getElementById('err-msg').textContent = d.error || 'Verification failed.';
      show('error');
    }
  } catch(e) {
    document.getElementById('err-msg').textContent = 'Network error. Please try again.';
    show('error');
  }
}

setTimeout(verify, 900);
</script>
</body>
</html>"""


# ── DB & Web server ────────────────────────────────────────────────────────────

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


async def verify_page(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    html = VERIFY_HTML.replace("__TOKEN__", token)
    return web.Response(text=html, content_type="text/html")


async def verify_submit(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"success": False, "error": "Bad request."}, status=400)

    token = data.get("token", "")
    fingerprint = data.get("fingerprint", "unknown")
    user_agent = request.headers.get("User-Agent", "")

    # Get real IP (Render puts it in X-Forwarded-For)
    x_fwd = request.headers.get("X-Forwarded-For", "")
    ip_address = x_fwd.split(",")[0].strip() if x_fwd else (request.remote or "unknown")

    async with AsyncSessionLocal() as session:
        from bot.services.db_service import process_device_verification, get_user, get_reward_per_referral
        result = await process_device_verification(session, token, ip_address, fingerprint, user_agent)

    if result.get("success"):
        bot: Bot = request.app["bot"]
        telegram_id = result["telegram_id"]
        referrer_id = result.get("referrer_id")
        is_duplicate = result["is_duplicate"]
        referral_given = result.get("referral_given", False)

        from bot.keyboards.user_kb import main_menu_kb

        try:
            if is_duplicate:
                # User: can still use bot, but referrer gets no points
                await bot.send_message(
                    telegram_id,
                    "⚠️ <b>Same Device Detected</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "This device is already linked to another account.\n"
                    "Your referral will <b>not</b> be counted.\n\n"
                    "You can still use the bot normally. Welcome!",
                    parse_mode="HTML",
                    reply_markup=main_menu_kb(),
                )
            else:
                # User: fresh device, all good
                await bot.send_message(
                    telegram_id,
                    "✅ <b>Device Verified! Welcome!</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🎉 You're all set to use the bot.\n"
                    "Refer friends to earn points & get Blinkit codes!",
                    parse_mode="HTML",
                    reply_markup=main_menu_kb(),
                )

            # Notify referrer
            if referrer_id:
                async with AsyncSessionLocal() as s2:
                    from bot.services.db_service import get_user as gu, get_reward_per_referral as grr
                    referrer = await gu(s2, referrer_id)
                    reward = await grr(s2)
                    if referrer:
                        if referral_given:
                            # Points given — good news
                            await bot.send_message(
                                referrer_id,
                                f"🎉 <b>You got {reward} Point!</b>\n\n"
                                "━━━━━━━━━━━━━━━━━━━━\n\n"
                                "A new user joined & verified via your link!\n\n"
                                f"💎 <b>+{reward} point(s)</b> added to your balance.\n"
                                f"🏆 <b>Total Points:</b> {referrer.points}",
                                parse_mode="HTML",
                            )
                        else:
                            # Same device — referrer gets warning
                            await bot.send_message(
                                referrer_id,
                                "⚠️ <b>Your One Refer Detected — Same Device</b>\n\n"
                                "━━━━━━━━━━━━━━━━━━━━\n\n"
                                "Someone joined via your link but their device was already\n"
                                "linked to another account.\n\n"
                                "❌ <b>No points credited</b> for this referral.",
                                parse_mode="HTML",
                            )
        except Exception as e:
            logger.warning(f"Bot message after verify failed: {e}")

    return web.json_response(result)


async def start_webserver(bot: Bot):
    port = int(os.getenv("PORT", "8080"))

    async def health(request):
        return web.Response(text="OK")

    app = web.Application()
    app["bot"] = bot  # Make bot accessible in web handlers
    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)
    app.router.add_get("/verify/{token}", verify_page)
    app.router.add_post("/verify/submit", verify_submit)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server running on port {port}")


async def keep_alive():
    if not RENDER_URL:
        logger.info("RENDER_URL not set — keep-alive disabled.")
        return
    base = RENDER_URL if RENDER_URL.startswith("http") else f"https://{RENDER_URL}"
    ping_url = base.rstrip("/") + "/healthz"
    logger.info(f"Keep-alive → pinging {ping_url} every 10 min.")
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.info(f"Keep-alive ping OK ({resp.status})")
            except Exception as e:
                logger.warning(f"Keep-alive ping failed: {e}")


# ── Entry point ────────────────────────────────────────────────────────────────

async def main():
    await create_tables()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(user.router)

    await start_webserver(bot)

    try:
        bot_info = await bot.get_me()
        logger.info(f"Starting bot: @{bot_info.username}")
        await bot.send_message(
            ADMIN_ID,
            f"🤖 <b>Bot Started!</b>\n\n"
            f"@{bot_info.username} is now online.\n"
            f"🛍 Blinkit 100 off Chocolate Bot",
        )
    except Exception as e:
        logger.warning(f"Could not send startup message: {e}")

    asyncio.create_task(keep_alive())

    logger.info("Polling started.")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
