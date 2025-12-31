# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Tests for network resilience module.
"""

import pytest
import asyncio
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from rra.integration.network_resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitOpenError,
    RequestQueue,
    QueuedRequest,
    RetryConfig,
    ResilientClient,
    calculate_delay,
    retry,
    async_retry,
)


# =============================================================================
# Circuit Breaker Tests
# =============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    @pytest.fixture
    def circuit(self):
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,
            half_open_max_calls=2,
        )
        return CircuitBreaker("test", config)

    def test_initial_state(self, circuit):
        """Test circuit starts in closed state."""
        assert circuit.state == CircuitState.CLOSED

    def test_stays_closed_on_success(self, circuit):
        """Test circuit stays closed on successful calls."""
        circuit.record_success()
        assert circuit.state == CircuitState.CLOSED

    def test_opens_after_failures(self, circuit):
        """Test circuit opens after threshold failures."""
        for _ in range(3):
            circuit.record_failure()

        assert circuit.state == CircuitState.OPEN

    def test_rejects_when_open(self, circuit):
        """Test circuit rejects requests when open."""
        for _ in range(3):
            circuit.record_failure()

        assert circuit.allow_request() is False

    def test_half_open_after_timeout(self, circuit):
        """Test circuit transitions to half-open after timeout."""
        for _ in range(3):
            circuit.record_failure()

        assert circuit.state == CircuitState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        assert circuit.state == CircuitState.HALF_OPEN

    def test_half_open_allows_limited_requests(self, circuit):
        """Test half-open state allows limited requests."""
        for _ in range(3):
            circuit.record_failure()

        time.sleep(1.1)

        # Should allow max_calls requests
        assert circuit.allow_request() is True
        assert circuit.allow_request() is True
        assert circuit.allow_request() is False

    def test_closes_after_successes_in_half_open(self, circuit):
        """Test circuit closes after successes in half-open."""
        for _ in range(3):
            circuit.record_failure()

        time.sleep(1.1)

        assert circuit.state == CircuitState.HALF_OPEN

        circuit.record_success()
        circuit.record_success()

        assert circuit.state == CircuitState.CLOSED

    def test_reopens_on_failure_in_half_open(self, circuit):
        """Test circuit reopens on failure in half-open."""
        for _ in range(3):
            circuit.record_failure()

        time.sleep(1.1)

        assert circuit.state == CircuitState.HALF_OPEN

        circuit.record_failure()

        assert circuit.state == CircuitState.OPEN

    def test_reset(self, circuit):
        """Test manual reset."""
        for _ in range(3):
            circuit.record_failure()

        assert circuit.state == CircuitState.OPEN

        circuit.reset()

        assert circuit.state == CircuitState.CLOSED
        assert circuit._state.failure_count == 0


# =============================================================================
# Request Queue Tests
# =============================================================================

class TestRequestQueue:
    """Tests for RequestQueue."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for queue storage."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def queue(self, temp_dir):
        return RequestQueue(queue_dir=temp_dir, max_size=10)

    def test_enqueue(self, queue):
        """Test adding request to queue."""
        result = queue.enqueue("req1", "post_entry", ("arg1",), {"key": "value"})
        assert result is True
        assert queue.size() == 1

    def test_dequeue(self, queue):
        """Test removing request from queue."""
        queue.enqueue("req1", "post_entry", ("arg1",), {})

        request = queue.dequeue()
        assert request is not None
        assert request.id == "req1"
        assert request.method == "post_entry"
        assert queue.size() == 0

    def test_peek(self, queue):
        """Test peeking at next request without removing."""
        queue.enqueue("req1", "method1", (), {})

        request = queue.peek()
        assert request.id == "req1"
        assert queue.size() == 1  # Still in queue

    def test_fifo_order(self, queue):
        """Test FIFO ordering."""
        queue.enqueue("req1", "method", (), {})
        queue.enqueue("req2", "method", (), {})
        queue.enqueue("req3", "method", (), {})

        assert queue.dequeue().id == "req1"
        assert queue.dequeue().id == "req2"
        assert queue.dequeue().id == "req3"

    def test_max_size(self, queue):
        """Test max size enforcement."""
        for i in range(15):
            queue.enqueue(f"req{i}", "method", (), {})

        assert queue.size() == 10  # Max size

    def test_remove(self, queue):
        """Test removing specific request."""
        queue.enqueue("req1", "method", (), {})
        queue.enqueue("req2", "method", (), {})

        result = queue.remove("req1")
        assert result is True
        assert queue.size() == 1
        assert queue.peek().id == "req2"

    def test_mark_failed(self, queue):
        """Test marking request as failed."""
        queue.enqueue("req1", "method", (), {})

        queue.mark_failed("req1", "Connection error")

        request = queue.peek()
        assert request.attempts == 1
        assert request.last_error == "Connection error"

    def test_persistence(self, temp_dir):
        """Test queue persists across instances."""
        queue1 = RequestQueue(queue_dir=temp_dir)
        queue1.enqueue("req1", "method", ("arg",), {"key": "value"})

        # Create new queue instance
        queue2 = RequestQueue(queue_dir=temp_dir)
        assert queue2.size() == 1

        request = queue2.peek()
        assert request.id == "req1"
        # JSON serialization converts tuples to lists
        assert list(request.args) == ["arg"]

    def test_clear(self, queue):
        """Test clearing queue."""
        queue.enqueue("req1", "method", (), {})
        queue.enqueue("req2", "method", (), {})

        queue.clear()
        assert queue.size() == 0


