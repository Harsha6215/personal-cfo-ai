"""
Decision History model — Story 5.9

Stores every AI recommendation for audit trail and learning.
Tracks: what was recommended, what was done, outcome.
"""

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class DecisionRecord(TimestampMixin, Base):
    __tablename__ = "decision_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Recommendation details
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON serialized list

    # Price at time of recommendation
    price_at_recommendation: Mapped[float | None] = mapped_column(Float, nullable=True)

    # User's actual action
    user_action: Mapped[str | None] = mapped_column(String(20), nullable=True)  # BOUGHT, SOLD, HELD, IGNORED
    user_action_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Outcome tracking
    price_after_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_after_30d: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)  # CORRECT, INCORRECT, PENDING

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<DecisionRecord {self.ticker} {self.action} {self.confidence}%>"
