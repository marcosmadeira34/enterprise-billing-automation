"""
EBA — Auth API Router
Rotas de autenticação, rotação de tokens, logout, perfil do usuário e recuperação de senhas.
"""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db_session
from app.core.exceptions import AuthenticationError
from app.core.permissions import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.modules.auth.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.modules.auth.service import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])
settings = get_settings()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login de usuário e emissão de tokens",
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Autentica usuário com e-mail e senha.
    Retorna access token e armazena refresh token em cookie HttpOnly seguro (SEC-001, SEC-013).
    """
    user = await auth_service.authenticate(session, payload.email, payload.password)
    access_token, refresh_token, expires_in = await auth_service.create_tokens(session, user)

    # Armazena refresh token em cookie seguro HttpOnly
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",  # noqa: S106 # nosec B106
        expires_in=expires_in,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovação de Access Token via Refresh Token com rotação",
)
async def refresh_token(
    response: Response,
    payload: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias="refresh_token"),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Renova sessão com rotação de refresh token e detecção de replay attack (SEC-013).
    Aceita o token via corpo da requisição ou cookie HttpOnly.
    """
    body_token = payload.refresh_token if payload else None
    token_str = body_token or cookie_token

    if not token_str:
        raise AuthenticationError("Token de atualização não informado.")

    access_token, new_refresh_token, expires_in = await auth_service.refresh_tokens(
        session, token_str
    )

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",  # noqa: S106 # nosec B106
        expires_in=expires_in,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Encerramento de sessão e revogação da família de tokens",
)
async def logout(
    response: Response,
    payload: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias="refresh_token"),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Encerra a sessão do usuário e revoga a família inteira de refresh tokens (SEC-013).
    """
    body_token = payload.refresh_token if payload else None
    token_str = body_token or cookie_token
    await auth_service.logout(session, token_str)

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return MessageResponse(message="Logout realizado com sucesso.")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Dados do perfil do usuário autenticado",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    """Retorna os dados do perfil do usuário atualmente autenticado."""
    return UserProfileResponse.model_validate(current_user)


@router.post(
    "/password/reset-request",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Solicitação de recuperação de senha por e-mail",
)
async def request_password_reset(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Gera token assinado e envia e-mail com link de recuperação.
    Protegido contra enumeração de usuários.
    """
    await auth_service.request_password_reset(session, payload.email)
    return MessageResponse(
        message="Se o e-mail estiver cadastrado, as instruções de recuperação foram enviadas."
    )


@router.post(
    "/password/reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Redefinição de senha com token assinado",
)
async def reset_password(
    payload: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Valida token, redefine a senha com Argon2id e encerra todas as sessões anteriores.
    """
    await auth_service.reset_password(session, payload.token, payload.new_password)
    return MessageResponse(message="Senha redefinida com sucesso. Faça login novamente.")
