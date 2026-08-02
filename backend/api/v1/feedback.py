"""
Feedback API — Sprint 6.6 Beta Launch

Collects user feedback via the in-app FeedbackWidget.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.base import new_uuid
from backend.models.feedback import Feedback
from backend.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Feedback"])

VALID_FEEDBACK_TYPES = {"bug", "feature", "ai_rating", "general"}


class FeedbackRequest(BaseModel):
    feedback_type: str = Field(..., description="One of: bug, feature, ai_rating, general")
    content: str = Field(..., min_length=1, max_length=5000)
    rating: int | None = Field(None, ge=1, le=5)
    page: str | None = Field(None, max_length=100)


class FeedbackResponse(BaseModel):
    id: str
    message: str


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def submit_feedback(
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.feedback_type not in VALID_FEEDBACK_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"feedback_type must be one of: {', '.join(VALID_FEEDBACK_TYPES)}",
        )

    feedback = Feedback(
        id=new_uuid(),
        user_id=user.id,
        feedback_type=body.feedback_type,
        content=body.content,
        rating=body.rating,
        page=body.page,
    )
    db.add(feedback)
    await db.flush()
    await db.commit()

    logger.info(
        "feedback.submitted",
        user_id=user.id,
        feedback_type=body.feedback_type,
        feedback_id=feedback.id,
    )
    return FeedbackResponse(id=feedback.id, message="Thanks for your feedback!")
