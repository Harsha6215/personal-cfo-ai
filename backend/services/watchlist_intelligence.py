"""
Watchlist Intelligence — Story 5.7

Enriches watchlist items with real-time intelligence:
  - Price alerts & target monitoring
  - AI-driven entry/exit signals
  - News sentiment for watched stocks
  - Technical trigger detection
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class WatchlistInsight:
    """Intelligence for a single watchlist item."""
    ticker: str
    name: str
    current_price: float
    change_pct: float
    # Price levels
    target_price: float | None = None
    stop_loss: float | None = None
    distance_to_target_pct: float | None = None
    # Intelligence
    signal: str = "NEUTRAL"  # ENTRY, EXIT, NEUTRAL, WATCH
    signal_reason: str = ""
    sentiment: str = "neutral"
    risk_level: str = "MEDIUM"
    # Scores
    composite_score: float | None = None
    news_count: int = 0
    alerts: list[str] = field(default_factory=list)


@dataclass
class WatchlistReport:
    """Full intelligence report for watchlist."""
    items: list[WatchlistInsight]
    actionable_count: int  # items with signal != NEUTRAL
    total_items: int
    summary: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WatchlistIntelligence:
    """
    Enriches raw watchlist with intelligence signals.
    """

    def analyze(
        self,
        watchlist: list[dict],  # {ticker, notes, target_price, stop_loss}
        quotes: dict[str, dict],  # {ticker: {price, change_pct, high_52w, low_52w}}
        recommendations: dict[str, dict] | None = None,  # {ticker: decision engine output}
    ) -> WatchlistReport:
        """Enrich watchlist items with intelligence."""
        items = []

        for item in watchlist:
            ticker = item["ticker"]
            quote = quotes.get(ticker, {})
            rec = recommendations.get(ticker, {}) if recommendations else {}

            price = quote.get("price", 0)
            change_pct = quote.get("change_pct", 0)
            high_52w = quote.get("high_52w", 0)
            low_52w = quote.get("low_52w", 0)

            # Targets from user notes or defaults
            target_price = item.get("target_price")
            stop_loss = item.get("stop_loss")

            # Calculate distances
            dist_to_target = None
            if target_price and price:
                dist_to_target = (target_price - price) / price * 100

            # Generate signal
            signal, reason = self._generate_signal(
                price, change_pct, high_52w, low_52w,
                target_price, stop_loss, rec
            )

            # Build alerts
            alerts = self._build_alerts(price, change_pct, high_52w, low_52w, target_price, stop_loss)

            items.append(WatchlistInsight(
                ticker=ticker,
                name=item.get("name", ticker),
                current_price=price,
                change_pct=round(change_pct, 2),
                target_price=target_price,
                stop_loss=stop_loss,
                distance_to_target_pct=round(dist_to_target, 2) if dist_to_target else None,
                signal=signal,
                signal_reason=reason,
                sentiment=rec.get("sentiment", "neutral"),
                risk_level=rec.get("risk_level", "MEDIUM"),
                composite_score=rec.get("weighted_score"),
                alerts=alerts,
            ))

        actionable = sum(1 for i in items if i.signal != "NEUTRAL")
        summary = f"{len(items)} watched stocks. {actionable} with actionable signals."

        return WatchlistReport(
            items=items,
            actionable_count=actionable,
            total_items=len(items),
            summary=summary,
        )

    def _generate_signal(
        self, price, change_pct, high_52w, low_52w,
        target_price, stop_loss, rec
    ) -> tuple[str, str]:
        """Generate entry/exit signal based on technical and AI data."""
        # Stop loss hit
        if stop_loss and price and price <= stop_loss:
            return "EXIT", f"Price ₹{price:.0f} hit stop loss ₹{stop_loss:.0f}"

        # Target hit
        if target_price and price and price >= target_price:
            return "EXIT", f"Price ₹{price:.0f} reached target ₹{target_price:.0f}"

        # AI strong buy signal
        if rec.get("action") in ("STRONG_BUY",) and rec.get("confidence", 0) > 75:
            return "ENTRY", f"AI Committee: STRONG BUY ({rec.get('confidence', 0):.0f}% confidence)"

        # Near 52W low (potential entry)
        if low_52w and price:
            dist_from_low = (price - low_52w) / low_52w * 100 if low_52w > 0 else 999
            if dist_from_low <= 10:
                return "ENTRY", f"Near 52W low — {dist_from_low:.1f}% above ₹{low_52w:.0f}"

        # AI sell signal
        if rec.get("action") in ("STRONG_SELL", "SELL"):
            return "EXIT", f"AI Committee: {rec.get('action')}"

        # Big daily move (needs attention)
        if abs(change_pct) > 5:
            direction = "up" if change_pct > 0 else "down"
            return "WATCH", f"Big move today: {change_pct:+.1f}% ({direction})"

        return "NEUTRAL", "No actionable signal"

    def _build_alerts(self, price, change_pct, high_52w, low_52w, target, stop_loss) -> list[str]:
        """Build alert list for this stock."""
        alerts = []
        if abs(change_pct) > 3:
            alerts.append(f"{'📈' if change_pct > 0 else '📉'} Moved {change_pct:+.1f}% today")
        if low_52w and price and (price - low_52w) / low_52w * 100 < 5:
            alerts.append("⚠️ Near 52-week low")
        if high_52w and price and (high_52w - price) / high_52w * 100 < 5:
            alerts.append("🎯 Near 52-week high")
        if target and price and price >= target * 0.95:
            alerts.append("🎯 Approaching target price")
        if stop_loss and price and price <= stop_loss * 1.05:
            alerts.append("⚠️ Approaching stop loss")
        return alerts
