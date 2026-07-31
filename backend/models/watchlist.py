"""
WatchlistItem model.

Symbols a user wants to track — not a position, just a watch.
One user can watch many symbols; each symbol can be watched by many users.
"""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class WatchlistItem(TimestampMixin, Base):
    __tablename__ = "watchlist"
    __table_args__ = (
        # Prevent a user adding the same symbol twice
        UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="watchlist")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<WatchlistItem id={self.id} symbol={self.symbol} user_id={self.user_id}>"
