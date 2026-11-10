"""
EBA — Auth Schemas & DTOs
Modelos Pydantic para requisições e respostas de autenticação e controle de sessão.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload para autenticação com credenciais."""

    email: EmailStr = Field(..., description="E-mail do usuário cadastrado")
    password: str = Field(..., min_length=8, description="Senha em texto claro")


class TokenResponse(BaseModel):
    """Resposta com tokens de acesso e renovação."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int = Field(..., description="Tempo de vida do access token em segundos")


class RefreshRequest(BaseModel):
    """Payload para rotação de refresh token."""

    refresh_token: str | None = Field(
        default=None,
        description="Refresh token (opcional se fornecido via cookie HttpOnly)",
    )


class UserProfileResponse(BaseModel):
    """Dados de perfil do usuário autenticado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    tenant_id: uuid.UUID | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class PasswordResetRequest(BaseModel):
    """Solicitação de recuperação de senha por e-mail."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirmação de alteração de senha com token assinado."""

    token: str = Field(..., description="Token de recuperação recebido por e-mail")
    new_password: str = Field(..., min_length=8, description="Nova senha do usuário")


class MessageResponse(BaseModel):
    """Resposta padrão com mensagem informativa."""

    message: str
