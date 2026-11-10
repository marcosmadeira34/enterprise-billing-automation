"""
Unit tests for AuthService: auth, token rotation, replay detection and password reset.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import decode_token, verify_password
from app.models.token import RefreshToken
from app.models.user import User
from app.modules.auth.service import auth_service, hash_refresh_token


@pytest.mark.unit
async def test_authenticate_success(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica autenticação bem-sucedida de usuário ativo."""
    user = await auth_service.authenticate(db_session, "admin@acme.com", "Password123!")
    assert user.id == sample_admin_user.id
    assert user.last_login_at is not None


@pytest.mark.unit
async def test_authenticate_wrong_password(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica falha de autenticação com senha incorreta."""
    with pytest.raises(AuthenticationError, match="E-mail ou senha incorretos"):
        await auth_service.authenticate(db_session, "admin@acme.com", "WrongPass123!")


@pytest.mark.unit
async def test_authenticate_nonexistent_email(db_session: AsyncSession) -> None:
    """Verifica falha de autenticação para e-mail inexistente."""
    with pytest.raises(AuthenticationError, match="E-mail ou senha incorretos"):
        await auth_service.authenticate(db_session, "nonexistent@acme.com", "AnyPassword123!")


@pytest.mark.unit
async def test_authenticate_inactive_user(
    db_session: AsyncSession,
    sample_viewer_user: User,
) -> None:
    """Verifica bloqueio de login para usuário desativado."""
    sample_viewer_user.is_active = False
    await db_session.commit()

    with pytest.raises(AuthenticationError, match="Conta de usuário desativada"):
        await auth_service.authenticate(db_session, "viewer@acme.com", "Password123!")


@pytest.mark.unit
async def test_create_tokens_stores_hash_and_family(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica emissão de tokens e armazenamento seguro do hash no banco."""
    access_token, refresh_token, expires_in = await auth_service.create_tokens(
        db_session, sample_admin_user
    )

    assert access_token is not None
    assert refresh_token is not None
    assert expires_in == 15 * 60

    # Valida payload do access token
    access_payload = decode_token(access_token)
    assert access_payload["sub"] == str(sample_admin_user.id)
    assert access_payload["type"] == "access"
    assert access_payload["roles"] == ["ADMIN"]

    # Valida armazenamento no banco
    token_hash = hash_refresh_token(refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db_session.execute(stmt)
    db_token = result.scalar_one_or_none()

    assert db_token is not None
    assert db_token.user_id == sample_admin_user.id
    assert db_token.is_revoked is False


@pytest.mark.unit
async def test_refresh_token_rotation_success(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica rotação de refresh token com revogação do token anterior."""
    _, refresh_token_v1, _ = await auth_service.create_tokens(db_session, sample_admin_user)

    # Renova token
    new_access, refresh_token_v2, _ = await auth_service.refresh_tokens(
        db_session, refresh_token_v1
    )

    assert new_access is not None
    assert refresh_token_v2 != refresh_token_v1

    # Token v1 deve estar revogado
    h1 = hash_refresh_token(refresh_token_v1)
    db_t1 = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h1))
    ).scalar_one()
    assert db_t1.is_revoked is True

    # Token v2 deve estar ativo e na mesma família
    h2 = hash_refresh_token(refresh_token_v2)
    db_t2 = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h2))
    ).scalar_one()
    assert db_t2.is_revoked is False
    assert db_t2.family_id == db_t1.family_id


@pytest.mark.unit
async def test_refresh_token_replay_attack_revokes_entire_family(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """
    SEC-013: Detecção de Replay Attack.
    Reutilizar um refresh token já consumido revoga toda a família de tokens.
    """
    _, token_v1, _ = await auth_service.create_tokens(db_session, sample_admin_user)

    # Uso legítimo (rotação para v2)
    _, token_v2, _ = await auth_service.refresh_tokens(db_session, token_v1)

    # Tentativa de replay: reuso de token_v1
    with pytest.raises(AuthenticationError, match="Tentativa de reutilização de token detectada"):
        await auth_service.refresh_tokens(db_session, token_v1)

    # Ambas as versões devem estar agora revogadas
    h1 = hash_refresh_token(token_v1)
    h2 = hash_refresh_token(token_v2)

    db_t1 = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h1))
    ).scalar_one()
    db_t2 = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h2))
    ).scalar_one()

    assert db_t1.is_revoked is True
    assert db_t2.is_revoked is True


@pytest.mark.unit
async def test_refresh_token_expired(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica rejeição de refresh token vencido."""
    _, token_str, _ = await auth_service.create_tokens(db_session, sample_admin_user)

    # Força expiração no banco
    token_hash = hash_refresh_token(token_str)
    db_t = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one()
    db_t.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()

    with pytest.raises(AuthenticationError, match="Token de atualização expirado"):
        await auth_service.refresh_tokens(db_session, token_str)


@pytest.mark.unit
async def test_logout_revokes_family(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica que o logout invalida a família inteira de tokens."""
    _, token_str, _ = await auth_service.create_tokens(db_session, sample_admin_user)

    await auth_service.logout(db_session, token_str)

    token_hash = hash_refresh_token(token_str)
    db_t = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one()
    assert db_t.is_revoked is True


@pytest.mark.unit
async def test_password_reset_flow(
    db_session: AsyncSession,
    sample_admin_user: User,
) -> None:
    """Verifica fluxo completo de recuperação e alteração de senha."""
    old_hash = sample_admin_user.hashed_password

    # 1. Solicitação de recuperação
    with patch("app.tasks.email.send_password_reset_email.delay") as mock_email:
        await auth_service.request_password_reset(db_session, "admin@acme.com")
        mock_email.assert_called_once()
        _, args, _ = mock_email.mock_calls[0]
        reset_token = args[1]

    # 2. Confirmação com nova senha
    new_password = "BrandNewSecurePassword123!"
    await auth_service.reset_password(db_session, reset_token, new_password)

    await db_session.refresh(sample_admin_user)
    assert sample_admin_user.hashed_password != old_hash
    assert verify_password(new_password, sample_admin_user.hashed_password) is True

    # 3. Tentativa de reusar o mesmo token deve falhar
    with pytest.raises(AuthenticationError, match="já utilizado ou revogado"):
        await auth_service.reset_password(db_session, reset_token, "AnotherPass123!")
