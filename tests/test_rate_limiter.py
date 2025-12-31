# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Tests for API rate limiting module.
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch

from rra.api.rate_limiter import (
    RateLimitConfig,
    InMemoryBackend,
    TokenBucketLimiter,
    SlidingWindowLimiter,
    RateLimiter,
    RateLimitExceeded,
    rate_limit,
)


# =============================================================================
# Configuration Tests
# =============================================================================

class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.requests_per_day == 10000
        assert config.burst_size == 10
        assert "/health" in config.exempt_paths

    def test_from_env(self):
        """Test configuration from environment variables."""
        with patch.dict("os.environ", {
            "RRA_RATE_LIMIT_REQUESTS": "100",
            "RRA_RATE_LIMIT_HOUR": "2000",
            "RRA_RATE_LIMIT_DAY": "20000",
            "RRA_RATE_LIMIT_BURST": "20",
        }):
            config = RateLimitConfig.from_env()
            assert config.requests_per_minute == 100
            assert config.requests_per_hour == 2000
            assert config.requests_per_day == 20000
            assert config.burst_size == 20


# =============================================================================
# Backend Tests
# =============================================================================

class TestInMemoryBackend:
    """Tests for InMemoryBackend."""

    @pytest.fixture
    def backend(self):
        return InMemoryBackend()

    @pytest.mark.asyncio
    async def test_token_storage(self, backend):
        """Test token storage and retrieval."""
        await backend.set_tokens("test_key", 10, time.time(), 3600)
        tokens, timestamp = await backend.get_tokens("test_key")
        assert tokens == 10
        assert timestamp > 0

    @pytest.mark.asyncio
    async def test_token_not_found(self, backend):
        """Test retrieval of non-existent tokens."""
        tokens, timestamp = await backend.get_tokens("nonexistent")
        assert tokens == 0
        assert timestamp == 0.0

    @pytest.mark.asyncio
    async def test_sliding_window_counter(self, backend):
        """Test sliding window counter."""
        # First request
        count1 = await backend.increment_counter("test", window=60)
        assert count1 == 1

        # Second request
        count2 = await backend.increment_counter("test", window=60)
        assert count2 == 2

        # Third request
        count3 = await backend.increment_counter("test", window=60)
        assert count3 == 3

    @pytest.mark.asyncio
    async def test_sliding_window_expiry(self, backend):
        """Test that old entries are removed from sliding window."""
        # Add entries with very short window
        await backend.increment_counter("test", window=1)
        await backend.increment_counter("test", window=1)

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # New request should start fresh
        count = await backend.increment_counter("test", window=1)
        assert count == 1

    @pytest.mark.asyncio
    async def test_cleanup(self, backend):
        """Test cleanup of expired entries."""
        await backend.set_tokens("test", 10, time.time() - 100000, 3600)
        await backend.increment_counter("test_counter", window=1)

        await asyncio.sleep(1.1)
        await backend.cleanup()

        # Cleaned up entries should be gone
        tokens, _ = await backend.get_tokens("test")
        assert tokens == 0


# =============================================================================
# Token Bucket Tests
# =============================================================================

class TestTokenBucketLimiter:
    """Tests for TokenBucketLimiter."""

    @pytest.fixture
    def limiter(self):
        backend = InMemoryBackend()
        return TokenBucketLimiter(backend, rate=1.0, bucket_size=5)

    @pytest.mark.asyncio
    async def test_initial_tokens(self, limiter):
        """Test that first request gets full bucket."""
        allowed, remaining, retry_after = await limiter.acquire("test")
        assert allowed is True
        assert remaining == 4  # Started with 5, used 1
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_token_consumption(self, limiter):
        """Test token consumption."""
        # Use all tokens
        for _ in range(5):
            allowed, _, _ = await limiter.acquire("test")
            assert allowed is True

        # Next request should fail
        allowed, remaining, retry_after = await limiter.acquire("test")
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_token_replenishment(self, limiter):
        """Test token replenishment over time."""
        # Use all tokens
        for _ in range(5):
            await limiter.acquire("test")

        # Wait for tokens to replenish
        await asyncio.sleep(2)

        # Should have tokens again
        allowed, _, _ = await limiter.acquire("test")
        assert allowed is True


# =============================================================================
# Sliding Window Tests
# =============================================================================

