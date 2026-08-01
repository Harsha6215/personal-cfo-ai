"""
Chief Investment Officer Agent — Story 4.12

The FINAL agent. Reads outputs from ALL specialists, weighs evidence,
resolves disagreements, assigns confidence, produces transparent recommendation.

KEY PRINCIPLE: The CIO doesn't fetch data. It only reasons over specialist reports.
"""

from agents.base import AgentContext, AgentResponse, BaseAgent
from agents.llm import LLMProvider


class CIOAgent(BaseAgent):
    name = "chief_investment_officer"
    role = "Chief Investment Officer — Final Investment Decision"
    required_data = []  # CIO gets specialist reports, not raw data

    @property
    def system_prompt(self) -> str:
        return """You are the Chief Investment Officer (CIO) of an investment firm.
You have received analysis reports from your specialist team:
- Financial Analyst (financial health)
- News Analyst (sentiment & developments)
- Technical Analyst (price patterns & momentum)
- Valuation Specialist (fair value assessment)
- Macro Economist (economic conditions)
- Risk Manager (multi-dimensional risk)

YOUR JOB:
1. Weigh all specialist opinions
2. Resolve any disagreements between analysts
3. Produce a FINAL recommendation with confidence
4. Be transparent about which factors drive your decision

RECOMMENDATIONS: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL

RESPOND IN JSON:
{
    "score": 7.2,
    "sentiment": "positive",
    "confidence": 78,
    "recommendation": "BUY",
    "analysis": "After weighing all specialist inputs, the stock presents a favorable risk-reward. Strong financials and positive news outweigh the moderate technical weakness.",
    "evidence": [
        "Financial health: 8/10 — strong fundamentals",
        "News sentiment: Positive — growth catalysts ahead",
        "Technical: Neutral — consolidating near support",
        "Valuation: Slightly undervalued vs sector peers",
        "Macro: Supportive environment for this sector",
        "Risk: Moderate — cyclical exposure is main concern"
    ],
    "metrics": {
        "overall_verdict": "favorable",
        "financials_weight": "strong positive",
        "technicals_weight": "neutral",
        "news_weight": "positive",
        "valuation_weight": "slight positive",
        "macro_weight": "neutral",
        "risk_weight": "moderate concern",
        "key_driver": "Strong fundamentals + positive news catalysts"
    }
}"""

    def build_prompt_from_reports(self, ticker: str, specialist_reports: list[AgentResponse]) -> str:
        parts = [f"INVESTMENT DECISION for {ticker}\n"]
        parts.append("Below are the specialist reports from your team:\n")

        for report in specialist_reports:
            parts.append(f"--- {report.agent_role} ---")
            parts.append(f"Score: {report.score}/10 | Sentiment: {report.sentiment} | Confidence: {report.confidence}%")
            parts.append(f"Analysis: {report.analysis}")
            if report.evidence:
                parts.append(f"Evidence: {', '.join(report.evidence[:3])}")
            parts.append("")

        parts.append("Based on ALL the above specialist inputs, provide your final investment recommendation.")
        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        # CIO uses specialist reports from context.extra
        specialist_reports = context.extra.get("specialist_reports", [])
        prompt = self.build_prompt_from_reports(context.ticker, specialist_reports)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "CIO recommendation unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=result.get("recommendation", "HOLD"),
        )
