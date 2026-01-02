# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Network resilience utilities for external service integrations.

Provides:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Request queuing for offline operation
- Fallback chain support
"""

import time
import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Tuple = (Exception,)
    retryable_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # failures before opening
    success_threshold: int = 2  # successes to close from half-open
    timeout: float = 30.0  # seconds before trying half-open
    half_open_max_calls: int = 3  # max calls in half-open state


@dataclass
class CircuitBreakerState:
    """Mutable state for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    half_open_calls: int = 0


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout transition."""
        if self._state.state == CircuitState.OPEN:
            # Check if timeout has passed
            if time.time() - self._state.last_failure_time >= self.config.timeout:
                logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN (timeout)")
                self._state.state = CircuitState.HALF_OPEN
                self._state.half_open_calls = 0
                self._state.success_count = 0
        return self._state.state

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state.state == CircuitState.HALF_OPEN:
            self._state.success_count += 1
            if self._state.success_count >= self.config.success_threshold:
                logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED (recovered)")
                self._state.state = CircuitState.CLOSED
                self._state.failure_count = 0
        elif self._state.state == CircuitState.CLOSED:
            # Reset failure count on success
            self._state.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._state.failure_count += 1
        self._state.last_failure_time = time.time()

        if self._state.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN (failure during recovery)")
            self._state.state = CircuitState.OPEN
        elif self._state.state == CircuitState.CLOSED:
            if self._state.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit {self.name}: CLOSED -> OPEN "
                    f"(failures: {self._state.failure_count})"
                )
                self._state.state = CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if request should be allowed."""
        current_state = self.state  # This checks timeout

        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            if self._state.half_open_calls < self.config.half_open_max_calls:
                self._state.half_open_calls += 1
                return True
            return False

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitBreakerState()
        logger.info(f"Circuit {self.name}: manually reset")


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(f"Circuit {circuit_name} is open. Retry after {retry_after:.1f}s")


@dataclass
class QueuedRequest:
    """A request queued for later execution."""

    id: str
    method: str
    args: tuple
    kwargs: dict
    created_at: str
    attempts: int = 0
    last_error: Optional[str] = None


