"""
EBA — Company (Tenant) Model
Representa a empresa contratante / tenant no ecossistema EBA.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GlobalBaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Company(GlobalBaseModel):
    """
    Empresa / Tenant cadastrado na plataforma.
    Cada empresa possui seu próprio isolamento de dados.
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cnpj: Mapped[str] = mapped_column(String(18), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    users: Mapped[list[User]] = relationship("User", back_populates="company")
