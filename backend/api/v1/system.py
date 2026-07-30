"""
System routes — health check and version.
These are the first routes visible in Swagger at localhost:8000/docs.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.config import Settings, get_settings

router = APIRouter(tags=["System"])


# ── Response schemas ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    service: str

    model_config = {"json_schema_extra": {"example": {"status": "ok", "service": "backend"}}}


class VersionResponse(BaseModel):
    version: str
    env: str
    name: str

    model_config = {
        "json_schema_extra": {
            "example": {"version": "0.1.0", "env": "local", "name": "Personal CFO AI"}
        }
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns `ok` if the service is running. Used by Docker healthchecks and load balancers.",
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="backend")


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="App version",
    description="Returns the current application version and environment.",
)
async def version(settings: Settings = Depends(get_settings)) -> VersionResponse:
    return VersionResponse(
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        name=settings.APP_NAME,
    )
