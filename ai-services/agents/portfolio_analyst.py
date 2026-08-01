"""
Portfolio Analyst Agent — Story 4.11

Role: Analyzes YOUR entire portfolio holistically (not individual stocks).
Output: Strengths, Weaknesses, Concentration, Diversification, Overall risk.
"""

from agents.base import AgentContext, AgentResponse, BaseAgent
from agents.llm import LLMProvider


class PortfolioAnalystAgent(BaseAgent):
    name = "portfolio_analyst"
    role = "Portfolio Analyst — Holistic Portfolio Assessment"
    required_data = ["holdings"]

    @property
    def system_prompt(self) -> str:
        return """You are a Portfolio Analyst advising a retail investor in India.
Analyze the ENTIRE portfolio holistically — not individual stocks.

ASSESS:
1. Diversification: How well spread across sectors, market caps?
2. Concentration Risk: Any single stock > 20% of portfolio?
3. Sector Allocation: Balance between cyclical/defensive/growth?
4. Asset Mix: Stocks vs ETFs vs Gold vs Debt?
5. Strengths: What's working well?
6. Weaknesses: What needs improvement?

RESPOND IN JSON:
{
    "score": 6.5,
    "sentiment": "neutral",
    "confidence": 75,
    "analysis": "Portfolio is moderately diversified with 10 holdings across 5 sectors. Over-concentration in mid-caps and absence of large-cap stability is a concern.",
    "evidence": [
        "10 holdings across 5 sectors — moderate diversification",
        "No allocation to large-cap IT or Banking majors",
        "Gold/Silver ETFs provide 25% defensive allocation — good",
        "High exposure to mid/small caps increases volatility"
    ],
    "metrics": {
        "diversification_score": 6,
        "concentration_risk": "moderate",
        "top_sector": "Manufacturing",
        "defensive_allocation": "25%",
        "suggestion": "Add large-cap stability via Nifty 50 ETF"
    }
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = ["Analyze this investor's complete portfolio:\n"]

        if context.holdings:
            total_value = sum(h.get("invested_value", 0) for h in context.holdings)
            parts.append(f"Total Holdings: {len(context.holdings)}")
            parts.append(f"Total Invested: ₹{total_value:,.0f}\n")
            parts.append("--- HOLDINGS ---")
            for h in context.holdings:
                pct = (h.get("invested_value", 0) / total_value * 100) if total_value > 0 else 0
                parts.append(f"  {h.get('ticker', '?'):12} | {h.get('asset_type', '?'):6} | Qty: {h.get('quantity', 0)} | Invested: ₹{h.get('invested_value', 0):,.0f} ({pct:.1f}%)")
        else:
            parts.append("No holdings data available.")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker="PORTFOLIO",
            analysis=result.get("analysis", "Portfolio analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
        )
