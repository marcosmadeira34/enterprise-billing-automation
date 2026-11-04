"""
Unit tests for tenant context variables.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.tenant import (
    get_current_tenant_id,
    get_current_user_id,
    set_current_tenant_id,
    set_current_user_id,
)


@pytest.mark.unit
def test_tenant_context_lifecycle() -> None:
    """Verifica definição e recuperação isolada do tenant_id."""
    set_current_tenant_id(None)
    assert get_current_tenant_id() is None

    test_id = uuid.uuid4()
    set_current_tenant_id(test_id)
    assert get_current_tenant_id() == test_id

    # Aceita formato string
    str_id = str(uuid.uuid4())
    set_current_tenant_id(str_id)
    assert get_current_tenant_id() == uuid.UUID(str_id)

    set_current_tenant_id(None)
    assert get_current_tenant_id() is None


@pytest.mark.unit
def test_user_context_lifecycle() -> None:
    """Verifica definição e recuperação isolada do user_id."""
    set_current_user_id(None)
    assert get_current_user_id() is None

    user_id = uuid.uuid4()
    set_current_user_id(user_id)
    assert get_current_user_id() == user_id

    set_current_user_id(None)
    assert get_current_user_id() is None
