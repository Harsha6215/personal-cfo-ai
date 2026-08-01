"""
BaseAgent — abstract base class for all AI specialist agents.

Every agent in the Investment Committee inherits from this.
Agents are specialized: each one has a specific role, sees only specific data,
and produces structured output with confidence and evidence.

Architecture:
    Agent receives context → uses tools to gather data → sends prompt to LLM → returns structured response
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AgentResponse:
    """
    Structured output from any agent.
    Every response includes confidence and evidence for explainability.
    """
    agent_name: str
    agent_role: str
    ticker: str
    analysis: str                       # Main analysis text
    score: float | None = None          # 0-10 score (optional)
    sentiment: str | None = None        # positive/negative/neutral
    confidence: float = 0.0             # 0-100%
    evidence: list[str] = field(default_factory=list)  # Evidence points
    metrics: dict[str, Any] = field(default_factory=dict)  # Key metrics
    recommendation: str | None = None   # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: int = 0
    error: str | None = None


@dataclass
class AgentContext:
    """
    Input context for an agent — what data it receives.
    Each agent type gets different data (separation of concerns).
    """
    ticker: str
    user_id: str | None = None
    portfolio_id: str | None = None
    # Data slots (populated by orchestrator based on agent needs)
    financials: dict | None = None
    price_history: list | None = None
    quote: dict | None = None
    company_info: dict | None = None
    news: list | None = None
    economy: dict | None = None
    holdings: list | None = None
    # Agent-specific extras
    extra: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base for all specialist AI agents.

    Subclass and implement:
        - name: agent identifier
        - role: human-readable role description
        - required_data: what data this agent needs
        - system_prompt: the system prompt for the LLM
        - execute(context) -> AgentResponse
    """

    name: str                    # e.g. "financial_analyst"
    role: str                    # e.g. "Equity Research Analyst specializing in financial analysis"
    required_data: list[str]     # e.g. ["financials", "quote"] — what data to fetch

    @abstractmethod
    async def execute(self, context: AgentContext, llm) -> AgentResponse:
        """
        Run the agent's analysis.

        Args:
            context: AgentContext with relevant data populated
            llm: LLM provider instance for generating analysis

        Returns:
            AgentResponse with structured output
        """
        ...

    def build_prompt(self, context: AgentContext) -> str:
        """
        Build the user prompt from context data.
        Override in subclasses for custom prompt construction.
        """
        return f"Analyze {context.ticker}"

    @property
    def system_prompt(self) -> str:
        """The system prompt that defines this agent's personality and constraints."""
        return f"You are a {self.role}. Provide focused, evidence-based analysis."
