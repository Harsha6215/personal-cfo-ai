"""
Scheduler API — status of background refresh jobs.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.scheduler import scheduler

router = APIRouter(tags=["Scheduler"])


class JobStatusResponse(BaseModel):
    name: str
    interval_seconds: int
    status: str
    last_run: str | None
    last_duration_ms: int | None
    run_count: int
    error_count: int
    last_error: str | None


@router.get(
    "/status",
    response_model=list[JobStatusResponse],
    summary="Get scheduler status",
    description="Returns status of all background data refresh jobs.",
)
async def get_scheduler_status(
    user: User = Depends(get_current_user),
):
    return scheduler.get_status()
