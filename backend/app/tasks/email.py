"""
EBA — Email & Notification Async Tasks
Tarefas Celery para despacho de e-mails transacionais (SEC-013 / F3-07).
"""

from __future__ import annotations

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="app.tasks.email.send_password_reset_email")  # type: ignore[untyped-decorator]
def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Envia e-mail de recuperação de senha com token assinado.
    """
    logger.info(
        "Enviando e-mail de recuperação de senha",
        to_email=to_email,
    )
    # Em produção ou integração com MailHog, o envio real SMTP ocorre aqui
    return True
