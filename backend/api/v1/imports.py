"""
Import API — upload files and manage import jobs.

Endpoints:
    POST /api/v1/import/upload   — upload file, get preview
    POST /api/v1/import/confirm  — confirm and persist previewed data
    GET  /api/v1/import/jobs     — list user's import history
"""

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.import_job import ImportJob
from backend.models.user import User
from backend.services.import_engine import AdapterRegistry, ImportService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Import"])

# ── Adapter registry (adapters registered here) ───────────────────────────────
from backend.services.import_engine.adapters.zerodha import ZerodhaHoldingsAdapter

registry = AdapterRegistry()
registry.register(ZerodhaHoldingsAdapter())


# ── Schemas ────────────────────────────────────────────────────────────────────

class PreviewResponse(BaseModel):
    import_job_id: str | None = None
    total_rows: int
    valid_transactions: int
    duplicates: int
    errors: int
    new_assets: list[str]
    validation_errors: list[str]


class ImportJobResponse(BaseModel):
    id: str
    source: str
    filename: str | None
    status: str
    rows_total: int
    rows_imported: int
    rows_failed: int
    rows_duplicate: int
    duration_ms: int | None
    created_at: str

    model_config = {"from_attributes": True}


class ConfirmRequest(BaseModel):
    import_job_id: str


class ConfirmResponse(BaseModel):
    import_job_id: str
    status: str
    rows_imported: int
    rows_failed: int
    rows_duplicate: int
    duration_ms: int | None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=PreviewResponse,
    summary="Upload file and get import preview",
    description="Uploads a CSV/file, auto-detects source, and returns a preview of what will be imported.",
)
async def upload_file(
    file: UploadFile = File(...),
    portfolio_id: str = Form(...),
    force_source: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Read file content
    content = (await file.read()).decode("utf-8", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    # Run import service preview
    service = ImportService(db, registry)
    preview = await service.preview(
        user_id=user.id,
        portfolio_id=portfolio_id,
        file_content=content,
        filename=file.filename,
        force_source=force_source,
    )

    if preview.validation_errors and preview.total_rows == 0:
        raise HTTPException(
            status_code=422,
            detail={"message": "Validation failed", "errors": preview.validation_errors},
        )

    # Get the job ID from DB (last previewing job for this user)
    result = await db.execute(
        select(ImportJob)
        .where(ImportJob.user_id == user.id, ImportJob.portfolio_id == portfolio_id)
        .order_by(ImportJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()

    return PreviewResponse(
        import_job_id=job.id if job else None,
        total_rows=preview.total_rows,
        valid_transactions=preview.valid_transactions,
        duplicates=preview.duplicates,
        errors=preview.errors,
        new_assets=preview.new_assets,
        validation_errors=preview.validation_errors,
    )


@router.post(
    "/confirm",
    response_model=ConfirmResponse,
    summary="Confirm and persist previewed import",
)
async def confirm_import(
    body: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Get the job
    result = await db.execute(
        select(ImportJob).where(ImportJob.id == body.import_job_id, ImportJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    if job.status.value not in ("PREVIEWING", "PENDING"):
        raise HTTPException(status_code=400, detail=f"Job is already {job.status.value}, cannot confirm")

    # Re-read the cached file content (stored in job) — for now re-parse
    # In production, cache the preview results in Redis or temp storage
    # For MVP: the frontend sends the file again with the job_id

    raise HTTPException(
        status_code=501,
        detail="Full confirm flow requires file re-upload. Use POST /import/upload-and-import for one-step import.",
    )


@router.get(
    "/jobs",
    response_model=list[ImportJobResponse],
    summary="List import history",
)
async def list_import_jobs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ImportJob)
        .where(ImportJob.user_id == user.id)
        .order_by(ImportJob.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.post(
    "/upload-and-import",
    response_model=ConfirmResponse,
    summary="Upload, preview, and import in one step",
    description="Combines upload + confirm. Parses the file, shows what was imported.",
)
async def upload_and_import(
    file: UploadFile = File(...),
    portfolio_id: str = Form(...),
    force_source: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One-step import: upload → parse → persist. Returns import results."""
    content = (await file.read()).decode("utf-8", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    service = ImportService(db, registry)

    # Preview (creates job in PREVIEWING state)
    preview = await service.preview(
        user_id=user.id,
        portfolio_id=portfolio_id,
        file_content=content,
        filename=file.filename,
        force_source=force_source,
    )

    if preview.validation_errors and preview.valid_transactions == 0:
        raise HTTPException(
            status_code=422,
            detail={"message": "Validation failed", "errors": preview.validation_errors},
        )

    # Get the job
    result = await db.execute(
        select(ImportJob)
        .where(ImportJob.user_id == user.id, ImportJob.portfolio_id == portfolio_id)
        .order_by(ImportJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=500, detail="Import job not created")

    # Confirm — persist to database
    valid_transactions = [t for t in preview.transactions if not t.error and not t.is_duplicate]
    job = await service.confirm_import(
        import_job_id=job.id,
        transactions=valid_transactions,
        portfolio_id=portfolio_id,
    )

    return ConfirmResponse(
        import_job_id=job.id,
        status=job.status.value,
        rows_imported=job.rows_imported,
        rows_failed=job.rows_failed,
        rows_duplicate=job.rows_duplicate,
        duration_ms=job.duration_ms,
    )
