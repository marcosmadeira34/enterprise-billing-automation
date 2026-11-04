"""
EBA — Extension Hook Points & Registry
Permite que regras comerciais particulares e integrações sob demanda
sejam injetadas no ciclo de vida sem alterar o núcleo da aplicação.
"""

from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class HookPoint(StrEnum):
    """Pontos de extensão do ciclo de vida das operações do EBA."""

    PRE_COMPANY_CREATE = "pre_company_create"
    POST_COMPANY_CREATE = "post_company_create"

    PRE_CONTRACT_ACTIVATE = "pre_contract_activate"
    POST_CONTRACT_ACTIVATE = "post_contract_activate"

    PRE_INVOICE_GENERATE = "pre_invoice_generate"
    POST_INVOICE_GENERATE = "post_invoice_generate"

    PRE_DOCUMENT_PROCESS = "pre_document_process"
    POST_DOCUMENT_PROCESS = "post_document_process"

    PRE_PAYMENT_CONFIRM = "pre_payment_confirm"
    POST_PAYMENT_CONFIRM = "post_payment_confirm"


@dataclass
class HookContext:
    """Contexto mutável transmitido sequencialmente através da cadeia de hooks."""

    hook_point: HookPoint
    tenant_id: UUID | None = None
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False
    cancel_reason: str | None = None

    def cancel(self, reason: str) -> None:
        """Cancela a operação subsequente no núcleo."""
        self.cancelled = True
        self.cancel_reason = reason


HookHandler = Callable[[HookContext], Awaitable[HookContext | None] | HookContext | None]


@dataclass
class _HookRegistration:
    handler: HookHandler
    priority: int
    tenant_id: UUID | None


class HookRegistry:
    """Registro e orquestrador de execução de hooks."""

    def __init__(self) -> None:
        self._hooks: dict[HookPoint, list[_HookRegistration]] = defaultdict(list)

    def register(
        self,
        hook_point: HookPoint,
        handler: HookHandler,
        priority: int = 100,
        tenant_id: UUID | None = None,
    ) -> None:
        """
        Registra um handler em um ponto de extensão.
        Menor valor de priority executa primeiro.
        Se tenant_id for informado, executa somente para aquele cliente.
        """
        reg = _HookRegistration(handler=handler, priority=priority, tenant_id=tenant_id)
        self._hooks[hook_point].append(reg)
        self._hooks[hook_point].sort(key=lambda r: r.priority)

    async def execute(self, context: HookContext) -> HookContext:
        """Executa a cadeia ordenada de hooks para o ponto informado."""
        registrations = self._hooks.get(context.hook_point, [])

        for reg in registrations:
            # Se o hook for específico de um tenant e não coincidir, pula
            if reg.tenant_id and reg.tenant_id != context.tenant_id:
                continue

            if context.cancelled:
                logger.info(
                    "Hook chain cancelled",
                    hook_point=context.hook_point,
                    reason=context.cancel_reason,
                )
                break

            try:
                if inspect.iscoroutinefunction(reg.handler):
                    result = await reg.handler(context)
                else:
                    result = reg.handler(context)

                if isinstance(result, HookContext):
                    context = result
            except Exception as exc:
                logger.error(
                    "Error executing hook handler",
                    hook_point=context.hook_point,
                    error=str(exc),
                )
                raise

        return context


# Instância global do registro de hooks
hook_registry = HookRegistry()
