"""
EBA — Security Test Suite (F3-10 / SEC-001..SEC-013)
20+ cenários de segurança automatizados cobrindo OWASP Top 10 e OWASP API Security Top 10.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import PermissionDeniedError, TenantIsolationError
from app.core.permissions import check_tenant_isolation, require_role
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.company import Company
from app.models.token import RefreshToken
from app.models.user import User, UserRole
from app.modules.auth.service import auth_service, hash_refresh_token

settings = get_settings()


# =============================================================================
# SEC-001: Autenticação JWT e Tratamento de Tokens
# =============================================================================


@pytest.mark.security
async def test_sec001_unauthenticated_request_rejected(async_client: AsyncClient) -> None:
    """SEC-001: Requisição a endpoint protegido sem token retorna 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHENTICATED"


@pytest.mark.security
async def test_sec001_forged_signature_token_rejected(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """SEC-001: Token forjado com chave secreta diferente é categoricamente rejeitado."""
    forged_token = jwt.encode(
        {"sub": str(sample_admin_user.id), "type": "access", "exp": 9999999999},
        "an_attacker_forged_secret_key_12345678",
        algorithm="HS256",
    )

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHENTICATED"


@pytest.mark.security
async def test_sec001_expired_token_rejected(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """SEC-001: Access token expirado é rejeitado com mensagem explicativa."""
    expired_token = create_access_token(
        subject=sample_admin_user.id,
        expires_delta=timedelta(seconds=-60),
    )

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expirado" in response.json()["message"].lower()


@pytest.mark.security
async def test_sec001_malformed_token_rejected(async_client: AsyncClient) -> None:
    """SEC-001: Token corrompido / lixo arbitrário retorna 401."""
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"},
    )
    assert response.status_code == 401


@pytest.mark.security
async def test_sec001_token_type_confusion_attack(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """
    SEC-001: Token Type Confusion.
    Enviar um Refresh Token como se fosse Access Token deve retornar 401.
    """
    refresh_token = create_refresh_token(subject=sample_admin_user.id)

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401
    assert "tipo de token inválido" in response.json()["message"].lower()


@pytest.mark.security
async def test_sec001_nonexistent_user_in_token_sub(async_client: AsyncClient) -> None:
    """SEC-001: Token com assinatura válida mas UUID de usuário inexistente no banco retorna 401."""
    ghost_token = create_access_token(subject=uuid.uuid4())

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ghost_token}"},
    )
    assert response.status_code == 401


@pytest.mark.security
async def test_sec001_deactivated_user_denied_access(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_viewer_user: User,
) -> None:
    """SEC-001: Usuário desativado é impedido de autenticar mesmo com token válido."""
    token = create_access_token(subject=sample_viewer_user.id)

    sample_viewer_user.is_active = False
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert "inativa" in response.json()["message"].lower()


@pytest.mark.security
async def test_sec001_soft_deleted_user_denied_access(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_viewer_user: User,
) -> None:
    """SEC-001: Usuário excluído via soft delete não autentica."""
    token = create_access_token(subject=sample_viewer_user.id)

    sample_viewer_user.is_deleted = True
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# =============================================================================
# SEC-002: Hashing Seguro de Senhas (Argon2id)
# =============================================================================


