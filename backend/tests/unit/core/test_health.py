"""
Unit tests for health endpoints.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.unit
async def test_liveness_probe(async_client: AsyncClient) -> None:
    """Valida retorno do endpoint de liveness."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "eba-api"}


@pytest.mark.unit
async def test_api_v1_status(async_client: AsyncClient) -> None:
    """Valida retorno do status da API v1."""
    response = await async_client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json() == {"api_version": "v1", "status": "active"}


@pytest.mark.unit
@patch("app.api.health.create_async_engine")
@patch("app.api.health.aioredis.from_url")
async def test_readiness_probe_healthy(
    mock_redis_from_url: MagicMock,
    mock_create_engine: MagicMock,
    async_client: AsyncClient,
) -> None:
    """Valida retorno de readiness quando os serviços respondem com sucesso."""
    # Mock do Redis
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis_from_url.return_value = mock_redis

    # Mock do PostgreSQL
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_conn
    mock_cm.__aexit__.return_value = None

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_cm
    mock_engine.dispose = AsyncMock()
    mock_create_engine.return_value = mock_engine

    response = await async_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "healthy"
    assert data["checks"]["redis"] == "healthy"


@pytest.mark.unit
@patch("app.api.health.create_async_engine")
@patch("app.api.health.aioredis.from_url")
async def test_readiness_probe_degraded(
    mock_redis_from_url: MagicMock,
    mock_create_engine: MagicMock,
    async_client: AsyncClient,
) -> None:
    """Valida retorno 503 de readiness quando uma dependência falha."""
    mock_create_engine.side_effect = Exception("DB Connection refused")
    mock_redis_from_url.side_effect = Exception("Redis connection refused")

    response = await async_client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
