"""
EBA — Enterprise Billing Automation
Main Application Factory & Lifespan Handler.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.config import Settings, get_settings
from app.core.logging import setup_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia ciclo de vida da aplicação (startup e shutdown)."""
    settings = get_settings()
    setup_logging(settings)
    logger.info(
        "Application starting up",
        app_name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )
    yield
    logger.info("Application shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory para o backend FastAPI."""
    current_settings = settings or get_settings()

    app = FastAPI(
        title=current_settings.app_name,
        version=current_settings.app_version,
        description="Plataforma corporativa de automação de faturamento e contratos.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Middleware de CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=current_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Middleware de Correlation / Request ID
    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=req_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # 3. Registro de Rotas
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
