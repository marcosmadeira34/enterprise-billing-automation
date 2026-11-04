"""
Unit tests for the extension HookRegistry.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.hooks import HookContext, HookPoint, HookRegistry


@pytest.mark.unit
async def test_hook_execution_order_and_mutation() -> None:
    """Verifica ordem de execução por prioridade e mutação de dados no contexto."""
    registry = HookRegistry()
    execution_order: list[int] = []

    def first_hook(ctx: HookContext) -> None:
        execution_order.append(1)
        ctx.data["step1"] = True

    def second_hook(ctx: HookContext) -> None:
        execution_order.append(2)
        ctx.data["step2"] = True

    registry.register(HookPoint.PRE_INVOICE_GENERATE, second_hook, priority=20)
    registry.register(HookPoint.PRE_INVOICE_GENERATE, first_hook, priority=10)

    initial_ctx = HookContext(
        hook_point=HookPoint.PRE_INVOICE_GENERATE,
        data={"invoice_id": "123"},
    )

    result_ctx = await registry.execute(initial_ctx)

    assert execution_order == [1, 2]
    assert result_ctx.data["step1"] is True
    assert result_ctx.data["step2"] is True
    assert result_ctx.cancelled is False


@pytest.mark.unit
async def test_hook_cancellation() -> None:
    """Verifica que um hook pode cancelar a execução subsequente."""
    registry = HookRegistry()
    executed_after = False

    def cancelling_hook(ctx: HookContext) -> None:
        ctx.cancel("Contrato sem limite de crédito.")

    def subsequent_hook(ctx: HookContext) -> None:
        nonlocal executed_after
        executed_after = True

    registry.register(HookPoint.PRE_INVOICE_GENERATE, cancelling_hook, priority=1)
    registry.register(HookPoint.PRE_INVOICE_GENERATE, subsequent_hook, priority=2)

    ctx = HookContext(hook_point=HookPoint.PRE_INVOICE_GENERATE)
    res = await registry.execute(ctx)

    assert res.cancelled is True
    assert res.cancel_reason == "Contrato sem limite de crédito."
    assert executed_after is False


@pytest.mark.unit
async def test_hook_tenant_filtering() -> None:
    """Verifica que hooks de um tenant específico não executam para outro tenant."""
    registry = HookRegistry()
    executed_tenants: list[uuid.UUID] = []

    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    def tenant_a_hook(ctx: HookContext) -> None:
        if ctx.tenant_id:
            executed_tenants.append(ctx.tenant_id)

    registry.register(
        HookPoint.PRE_INVOICE_GENERATE,
        tenant_a_hook,
        tenant_id=tenant_a,
    )

    # Executa para tenant B — não deve executar o hook
    await registry.execute(
        HookContext(hook_point=HookPoint.PRE_INVOICE_GENERATE, tenant_id=tenant_b)
    )
    assert len(executed_tenants) == 0

    # Executa para tenant A — deve executar
    await registry.execute(
        HookContext(hook_point=HookPoint.PRE_INVOICE_GENERATE, tenant_id=tenant_a)
    )
    assert executed_tenants == [tenant_a]
