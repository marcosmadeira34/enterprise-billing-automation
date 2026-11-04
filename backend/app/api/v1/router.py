"""
EBA — API Version 1 Router
Agregador principal de rotas da versão 1 da API.
"""

from __future__ import annotations

from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")


@api_v1_router.get("/status", tags=["Status"])
async def get_v1_status() -> dict[str, str]:
    """Retorna versão e integridade da API v1."""
    return {"api_version": "v1", "status": "active"}
