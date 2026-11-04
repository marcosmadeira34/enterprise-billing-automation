"""
Unit tests for the internal in-memory EventBus.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.core.events import BaseEvent, EventBus


@dataclass
class InvoiceCreatedEvent(BaseEvent):
    invoice_number: str = "INV-001"
    amount: float = 1500.0


@pytest.mark.unit
async def test_event_bus_publish_and_subscribe() -> None:
    """Verifica publicação e recebimento síncrono e assíncrono de eventos."""
    bus = EventBus()
    received_sync: list[InvoiceCreatedEvent] = []
    received_async: list[InvoiceCreatedEvent] = []

    def sync_handler(event: InvoiceCreatedEvent) -> None:
        received_sync.append(event)

    async def async_handler(event: InvoiceCreatedEvent) -> None:
        received_async.append(event)

    bus.subscribe(InvoiceCreatedEvent, sync_handler)
    bus.subscribe(InvoiceCreatedEvent, async_handler)

    test_event = InvoiceCreatedEvent(
        tenant_id=uuid.uuid4(),
        invoice_number="INV-2026-999",
        amount=2500.0,
    )

    await bus.publish(test_event)

    assert len(received_sync) == 1
    assert received_sync[0].invoice_number == "INV-2026-999"

    assert len(received_async) == 1
    assert received_async[0].amount == 2500.0

    # Teste de unsubscribe
    bus.unsubscribe(InvoiceCreatedEvent, sync_handler)
    await bus.publish(test_event)

    assert len(received_sync) == 1  # Não aumentou
    assert len(received_async) == 2  # Aumentou
