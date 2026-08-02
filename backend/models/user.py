"""
User model.

Central identity record. Every other entity links back to a User.
Authentication (password hashing, tokens) is handled in Story 6.
Role-based access added in Epic 6 (SaaS Platform Foundation).
"""

import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole_enum"), nullable=False, default=UserRole.USER
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    portfolios: Mapped[list["Portfolio"]] = relationship(  # type: ignore[name-defined]
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    watchlist: Mapped[list["WatchlistItem"]] = relationship(  # type: ignore[name-defined]
        "WatchlistItem", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
