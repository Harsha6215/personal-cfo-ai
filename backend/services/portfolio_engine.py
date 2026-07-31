"""
Portfolio Calculation Engine — Story 2.5

Replays financial events to compute current holdings.
This engine doesn't know about Zerodha or any broker — only canonical events.

Usage:
    engine = PortfolioEngine(db)
    holdings = await engine.calculate_holdings(portfolio_id)
    summary = await engine.get_summary(portfolio_id)
"""

from dataclasses import dataclass

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset
from backend.models.financial_event import EventType, FinancialEvent

logger = structlog.get_logger(__name__)


@dataclass
class ComputedHolding:
    """A single holding computed from events."""
    asset_id: str
    ticker: str
    name: str
    asset_type: str
    quantity: float
    average_cost: float
    invested_value: float   # quantity * average_cost
    # current_price: float  # needs live data (Epic 3)
    # market_value: float
    # unrealized_gain: float
    # gain_pct: float


@dataclass
class PortfolioSummaryData:
    """Aggregated portfolio metrics."""
    total_invested: float
    total_holdings: int
    total_events: int
    holdings: list[ComputedHolding]


class PortfolioEngine:
    """Replays events to derive current portfolio state."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_holdings(self, portfolio_id: str) -> list[ComputedHolding]:
        """
        Replay all events for a portfolio and return computed holdings.

        Logic:
            BUY/SIP:   add quantity, update average cost
            SELL:      subtract quantity
            BONUS:     add quantity at zero cost
            SPLIT:     multiply quantity, divide average cost
            DIVIDEND:  no quantity change (record only)
        """
        # Fetch all events ordered chronologically
        result = await self.db.execute(
            select(FinancialEvent, Asset)
            .join(Asset, FinancialEvent.asset_id == Asset.id)
            .where(FinancialEvent.portfolio_id == portfolio_id)
            .order_by(FinancialEvent.executed_at)
        )
        rows = result.all()

        # Build position map: asset_id -> {quantity, total_cost}
        positions: dict[str, dict] = {}

        for event, asset in rows:
            aid = event.asset_id
            if aid not in positions:
                positions[aid] = {
                    "quantity": 0.0,
                    "total_cost": 0.0,
                    "ticker": asset.ticker,
                    "name": asset.name,
                    "asset_type": asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type),
                }

            pos = positions[aid]
            qty = float(event.quantity)
            price = float(event.price)

            if event.event_type in (EventType.BUY, EventType.SIP):
                pos["total_cost"] += qty * price
                pos["quantity"] += qty

            elif event.event_type == EventType.SELL:
                if pos["quantity"] > 0:
                    # Reduce cost proportionally
                    cost_per_unit = pos["total_cost"] / pos["quantity"] if pos["quantity"] > 0 else 0
                    pos["total_cost"] -= qty * cost_per_unit
                    pos["quantity"] -= qty

            elif event.event_type == EventType.BONUS:
                # Free shares — no cost
                pos["quantity"] += qty

            elif event.event_type == EventType.SPLIT:
                # Split: multiply quantity by ratio
                if event.split_ratio_from and event.split_ratio_to:
                    ratio = float(event.split_ratio_to) / float(event.split_ratio_from)
                    pos["quantity"] *= ratio
                    # Average cost adjusts inversely
                    # total_cost stays same, quantity increases

            # DIVIDEND, INTEREST, TAX: no quantity change

        # Convert to ComputedHolding objects (only positions with quantity > 0)
        holdings = []
        for aid, pos in positions.items():
            if pos["quantity"] > 0.001:  # filter out dust
                avg_cost = pos["total_cost"] / pos["quantity"] if pos["quantity"] > 0 else 0
                holdings.append(ComputedHolding(
                    asset_id=aid,
                    ticker=pos["ticker"],
                    name=pos["name"],
                    asset_type=pos["asset_type"],
                    quantity=round(pos["quantity"], 4),
                    average_cost=round(avg_cost, 2),
                    invested_value=round(pos["total_cost"], 2),
                ))

        # Sort by invested value descending
        holdings.sort(key=lambda h: h.invested_value, reverse=True)
        return holdings

    async def get_summary(self, portfolio_id: str) -> PortfolioSummaryData:
        """Get portfolio summary with holdings."""
        holdings = await self.calculate_holdings(portfolio_id)

        total_invested = sum(h.invested_value for h in holdings)

        # Count total events
        event_count = await self.db.execute(
            select(func.count(FinancialEvent.id))
            .where(FinancialEvent.portfolio_id == portfolio_id)
        )
        total_events = event_count.scalar() or 0

        return PortfolioSummaryData(
            total_invested=round(total_invested, 2),
            total_holdings=len(holdings),
            total_events=total_events,
            holdings=holdings,
        )
