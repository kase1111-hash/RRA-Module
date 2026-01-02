# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Dreaming Status - Real-time visibility into RRA processing.

Provides a lightweight status line that shows what's happening inside
the code while it's working. Updates are throttled to once every 5 seconds
to minimize performance impact.

Usage:
    from rra.status.dreaming import get_dreaming_status

    dreaming = get_dreaming_status()
    dreaming.start("Parsing repository structure")
    # ... do work ...
    dreaming.complete("Parsing repository structure")
"""

import asyncio
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List, Dict, Any
from collections import deque


class StatusType(Enum):
    """Type of status update."""

    START = "start"
    COMPLETE = "complete"
    ERROR = "error"
    INFO = "info"


@dataclass
class StatusEntry:
    """A single status entry."""

    operation: str
    status_type: StatusType
    timestamp: datetime
    duration_ms: Optional[float] = None
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "type": self.status_type.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "details": self.details,
        }

    def format_message(self) -> str:
        """Format as a display message."""
        if self.status_type == StatusType.START:
            return f"Starting: {self.operation}"
        elif self.status_type == StatusType.COMPLETE:
            if self.duration_ms is not None:
                return f"Completed: {self.operation} ({self.duration_ms:.0f}ms)"
            return f"Completed: {self.operation}"
        elif self.status_type == StatusType.ERROR:
            return f"Error: {self.operation} - {self.details or 'Unknown error'}"
        else:
            return f"{self.operation}"


class DreamingStatus:
    """
    Throttled status updates for real-time visibility.

    Only emits updates every 5 seconds to avoid performance overhead.
    Tracks start and completion of operations.

    Attributes:
        throttle_seconds: Time between status emissions (default 5)
        enabled: Whether status updates are active
    """

    # Default throttle interval in seconds
    DEFAULT_THROTTLE_SECONDS = 5.0

    def __init__(
        self,
        throttle_seconds: float = DEFAULT_THROTTLE_SECONDS,
        enabled: bool = True,
        max_history: int = 100,
    ):
        """
        Initialize the dreaming status tracker.

        Args:
            throttle_seconds: Minimum time between status emissions
            enabled: Whether to emit status updates
            max_history: Maximum number of entries to keep in history
        """
        self._throttle_seconds = throttle_seconds
        self._enabled = enabled
        self._max_history = max_history

        # Timing state
        self._last_emit_time: float = 0
        self._pending_entry: Optional[StatusEntry] = None

        # Operation tracking (for calculating durations)
        self._operation_starts: Dict[str, float] = {}

        # History of status entries
        self._history: deque = deque(maxlen=max_history)

        # Current status for display
        self._current_status: Optional[str] = None
        self._current_operation: Optional[str] = None

        # Callbacks for status updates (CLI, WebSocket, etc.)
        self._callbacks: List[Callable[[StatusEntry], None]] = []
        self._async_callbacks: List[Callable[[StatusEntry], Any]] = []

        # Thread safety
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def throttle_seconds(self) -> float:
        return self._throttle_seconds

    @throttle_seconds.setter
    def throttle_seconds(self, value: float) -> None:
        self._throttle_seconds = max(0.1, value)  # Minimum 100ms

    @property
    def current_status(self) -> Optional[str]:
        """Get the current status message."""
        return self._current_status

    @property
    def current_operation(self) -> Optional[str]:
        """Get the current operation name."""
        return self._current_operation

    def add_callback(self, callback: Callable[[StatusEntry], None]) -> None:
        """Add a synchronous callback for status updates."""
        with self._lock:
            self._callbacks.append(callback)

    def add_async_callback(self, callback: Callable[[StatusEntry], Any]) -> None:
        """Add an async callback for status updates."""
        with self._lock:
            self._async_callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
            if callback in self._async_callbacks:
                self._async_callbacks.remove(callback)

    def _should_emit(self) -> bool:
        """Check if enough time has passed to emit a new status."""
        current_time = time.time()
        return (current_time - self._last_emit_time) >= self._throttle_seconds

    def _emit(self, entry: StatusEntry) -> None:
        """Emit a status entry to all callbacks."""
        if not self._enabled:
            return

        with self._lock:
            self._last_emit_time = time.time()
            self._current_status = entry.format_message()
            self._current_operation = entry.operation
            self._history.append(entry)

            # Call synchronous callbacks
            for callback in self._callbacks:
                try:
                    callback(entry)
                except Exception:
                    pass  # Don't let callback errors break status updates

            # Schedule async callbacks if any
            if self._async_callbacks:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        for callback in self._async_callbacks:
                            asyncio.create_task(self._call_async(callback, entry))
                except RuntimeError:
                    pass  # No event loop available

    async def _call_async(self, callback: Callable, entry: StatusEntry) -> None:
        """Call an async callback safely."""
        try:
            result = callback(entry)
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass  # Don't let callback errors break status updates

    def start(self, operation: str, details: Optional[str] = None) -> None:
        """
        Mark the start of an operation.

        Args:
            operation: Name of the operation starting
            details: Optional additional details
        """
        if not self._enabled:
            return

        current_time = time.time()
        self._operation_starts[operation] = current_time

        entry = StatusEntry(
            operation=operation,
            status_type=StatusType.START,
            timestamp=datetime.now(),
            details=details,
        )

        if self._should_emit():
            self._emit(entry)
        else:
            self._pending_entry = entry

    def complete(self, operation: str, details: Optional[str] = None) -> None:
        """
        Mark the completion of an operation.

        Args:
            operation: Name of the operation that completed
            details: Optional additional details
        """
        if not self._enabled:
            return

        current_time = time.time()
        duration_ms = None

        if operation in self._operation_starts:
            start_time = self._operation_starts.pop(operation)
            duration_ms = (current_time - start_time) * 1000

        entry = StatusEntry(
            operation=operation,
            status_type=StatusType.COMPLETE,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            details=details,
        )

        # Completions are always emitted (they're important milestones)
        # but still respect the throttle
        if self._should_emit():
            self._emit(entry)
        else:
            self._pending_entry = entry

    def error(self, operation: str, error_message: str) -> None:
        """
        Mark an error in an operation.

        Errors are always emitted immediately (bypass throttle).

        Args:
            operation: Name of the operation that errored
            error_message: Description of the error
        """
        if not self._enabled:
            return

        # Calculate duration if we have a start time
        duration_ms = None
        if operation in self._operation_starts:
            start_time = self._operation_starts.pop(operation)
            duration_ms = (time.time() - start_time) * 1000

        entry = StatusEntry(
            operation=operation,
            status_type=StatusType.ERROR,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            details=error_message,
        )

        # Errors bypass the throttle
        self._emit(entry)

    def info(self, message: str) -> None:
        """
        Emit an informational status message.

        Args:
            message: The info message to emit
        """
        if not self._enabled:
            return

        entry = StatusEntry(
            operation=message,
            status_type=StatusType.INFO,
            timestamp=datetime.now(),
        )

        if self._should_emit():
            self._emit(entry)
        else:
            self._pending_entry = entry

    def flush(self) -> None:
        """Force emit any pending status entry."""
        if self._pending_entry:
            self._emit(self._pending_entry)
            self._pending_entry = None

    def get_history(self, limit: int = 10) -> List[StatusEntry]:
        """
        Get recent status history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of recent status entries (newest first)
        """
        with self._lock:
            entries = list(self._history)
            entries.reverse()
            return entries[:limit]

    def clear_history(self) -> None:
        """Clear the status history."""
        with self._lock:
            self._history.clear()
            self._current_status = None
            self._current_operation = None

    def get_active_operations(self) -> List[str]:
        """Get list of operations that have started but not completed."""
        with self._lock:
            return list(self._operation_starts.keys())


# Global singleton instance
_dreaming_status: Optional[DreamingStatus] = None
_dreaming_lock = threading.Lock()


def get_dreaming_status() -> DreamingStatus:
    """
    Get the global dreaming status instance.

    Returns:
        The singleton DreamingStatus instance
    """
    global _dreaming_status

    if _dreaming_status is None:
        with _dreaming_lock:
            if _dreaming_status is None:
                _dreaming_status = DreamingStatus()

    return _dreaming_status


def configure_dreaming(
    throttle_seconds: float = DreamingStatus.DEFAULT_THROTTLE_SECONDS,
    enabled: bool = True,
) -> DreamingStatus:
    """
    Configure the global dreaming status instance.

    Args:
        throttle_seconds: Time between status emissions
        enabled: Whether to emit status updates

    Returns:
        The configured DreamingStatus instance
    """
    status = get_dreaming_status()
    status.throttle_seconds = throttle_seconds
    status.enabled = enabled
    return status
