"""
FinancialEvent model — the immutable event-sourced ledger.

Every financial action (buy, sell, dividend, split, etc.) is recorded as an
immutable event. The current portfolio state is DERIVED by replaying these events.

This replaces the simple "Transaction" model from Epic 1 with a richer event model
that supports: BUY, SELL, BONUS, SPLIT, DIVIDEND, SIP, TRANSFER, MERGER, INTEREST, TAX.

Key principle: events are never updated or deleted. They are append-only.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class EventType(str, enum.Enum):
    BUY       = "BUY"
    SELL      = "SELL"
    BONUS     = "BONUS"
    SPLIT     = "SPLIT"       # quantity multiplied, price divided
    DIVIDEND  = "DIVIDEND"
    SIP       = "SIP"         # systematic investment plan (same as BUY but tagged)
    TRANSFER  = "TRANSFER"    # moved between brokers
    MERGER    = "MERGER"      # corporate action: old shares → new shares
    INTEREST  = "INTEREST"    # for bonds / FDs
    TAX       = "TAX"         # tax deducted at source


class FinancialEvent(TimestampMixin, Base):
    """
    The core domain entity. Everything else is derived from these events.

    To reconstruct a portfolio on any date:
        SELECT * FROM financial_events
        WHERE portfolio_id = :pid AND executed_at <= :date
        ORDER BY executed_at
    """
    __tablename__ = "financial_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )

    # ── Core references ────────────────────────────────────────────────────────
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    import_job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("import_jobs.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # ── Event data ─────────────────────────────────────────────────────────────
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType), nullable=False, index=True
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    fees: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)

    # ── Metadata ───────────────────────────────────────────────────────────────
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "zerodha", "icici", "manual"
    exchange: Mapped[str | None] = mapped_column(String(10), nullable=True)  # NSE, BSE
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # For splits/mergers: ratio information
    split_ratio_from: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    split_ratio_to: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="financial_events")  # type: ignore[name-defined]
    asset: Mapped["Asset"] = relationship("Asset", back_populates="financial_events")  # type: ignore[name-defined]
    import_job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="events")  # type: ignore[name-defined]

    @property
    def total_value(self) -> float:
        """Convenience: quantity × price + fees."""
        return float(self.quantity) * float(self.price) + float(self.fees)

    def __repr__(self) -> str:
        return f"<FinancialEvent id={self.id} type={self.event_type} asset={self.asset_id} qty={self.quantity}>"
