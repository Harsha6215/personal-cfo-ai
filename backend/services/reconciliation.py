"""
Reconciliation Service — Story 2.8

Compares current holdings against the previous import to detect discrepancies.
Flags: new positions, missing positions, quantity mismatches.

Usage:
    service = ReconciliationService(db)
    alerts = await service.reconcile(portfolio_id)
"""

from dataclasses import dataclass

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.financial_event import FinancialEvent, EventType
from backend.models.asset import Asset
from backend.models.import_job import ImportJob
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)


@dataclass
class ReconciliationAlert:
    """A single reconciliation discrepancy."""
    ticker: str
    asset_id: str
    alert_type: str        # "new_position", "quantity_increase", "quantity_decrease", "position_gone"
    previous_qty: float
    current_qty: float
    difference: float
    message: str


class ReconciliationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile(self, portfolio_id: str) -> list[ReconciliationAlert]:
        """
        Compare the latest import against the previous state.
        Returns alerts for any discrepancies.
        """
        # Get the two most recent import jobs
        result = await self.db.execute(
            select(ImportJob)
            .where(ImportJob.portfolio_id == portfolio_id, ImportJob.status.in_(["COMPLETED", "PARTIAL"]))
            .order_by(ImportJob.created_at.desc())
            .limit(2)
        )
        jobs = result.scalars().all()

        if len(jobs) < 2:
            # Only one import — no previous state to compare against
            # Compare against empty (everything is new)
            engine = PortfolioEngine(self.db)
            holdings = await engine.calculate_holdings(portfolio_id)

            alerts = []
            for h in holdings:
                alerts.append(ReconciliationAlert(
                    ticker=h.ticker,
                    asset_id=h.asset_id,
                    alert_type="new_position",
                    previous_qty=0,
                    current_qty=h.quantity,
                    difference=h.quantity,
                    message=f"New position: {h.ticker} ({h.quantity} shares)",
                ))
            return alerts

        latest_job = jobs[0]
        previous_job = jobs[1]

        # Get events from the latest import
        latest_events = await self.db.execute(
            select(FinancialEvent, Asset)
            .join(Asset, FinancialEvent.asset_id == Asset.id)
            .where(FinancialEvent.import_job_id == latest_job.id)
        )
        latest_rows = latest_events.all()

        # Get events from the previous import
        previous_events = await self.db.execute(
            select(FinancialEvent, Asset)
            .join(Asset, FinancialEvent.asset_id == Asset.id)
            .where(FinancialEvent.import_job_id == previous_job.id)
        )
        previous_rows = previous_events.all()

        # Build ticker -> quantity maps
        latest_map: dict[str, float] = {}
        for event, asset in latest_rows:
            ticker = asset.ticker
            latest_map[ticker] = latest_map.get(ticker, 0) + float(event.quantity)

        previous_map: dict[str, float] = {}
        for event, asset in previous_rows:
            ticker = asset.ticker
            previous_map[ticker] = previous_map.get(ticker, 0) + float(event.quantity)

        # Find discrepancies
        alerts: list[ReconciliationAlert] = []
        all_tickers = set(latest_map.keys()) | set(previous_map.keys())

        for ticker in sorted(all_tickers):
            current_qty = latest_map.get(ticker, 0)
            prev_qty = previous_map.get(ticker, 0)
            diff = current_qty - prev_qty

            # Find asset_id
            asset_result = await self.db.execute(
                select(Asset).where(Asset.ticker == ticker).limit(1)
            )
            asset = asset_result.scalar_one_or_none()
            asset_id = asset.id if asset else ""

            if prev_qty == 0 and current_qty > 0:
                alerts.append(ReconciliationAlert(
                    ticker=ticker, asset_id=asset_id,
                    alert_type="new_position",
                    previous_qty=prev_qty, current_qty=current_qty, difference=diff,
                    message=f"New position: {ticker} ({current_qty} shares)",
                ))
            elif current_qty == 0 and prev_qty > 0:
                alerts.append(ReconciliationAlert(
                    ticker=ticker, asset_id=asset_id,
                    alert_type="position_gone",
                    previous_qty=prev_qty, current_qty=current_qty, difference=diff,
                    message=f"Position closed: {ticker} (was {prev_qty} shares)",
                ))
            elif abs(diff) > 0.001:
                alert_type = "quantity_increase" if diff > 0 else "quantity_decrease"
                direction = "increased" if diff > 0 else "decreased"
                alerts.append(ReconciliationAlert(
                    ticker=ticker, asset_id=asset_id,
                    alert_type=alert_type,
                    previous_qty=prev_qty, current_qty=current_qty, difference=diff,
                    message=f"{ticker} {direction} by {abs(diff)} shares ({prev_qty} → {current_qty})",
                ))

        return alerts
