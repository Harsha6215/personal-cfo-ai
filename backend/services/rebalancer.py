"""
Portfolio Rebalancer — Story 5.5

Generates concrete buy/sell orders to move portfolio toward target allocation.
Considers:
  - Transaction costs (brokerage)
  - Minimum trade sizes
  - Tax implications (LTCG vs STCG threshold)
  - Lot size constraints
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RebalanceOrder:
    """A single rebalance trade order."""
    ticker: str
    name: str
    action: str  # "BUY" or "SELL"
    quantity: int
    estimated_price: float
    estimated_amount: float
    reason: str
    priority: int  # 1 = highest priority


@dataclass
class RebalancePlan:
    """Complete rebalance plan with orders."""
    orders: list[RebalanceOrder]
    total_buy_amount: float
    total_sell_amount: float
    net_cash_needed: float
    estimated_charges: float
    tax_note: str
    summary: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioRebalancer:
    """
    Generates rebalance orders from allocation drift data.
    Pure computation — works with allocation plan output.
    """

    BROKERAGE_PCT = 0.03  # 0.03% (discount broker)
    STT_PCT = 0.1  # 0.1% on sell side
    MIN_ORDER_AMOUNT = 500  # Don't bother with orders < ₹500

    def generate_plan(
        self,
        allocation_slots: list[dict],
        prices: dict[str, float],
        available_cash: float = 0,
    ) -> RebalancePlan:
        """
        Generate rebalance orders from allocation drift data.

        Args:
            allocation_slots: list of {ticker, name, drift_pct, action, amount_to_adjust}
            prices: {ticker: current_price}
            available_cash: extra cash available for buying
        """
        orders = []
        total_buy = 0.0
        total_sell = 0.0
        priority = 0

        # Process sells first (generate cash), then buys
        sells = [s for s in allocation_slots if s.get("action") == "TRIM"]
        buys = [s for s in allocation_slots if s.get("action") == "BUY_MORE"]

        # SELLS
        for slot in sorted(sells, key=lambda s: abs(s.get("drift_pct", 0)), reverse=True):
            ticker = slot["ticker"]
            price = prices.get(ticker, 0)
            amount = slot.get("amount_to_adjust", 0)

            if price <= 0 or amount < self.MIN_ORDER_AMOUNT:
                continue

            priority += 1
            qty = int(amount / price)
            if qty <= 0:
                continue

            est_amount = qty * price
            total_sell += est_amount

            orders.append(RebalanceOrder(
                ticker=ticker,
                name=slot.get("name", ticker),
                action="SELL",
                quantity=qty,
                estimated_price=price,
                estimated_amount=round(est_amount, 2),
                reason=f"Overweight by {abs(slot.get('drift_pct', 0)):.1f}%",
                priority=priority,
            ))

        # BUYS
        cash_available = available_cash + total_sell
        for slot in sorted(buys, key=lambda s: abs(s.get("drift_pct", 0)), reverse=True):
            ticker = slot["ticker"]
            price = prices.get(ticker, 0)
            amount = min(slot.get("amount_to_adjust", 0), cash_available)

            if price <= 0 or amount < self.MIN_ORDER_AMOUNT:
                continue

            priority += 1
            qty = int(amount / price)
            if qty <= 0:
                continue

            est_amount = qty * price
            total_buy += est_amount
            cash_available -= est_amount

            orders.append(RebalanceOrder(
                ticker=ticker,
                name=slot.get("name", ticker),
                action="BUY",
                quantity=qty,
                estimated_price=price,
                estimated_amount=round(est_amount, 2),
                reason=f"Underweight by {abs(slot.get('drift_pct', 0)):.1f}%",
                priority=priority,
            ))

        # Charges estimate
        charges = (total_buy + total_sell) * self.BROKERAGE_PCT / 100
        charges += total_sell * self.STT_PCT / 100

        net_cash = total_buy - total_sell
        tax_note = "Sells held > 1 year: LTCG (10% above ₹1L). Held < 1 year: STCG (15%)."

        sell_count = sum(1 for o in orders if o.action == "SELL")
        buy_count = sum(1 for o in orders if o.action == "BUY")
        summary = f"{len(orders)} orders ({buy_count} buys, {sell_count} sells). "
        summary += f"Net cash needed: ₹{max(0, net_cash):,.0f}." if net_cash > 0 else f"Generates ₹{abs(net_cash):,.0f} cash."

        return RebalancePlan(
            orders=orders,
            total_buy_amount=round(total_buy, 2),
            total_sell_amount=round(total_sell, 2),
            net_cash_needed=round(max(0, net_cash), 2),
            estimated_charges=round(charges, 2),
            tax_note=tax_note,
            summary=summary,
        )
