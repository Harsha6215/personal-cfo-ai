"""
Tests for /api/v1/health and /api/v1/version.

Run:  docker compose run backend pytest
"""

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "backend"


@pytest.mark.asyncio
async def test_version_returns_version(client):
    response = await client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert "version" in body
    assert "env" in body
    assert "name" in body


@pytest.mark.asyncio
async def test_health_has_request_id_header(client):
    response = await client.get("/api/v1/health")
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_root_health_shortcut(client):
    """Docker healthcheck uses /health (no /api/v1 prefix)."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_docs_accessible(client):
    """Swagger UI must be reachable."""
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_json_accessible(client):
    """OpenAPI schema must be reachable."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Personal CFO AI"