# =============================================================================
# Retry Logic Tests
# =============================================================================

class TestRetryLogic:
    """Tests for retry utilities."""

    def test_calculate_delay_exponential(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0

    def test_calculate_delay_max(self):
        """Test max delay cap."""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)

        assert calculate_delay(10, config) == 5.0

    def test_calculate_delay_jitter(self):
        """Test jitter adds randomness."""
        config = RetryConfig(base_delay=1.0, jitter=True)

        delays = [calculate_delay(0, config) for _ in range(10)]
        # Not all delays should be the same
        assert len(set(delays)) > 1

    def test_retry_decorator_success(self):
        """Test retry decorator with successful function."""
        call_count = 0

        @retry(RetryConfig(max_retries=3))
        def succeeding_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeeding_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_decorator_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = 0

        @retry(RetryConfig(max_retries=3, base_delay=0.01))
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_retry_decorator_exhausted(self):
        """Test retry decorator when retries exhausted."""
        call_count = 0

        @retry(RetryConfig(max_retries=2, base_delay=0.01))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Permanent failure")

        with pytest.raises(ConnectionError):
            always_fails()

        assert call_count == 3  # Initial + 2 retries


class TestAsyncRetry:
    """Tests for async retry decorator."""

    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """Test async retry with successful function."""
        call_count = 0

        @async_retry(RetryConfig(max_retries=3))
        async def async_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await async_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_eventual_success(self):
        """Test async retry with eventual success."""
        call_count = 0

        @async_retry(RetryConfig(max_retries=3, base_delay=0.01))
        async def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await eventually_succeeds()
        assert result == "success"
        assert call_count == 3


# =============================================================================
# Resilient Client Tests
# =============================================================================

class TestResilientClient:
    """Tests for ResilientClient."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client."""
        client = MagicMock()
        client.do_something = MagicMock(return_value="result")
        return client

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for queue."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_execute_success(self, mock_client, temp_dir):
        """Test successful execution."""
        resilient = ResilientClient(
            name="test",
            client_factory=lambda: mock_client,
            retry_config=RetryConfig(max_retries=1),
        )
        resilient.queue = RequestQueue(queue_dir=temp_dir)

        success, result = resilient.execute("do_something", "arg1", key="value")

        assert success is True
        assert result == "result"
        mock_client.do_something.assert_called_once_with("arg1", key="value")

    def test_execute_with_retry(self, temp_dir):
        """Test execution with retry on failure."""
        call_count = 0

        def flaky_method():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        mock_client = MagicMock()
        mock_client.flaky_method = flaky_method

        resilient = ResilientClient(
            name="test",
            client_factory=lambda: mock_client,
            retry_config=RetryConfig(max_retries=3, base_delay=0.01),
        )
        resilient.queue = RequestQueue(queue_dir=temp_dir)

        success, result = resilient.execute("flaky_method")

        assert success is True
        assert result == "success"
        assert call_count == 3

    def test_circuit_breaker_integration(self, temp_dir):
        """Test circuit breaker integration."""
        mock_client = MagicMock()
        mock_client.failing_method = MagicMock(side_effect=ConnectionError("Failed"))

        resilient = ResilientClient(
            name="test",
            client_factory=lambda: mock_client,
            retry_config=RetryConfig(max_retries=0),
            circuit_config=CircuitBreakerConfig(failure_threshold=3),
        )
        resilient.queue = RequestQueue(queue_dir=temp_dir)

        # Cause failures to open circuit
        for _ in range(5):
            try:
                resilient.execute("failing_method", queue_on_failure=False)
            except Exception:
                pass

        # Circuit should be open
        assert resilient.circuit_breaker.state == CircuitState.OPEN

        # Next call should fail with CircuitOpenError
        with pytest.raises(CircuitOpenError):
            resilient.execute("failing_method", queue_on_failure=False)

    def test_get_status(self, mock_client, temp_dir):
        """Test status reporting."""
        resilient = ResilientClient(
            name="test_client",
            client_factory=lambda: mock_client,
            fallback_urls=["http://backup1", "http://backup2"],
        )
        resilient.queue = RequestQueue(queue_dir=temp_dir)

        status = resilient.get_status()

        assert status["name"] == "test_client"
        assert status["circuit_state"] == "closed"
        assert status["queue_size"] == 0
        assert status["fallback_urls_available"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