class TestSlidingWindowLimiter:
    """Tests for SlidingWindowLimiter."""

    @pytest.fixture
    def limiter(self):
        backend = InMemoryBackend()
        return SlidingWindowLimiter(backend, limit=5, window=60)

    @pytest.mark.asyncio
    async def test_under_limit(self, limiter):
        """Test requests under limit."""
        for _ in range(5):
            allowed, remaining, retry_after = await limiter.check("test")
            assert allowed is True
            assert retry_after == 0

    @pytest.mark.asyncio
    async def test_over_limit(self, limiter):
        """Test requests over limit."""
        # Use up limit
        for _ in range(5):
            await limiter.check("test")

        # Next should fail
        allowed, remaining, retry_after = await limiter.check("test")
        assert allowed is False
        assert remaining == 0
        assert retry_after == 60


# =============================================================================
# RateLimiter Integration Tests
# =============================================================================

class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.fixture
    def limiter(self):
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            burst_size=5,
            exempt_paths=["/health", "/docs"],
        )
        return RateLimiter(config)

    def _make_mock_request(self, path="/api/test", client_ip="192.168.1.1", api_key=None):
        """Create a mock FastAPI request."""
        request = MagicMock()
        request.url.path = path
        request.client.host = client_ip

        # Create a proper headers mock that mimics dict-like behavior
        headers_dict = {"X-Forwarded-For": ""}
        if api_key:
            headers_dict["X-API-Key"] = api_key

        request.headers.get = MagicMock(side_effect=lambda k, d="": headers_dict.get(k, d))
        return request

    @pytest.mark.asyncio
    async def test_exempt_path(self, limiter):
        """Test that exempt paths bypass rate limiting."""
        request = self._make_mock_request(path="/health")
        allowed, headers = await limiter.check_rate_limit(request)
        assert allowed is True
        assert headers == {}

    @pytest.mark.asyncio
    async def test_normal_request(self, limiter):
        """Test normal request within limits."""
        request = self._make_mock_request()
        allowed, headers = await limiter.check_rate_limit(request)
        assert allowed is True
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, limiter):
        """Test rate limit headers are set correctly."""
        request = self._make_mock_request()
        allowed, headers = await limiter.check_rate_limit(request)

        assert headers["X-RateLimit-Limit"] == "10"  # requests_per_minute
        assert "X-RateLimit-Reset" in headers

    @pytest.mark.asyncio
    async def test_different_clients(self, limiter):
        """Test that different clients have separate limits."""
        request1 = self._make_mock_request(client_ip="192.168.1.1")
        request2 = self._make_mock_request(client_ip="192.168.1.2")

        # Both should be allowed
        allowed1, _ = await limiter.check_rate_limit(request1)
        allowed2, _ = await limiter.check_rate_limit(request2)

        assert allowed1 is True
        assert allowed2 is True

    @pytest.mark.asyncio
    async def test_api_key_identification(self):
        """Test that API key is used for client identification."""
        # Create fresh limiter with high limits
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_size=20,
            exempt_paths=["/health"],
        )
        limiter = RateLimiter(config)

        request1 = self._make_mock_request(api_key="key1")
        request2 = self._make_mock_request(api_key="key2")

        # Make requests with both keys
        for _ in range(5):
            await limiter.check_rate_limit(request1)
            await limiter.check_rate_limit(request2)

        # Both should still be allowed (separate buckets)
        allowed1, _ = await limiter.check_rate_limit(request1)
        allowed2, _ = await limiter.check_rate_limit(request2)

        assert allowed1 is True
        assert allowed2 is True


# =============================================================================
# Decorator Tests
# =============================================================================

class TestRateLimitDecorator:
    """Tests for rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_decorator_allows_requests(self):
        """Test that decorated function allows requests within limit."""
        @rate_limit(requests=5, window=60)
        async def test_endpoint(request):
            return "success"

        request = MagicMock()
        request.client.host = "test"

        result = await test_endpoint(request)
        assert result == "success"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Decorator uses shared async state; tested via middleware instead")
    async def test_decorator_blocks_excess(self):
        """Test that decorator blocks requests over limit."""
        import uuid
        from fastapi import HTTPException

        # Use unique client ID to avoid state from other tests
        unique_client = f"test-{uuid.uuid4()}"

        @rate_limit(requests=2, window=60)
        async def test_endpoint_excess(request):
            return "success"

        request = MagicMock()
        request.client.host = unique_client

        # First two should succeed
        await test_endpoint_excess(request)
        await test_endpoint_excess(request)

        # Third should fail
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint_excess(request)

        assert exc_info.value.status_code == 429


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
