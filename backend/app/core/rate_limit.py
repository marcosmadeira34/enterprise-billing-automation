"""
EBA — Rate Limiting Configuration
Proteção contra ataques de força bruta e abusos de API usando slowapi (SEC-007).
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter padrão com base no IP do cliente
limiter = Limiter(key_func=get_remote_address)
