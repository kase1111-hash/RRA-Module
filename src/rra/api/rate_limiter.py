# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Advanced rate limiting for the RRA API.

Provides multiple rate limiting strategies:
- Token bucket for smooth rate limiting
- Sliding window for accurate counting
- Per-endpoint and per-user limits
- Redis backend for distributed deployments
"""

import os
import time
import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Callable, Any, cast
from enum import Enum
from functools import wraps

from fastapi import Request, HTTPException, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int, limit: int, remaining: int = 0):
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Default limits
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000

    # Burst allowance (token bucket)
    burst_size: int = 10

    # Per-endpoint overrides
    endpoint_limits: Dict[str, int] = field(default_factory=dict)

    # Exempt paths (no rate limiting)
    exempt_paths: list = field(default_factory=lambda: ["/health", "/docs", "/openapi.json"])

    # Use Redis for distributed rate limiting
    use_redis: bool = False
    redis_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create config from environment variables."""
        return cls(
            requests_per_minute=int(os.environ.get("RRA_RATE_LIMIT_REQUESTS", "60")),
            requests_per_hour=int(os.environ.get("RRA_RATE_LIMIT_HOUR", "1000")),
            requests_per_day=int(os.environ.get("RRA_RATE_LIMIT_DAY", "10000")),
            burst_size=int(os.environ.get("RRA_RATE_LIMIT_BURST", "10")),
            use_redis=os.environ.get("RRA_RATE_LIMIT_REDIS", "false").lower() == "true",
            redis_url=os.environ.get("REDIS_URL"),
        )


