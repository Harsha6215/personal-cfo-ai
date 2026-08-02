"""
Allocation Engine — Story 5.3

Computes target vs actual allocation and suggests rebalancing moves.
Supports multiple allocation strategies:
  - Equal Weight
  - Market Cap Weighted
  - Risk Parity
  - Custom (user-defined targets)
"""

from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class Strategy(str, Enum):
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP = "market_cap"
    RISK_PARITY = "risk_parity"
    CUSTOM = "custom"


@dataclass
class AllocationSlot:
    """One slot in target allocation."""
    ticker: str
    name: str
    target_pct: float
    actual_pct: float
    drift_pct: float  # actual - target
    action: str  # "BUY_MORE", "TRIM", "ON_TARGET"
    amount_to_adjust: float  # INR to buy/sell to reach target


@dataclass
class AllocationPlan:
    """Full allocation plan for a portfolio."""
    strategy: str
    total_value: float
    slots: list[AllocationSlot]
    max_drift: float
    needs_rebalance: bool
    summary: str


class AllocationEngine:
    """
    Computes target allocations and drift analysis.
    Pure computation — no DB or LLM needed.
    """

    DRIFT_THRESHOLD = 5.0  # rebalance if any slot drifts > 5%

    def compute_equal_weight(
        self, holdings: list[dict], total_value: float
    ) -> AllocationPlan:
        """Equal weight across all holdings."""
        n = len(holdings)
        if n == 0:
            return AllocationPlan(
                strategy="equal_weight", total_value=0,
                slots=[], max_drift=0, needs_rebalance=False,
                summary="No holdings to allocate.",
            )

        target_pct = 100.0 / n
        slots = []
        max_drift = 0.0

        for h in holdings:
            actual_pct = (h["invested_value"] / total_value * 100) if total_value > 0 else 0
            drift = actual_pct - target_pct
            max_drift = max(max_drift, abs(drift))

            if drift > self.DRIFT_THRESHOLD:
                action = "TRIM"
            elif drift < -self.DRIFT_THRESHOLD:
                action = "BUY_MORE"
            else:
                action = "ON_TARGET"

            amount = abs(drift / 100 * total_value)

            slots.append(AllocationSlot(
                ticker=h["ticker"],
                name=h.get("name", h["ticker"]),
                target_pct=round(target_pct, 2),
                actual_pct=round(actual_pct, 2),
                drift_pct=round(drift, 2),
                action=action,
                amount_to_adjust=round(amount, 2),
            ))

        slots.sort(key=lambda s: abs(s.drift_pct), reverse=True)
        needs_rebalance = max_drift > self.DRIFT_THRESHOLD

        overweight = [s.ticker for s in slots if s.action == "TRIM"]
        underweight = [s.ticker for s in slots if s.action == "BUY_MORE"]
        summary_parts = [f"Equal-weight target: {target_pct:.1f}% each."]
        if overweight:
            summary_parts.append(f"Overweight: {', '.join(overweight[:3])}.")
        if underweight:
            summary_parts.append(f"Underweight: {', '.join(underweight[:3])}.")
        if not needs_rebalance:
            summary_parts.append("Portfolio is within tolerance.")

        return AllocationPlan(
            strategy="equal_weight",
            total_value=total_value,
            slots=slots,
            max_drift=round(max_drift, 2),
            needs_rebalance=needs_rebalance,
            summary=" ".join(summary_parts),
        )

    def compute_custom(
        self, holdings: list[dict], total_value: float, targets: dict[str, float]
    ) -> AllocationPlan:
        """Custom targets: {ticker: target_pct}."""
        slots = []
        max_drift = 0.0

        for h in holdings:
            ticker = h["ticker"]
            target_pct = targets.get(ticker, 0)
            actual_pct = (h["invested_value"] / total_value * 100) if total_value > 0 else 0
            drift = actual_pct - target_pct
            max_drift = max(max_drift, abs(drift))

            if drift > self.DRIFT_THRESHOLD:
                action = "TRIM"
            elif drift < -self.DRIFT_THRESHOLD:
                action = "BUY_MORE"
            else:
                action = "ON_TARGET"

            amount = abs(drift / 100 * total_value)
            slots.append(AllocationSlot(
                ticker=ticker,
                name=h.get("name", ticker),
                target_pct=round(target_pct, 2),
                actual_pct=round(actual_pct, 2),
                drift_pct=round(drift, 2),
                action=action,
                amount_to_adjust=round(amount, 2),
            ))

        slots.sort(key=lambda s: abs(s.drift_pct), reverse=True)
        needs_rebalance = max_drift > self.DRIFT_THRESHOLD

        return AllocationPlan(
            strategy="custom",
            total_value=total_value,
            slots=slots,
            max_drift=round(max_drift, 2),
            needs_rebalance=needs_rebalance,
            summary=f"Custom allocation. Max drift: {max_drift:.1f}%. {'Rebalance needed.' if needs_rebalance else 'Within tolerance.'}",
        )

    def compute_sector_allocation(self, holdings: list[dict], total_value: float) -> dict:
        """Group holdings by sector/asset_type and compute allocation."""
        sectors: dict[str, float] = {}
        for h in holdings:
            sector = h.get("asset_type", "UNKNOWN")
            sectors[sector] = sectors.get(sector, 0) + h.get("invested_value", 0)

        return {
            sector: round(val / total_value * 100, 2) if total_value > 0 else 0
            for sector, val in sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        }
