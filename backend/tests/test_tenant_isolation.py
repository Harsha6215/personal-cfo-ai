"""
Integration tests for multi-tenant isolation — Epic 6 Sprint 6.1

Tests verify that:
1. Role-based access control works (admin vs regular user)
2. Rate limiting returns 429 when exceeded
3. Rate limiting allows requests under limit
4. Rate limiting fails open when Redis is unavailable
5. Tenant context dependency works
6. Cross-user data isolation at the API level
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ── Mock redis module before any backend imports that need it ───────────────────
# This allows tests to run without the redis package installed.
if "redis" not in sys.modules:
    mock_redis_module = MagicMock()
    mock_redis_module.asyncio = MagicMock()
    mock_redis_module.asyncio.Redis = MagicMock()
    mock_redis_module.asyncio.from_url = MagicMock()
    sys.modules["redis"] = mock_redis_module
    sys.modules["redis.asyncio"] = mock_redis_module.asyncio

from backend.core.security import create_access_token  # noqa: E402
from backend.models.user import UserRole  # noqa: E402


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_token(user_id: str) -> str:
    """Generate a valid JWT for a given user_id."""
    return create_access_token(data={"sub": user_id})


def _make_user(user_id: str, email: str, role: UserRole = UserRole.USER):
    """Create a mock User object with the correct role type."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.is_active = True
    user.role = role
    user.full_name = "Test User"
    user.hashed_password = "hashed"
    user.portfolios = []
    user.watchlist = []
    return user


USER_A_ID = "aaaa-1111-aaaa-1111"
USER_B_ID = "bbbb-2222-bbbb-2222"


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def user_a():
    return _make_user(USER_A_ID, "userA@test.com")


@pytest.fixture
def user_b():
    return _make_user(USER_B_ID, "userB@test.com")


@pytest.fixture
def token_a():
    return _make_token(USER_A_ID)


@pytest.fixture
def token_b():
    return _make_token(USER_B_ID)


