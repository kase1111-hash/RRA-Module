# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Webhook authentication and rate limiting for RRA Module.

Provides security for external webhook integrations:
- HMAC-SHA256 signature verification
- Rate limiting per agent
- Credential management
- IP allowlisting (optional)
"""

import hmac
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from collections import defaultdict


class RateLimiter:
    """
    Token bucket rate limiter for webhook endpoints.

    Default: 100 requests per hour per agent.
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_minutes: int = 60,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_minutes: Time window in minutes
            storage_path: Optional path to persist rate limit state
        """
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.storage_path = storage_path
        self._requests: Dict[str, List[datetime]] = defaultdict(list)
        self._load_state()

    def _load_state(self) -> None:
        """Load rate limit state from disk."""
        if self.storage_path and self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for key, timestamps in data.items():
                        self._requests[key] = [
                            datetime.fromisoformat(ts) for ts in timestamps
                        ]
            except (json.JSONDecodeError, IOError):
                pass

    def _save_state(self) -> None:
        """Save rate limit state to disk."""
        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                key: [ts.isoformat() for ts in timestamps]
                for key, timestamps in self._requests.items()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f)

    def _cleanup_old_requests(self, agent_id: str) -> None:
        """Remove requests outside the time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        self._requests[agent_id] = [
            ts for ts in self._requests[agent_id] if ts > cutoff
        ]

    def check(self, agent_id: str) -> bool:
        """
        Check if a request is allowed under rate limits.

        Args:
            agent_id: The agent/repo ID

        Returns:
            True if request is allowed, False if rate limited
        """
        self._cleanup_old_requests(agent_id)
        return len(self._requests[agent_id]) < self.max_requests

    def record(self, agent_id: str) -> bool:
        """
        Record a request and check rate limit.

        Args:
            agent_id: The agent/repo ID

        Returns:
            True if request is allowed, False if rate limited
        """
        self._cleanup_old_requests(agent_id)

        if len(self._requests[agent_id]) >= self.max_requests:
            return False

        self._requests[agent_id].append(datetime.utcnow())
        self._save_state()
        return True

    def get_remaining(self, agent_id: str) -> int:
        """Get remaining requests for an agent."""
        self._cleanup_old_requests(agent_id)
        return max(0, self.max_requests - len(self._requests[agent_id]))

    def get_reset_time(self, agent_id: str) -> Optional[datetime]:
        """Get the time when the oldest request expires."""
        self._cleanup_old_requests(agent_id)
        if not self._requests[agent_id]:
            return None
        oldest = min(self._requests[agent_id])
        return oldest + timedelta(minutes=self.window_minutes)


class WebhookSecurity:
    """
    Manage webhook credentials and signature verification.

    Provides:
    - HMAC-SHA256 signature generation and verification
    - Credential rotation
    - IP allowlisting
    """

    def __init__(self, credentials_path: Optional[Path] = None):
        """
        Initialize webhook security.

        Args:
            credentials_path: Path to store webhook credentials
        """
        self.credentials_path = credentials_path or Path("agent_knowledge_bases/webhook_credentials.json")
        self._credentials: Dict[str, Dict[str, Any]] = {}
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load credentials from disk."""
        if self.credentials_path.exists():
            try:
                with open(self.credentials_path, 'r') as f:
                    self._credentials = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._credentials = {}

    def _save_credentials(self) -> None:
        """Save credentials to disk."""
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.credentials_path, 'w') as f:
            json.dump(self._credentials, f, indent=2, default=str)

    def generate_credentials(
        self,
        agent_id: str,
        base_url: str = "https://natlangchain.io",
        allowed_ips: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate webhook credentials for an agent.

        Args:
            agent_id: The agent/repo ID
            base_url: Base URL for webhook endpoint
            allowed_ips: Optional list of allowed source IPs

        Returns:
            Dictionary with webhook URL, secret key, and configuration
        """
        secret_key = secrets.token_urlsafe(32)

        credential = {
            "agent_id": agent_id,
            "secret_key": secret_key,
            "webhook_url": f"{base_url}/webhook/{agent_id}",
            "created_at": datetime.utcnow().isoformat(),
            "allowed_ips": allowed_ips or [],
            "is_active": True,
            "rate_limit": "100 requests/hour",
        }

        self._credentials[agent_id] = credential
        self._save_credentials()

        return credential

    def rotate_secret(self, agent_id: str) -> Optional[str]:
        """
        Rotate the secret key for an agent.

        Args:
            agent_id: The agent/repo ID

        Returns:
            New secret key, or None if agent not found
        """
        if agent_id not in self._credentials:
            return None

        new_secret = secrets.token_urlsafe(32)
        self._credentials[agent_id]["secret_key"] = new_secret
        self._credentials[agent_id]["rotated_at"] = datetime.utcnow().isoformat()
        self._save_credentials()

        return new_secret

    def revoke_credentials(self, agent_id: str) -> bool:
        """
        Revoke webhook credentials for an agent.

        Args:
            agent_id: The agent/repo ID

        Returns:
            True if revoked, False if not found
        """
        if agent_id not in self._credentials:
            return False

        self._credentials[agent_id]["is_active"] = False
        self._credentials[agent_id]["revoked_at"] = datetime.utcnow().isoformat()
        self._save_credentials()

        return True

    def get_credentials(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get credentials for an agent (without exposing secret)."""
        creds = self._credentials.get(agent_id)
        if not creds:
            return None

        # Return copy without secret
        return {
            k: v for k, v in creds.items()
            if k != "secret_key"
        }

    def verify_signature(
        self,
        agent_id: str,
        payload: dict,
        signature: str
    ) -> bool:
        """
        Verify HMAC-SHA256 signature of webhook payload.

        Args:
            agent_id: The agent/repo ID
            payload: Request payload dictionary
            signature: Signature from X-Webhook-Signature header

        Returns:
            True if signature is valid
        """
        creds = self._credentials.get(agent_id)
        if not creds or not creds.get("is_active", False):
            return False

        secret = creds.get("secret_key")
        if not secret:
            return False

        # Compute expected signature
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        expected = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures (with or without sha256= prefix)
        expected_with_prefix = f"sha256={expected}"

        return (
            hmac.compare_digest(signature, expected) or
            hmac.compare_digest(signature, expected_with_prefix)
        )

    def verify_ip(self, agent_id: str, source_ip: str) -> bool:
        """
        Verify source IP is in allowlist (if configured).

        Args:
            agent_id: The agent/repo ID
            source_ip: Source IP address

        Returns:
            True if IP is allowed (or no allowlist configured)
        """
        creds = self._credentials.get(agent_id)
        if not creds:
            return False

        allowed_ips = creds.get("allowed_ips", [])
        if not allowed_ips:
            return True  # No IP restriction

        return source_ip in allowed_ips

    def compute_signature(self, agent_id: str, payload: dict) -> Optional[str]:
        """
        Compute signature for a payload (for testing/docs).

        Args:
            agent_id: The agent/repo ID
            payload: Payload to sign

        Returns:
            HMAC-SHA256 signature with sha256= prefix
        """
        creds = self._credentials.get(agent_id)
        if not creds:
            return None

        secret = creds.get("secret_key")
        if not secret:
            return None

        payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        signature = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"


# Global instances for convenience
rate_limiter = RateLimiter()
webhook_security = WebhookSecurity()


def verify_webhook_signature(agent_id: str, payload: dict, signature: str) -> bool:
    """Convenience function for signature verification."""
    return webhook_security.verify_signature(agent_id, payload, signature)
