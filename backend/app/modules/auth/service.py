"""
EBA — Auth Service
Lógica de negócio de autenticação, rotação segura de tokens com detecção de replay,
encerramento de sessão e ciclo de vida de senhas.
"""

from __future__ import annotations

import contextlib
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.base import utc_now
from app.models.token import RefreshToken
from app.models.user import User
from app.tasks.email import send_password_reset_email

settings = get_settings()


def ensure_utc(dt: datetime) -> datetime:
    """Garante que o objeto datetime possua timezone UTC (compatibilidade SQLite)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def hash_refresh_token(token: str) -> str:
    """Gera hash SHA-256 seguro do refresh token para armazenamento no banco (SEC-013)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    """Serviço de gerenciamento de autenticação e sessões."""

    async def authenticate(
        self,
        session: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        """Autentica usuário por e-mail e senha com Argon2id."""
        stmt = select(User).where(User.email == email.lower(), User.is_deleted.is_(False))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("E-mail ou senha incorretos.")

        if not user.is_active:
            raise AuthenticationError("Conta de usuário desativada.")

        user.last_login_at = utc_now()
        await session.commit()
        return user

    async def create_tokens(
        self,
        session: AsyncSession,
        user: User,
        family_id: uuid.UUID | None = None,
    ) -> tuple[str, str, int]:
        """
        Emite um par de Access Token + Refresh Token.
        Registra o hash do Refresh Token com identificador de família (SEC-013).
        """
        access_token = create_access_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            roles=[user.role],
        )

        refresh_token = create_refresh_token(
            subject=user.id,
            tenant_id=user.tenant_id,
        )

        token_family = family_id or uuid.uuid4()
        token_hash = hash_refresh_token(refresh_token)
        expires_at = utc_now() + timedelta(days=settings.jwt_refresh_token_expire_days)

        db_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            family_id=token_family,
            expires_at=expires_at,
            is_revoked=False,
        )
        session.add(db_token)
        await session.commit()

        expires_in = settings.jwt_access_token_expire_minutes * 60
        return access_token, refresh_token, expires_in

    async def refresh_tokens(
        self,
        session: AsyncSession,
        refresh_token_str: str,
    ) -> tuple[str, str, int]:
        """
        Renova tokens com rotação estrita e detecção de replay attack (SEC-013).
        Se um token já revogado for reutilizado, toda a família de tokens é invalidada.
        """
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise AuthenticationError("Tipo de token inválido para renovação.")

        token_hash = hash_refresh_token(refresh_token_str)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await session.execute(stmt)
        db_token = result.scalar_one_or_none()

        if db_token is None:
            raise AuthenticationError("Token de atualização não encontrado.")

        # Replay Attack detectado: token já foi revogado anteriormente
        if db_token.is_revoked:
            revoke_stmt = (
                update(RefreshToken)
                .where(RefreshToken.family_id == db_token.family_id)
                .values(is_revoked=True)
            )
            await session.execute(revoke_stmt)
            await session.commit()
            raise AuthenticationError(
                "Tentativa de reutilização de token detectada. Sessão revogada por segurança."
            )

        if ensure_utc(db_token.expires_at) < utc_now():
            raise AuthenticationError("Token de atualização expirado.")

        # Revoga o token atual
        db_token.is_revoked = True

        # Busca usuário atual
        user_stmt = select(User).where(User.id == db_token.user_id, User.is_deleted.is_(False))
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if user is None or not user.is_active:
            await session.commit()
            raise AuthenticationError("Usuário associado ao token inativo ou removido.")

        # Emite novo par mantendo a mesma família
        return await self.create_tokens(session, user, family_id=db_token.family_id)

    async def logout(
        self,
        session: AsyncSession,
        refresh_token_str: str | None,
    ) -> None:
        """Invalida a família inteira de tokens do refresh token apresentado (SEC-013)."""
        if not refresh_token_str:
            return

        with contextlib.suppress(Exception):
            token_hash = hash_refresh_token(refresh_token_str)
            stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            result = await session.execute(stmt)
            db_token = result.scalar_one_or_none()
            if db_token:
                revoke_stmt = (
                    update(RefreshToken)
                    .where(RefreshToken.family_id == db_token.family_id)
                    .values(is_revoked=True)
                )
                await session.execute(revoke_stmt)
                await session.commit()

    async def request_password_reset(
        self,
        session: AsyncSession,
        email: str,
    ) -> None:
        """
        Inicia fluxo de recuperação de senha gerando token assinado.
        Sempre retorna sucesso mesmo se e-mail não existir (anti-enumeração).
        """
        stmt = select(User).where(User.email == email.lower(), User.is_deleted.is_(False))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is not None and user.is_active:
            fingerprint = hashlib.sha256(user.hashed_password.encode("utf-8")).hexdigest()[:16]
            reset_token = create_access_token(
                subject=user.id,
                expires_delta=timedelta(hours=1),
                extra_claims={
                    "type": "password_reset",
                    "pwhash_prefix": fingerprint,
                },
            )
            send_password_reset_email.delay(user.email, reset_token)

    async def reset_password(
        self,
        session: AsyncSession,
        token: str,
        new_password: str,
    ) -> None:
        """
        Valida token de recuperação, altera a senha e invalida todas as sessões anteriores.
        """
        payload = decode_token(token)
        if payload.get("type") != "password_reset":
            raise AuthenticationError("Token inválido para redefinição de senha.")

        user_id_raw = payload.get("sub")
        if not user_id_raw:
            raise AuthenticationError("Token de recuperação malformado.")

        try:
            user_uuid = UUID(str(user_id_raw))
        except ValueError as err:
            raise AuthenticationError("Identificador de usuário inválido no token.") from err

        stmt = select(User).where(User.id == user_uuid, User.is_deleted.is_(False))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise AuthenticationError("Usuário inválido ou inativo.")

        # Invalidação por modificação da senha (token foi gerado com prefixo do hash antigo)
        current_fingerprint = hashlib.sha256(user.hashed_password.encode("utf-8")).hexdigest()[:16]
        if payload.get("pwhash_prefix") != current_fingerprint:
            raise AuthenticationError("Token de recuperação já utilizado ou revogado.")

        user.hashed_password = hash_password(new_password)

        # Invalida todas as sessões e tokens ativos do usuário
        revoke_all_stmt = (
            update(RefreshToken).where(RefreshToken.user_id == user.id).values(is_revoked=True)
        )
        await session.execute(revoke_all_stmt)
        await session.commit()


auth_service = AuthService()
