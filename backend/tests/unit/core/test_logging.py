"""
Unit tests for structured logging setup.
"""

from __future__ import annotations

import pytest

from app.config import LogFormat, Settings
from app.core.logging import setup_logging


@pytest.mark.unit
def test_setup_logging_console(test_settings: Settings) -> None:
    """Verifica inicialização do logging em modo console."""
    setup_logging(test_settings)


@pytest.mark.unit
def test_setup_logging_json() -> None:
    """Verifica inicialização do logging em modo JSON."""
    settings = Settings(
        secret_key="super_secure_test_secret_key_minimum_32_characters_123",
        postgres_password="pass",
        redis_password="pass",
        minio_access_key="acc",
        minio_secret_key="sec",
        log_format=LogFormat.JSON,
    )
    setup_logging(settings)
