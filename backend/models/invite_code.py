"""
InviteCode model — Sprint 6.6 Beta Launch

Tracks invite codes used to gate beta access.
Each code has a limited number of uses and optional expiration.
"""

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class InviteCode(TimestampMixin, Base):
    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<InviteCode code={self.code} uses={self.current_uses}/{self.max_uses}>"
