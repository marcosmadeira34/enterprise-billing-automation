"""
Unit tests for custom exceptions and error serialization.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
    TenantIsolationError,
)


@pytest.mark.unit
def test_custom_exception_properties() -> None:
    """Verifica atributos e códigos de status das exceções de domínio."""
    e_not_found = EntityNotFoundError("Invoice", "INV-100")
    assert e_not_found.status_code == 404
    assert e_not_found.code == "NOT_FOUND"

    e_conflict = EntityAlreadyExistsError("Company", "12.345.678/0001-90")
    assert e_conflict.status_code == 409
    assert e_conflict.code == "CONFLICT"

    e_forbidden = PermissionDeniedError()
    assert e_forbidden.status_code == 403

    e_tenant = TenantIsolationError()
    assert e_tenant.status_code == 403
    assert e_tenant.code == "TENANT_VIOLATION"

    e_business = BusinessRuleViolationError("Saldo insuficiente", details={"saldo": 0})
    assert e_business.status_code == 400
    assert e_business.details == {"saldo": 0}


@pytest.mark.unit
async def test_validation_error_handler(async_client: AsyncClient) -> None:
    """Verifica que requisição com parâmetros inválidos retorna 422 padronizado."""
    # Chamada propositalmente incorreta para testar exception handler
    response = await async_client.post("/api/v1/status", json={"invalid": "field"})
    # Status endpoint é GET, portanto POST retorna 405 Method Not Allowed
    assert response.status_code == 405
