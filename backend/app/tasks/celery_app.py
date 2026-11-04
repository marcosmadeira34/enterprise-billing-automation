"""
EBA — Celery Application Definition
Configuração do Celery com Redis broker e filas segmentadas.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "eba_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.celery_task_always_eager,
    task_routes={
        "app.tasks.critical.*": {"queue": "critical"},
        "app.tasks.billing.*": {"queue": "high"},
        "app.tasks.email.*": {"queue": "default"},
        "app.tasks.reports.*": {"queue": "low"},
    },
)


@celery_app.task(name="app.tasks.ping")  # type: ignore[untyped-decorator]
def ping_task() -> str:
    """Tarefa de verificação de sanidade dos workers."""
    return "pong"
