"""
LLM Provider Abstraction — Story 4.1

Supports multiple LLM backends. Default: OpenAI GPT-4o.
To switch providers, just instantiate a different class.

Usage:
    llm = OpenAIProvider()  # reads OPENAI_API_KEY from env
    response = await llm.generate(system_prompt, user_prompt)
"""

import os
from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger(__name__)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    provider_name: str
    model: str

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Generate a response from the LLM."""
        ...

    @abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict:
        """Generate a JSON response from the LLM."""
        ...


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4o provider."""

    provider_name = "openai"
    model = "gpt-4o"

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        self.model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self._api_key:
            logger.warning("openai.no_api_key", msg="OPENAI_API_KEY not set. AI features will not work.")

    def _get_client(self):
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=self._api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Generate text response."""
        if not self._api_key:
            return "[AI unavailable — OPENAI_API_KEY not configured]"

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.choices[0].message.content or ""
            logger.info("llm.generated", model=self.model, tokens=response.usage.total_tokens if response.usage else 0)
            return result
        except Exception as e:
            logger.error("llm.error", model=self.model, error=str(e))
            return f"[AI error: {str(e)}]"

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> dict:
        """Generate JSON response using structured output."""
        import json

        if not self._api_key:
            return {"error": "OPENAI_API_KEY not configured"}

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt + "\n\nRespond ONLY with valid JSON."},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            logger.error("llm.json_error", model=self.model, error=str(e))
            return {"error": str(e)}


class MockLLMProvider(LLMProvider):
    """
    Mock provider for testing without an API key.
    Returns realistic-looking placeholder responses.
    """

    provider_name = "mock"
    model = "mock-v1"

    async def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return (
            "Based on the available data, this stock shows moderate fundamentals "
            "with stable revenue growth. The company maintains healthy cash flows "
            "and manageable debt levels. Current market conditions are neutral to "
            "slightly positive for this sector."
        )

    async def generate_json(self, system_prompt: str, user_prompt: str, **kwargs) -> dict:
        return {
            "score": 7.5,
            "sentiment": "neutral",
            "confidence": 72,
            "analysis": "Moderate fundamentals with stable growth trajectory.",
            "evidence": [
                "Revenue showing consistent growth",
                "Debt-to-equity within acceptable range",
                "Market conditions neutral",
            ],
            "recommendation": "HOLD",
        }
