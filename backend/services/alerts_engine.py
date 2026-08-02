"""
Alerts Engine — Story 5.8

Generates real-time alerts for portfolio changes, market events, and AI signals.
Alert types:
  - Price alerts (target hit, stop loss, big moves)
  - Portfolio alerts (concentration, rebalance needed)
  - AI alerts (recommendation changes, high-conviction signals)
  - News alerts (significant news about held stocks)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class AlertSeverity(str, Enum):
    CRITICAL = "critical"  # Immediate attention needed
    WARNING = "warning"  # Should review soon
    INFO = "info"  # FYI / informational


class AlertCategory(str, Enum):
    PRICE = "price"
    PORTFOLIO = "portfolio"
    AI_SIGNAL = "ai_signal"
    NEWS = "news"
    REBALANCE = "rebalance"


@dataclass
class Alert:
    """A single alert."""
    id: str
    category: str
    severity: str
    title: str
    message: str
    ticker: str | None = None
    action_required: bool = False
    suggested_action: str | None = None
    data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_read: bool = False


@dataclass
class AlertsSummary:
    """Summary of all active alerts."""
    alerts: list[Alert]
    critical_count: int
    warning_count: int
    info_count: int
    total: int


class AlertsEngine:
    """
    Generates alerts from portfolio and market state.
    Stateless computation — checks conditions and emits alerts.
    """

    def __init__(self):
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"alert_{self._counter}"

    def check_price_alerts(
        self, holdings: list[dict], quotes: dict[str, dict]
    ) -> list[Alert]:
        """Check for significant price movements in held stocks."""
        alerts = []

        for h in holdings:
            ticker = h["ticker"]
            quote = quotes.get(ticker, {})
            change_pct = quote.get("change_pct", 0)
            price = quote.get("price", 0)
            high_52w = quote.get("high_52w", 0)
            low_52w = quote.get("low_52w", 0)

            # Big daily drop (> 5%)
            if change_pct <= -5:
                alerts.append(Alert(
                    id=self._next_id(),
                    category=AlertCategory.PRICE,
                    severity=AlertSeverity.WARNING if change_pct > -8 else AlertSeverity.CRITICAL,
                    title=f"{ticker} dropped {change_pct:.1f}%",
                    message=f"Your holding {ticker} fell {abs(change_pct):.1f}% today to ₹{price:.0f}.",
                    ticker=ticker,
                    action_required=change_pct <= -8,
                    suggested_action="Review position and check for news",
                    data={"change_pct": change_pct, "price": price},
                ))

            # Big daily gain (> 8%)
            elif change_pct >= 8:
                alerts.append(Alert(
                    id=self._next_id(),
                    category=AlertCategory.PRICE,
                    severity=AlertSeverity.INFO,
                    title=f"{ticker} surged +{change_pct:.1f}%",
                    message=f"Your holding {ticker} gained {change_pct:.1f}% today. Consider booking partial profits.",
                    ticker=ticker,
                    suggested_action="Consider trimming position",
                    data={"change_pct": change_pct, "price": price},
                ))

            # Near 52W low
            if low_52w and price and low_52w > 0:
                dist = (price - low_52w) / low_52w * 100
                if dist <= 5:
                    alerts.append(Alert(
                        id=self._next_id(),
                        category=AlertCategory.PRICE,
                        severity=AlertSeverity.WARNING,
                        title=f"{ticker} near 52-week low",
                        message=f"{ticker} at ₹{price:.0f} is just {dist:.1f}% above its 52W low (₹{low_52w:.0f}).",
                        ticker=ticker,
                        suggested_action="Evaluate if fundamentals have changed",
                    ))

        return alerts

    def check_portfolio_alerts(
        self, holdings: list[dict], total_value: float
    ) -> list[Alert]:
        """Check portfolio-level alerts (concentration, etc)."""
        alerts = []

        if not holdings or total_value <= 0:
            return alerts

        # Concentration check
        for h in holdings:
            pct = h.get("invested_value", 0) / total_value * 100
            if pct > 30:
                alerts.append(Alert(
                    id=self._next_id(),
                    category=AlertCategory.PORTFOLIO,
                    severity=AlertSeverity.WARNING,
                    title=f"High concentration: {h['ticker']} ({pct:.0f}%)",
                    message=f"{h['ticker']} is {pct:.0f}% of your portfolio. Consider diversifying.",
                    ticker=h["ticker"],
                    action_required=True,
                    suggested_action="Trim position or add to other holdings",
                    data={"concentration_pct": pct},
                ))

        # Too few holdings
        if len(holdings) < 5:
            alerts.append(Alert(
                id=self._next_id(),
                category=AlertCategory.PORTFOLIO,
                severity=AlertSeverity.INFO,
                title="Low diversification",
                message=f"Only {len(holdings)} holdings. Consider adding more stocks for diversification.",
                action_required=False,
                suggested_action="Add 5-10 more stocks across different sectors",
            ))

        return alerts

    def check_ai_alerts(self, recommendations: list[dict]) -> list[Alert]:
        """Check for AI-generated alerts (strong signals)."""
        alerts = []

        for rec in recommendations:
            ticker = rec.get("ticker", "?")
            action = rec.get("action", "HOLD")
            confidence = rec.get("confidence", 0)

            if action == "STRONG_BUY" and confidence > 80:
                alerts.append(Alert(
                    id=self._next_id(),
                    category=AlertCategory.AI_SIGNAL,
                    severity=AlertSeverity.INFO,
                    title=f"Strong BUY signal: {ticker}",
                    message=f"AI Committee gives {ticker} a STRONG BUY with {confidence:.0f}% confidence.",
                    ticker=ticker,
                    suggested_action="Review analysis and consider adding",
                    data={"action": action, "confidence": confidence},
                ))
            elif action == "STRONG_SELL" and confidence > 75:
                alerts.append(Alert(
                    id=self._next_id(),
                    category=AlertCategory.AI_SIGNAL,
                    severity=AlertSeverity.WARNING,
                    title=f"SELL signal: {ticker}",
                    message=f"AI Committee recommends SELLING {ticker} ({confidence:.0f}% confidence).",
                    ticker=ticker,
                    action_required=True,
                    suggested_action="Review position and consider exiting",
                    data={"action": action, "confidence": confidence},
                ))

        return alerts

    def generate_all(
        self,
        holdings: list[dict],
        total_value: float,
        quotes: dict[str, dict],
        recommendations: list[dict] | None = None,
    ) -> AlertsSummary:
        """Run all alert checks and return summary."""
        self._counter = 0
        all_alerts = []

        all_alerts.extend(self.check_price_alerts(holdings, quotes))
        all_alerts.extend(self.check_portfolio_alerts(holdings, total_value))
        if recommendations:
            all_alerts.extend(self.check_ai_alerts(recommendations))

        # Sort: critical first, then warning, then info
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        all_alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

        return AlertsSummary(
            alerts=all_alerts,
            critical_count=sum(1 for a in all_alerts if a.severity == "critical"),
            warning_count=sum(1 for a in all_alerts if a.severity == "warning"),
            info_count=sum(1 for a in all_alerts if a.severity == "info"),
            total=len(all_alerts),
        )
