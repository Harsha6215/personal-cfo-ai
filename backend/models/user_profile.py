"""
UserProfile model — Epic 6 Sprint 6.4

Stores onboarding data and user preferences:
- Risk appetite, investment horizon, monthly income, age
- Primary financial goals, experience level
- Onboarding progress tracking
"""

import enum

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class RiskAppetite(str, enum.Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"
    VERY_AGGRESSIVE = "VERY_AGGRESSIVE"


class InvestmentHorizon(str, enum.Enum):
    SHORT = "SHORT"       # < 2 years
    MEDIUM = "MEDIUM"     # 2-5 years
    LONG = "LONG"         # 5-10 years
    VERY_LONG = "VERY_LONG"  # 10+ years


class ExperienceLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"
    EXPERT = "EXPERT"


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )

    # ── Financial profile ──────────────────────────────────────────────────────
    risk_appetite: Mapped[str | None] = mapped_column(
        Enum(RiskAppetite, name="risk_appetite_enum"), nullable=True
    )
    investment_horizon: Mapped[str | None] = mapped_column(
        Enum(InvestmentHorizon, name="investment_horizon_enum"), nullable=True
    )
    monthly_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Goals & experience ─────────────────────────────────────────────────────
    primary_goals: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. ["WEALTH_GROWTH", "RETIREMENT", "TAX_SAVING", "EMERGENCY_FUND"]
    experience_level: Mapped[str | None] = mapped_column(
        Enum(ExperienceLevel, name="experience_level_enum"), nullable=True
    )

    # ── Onboarding tracking ────────────────────────────────────────────────────
    onboarding_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 0=not started, 1=risk, 2=goals, 3=profile, 4=upload, 5=doctor, 6=complete
    onboarding_completed_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} step={self.onboarding_step}>"
