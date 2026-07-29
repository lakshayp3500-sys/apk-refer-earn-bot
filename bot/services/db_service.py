import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models import User, Channel, Referral, Code, Redemption, Setting, VerificationToken, DeviceRecord
from bot.config import REWARD_PER_REFERRAL_DEFAULT, WITHDRAW_POINTS_DEFAULT


# ── Settings ───────────────────────────────────────────────────────────────────

async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    result = await session.execute(select(Setting).where(Setting.key == key))
    s = result.scalar_one_or_none()
    return s.value if s else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    result = await session.execute(select(Setting).where(Setting.key == key))
    s = result.scalar_one_or_none()
    if s:
        s.value = value
    else:
        session.add(Setting(key=key, value=value))
    await session.commit()


async def get_reward_per_referral(session: AsyncSession) -> int:
    val = await get_setting(session, "reward_per_referral", str(REWARD_PER_REFERRAL_DEFAULT))
    try:
        return int(val)
    except ValueError:
        return REWARD_PER_REFERRAL_DEFAULT


async def get_redeem_cost(session: AsyncSession) -> int:
    val = await get_setting(session, "redeem_cost", str(WITHDRAW_POINTS_DEFAULT))
    try:
        return int(val)
    except ValueError:
        return WITHDRAW_POINTS_DEFAULT


# ── Users ──────────────────────────────────────────────────────────────────────

async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    referred_by: int | None = None,
) -> tuple[User, bool]:
    user = await get_user(session, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        await session.commit()
        return user, False
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referred_by=referred_by,
        points=0,
    )
    session.add(user)
    await session.commit()
    return user, True


async def mark_user_verified(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user and not user.verified:
        user.verified = True
        await session.commit()


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return list(result.scalars().all())


async def block_user(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.blocked = True
        await session.commit()


async def unblock_user(session: AsyncSession, telegram_id: int) -> None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        user.blocked = False
        await session.commit()


# ── Referrals ──────────────────────────────────────────────────────────────────

async def process_referral(session: AsyncSession, referrer_id: int, referred_id: int) -> bool:
    existing = await session.execute(
        select(Referral).where(Referral.referred_id == referred_id)
    )
    if existing.scalar_one_or_none():
        return False
    referrer = await get_user(session, referrer_id)
    if not referrer or referrer.telegram_id == referred_id:
        return False
    reward = await get_reward_per_referral(session)
    session.add(Referral(referrer_id=referrer_id, referred_id=referred_id))
    referrer.points += reward
    referrer.referrals += 1
    await session.commit()
    return True


# ── Channels ───────────────────────────────────────────────────────────────────

async def get_all_channels(session: AsyncSession) -> list[Channel]:
    result = await session.execute(select(Channel))
    return list(result.scalars().all())


async def add_channel(session: AsyncSession, channel_id: str, channel_username: str, channel_title: str | None) -> Channel:
    ch = Channel(channel_id=channel_id, channel_username=channel_username, channel_title=channel_title)
    session.add(ch)
    await session.commit()
    return ch


async def remove_channel(session: AsyncSession, channel_db_id: int) -> bool:
    result = await session.execute(select(Channel).where(Channel.id == channel_db_id))
    ch = result.scalar_one_or_none()
    if ch:
        await session.delete(ch)
        await session.commit()
        return True
    return False


# ── Codes ──────────────────────────────────────────────────────────────────────

async def get_all_codes(session: AsyncSession) -> list[Code]:
    result = await session.execute(select(Code).order_by(Code.created_at.desc()))
    return list(result.scalars().all())


async def get_available_codes_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(Code.id)).where(Code.is_used == False)
    )
    return result.scalar() or 0


async def add_codes(session: AsyncSession, code_strings: list[str]) -> tuple[int, int]:
    added = 0
    skipped = 0
    for raw in code_strings:
        code_val = raw.strip()
        if not code_val:
            continue
        existing = await session.execute(select(Code).where(Code.code == code_val))
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        session.add(Code(code=code_val))
        added += 1
    await session.commit()
    return added, skipped


async def remove_code(session: AsyncSession, code_id: int) -> bool:
    result = await session.execute(select(Code).where(Code.id == code_id))
    code = result.scalar_one_or_none()
    if code and not code.is_used:
        await session.delete(code)
        await session.commit()
        return True
    return False


async def clear_unused_codes(session: AsyncSession) -> int:
    result = await session.execute(select(Code).where(Code.is_used == False))
    codes = list(result.scalars().all())
    for c in codes:
        await session.delete(c)
    await session.commit()
    return len(codes)


# ── Redemptions ────────────────────────────────────────────────────────────────

