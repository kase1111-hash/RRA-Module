# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
API Authentication for RRA Module.

Provides authentication middleware and utilities:
- API key authentication
- JWT token validation (optional)
- Role-based access control
"""

import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from functools import wraps

from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials


# =============================================================================
# Configuration
# =============================================================================

# Environment-based configuration
API_KEY_HEADER_NAME = "X-API-Key"
AUTH_ENABLED = os.environ.get("RRA_AUTH_ENABLED", "false").lower() == "true"
ADMIN_API_KEY = os.environ.get("RRA_ADMIN_API_KEY", None)

# API key storage path
API_KEYS_PATH = Path(os.environ.get("RRA_API_KEYS_PATH", "data/api_keys.json"))


# Security schemes
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# =============================================================================
# API Key Manager
# =============================================================================


class APIKeyManager:
    """
    Manages API keys for authentication.

    Keys are hashed before storage for security.
    """

    def __init__(self, storage_path: Path = API_KEYS_PATH):
        """Initialize the API key manager."""
        self.storage_path = storage_path
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._load_keys()

    def _hash_key(self, key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _load_keys(self) -> None:
        """Load API keys from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    self._keys = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._keys = {}

    def _save_keys(self) -> None:
        """Save API keys to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self._keys, f, indent=2, default=str)

    def create_key(
        self, name: str, scopes: List[str] = None, expires_in_days: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Create a new API key.

        Args:
            name: Human-readable name for the key
            scopes: List of allowed scopes (e.g., ['read', 'write', 'admin'])
            expires_in_days: Optional expiration in days

        Returns:
            Dict with 'key' (only shown once) and 'key_id'
        """
        # Generate a secure random key
        raw_key = secrets.token_urlsafe(32)
        key_id = secrets.token_hex(8)
        key_hash = self._hash_key(raw_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()

        # Store key metadata (NOT the raw key)
        self._keys[key_hash] = {
            "key_id": key_id,
            "name": name,
            "scopes": scopes or ["read"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "is_active": True,
            "last_used": None,
        }

        self._save_keys()

        return {
            "key": raw_key,  # Only returned once!
            "key_id": key_id,
            "name": name,
            "scopes": scopes or ["read"],
            "expires_at": expires_at,
        }

    def validate_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key.

        Args:
            key: The raw API key to validate

        Returns:
            Key metadata if valid, None otherwise
        """
        if not key:
            return None

        key_hash = self._hash_key(key)
        key_data = self._keys.get(key_hash)

        if not key_data:
            return None

        # Check if active
        if not key_data.get("is_active", False):
            return None

        # Check expiration
        expires_at = key_data.get("expires_at")
        if expires_at:
            if datetime.fromisoformat(expires_at) < datetime.utcnow():
                return None

        # Update last used
        key_data["last_used"] = datetime.utcnow().isoformat()
        self._save_keys()

        return key_data

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by its ID."""
        for key_hash, data in self._keys.items():
            if data.get("key_id") == key_id:
                data["is_active"] = False
                self._save_keys()
                return True
        return False

    def list_keys(self) -> List[Dict[str, Any]]:
        """List all API keys (without the actual keys)."""
        return [
            {
                "key_id": data["key_id"],
                "name": data["name"],
                "scopes": data["scopes"],
                "created_at": data["created_at"],
                "expires_at": data.get("expires_at"),
                "is_active": data["is_active"],
                "last_used": data.get("last_used"),
            }
            for data in self._keys.values()
        ]


# Global instance
api_key_manager = APIKeyManager()


# =============================================================================
# Authentication Dependencies
# =============================================================================


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[Dict[str, Any]]:
    """
    Dependency to validate API key from header.

    Returns key metadata if valid, None if no key or invalid.
    """
    if not api_key:
        return None

    # Check admin key first
    if ADMIN_API_KEY and api_key == ADMIN_API_KEY:
        return {
            "key_id": "admin",
            "name": "Admin Key",
            "scopes": ["admin", "read", "write"],
            "is_admin": True,
        }

    return api_key_manager.validate_key(api_key)


async def require_auth(
    api_key: Optional[Dict[str, Any]] = Depends(get_api_key),
) -> Dict[str, Any]:
    """
    Dependency that requires valid authentication.

    Raises HTTPException 401 if not authenticated.
    """
    if not AUTH_ENABLED:
        # Auth disabled - return anonymous access
        return {"key_id": "anonymous", "scopes": ["read", "write"]}

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Set X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


async def require_admin(
    api_key: Dict[str, Any] = Depends(require_auth),
) -> Dict[str, Any]:
    """
    Dependency that requires admin access.

    Raises HTTPException 403 if not admin.
    """
    if "admin" not in api_key.get("scopes", []):
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    return api_key


async def require_scope(scope: str):
    """
    Factory for scope-checking dependency.

    Usage:
        @app.get("/endpoint", dependencies=[Depends(require_scope("write"))])
    """

    async def check_scope(
        api_key: Dict[str, Any] = Depends(require_auth),
    ) -> Dict[str, Any]:
        if scope not in api_key.get("scopes", []):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{scope}' required.",
            )
        return api_key

    return check_scope


# =============================================================================
# Optional Auth (for public endpoints that benefit from auth)
# =============================================================================


async def optional_auth(
    api_key: Optional[Dict[str, Any]] = Depends(get_api_key),
) -> Optional[Dict[str, Any]]:
    """
    Dependency that accepts optional authentication.

    Returns key metadata if authenticated, None otherwise.
    Useful for public endpoints that have enhanced features for authenticated users.
    """
    return api_key
