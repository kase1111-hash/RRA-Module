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
import ipaddress
import socket
import base64
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse


# =============================================================================
# SSRF Protection
# =============================================================================

# Networks to block for SSRF protection
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Localhost
    ipaddress.ip_network("10.0.0.0/8"),  # Private (Class A)
    ipaddress.ip_network("172.16.0.0/12"),  # Private (Class B)
    ipaddress.ip_network("192.168.0.0/16"),  # Private (Class C)
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS/cloud metadata)
    ipaddress.ip_network("0.0.0.0/8"),  # "This" network
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::1/128"),  # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def validate_callback_url(url: str) -> bool:
    """
    Validate callback URL to prevent SSRF attacks.

    Blocks:
    - Non-HTTPS URLs
    - Localhost and loopback addresses
    - Private network ranges
    - Cloud metadata endpoints
    - Link-local addresses

    Args:
        url: URL to validate

    Returns:
        True if URL is safe to call, False otherwise
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # Only allow HTTPS
        if parsed.scheme != "https":
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Block localhost variants
        if hostname.lower() in ("localhost", "localhost.localdomain"):
            return False

        # Resolve hostname to IP
        try:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)

            # Check against blocked networks
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return False
        except socket.gaierror:
            # DNS resolution failed - could be malicious
            return False

        # Block specific cloud metadata hostnames
        blocked_hostnames = [
            "metadata.google.internal",
            "metadata.goog",
            "kubernetes.default",
        ]
        if any(hostname.lower().endswith(h) for h in blocked_hostnames):
            return False

        return True

    except Exception:
        return False


# =============================================================================
# Encryption Utilities
# =============================================================================


class CredentialEncryption:
    """
    Encrypt/decrypt credentials at rest using Fernet symmetric encryption.

    Uses environment variable for encryption key or generates a local key.
    """

    def __init__(self):
        """Initialize encryption with key from environment or generate one."""
        self._key = self._get_or_create_key()

    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or create a local one."""
        # Try environment variable first
        env_key = os.environ.get("RRA_ENCRYPTION_KEY")
        if env_key:
            # Decode base64-encoded key from environment
            try:
                return base64.urlsafe_b64decode(env_key.encode())
            except Exception:
                pass

        # Fall back to local key file
        key_path = Path("data/.encryption_key")
        if key_path.exists():
            return key_path.read_bytes()

        # Generate new key
        key = secrets.token_bytes(32)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
        # Set restrictive permissions
        os.chmod(key_path, 0o600)
        return key

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string using AES-256-GCM.

        Args:
            data: Plaintext string to encrypt

        Returns:
            Base64-encoded encrypted data with nonce
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        aesgcm = AESGCM(self._key)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)

        # Combine nonce and ciphertext
        encrypted = nonce + ciphertext
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.

        Args:
            encrypted_data: Base64-encoded encrypted data

        Returns:
            Decrypted plaintext string
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        data = base64.urlsafe_b64decode(encrypted_data.encode())
        nonce = data[:12]
        ciphertext = data[12:]

        aesgcm = AESGCM(self._key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()


# =============================================================================
# Replay Attack Protection
# =============================================================================


class NonceTracker:
    """
    Track used nonces/timestamps to prevent replay attacks.

    Maintains a sliding window of recently used nonces.
    """

    # Maximum age of valid requests (5 minutes)
    MAX_AGE_SECONDS = 300

    # Maximum number of nonces to track
    MAX_NONCES = 10000

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize nonce tracker."""
        self.storage_path = storage_path or Path("data/nonces.json")
        self._nonces: Dict[str, datetime] = {}
        self._load_nonces()

    def _load_nonces(self) -> None:
        """Load nonces from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    self._nonces = {k: datetime.fromisoformat(v) for k, v in data.items()}
            except (json.JSONDecodeError, IOError):
                self._nonces = {}

        # Cleanup old nonces on load
        self._cleanup()

    def _save_nonces(self) -> None:
        """Save nonces to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump({k: v.isoformat() for k, v in self._nonces.items()}, f)

    def _cleanup(self) -> None:
        """Remove expired nonces."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.MAX_AGE_SECONDS)
        self._nonces = {k: v for k, v in self._nonces.items() if v > cutoff}

        # Also limit total count
        if len(self._nonces) > self.MAX_NONCES:
            # Keep most recent
            sorted_nonces = sorted(self._nonces.items(), key=lambda x: x[1], reverse=True)
            self._nonces = dict(sorted_nonces[: self.MAX_NONCES])

    def validate_request(self, timestamp: str, nonce: Optional[str] = None) -> tuple[bool, str]:
        """
        Validate a request's timestamp and optional nonce.

        Args:
            timestamp: ISO format timestamp from request
            nonce: Optional unique nonce from request

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            request_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return False, "Invalid timestamp format"

        now = datetime.utcnow()

        # Check if timestamp is too old
        age = (now - request_time.replace(tzinfo=None)).total_seconds()
        if age > self.MAX_AGE_SECONDS:
            return False, f"Request expired (age: {age:.0f}s, max: {self.MAX_AGE_SECONDS}s)"

        # Check if timestamp is in the future (with 30s tolerance for clock skew)
        if age < -30:
            return False, "Request timestamp is in the future"

        # If nonce provided, check for replay
        if nonce:
            nonce_key = f"{timestamp}:{nonce}"
            if nonce_key in self._nonces:
                return False, "Duplicate request (replay detected)"

            # Record this nonce
            self._nonces[nonce_key] = datetime.utcnow()
            self._cleanup()
            self._save_nonces()

        return True, ""

    def clear(self) -> None:
        """Clear all tracked nonces."""
        self._nonces = {}
        self._save_nonces()


class RateLimiter:
    """
    Token bucket rate limiter for webhook endpoints.

    Default: 100 requests per hour per agent.
    """

    def __init__(
        self, max_requests: int = 100, window_minutes: int = 60, storage_path: Optional[Path] = None
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
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for key, timestamps in data.items():
                        self._requests[key] = [datetime.fromisoformat(ts) for ts in timestamps]
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
            with open(self.storage_path, "w") as f:
                json.dump(data, f)

    def _cleanup_old_requests(self, agent_id: str) -> None:
        """Remove requests outside the time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        self._requests[agent_id] = [ts for ts in self._requests[agent_id] if ts > cutoff]

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
        self.credentials_path = credentials_path or Path(
            "agent_knowledge_bases/webhook_credentials.json"
        )
        self._credentials: Dict[str, Dict[str, Any]] = {}
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load credentials from disk."""
        if self.credentials_path.exists():
            try:
                with open(self.credentials_path, "r") as f:
                    self._credentials = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._credentials = {}

    def _save_credentials(self) -> None:
        """Save credentials to disk."""
        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.credentials_path, "w") as f:
            json.dump(self._credentials, f, indent=2, default=str)

    def generate_credentials(
        self,
        agent_id: str,
        base_url: str = "https://natlangchain.io",
        allowed_ips: Optional[List[str]] = None,
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
        return {k: v for k, v in creds.items() if k != "secret_key"}

    def verify_signature(self, agent_id: str, payload: dict, signature: str) -> bool:
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
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        # Compare signatures (with or without sha256= prefix)
        expected_with_prefix = f"sha256={expected}"

        return hmac.compare_digest(signature, expected) or hmac.compare_digest(
            signature, expected_with_prefix
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

        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        return f"sha256={signature}"


# Global instances for convenience
rate_limiter = RateLimiter()
webhook_security = WebhookSecurity()


def verify_webhook_signature(agent_id: str, payload: dict, signature: str) -> bool:
    """Convenience function for signature verification."""
    return webhook_security.verify_signature(agent_id, payload, signature)
