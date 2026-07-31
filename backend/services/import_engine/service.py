"""
ImportService — orchestrates the full import pipeline.

Pipeline:
    1. Upload file
    2. Detect source (which adapter?)
    3. Validate format
    4. Parse into canonical transactions
    5. Check for duplicates against existing data
    6. Preview (return to user without persisting)
    7. Confirm → persist to database
    8. Recalculate portfolio

Usage:
    service = ImportService(db, registry)
    preview = await service.preview(user_id, portfolio_id, file_content, filename)
    result = await service.confirm(preview.import_job_id)
"""

import time
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.financial_event import EventType, FinancialEvent
from backend.models.import_job import ImportJob, ImportSource, ImportStatus
from backend.services.import_engine.adapter import (
    ImportAdapter,
    ParsedTransaction,
    PreviewResult,
    ValidationResult,
)
from backend.services.import_engine.registry import AdapterRegistry

logger = structlog.get_logger(__name__)


class ImportService:
    def __init__(self, db: AsyncSession, registry: AdapterRegistry):
        self.db = db
        self.registry = registry

    # ── Step 1-4: Preview ──────────────────────────────────────────────────────

    async def preview(
        self,
        user_id: str,
        portfolio_id: str,
        file_content: str,
        filename: str | None = None,
        force_source: str | None = None,
    ) -> PreviewResult:
        """
        Parse file and return preview without persisting.
        Creates an ImportJob in PREVIEWING state.
        """

        # Detect adapter
        if force_source:
            adapter = self.registry.get_by_source(force_source)
        else:
            adapter = self.registry.detect(file_content, filename)

        if adapter is None:
            return PreviewResult(
                validation_errors=["Could not detect file source. Supported: " + ", ".join(self.registry.available_sources)]
            )

        # Validate
        validation = adapter.validate(file_content)
        if not validation.is_valid:
            return PreviewResult(validation_errors=validation.errors)

        # Parse
        transactions = adapter.parse(file_content)

        # Check for duplicates
        await self._mark_duplicates(portfolio_id, transactions)

        # Identify new assets (tickers not in DB)
        new_assets = await self._find_new_assets(transactions)

        # Create ImportJob (PREVIEWING state)
        job = ImportJob(
            user_id=user_id,
            portfolio_id=portfolio_id,
            source=adapter.source,
            filename=filename,
            status=ImportStatus.PREVIEWING,
            rows_total=len(transactions),
        )
        self.db.add(job)
        await self.db.flush()

        # Build preview
        valid = [t for t in transactions if not t.error and not t.is_duplicate]
        duplicates = [t for t in transactions if t.is_duplicate]
        errors = [t for t in transactions if t.error]

        return PreviewResult(
            total_rows=len(transactions),
            valid_transactions=len(valid),
            duplicates=len(duplicates),
            errors=len(errors),
            new_assets=new_assets,
            transactions=transactions,
            validation_errors=[t.error for t in errors if t.error],
        )

    # ── Step 5-8: Confirm and persist ──────────────────────────────────────────

    async def confirm_import(
        self,
        import_job_id: str,
        transactions: list[ParsedTransaction],
        portfolio_id: str,
    ) -> ImportJob:
        """
        Persist previewed transactions to the database.
        Creates FinancialEvent records and updates the ImportJob.
        """
        start_time = time.perf_counter()

        # Get/update job
        result = await self.db.execute(
            select(ImportJob).where(ImportJob.id == import_job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"ImportJob {import_job_id} not found")

        job.status = ImportStatus.IMPORTING
        job.started_at = datetime.now(timezone.utc)

        rows_imported = 0
        rows_failed = 0
        rows_duplicate = 0

        for txn in transactions:
            if txn.is_duplicate:
                rows_duplicate += 1
                continue
            if txn.error:
                rows_failed += 1
                continue

            try:
                # Ensure asset exists
                asset = await self._get_or_create_asset(txn)

                # Create financial event
                event = FinancialEvent(
                    portfolio_id=portfolio_id,
                    asset_id=asset.id,
                    import_job_id=import_job_id,
                    event_type=EventType(txn.event_type),
                    quantity=txn.quantity,
                    price=txn.price,
                    amount=txn.amount or (txn.quantity * txn.price),
                    fees=txn.fees,
                    executed_at=txn.executed_at,
                    source=txn.source,
                    exchange=txn.exchange,
                    notes=txn.notes,
                    split_ratio_from=txn.split_ratio_from,
                    split_ratio_to=txn.split_ratio_to,
                )
                self.db.add(event)
                rows_imported += 1
            except Exception as e:
                rows_failed += 1
                logger.warning("import.row_failed", row=txn.row_number, error=str(e))

        # Update job
        duration = int((time.perf_counter() - start_time) * 1000)
        job.rows_imported = rows_imported
        job.rows_failed = rows_failed
        job.rows_duplicate = rows_duplicate
        job.duration_ms = duration
        job.completed_at = datetime.now(timezone.utc)
        job.status = (
            ImportStatus.COMPLETED if rows_failed == 0
            else ImportStatus.PARTIAL if rows_imported > 0
            else ImportStatus.FAILED
        )

        await self.db.flush()

        logger.info(
            "import.completed",
            job_id=job.id,
            imported=rows_imported,
            failed=rows_failed,
            duplicates=rows_duplicate,
            duration_ms=duration,
        )

        return job

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _mark_duplicates(
        self, portfolio_id: str, transactions: list[ParsedTransaction]
    ) -> None:
        """Check if transactions already exist (same asset + date + type + qty)."""
        for txn in transactions:
            result = await self.db.execute(
                select(FinancialEvent).where(
                    FinancialEvent.portfolio_id == portfolio_id,
                    FinancialEvent.event_type == txn.event_type,
                    FinancialEvent.quantity == txn.quantity,
                    FinancialEvent.price == txn.price,
                    FinancialEvent.executed_at == txn.executed_at,
                ).limit(1)
            )
            if result.scalar_one_or_none():
                txn.is_duplicate = True

    async def _find_new_assets(self, transactions: list[ParsedTransaction]) -> list[str]:
        """Return tickers that don't exist in the assets table yet."""
        tickers = set(t.ticker for t in transactions if not t.error)
        new = []
        for ticker in tickers:
            result = await self.db.execute(
                select(Asset).where(Asset.ticker == ticker).limit(1)
            )
            if not result.scalar_one_or_none():
                new.append(ticker)
        return sorted(new)

    async def _get_or_create_asset(self, txn: ParsedTransaction) -> Asset:
        """Find asset by ticker, or create it if it doesn't exist."""
        result = await self.db.execute(
            select(Asset).where(Asset.ticker == txn.ticker).limit(1)
        )
        asset = result.scalar_one_or_none()

        if asset:
            return asset

        # Auto-create from transaction data
        asset = Asset(
            ticker=txn.ticker,
            name=txn.ticker,  # will be enriched later (Epic 3)
            isin=txn.isin,
            exchange=txn.exchange or "NSE",
        )
        self.db.add(asset)
        await self.db.flush()
        await self.db.refresh(asset)
        logger.info("asset.auto_created", ticker=txn.ticker, asset_id=asset.id)
        return asset