async def redeem_code(session: AsyncSession, telegram_id: int) -> tuple[bool, str]:
    user = await get_user(session, telegram_id)
    if not user:
        return False, "User not found."
    cost = await get_redeem_cost(session)
    if user.points < cost:
        return False, f"Insufficient points. You need {cost} pts, you have {user.points}."
    result = await session.execute(
        select(Code).where(Code.is_used == False).order_by(Code.created_at.asc()).limit(1)
    )
    code = result.scalar_one_or_none()
    if not code:
        return False, "No codes available right now. Please try again later or contact support."
    user.points -= cost
    code.is_used = True
    code.used_by_telegram_id = telegram_id
    code.used_at = datetime.now(timezone.utc)
    session.add(Redemption(user_telegram_id=telegram_id, code_id=code.id, points_spent=cost))
    await session.commit()
    return True, code.code


async def get_user_redemptions(session: AsyncSession, telegram_id: int) -> list[Redemption]:
    result = await session.execute(
        select(Redemption).where(Redemption.user_telegram_id == telegram_id).order_by(Redemption.date.desc())
    )
    return list(result.scalars().all())


# ── Stats ──────────────────────────────────────────────────────────────────────

async def get_stats(session: AsyncSession) -> dict:
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    verified_users = (await session.execute(
        select(func.count(User.id)).where(User.verified == True)
    )).scalar() or 0
    total_referrals = (await session.execute(select(func.count(Referral.id)))).scalar() or 0
    total_redemptions = (await session.execute(select(func.count(Redemption.id)))).scalar() or 0
    available_codes = (await session.execute(
        select(func.count(Code.id)).where(Code.is_used == False)
    )).scalar() or 0
    total_codes = (await session.execute(select(func.count(Code.id)))).scalar() or 0
    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "total_referrals": total_referrals,
        "total_redemptions": total_redemptions,
        "available_codes": available_codes,
        "total_codes": total_codes,
    }


# ── Device Verification ────────────────────────────────────────────────────────

async def create_verification_token(
    session: AsyncSession, telegram_id: int, referrer_id: int | None = None
) -> str:
    token = secrets.token_hex(24)
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    session.add(VerificationToken(
        token=token,
        telegram_id=telegram_id,
        referrer_id=referrer_id,
        expires_at=expires,
    ))
    await session.commit()
    return token


async def process_device_verification(
    session: AsyncSession,
    token: str,
    ip_address: str,
    fingerprint_hash: str,
    user_agent: str,
) -> dict:
    """
    Verify device. Duplicate detection is based ONLY on canvas fingerprint
    (NOT on IP or phone model/user-agent) to avoid false positives when two
    people have the same phone model or share the same Wi-Fi network.

    Returns: success, is_duplicate, telegram_id, referrer_id, referral_given,
             user_name, user_username
    """
    now = datetime.now(timezone.utc)

    # Validate token
    result = await session.execute(
        select(VerificationToken).where(
            VerificationToken.token == token,
            VerificationToken.used == False,
            VerificationToken.expires_at > now,
        )
    )
    vtoken = result.scalar_one_or_none()
    if not vtoken:
        return {"success": False, "error": "Verification link is invalid or has expired. Send /start again."}

    telegram_id = vtoken.telegram_id
    referrer_id = vtoken.referrer_id

    # ── Duplicate check: ONLY canvas fingerprint ───────────────────────────────
    # We intentionally skip IP-based checks to avoid false positives:
    #   • Same Wi-Fi  → same IP but different devices (NOT duplicate)
    #   • Same phone model → same user-agent but different devices (NOT duplicate)
    # Canvas fingerprint varies even on identical hardware (GPU driver differences).
    fp_dup = None
    if fingerprint_hash and fingerprint_hash != "unknown":
        fp_dup = (await session.execute(
            select(DeviceRecord).where(
                DeviceRecord.fingerprint_hash == fingerprint_hash,
                DeviceRecord.telegram_id != telegram_id,
            )
        )).scalar_one_or_none()

    is_duplicate = fp_dup is not None

    # ── Store / update device record ───────────────────────────────────────────
    existing_rec = (await session.execute(
        select(DeviceRecord).where(DeviceRecord.telegram_id == telegram_id)
    )).scalar_one_or_none()

    if existing_rec:
        existing_rec.ip_address = ip_address
        existing_rec.fingerprint_hash = fingerprint_hash
        existing_rec.user_agent = user_agent
        existing_rec.verified_at = now
    else:
        session.add(DeviceRecord(
            telegram_id=telegram_id,
            ip_address=ip_address,
            fingerprint_hash=fingerprint_hash,
            user_agent=user_agent,
        ))

    # ── Mark token used & user verified ───────────────────────────────────────
    vtoken.used = True
    await mark_user_verified(session, telegram_id)

    # ── Referral: only if NOT duplicate ───────────────────────────────────────
    referral_given = False
    if not is_duplicate and referrer_id:
        referral_given = await process_referral(session, referrer_id, telegram_id)

    # Fetch user info for admin notification
    user = await get_user(session, telegram_id)
    user_name = user.first_name or "N/A" if user else "N/A"
    user_username = f"@{user.username}" if user and user.username else "no username"

    await session.commit()

    return {
        "success": True,
        "is_duplicate": is_duplicate,
        "telegram_id": telegram_id,
        "referrer_id": referrer_id,
        "referral_given": referral_given,
        "user_name": user_name,
        "user_username": user_username,
    }
