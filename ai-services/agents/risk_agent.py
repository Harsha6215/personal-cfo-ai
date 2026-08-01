"""
Risk Manager Agent — Story 4.7

Role: Assesses risk from multiple dimensions.
Checks: Debt, Governance, Concentration, Volatility, Sector Exposure, Currency.
Output: Risk Score, Main Risk, Mitigation suggestions.
"""

from agents.base import AgentContext, AgentResponse, BaseAgent
from agents.llm import LLMProvider


class RiskManagerAgent(BaseAgent):
    name = "risk_manager"
    role = "Risk Manager — Multi-Dimensional Risk Assessment"
    required_data = ["quote", "company_info", "financials"]

    @property
    def system_prompt(self) -> str:
        return """You are a Risk Manager at an institutional investment firm.
Your ONLY job is to identify and quantify risks. You are conservative by nature.

RISK DIMENSIONS TO ASSESS:
1. Financial Risk: Debt levels, cash burn, liquidity
2. Valuation Risk: Overvaluation, bubble indicators
3. Market Risk: Volatility (beta), drawdown potential
4. Sector Risk: Cyclicality, regulatory threats
5. Concentration Risk: Single-product dependency, geography
6. Governance Risk: Promoter pledging, related-party transactions

SCORING:
- Risk Score 0-10 (0 = extremely risky, 10 = very safe)
- Identify the TOP risk factor
- Provide mitigation suggestion

RESPOND ONLY IN THIS JSON FORMAT:
{
    "score": 7.0,
    "sentiment": "neutral",
    "confidence": 70,
    "analysis": "Moderate risk profile. Main concern is high sector concentration in cyclical auto segment. Financials are healthy with low debt.",
    "evidence": [
        "Beta of 1.2 — slightly higher volatility than market",
        "Debt-to-equity appears manageable",
        "Cyclical sector — vulnerable to economic slowdowns",
        "52W drawdown was 25% — moderate downside risk"
    ],
    "metrics": {
        "overall_risk": "moderate",
        "financial_risk": "low",
        "market_risk": "moderate",
        "sector_risk": "moderate",
        "top_risk_factor": "cyclical sector exposure",
        "mitigation": "Diversify with defensive sectors"
    }
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = [f"Risk assessment for {context.ticker}.\n"]

        if context.company_info:
            parts.append(f"Company: {context.company_info.get('name', context.ticker)}")
            parts.append(f"Sector: {context.company_info.get('sector', 'Unknown')}")
            parts.append(f"Industry: {context.company_info.get('industry', 'Unknown')}")
            if context.company_info.get('beta'):
                parts.append(f"Beta: {context.company_info['beta']}")
            if context.company_info.get('market_cap'):
                parts.append(f"Market Cap: ₹{context.company_info['market_cap']/1e7:.0f} Cr")

        if context.quote:
            parts.append(f"\nCurrent Price: ₹{context.quote.get('price', 0):.2f}")
            high = context.quote.get('high_52w', 0)
            low = context.quote.get('low_52w', 0)
            price = context.quote.get('price', 0)
            if high and low and price:
                drawdown = ((high - price) / high * 100)
                parts.append(f"52W High: ₹{high:.0f} (down {drawdown:.0f}% from high)")
                parts.append(f"52W Low: ₹{low:.0f}")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "Risk analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=None,
        )
