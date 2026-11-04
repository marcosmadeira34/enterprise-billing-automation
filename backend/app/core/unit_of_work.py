"""
EBA — Unit of Work Pattern
Gerenciamento atômico de transações entre múltiplos repositórios e serviços.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory

logger = structlog.get_logger(__name__)


class AsyncUnitOfWork:
    """
    Context manager assíncrono para Unit of Work.
    Garante que todas as mutações no banco ocorram em uma única transação atômica.
    Em caso de exceção, executa rollback automático.
    """

    def __init__(self, session_factory: Any = None) -> None:
        self.session_factory = session_factory or async_session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self.session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if not self.session:
            return

        if exc_type is not None:
            logger.warning(
                "Transaction rolled back due to error",
                error_type=exc_type.__name__,
                error=str(exc_val),
            )
            await self.rollback()
        else:
            try:
                await self.commit()
            except Exception:
                await self.rollback()
                raise
        await self.session.close()

    async def commit(self) -> None:
        """Confirma a transação atual."""
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        """Reverte a transação atual."""
        if self.session:
            await self.session.rollback()