class RateLimitBackend(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def get_tokens(self, key: str) -> Tuple[int, float]:
        """Get current token count and last update time."""
        pass

    @abstractmethod
    async def set_tokens(self, key: str, tokens: int, timestamp: float, ttl: int) -> None:
        """Set token count and timestamp."""
        pass

    @abstractmethod
    async def increment_counter(self, key: str, window: int) -> int:
        """Increment sliding window counter, return current count."""
        pass


class InMemoryBackend(RateLimitBackend):
    """In-memory rate limit storage (single-server only)."""

    def __init__(self):
        self._tokens: Dict[str, Tuple[int, float]] = {}
        self._counters: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def get_tokens(self, key: str) -> Tuple[int, float]:
        """Get current token count and last update time."""
        async with self._lock:
            if key in self._tokens:
                return self._tokens[key]
            return (0, 0.0)

    async def set_tokens(self, key: str, tokens: int, timestamp: float, ttl: int) -> None:
        """Set token count and timestamp."""
        async with self._lock:
            self._tokens[key] = (tokens, timestamp)

    async def increment_counter(self, key: str, window: int) -> int:
        """Increment sliding window counter."""
        async with self._lock:
            now = time.time()
            cutoff = now - window

            if key not in self._counters:
                self._counters[key] = []

            # Remove old entries
            self._counters[key] = [t for t in self._counters[key] if t > cutoff]

            # Add current request
            self._counters[key].append(now)

            return len(self._counters[key])

    async def cleanup(self) -> None:
        """Clean up expired entries."""
        async with self._lock:
            now = time.time()
            # Clean tokens older than 1 day
            self._tokens = {k: v for k, v in self._tokens.items() if now - v[1] < 86400}
            # Clean counters older than 1 day
            cutoff = now - 86400
            for key in list(self._counters.keys()):
                self._counters[key] = [t for t in self._counters[key] if t > cutoff]
                if not self._counters[key]:
                    del self._counters[key]


class RedisBackend(RateLimitBackend):
    """Redis-based rate limit storage for distributed deployments."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        """Lazy initialization of Redis client."""
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(self.redis_url)
            except ImportError:
                raise ImportError("redis package required for Redis backend")
        return self._redis

    async def get_tokens(self, key: str) -> Tuple[int, float]:
        """Get current token count and last update time from Redis."""
        r = await self._get_redis()
        data = await r.hgetall(f"ratelimit:tokens:{key}")
        if data:
            return (int(data.get(b"tokens", 0)), float(data.get(b"timestamp", 0)))
        return (0, 0.0)

    async def set_tokens(self, key: str, tokens: int, timestamp: float, ttl: int) -> None:
        """Set token count and timestamp in Redis."""
        r = await self._get_redis()
        pipe = r.pipeline()
        pipe.hset(f"ratelimit:tokens:{key}", mapping={"tokens": tokens, "timestamp": timestamp})
        pipe.expire(f"ratelimit:tokens:{key}", ttl)
        await pipe.execute()

    async def increment_counter(self, key: str, window: int) -> int:
        """Increment sliding window counter using Redis sorted set."""
        r = await self._get_redis()
        now = time.time()
        redis_key = f"ratelimit:window:{key}"

        pipe = r.pipeline()
        # Remove old entries
        pipe.zremrangebyscore(redis_key, 0, now - window)
        # Add current request
        pipe.zadd(redis_key, {str(now): now})
        # Get count
        pipe.zcard(redis_key)
        # Set expiry
        pipe.expire(redis_key, window)

        results = await pipe.execute()
        return int(results[2])  # zcard result


class TokenBucketLimiter:
    """Token bucket rate limiter for smooth rate limiting."""

    def __init__(
        self,
        backend: RateLimitBackend,
        rate: float,  # tokens per second
        bucket_size: int,  # max tokens
    ):
        self.backend = backend
        self.rate = rate
        self.bucket_size = bucket_size

    async def acquire(self, key: str, tokens: int = 1) -> Tuple[bool, int, int]:
        """
        Try to acquire tokens.

        Returns:
            Tuple of (allowed, remaining, retry_after_seconds)
        """
        now = time.time()
        current_tokens, last_update = await self.backend.get_tokens(key)

        # Calculate tokens to add based on time elapsed
        if last_update > 0:
            elapsed = now - last_update
            tokens_to_add = int(elapsed * self.rate)
            current_tokens = min(self.bucket_size, current_tokens + tokens_to_add)
        else:
            # First request - start with full bucket
            current_tokens = self.bucket_size

        # Check if we have enough tokens
        if current_tokens >= tokens:
            new_tokens = current_tokens - tokens
            await self.backend.set_tokens(key, new_tokens, now, 3600)
            return (True, new_tokens, 0)
        else:
            # Calculate when tokens will be available
            tokens_needed = tokens - current_tokens
            retry_after = int(tokens_needed / self.rate) + 1
            return (False, 0, retry_after)


class SlidingWindowLimiter:
    """Sliding window rate limiter for accurate counting."""

    def __init__(self, backend: RateLimitBackend, limit: int, window: int):
        """
        Args:
            backend: Storage backend
            limit: Maximum requests per window
            window: Window size in seconds
        """
        self.backend = backend
        self.limit = limit
        self.window = window

    async def check(self, key: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (allowed, remaining, retry_after_seconds)
        """
        count = await self.backend.increment_counter(key, self.window)
        remaining = max(0, self.limit - count)

        if count <= self.limit:
            return (True, remaining, 0)
        else:
            # Retry after window expires
            return (False, 0, self.window)


class RateLimiter:
    """
    Combined rate limiter with multiple strategies.

    Uses token bucket for burst handling and sliding window for
    accurate rate limiting across different time windows.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig.from_env()

        # Initialize backend
        self.backend: RateLimitBackend
        if self.config.use_redis and self.config.redis_url:
            self.backend = RedisBackend(self.config.redis_url)
        else:
            self.backend = InMemoryBackend()

        # Token bucket for burst handling
        # Allow burst_size requests instantly, then rate tokens/second
        rate_per_second = self.config.requests_per_minute / 60.0
        self.token_bucket = TokenBucketLimiter(
            self.backend, rate=rate_per_second, bucket_size=self.config.burst_size
        )

        # Sliding windows for different time periods
        self.minute_limiter = SlidingWindowLimiter(
            self.backend, limit=self.config.requests_per_minute, window=60
        )
        self.hour_limiter = SlidingWindowLimiter(
            self.backend, limit=self.config.requests_per_hour, window=3600
        )
        self.day_limiter = SlidingWindowLimiter(
            self.backend, limit=self.config.requests_per_day, window=86400
        )

    def _get_client_key(self, request: Request) -> str:
        """Generate a unique key for the client."""
        # Use API key if present, otherwise IP
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            # Hash the API key for privacy
            return f"api:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"

        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        return f"ip:{client_ip}"

    def _get_endpoint_limit(self, path: str) -> Optional[int]:
        """Get custom limit for specific endpoint."""
        for pattern, limit in self.config.endpoint_limits.items():
            if path.startswith(pattern):
                return limit
        return None

    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.

        Returns:
            Tuple of (allowed, headers_dict)
        """
        path = request.url.path

        # Check exempt paths
        if any(path.startswith(exempt) for exempt in self.config.exempt_paths):
            return (True, {})

        client_key = self._get_client_key(request)
        endpoint_key = f"{client_key}:{path}"

        # Check token bucket first (for burst handling)
        bucket_ok, bucket_remaining, bucket_retry = await self.token_bucket.acquire(
            f"bucket:{client_key}"
        )

        if not bucket_ok:
            return (
                False,
                {
                    "X-RateLimit-Limit": str(self.config.burst_size),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + bucket_retry),
                    "Retry-After": str(bucket_retry),
                },
            )

        # Check minute window
        minute_ok, minute_remaining, minute_retry = await self.minute_limiter.check(
            f"minute:{client_key}"
        )

        if not minute_ok:
            return (
                False,
                {
                    "X-RateLimit-Limit": str(self.config.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + minute_retry),
                    "Retry-After": str(minute_retry),
                },
            )

        # Check hour window
        hour_ok, hour_remaining, hour_retry = await self.hour_limiter.check(f"hour:{client_key}")

        if not hour_ok:
            return (
                False,
                {
                    "X-RateLimit-Limit": str(self.config.requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + hour_retry),
                    "Retry-After": str(hour_retry),
                },
            )

        # Check day window
        day_ok, day_remaining, day_retry = await self.day_limiter.check(f"day:{client_key}")

        if not day_ok:
            return (
                False,
                {
                    "X-RateLimit-Limit": str(self.config.requests_per_day),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + day_retry),
                    "Retry-After": str(day_retry),
                },
            )

        # All checks passed
        return (
            True,
            {
                "X-RateLimit-Limit": str(self.config.requests_per_minute),
                "X-RateLimit-Remaining": str(minute_remaining),
                "X-RateLimit-Reset": str(int(time.time()) + 60),
            },
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()
        self._enabled = os.environ.get("RRA_RATE_LIMIT_ENABLED", "true").lower() == "true"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        """Check rate limit and process request."""
        if not self._enabled:
            return cast(Response, await call_next(request))

        allowed, headers = await self.rate_limiter.check_rate_limit(request)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {request.client.host if request.client else 'unknown'} "
                f"on {request.url.path}"
            )
            response = Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response

        # Process request
        response = cast(Response, await call_next(request))

        # Add rate limit headers to successful responses
        for key, value in headers.items():
            response.headers[key] = value

        return response


