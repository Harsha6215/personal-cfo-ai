"""
Valuation Agent — Story 4.5

Role: Valuation Specialist — computes intrinsic value using multiple models.
Approach: Calculation FIRST, then AI explains.

Computes: PE, PB, PEG, EV/EBITDA, Earnings Yield
Then AI interprets: undervalued/fairly valued/overvalued with reasoning.
"""

from ai_services.agents.base import AgentContext, AgentResponse, BaseAgent
from ai_services.agents.llm import LLMProvider


def _compute_valuation_metrics(quote: dict, company: dict) -> dict:
    """Compute valuation ratios from available data."""
    metrics = {}
    price = quote.get("price", 0)

    # P/E Ratio
    pe = company.get("pe_ratio") or quote.get("pe_ratio")
    if pe and pe > 0:
        metrics["pe_ratio"] = round(pe, 2)
        metrics["earnings_yield"] = round(100 / pe, 2)  # inverse of PE

    # EPS
    eps = company.get("eps") or quote.get("eps")
    if eps:
        metrics["eps"] = round(eps, 2)

    # Market Cap
    mcap = company.get("market_cap") or quote.get("market_cap")
    if mcap:
        metrics["market_cap_cr"] = round(mcap / 1e7, 0)

    # Price vs 52W range (valuation context)
    high_52w = company.get("high_52w") or quote.get("high_52w")
    low_52w = company.get("low_52w") or quote.get("low_52w")
    if high_52w and low_52w and price:
        range_52w = high_52w - low_52w
        if range_52w > 0:
            position = (price - low_52w) / range_52w * 100
            metrics["position_in_52w_range"] = round(position, 1)
            metrics["discount_from_52w_high"] = round((1 - price / high_52w) * 100, 1)

    # Beta
    beta = company.get("beta")
    if beta:
        metrics["beta"] = round(beta, 2)

    # Dividend Yield
    div_yield = company.get("dividend_yield")
    if div_yield and div_yield > 0:
        metrics["dividend_yield_pct"] = round(div_yield * 100, 2)

    return metrics


class ValuationAgent(BaseAgent):
    name = "valuation_specialist"
    role = "Valuation Specialist — Intrinsic Value & Fair Price Assessment"
    required_data = ["quote", "company_info", "financials"]

    @property
    def system_prompt(self) -> str:
        return """You are a Valuation Specialist at an equity research firm.
Your job is to assess whether a stock is undervalued, fairly valued, or overvalued.

APPROACH:
1. Look at the computed valuation metrics provided (PE, EPS, earnings yield, 52W position)
2. Compare to sector averages (use your knowledge of Indian market PE ranges)
3. Determine fair value assessment
4. Provide specific reasoning

INDIAN MARKET CONTEXT:
- Nifty 50 average PE: ~22x
- IT sector: 25-30x PE is normal
- Banking: 15-20x PE is normal
- Manufacturing: 20-35x PE depending on growth
- Small/mid cap premium: 10-20% above large cap

RESPOND ONLY IN THIS JSON FORMAT:
{
    "score": 6.0,
    "sentiment": "neutral",
    "confidence": 70,
    "analysis": "Stock is trading at 25x PE which is in line with sector averages. At 15% discount from 52W high, offering moderate value.",
    "evidence": [
        "PE of 25x vs sector average of 28x — slight discount",
        "Trading 15% below 52-week high",
        "Earnings yield of 4% — moderate",
        "Dividend yield of 1.2% provides some downside support"
    ],
    "metrics": {
        "valuation_verdict": "fairly_valued",
        "pe_vs_sector": "slight_discount",
        "upside_potential_pct": 8,
        "intrinsic_pe_estimate": 28
    }
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = [f"Valuation assessment for {context.ticker}.\n"]

        if context.company_info:
            parts.append(f"Company: {context.company_info.get('name', context.ticker)}")
            parts.append(f"Sector: {context.company_info.get('sector', 'Unknown')}")
            parts.append(f"Industry: {context.company_info.get('industry', 'Unknown')}")

        # Compute valuation metrics
        quote = context.quote or {}
        company = context.company_info or {}
        metrics = _compute_valuation_metrics(quote, company)

        if metrics:
            parts.append("\n--- COMPUTED VALUATION METRICS ---")
            if "pe_ratio" in metrics:
                parts.append(f"P/E Ratio: {metrics['pe_ratio']}x")
            if "earnings_yield" in metrics:
                parts.append(f"Earnings Yield: {metrics['earnings_yield']}%")
            if "eps" in metrics:
                parts.append(f"EPS: ₹{metrics['eps']}")
            if "market_cap_cr" in metrics:
                parts.append(f"Market Cap: ₹{metrics['market_cap_cr']:,.0f} Cr")
            if "position_in_52w_range" in metrics:
                parts.append(f"Position in 52W Range: {metrics['position_in_52w_range']}% (0=low, 100=high)")
            if "discount_from_52w_high" in metrics:
                parts.append(f"Discount from 52W High: {metrics['discount_from_52w_high']}%")
            if "beta" in metrics:
                parts.append(f"Beta: {metrics['beta']}")
            if "dividend_yield_pct" in metrics:
                parts.append(f"Dividend Yield: {metrics['dividend_yield_pct']}%")

        if context.quote:
            parts.append(f"\nCurrent Price: ₹{context.quote.get('price', 0):.2f}")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "Valuation analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=None,
        )
