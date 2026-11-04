"""
EBA — Internal In-Memory EventBus
Desacoplamento de domínios no Modular Monolith via publicação e assinatura de eventos internos.
"""

from __future__ import annotations

import inspect
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

import structlog

from app.models.base import utc_now

logger = structlog.get_logger(__name__)


@dataclass
class BaseEvent:
    """Evento base do domínio."""

    tenant_id: UUID | None = None
    event_id: UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=utc_now)


EventType = TypeVar("EventType", bound=BaseEvent)
EventHandler = Callable[[Any], Awaitable[None] | None]


class EventBus:
    """Barramento de eventos síncrono e assíncrono em memória."""

    def __init__(self) -> None:
        self._handlers: dict[type[BaseEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_cls: type[EventType], handler: EventHandler) -> None:
        """Registra um handler para um tipo específico de evento."""
        self._handlers[event_cls].append(handler)
        logger.debug(
            "Event handler subscribed",
            event_type=event_cls.__name__,
            handler=getattr(handler, "__name__", str(handler)),
        )

    def unsubscribe(self, event_cls: type[EventType], handler: EventHandler) -> None:
        """Remove um handler registrado."""
        if handler in self._handlers[event_cls]:
            self._handlers[event_cls].remove(handler)

    async def publish(self, event: BaseEvent) -> None:
        """Publica um evento e notifica todos os subscribers registrados."""
        event_cls = type(event)
        handlers = self._handlers.get(event_cls, [])

        logger.info(
            "Publishing internal event",
            event_name=event_cls.__name__,
            event_id=str(event.event_id),
            handlers_count=len(handlers),
        )

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error(
                    "Error executing event handler",
                    event_name=event_cls.__name__,
                    handler=getattr(handler, "__name__", str(handler)),
                    error=str(exc),
                )
                # Não interrompe a execução dos demais handlers


# Singleton global do barramento
event_bus = EventBus()
