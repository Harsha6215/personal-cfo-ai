"""
Financial Analyst Agent — Story 4.2

Role: Equity Research Analyst specializing in financial statement analysis.
Input: Balance Sheet, Income Statement, Cash Flow, Quarterly Results, Growth metrics.
Output: Financial Health score, trend indicators, evidence.

Does NOT give buy/sell recommendations — only financial analysis.
"""

from ai_services.agents.base import AgentContext, AgentResponse, BaseAgent
from ai_services.agents.llm import LLMProvider


class FinancialAnalystAgent(BaseAgent):
    name = "financial_analyst"
    role = "Equity Research Analyst — Financial Statement Analysis"
    required_data = ["financials", "quote", "company_info"]

    @property
    def system_prompt(self) -> str:
        return """You are a senior Equity Research Analyst at a top Indian investment bank (like Kotak, ICICI Securities).
Your ONLY job is to analyze financial statements and provide a health assessment.

STRICT RULES:
- Focus ONLY on: Revenue, Net Profit, Operating Margins, Debt/Equity, Cash Flow, ROE, ROCE, EPS growth
- Do NOT give buy/sell/hold recommendations — only financial health analysis
- Score financial health from 0.0 to 10.0
- Provide 3-5 specific evidence points backed by numbers
- Be concise, data-driven, and quantitative
- Context: Indian stock market (NSE/BSE), values in ₹ Crores

RESPOND ONLY IN THIS JSON FORMAT:
{
    "score": 7.5,
    "sentiment": "positive",
    "confidence": 78,
    "analysis": "Concise 2-3 sentence financial health summary with specific numbers.",
    "evidence": [
        "Revenue grew 12% YoY to ₹4,521 Cr",
        "Operating margin expanded from 18% to 21%",
        "Debt-to-equity ratio reduced to 0.3x",
        "Free cash flow positive for 8 consecutive quarters"
    ],
    "metrics": {
        "revenue_trend": "growing",
        "profit_margin": "expanding",
        "debt_level": "low",
        "cash_flow": "strong",
        "roe": "18.5%"
    }
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = [f"Analyze the financial health of {context.ticker}.\n"]

        if context.company_info:
            parts.append(f"Company: {context.company_info.get('name', context.ticker)}")
            parts.append(f"Sector: {context.company_info.get('sector', 'Unknown')}")
            parts.append(f"Industry: {context.company_info.get('industry', 'Unknown')}")
            if context.company_info.get('pe_ratio'):
                parts.append(f"P/E Ratio: {context.company_info['pe_ratio']:.1f}")
            if context.company_info.get('eps'):
                parts.append(f"EPS: ₹{context.company_info['eps']:.2f}")
            if context.company_info.get('market_cap'):
                parts.append(f"Market Cap: ₹{context.company_info['market_cap']/1e7:.0f} Cr")

        if context.quote:
            parts.append(f"\nCurrent Price: ₹{context.quote.get('price', 0):.2f}")
            if context.quote.get('high_52w'):
                parts.append(f"52W Range: ₹{context.quote.get('low_52w', 0):.0f} - ₹{context.quote.get('high_52w', 0):.0f}")

        if context.financials and context.financials.get("income_quarterly"):
            parts.append("\n--- QUARTERLY INCOME STATEMENT (Last 4 Quarters) ---")
            quarters = context.financials["income_quarterly"][:4]
            for q in quarters:
                parts.append(f"\nQuarter ending {q['period_date']}:")
                data = q.get("data", {})
                for key in list(data.keys())[:8]:
                    val = data[key]
                    if isinstance(val, (int, float)):
                        parts.append(f"  {key}: ₹{val/1e7:.1f} Cr" if abs(val) > 1e6 else f"  {key}: {val}")
                    else:
                        parts.append(f"  {key}: {val}")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "Financial analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=None,  # Financial analyst never recommends
        )
