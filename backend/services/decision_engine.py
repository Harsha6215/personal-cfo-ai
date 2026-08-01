"""
Decision Intelligence Engine — Epic 5

Transforms AI analysis into personalized, explainable investment decisions.
Not an LLM — a weighted scoring engine that combines agent outputs.

Story 5.1: Recommendation Engine (weighs agent scores)
Story 5.2: Portfolio Context (personalizes based on holdings)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)


# ── Configurable weights per agent ─────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "financial_analyst": 0.25,
    "valuation_specialist": 0.20,
    "technical_analyst": 0.15,
    "news_analyst": 0.15,
    "risk_manager": 0.15,
    "macro_economist": 0.10,
}


@dataclass
class Recommendation:
    """Final investment recommendation with full explainability."""
    ticker: str
    action: str              # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    confidence: float        # 0-100%
    priority: str            # HIGH, MEDIUM, LOW
    weighted_score: float    # 0-10 composite
    reasoning: str
    evidence: list[str] = field(default_factory=list)
    agent_scores: dict[str, float] = field(default_factory=dict)
    portfolio_context: str | None = None  # personalized note
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PortfolioContext:
    """User's portfolio context for personalization."""
    total_holdings: int = 0
    total_invested: float = 0
    sector_allocation: dict[str, float] = field(default_factory=dict)  # sector -> %
    top_holding_pct: float = 0  # largest position as %
    has_stock: bool = False  # already holds this stock?
    existing_quantity: float = 0


class DecisionEngine:
    """
    Weighs AI agent scores to produce a final recommendation.
    Not an LLM — pure computation + rules.
    """

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def recommend(
        self,
        ticker: str,
        agent_scores: dict[str, float],  # agent_name -> score (0-10)
        portfolio_ctx: PortfolioContext | None = None,
    ) -> Recommendation:
        """
        Produce a weighted recommendation from agent scores.

        Args:
            ticker: Stock ticker
            agent_scores: dict of agent_name -> score (0-10)
            portfolio_ctx: Optional portfolio context for personalization
        """
        # Calculate weighted composite score
        total_weight = 0
        weighted_sum = 0
        for agent, score in agent_scores.items():
            weight = self.weights.get(agent, 0.1)
            weighted_sum += score * weight
            total_weight += weight

        composite = weighted_sum / total_weight if total_weight > 0 else 5.0

        # Map composite score to action
        action = self._score_to_action(composite)
        confidence = self._calculate_confidence(agent_scores, composite)
        priority = self._calculate_priority(composite, confidence)

        # Build evidence
        evidence = []
        for agent, score in sorted(agent_scores.items(), key=lambda x: x[1], reverse=True):
            sentiment = "Strong" if score >= 7.5 else "Moderate" if score >= 5 else "Weak"
            evidence.append(f"{agent.replace('_', ' ').title()}: {sentiment} ({score:.1f}/10)")

        # Portfolio personalization (Story 5.2)
        portfolio_note = None
        if portfolio_ctx:
            portfolio_note = self._personalize(ticker, action, portfolio_ctx)

        # Build reasoning
        reasoning = self._build_reasoning(ticker, action, composite, agent_scores)

        return Recommendation(
            ticker=ticker,
            action=action,
            confidence=round(confidence, 1),
            priority=priority,
            weighted_score=round(composite, 2),
            reasoning=reasoning,
            evidence=evidence,
            agent_scores=agent_scores,
            portfolio_context=portfolio_note,
        )

    def _score_to_action(self, score: float) -> str:
        if score >= 8.5:
            return "STRONG_BUY"
        elif score >= 7.0:
            return "BUY"
        elif score >= 4.5:
            return "HOLD"
        elif score >= 3.0:
            return "SELL"
        else:
            return "STRONG_SELL"

    def _calculate_confidence(self, agent_scores: dict[str, float], composite: float) -> float:
        """Confidence is higher when agents agree, lower when they diverge."""
        if not agent_scores:
            return 50.0
        scores = list(agent_scores.values())
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        # Low variance = high confidence, high variance = low confidence
        agreement_factor = max(0, 100 - variance * 10)
        # Base confidence from composite strength
        strength_factor = abs(composite - 5) * 10  # farther from neutral = more confident
        return min(95, (agreement_factor * 0.6 + strength_factor * 0.4))

    def _calculate_priority(self, composite: float, confidence: float) -> str:
        if abs(composite - 5) > 2.5 and confidence > 70:
            return "HIGH"
        elif abs(composite - 5) > 1.5 or confidence > 60:
            return "MEDIUM"
        else:
            return "LOW"

    def _personalize(self, ticker: str, action: str, ctx: PortfolioContext) -> str:
        """Story 5.2: Portfolio Context Engine — personalized advice."""
        notes = []

        if ctx.has_stock:
            if action in ("BUY", "STRONG_BUY"):
                notes.append(f"You already hold {ticker} ({ctx.existing_quantity} shares). Consider if adding increases concentration.")
            elif action in ("SELL", "STRONG_SELL"):
                notes.append(f"You hold {ticker}. This recommendation suggests reducing position.")

        # Sector concentration check
        if ctx.sector_allocation:
            max_sector = max(ctx.sector_allocation.items(), key=lambda x: x[1], default=("", 0))
            if max_sector[1] > 30:
                notes.append(f"⚠️ Your portfolio is {max_sector[1]:.0f}% in {max_sector[0]}. Consider diversification.")

        if ctx.top_holding_pct > 25:
            notes.append(f"⚠️ Your largest position is {ctx.top_holding_pct:.0f}% of portfolio. High concentration risk.")

        return " | ".join(notes) if notes else None

    def _build_reasoning(self, ticker: str, action: str, composite: float, scores: dict) -> str:
        top_positive = [k for k, v in scores.items() if v >= 7]
        top_negative = [k for k, v in scores.items() if v < 4]

        parts = [f"Composite score: {composite:.1f}/10 → {action}."]
        if top_positive:
            parts.append(f"Strengths: {', '.join(a.replace('_', ' ') for a in top_positive)}.")
        if top_negative:
            parts.append(f"Concerns: {', '.join(a.replace('_', ' ') for a in top_negative)}.")
        return " ".join(parts)
