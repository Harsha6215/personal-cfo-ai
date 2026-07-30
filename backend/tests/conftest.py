"""
pytest configuration and shared fixtures.

All tests import fixtures from here automatically (pytest discovers conftest.py).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client wired to the FastAPI app — no real server needed."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
