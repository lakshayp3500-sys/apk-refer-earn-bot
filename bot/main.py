import asyncio
import logging
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ErrorEvent

from bot.config import BOT_TOKEN, ADMIN_ID, RENDER_URL
from bot.database import engine, Base, AsyncSessionLocal
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.handlers import start, user, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PING_INTERVAL = 10 * 60  # 10 minutes

# ── Verification HTML page ─────────────────────────────────────────────────────
# Fingerprint strategy (3-layer, hardware-level):
#   Layer 1 — Canvas 2D  : GPU font/path rendering differences
#   Layer 2 — WebGL      : exact GPU model, driver version, renderer string
#   Layer 3 — AudioContext: audio hardware oscillator differences
# Even two identical phone models produce different fingerprints because:
#   • GPU drivers installed at factory differ per unit
#   • Audio hardware calibration differs per unit
# IP is stored for logs only — NEVER used for duplicate detection.

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
    <div class="sub">You're all set! Close this page and return to the bot.</div>
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

// ── FNV-1a 32-bit hash (better avalanche than djb2) ──────────────────────────
function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (Math.imul(h, 0x01000193)) >>> 0;
  }
  return h.toString(16).padStart(8, '0');
}

// ── Layer 1: Canvas 2D fingerprint ───────────────────────────────────────────
// Draws text, emoji, gradients, arcs. GPU font-rendering path differs per device.
function canvasFP() {
  try {
    const c = document.createElement('canvas');
    c.width = 240; c.height = 60;
    const g = c.getContext('2d');
    g.textBaseline = 'alphabetic';
    g.fillStyle = '#f60';
    g.fillRect(120, 1, 62, 20);
    g.fillStyle = '#069';
    g.font = '15px Arial';
    g.fillText('Blinkit🛒100off', 2, 15);
    g.fillStyle = 'rgba(102,200,0,0.7)';
    g.font = '12px Georgia';
    g.fillText('refer&earn ✓', 4, 35);
    g.beginPath();
    g.arc(50, 50, 10, 0, Math.PI * 2);
    g.fillStyle = '#0c831f';
    g.fill();
    // Gradient
    const grad = g.createLinearGradient(0, 0, 240, 0);
    grad.addColorStop(0, '#fff'); grad.addColorStop(1, '#0c831f');
    g.fillStyle = grad;
    g.fillRect(0, 55, 240, 5);
    return fnv1a(c.toDataURL().slice(-128));
  } catch(e) { return 'no2d'; }
}

// ── Layer 2: WebGL fingerprint ───────────────────────────────────────────────
// Renderer string contains exact GPU model & driver version.
// Even same phone models can have different GPU drivers per unit.
function webglFP() {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
    if (!gl) return 'nogl';
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    const renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : 'hidden';
    const vendor   = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL)   : 'hidden';
    // Also draw a scene — the pixel output differs per GPU
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, 'attribute vec2 p;void main(){gl_Position=vec4(p,0,1);}');
    gl.compileShader(vs);
    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, 'precision mediump float;void main(){gl_FragColor=vec4(.3,.6,.9,1.);}');
    gl.compileShader(fs);
    const prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    gl.useProgram(prog);
    c.width = 16; c.height = 16;
    gl.viewport(0, 0, 16, 16);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    const pixels = new Uint8Array(16 * 16 * 4);
    gl.readPixels(0, 0, 16, 16, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    const pixHash = fnv1a(Array.from(pixels.slice(0, 64)).join(','));
    return fnv1a(renderer + '|' + vendor + '|' + pixHash);
  } catch(e) { return 'nogl'; }
}

// ── Layer 3: AudioContext fingerprint ────────────────────────────────────────
// Oscillator output varies by audio hardware even on same phone model.
function audioCB(hash) {
  try {
    const ctx = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(1, 44100, 44100);
    const osc = ctx.createOscillator();
    osc.type = 'triangle';
    osc.frequency.value = 10000;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -50; comp.knee.value = 40;
    comp.ratio.value = 12; comp.reduction; comp.attack.value = 0; comp.release.value = 0.25;
    osc.connect(comp); comp.connect(ctx.destination);
    osc.start(0);
    ctx.startRendering();
    ctx.oncomplete = function(e) {
      const buf = e.renderedBuffer.getChannelData(0);
      let sum = 0;
      for (let i = 4500; i < 5000; i++) sum += Math.abs(buf[i]);
      hash.audio = fnv1a(sum.toString());
      finish(hash);
    };
  } catch(e) {
    hash.audio = 'noaudio';
    finish(hash);
  }
}

// ── Assemble final fingerprint ───────────────────────────────────────────────
function finish(hash) {
  const combined = [
    hash.canvas,
    hash.webgl,
    hash.audio,
    hash.screen,
    hash.hw,
    hash.tz,
    hash.lang,
    hash.touch,
    hash.dpr,
    hash.mem,
  ].join('::');
  const final = String(fnv1a(combined));  // FIX: convert to string, DB column is String(256)
  sendVerify(final);
}

function show(id) {
  ['verifying','success','duplicate','error'].forEach(s=>{
    document.getElementById(s).classList.toggle('hidden', s!==id);
  });
}

