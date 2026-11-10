"""
Unit tests for RBAC Permissions & Tenant Isolation (SEC-003, SEC-004).
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError, TenantIsolationError
from app.core.permissions import check_tenant_isolation, get_current_user, require_role
from app.core.security import create_access_token, create_refresh_token
from app.core.tenant import get_current_tenant_id, get_current_user_id
from app.models.user import User, UserRole


@pytest.mark.unit
async def test_get_current_user_success(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica autenticação e injeção de contexto a partir de token válido."""
    token = create_access_token(
        subject=sample_admin_user.id,
        tenant_id=sample_admin_user.tenant_id,
        roles=[sample_admin_user.role],
    )

    user = await get_current_user(
        authorization=f"Bearer {token}",
        session=db_session,
    )

    assert user.id == sample_admin_user.id
    assert get_current_user_id() == sample_admin_user.id
    assert get_current_tenant_id() == sample_admin_user.tenant_id


@pytest.mark.unit
async def test_get_current_user_missing_header(db_session: AsyncSession) -> None:
    """Rejeita requisição sem header Authorization."""
    with pytest.raises(AuthenticationError, match="Token de autenticação não fornecido"):
        await get_current_user(authorization=None, session=db_session)


@pytest.mark.unit
async def test_get_current_user_invalid_bearer_format(db_session: AsyncSession) -> None:
    """Rejeita esquema que não seja Bearer."""
    with pytest.raises(AuthenticationError, match="Formato de cabeçalho de autenticação inválido"):
        await get_current_user(authorization="Basic invalid_format", session=db_session)


@pytest.mark.unit
async def test_get_current_user_token_type_confusion(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Rejeita refresh token usado como access token (Token Type Confusion)."""
    refresh_token = create_refresh_token(subject=sample_admin_user.id)

    with pytest.raises(AuthenticationError, match="Tipo de token inválido"):
        await get_current_user(authorization=f"Bearer {refresh_token}", session=db_session)


@pytest.mark.unit
async def test_get_current_user_expired_token(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Rejeita access token expirado."""
    expired_token = create_access_token(
        subject=sample_admin_user.id,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(AuthenticationError, match="Token expirado"):
        await get_current_user(authorization=f"Bearer {expired_token}", session=db_session)


@pytest.mark.unit
async def test_get_current_user_inactive_account(
    db_session: AsyncSession,
    sample_viewer_user: User,
) -> None:
    """Rejeita acesso de usuário com conta inativa."""
    token = create_access_token(subject=sample_viewer_user.id)

    sample_viewer_user.is_active = False
    await db_session.commit()

    with pytest.raises(AuthenticationError, match="Conta de usuário inativa"):
        await get_current_user(authorization=f"Bearer {token}", session=db_session)


@pytest.mark.unit
async def test_require_role_allowed_for_matching_role(sample_admin_user: User) -> None:
    """Permite acesso quando o usuário possui a role exigida."""
    checker = require_role(UserRole.ADMIN)
    result = await checker(current_user=sample_admin_user)
    assert result.id == sample_admin_user.id


@pytest.mark.unit
async def test_require_role_forbidden_for_insufficient_role(sample_viewer_user: User) -> None:
    """Nega acesso (403) quando a role do usuário for insuficiente (SEC-003)."""
    checker = require_role(UserRole.ADMIN)
    with pytest.raises(PermissionDeniedError, match="Acesso negado"):
        await checker(current_user=sample_viewer_user)


@pytest.mark.unit
async def test_require_role_superadmin_bypasses_check(sample_superadmin_user: User) -> None:
    """Superadmin possui autorização global independente da role solicitada."""
    checker = require_role(UserRole.ADMIN, UserRole.MANAGER)
    result = await checker(current_user=sample_superadmin_user)
    assert result.id == sample_superadmin_user.id


@pytest.mark.unit
def test_check_tenant_isolation_same_tenant(sample_admin_user: User) -> None:
    """Permite acesso a recursos pertencentes ao mesmo tenant."""
    # Não deve levantar exceção
    check_tenant_isolation(sample_admin_user.tenant_id, sample_admin_user)


@pytest.mark.unit
def test_check_tenant_isolation_cross_tenant_denied(sample_admin_user: User) -> None:
    """Nega acesso (403 IDOR) a recurso de outro tenant (SEC-004)."""
    foreign_tenant_id = uuid.uuid4()
    with pytest.raises(TenantIsolationError, match="Acesso negado: você não tem permissão"):
        check_tenant_isolation(foreign_tenant_id, sample_admin_user)


@pytest.mark.unit
def test_check_tenant_isolation_superadmin_allowed(sample_superadmin_user: User) -> None:
    """Superadmin pode acessar recursos de qualquer tenant sem violação de isolamento."""
    foreign_tenant_id = uuid.uuid4()
    # Não deve levantar exceção
    check_tenant_isolation(foreign_tenant_id, sample_superadmin_user)