class RequestQueue:
    """
    Queue for storing failed requests to retry later.

    Persists to disk for durability across restarts.
    """

    def __init__(self, queue_dir: str = ".rra_queue", max_size: int = 1000):
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self._queue: List[QueuedRequest] = []
        self._load_queue()

    def _get_queue_file(self) -> Path:
        return self.queue_dir / "pending_requests.json"

    def _load_queue(self) -> None:
        """Load queued requests from disk."""
        queue_file = self._get_queue_file()
        if queue_file.exists():
            try:
                with open(queue_file, "r") as f:
                    data = json.load(f)
                    self._queue = [QueuedRequest(**item) for item in data]
                logger.info(f"Loaded {len(self._queue)} queued requests")
            except Exception as e:
                logger.error(f"Failed to load queue: {e}")
                self._queue = []

    def _save_queue(self) -> None:
        """Save queued requests to disk."""
        queue_file = self._get_queue_file()
        try:
            data = [
                {
                    "id": r.id,
                    "method": r.method,
                    "args": r.args,
                    "kwargs": r.kwargs,
                    "created_at": r.created_at,
                    "attempts": r.attempts,
                    "last_error": r.last_error,
                }
                for r in self._queue
            ]
            with open(queue_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save queue: {e}")

    def enqueue(self, request_id: str, method: str, args: tuple, kwargs: dict) -> bool:
        """Add a request to the queue."""
        if len(self._queue) >= self.max_size:
            logger.warning("Request queue full, dropping oldest request")
            self._queue.pop(0)

        # Sanitize kwargs - remove non-serializable items
        safe_kwargs = {}
        for k, v in kwargs.items():
            try:
                json.dumps(v)
                safe_kwargs[k] = v
            except (TypeError, ValueError):
                safe_kwargs[k] = str(v)

        request = QueuedRequest(
            id=request_id,
            method=method,
            args=args,
            kwargs=safe_kwargs,
            created_at=datetime.now().isoformat(),
        )
        self._queue.append(request)
        self._save_queue()
        logger.info(f"Queued request {request_id} for later execution")
        return True

    def dequeue(self) -> Optional[QueuedRequest]:
        """Get the next request from the queue."""
        if self._queue:
            request = self._queue.pop(0)
            self._save_queue()
            return request
        return None

    def peek(self) -> Optional[QueuedRequest]:
        """View the next request without removing it."""
        if self._queue:
            return self._queue[0]
        return None

    def mark_failed(self, request_id: str, error: str) -> None:
        """Mark a request as failed and requeue if within retry limit."""
        for request in self._queue:
            if request.id == request_id:
                request.attempts += 1
                request.last_error = error
                self._save_queue()
                return

    def remove(self, request_id: str) -> bool:
        """Remove a request from the queue."""
        for i, request in enumerate(self._queue):
            if request.id == request_id:
                self._queue.pop(i)
                self._save_queue()
                return True
        return False

    def size(self) -> int:
        """Get queue size."""
        return len(self._queue)

    def clear(self) -> None:
        """Clear all queued requests."""
        self._queue = []
        self._save_queue()


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay for retry attempt with optional jitter."""
    import random

    delay = min(config.base_delay * (config.exponential_base**attempt), config.max_delay)

    if config.jitter:
        # Add random jitter of 0-50%
        delay *= 1 + random.random() * 0.5

    return delay


def retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to functions.

    Usage:
        @retry(RetryConfig(max_retries=3))
        def make_request():
            ...
    """
    retry_config = config or RetryConfig()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retry_config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < retry_config.max_retries:
                        delay = calculate_delay(attempt, retry_config)
                        logger.warning(
                            f"Retry {attempt + 1}/{retry_config.max_retries} for "
                            f"{func.__name__} after {delay:.2f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {retry_config.max_retries} retries exhausted for "
                            f"{func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


def async_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to async functions.

    Usage:
        @async_retry(RetryConfig(max_retries=3))
        async def make_request():
            ...
    """
    retry_config = config or RetryConfig()

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retry_config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < retry_config.max_retries:
                        delay = calculate_delay(attempt, retry_config)
                        logger.warning(
                            f"Retry {attempt + 1}/{retry_config.max_retries} for "
                            f"{func.__name__} after {delay:.2f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {retry_config.max_retries} retries exhausted for "
                            f"{func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


class ResilientClient(Generic[T]):
    """
    Wrapper that adds resilience to any client.

    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker for failing services
    - Request queuing for offline operation
    - Fallback to alternative endpoints
    """

    def __init__(
        self,
        name: str,
        client_factory: Callable[[], T],
        fallback_urls: Optional[List[str]] = None,
        retry_config: Optional[RetryConfig] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        enable_queue: bool = True,
    ):
        self.name = name
        self._client_factory = client_factory
        self._client: Optional[T] = None
        self._fallback_urls = fallback_urls or []
        self._current_url_index = 0
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(name, circuit_config)
        self.queue = RequestQueue() if enable_queue else None

    @property
    def client(self) -> T:
        """Get or create the underlying client."""
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def _switch_to_fallback(self) -> bool:
        """Switch to next fallback URL if available."""
        if self._current_url_index < len(self._fallback_urls):
            self._current_url_index += 1
            self._client = None  # Force recreation with new URL
            url = self._fallback_urls[self._current_url_index - 1]
            logger.info(f"Switching {self.name} to fallback URL: {url}")
            return True
        return False

    def execute(
        self, method_name: str, *args, queue_on_failure: bool = True, **kwargs
    ) -> Tuple[bool, Any]:
        """
        Execute a method with resilience patterns.

        Returns:
            Tuple of (success, result_or_error)
        """
        # Check circuit breaker
        if not self.circuit_breaker.allow_request():
            if queue_on_failure and self.queue:
                import uuid

                request_id = str(uuid.uuid4())
                self.queue.enqueue(request_id, method_name, args, kwargs)
                return (False, {"queued": True, "request_id": request_id})
            raise CircuitOpenError(self.name, self.circuit_breaker.config.timeout)

        last_error = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                method = getattr(self.client, method_name)
                result = method(*args, **kwargs)
                self.circuit_breaker.record_success()
                return (True, result)

            except self.retry_config.retryable_exceptions as e:
                last_error = e
                self.circuit_breaker.record_failure()

                if attempt < self.retry_config.max_retries:
                    # Try fallback URL
                    if self._switch_to_fallback():
                        logger.info("Retrying with fallback URL")
                        continue

                    delay = calculate_delay(attempt, self.retry_config)
                    logger.warning(f"Retry {attempt + 1} after {delay:.2f}s: {e}")
                    time.sleep(delay)

        # All retries failed
        if queue_on_failure and self.queue:
            import uuid

            request_id = str(uuid.uuid4())
            self.queue.enqueue(request_id, method_name, args, kwargs)
            return (False, {"queued": True, "request_id": request_id, "error": str(last_error)})

        return (False, {"error": str(last_error)})

    async def execute_async(
        self, method_name: str, *args, queue_on_failure: bool = True, **kwargs
    ) -> Tuple[bool, Any]:
        """
        Execute an async method with resilience patterns.

        Returns:
            Tuple of (success, result_or_error)
        """
        # Check circuit breaker
        if not self.circuit_breaker.allow_request():
            if queue_on_failure and self.queue:
                import uuid

                request_id = str(uuid.uuid4())
                self.queue.enqueue(request_id, method_name, args, kwargs)
                return (False, {"queued": True, "request_id": request_id})
            raise CircuitOpenError(self.name, self.circuit_breaker.config.timeout)

        last_error = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                method = getattr(self.client, method_name)
                result = await method(*args, **kwargs)
                self.circuit_breaker.record_success()
                return (True, result)

            except self.retry_config.retryable_exceptions as e:
                last_error = e
                self.circuit_breaker.record_failure()

                if attempt < self.retry_config.max_retries:
                    # Try fallback URL
                    if self._switch_to_fallback():
                        logger.info("Retrying with fallback URL")
                        continue

                    delay = calculate_delay(attempt, self.retry_config)
                    logger.warning(f"Retry {attempt + 1} after {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)

        # All retries failed
        if queue_on_failure and self.queue:
            import uuid

            request_id = str(uuid.uuid4())
            self.queue.enqueue(request_id, method_name, args, kwargs)
            return (False, {"queued": True, "request_id": request_id, "error": str(last_error)})

        return (False, {"error": str(last_error)})

    async def process_queue(self, max_items: int = 10) -> List[Tuple[str, bool]]:
        """
        Process queued requests.

        Returns:
            List of (request_id, success) tuples
        """
        if not self.queue:
            return []

        results = []
        processed = 0

        while processed < max_items:
            request = self.queue.peek()
            if not request:
                break

            # Don't retry if circuit is open
            if not self.circuit_breaker.allow_request():
                break

            # Max 5 attempts per request
            if request.attempts >= 5:
                logger.warning(f"Dropping request {request.id} after 5 attempts")
                self.queue.remove(request.id)
                results.append((request.id, False))
                processed += 1
                continue

            try:
                method = getattr(self.client, request.method)
                if asyncio.iscoroutinefunction(method):
                    await method(*request.args, **request.kwargs)
                else:
                    method(*request.args, **request.kwargs)

                self.circuit_breaker.record_success()
                self.queue.remove(request.id)
                results.append((request.id, True))
                logger.info(f"Successfully processed queued request {request.id}")

            except Exception as e:
                self.circuit_breaker.record_failure()
                self.queue.mark_failed(request.id, str(e))
                results.append((request.id, False))
                logger.warning(f"Failed to process queued request {request.id}: {e}")

            processed += 1

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get resilience status."""
        return {
            "name": self.name,
            "circuit_state": self.circuit_breaker.state.value,
            "failure_count": self.circuit_breaker._state.failure_count,
            "queue_size": self.queue.size() if self.queue else 0,
            "current_url_index": self._current_url_index,
            "fallback_urls_available": len(self._fallback_urls) - self._current_url_index,
        }
