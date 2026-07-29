from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.db_service import (
    get_user, redeem_code, get_user_redemptions,
    get_all_channels, get_reward_per_referral, get_redeem_cost,
    get_available_codes_count,
)
from bot.keyboards.user_kb import (
    main_menu_kb, code_confirm_kb, back_to_menu_kb, support_kb, join_channels_kb
)
from bot.utils.channel_checker import get_missing_channels
from bot.config import BOT_USERNAME

router = Router()

PRODUCT_NAME = "Blinkit 100 off Chocolate"


async def _check_access(message_or_callback, session: AsyncSession, bot: Bot) -> tuple[bool, object | None]:
    if isinstance(message_or_callback, Message):
        uid = message_or_callback.from_user.id
        send = message_or_callback.answer
    else:
        uid = message_or_callback.from_user.id
        send = message_or_callback.message.answer

    user = await get_user(session, uid)
    if not user:
        await send("Please send /start to begin.", parse_mode="HTML")
        return False, None
    if user.blocked:
        await send("🚫 <b>Your account is suspended.</b>", parse_mode="HTML")
        return False, None

    if not user.verified:
        channels = await get_all_channels(session)
        if channels:
            missing = await get_missing_channels(bot, uid, channels)
            if missing:
                await send(
                    "⚠️ <b>Join Required Channels First</b>\n\n"
                    "Please join all required channels before using the bot.",
                    parse_mode="HTML",
                    reply_markup=join_channels_kb(channels),
                )
                return False, None
    return True, user


# ── Profile ────────────────────────────────────────────────────────────────────

@router.message(F.text == "👤 My Profile")
async def show_profile(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    ref_link = (
        f"https://t.me/{BOT_USERNAME}?start={user.telegram_id}"
        if BOT_USERNAME else "Set BOT_USERNAME env var"
    )
    join_str = user.join_date.strftime("%d %b %Y") if user.join_date else "N/A"

    await message.answer(
        f"👤 <b>Your Profile</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>ID:</b> <code>{user.telegram_id}</code>\n"
        f"👤 <b>Name:</b> {user.first_name or 'N/A'}\n"
        f"📅 <b>Joined:</b> {join_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Points:</b> {user.points}\n"
        f"👥 <b>Referrals:</b> {user.referrals}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>Your Refer Link:</b>\n"
        f"<code>{ref_link}</code>",
        parse_mode="HTML",
    )


# ── Refer & Earn ───────────────────────────────────────────────────────────────

@router.message(F.text == "🎯 Refer & Earn")
async def refer_earn(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    ref_link = (
        f"https://t.me/{BOT_USERNAME}?start={user.telegram_id}"
        if BOT_USERNAME else "Set BOT_USERNAME env var"
    )
    reward = await get_reward_per_referral(session)
    cost = await get_redeem_cost(session)

    await message.answer(
        f"🎯 <b>Refer & Earn</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Earn {reward} Point(s)</b> for every friend you refer!\n\n"
        f"📌 <b>How it works:</b>\n"
        f"  1️⃣ Share your unique referral link\n"
        f"  2️⃣ Friend joins & completes setup\n"
        f"  3️⃣ You earn <b>{reward} point(s)</b> instantly\n"
        f"  4️⃣ Collect <b>{cost} points</b> → get 1 free Blinkit code!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 <b>Total Referrals:</b> {user.referrals}\n"
        f"💰 <b>Points Balance:</b> {user.points}",
        parse_mode="HTML",
    )


# ── Get Blinkit Code ───────────────────────────────────────────────────────────

@router.message(F.text == "🛍 Get Blinkit Code")
async def get_code_menu(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    cost = await get_redeem_cost(session)
    available = await get_available_codes_count(session)

    if available == 0:
        await message.answer(
            f"😔 <b>No Codes Available</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"All <b>{PRODUCT_NAME}</b> codes are currently out of stock.\n\n"
            f"Please check back later or contact support.",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb(),
        )
        return

    if user.points < cost:
        needed = cost - user.points
        await message.answer(
            f"💎 <b>{PRODUCT_NAME}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎟 <b>Cost:</b> {cost} Points\n"
            f"💰 <b>Your Balance:</b> {user.points} Points\n"
            f"❌ <b>Need:</b> {needed} more point(s)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📢 Refer <b>{needed}</b> more friend(s) to earn enough points!",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"🛍 <b>{PRODUCT_NAME}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎟 <b>Cost:</b> {cost} Points\n"
        f"💰 <b>Your Balance:</b> {user.points} Points\n"
        f"📦 <b>In Stock:</b> {available} code(s) available\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"After redeeming, you will receive <b>1 unique code</b> that can be used on the Blinkit app.\n\n"
        f"⚠️ Each code is one-time use. Confirm only if you are ready.",
        parse_mode="HTML",
        reply_markup=code_confirm_kb(),
    )


@router.callback_query(F.data == "code_confirm")
async def confirm_redeem(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(callback, session, bot)
    if not ok:
        return

    success, result = await redeem_code(session, user.telegram_id)

    if not success:
        await callback.message.edit_text(
            f"❌ <b>Redemption Failed</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{result}",
            parse_mode="HTML",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer("Redemption failed.", show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ <b>Code Redeemed Successfully!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎟 <b>Your {PRODUCT_NAME} Code:</b>\n\n"
        f"<code>{result}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 <b>How to use:</b>\n"
        f"Open Blinkit app → Cart → Apply Coupon → Enter above code\n\n"
        f"⚠️ This code is for one-time use only. Do not share it.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer("✅ Code sent!", show_alert=False)


@router.callback_query(F.data == "code_cancel")
async def cancel_redeem(callback: CallbackQuery):
    await callback.message.edit_text(
        "❌ <b>Redemption Cancelled.</b>\n\nNo points were deducted.",
        parse_mode="HTML",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


# ── History ────────────────────────────────────────────────────────────────────

@router.message(F.text == "📜 History")
async def show_history(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    redemptions = await get_user_redemptions(session, user.telegram_id)
    if not redemptions:
        await message.answer(
            f"📭 <b>No Redemption History</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"You haven't redeemed any {PRODUCT_NAME} codes yet.\n"
            f"Refer friends to earn points and get started!",
            parse_mode="HTML",
        )
        return

    lines = [f"📜 <b>Redemption History</b>\n\n━━━━━━━━━━━━━━━━━━━━\n"]
    for i, r in enumerate(redemptions[:15], 1):
        date_str = r.date.strftime("%d %b %Y") if r.date else "N/A"
        code_val = r.code.code if r.code else "N/A"
        short_code = code_val[:20] + "…" if len(code_val) > 20 else code_val
        lines.append(
            f"{i}. 🎟 <code>{short_code}</code> — {r.points_spent} pts — {date_str}"
        )

    if len(redemptions) > 15:
        lines.append(f"\n<i>Showing last 15 of {len(redemptions)} redemptions.</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ── Support ────────────────────────────────────────────────────────────────────

@router.message(F.text == "💬 Support")
async def support(message: Message, session: AsyncSession, bot: Bot):
    ok, user = await _check_access(message, session, bot)
    if not ok:
        return

    await message.answer(
        "💬 <b>Support</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Need help? Our support team is here for you.\n\n"
        "📩 Tap the button below to reach us directly.",
        parse_mode="HTML",
        reply_markup=support_kb(),
    )


# ── Misc callbacks ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer(
        "🏠 <b>Main Menu</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
