"""
Unit tests for configuration validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.unit
def test_valid_settings(test_settings: Settings) -> None:
    """Verifica carregamento de configurações válidas."""
    assert test_settings.is_testing is True
    assert test_settings.secret_key is not None
    assert len(test_settings.secret_key) >= 32
    assert "postgresql+asyncpg://" in test_settings.effective_database_url
    assert "redis://" in (test_settings.celery_broker_url or "")


@pytest.mark.unit
def test_reject_weak_secret_key() -> None:
    """Rejeita inicialização se a SECRET_KEY for fraca ou muito curta."""
    with pytest.raises(ValidationError):
        Settings(
            secret_key="short",
            postgres_password="pass",
            redis_password="pass",
            minio_access_key="acc",
            minio_secret_key="sec",
        )


@pytest.mark.unit
def test_cors_origins_parsing() -> None:
    """Valida conversão de string CSV para lista de origens."""
    settings = Settings(
        secret_key="super_secure_test_secret_key_minimum_32_characters_123",
        postgres_password="pass",
        redis_password="pass",
        minio_access_key="acc",
        minio_secret_key="sec",
        allowed_origins="http://example.com, https://app.example.com",  # type: ignore[arg-type]
    )
    assert settings.allowed_origins == ["http://example.com", "https://app.example.com"]
