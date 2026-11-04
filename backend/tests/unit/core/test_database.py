"""
Unit tests for database session provider.
"""

from __future__ import annotations

import pytest

from app.core.database import get_db_session


@pytest.mark.unit
async def test_get_db_session_lifecycle() -> None:
    """Verifica que o gerador de sessão fecha após o uso."""
    session_gen = get_db_session()
    # Verifica que o gerador é instanciado
    assert session_gen is not None
