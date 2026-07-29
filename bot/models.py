from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    join_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    redemptions: Mapped[list["Redemption"]] = relationship(
        "Redemption", back_populates="user", foreign_keys="Redemption.user_telegram_id"
    )


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_username: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Code(Base):
    """Unique one-time-use Blinkit coupon codes."""
    __tablename__ = "codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    redemption: Mapped["Redemption | None"] = relationship(
        "Redemption", back_populates="code", uselist=False
    )


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True
    )
    code_id: Mapped[int] = mapped_column(Integer, ForeignKey("codes.id"), nullable=False)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(
        "User", back_populates="redemptions", foreign_keys=[user_telegram_id]
    )
    code: Mapped["Code"] = relationship("Code", back_populates="redemption")


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


# ── Device Verification ────────────────────────────────────────────────────────

class VerificationToken(Base):
    """One-time token sent to user for device verification via web."""
    __tablename__ = "verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    referrer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeviceRecord(Base):
    """Stores verified device info per Telegram user to detect duplicate devices."""
    __tablename__ = "device_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
