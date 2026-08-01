"""
Macro Economist Agent — Story 4.6

Role: Analyzes macroeconomic conditions and their impact on specific stocks/sectors.
Input: GDP, Inflation, Interest Rates, USD, Oil, Gold indicators.
Output: Macro outlook + sector-level impact assessment.
"""

from agents.base import AgentContext, AgentResponse, BaseAgent
from agents.llm import LLMProvider


class MacroEconomistAgent(BaseAgent):
    name = "macro_economist"
    role = "Macro Economist — Economic Conditions & Sector Impact"
    required_data = ["economy", "company_info"]

    @property
    def system_prompt(self) -> str:
        return """You are a Macro Economist at a leading Indian investment firm.
Your job is to assess current macroeconomic conditions and their impact on a specific stock/sector.

FOCUS ON:
- Interest rate environment (RBI repo rate) and its impact
- Currency movements (USDINR) and export/import implications
- Commodity prices (Oil, Gold) and sector-level effects
- Inflation trends and margin pressure
- Global factors (US yields, Fed policy) that affect Indian markets

INDIAN MARKET CONTEXT:
- IT sector benefits from weak INR
- Banking benefits from rate cuts, hurts from rate hikes
- FMCG/Auto hurt by high inflation
- Metal/Mining linked to commodity cycles
- Pharma relatively defensive

RESPOND ONLY IN THIS JSON FORMAT:
{
    "score": 6.5,
    "sentiment": "neutral",
    "confidence": 65,
    "analysis": "Macro environment is neutral to slightly positive for this sector. Stable rates and falling crude support margins.",
    "evidence": [
        "RBI maintaining status quo on rates — positive for growth",
        "USDINR stable around 84 — neutral for this sector",
        "Crude oil falling — reduces input costs",
        "Inflation moderating — supports consumption"
    ],
    "metrics": {
        "macro_outlook": "neutral_to_positive",
        "rate_impact": "neutral",
        "currency_impact": "neutral",
        "commodity_impact": "positive",
        "sector_sensitivity": "moderate"
    }
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = [f"Macro assessment for {context.ticker}.\n"]

        if context.company_info:
            parts.append(f"Company: {context.company_info.get('name', context.ticker)}")
            parts.append(f"Sector: {context.company_info.get('sector', 'Unknown')}")
            parts.append(f"Industry: {context.company_info.get('industry', 'Unknown')}")

        if context.economy:
            parts.append("\n--- CURRENT ECONOMIC INDICATORS ---")
            for key, val in context.economy.items():
                parts.append(f"{key}: {val}")
        else:
            parts.append("\nNote: Use your knowledge of current Indian macro conditions (Aug 2026).")
            parts.append("RBI repo rate ~6.5%, USDINR ~84, Inflation ~4.5%, Crude ~$70-75")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "Macro analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=None,
        )
