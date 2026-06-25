import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from bot.config import BOT_TOKEN, ADMIN_ID, RENDER_URL
from bot.database import engine, Base
from bot.middlewares.db_middleware import DbSessionMiddleware
from bot.handlers import start, user, admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PING_INTERVAL = 10 * 60


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


async def keep_alive():
    if not RENDER_URL:
        logger.info("RENDER_URL not set — keep-alive disabled.")
        return

    ping_url = RENDER_URL.rstrip("/") + "/api/healthz"
    logger.info(f"Keep-alive started → pinging {ping_url} every 10 min.")

    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            try:
                async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.info(f"Keep-alive ping OK ({resp.status})")
            except Exception as e:
                logger.warning(f"Keep-alive ping failed: {e}")


async def main():
    await create_tables()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(user.router)

    try:
        bot_info = await bot.get_me()
        logger.info(f"Starting bot: @{bot_info.username}")
        await bot.send_message(
            ADMIN_ID,
            f"🤖 <b>Bot Started!</b>\n\n"
            f"@{bot_info.username} is now online.\n"
            f"📱 APK Refer &amp; Earn Bot",
            parse_mode="HTML",
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