@pytest.mark.security
def test_sec002_argon2id_hashing() -> None:
    """SEC-002: Senhas usam padrão Argon2id ($argon2id$) e nunca texto claro."""
    raw_password = "P@sswordSuperSecure2026!"
    hashed = hash_password(raw_password)

    assert hashed.startswith("$argon2id$")
    assert raw_password not in hashed
    assert verify_password(raw_password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


# =============================================================================
# SEC-003: RBAC (Role-Based Access Control)
# =============================================================================


@pytest.mark.security
async def test_sec003_rbac_viewer_denied_admin_endpoint(sample_viewer_user: User) -> None:
    """SEC-003: Usuário com role VIEWER recebe 403 Forbidden em rota ADMIN."""
    admin_guard = require_role(UserRole.ADMIN)

    with pytest.raises(PermissionDeniedError, match="Acesso negado"):
        await admin_guard(current_user=sample_viewer_user)


@pytest.mark.security
async def test_sec003_rbac_operator_denied_admin_endpoint(
    db_session: AsyncSession,
    sample_company: Company,
) -> None:
    """SEC-003: Usuário OPERATOR recebe 403 Forbidden em rota ADMIN."""
    operator = User(
        id=uuid.uuid4(),
        email="operator@acme.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Operator User",
        role=UserRole.OPERATOR.value,
        tenant_id=sample_company.id,
        is_active=True,
    )
    admin_guard = require_role(UserRole.ADMIN)

    with pytest.raises(PermissionDeniedError, match="Acesso negado"):
        await admin_guard(current_user=operator)


@pytest.mark.security
async def test_sec003_rbac_admin_granted_admin_endpoint(sample_admin_user: User) -> None:
    """SEC-003: Usuário ADMIN acessa rota ADMIN com sucesso."""
    admin_guard = require_role(UserRole.ADMIN)
    user = await admin_guard(current_user=sample_admin_user)
    assert user.id == sample_admin_user.id


@pytest.mark.security
async def test_sec003_rbac_superadmin_universal_access(sample_superadmin_user: User) -> None:
    """SEC-003: SUPERADMIN pode acessar qualquer rota restrita."""
    admin_guard = require_role(UserRole.ADMIN, UserRole.MANAGER)
    user = await admin_guard(current_user=sample_superadmin_user)
    assert user.id == sample_superadmin_user.id


# =============================================================================
# SEC-004: Prevenção de IDOR & Isolamento de Tenants
# =============================================================================


@pytest.mark.security
def test_sec004_idor_cross_tenant_denied(sample_admin_user: User) -> None:
    """SEC-004: Tentativa de acessar recurso de outro tenant é barrada com TenantIsolationError."""
    other_tenant_id = uuid.uuid4()

    with pytest.raises(TenantIsolationError, match="você não tem permissão"):
        check_tenant_isolation(other_tenant_id, sample_admin_user)


@pytest.mark.security
def test_sec004_idor_superadmin_allowed(sample_superadmin_user: User) -> None:
    """SEC-004: SUPERADMIN tem bypass legítimo de isolamento para gerenciar a plataforma."""
    target_tenant_id = uuid.uuid4()
    # Não deve levantar exceção
    check_tenant_isolation(target_tenant_id, sample_superadmin_user)


# =============================================================================
# SEC-013: Proteção de Refresh Tokens, Family Tracking & Anti-Enumeração
# =============================================================================


@pytest.mark.security
async def test_sec013_refresh_token_never_stored_in_plaintext(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """SEC-013: O token de atualização é armazenado apenas como hash SHA-256 no banco."""
    _, refresh_token, _ = await auth_service.create_tokens(db_session, sample_admin_user)

    # Verifica se a string em claro do token existe no banco
    stmt = select(RefreshToken).where(RefreshToken.token_hash == refresh_token)
    res = await db_session.execute(stmt)
    assert res.scalar_one_or_none() is None

    # O hash SHA-256 deve estar no banco
    expected_hash = hash_refresh_token(refresh_token)
    stmt_hash = select(RefreshToken).where(RefreshToken.token_hash == expected_hash)
    res_hash = await db_session.execute(stmt_hash)
    assert res_hash.scalar_one_or_none() is not None


@pytest.mark.security
async def test_sec013_replay_attack_revokes_token_family(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """
    SEC-013: Reutilização de um refresh token já consumido revoga
    imediatamente todos os tokens daquela família de sessão.
    """
    # 1. Login inicial
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Password123!"},
    )
    token_v1 = login_resp.json()["refresh_token"]

    # 2. Primeira rotação (v1 -> v2)
    refresh_resp1 = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_v1},
    )
    assert refresh_resp1.status_code == 200
    token_v2 = refresh_resp1.json()["refresh_token"]

    # 3. Ataque de Replay: o invasor ou cliente desatualizado tenta usar token_v1 novamente
    replay_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_v1},
    )
    assert replay_resp.status_code == 401
    assert "reutilização de token detectada" in replay_resp.json()["message"].lower()

    # 4. Token v2 também foi invalidado devido ao replay attack
    revoked_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_v2},
    )
    assert revoked_resp.status_code == 401


@pytest.mark.security
async def test_sec013_logout_invalidates_refresh_token(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """SEC-013: Após o logout, o refresh token não pode mais ser utilizado para novas emissões."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Password123!"},
    )
    token = login_resp.json()["refresh_token"]

    # Realiza logout
    await async_client.post("/api/v1/auth/logout", json={"refresh_token": token})

    # Tenta usar o token após logout
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token},
    )
    assert refresh_resp.status_code == 401


@pytest.mark.security
async def test_sec013_password_reset_anti_enumeration(async_client: AsyncClient) -> None:
    """
    SEC-013: Solicitação de reset para e-mail inexistente retorna resposta idêntica (200 OK)
    para evitar enumeração de usuários do sistema.
    """
    response = await async_client.post(
        "/api/v1/auth/password/reset-request",
        json={"email": "ghost.user.does.not.exist@acme.com"},
    )
    assert response.status_code == 200
    assert "instruções de recuperação foram enviadas" in response.json()["message"]


@pytest.mark.security
async def test_sec013_password_reset_token_cannot_be_reused(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """SEC-013: Token de recuperação de senha é invalidado após o primeiro uso."""
    with patch("app.tasks.email.send_password_reset_email.delay") as mock_email:
        await async_client.post(
            "/api/v1/auth/password/reset-request",
            json={"email": "admin@acme.com"},
        )
        _, args, _ = mock_email.mock_calls[0]
        token = args[1]

    # Primeiro uso: sucesso
    resp1 = await async_client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": "NewSecurePassword123!"},
    )
    assert resp1.status_code == 200

    # Segundo uso (tentativa de reutilização): bloqueado
    resp2 = await async_client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": "AnotherNewPassword123!"},
    )
    assert resp2.status_code == 401
    assert "já utilizado ou revogado" in resp2.json()["message"].lower()


@pytest.mark.security
async def test_sec007_login_rate_limiting(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """
    SEC-007: Proteção contra força bruta (Rate Limiting).
    Requisições repetidas ao endpoint de login excedem o limite de 5/min e retornam 429.
    """
    responses = []
    for _ in range(6):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@acme.com", "password": "WrongPassword!"},
        )
        responses.append(resp.status_code)

    # Pelo menos uma das requisições deve ter retornado 429 Too Many Requests
    assert 429 in responses
