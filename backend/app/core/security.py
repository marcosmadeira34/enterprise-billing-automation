"""
EBA — Cryptography & Security Utilities
Hash de senhas com Argon2id e geração/validação de tokens JWT via PyJWT.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings
from app.core.exceptions import AuthenticationError

settings = get_settings()

# Hasher Argon2id padrão da indústria (recomendado OWASP)
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Gera hash seguro da senha com salt automático usando Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto claro corresponde ao hash Argon2id."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(
    subject: str | UUID,
    tenant_id: UUID | None = None,
    roles: list[str] | None = None,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Gera Access Token JWT de curta duração."""
    now = datetime.now(UTC)
    delta = expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire = now + delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
        "tenant_id": str(tenant_id) if tenant_id else None,
        "roles": roles or [],
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    subject: str | UUID,
    tenant_id: UUID | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Gera Refresh Token JWT de longa duração para renovação de sessões."""
    now = datetime.now(UTC)
    delta = expires_delta or timedelta(days=settings.jwt_refresh_token_expire_days)
    expire = now + delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
        "tenant_id": str(tenant_id) if tenant_id else None,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica e valida assinatura e expiração do token JWT."""
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as err:
        raise AuthenticationError("Token expirado.") from err
    except jwt.InvalidTokenError as err:
        raise AuthenticationError("Token inválido ou forjado.") from err
