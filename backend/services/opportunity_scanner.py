"""
Opportunity Scanner — Story 5.4

Identifies investment opportunities based on:
  - Stocks near 52-week lows with strong fundamentals
  - Sector rotation signals
  - High-conviction recommendations from Decision Engine
  - Watchlist price triggers
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class OpportunityType(str, Enum):
    VALUE_DIP = "value_dip"           # Near 52W low + good fundamentals
    MOMENTUM = "momentum"             # Strong uptrend + volume breakout
    SECTOR_ROTATION = "sector_rotation"  # Sector turning favorable
    HIGH_CONVICTION = "high_conviction"  # Multiple agents agree strongly
    WATCHLIST_TRIGGER = "watchlist_trigger"  # Watchlist stock hit target


@dataclass
class Opportunity:
    """A single investment opportunity."""
    ticker: str
    name: str
    opportunity_type: str
    score: float  # 0-100 attractiveness
    reason: str
    entry_price: float | None = None
    target_price: float | None = None
    upside_pct: float | None = None
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    evidence: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ScanResult:
    """Results from an opportunity scan."""
    total_scanned: int
    opportunities: list[Opportunity]
    scan_time_ms: int = 0
    summary: str = ""


class OpportunityScanner:
    """
    Scans market data to identify actionable opportunities.
    Pure computation — works with pre-fetched data.
    """

    def scan_value_dips(self, quotes: list[dict]) -> list[Opportunity]:
        """Find stocks near 52W lows that might be undervalued."""
        opportunities = []

        for q in quotes:
            ticker = q.get("ticker", "")
            price = q.get("price", 0)
            low_52w = q.get("low_52w", 0)
            high_52w = q.get("high_52w", 0)
            pe_ratio = q.get("pe_ratio")

            if not price or not low_52w or not high_52w:
                continue

            # Calculate distance from 52W low
            distance_from_low = ((price - low_52w) / low_52w * 100) if low_52w > 0 else 999
            distance_from_high = ((high_52w - price) / high_52w * 100) if high_52w > 0 else 0

            # Opportunity: within 15% of 52W low AND reasonable PE
            if distance_from_low <= 15 and (pe_ratio is None or pe_ratio < 30):
                score = max(0, 100 - distance_from_low * 5)
                evidence = [
                    f"Price ₹{price:.0f} is {distance_from_low:.1f}% above 52W low (₹{low_52w:.0f})",
                    f"Down {distance_from_high:.1f}% from 52W high (₹{high_52w:.0f})",
                ]
                if pe_ratio:
                    evidence.append(f"P/E ratio: {pe_ratio:.1f}")

                opportunities.append(Opportunity(
                    ticker=ticker,
                    name=q.get("name", ticker),
                    opportunity_type=OpportunityType.VALUE_DIP,
                    score=round(score, 1),
                    reason=f"Trading near 52W low with {distance_from_high:.0f}% upside potential",
                    entry_price=price,
                    target_price=high_52w * 0.8,  # conservative 80% of high
                    upside_pct=round(distance_from_high, 1),
                    risk_level="MEDIUM" if distance_from_low > 5 else "HIGH",
                    evidence=evidence,
                ))

        opportunities.sort(key=lambda o: o.score, reverse=True)
        return opportunities

    def scan_momentum(self, quotes: list[dict]) -> list[Opportunity]:
        """Find stocks with strong momentum (near 52W highs with volume)."""
        opportunities = []

        for q in quotes:
            ticker = q.get("ticker", "")
            price = q.get("price", 0)
            high_52w = q.get("high_52w", 0)
            change_pct = q.get("change_pct", 0)

            if not price or not high_52w:
                continue

            distance_from_high = ((high_52w - price) / high_52w * 100) if high_52w > 0 else 999

            # Momentum: within 5% of 52W high AND positive daily change
            if distance_from_high <= 5 and change_pct > 0:
                score = max(0, 90 - distance_from_high * 10)
                opportunities.append(Opportunity(
                    ticker=ticker,
                    name=q.get("name", ticker),
                    opportunity_type=OpportunityType.MOMENTUM,
                    score=round(score, 1),
                    reason=f"Strong momentum — {distance_from_high:.1f}% from 52W high",
                    entry_price=price,
                    risk_level="MEDIUM",
                    evidence=[
                        f"Price ₹{price:.0f} near 52W high (₹{high_52w:.0f})",
                        f"Today: +{change_pct:.2f}%",
                    ],
                ))

        opportunities.sort(key=lambda o: o.score, reverse=True)
        return opportunities

    def scan_from_recommendations(
        self, recommendations: list[dict]
    ) -> list[Opportunity]:
        """Convert high-conviction recommendations into opportunities."""
        opportunities = []

        for rec in recommendations:
            if rec.get("action") in ("STRONG_BUY", "BUY") and rec.get("confidence", 0) > 70:
                opportunities.append(Opportunity(
                    ticker=rec["ticker"],
                    name=rec.get("name", rec["ticker"]),
                    opportunity_type=OpportunityType.HIGH_CONVICTION,
                    score=rec.get("confidence", 75),
                    reason=f"AI Committee: {rec['action']} with {rec.get('confidence', 0):.0f}% confidence",
                    risk_level="LOW" if rec.get("confidence", 0) > 85 else "MEDIUM",
                    evidence=rec.get("evidence", []),
                ))

        return opportunities
