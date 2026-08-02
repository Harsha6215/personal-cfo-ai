"""
Feedback model — Sprint 6.6 Beta Launch

Stores user feedback collected via the in-app FeedbackWidget.
Supports types: bug, feature, ai_rating, general.
"""

from sqlalchemy import Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base import TimestampMixin, new_uuid


class Feedback(TimestampMixin, Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid, index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # bug, feature, ai_rating, general
    content: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    page: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} type={self.feedback_type} user={self.user_id}>"