async function sendVerify(fingerprint) {
  try {
    const res = await fetch('/verify/submit', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ token: TOKEN, fingerprint: fingerprint })
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

// ── Start fingerprinting ─────────────────────────────────────────────────────
setTimeout(function() {
  const hash = {
    canvas : canvasFP(),
    webgl  : webglFP(),
    audio  : null,
    screen : fnv1a(screen.width + 'x' + screen.height + 'x' + (screen.colorDepth||24)),
    hw     : String(navigator.hardwareConcurrency || 0),
    tz     : fnv1a(Intl.DateTimeFormat().resolvedOptions().timeZone || ''),
    lang   : fnv1a(navigator.language || ''),
    touch  : String(navigator.maxTouchPoints || 0),
    dpr    : String(Math.round((window.devicePixelRatio || 1) * 10)),
    mem    : String(navigator.deviceMemory || 0),
  };
  audioCB(hash); // async; calls finish() when done
}, 300);
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

    # Store IP for logs only — NOT used for duplicate detection
    x_fwd = request.headers.get("X-Forwarded-For", "")
    ip_address = x_fwd.split(",")[0].strip() if x_fwd else (request.remote or "unknown")

    async with AsyncSessionLocal() as session:
        from bot.services.db_service import process_device_verification
        result = await process_device_verification(
            session, token, ip_address, fingerprint, user_agent
        )

    if result.get("success"):
        bot: Bot = request.app["bot"]
        telegram_id  = result["telegram_id"]
        referrer_id  = result.get("referrer_id")
        is_duplicate = result["is_duplicate"]
        referral_given = result.get("referral_given", False)
        user_name    = result.get("user_name", "N/A")
        user_uname   = result.get("user_username", "no username")

        from bot.keyboards.user_kb import main_menu_kb

        # ── Message to the new user ──────────────────────────────────────────
        try:
            if is_duplicate:
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
                await bot.send_message(
                    telegram_id,
                    "✅ <b>Device Verified! Welcome!</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    "🎉 You're all set to use the bot.\n"
                    "Refer friends to earn points & get Blinkit codes!",
                    parse_mode="HTML",
                    reply_markup=main_menu_kb(),
                )
        except Exception as e:
            logger.warning(f"User message after verify failed: {e}")

        # ── Message to the referrer ──────────────────────────────────────────
        if referrer_id:
            try:
                async with AsyncSessionLocal() as s2:
                    from bot.services.db_service import get_user as gu, get_reward_per_referral as grr
                    referrer = await gu(s2, referrer_id)
                    reward   = await grr(s2)
                if referrer:
                    if referral_given:
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
                        await bot.send_message(
                            referrer_id,
                            "⚠️ <b>Your One Refer Detected — Same Device</b>\n\n"
                            "━━━━━━━━━━━━━━━━━━━━\n\n"
                            "Someone joined via your link but their device\n"
                            "was already linked to another account.\n\n"
                            "❌ <b>No points credited</b> for this referral.",
                            parse_mode="HTML",
                        )
            except Exception as e:
                logger.warning(f"Referrer message after verify failed: {e}")

        # ── Admin notification ───────────────────────────────────────────────
        try:
            if is_duplicate:
                admin_text = (
                    "⚠️ <b>New User Join — Same Device</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👤 <b>Name:</b> {user_name}\n"
                    f"🔗 <b>Username:</b> {user_uname}\n"
                    f"🆔 <b>ID:</b> <code>{telegram_id}</code>\n\n"
                    "❌ Device fingerprint matched another account.\n"
                    "No points given to referrer."
                )
            else:
                admin_text = (
                    "✅ <b>New User Verified</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👤 <b>Name:</b> {user_name}\n"
                    f"🔗 <b>Username:</b> {user_uname}\n"
                    f"🆔 <b>ID:</b> <code>{telegram_id}</code>\n\n"
                    "✅ Fresh device. Referral counted."
                    if referral_given else
                    "✅ <b>New User Verified</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👤 <b>Name:</b> {user_name}\n"
                    f"🔗 <b>Username:</b> {user_uname}\n"
                    f"🆔 <b>ID:</b> <code>{telegram_id}</code>\n\n"
                    "✅ Fresh device. No referrer."
                )
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Admin notification failed: {e}")

    return web.json_response(result)


async def start_webserver(bot: Bot):
    port = int(os.getenv("PORT", "8080"))

    async def health(request):
        return web.Response(text="OK")

    app = web.Application()
    app["bot"] = bot
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


# ── Global Error Handler ──────────────────────────────────────────────────────
async def global_error_handler(event: ErrorEvent, bot: Bot) -> None:
    """Catch all unhandled handler exceptions, log + notify admin."""
    exception = event.exception
    logger.exception("Unhandled handler exception: %s", exception)
    try:
        short = str(exception)[:300]
        await bot.send_message(
            ADMIN_ID,
            f"⚠️ <b>Bot Error</b>\n\n<code>{short}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass


async def main():
    await create_tables()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(user.router)
    dp.errors.register(global_error_handler)

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
