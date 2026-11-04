"""
EBA — Pytest Configuration & Fixtures
"""

from __future__ import annotations

import os

# Define variáveis de ambiente antes de qualquer import de app.*
os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "super_secure_test_secret_key_minimum_32_characters_123"
os.environ["POSTGRES_PASSWORD"] = "test_postgres_pass"
os.environ["REDIS_PASSWORD"] = "test_redis_pass"
os.environ["MINIO_ACCESS_KEY"] = "test_minio_key"
os.environ["MINIO_SECRET_KEY"] = "test_minio_secret"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.config import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def test_settings() -> Settings:
    """Fixture com configurações limpas de teste."""
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def async_client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP assíncrono para testes da API."""
    test_app = create_app(test_settings)
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
