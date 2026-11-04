"""
Unit tests for security, password hashing, and JWT tokens.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.mark.unit
def test_password_hashing_and_verification() -> None:
    """Verifica que senhas são hashadas com Argon2id e validadas com sucesso."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.unit
def test_jwt_access_token_creation_and_decoding() -> None:
    """Valida geração e decodificação de Access Token."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    roles = ["ADMIN", "MANAGER"]

    token = create_access_token(
        subject=user_id,
        tenant_id=tenant_id,
        roles=roles,
    )

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["roles"] == roles
    assert payload["type"] == "access"


@pytest.mark.unit
def test_jwt_refresh_token_creation() -> None:
    """Valida geração de Refresh Token."""
    user_id = uuid.uuid4()
    token = create_refresh_token(subject=user_id)

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


@pytest.mark.unit
def test_jwt_expired_token_raises_error() -> None:
    """Valida que tokens expirados disparam AuthenticationError."""
    token = create_access_token(
        subject="user1",
        expires_delta=timedelta(seconds=-10),  # Já expirado
    )

    with pytest.raises(AuthenticationError, match="Token expirado"):
        decode_token(token)


@pytest.mark.unit
def test_jwt_invalid_token_raises_error() -> None:
    """Valida que tokens malformados disparam AuthenticationError."""
    with pytest.raises(AuthenticationError, match="Token inválido"):
        decode_token("invalid.token.signature")
