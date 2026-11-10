"""
Unit & Integration tests for Auth API Endpoints (/api/v1/auth/*).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.user import User


@pytest.mark.unit
async def test_api_login_success(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """Valida endpoint de login com retorno de tokens e cookie HttpOnly."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Password123!"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900

    # Cookie HttpOnly deve estar presente
    assert "refresh_token" in response.cookies


@pytest.mark.unit
async def test_api_login_invalid_credentials(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """Valida erro 401 para credenciais inválidas."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "WrongPassword999!"},
    )

    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHENTICATED"


@pytest.mark.unit
async def test_api_login_validation_error(async_client: AsyncClient) -> None:
    """Valida erro 422 para schema inválido."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.unit
async def test_api_refresh_token_via_body(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """Valida renovação de token enviando refresh_token pelo body."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Password123!"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert data["refresh_token"] != refresh_token


@pytest.mark.unit
async def test_api_refresh_token_via_cookie(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """Valida renovação de token lendo o cookie HttpOnly."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200

    # O cliente HTTP persistiu o cookie da resposta anterior
    refresh_resp = await async_client.post("/api/v1/auth/refresh")

    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


@pytest.mark.unit
async def test_api_logout(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """Valida logout e deleção de cookie."""
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200

    logout_resp = await async_client.post("/api/v1/auth/logout")

    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logout realizado com sucesso."


@pytest.mark.unit
async def test_api_get_me_authenticated(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """Valida recuperação do perfil do usuário com token Bearer."""
    token = create_access_token(
        subject=sample_admin_user.id,
        tenant_id=sample_admin_user.tenant_id,
        roles=[sample_admin_user.role],
    )

    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@acme.com"
    assert data["role"] == "ADMIN"
    assert data["tenant_id"] == str(sample_admin_user.tenant_id)


@pytest.mark.unit
async def test_api_get_me_unauthenticated(async_client: AsyncClient) -> None:
    """Rejeita requisição a /me sem cabeçalho Authorization."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHENTICATED"


@pytest.mark.unit
async def test_api_password_reset_flow(
    async_client: AsyncClient,
    sample_admin_user: User,
) -> None:
    """Valida fluxo de recuperação de senha pelos endpoints de API."""
    with patch("app.tasks.email.send_password_reset_email.delay") as mock_email:
        req_resp = await async_client.post(
            "/api/v1/auth/password/reset-request",
            json={"email": "admin@acme.com"},
        )
        assert req_resp.status_code == 200
        mock_email.assert_called_once()
        _, args, _ = mock_email.mock_calls[0]
        token = args[1]

    # Redefine a senha
    reset_resp = await async_client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": "CompletelyNewPassword123!"},
    )
    assert reset_resp.status_code == 200

    # Faz login com a nova senha
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "CompletelyNewPassword123!"},
    )
    assert login_resp.status_code == 200
