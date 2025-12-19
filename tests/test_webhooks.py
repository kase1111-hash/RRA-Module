# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for Webhook Bridge infrastructure."""

import pytest
import json
import hmac
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta

from rra.security.webhook_auth import (
    WebhookSecurity,
    RateLimiter,
)


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_initial_state_allows_requests(self):
        """Test that new agents have full quota."""
        limiter = RateLimiter(max_requests=10, window_minutes=60)
        assert limiter.check("new_agent") is True
        assert limiter.get_remaining("new_agent") == 10

    def test_record_decrements_remaining(self):
        """Test that recording requests decrements quota."""
        limiter = RateLimiter(max_requests=10, window_minutes=60)

        # Record 3 requests
        for _ in range(3):
            assert limiter.record("test_agent") is True

        assert limiter.get_remaining("test_agent") == 7

    def test_rate_limit_exceeded(self):
        """Test that rate limit is enforced."""
        limiter = RateLimiter(max_requests=5, window_minutes=60)

        # Use all quota
        for _ in range(5):
            assert limiter.record("test_agent") is True

        # Next request should fail
        assert limiter.record("test_agent") is False
        assert limiter.check("test_agent") is False
        assert limiter.get_remaining("test_agent") == 0

    def test_separate_agents_separate_limits(self):
        """Test that different agents have separate quotas."""
        limiter = RateLimiter(max_requests=3, window_minutes=60)

        # Use all quota for agent1
        for _ in range(3):
            limiter.record("agent1")

        # agent2 should still have full quota
        assert limiter.get_remaining("agent1") == 0
        assert limiter.get_remaining("agent2") == 3

    def test_persistence(self):
        """Test that rate limit state persists."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "rate_limits.json"

            # First instance - record some requests
            limiter1 = RateLimiter(max_requests=10, window_minutes=60, storage_path=storage_path)
            for _ in range(4):
                limiter1.record("persistent_agent")

            # Second instance - should see same state
            limiter2 = RateLimiter(max_requests=10, window_minutes=60, storage_path=storage_path)
            assert limiter2.get_remaining("persistent_agent") == 6


class TestWebhookSecurity:
    """Test cases for WebhookSecurity."""

    def test_generate_credentials(self):
        """Test credential generation."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            creds = security.generate_credentials("test_agent")

            assert "secret_key" in creds
            assert len(creds["secret_key"]) > 20
            assert creds["webhook_url"].endswith("/test_agent")
            assert creds["is_active"] is True

    def test_signature_verification_valid(self):
        """Test valid signature verification."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            creds = security.generate_credentials("test_agent")
            secret = creds["secret_key"]

            payload = {"message": "hello", "test": 123}

            # Compute signature the same way
            payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
            signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

            # Verify without prefix
            assert security.verify_signature("test_agent", payload, signature) is True

            # Verify with prefix
            assert security.verify_signature("test_agent", payload, f"sha256={signature}") is True

    def test_signature_verification_invalid(self):
        """Test invalid signature rejection."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            security.generate_credentials("test_agent")

            payload = {"message": "hello"}
            invalid_sig = "sha256=invalid_signature_here"

            assert security.verify_signature("test_agent", payload, invalid_sig) is False

    def test_signature_verification_unknown_agent(self):
        """Test signature verification for unknown agent."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            assert security.verify_signature("unknown", {}, "any_sig") is False

    def test_rotate_secret(self):
        """Test secret rotation."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            creds = security.generate_credentials("test_agent")
            old_secret = creds["secret_key"]

            new_secret = security.rotate_secret("test_agent")

            assert new_secret is not None
            assert new_secret != old_secret

            # Old signature should no longer work
            payload = {"test": 1}
            old_sig = hmac.new(
                old_secret.encode(),
                json.dumps(payload, sort_keys=True, separators=(',', ':')).encode(),
                hashlib.sha256
            ).hexdigest()

            assert security.verify_signature("test_agent", payload, old_sig) is False

    def test_revoke_credentials(self):
        """Test credential revocation."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            creds = security.generate_credentials("test_agent")
            secret = creds["secret_key"]

            # Revoke
            assert security.revoke_credentials("test_agent") is True

            # Signatures should no longer verify
            payload = {"test": 1}
            sig = hmac.new(
                secret.encode(),
                json.dumps(payload, sort_keys=True, separators=(',', ':')).encode(),
                hashlib.sha256
            ).hexdigest()

            assert security.verify_signature("test_agent", payload, sig) is False

    def test_get_credentials_without_secret(self):
        """Test that get_credentials doesn't expose secret."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            security.generate_credentials("test_agent")
            creds = security.get_credentials("test_agent")

            assert creds is not None
            assert "secret_key" not in creds
            assert "webhook_url" in creds

    def test_ip_allowlist_empty(self):
        """Test that empty IP allowlist allows all."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            security.generate_credentials("test_agent", allowed_ips=[])

            assert security.verify_ip("test_agent", "1.2.3.4") is True
            assert security.verify_ip("test_agent", "5.6.7.8") is True

    def test_ip_allowlist_configured(self):
        """Test that IP allowlist is enforced."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            security.generate_credentials("test_agent", allowed_ips=["1.2.3.4", "10.0.0.1"])

            assert security.verify_ip("test_agent", "1.2.3.4") is True
            assert security.verify_ip("test_agent", "10.0.0.1") is True
            assert security.verify_ip("test_agent", "5.6.7.8") is False

    def test_persistence(self):
        """Test that credentials persist across instances."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"

            # First instance - generate credentials
            security1 = WebhookSecurity(credentials_path=creds_path)
            creds = security1.generate_credentials("persistent_agent")
            secret = creds["secret_key"]

            # Second instance - verify signature works
            security2 = WebhookSecurity(credentials_path=creds_path)
            payload = {"test": 1}
            sig = hmac.new(
                secret.encode(),
                json.dumps(payload, sort_keys=True, separators=(',', ':')).encode(),
                hashlib.sha256
            ).hexdigest()

            assert security2.verify_signature("persistent_agent", payload, sig) is True


class TestComputeSignature:
    """Test signature computation helper."""

    def test_compute_signature(self):
        """Test compute_signature for documentation/testing."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            creds = security.generate_credentials("test_agent")

            payload = {"key": "value"}
            sig = security.compute_signature("test_agent", payload)

            assert sig is not None
            assert sig.startswith("sha256=")
            assert security.verify_signature("test_agent", payload, sig) is True

    def test_compute_signature_unknown_agent(self):
        """Test compute_signature for unknown agent."""
        with TemporaryDirectory() as tmpdir:
            creds_path = Path(tmpdir) / "creds.json"
            security = WebhookSecurity(credentials_path=creds_path)

            sig = security.compute_signature("unknown", {})
            assert sig is None
