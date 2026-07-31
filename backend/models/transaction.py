"""
Transaction model.

Records every BUY or SELL event against a Holding.
This is the immutable audit log — transactions are never deleted, only added.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class TransactionType(str, enum.Enum):
    BUY  = "BUY"
    SELL = "SELL"


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    holding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("holdings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    holding: Mapped["Holding"] = relationship("Holding", back_populates="transactions")  # type: ignore[name-defined]

    @property
    def total_value(self) -> float:
        """Convenience: quantity × price."""
        return float(self.quantity) * float(self.price)

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.type} qty={self.quantity} price={self.price}>"
