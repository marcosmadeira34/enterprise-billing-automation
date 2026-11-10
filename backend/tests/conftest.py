"""
EBA — Pytest Configuration & Fixtures
Configuração de ambiente isolado em memória (SQLite async) para testes unitários e de integração.
"""

from __future__ import annotations

import os

# Define variáveis de ambiente antes de qualquer import de app.*
os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "super_secure_test_secret_key_minimum_32_characters_123"
os.environ["POSTGRES_PASSWORD"] = "test_postgres_pass"
os.environ["REDIS_PASSWORD"] = "test_redis_pass"
os.environ["MINIO_ACCESS_KEY"] = "test_minio_key"
os.environ["MINIO_SECRET_KEY"] = "test_minio_secret"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

import uuid  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402, F401
from app.config import Settings, get_settings  # noqa: E402
from app.core.database import get_db_session  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    """Reseta contador de rate limiting antes de cada teste."""
    limiter.reset()


@pytest.fixture
def test_settings() -> Settings:
    """Fixture com configurações limpas de teste."""
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Engine SQLite assíncrono em memória para testes."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Sessão assíncrona do banco em memória para testes unitários e de integração."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def test_app(test_settings: Settings, db_session: AsyncSession) -> FastAPI:
    """Aplicação FastAPI com override do gerador de sessão para o banco de teste."""
    app_instance = create_app(test_settings)

    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app_instance.dependency_overrides[get_db_session] = _get_test_session
    return app_instance


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP assíncrono para testes de endpoints da API."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def sample_company(db_session: AsyncSession) -> Company:
    """Cria uma empresa/tenant de teste."""
    company = Company(
        id=uuid.uuid4(),
        name="Acme Corp Test",
        trade_name="Acme",
        cnpj="12345678000199",
        email="contact@acme.com",
        phone="+551199999999",
        is_active=True,
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


@pytest.fixture
async def sample_admin_user(db_session: AsyncSession, sample_company: Company) -> User:
    """Cria um usuário ADMIN associado ao tenant de teste."""
    user = User(
        id=uuid.uuid4(),
        email="admin@acme.com",
        hashed_password=hash_password("Password123!"),
        full_name="Admin Test User",
        role=UserRole.ADMIN.value,
        tenant_id=sample_company.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_viewer_user(db_session: AsyncSession, sample_company: Company) -> User:
    """Cria um usuário VIEWER associado ao tenant de teste."""
    user = User(
        id=uuid.uuid4(),
        email="viewer@acme.com",
        hashed_password=hash_password("Password123!"),
        full_name="Viewer Test User",
        role=UserRole.VIEWER.value,
        tenant_id=sample_company.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_superadmin_user(db_session: AsyncSession) -> User:
    """Cria um SUPERADMIN global (sem vínculo de tenant)."""
    user = User(
        id=uuid.uuid4(),
        email="superadmin@eba.com",
        hashed_password=hash_password("SuperSecret123!"),
        full_name="Global Superadmin",
        role=UserRole.SUPERADMIN.value,
        tenant_id=None,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
