# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Shared API authentication module.

Provides API key validation for all RRA API endpoints.

Security:
- Uses constant-time comparison to prevent timing attacks
- Supports multiple valid API keys via environment variable
- Cryptographically secure session ID generation
"""

import os
import hmac
import secrets
from typing import Optional
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader


# API Key configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Session configuration
SESSION_ID_LENGTH = 32  # bytes
SESSION_EXPIRY_HOURS = 24


@dataclass
class SessionData:
    """Session data structure."""

    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) - self.last_activity > timedelta(hours=SESSION_EXPIRY_HOURS)

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)


def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> bool:
    """
    Verify API key from request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        True if API key is valid

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    # Get valid API keys from environment
    # Supports comma-separated list for key rotation
    api_keys_env = os.environ.get("RRA_API_KEYS", "")

    if not api_keys_env:
        # Fallback to single key for backwards compatibility
        api_keys_env = os.environ.get("RRA_API_KEY", "")

    if not api_keys_env:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: No API keys configured. "
                   "Set RRA_API_KEYS or RRA_API_KEY environment variable.",
        )

    # Parse valid keys
    valid_keys = [k.strip() for k in api_keys_env.split(",") if k.strip()]

    # Constant-time comparison to prevent timing attacks
    for valid_key in valid_keys:
        if hmac.compare_digest(api_key, valid_key):
            return True

    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "API-Key"},
    )


def generate_session_id() -> str:
    """
    Generate a cryptographically secure session ID.

    Returns:
        URL-safe base64 encoded random session ID
    """
    return secrets.token_urlsafe(SESSION_ID_LENGTH)


def optional_api_key(api_key: str = Security(API_KEY_HEADER)) -> Optional[bool]:
    """
    Optional API key verification for public endpoints with optional auth.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        True if valid key provided, None if no key provided

    Raises:
        HTTPException: If a key is provided but is invalid (prevents silent downgrade)
    """
    if api_key is None:
        return None

    # Key was provided — validate it strictly (don't silently downgrade)
    return verify_api_key(api_key)


# Dependency shortcuts
RequireAuth = Depends(verify_api_key)
OptionalAuth = Depends(optional_api_key)
