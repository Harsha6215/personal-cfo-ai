"""
Financial Analyst Agent — Story 4.2 (starter implementation shipped with framework).

Analyzes financial health: Revenue, Profit, Debt, Cash Flow, ROE.
Does NOT give buy/sell recommendations — only financial analysis.
"""

import json

from ai_services.agents.base import AgentContext, AgentResponse, BaseAgent
from ai_services.agents.llm import LLMProvider


class FinancialAnalystAgent(BaseAgent):
    name = "financial_analyst"
    role = "Equity Research Analyst specializing in financial statement analysis"
    required_data = ["financials", "quote", "company_info"]

    @property
    def system_prompt(self) -> str:
        return """You are a senior Equity Research Analyst at a top investment bank.
Your job is to analyze financial statements and provide a health assessment.

Rules:
- Focus ONLY on financial metrics: Revenue, Profit, Margins, Debt, Cash Flow, ROE, ROCE
- Do NOT give buy/sell recommendations
- Score financial health from 0 to 10
- Provide 3-5 key evidence points
- Be concise and data-driven
- Context: Indian stock market (NSE/BSE)

Respond in JSON format:
{
    "score": 7.5,
    "sentiment": "positive",
    "confidence": 78,
    "analysis": "2-3 sentence summary",
    "evidence": ["point 1", "point 2", "point 3"],
    "metrics": {"revenue_trend": "growing", "debt_level": "moderate", "roe": "15.2%"}
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = [f"Analyze the financial health of {context.ticker}."]

        if context.company_info:
            parts.append(f"\nCompany: {context.company_info.get('name', context.ticker)}")
            parts.append(f"Sector: {context.company_info.get('sector', 'Unknown')}")
            if context.company_info.get('pe_ratio'):
                parts.append(f"P/E: {context.company_info['pe_ratio']}")
            if context.company_info.get('eps'):
                parts.append(f"EPS: {context.company_info['eps']}")

        if context.quote:
            parts.append(f"\nCurrent Price: ₹{context.quote.get('price', 0)}")
            parts.append(f"Market Cap: ₹{context.quote.get('market_cap', 0):,.0f}")

        if context.financials and context.financials.get("income_quarterly"):
            # Include last 2 quarters of income data
            quarters = context.financials["income_quarterly"][:2]
            for q in quarters:
                parts.append(f"\nQuarter {q['period_date']}:")
                data = q.get("data", {})
                for key in list(data.keys())[:5]:
                    parts.append(f"  {key}: {data[key]}")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "Analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=None,  # Financial analyst doesn't recommend
        )
