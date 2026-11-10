"""
EBA — Custom Exceptions & Error Handlers
Padronização de respostas de erro e hierarquia de exceções de domínio.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = structlog.get_logger(__name__)


class AppException(Exception):
    """Exceção base da aplicação."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class EntityNotFoundError(AppException):
    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} '{identifier}' não encontrado(a).",
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class EntityAlreadyExistsError(AppException):
    def __init__(self, entity_name: str, identifier: Any) -> None:
        super().__init__(
            message=f"{entity_name} '{identifier}' já existe no sistema.",
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Credenciais inválidas ou token expirado.") -> None:
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Acesso negado para esta operação.") -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class TenantIsolationError(AppException):
    def __init__(
        self,
        message: str = "Tentativa de acesso não autorizado a recurso de outro tenant.",
    ) -> None:
        super().__init__(
            message=message,
            code="TENANT_VIOLATION",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class BusinessRuleViolationError(AppException):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message=message,
            code="BUSINESS_RULE_VIOLATION",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra tratadores de erro globais no FastAPI."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application error caught",
            error_code=exc.code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Dados de entrada inválidos.",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        logger.warning(
            "Rate limit exceeded",
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": f"Limite de requisições excedido: {exc.detail}",
                "details": None,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled server exception",
            exc_info=exc,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Ocorreu um erro interno no servidor.",
            },
        )
