from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.models import Channel


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Refer & Earn"), KeyboardButton(text="🛍 Get Blinkit Code")],
            [KeyboardButton(text="👤 My Profile"),   KeyboardButton(text="📜 History")],
            [KeyboardButton(text="💬 Support")],
        ],
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Select an option…",
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def join_channels_kb(channels: list[Channel], show_check: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        username = ch.channel_username.lstrip("@")
        title = ch.channel_title or ch.channel_username
        builder.row(InlineKeyboardButton(text=f"📢 {title}", url=f"https://t.me/{username}"))
    if show_check:
        builder.row(InlineKeyboardButton(text="✅ I've Joined All Channels", callback_data="check_join"))
    return builder.as_markup()


def recheck_channels_kb(missing: list[Channel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in missing:
        username = ch.channel_username.lstrip("@")
        title = ch.channel_title or ch.channel_username
        builder.row(InlineKeyboardButton(text=f"📢 Join {title}", url=f"https://t.me/{username}"))
    builder.row(InlineKeyboardButton(text="🔄 Check Again", callback_data="check_join"))
    return builder.as_markup()


def verify_device_kb(verify_url: str) -> InlineKeyboardMarkup:
    """Button that opens the device verification web page."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Verify My Device", url=verify_url)],
    ])


def code_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm & Get Code", callback_data="code_confirm"),
            InlineKeyboardButton(text="❌ Cancel",              callback_data="code_cancel"),
        ]
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Back to Menu", callback_data="main_menu")]
    ])


def support_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Contact Support", url="https://t.me/ZEXUS_HERE")]
    ])