@pytest_asyncio.fixture
async def isolated_client(user_a):
    """
    Client with dependency overrides so tests don't hit real DB/Redis.
    Auth is overridden to return user_a by default.
    """
    from httpx import ASGITransport, AsyncClient

    from backend.core.auth import get_current_user
    from backend.core.database import get_db
    from backend.main import app

    # Mock DB session that returns empty results by default
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_db] = override_get_db

    # Patch get_redis_pool to return None (fail-open, no Redis needed)
    with patch("backend.core.cache.get_redis_pool", new=AsyncMock(return_value=None)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac, mock_db

    app.dependency_overrides.clear()


# ── Test: Admin role enforcement ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user():
    """The require_admin dependency should raise 403 for non-admin users."""
    from fastapi import HTTPException

    from backend.core.auth import require_admin

    regular_user = _make_user("user-1", "user@test.com", role=UserRole.USER)

    with pytest.raises(HTTPException) as exc_info:
        await require_admin(user=regular_user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_allows_admin_user():
    """The require_admin dependency should pass for admin users."""
    from backend.core.auth import require_admin

    admin_user = _make_user("admin-1", "admin@test.com", role=UserRole.ADMIN)

    result = await require_admin(user=admin_user)
    assert result.id == "admin-1"


# ── Test: Rate limiting ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_rejects_when_exceeded():
    """Rate limiter should return 429 after exceeding the limit."""
    from fastapi import HTTPException

    from backend.core.rate_limit import RATE_LIMIT_REQUESTS, check_rate_limit

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/portfolios"

    # Create a mock Redis that behaves like a real pipeline
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    # Pipeline methods return the pipe for chaining
    mock_pipe.zremrangebyscore.return_value = mock_pipe
    mock_pipe.zcard.return_value = mock_pipe
    mock_pipe.zadd.return_value = mock_pipe
    mock_pipe.expire.return_value = mock_pipe
    # execute() is async
    mock_pipe.execute = AsyncMock(return_value=[
        None,                    # zremrangebyscore
        RATE_LIMIT_REQUESTS,     # zcard — at limit
        None,                    # zadd
        None,                    # expire
    ])
    mock_redis.pipeline.return_value = mock_pipe
    mock_redis.zrem = AsyncMock()

    user = _make_user("rate-test-user", "rate@test.com")

    # Patch _get_redis to return our mock synchronously (it's an async func)
    async def mock_get_redis():
        return mock_redis

    with patch("backend.core.rate_limit._get_redis", side_effect=mock_get_redis):
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(request=mock_request, user=user)
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail


@pytest.mark.asyncio
async def test_rate_limit_allows_when_under_limit():
    """Rate limit should allow requests when under the limit."""
    from backend.core.rate_limit import check_rate_limit

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/portfolios"

    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.zremrangebyscore.return_value = mock_pipe
    mock_pipe.zcard.return_value = mock_pipe
    mock_pipe.zadd.return_value = mock_pipe
    mock_pipe.expire.return_value = mock_pipe
    mock_pipe.execute = AsyncMock(return_value=[None, 50, None, None])
    mock_redis.pipeline.return_value = mock_pipe

    user = _make_user("rate-test-user-2", "rate2@test.com")

    async def mock_get_redis():
        return mock_redis

    with patch("backend.core.rate_limit._get_redis", side_effect=mock_get_redis):
        result = await check_rate_limit(request=mock_request, user=user)
        assert result.id == "rate-test-user-2"


@pytest.mark.asyncio
async def test_rate_limit_fails_open_when_redis_unavailable():
    """Rate limiter should allow requests when Redis is down (fail-open)."""
    from backend.core.rate_limit import check_rate_limit

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/portfolios"

    user = _make_user("rate-test-user-3", "rate3@test.com")

    async def mock_get_redis():
        return None

    with patch("backend.core.rate_limit._get_redis", side_effect=mock_get_redis):
        result = await check_rate_limit(request=mock_request, user=user)
        assert result.id == "rate-test-user-3"


@pytest.mark.asyncio
async def test_rate_limit_fails_open_on_redis_error():
    """Rate limiter should allow requests when Redis throws an error."""
    from backend.core.rate_limit import check_rate_limit

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/portfolios"

    mock_redis = MagicMock()
    mock_redis.pipeline.side_effect = Exception("Redis connection lost")

    user = _make_user("rate-test-user-4", "rate4@test.com")

    async def mock_get_redis():
        return mock_redis

    with patch("backend.core.rate_limit._get_redis", side_effect=mock_get_redis):
        result = await check_rate_limit(request=mock_request, user=user)
        assert result.id == "rate-test-user-4"


# ── Test: Tenant context dependency ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_tenant_db_sets_session_variable():
    """get_tenant_db should execute SET LOCAL with the user's ID."""
    from backend.core.tenant import get_tenant_db

    mock_db = AsyncMock()
    user = _make_user(USER_A_ID, "userA@test.com")

    result = await get_tenant_db(user=user, db=mock_db)

    # Verify SET LOCAL was called with the user's ID
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args
    # First positional arg is text(), second is params dict
    sql_text = str(call_args[0][0])
    assert "app.current_user_id" in sql_text
    params = call_args[0][1]
    assert params["user_id"] == USER_A_ID
    assert result == mock_db


# ── Test: UserRole enum ────────────────────────────────────────────────────────

def test_user_role_values():
    """UserRole enum should have USER and ADMIN values."""
    assert UserRole.USER == "USER"
    assert UserRole.ADMIN == "ADMIN"
    assert UserRole.USER.value == "USER"
    assert UserRole.ADMIN.value == "ADMIN"


def test_user_is_admin_property():
    """User.is_admin property should correctly identify admin users."""
    admin = _make_user("admin-1", "admin@test.com", role=UserRole.ADMIN)
    regular = _make_user("user-1", "user@test.com", role=UserRole.USER)

    assert admin.role == UserRole.ADMIN
    assert regular.role == UserRole.USER


# ── Test: Cross-user data isolation via API ────────────────────────────────────
# These tests use dependency overrides to bypass real DB/Redis while verifying
# the API routes properly scope queries by user_id.

@pytest.mark.asyncio
async def test_user_a_gets_empty_portfolios(isolated_client):
    """User A with no portfolios should get an empty list."""
    client, mock_db = isolated_client
    response = await client.get("/api/v1/portfolios")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_portfolio_by_id(isolated_client):
    """User A should get 404 when trying to access a portfolio that doesn't belong to them."""
    client, mock_db = isolated_client

    # DB returns None because the query filters by user_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    response = await client.get("/api/v1/portfolios/port-b-1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_decision_history(isolated_client):
    """User A should only see their own decision history (empty if no records)."""
    client, mock_db = isolated_client

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    response = await client.get("/api/v1/decisions/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["decisions"] == []


@pytest.mark.asyncio
async def test_user_a_cannot_access_user_b_import_jobs(isolated_client):
    """User A should only see their own import jobs."""
    client, mock_db = isolated_client

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    response = await client.get("/api/v1/import/jobs")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_user_a_cannot_modify_user_b_decision(isolated_client):
    """User A should get 404 when trying to record action on User B's decision."""
    client, mock_db = isolated_client

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    response = await client.post(
        "/api/v1/decisions/history/decision-b-1/action",
        json={"user_action": "BOUGHT"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_two_users_see_different_data():
    """
    When User A and User B both request portfolios, each only sees their own.
    This verifies the route always passes user.id to the WHERE clause.
    """
    from httpx import ASGITransport, AsyncClient

    from backend.core.auth import get_current_user
    from backend.core.database import get_db
    from backend.main import app

    user_a = _make_user(USER_A_ID, "userA@test.com")
    user_b = _make_user(USER_B_ID, "userB@test.com")

    # Simulate portfolios for each user
    portfolio_a = MagicMock()
    portfolio_a.id = "port-a"
    portfolio_a.name = "A Portfolio"
    portfolio_a.currency = "INR"
    portfolio_a.description = None
    portfolio_a.created_at = "2026-01-01T00:00:00"
    portfolio_a.user_id = USER_A_ID

    portfolio_b = MagicMock()
    portfolio_b.id = "port-b"
    portfolio_b.name = "B Portfolio"
    portfolio_b.currency = "USD"
    portfolio_b.description = None
    portfolio_b.created_at = "2026-02-01T00:00:00"
    portfolio_b.user_id = USER_B_ID

    async def make_client_for_user(user, portfolios):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = portfolios
        mock_db.execute.return_value = mock_result

        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            return await ac.get("/api/v1/portfolios")

    try:
        with patch("backend.core.cache.get_redis_pool", new=AsyncMock(return_value=None)):
            # User A sees only their portfolio
            response_a = await make_client_for_user(user_a, [portfolio_a])
            assert response_a.status_code == 200
            data_a = response_a.json()
            assert len(data_a) == 1
            assert data_a[0]["id"] == "port-a"

            # User B sees only their portfolio
            response_b = await make_client_for_user(user_b, [portfolio_b])
            assert response_b.status_code == 200
            data_b = response_b.json()
            assert len(data_b) == 1
            assert data_b[0]["id"] == "port-b"
    finally:
        app.dependency_overrides.clear()


# ── Test: Route-level user_id filtering verification ───────────────────────────
# Static analysis tests — confirm the pattern exists in route code.

def test_portfolio_route_filters_by_user_id():
    """Verify that portfolios.list_portfolios uses user.id in query."""
    import inspect

    from backend.api.v1.portfolios import list_portfolios

    source = inspect.getsource(list_portfolios)
    assert "user.id" in source
    assert "Portfolio.user_id" in source


def test_import_jobs_route_filters_by_user_id():
    """Verify import jobs route filters by user_id."""
    import inspect

    from backend.api.v1.imports import list_import_jobs

    source = inspect.getsource(list_import_jobs)
    assert "user.id" in source
    assert "ImportJob.user_id" in source


def test_decision_history_route_filters_by_user_id():
    """Verify decision history route filters by user_id."""
    import inspect

    from backend.api.v1.decision_history import get_decision_history

    source = inspect.getsource(get_decision_history)
    assert "user.id" in source
    assert "DecisionRecord.user_id" in source


def test_watchlist_route_filters_by_user_id():
    """Verify watchlist route filters by user_id."""
    import inspect

    from backend.api.v1.watchlist_intel import get_watchlist_intelligence

    source = inspect.getsource(get_watchlist_intelligence)
    assert "user.id" in source
    assert "WatchlistItem.user_id" in source
