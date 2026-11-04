"""
EBA — Base Models & Mixins
Padrão declarativo SQLAlchemy 2.x com suporte nativo a UUID, Multi-Tenancy e Soft-Delete.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


def utc_now() -> datetime:
    """Retorna datetime UTC consciente."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Classe base declarativa para todos os modelos SQLAlchemy 2.x."""

    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Gera automaticamente o nome da tabela em plural snake_case."""
        name = cls.__name__.lower()
        if not name.endswith("s"):
            return f"{name}s"
        return name


class TimestampMixin:
    """Mixin com timestamps de criação e atualização em UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class TenantMixin:
    """Mixin para isolamento de dados por Tenant (Empresa)."""

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            Uuid(as_uuid=True),
            nullable=False,
            index=True,
        )


class SoftDeleteMixin:
    """Mixin para exclusão lógica (soft delete)."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


class BaseModel(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """
    Modelo base abstrato para entidades de domínio com isolamento multi-tenant.
    Possui chave primária UUID v4, timestamps, tenant_id e soft-delete.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class GlobalBaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Modelo base abstrato para entidades globais do sistema (não vinculadas a um tenant específico).
    Exemplo: Superadministradores da plataforma e Catálogo de Tenants.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
