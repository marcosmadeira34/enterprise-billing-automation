"""
Unit tests for repository pattern and soft delete filtering.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import EntityNotFoundError
from app.core.repository import BaseRepository
from app.core.tenant import set_current_tenant_id
from app.core.unit_of_work import AsyncUnitOfWork
from app.models.base import BaseModel


class DummyEntity(BaseModel):
    """Entidade dummy para validação do repositório."""

    __tablename__ = "dummy_entities"


@pytest.mark.unit
async def test_repository_get_by_id_found() -> None:
    """Verifica busca bem-sucedida de entidade existente."""
    mock_session = AsyncMock()
    mock_entity = DummyEntity()
    mock_entity.id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_entity
    mock_session.execute.return_value = mock_result

    repo = BaseRepository(DummyEntity, mock_session)
    result = await repo.get_by_id(mock_entity.id)

    assert result == mock_entity


@pytest.mark.unit
async def test_repository_get_by_id_or_fail() -> None:
    """Verifica levantamento de exceção para entidade inexistente."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    repo = BaseRepository(DummyEntity, mock_session)
    missing_id = uuid.uuid4()

    with pytest.raises(EntityNotFoundError):
        await repo.get_by_id_or_fail(missing_id)


@pytest.mark.unit
async def test_repository_create_sets_tenant() -> None:
    """Verifica que create associa automaticamente o tenant_id ativo."""
    active_tenant = uuid.uuid4()
    set_current_tenant_id(active_tenant)

    mock_session = AsyncMock()
    repo = BaseRepository(DummyEntity, mock_session)

    entity = DummyEntity()
    created = await repo.create(entity)

    assert created.tenant_id == active_tenant
    mock_session.add.assert_called_once_with(entity)
    set_current_tenant_id(None)


@pytest.mark.unit
async def test_unit_of_work_commit_and_rollback() -> None:
    """Verifica ciclo de vida do Unit of Work."""
    mock_session = AsyncMock()
    mock_session_factory = MagicMock(return_value=mock_session)

    # Caso de sucesso: deve chamar commit
    async with AsyncUnitOfWork(session_factory=mock_session_factory) as uow:
        assert uow.session == mock_session

    mock_session.commit.assert_called_once()
    mock_session.close.assert_called_once()

    # Caso de erro: deve chamar rollback
    mock_session_fail = AsyncMock()
    mock_factory_fail = MagicMock(return_value=mock_session_fail)

    with pytest.raises(ValueError, match="Erro simulado"):
        async with AsyncUnitOfWork(session_factory=mock_factory_fail):
            raise ValueError("Erro simulado")

    mock_session_fail.rollback.assert_called_once()
    mock_session_fail.close.assert_called_once()