def rate_limit(
    requests: int = 10, window: int = 60, key_func: Optional[Callable[[Request], str]] = None
):
    """
    Decorator for endpoint-specific rate limiting.

    Args:
        requests: Maximum requests per window
        window: Window size in seconds
        key_func: Optional function to generate rate limit key

    Usage:
        @app.get("/api/expensive")
        @rate_limit(requests=5, window=60)
        async def expensive_endpoint():
            ...
    """
    backend = InMemoryBackend()
    limiter = SlidingWindowLimiter(backend, limit=requests, window=window)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find Request in args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                # Can't rate limit without request
                return await func(*args, **kwargs)

            # Generate key
            if key_func:
                key = key_func(request)
            else:
                client_ip = request.client.host if request.client else "unknown"
                key = f"{func.__name__}:{client_ip}"

            # Check limit
            allowed, remaining, retry_after = await limiter.check(key)

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience function for FastAPI app setup
def setup_rate_limiting(app, config: Optional[RateLimitConfig] = None):
    """
    Set up rate limiting for a FastAPI application.

    Args:
        app: FastAPI application instance
        config: Optional rate limit configuration

    Usage:
        from rra.api.rate_limiter import setup_rate_limiting

        app = FastAPI()
        setup_rate_limiting(app)
    """
    rate_limiter = RateLimiter(config)
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    logger.info("Rate limiting enabled")
    return rate_limiter
