"""
AI Agent Framework — Story 4.1

The foundation for all AI agents in the Investment Committee.
Every agent uses this same framework: BaseAgent → Tools → Prompt → LLM → Output.
"""

from ai_services.agents.base import BaseAgent, AgentResponse, AgentContext
from ai_services.agents.orchestrator import AgentOrchestrator
from ai_services.agents.llm import LLMProvider, OpenAIProvider

__all__ = [
    "BaseAgent",
    "AgentResponse",
    "AgentContext",
    "AgentOrchestrator",
    "LLMProvider",
    "OpenAIProvider",
]
