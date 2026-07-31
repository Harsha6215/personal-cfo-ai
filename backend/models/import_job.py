"""
ImportJob model — tracks every data import operation.

Provides full audit trail: who imported what, when, from where, with what result.
Events (financial_events) link back to the job that created them.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class ImportStatus(str, enum.Enum):
    PENDING    = "PENDING"
    PREVIEWING = "PREVIEWING"
    IMPORTING  = "IMPORTING"
    COMPLETED  = "COMPLETED"
    PARTIAL    = "PARTIAL"     # some rows failed
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"


class ImportSource(str, enum.Enum):
    ZERODHA     = "ZERODHA"
    ICICI       = "ICICI"
    GROWW       = "GROWW"
    INDMONEY    = "INDMONEY"
    ETMONEY     = "ETMONEY"
    CAS_PDF     = "CAS_PDF"      # CAMS/Karvy CAS statement
    CSV_GENERIC = "CSV_GENERIC"
    MANUAL      = "MANUAL"


class ImportJob(TimestampMixin, Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Job metadata ───────────────────────────────────────────────────────────
    source: Mapped[ImportSource] = mapped_column(
        Enum(ImportSource, name="importsource_enum"), nullable=False
    )
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, name="importstatus_enum"), nullable=False, default=ImportStatus.PENDING
    )

    # ── Counters ───────────────────────────────────────────────────────────────
    rows_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_duplicate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Timing ─────────────────────────────────────────────────────────────────
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Error details ──────────────────────────────────────────────────────────
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]
    portfolio: Mapped["Portfolio"] = relationship("Portfolio")  # type: ignore[name-defined]
    events: Mapped[list["FinancialEvent"]] = relationship(  # type: ignore[name-defined]
        "FinancialEvent", back_populates="import_job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ImportJob id={self.id} source={self.source} status={self.status}>"
