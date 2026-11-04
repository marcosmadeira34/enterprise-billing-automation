"""
Unit tests for Celery configuration and tasks.
"""

from __future__ import annotations

import pytest

from app.tasks.celery_app import celery_app, ping_task


@pytest.mark.unit
def test_celery_task_ping() -> None:
    """Verifica que a tarefa de ping do Celery executa com sucesso."""
    result = ping_task()
    assert result == "pong"


@pytest.mark.unit
def test_celery_config_queues() -> None:
    """Verifica mapeamento de filas configuradas no Celery."""
    routes = celery_app.conf.task_routes
    assert "app.tasks.critical.*" in routes
    assert routes["app.tasks.critical.*"]["queue"] == "critical"
    assert routes["app.tasks.billing.*"]["queue"] == "high"
