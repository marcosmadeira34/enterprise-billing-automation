"""
EBA — Permissions & Role-Based Access Control (RBAC)
Dependências de autorização para proteção de endpoints conforme SEC-003 e SEC-004.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError, PermissionDeniedError, TenantIsolationError
from app.core.security import decode_token
from app.core.tenant import set_current_tenant_id, set_current_user_id
from app.models.user import User, UserRole


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Dependência FastAPI que extrai e valida o token Bearer JWT,
    carrega o usuário do banco e injeta o contexto do tenant/usuário.
    """
    if not authorization:
        raise AuthenticationError("Token de autenticação não fornecido.")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Formato de cabeçalho de autenticação inválido.")

    token = parts[1]
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AuthenticationError("Tipo de token inválido para autenticação de requisições.")

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise AuthenticationError("Token não contém a identificação do sujeito (sub).")

    try:
        user_uuid = UUID(str(user_id_raw))
    except ValueError as err:
        raise AuthenticationError("Identificador de usuário no token é inválido.") from err

    stmt = select(User).where(User.id == user_uuid, User.is_deleted.is_(False))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("Usuário associado ao token não existe ou foi removido.")

    if not user.is_active:
        raise AuthenticationError("Conta de usuário inativa.")

    # Injeta no contexto do request
    set_current_user_id(user.id)
    set_current_tenant_id(user.tenant_id)

    return user


def require_role(*allowed_roles: str | UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    """
    Fábrica de dependência para controle de acesso baseado em função (RBAC).
    Superadmin possui acesso irrestrito por padrão.
    """
    normalized_roles = {
        role.value if isinstance(role, UserRole) else str(role) for role in allowed_roles
    }

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role == UserRole.SUPERADMIN.value or current_user.role in normalized_roles:
            return current_user

        raise PermissionDeniedError(
            f"Acesso negado. Perfil '{current_user.role}' não tem permissão para esta operação."
        )

    return role_checker


def check_tenant_isolation(
    resource_tenant_id: uuid.UUID | None,
    current_user: User,
) -> None:
    """
    Garante o isolamento entre tenants (Prevenção de IDOR conforme SEC-004).
    Superadmins podem acessar dados de qualquer tenant.
    """
    if current_user.role == UserRole.SUPERADMIN.value:
        return

    if resource_tenant_id is None or current_user.tenant_id != resource_tenant_id:
        raise TenantIsolationError(
            "Acesso negado: você não tem permissão para acessar recursos deste tenant."
        )
