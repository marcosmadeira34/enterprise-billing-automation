"""
Unit tests for Auth Models (User, Company, RefreshToken).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.token import RefreshToken
from app.models.user import User, UserRole


@pytest.mark.unit
async def test_user_and_company_relationship(db_session: AsyncSession) -> None:
    """Valida integridade do modelo User associado a Company."""
    company = Company(
        id=uuid.uuid4(),
        name="Tech Solutions Ltda",
        trade_name="TechSol",
        cnpj="98765432000188",
        email="contato@techsol.com",
        is_active=True,
    )
    db_session.add(company)
    await db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email="dev@techsol.com",
        hashed_password="argon2_hashed_dummy_string",
        full_name="Tech Developer",
        role=UserRole.MANAGER.value,
        tenant_id=company.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    await db_session.refresh(user)
    assert user.role == "MANAGER"
    assert user.tenant_id == company.id
    assert user.is_active is True
    assert user.is_deleted is False


@pytest.mark.unit
async def test_refresh_token_lifecycle(db_session: AsyncSession, sample_viewer_user: User) -> None:
    """Valida integridade do modelo RefreshToken e rastreamento de família."""
    family = uuid.uuid4()
    token = RefreshToken(
        id=uuid.uuid4(),
        user_id=sample_viewer_user.id,
        token_hash="fake_hash_1234567890abcdef",
        family_id=family,
        expires_at=datetime.now(UTC),
        is_revoked=False,
    )
    db_session.add(token)
    await db_session.commit()
    await db_session.refresh(token)

    assert token.user_id == sample_viewer_user.id
    assert token.family_id == family
    assert token.is_revoked is False
