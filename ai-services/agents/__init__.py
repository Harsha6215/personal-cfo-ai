"""
AI Agent Framework — Story 4.1

The foundation for all AI agents in the Investment Committee.
Every agent uses this same framework: BaseAgent → Tools → Prompt → LLM → Output.
"""

from agents.base import BaseAgent, AgentResponse, AgentContext
from agents.orchestrator import AgentOrchestrator
from agents.llm import LLMProvider, OpenAIProvider

__all__ = [
    "BaseAgent",
    "AgentResponse",
    "AgentContext",
    "AgentOrchestrator",
    "LLMProvider",
    "OpenAIProvider",
]
