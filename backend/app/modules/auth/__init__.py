"""
EBA — Authentication & Session Management Module
"""

from app.modules.auth.router import router
from app.modules.auth.schemas import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.modules.auth.service import AuthService, auth_service

__all__ = [
    "router",
    "AuthService",
    "auth_service",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "UserProfileResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "MessageResponse",
]
