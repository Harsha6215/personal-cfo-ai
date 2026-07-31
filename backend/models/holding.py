"""
Holding model.

Represents a single security position within a Portfolio.
asset_type distinguishes between STOCK, ETF, MF (mutual fund), CRYPTO, BOND.
average_cost is updated each time a BUY transaction is recorded.
"""

import enum

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class AssetType(str, enum.Enum):
    STOCK  = "STOCK"
    ETF    = "ETF"
    MF     = "MF"       # Mutual Fund
    CRYPTO = "CRYPTO"
    BOND   = "BOND"
    OTHER  = "OTHER"


class Holding(TimestampMixin, Base):
    __tablename__ = "holdings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    average_cost: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType), nullable=False, default=AssetType.STOCK
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="holdings")  # type: ignore[name-defined]
    transactions: Mapped[list["Transaction"]] = relationship(  # type: ignore[name-defined]
        "Transaction", back_populates="holding", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Holding id={self.id} symbol={self.symbol} qty={self.quantity}>"
