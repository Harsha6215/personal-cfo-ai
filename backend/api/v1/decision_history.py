"""
Decision History API — Story 5.9

GET  /api/v1/decisions/history — get all past decisions
POST /api/v1/decisions/history/{id}/action — record user's action on a recommendation
"""

import json
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.decision_history import DecisionRecord
from backend.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Decision History"])


class DecisionRecordResponse(BaseModel):
    id: str
    ticker: str
    action: str
    confidence: float
    weighted_score: float
    reasoning: str | None = None
    evidence: list[str] = []
    price_at_recommendation: float | None = None
    user_action: str | None = None
    outcome_return_pct: float | None = None
    outcome_verdict: str | None = None
    created_at: str


class DecisionHistoryResponse(BaseModel):
    decisions: list[DecisionRecordResponse]
    total: int
    accuracy_pct: float | None = None  # % of correct predictions


class RecordActionRequest(BaseModel):
    user_action: str  # BOUGHT, SOLD, HELD, IGNORED


@router.get(
    "/history",
    response_model=DecisionHistoryResponse,
    summary="Get decision history",
)
async def get_decision_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DecisionRecord)
        .where(DecisionRecord.user_id == user.id)
        .order_by(DecisionRecord.created_at.desc())
        .limit(limit)
    )
    records = result.scalars().all()

    # Calculate accuracy
    resolved = [r for r in records if r.outcome_verdict in ("CORRECT", "INCORRECT")]
    accuracy = None
    if resolved:
        correct = sum(1 for r in resolved if r.outcome_verdict == "CORRECT")
        accuracy = round(correct / len(resolved) * 100, 1)

    return DecisionHistoryResponse(
        decisions=[
            DecisionRecordResponse(
                id=r.id,
                ticker=r.ticker,
                action=r.action,
                confidence=r.confidence,
                weighted_score=r.weighted_score,
                reasoning=r.reasoning,
                evidence=json.loads(r.evidence) if r.evidence else [],
                price_at_recommendation=r.price_at_recommendation,
                user_action=r.user_action,
                outcome_return_pct=r.outcome_return_pct,
                outcome_verdict=r.outcome_verdict,
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in records
        ],
        total=len(records),
        accuracy_pct=accuracy,
    )


@router.post(
    "/history/{decision_id}/action",
    summary="Record user action on a recommendation",
)
async def record_user_action(
    decision_id: str,
    body: RecordActionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DecisionRecord)
        .where(DecisionRecord.id == decision_id, DecisionRecord.user_id == user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Decision record not found")

    record.user_action = body.user_action
    record.user_action_date = datetime.now(timezone.utc)
    await db.commit()

    return {"status": "recorded", "decision_id": decision_id, "user_action": body.user_action}


@router.post(
    "/history/save",
    summary="Save a new decision record",
)
async def save_decision(
    ticker: str,
    action: str,
    confidence: float,
    weighted_score: float,
    reasoning: str = "",
    evidence: str = "[]",
    price: float | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = DecisionRecord(
        user_id=user.id,
        ticker=ticker.upper(),
        action=action,
        confidence=confidence,
        weighted_score=weighted_score,
        reasoning=reasoning,
        evidence=evidence,
        price_at_recommendation=price,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {"status": "saved", "decision_id": record.id}
