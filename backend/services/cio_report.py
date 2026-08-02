"""
Daily CIO Report Generator — Story 5.12

Produces a comprehensive daily investment intelligence report:
  - Market overview (indices, sectors)
  - Portfolio health snapshot
  - Top recommendations
  - Alerts summary
  - Opportunity pipeline
  - Key risks to watch
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MarketSnapshot:
    """Market indices and sector overview."""
    nifty50: float | None = None
    nifty50_change_pct: float | None = None
    sensex: float | None = None
    sensex_change_pct: float | None = None
    market_mood: str = "neutral"  # bullish, bearish, neutral
    top_gaining_sectors: list[str] = field(default_factory=list)
    top_losing_sectors: list[str] = field(default_factory=list)


@dataclass
class PortfolioSnapshot:
    """Quick portfolio health check."""
    total_invested: float = 0
    total_holdings: int = 0
    top_gainers: list[dict] = field(default_factory=list)  # [{ticker, change_pct}]
    top_losers: list[dict] = field(default_factory=list)
    needs_rebalance: bool = False
    concentration_warnings: list[str] = field(default_factory=list)


@dataclass
class CIOReport:
    """The complete Daily CIO Report."""
    report_date: str
    greeting: str
    market: MarketSnapshot
    portfolio: PortfolioSnapshot
    top_recommendations: list[dict]  # [{ticker, action, confidence, reason}]
    alerts_summary: dict  # {critical, warning, info, total}
    opportunities: list[dict]  # [{ticker, type, score, reason}]
    risks_to_watch: list[str]
    action_items: list[str]  # Concrete things to do today
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CIOReportGenerator:
    """
    Assembles a daily CIO report from all intelligence sources.
    Pure assembly — receives pre-computed data from services.
    """

    def generate(
        self,
        market_data: dict | None = None,
        portfolio_data: dict | None = None,
        recommendations: list[dict] | None = None,
        alerts: dict | None = None,
        opportunities: list[dict] | None = None,
    ) -> CIOReport:
        """Assemble CIO report from all sources."""
        now = datetime.now(timezone.utc)
        report_date = now.strftime("%B %d, %Y")
        hour = now.hour

        # Greeting based on time
        if hour < 12:
            greeting = "Good morning! Here's your daily investment briefing."
        elif hour < 17:
            greeting = "Good afternoon! Here's your market update."
        else:
            greeting = "Good evening! Here's today's investment summary."

        # Market snapshot
        market = self._build_market_snapshot(market_data)

        # Portfolio snapshot
        portfolio = self._build_portfolio_snapshot(portfolio_data)

        # Top recommendations (limit to 5)
        top_recs = []
        if recommendations:
            strong = [r for r in recommendations if r.get("action") in ("STRONG_BUY", "STRONG_SELL", "BUY")]
            top_recs = sorted(strong, key=lambda r: r.get("confidence", 0), reverse=True)[:5]

        # Alerts summary
        alerts_summary = alerts or {"critical": 0, "warning": 0, "info": 0, "total": 0}

        # Opportunities (limit to 5)
        opps = (opportunities or [])[:5]

        # Risks to watch
        risks = self._identify_risks(market, portfolio, alerts_summary)

        # Action items
        action_items = self._build_action_items(
            market, portfolio, top_recs, alerts_summary, opps
        )

        return CIOReport(
            report_date=report_date,
            greeting=greeting,
            market=market,
            portfolio=portfolio,
            top_recommendations=top_recs,
            alerts_summary=alerts_summary,
            opportunities=opps,
            risks_to_watch=risks,
            action_items=action_items,
        )

    def _build_market_snapshot(self, data: dict | None) -> MarketSnapshot:
        if not data:
            return MarketSnapshot()

        change = data.get("nifty50_change_pct", 0)
        mood = "bullish" if change > 1 else "bearish" if change < -1 else "neutral"

        return MarketSnapshot(
            nifty50=data.get("nifty50"),
            nifty50_change_pct=data.get("nifty50_change_pct"),
            sensex=data.get("sensex"),
            sensex_change_pct=data.get("sensex_change_pct"),
            market_mood=mood,
            top_gaining_sectors=data.get("top_gaining_sectors", []),
            top_losing_sectors=data.get("top_losing_sectors", []),
        )

    def _build_portfolio_snapshot(self, data: dict | None) -> PortfolioSnapshot:
        if not data:
            return PortfolioSnapshot()

        return PortfolioSnapshot(
            total_invested=data.get("total_invested", 0),
            total_holdings=data.get("total_holdings", 0),
            top_gainers=data.get("top_gainers", [])[:3],
            top_losers=data.get("top_losers", [])[:3],
            needs_rebalance=data.get("needs_rebalance", False),
            concentration_warnings=data.get("concentration_warnings", []),
        )

    def _identify_risks(self, market: MarketSnapshot, portfolio: PortfolioSnapshot, alerts: dict) -> list[str]:
        risks = []
        if market.market_mood == "bearish":
            risks.append("Market in bearish territory — defensive positioning recommended")
        if portfolio.needs_rebalance:
            risks.append("Portfolio needs rebalancing — allocation drift detected")
        if portfolio.concentration_warnings:
            risks.append(f"Concentration risk: {', '.join(portfolio.concentration_warnings[:2])}")
        if alerts.get("critical", 0) > 0:
            risks.append(f"{alerts['critical']} critical alert(s) require immediate attention")
        if not risks:
            risks.append("No significant risks detected today")
        return risks

    def _build_action_items(
        self, market, portfolio, recommendations, alerts, opportunities
    ) -> list[str]:
        items = []

        if alerts.get("critical", 0) > 0:
            items.append(f"⚠️ Review {alerts['critical']} critical alert(s)")

        if portfolio.needs_rebalance:
            items.append("📊 Review rebalance plan — portfolio drifted from targets")

        if recommendations:
            strong_buys = [r["ticker"] for r in recommendations if r.get("action") == "STRONG_BUY"]
            if strong_buys:
                items.append(f"🎯 Strong buy signals: {', '.join(strong_buys[:3])}")

        if opportunities:
            items.append(f"🔍 {len(opportunities)} new opportunities identified — review scanner")

        if not items:
            items.append("✅ No urgent actions today. Portfolio is on track.")

        return items
