"""
Agent Orchestrator — routes requests to specialist agents.

This is the conductor of the AI Investment Committee.
It decides which agents to run, gathers their data, and combines results.

Usage:
    orchestrator = AgentOrchestrator(llm=OpenAIProvider())
    orchestrator.register(FinancialAnalystAgent())
    orchestrator.register(NewsIntelligenceAgent())

    # Run single agent
    response = await orchestrator.run_agent("financial_analyst", context)

    # Run all agents (Investment Committee)
    responses = await orchestrator.run_all(context)
"""

import time
from datetime import datetime, timezone

import structlog

from agents.base import AgentContext, AgentResponse, BaseAgent
from agents.llm import LLMProvider

logger = structlog.get_logger(__name__)


class AgentOrchestrator:
    """
    Coordinates the AI Investment Committee.

    Manages agent registration, data routing, and execution.
    Each agent only receives the data it needs (separation of concerns).
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register a specialist agent."""
        self._agents[agent.name] = agent
        logger.info("orchestrator.registered", agent=agent.name, role=agent.role)

    def list_agents(self) -> list[dict]:
        """List all registered agents."""
        return [
            {"name": a.name, "role": a.role, "required_data": a.required_data}
            for a in self._agents.values()
        ]

    async def run_agent(self, agent_name: str, context: AgentContext) -> AgentResponse:
        """Run a single specialist agent."""
        agent = self._agents.get(agent_name)
        if not agent:
            return AgentResponse(
                agent_name=agent_name,
                agent_role="unknown",
                ticker=context.ticker,
                analysis=f"Agent '{agent_name}' not found.",
                error=f"No agent registered with name '{agent_name}'",
            )

        start = time.perf_counter()
        try:
            response = await agent.execute(context, self.llm)
            response.execution_time_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "orchestrator.agent.completed",
                agent=agent_name,
                ticker=context.ticker,
                confidence=response.confidence,
                time_ms=response.execution_time_ms,
            )
            return response
        except Exception as e:
            logger.error("orchestrator.agent.failed", agent=agent_name, error=str(e))
            return AgentResponse(
                agent_name=agent_name,
                agent_role=agent.role,
                ticker=context.ticker,
                analysis=f"Agent failed: {str(e)}",
                error=str(e),
                execution_time_ms=int((time.perf_counter() - start) * 1000),
            )

    async def run_all(self, context: AgentContext) -> list[AgentResponse]:
        """
        Run ALL registered agents (the full Investment Committee).
        Returns responses from each specialist.
        """
        responses: list[AgentResponse] = []
        for name in self._agents:
            response = await self.run_agent(name, context)
            responses.append(response)
        return responses

    async def run_selected(self, agent_names: list[str], context: AgentContext) -> list[AgentResponse]:
        """Run only selected agents."""
        responses: list[AgentResponse] = []
        for name in agent_names:
            response = await self.run_agent(name, context)
            responses.append(response)
        return responses
