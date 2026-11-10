"""
EBA — User & RBAC Models
Gerenciamento de identidades, credenciais e perfis de acesso.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GlobalBaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.token import RefreshToken


class UserRole(StrEnum):
    """Níveis de acesso baseados em função (RBAC)."""

    SUPERADMIN = "SUPERADMIN"  # Acesso global à plataforma (cross-tenant)
    ADMIN = "ADMIN"  # Administrador da empresa/tenant
    MANAGER = "MANAGER"  # Gestor de faturamento e aprovações
    OPERATOR = "OPERATOR"  # Operador de emissão e cobrança
    VIEWER = "VIEWER"  # Consulta e relatórios


class User(GlobalBaseModel):
    """
    Usuário do sistema.
    Pode estar associado a um tenant (empresa) específico ou ser global (Superadmin).
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default=UserRole.VIEWER.value, nullable=False)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    company: Mapped[Company | None] = relationship("Company", back_populates="users")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
