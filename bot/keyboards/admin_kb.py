from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.models import Channel, Code


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistics",     callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Broadcast",      callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="📡 Channels",       callback_data="admin_channels"),
            InlineKeyboardButton(text="🎟 Code Manager",   callback_data="admin_codes"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Point Settings", callback_data="admin_points"),
            InlineKeyboardButton(text="👥 Users",          callback_data="admin_users"),
        ],
    ])


def admin_channels_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Channel",    callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="➖ Remove Channel", callback_data="admin_remove_channel")],
        [InlineKeyboardButton(text="📋 List Channels",  callback_data="admin_list_channels")],
        [InlineKeyboardButton(text="◀️ Back",           callback_data="admin_back")],
    ])


def admin_codes_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Codes",          callback_data="admin_add_codes")],
        [InlineKeyboardButton(text="📋 View Code Stats",    callback_data="admin_list_codes")],
        [InlineKeyboardButton(text="➖ Remove a Code",      callback_data="admin_remove_code")],
        [InlineKeyboardButton(text="🗑 Clear All Unused",   callback_data="admin_clear_codes")],
        [InlineKeyboardButton(text="◀️ Back",               callback_data="admin_back")],
    ])


def admin_remove_code_kb(codes: list[Code]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code in codes[:20]:  # Show max 20 at a time
        short = code.code[:30] + "…" if len(code.code) > 30 else code.code
        builder.row(InlineKeyboardButton(
            text=f"🗑 {short}",
            callback_data=f"admin_del_code_{code.id}",
        ))
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="admin_codes"))
    return builder.as_markup()


def admin_remove_channels_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        title = ch.channel_title or ch.channel_username
        builder.row(InlineKeyboardButton(
            text=f"🗑 {title}",
            callback_data=f"admin_del_ch_{ch.id}",
        ))
    builder.row(InlineKeyboardButton(text="◀️ Back", callback_data="admin_channels"))
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Admin Panel", callback_data="admin_back")]
    ])


def admin_broadcast_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Send to Channels", callback_data="admin_bc_channels")],
        [InlineKeyboardButton(text="👥 Send to Users",    callback_data="admin_bc_users")],
        [InlineKeyboardButton(text="◀️ Back",             callback_data="admin_back")],
    ])


def admin_confirm_clear_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes, Clear All", callback_data="admin_clear_codes_confirm"),
            InlineKeyboardButton(text="❌ Cancel",         callback_data="admin_codes"),
        ]
    ])
