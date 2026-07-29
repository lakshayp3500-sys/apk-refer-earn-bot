import logging

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.db_service import (
    get_or_create_user, get_all_channels, mark_user_verified,
    process_referral, get_user, create_verification_token,
)
from bot.keyboards.user_kb import (
    join_channels_kb, recheck_channels_kb, main_menu_kb, verify_device_kb,
)
from bot.utils.channel_checker import get_missing_channels
from bot.config import ADMIN_ID, RENDER_URL

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, bot: Bot):
    try:
        # Handle deep-link args (/start <ref_id>)
        text = message.text or "/start"
        args = text.split(maxsplit=1)
        ref_id: int | None = None
        if len(args) > 1:
            try:
                ref_id = int(args[1])
                if ref_id == message.from_user.id:
                    ref_id = None
            except ValueError:
                ref_id = None

        user, is_new = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            referred_by=ref_id if ref_id else None,
        )

        if user.blocked:
            await message.answer(
                "🚫 <b>Access Restricted</b>\n\n"
                "Your account has been suspended.\n"
                "Contact support if you believe this is a mistake.",
                parse_mode="HTML",
            )
            return

        # Already verified — just show main menu
        if user.verified:
            await message.answer(
                f"👋 <b>Welcome back, {message.from_user.first_name or 'there'}!</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Use the menu below to navigate.",
                parse_mode="HTML",
                reply_markup=main_menu_kb(),
            )
            return

        channels = await get_all_channels(session)

        # No channels configured — skip to device verification
        if not channels:
            await _send_device_verify(message, session, ref_id)
            return

        missing = await get_missing_channels(bot, message.from_user.id, channels)
        if not missing:
            await _send_device_verify(message, session, ref_id)
            return

        await message.answer(
            f"👋 <b>Welcome, {message.from_user.first_name or 'there'}!</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔐 <b>Step 1 of 2 — Join Channels</b>\n\n"
            f"Join all <b>{len(channels)}</b> channel(s) below, then tap "
            f"<b>✅ I've Joined All Channels</b>.",
            parse_mode="HTML",
            reply_markup=join_channels_kb(channels),
        )

    except Exception as exc:
        logger.exception("Unhandled error in cmd_start for user %s: %s", message.from_user.id, exc)
        try:
            await message.answer(
                "⚠️ <b>Something went wrong.</b>\n\n"
                "Please try <b>/start</b> again in a few seconds.\n"
                "If the issue persists, contact support.",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data == "check_join")
async def check_join(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    try:
        user = await get_user(session, callback.from_user.id)
        if not user:
            await callback.answer("Please send /start first.", show_alert=True)
            return

        # Already verified — no need to go through check again
        if user.verified:
            await callback.message.answer(
                "✅ <b>You are already verified!</b>\n\nUse the menu below.",
                parse_mode="HTML",
                reply_markup=main_menu_kb(),
            )
            await callback.answer()
            return

        channels = await get_all_channels(session)
        if not channels:
            await _send_device_verify_cb(callback, session, user.referred_by)
            return

        missing = await get_missing_channels(bot, callback.from_user.id, channels)
        if missing:
            await callback.message.edit_text(
                "⚠️ <b>Channels Not Joined Yet</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"You still need to join <b>{len(missing)}</b> channel(s).\n"
                "Join them below and tap <b>🔄 Check Again</b>.",
                parse_mode="HTML",
                reply_markup=recheck_channels_kb(missing),
            )
            await callback.answer("❌ You haven't joined all channels yet.", show_alert=True)
            return

        await _send_device_verify_cb(callback, session, user.referred_by)

    except Exception as exc:
        logger.exception("Unhandled error in check_join for user %s: %s", callback.from_user.id, exc)
        await callback.answer("⚠️ An error occurred. Please send /start again.", show_alert=True)


# ── Device Verification Helpers ────────────────────────────────────────────────

async def _send_device_verify(message: Message, session: AsyncSession, ref_id: int | None):
    """Send device verification link after channels are joined."""
    if not RENDER_URL:
        # Fallback: no RENDER_URL set — skip device verify, just verify normally
        await mark_user_verified(session, message.from_user.id)
        if ref_id:
            await process_referral(session, ref_id, message.from_user.id)
        await message.answer(
            "✅ <b>All Done! Welcome!</b>\n\nUse the menu below to get started.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        return

    token = await create_verification_token(session, message.from_user.id, ref_id)
    base = RENDER_URL if RENDER_URL.startswith("http") else f"https://{RENDER_URL}"
    verify_url = f"{base.rstrip('/')}/verify/{token}"

    await message.answer(
        "🎉 <b>All Channels Joined!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔐 <b>Step 2 of 2 — Verify Your Device</b>\n\n"
        "Tap the button below to verify your device.\n"
        "This protects against fake referrals.\n\n"
        "⏳ Link expires in <b>30 minutes</b>.",
        parse_mode="HTML",
        reply_markup=verify_device_kb(verify_url),
    )


async def _send_device_verify_cb(callback: CallbackQuery, session: AsyncSession, ref_id: int | None):
    """Same as above but from a callback query."""
    if not RENDER_URL:
        await mark_user_verified(session, callback.from_user.id)
        if ref_id:
            await process_referral(session, ref_id, callback.from_user.id)
        await callback.message.edit_text(
            "✅ <b>All Done! Welcome!</b>",
            parse_mode="HTML",
        )
        await callback.message.answer(
            "🏠 Use the menu below.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    token = await create_verification_token(session, callback.from_user.id, ref_id)
    base = RENDER_URL if RENDER_URL.startswith("http") else f"https://{RENDER_URL}"
    verify_url = f"{base.rstrip('/')}/verify/{token}"

    await callback.message.edit_text(
        "🎉 <b>All Channels Joined!</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔐 <b>Step 2 of 2 — Verify Your Device</b>\n\n"
        "Tap the button below to verify your device.\n"
        "This protects against fake referrals.\n\n"
        "⏳ Link expires in <b>30 minutes</b>.",
        parse_mode="HTML",
        reply_markup=verify_device_kb(verify_url),
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.answer(
        "🏠 <b>Main Menu</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
