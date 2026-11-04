"""
EBA — Tenant Context Management
Gerenciamento de contexto do Tenant ativo via ContextVars.
Garante que em qualquer ponto do ciclo de requisição o tenant_id esteja isolado e disponível.
"""

from __future__ import annotations

from contextvars import ContextVar
from uuid import UUID

# Variável de contexto assíncrona para o tenant ativo na requisição
_tenant_context: ContextVar[UUID | None] = ContextVar("tenant_id", default=None)
_user_context: ContextVar[UUID | None] = ContextVar("user_id", default=None)


def set_current_tenant_id(tenant_id: UUID | str | None) -> None:
    """Define o tenant_id ativo na requisição atual."""
    if tenant_id is None:
        _tenant_context.set(None)
    elif isinstance(tenant_id, UUID):
        _tenant_context.set(tenant_id)
    else:
        _tenant_context.set(UUID(str(tenant_id)))


def get_current_tenant_id() -> UUID | None:
    """Obtém o tenant_id ativo na requisição atual."""
    return _tenant_context.get()


def set_current_user_id(user_id: UUID | str | None) -> None:
    """Define o user_id ativo na requisição atual."""
    if user_id is None:
        _user_context.set(None)
    elif isinstance(user_id, UUID):
        _user_context.set(user_id)
    else:
        _user_context.set(UUID(str(user_id)))


def get_current_user_id() -> UUID | None:
    """Obtém o user_id ativo na requisição atual."""
    return _user_context.get()
