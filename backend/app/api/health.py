"""
EBA — Health Check Endpoints
Liveness and Readiness probes para Docker Compose e Orquestradores.
"""

from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Informa se a aplicação FastAPI está executando.",
)
async def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "eba-api"}


@router.get(
    "/ready",
    summary="Readiness Probe",
    description="Verifica conectividade com banco de dados e redis.",
)
async def readiness() -> JSONResponse:
    settings = get_settings()
    checks: dict[str, str] = {}
    is_healthy = True

    # 1. Checagem PostgreSQL
    try:
        test_engine = create_async_engine(
            settings.effective_database_url,
            pool_pre_ping=True,
            connect_args={"timeout": 3},
        )
        async with test_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await test_engine.dispose()
        checks["database"] = "healthy"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"unhealthy: {exc!s}"
        is_healthy = False

    # 2. Checagem Redis
    try:
        r = aioredis.from_url(
            f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
            socket_timeout=2.0,
        )
        await r.ping()
        await r.aclose()
        checks["redis"] = "healthy"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"unhealthy: {exc!s}"
        is_healthy = False

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_healthy else "degraded",
            "checks": checks,
        },
    )
