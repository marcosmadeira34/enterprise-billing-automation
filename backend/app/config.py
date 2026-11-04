"""
EBA — Application Configuration
Centraliza todas as configurações via Pydantic BaseSettings.
Valores são carregados de variáveis de ambiente ou do arquivo .env.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Any

from pydantic import (
    BeforeValidator,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogFormat(StrEnum):
    CONSOLE = "console"
    JSON = "json"


def _parse_cors_origins(v: Any) -> list[str]:
    """Parse ALLOWED_ORIGINS de string CSV para lista."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    return []


class Settings(BaseSettings):
    """
    Configurações da aplicação EBA.

    Todas as variáveis são carregadas do ambiente ou do arquivo .env.
    Variáveis sem valor padrão são obrigatórias — a aplicação falha no
    startup se estiverem ausentes.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Aplicação
    # -------------------------------------------------------------------------
    app_env: Environment = Environment.DEVELOPMENT
    app_name: str = "Enterprise Billing Automation"
    app_version: str = "0.1.0"
    app_debug: bool = False
    app_host: str = "0.0.0.0"  # nosec B104
    app_port: int = 8000

    # SECRET_KEY — obrigatório, mínimo 32 caracteres
    secret_key: str

    # -------------------------------------------------------------------------
    # JWT
    # -------------------------------------------------------------------------
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "eba_dev"
    postgres_user: str = "eba_user"
    postgres_password: str

    # URL assíncrona (asyncpg) — construída automaticamente se não definida
    database_url: str | None = None

    # URL de teste — usada apenas quando app_env == TESTING
    test_database_url: str | None = None

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str
    redis_db: int = 0

    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # -------------------------------------------------------------------------
    # MinIO
    # -------------------------------------------------------------------------
    minio_endpoint: str = "minio:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket_documents: str = "eba-documents"
    minio_secure: bool = False
    minio_presigned_url_expire_seconds: int = 900

    # -------------------------------------------------------------------------
    # Email
    # -------------------------------------------------------------------------
    mail_server: str = "mailhog"
    mail_port: int = 1025
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@eba.local"
    mail_from_name: str = "EBA Platform"
    mail_tls: bool = False
    mail_ssl: bool = False

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    allowed_origins: Annotated[list[str], BeforeValidator(_parse_cors_origins)] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_default: str = "100/minute"

    # -------------------------------------------------------------------------
    # Sentry
    # -------------------------------------------------------------------------
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.CONSOLE

    # -------------------------------------------------------------------------
    # Celery Workers
    # -------------------------------------------------------------------------
    celery_worker_concurrency: int = 4
    celery_task_always_eager: bool = False

    # -------------------------------------------------------------------------
    # Bootstrap
    # -------------------------------------------------------------------------
    bootstrap_admin_email: str = "admin@eba.local"
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "EBA Administrator"

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    feature_audit_log: bool = True
    feature_rate_limiting: bool = True
    feature_sentry: bool = False

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("secret_key", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Valida que SECRET_KEY tem entropia suficiente.
        Falha no startup se o valor for fraco ou padrão.
        """
        weak_values = {
            "secret",
            "changeme",
            "password",
            "12345678",
            "change_me",
            "CHANGE_ME",
            "CHANGE_ME_generate_with_secrets_token_hex_32_chars_minimum",
        }
        if not v or v in weak_values:
            msg = (
                "SECRET_KEY é inválido ou usa o valor padrão. "
                'Gere um com: python -c "import secrets; print(secrets.token_hex(32))"'
            )
            raise ValueError(msg)
        if len(v) < 32:
            msg = f"SECRET_KEY muito curto ({len(v)} chars). Mínimo: 32 caracteres."
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def build_computed_urls(self) -> Settings:
        """Constrói URLs compostas a partir das variáveis individuais."""
        # Database URL
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

        # Celery Broker URL
        if not self.celery_broker_url:
            self.celery_broker_url = (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
            )

        # Celery Result Backend
        if not self.celery_result_backend:
            self.celery_result_backend = (
                f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/1"
            )

        return self

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.app_env == Environment.TESTING

    @property
    def effective_database_url(self) -> str:
        """Retorna a URL do banco correta para o ambiente."""
        if self.is_testing and self.test_database_url:
            return self.test_database_url
        return self.database_url or ""

    @property
    def sync_database_url(self) -> str:
        """URL síncrona para uso com Alembic (psycopg2)."""
        url = self.effective_database_url
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@lru_cache
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.
    Usa @lru_cache para evitar releitura do .env a cada chamada.
    Para sobrescrever em testes: use dependency override ou limpe o cache.
    """
    return Settings()  # type: ignore[call-arg]
