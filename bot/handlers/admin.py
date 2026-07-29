from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import ADMIN_ID
from bot.services.db_service import (
    get_stats, get_all_users, get_user, block_user, unblock_user,
    get_all_channels, add_channel, remove_channel,
    get_all_codes, add_codes, remove_code, clear_unused_codes,
    get_setting, set_setting, get_reward_per_referral, get_redeem_cost,
)
from bot.keyboards.admin_kb import (
    admin_panel_kb, admin_channels_kb, admin_codes_kb,
    admin_remove_channels_kb, admin_remove_code_kb,
    admin_back_kb, admin_broadcast_type_kb, admin_confirm_clear_kb,
)

router = Router()

PRODUCT_NAME = "Blinkit 100 off Chocolate"


class AdminStates(StatesGroup):
    waiting_channel = State()
    waiting_codes = State()          # Bulk codes input (one per line)
    waiting_broadcast_msg = State()
    waiting_broadcast_channel_msg = State()


# ── Admin Entry ────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    stats = await get_stats(session)
    await message.answer(
        f"🛡 <b>Admin Panel</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {stats['total_users']}\n"
        f"✅ <b>Verified:</b> {stats['verified_users']}\n"
        f"🎯 <b>Total Referrals:</b> {stats['total_referrals']}\n"
        f"🎟 <b>Codes Redeemed:</b> {stats['total_redemptions']}\n"
        f"📦 <b>Codes in Stock:</b> {stats['available_codes']}",
        parse_mode="HTML",
        reply_markup=admin_panel_kb(),
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.clear()
    stats = await get_stats(session)
    await callback.message.edit_text(
        f"🛡 <b>Admin Panel</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {stats['total_users']}\n"
        f"✅ <b>Verified:</b> {stats['verified_users']}\n"
        f"🎯 <b>Total Referrals:</b> {stats['total_referrals']}\n"
        f"🎟 <b>Codes Redeemed:</b> {stats['total_redemptions']}\n"
        f"📦 <b>Codes in Stock:</b> {stats['available_codes']}",
        parse_mode="HTML",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    stats = await get_stats(session)
    reward = await get_reward_per_referral(session)
    cost = await get_redeem_cost(session)
    await callback.message.edit_text(
        f"📊 <b>Statistics</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>Total Users:</b> {stats['total_users']}\n"
        f"✅ <b>Verified Users:</b> {stats['verified_users']}\n"
        f"🎯 <b>Total Referrals:</b> {stats['total_referrals']}\n"
        f"🎟 <b>Codes Redeemed:</b> {stats['total_redemptions']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Available Codes:</b> {stats['available_codes']}\n"
        f"🗃 <b>Total Codes:</b> {stats['total_codes']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Reward/Referral:</b> {reward} pt(s)\n"
        f"🛍 <b>Redeem Cost:</b> {cost} pt(s)",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


# ── Channels ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.message.edit_text(
        "📡 <b>Channel Manager</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Manage force-join channels:",
        parse_mode="HTML",
        reply_markup=admin_channels_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_channel")
async def admin_add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_channel)
    await callback.message.edit_text(
        "📡 <b>Add Channel</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the channel username (e.g. <code>@mychannel</code>).\n\n"
        "<i>Bot must be an admin in that channel.</i>",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_channel)
async def admin_add_channel_receive(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    raw = message.text.strip()
    username = raw if raw.startswith("@") else f"@{raw}"
    try:
        chat = await bot.get_chat(username)
        ch = await add_channel(session, str(chat.id), username, chat.title)
        await message.answer(
            f"✅ <b>Channel Added!</b>\n\n"
            f"📢 <b>{chat.title}</b> (<code>{username}</code>)",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    except Exception as e:
        await message.answer(
            f"❌ <b>Failed to add channel.</b>\n\n"
            f"Make sure the bot is an admin and the username is correct.\n\n"
            f"<code>{e}</code>",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )


@router.callback_query(F.data == "admin_remove_channel")
async def admin_remove_channel(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    channels = await get_all_channels(session)
    if not channels:
        await callback.answer("No channels to remove.", show_alert=True)
        return
    await callback.message.edit_text(
        "➖ <b>Remove Channel</b>\n\nSelect a channel to remove:",
        parse_mode="HTML",
        reply_markup=admin_remove_channels_kb(channels),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_ch_"))
async def admin_delete_channel(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    ch_id = int(callback.data.split("_")[-1])
    removed = await remove_channel(session, ch_id)
    await callback.answer("✅ Channel removed." if removed else "❌ Not found.", show_alert=True)
    channels = await get_all_channels(session)
    if channels:
        await callback.message.edit_reply_markup(reply_markup=admin_remove_channels_kb(channels))
    else:
        await callback.message.edit_text(
            "📡 No channels remaining.", parse_mode="HTML", reply_markup=admin_back_kb()
        )


@router.callback_query(F.data == "admin_list_channels")
async def admin_list_channels(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    channels = await get_all_channels(session)
    if not channels:
        await callback.answer("No channels configured.", show_alert=True)
        return
    lines = ["📡 <b>Configured Channels</b>\n"]
    for i, ch in enumerate(channels, 1):
        lines.append(f"{i}. {ch.channel_title or ''} <code>{ch.channel_username}</code>")
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=admin_channels_kb()
    )
    await callback.answer()


# ── Code Manager ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_codes")
async def admin_codes_menu(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    stats = await get_stats(session)
    await callback.message.edit_text(
        f"🎟 <b>Code Manager — {PRODUCT_NAME}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Available Codes:</b> {stats['available_codes']}\n"
        f"✅ <b>Used Codes:</b> {stats['total_redemptions']}\n"
        f"🗃 <b>Total Codes:</b> {stats['total_codes']}",
        parse_mode="HTML",
        reply_markup=admin_codes_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_codes")
async def admin_add_codes_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_codes)
    await callback.message.edit_text(
        f"➕ <b>Add Codes</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Send your <b>{PRODUCT_NAME}</b> codes — <b>one per line</b>:\n\n"
        f"<code>CODE1\nCODE2\nCODE3</code>\n\n"
        f"Duplicate codes will be skipped automatically.",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_codes)
async def admin_add_codes_receive(message: Message, state: FSMContext, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    lines = message.text.strip().splitlines()
    added, skipped = await add_codes(session, lines)
    await message.answer(
        f"✅ <b>Codes Added!</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>Added:</b> {added}\n"
        f"⚠️ <b>Skipped (duplicates):</b> {skipped}\n"
        f"📊 <b>Total processed:</b> {added + skipped}",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )


@router.callback_query(F.data == "admin_list_codes")
async def admin_list_codes(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    stats = await get_stats(session)
    codes = await get_all_codes(session)
    available = [c for c in codes if not c.is_used]
    used = [c for c in codes if c.is_used]

    lines = [
        f"📋 <b>Code Stock Overview</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>Available:</b> {len(available)}\n"
        f"✅ <b>Used:</b> {len(used)}\n"
        f"🗃 <b>Total:</b> {len(codes)}\n\n"
    ]
    if available:
        lines.append("🔑 <b>Next codes to be given (first 5):</b>")
        for c in available[:5]:
            short = c.code[:25] + "…" if len(c.code) > 25 else c.code
            lines.append(f"  • <code>{short}</code>")
    await callback.message.edit_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=admin_codes_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_remove_code")
async def admin_remove_code_menu(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    codes = await get_all_codes(session)
    available = [c for c in codes if not c.is_used]
    if not available:
        await callback.answer("No unused codes to remove.", show_alert=True)
        return
    await callback.message.edit_text(
        "➖ <b>Remove Code</b>\n\nSelect an unused code to delete:",
        parse_mode="HTML",
        reply_markup=admin_remove_code_kb(available),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_code_"))
async def admin_delete_code(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    code_id = int(callback.data.split("_")[-1])
    removed = await remove_code(session, code_id)
    await callback.answer("✅ Code removed." if removed else "❌ Could not remove (already used?).", show_alert=True)
    codes = await get_all_codes(session)
    available = [c for c in codes if not c.is_used]
    if available:
        await callback.message.edit_reply_markup(reply_markup=admin_remove_code_kb(available))
    else:
        await callback.message.edit_text(
            "📭 No unused codes remaining.", parse_mode="HTML", reply_markup=admin_back_kb()
        )


@router.callback_query(F.data == "admin_clear_codes")
async def admin_clear_codes_confirm_prompt(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    stats = await get_stats(session)
    await callback.message.edit_text(
        f"⚠️ <b>Clear All Unused Codes?</b>\n\n"
        f"This will permanently delete <b>{stats['available_codes']}</b> unused code(s).\n\n"
        f"Used codes will NOT be affected.",
        parse_mode="HTML",
        reply_markup=admin_confirm_clear_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_clear_codes_confirm")
async def admin_clear_codes_execute(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    count = await clear_unused_codes(session)
    await callback.message.edit_text(
        f"🗑 <b>Done!</b> {count} unused code(s) cleared.",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


# ── Point Settings ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_points")
async def admin_points_menu(callback: CallbackQuery, session: AsyncSession):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    reward = await get_reward_per_referral(session)
    cost = await get_redeem_cost(session)
    await callback.message.edit_text(
        f"⚙️ <b>Point Settings</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>Reward per Referral:</b> {reward} pt(s)\n"
        f"🛍 <b>Redeem Cost (per code):</b> {cost} pt(s)\n\n"
        f"Use commands to change:\n"
        f"<code>/setreward N</code> — set referral reward\n"
        f"<code>/setcost N</code> — set redeem cost",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(Command("setreward"))
async def cmd_set_reward(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit() or int(parts[1]) < 1:
        await message.answer("Usage: <code>/setreward N</code> (N ≥ 1)", parse_mode="HTML")
        return
    await set_setting(session, "reward_per_referral", parts[1])
    await message.answer(f"✅ Referral reward set to <b>{parts[1]}</b> pt(s).", parse_mode="HTML")


@router.message(Command("setcost"))
async def cmd_set_cost(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit() or int(parts[1]) < 1:
        await message.answer("Usage: <code>/setcost N</code> (N ≥ 1)", parse_mode="HTML")
        return
    await set_setting(session, "redeem_cost", parts[1])
    await message.answer(f"✅ Redeem cost set to <b>{parts[1]}</b> pt(s).", parse_mode="HTML")


# ── Users ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.message.edit_text(
        "👥 <b>User Management</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Available commands:\n\n"
        "<code>/userinfo USER_ID</code> — view user details\n"
        "<code>/block USER_ID</code> — block a user\n"
        "<code>/unblock USER_ID</code> — unblock a user\n"
        "<code>/addpts USER_ID N</code> — add points\n"
        "<code>/rmpts USER_ID N</code> — remove points",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(Command("userinfo"))
async def cmd_userinfo(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Usage: <code>/userinfo USER_ID</code>", parse_mode="HTML")
        return
    user = await get_user(session, int(parts[1]))
    if not user:
        await message.answer("❌ User not found.", parse_mode="HTML")
        return
    join_str = user.join_date.strftime("%d %b %Y") if user.join_date else "N/A"
    await message.answer(
        f"👤 <b>User Info</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user.telegram_id}</code>\n"
        f"👤 <b>Name:</b> {user.first_name or 'N/A'}\n"
        f"🔗 <b>Username:</b> @{user.username or 'N/A'}\n"
        f"📅 <b>Joined:</b> {join_str}\n\n"
        f"💎 <b>Points:</b> {user.points}\n"
        f"👥 <b>Referrals:</b> {user.referrals}\n"
        f"✅ <b>Verified:</b> {'Yes' if user.verified else 'No'}\n"
        f"🚫 <b>Blocked:</b> {'Yes' if user.blocked else 'No'}",
        parse_mode="HTML",
    )


@router.message(Command("block"))
async def cmd_block(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: <code>/block USER_ID</code>", parse_mode="HTML")
        return
    await block_user(session, int(parts[1]))
    await message.answer(f"🚫 User <code>{parts[1]}</code> blocked.", parse_mode="HTML")


@router.message(Command("unblock"))
async def cmd_unblock(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: <code>/unblock USER_ID</code>", parse_mode="HTML")
        return
    await unblock_user(session, int(parts[1]))
    await message.answer(f"✅ User <code>{parts[1]}</code> unblocked.", parse_mode="HTML")


@router.message(Command("addpts"))
async def cmd_add_pts(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3 or not parts[2].isdigit():
        await message.answer("Usage: <code>/addpts USER_ID N</code>", parse_mode="HTML")
        return
    user = await get_user(session, int(parts[1]))
    if not user:
        await message.answer("❌ User not found.", parse_mode="HTML")
        return
    user.points += int(parts[2])
    await session.commit()
    await message.answer(
        f"✅ Added <b>{parts[2]}</b> pts to <code>{parts[1]}</code>. New balance: <b>{user.points}</b>",
        parse_mode="HTML",
    )


@router.message(Command("rmpts"))
async def cmd_rm_pts(message: Message, session: AsyncSession):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 3 or not parts[2].isdigit():
        await message.answer("Usage: <code>/rmpts USER_ID N</code>", parse_mode="HTML")
        return
    user = await get_user(session, int(parts[1]))
    if not user:
        await message.answer("❌ User not found.", parse_mode="HTML")
        return
    user.points = max(0, user.points - int(parts[2]))
    await session.commit()
    await message.answer(
        f"✅ Removed <b>{parts[2]}</b> pts from <code>{parts[1]}</code>. New balance: <b>{user.points}</b>",
        parse_mode="HTML",
    )


# ── Broadcast ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 <b>Broadcast</b>\n\nChoose broadcast target:",
        parse_mode="HTML",
        reply_markup=admin_broadcast_type_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_bc_channels")
async def admin_bc_channels_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_broadcast_channel_msg)
    await callback.message.edit_text(
        "📢 <b>Broadcast to Channels</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the message to broadcast to all configured channels:",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_channel_msg)
async def admin_broadcast_channels_send(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    channels = await get_all_channels(session)
    if not channels:
        await message.answer("❌ No channels configured.", parse_mode="HTML", reply_markup=admin_back_kb())
        return
    status_msg = await message.answer(f"⏳ Sending to {len(channels)} channel(s)...")
    sent_names, failed = [], []
    for ch in channels:
        try:
            ref = ch.channel_id if ch.channel_id.startswith("-") else f"@{ch.channel_username.lstrip('@')}"
            await bot.copy_message(ref, message.chat.id, message.message_id)
            sent_names.append(ch.channel_title or ch.channel_username)
        except Exception:
            failed.append(ch.channel_title or ch.channel_username)
    lines = [f"📢 <b>Broadcast Complete!</b>\n\n✅ Sent ({len(sent_names)}):"]
    lines += [f"  • {n}" for n in sent_names]
    if failed:
        lines.append(f"\n❌ Failed ({len(failed)}):")
        lines += [f"  • {n}" for n in failed]
    try:
        await status_msg.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=admin_back_kb())
    except Exception:
        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=admin_back_kb())


@router.callback_query(F.data == "admin_bc_users")
async def admin_bc_users_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_broadcast_msg)
    await callback.message.edit_text(
        "👥 <b>Broadcast to Users</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send the message to broadcast to all verified users:",
        parse_mode="HTML",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_msg)
async def admin_broadcast_send(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    users = await get_all_users(session)
    verified = [u for u in users if u.verified and not u.blocked]
    status_msg = await message.answer(f"⏳ Sending to {len(verified)} user(s)...")
    sent = failed = 0
    for u in verified:
        try:
            await bot.copy_message(u.telegram_id, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
    try:
        await status_msg.edit_text(
            f"👥 <b>Broadcast Complete!</b>\n\n"
            f"✅ Sent: <b>{sent}</b>\n"
            f"❌ Failed: <b>{failed}</b>\n"
            f"📊 Total: {sent + failed}",
            parse_mode="HTML",
            reply_markup=admin_back_kb(),
        )
    except Exception:
        await message.answer(f"✅ Sent: {sent} | ❌ Failed: {failed}", parse_mode="HTML")
