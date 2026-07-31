"""
Asset model — the master reference for any tradeable security.

This is a canonical record. Regardless of broker, every security maps to one Asset.
Think of it as the "product catalog" for investments.

Examples:
    ISIN: INE009A01021 → Ticker: INFY → Name: Infosys Ltd → Exchange: NSE
    ISIN: INE002A01018 → Ticker: RELIANCE → Name: Reliance Industries → Exchange: NSE
"""

import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class AssetType(str, enum.Enum):
    STOCK  = "STOCK"
    ETF    = "ETF"
    MF     = "MF"         # Mutual Fund
    CRYPTO = "CRYPTO"
    BOND   = "BOND"
    FD     = "FD"         # Fixed Deposit
    GOLD   = "GOLD"
    OTHER  = "OTHER"


class Exchange(str, enum.Enum):
    NSE  = "NSE"
    BSE  = "BSE"
    MCX  = "MCX"
    NCDEX = "NCDEX"
    OTHER = "OTHER"


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    # Identifiers — at least one must be present
    isin: Mapped[str | None] = mapped_column(String(12), unique=True, nullable=True, index=True)
    ticker: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[Exchange] = mapped_column(
        Enum(Exchange), nullable=False, default=Exchange.NSE
    )

    # Descriptive
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType), nullable=False, default=AssetType.STOCK
    )
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────────
    financial_events: Mapped[list["FinancialEvent"]] = relationship(  # type: ignore[name-defined]
        "FinancialEvent", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} ticker={self.ticker} isin={self.isin}>"
