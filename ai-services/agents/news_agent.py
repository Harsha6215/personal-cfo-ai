"""
News Intelligence Agent — Story 4.3

Role: News Analyst — analyzes recent news sentiment and key developments.
Input: Company News headlines from RSS feeds.
Output: Overall sentiment, key developments, management outlook.
"""

from agents.base import AgentContext, AgentResponse, BaseAgent
from agents.llm import LLMProvider


class NewsIntelligenceAgent(BaseAgent):
    name = "news_analyst"
    role = "News Intelligence Analyst — Sentiment & Key Developments"
    required_data = ["news", "company_info"]

    @property
    def system_prompt(self) -> str:
        return """You are a News Intelligence Analyst at a financial research firm.
Your job is to analyze recent news headlines about a company and determine:
1. Overall news sentiment (positive/negative/neutral)
2. Key developments that could impact the stock
3. Any red flags or catalysts

STRICT RULES:
- Analyze ONLY the news provided — don't invent information
- Focus on material events: earnings, management changes, regulatory, M&A, new products
- Ignore generic market noise
- Score news impact from 0 to 10 (10 = highly impactful positive news)

RESPOND ONLY IN THIS JSON FORMAT:
{
    "score": 7.0,
    "sentiment": "positive",
    "confidence": 72,
    "analysis": "Recent news is mostly positive with focus on growth initiatives and strong quarterly performance.",
    "evidence": [
        "Company announced 15% revenue growth in latest quarter",
        "New factory commissioning expected to add 20% capacity",
        "Management guided for strong demand in H2"
    ],
    "metrics": {
        "positive_news": 4,
        "negative_news": 1,
        "neutral_news": 2,
        "key_theme": "growth expansion"
    }
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = [f"Analyze recent news for {context.ticker}.\n"]

        if context.company_info:
            parts.append(f"Company: {context.company_info.get('name', context.ticker)}")
            parts.append(f"Sector: {context.company_info.get('sector', 'Unknown')}")

        if context.news:
            parts.append("\n--- RECENT NEWS HEADLINES ---")
            for i, article in enumerate(context.news[:10], 1):
                parts.append(f"{i}. [{article.get('source', 'Unknown')}] {article.get('title', '')}")
                if article.get('published'):
                    parts.append(f"   Published: {article['published']}")
        else:
            parts.append("\nNo recent news available for this stock.")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "News analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=None,
        )
