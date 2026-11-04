"""
EBA — Generic Async Repository Pattern
Implementação base para persistência com isolamento automático por Tenant e Soft-Delete.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.core.tenant import get_current_tenant_id
from app.models.base import Base, utc_now

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Repositório genérico assíncrono.
    Aplica filtros de tenant_id e soft-delete de forma transparente.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    def _apply_tenant_filter(self, query: Any) -> Any:
        """Aplica filtro de tenant se o modelo possuir tenant_id e houver tenant ativo."""
        if hasattr(self.model, "tenant_id"):
            tenant_id = get_current_tenant_id()
            if tenant_id:
                query = query.where(getattr(self.model, "tenant_id") == tenant_id)
        return query

    def _apply_soft_delete_filter(self, query: Any, include_deleted: bool = False) -> Any:
        """Aplica filtro para excluir registros soft-deleted por padrão."""
        if hasattr(self.model, "is_deleted") and not include_deleted:
            query = query.where(getattr(self.model, "is_deleted") == False)  # noqa: E712
        return query

    async def get_by_id(
        self,
        id: UUID,
        include_deleted: bool = False,
    ) -> ModelType | None:
        """Busca entidade por ID respeitando tenant e soft-delete."""
        query = select(self.model).where(getattr(self.model, "id") == id)
        query = self._apply_tenant_filter(query)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_id_or_fail(
        self,
        id: UUID,
        include_deleted: bool = False,
    ) -> ModelType:
        """Busca entidade por ID ou levanta EntityNotFoundError."""
        entity = await self.get_by_id(id, include_deleted=include_deleted)
        if not entity:
            raise EntityNotFoundError(self.model.__name__, id)
        return entity

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> Sequence[ModelType]:
        """Lista entidades com paginação, filtro de tenant e exclusão lógica."""
        query = select(self.model).offset(skip).limit(limit)
        query = self._apply_tenant_filter(query)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        if hasattr(self.model, "created_at"):
            query = query.order_by(getattr(self.model, "created_at").desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, include_deleted: bool = False) -> int:
        """Retorna contagem total de registros para o tenant atual."""
        query = select(func.count()).select_from(self.model)
        query = self._apply_tenant_filter(query)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, entity: ModelType) -> ModelType:
        """Adiciona e persiste nova entidade associando o tenant_id ativo se aplicável."""
        if hasattr(entity, "tenant_id") and getattr(entity, "tenant_id", None) is None:
            active_tenant = get_current_tenant_id()
            if active_tenant:
                setattr(entity, "tenant_id", active_tenant)

        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Atualiza entidade e atualiza timestamp de modificação."""
        if hasattr(entity, "updated_at"):
            setattr(entity, "updated_at", utc_now())
        await self.session.flush()
        return entity

    async def soft_delete(self, id: UUID) -> bool:
        """Executa exclusão lógica alterando flag is_deleted e deleted_at."""
        entity = await self.get_by_id(id)
        if not entity:
            return False

        if hasattr(entity, "is_deleted"):
            setattr(entity, "is_deleted", True)
            setattr(entity, "deleted_at", utc_now())
            await self.session.flush()
            return True

        await self.session.delete(entity)
        await self.session.flush()
        return True
