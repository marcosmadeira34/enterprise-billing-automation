"""
EBA — Core Middlewares
Extração de contexto Multi-Tenant e injeção em ContextVars.
"""

from __future__ import annotations

import contextlib
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.security import decode_token
from app.core.tenant import set_current_tenant_id, set_current_user_id


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware que extrai o tenant_id e user_id do token JWT (Authorization Bearer)
    ou do header X-Tenant-ID (para chamadas inter-serviço/admin).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        auth_header = request.headers.get("Authorization")
        tenant_header = request.headers.get("X-Tenant-ID")

        tenant_id: UUID | None = None
        user_id: UUID | None = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            with contextlib.suppress(Exception):
                payload = decode_token(token)
                sub = payload.get("sub")
                t_id = payload.get("tenant_id")
                if sub:
                    user_id = UUID(str(sub))
                if t_id:
                    tenant_id = UUID(str(t_id))

        if not tenant_id and tenant_header:
            with contextlib.suppress(Exception):
                tenant_id = UUID(str(tenant_header))

        set_current_tenant_id(tenant_id)
        set_current_user_id(user_id)

        try:
            return await call_next(request)
        finally:
            set_current_tenant_id(None)
            set_current_user_id(None)
