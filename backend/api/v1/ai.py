"""
AI API — triggers agent analysis via the Investment Committee.

POST /api/v1/ai/analyze/:ticker — run all specialist agents
GET  /api/v1/ai/agents — list registered agents
"""

import sys
import os
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.user import User

# Add ai-services to path (folder has hyphen — can't import directly as package)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_AI_SERVICES_PATH = os.path.join(_PROJECT_ROOT, "ai-services")
if _AI_SERVICES_PATH not in sys.path:
    sys.path.insert(0, _AI_SERVICES_PATH)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["AI Intelligence"])


# ── Response schemas ───────────────────────────────────────────────────────────

class AgentAnalysis(BaseModel):
    agent_name: str
    agent_role: str
    analysis: str
    score: float | None = None
    sentiment: str | None = None
    confidence: float = 0
    evidence: list[str] = []
    metrics: dict = {}
    recommendation: str | None = None
    execution_time_ms: int = 0
    error: str | None = None


class AnalysisResponse(BaseModel):
    ticker: str
    total_time_ms: int
    agents_run: int
    analyses: list[AgentAnalysis]


class AgentInfo(BaseModel):
    name: str
    role: str
    required_data: list[str]


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get(
    "/agents",
    response_model=list[AgentInfo],
    summary="List registered AI agents",
)
async def list_agents(user: User = Depends(get_current_user)):
    from agents.orchestrator import AgentOrchestrator
    from agents.llm import MockLLMProvider

    orchestrator = _get_orchestrator()
    return orchestrator.list_agents()


@router.post(
    "/analyze/{ticker}",
    response_model=AnalysisResponse,
    summary="Run AI Investment Committee analysis",
    description="Runs all specialist AI agents on a ticker and returns their combined analysis.",
)
async def analyze_ticker(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start = time.perf_counter()

    # Build context with market data
    from agents.base import AgentContext

    context = AgentContext(ticker=ticker.upper(), user_id=user.id)

    # Fetch data for agents
    from backend.services.market_data import MarketDataService, YahooFinanceProvider
    from backend.services.market_data.financials import fetch_financials
    from backend.services.market_data.news import fetch_news

    market = MarketDataService(provider=YahooFinanceProvider())

    # Gather data (agents will use what they need)
    quote = await market.get_quote(ticker.upper())
    if quote:
        context.quote = {"price": quote.price, "change": quote.change, "change_pct": quote.change_pct,
                         "volume": quote.volume, "pe_ratio": quote.pe_ratio, "eps": quote.eps,
                         "market_cap": quote.market_cap, "high_52w": quote.high_52w, "low_52w": quote.low_52w}

    company = await market.get_company_info(ticker.upper())
    if company:
        context.company_info = {"name": company.name, "sector": company.sector, "industry": company.industry,
                                "description": company.description, "market_cap": company.market_cap,
                                "pe_ratio": company.pe_ratio, "eps": company.eps, "beta": company.beta}

    financials = await fetch_financials(ticker.upper(), "income", "quarterly")
    if financials:
        context.financials = {"income_quarterly": financials}

    news_articles = await fetch_news(ticker.upper(), limit=5)
    if news_articles:
        context.news = [{"title": a.title, "source": a.source, "published": a.published} for a in news_articles]

    # Price history for technical analysis
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=200)
    bars = await market.get_history(ticker.upper(), start_date, end_date)
    if bars:
        context.price_history = [{"close": b.close, "high": b.high, "low": b.low, "volume": b.volume} for b in bars]

    # Run agents
    orchestrator = _get_orchestrator()
    responses = await orchestrator.run_all(context)

    total_time = int((time.perf_counter() - start) * 1000)

    return AnalysisResponse(
        ticker=ticker.upper(),
        total_time_ms=total_time,
        agents_run=len(responses),
        analyses=[
            AgentAnalysis(
                agent_name=r.agent_name,
                agent_role=r.agent_role,
                analysis=r.analysis,
                score=r.score,
                sentiment=r.sentiment,
                confidence=r.confidence,
                evidence=r.evidence,
                metrics=r.metrics,
                recommendation=r.recommendation,
                execution_time_ms=r.execution_time_ms,
                error=r.error,
            )
            for r in responses
        ],
    )


# ── Orchestrator setup ─────────────────────────────────────────────────────────

_orchestrator = None

def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from agents.orchestrator import AgentOrchestrator
        from agents.llm import OpenAIProvider, MockLLMProvider

        # Use OpenAI if key available, otherwise mock
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            llm = OpenAIProvider(api_key=api_key)
        else:
            logger.warning("ai.using_mock", msg="No OPENAI_API_KEY — using MockLLMProvider")
            llm = MockLLMProvider()

        _orchestrator = AgentOrchestrator(llm=llm)

        # Register the first agent (Financial Analyst — Story 4.2 will add more)
        from agents.financial_analyst import FinancialAnalystAgent
        _orchestrator.register(FinancialAnalystAgent())

        # Story 4.3: News Intelligence Agent
        from agents.news_agent import NewsIntelligenceAgent
        _orchestrator.register(NewsIntelligenceAgent())

        # Story 4.4: Technical Analysis Agent
        from agents.technical_analyst import TechnicalAnalystAgent
        _orchestrator.register(TechnicalAnalystAgent())

        # Story 4.5: Valuation Agent
        from agents.valuation_agent import ValuationAgent
        _orchestrator.register(ValuationAgent())

        # Story 4.6: Macro Economist Agent
        from agents.macro_agent import MacroEconomistAgent
        _orchestrator.register(MacroEconomistAgent())

        # Story 4.7: Risk Manager Agent
        from agents.risk_agent import RiskManagerAgent
        _orchestrator.register(RiskManagerAgent())

    return _orchestrator
