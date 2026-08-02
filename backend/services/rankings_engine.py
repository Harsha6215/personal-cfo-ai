"""
Buy/Sell Rankings Engine — Story 5.6

Produces a ranked leaderboard of stocks sorted by composite decision score.
Combines Decision Engine outputs into a single ranked list with:
  - Relative strength
  - Conviction levels
  - Position sizing suggestions
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RankedStock:
    """A stock with its ranking and score breakdown."""
    rank: int
    ticker: str
    name: str
    action: str  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    composite_score: float  # 0-10
    confidence: float  # 0-100
    momentum_score: float  # price momentum (0-10)
    value_score: float  # value attractiveness (0-10)
    risk_score: float  # risk (0-10, higher = safer)
    change_from_last: str  # "up", "down", "same", "new"
    suggested_action: str  # "Add", "Hold", "Trim", "Exit"


@dataclass
class Rankings:
    """Complete rankings output."""
    buy_list: list[RankedStock]
    sell_list: list[RankedStock]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str = ""


class RankingsEngine:
    """
    Produces ranked buy/sell lists from Decision Engine recommendations.
    """

    def rank(self, recommendations: list[dict]) -> Rankings:
        """
        Rank stocks from a list of recommendation dicts.

        Each dict: {ticker, name, action, weighted_score, confidence, agent_scores}
        """
        buy_list = []
        sell_list = []

        for rec in recommendations:
            score = rec.get("weighted_score", 5.0)
            confidence = rec.get("confidence", 50)
            action = rec.get("action", "HOLD")
            agent_scores = rec.get("agent_scores", {})

            # Extract sub-scores
            momentum = agent_scores.get("technical_analyst", 5.0)
            value = agent_scores.get("valuation_specialist", 5.0)
            risk = agent_scores.get("risk_manager", 5.0)

            # Determine suggested action
            if action in ("STRONG_BUY", "BUY") and confidence > 70:
                suggested = "Add"
            elif action in ("STRONG_SELL", "SELL"):
                suggested = "Exit" if confidence > 75 else "Trim"
            else:
                suggested = "Hold"

            stock = RankedStock(
                rank=0,  # assigned below
                ticker=rec.get("ticker", "?"),
                name=rec.get("name", rec.get("ticker", "?")),
                action=action,
                composite_score=round(score, 2),
                confidence=round(confidence, 1),
                momentum_score=round(momentum, 1),
                value_score=round(value, 1),
                risk_score=round(risk, 1),
                change_from_last="new",
                suggested_action=suggested,
            )

            if action in ("STRONG_BUY", "BUY"):
                buy_list.append(stock)
            elif action in ("STRONG_SELL", "SELL"):
                sell_list.append(stock)

        # Sort and assign ranks
        buy_list.sort(key=lambda s: (s.composite_score, s.confidence), reverse=True)
        for i, s in enumerate(buy_list, 1):
            s.rank = i

        sell_list.sort(key=lambda s: s.composite_score)
        for i, s in enumerate(sell_list, 1):
            s.rank = i

        summary = f"{len(buy_list)} stocks on Buy list, {len(sell_list)} on Sell list."
        return Rankings(buy_list=buy_list, sell_list=sell_list, summary=summary)
