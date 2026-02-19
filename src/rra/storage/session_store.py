# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Session Storage Abstraction for RRA Module.

Provides pluggable session storage backends:
- InMemorySessionStore: For development/testing (default fallback)
- RedisSessionStore: For production (horizontal scaling)

Addresses H-001: In-memory session storage needs Redis/DB for production scaling.
"""

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SessionData(Generic[T]):
    """
    Session data wrapper with expiry tracking.

    Generic type T allows storing any serializable session payload.
    """

    def __init__(
        self,
        payload: T,
        expiry_hours: float = 24.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize session data.

        Args:
            payload: The session payload (e.g., NegotiatorAgent)
            expiry_hours: Hours until session expires
            metadata: Optional metadata about the session
        """
        self.payload = payload
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        self.expiry_hours = expiry_hours
        self.metadata = metadata or {}

    def is_expired(self) -> bool:
        """Check if session has expired based on last activity."""
        expiry_time = timedelta(hours=self.expiry_hours)
        return datetime.now(timezone.utc) - self.last_activity > expiry_time

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session metadata (not payload) to dict."""
        return {
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "expiry_hours": self.expiry_hours,
            "metadata": self.metadata,
            "is_expired": self.is_expired(),
        }


class SessionStore(ABC):
    """
    Abstract base class for session storage backends.

    Implementations must be thread-safe for concurrent access.
    """

    @abstractmethod
    def get(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            SessionData if found and not expired, None otherwise
        """
        pass

    @abstractmethod
    def set(self, session_id: str, session: SessionData) -> None:
        """
        Store or update a session.

        Args:
            session_id: Unique session identifier
            session: Session data to store
        """
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session to delete

        Returns:
            True if session existed and was deleted
        """
        pass

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """
        Check if a session exists (and is not expired).

        Args:
            session_id: Session to check

        Returns:
            True if session exists and is valid
        """
        pass

    @abstractmethod
    def touch(self, session_id: str) -> bool:
        """
        Update session's last activity timestamp.

        Args:
            session_id: Session to touch

        Returns:
            True if session was found and updated
        """
        pass

    @abstractmethod
    def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.

        Returns:
            Number of sessions removed
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        Get total number of active sessions.

        Returns:
            Session count
        """
        pass


class InMemorySessionStore(SessionStore):
    """
    In-memory session storage for development and testing.

    WARNING: Not suitable for production - sessions lost on restart
    and cannot scale across multiple instances.

    Thread-safe via internal lock for concurrent access.
    """

    def __init__(self):
        """Initialize in-memory store."""
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.Lock()
        logger.warning(
            "Using in-memory session store. "
            "Set RRA_REDIS_URL for production deployment."
        )

    def get(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session, returning None if expired."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired():
                del self._sessions[session_id]
                return None
            return session

    def set(self, session_id: str, session: SessionData) -> None:
        """Store session in memory."""
        with self._lock:
            self._sessions[session_id] = session

    def delete(self, session_id: str) -> bool:
        """Delete session from memory."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def exists(self, session_id: str) -> bool:
        """Check if valid session exists."""
        return self.get(session_id) is not None

    def touch(self, session_id: str) -> bool:
        """Update session activity timestamp."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.is_expired():
                return False
            session.touch()
            return True

    def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
            for sid in expired:
                del self._sessions[sid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired in-memory sessions")
        return len(expired)

    def count(self) -> int:
        """Count active sessions."""
        # Cleanup first to get accurate count
        self.cleanup_expired()
        with self._lock:
            return len(self._sessions)


class RedisSessionStore(SessionStore):
    """
    Redis-backed session storage for production use.

    Features:
    - Horizontal scaling across multiple server instances
    - Persistence across server restarts
    - Automatic TTL-based expiration
    - Atomic operations for thread safety

    Requires: redis package (pip install redis)
    """

    # Redis key prefix to namespace sessions
    KEY_PREFIX = "rra:session:"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl_hours: float = 24.0,
        key_prefix: Optional[str] = None,
    ):
        """
        Initialize Redis session store.

        Args:
            redis_url: Redis connection URL (default: from RRA_REDIS_URL env)
            default_ttl_hours: Default session TTL in hours
            key_prefix: Optional custom key prefix

        Raises:
            ImportError: If redis package not installed
            ConnectionError: If cannot connect to Redis
        """
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis package required for RedisSessionStore. "
                "Install with: pip install redis"
            )

        self.redis_url = redis_url or os.environ.get(
            "RRA_REDIS_URL", "redis://localhost:6379/0"
        )
        self.default_ttl_hours = default_ttl_hours
        self.key_prefix = key_prefix or self.KEY_PREFIX

        # Create Redis connection pool
        self._redis = redis.from_url(
            self.redis_url,
            decode_responses=False,  # We use pickle for serialization
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )

        # Verify connection
        try:
            self._redis.ping()
            logger.info(f"Connected to Redis session store at {self._mask_url(self.redis_url)}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _mask_url(self, url: str) -> str:
        """Mask password in Redis URL for logging."""
        import re
        return re.sub(r"://[^:]+:[^@]+@", "://***:***@", url)

    def _make_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    def _serialize(self, session: SessionData) -> bytes:
        """Serialize session metadata for Redis storage (JSON-safe, no pickle)."""
        data = {
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "expiry_hours": session.expiry_hours,
            "metadata": session.metadata,
        }
        return json.dumps(data).encode("utf-8")

    def _deserialize(self, data: bytes) -> Optional[SessionData]:
        """Deserialize session data from Redis (JSON-safe, no pickle)."""
        try:
            parsed = json.loads(data.decode("utf-8"))
            session = SessionData(
                payload=None,  # Payload must be reconstructed by caller
                expiry_hours=parsed.get("expiry_hours", self.default_ttl_hours),
                metadata=parsed.get("metadata", {}),
            )
            session.created_at = datetime.fromisoformat(parsed["created_at"])
            session.last_activity = datetime.fromisoformat(parsed["last_activity"])
            return session
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to deserialize session: {e}")
            return None

    def get(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session from Redis."""
        key = self._make_key(session_id)
        data = self._redis.get(key)

        if data is None:
            return None

        session = self._deserialize(data)
        if session is None:
            # Corrupted data, clean it up
            self._redis.delete(key)
            return None

        if session.is_expired():
            # Expired but TTL hasn't kicked in yet
            self._redis.delete(key)
            return None

        return session

    def set(self, session_id: str, session: SessionData) -> None:
        """Store session in Redis with TTL."""
        key = self._make_key(session_id)
        data = self._serialize(session)

        # Calculate TTL based on session expiry
        ttl_seconds = int(session.expiry_hours * 3600)

        self._redis.setex(key, ttl_seconds, data)

    def delete(self, session_id: str) -> bool:
        """Delete session from Redis."""
        key = self._make_key(session_id)
        return self._redis.delete(key) > 0

    def exists(self, session_id: str) -> bool:
        """Check if session exists in Redis."""
        # We need to check both existence and expiration
        session = self.get(session_id)
        return session is not None

    def touch(self, session_id: str) -> bool:
        """Update session activity and refresh TTL."""
        session = self.get(session_id)
        if session is None:
            return False

        session.touch()
        self.set(session_id, session)
        return True

    def cleanup_expired(self) -> int:
        """
        Remove expired sessions.

        Note: Redis TTL handles most cleanup automatically.
        This method catches sessions that expired but haven't
        been TTL'd yet (edge cases with activity-based expiry).
        """
        count = 0
        pattern = f"{self.key_prefix}*"

        # Use SCAN to iterate without blocking
        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor, match=pattern, count=100)

            for key in keys:
                data = self._redis.get(key)
                if data:
                    session = self._deserialize(data)
                    if session and session.is_expired():
                        self._redis.delete(key)
                        count += 1

            if cursor == 0:
                break

        if count > 0:
            logger.info(f"Cleaned up {count} expired Redis sessions")

        return count

    def count(self) -> int:
        """Count active sessions in Redis."""
        pattern = f"{self.key_prefix}*"
        count = 0

        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis connection and session statistics.

        Returns:
            Dictionary with stats
        """
        info = self._redis.info()
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "total_sessions": self.count(),
            "redis_version": info.get("redis_version", "unknown"),
        }


def create_session_store() -> SessionStore:
    """
    Factory function to create appropriate session store.

    Uses Redis if RRA_REDIS_URL is set, otherwise falls back to in-memory.

    Returns:
        Configured SessionStore instance
    """
    redis_url = os.environ.get("RRA_REDIS_URL")

    if redis_url:
        try:
            return RedisSessionStore(redis_url=redis_url)
        except ImportError:
            logger.warning(
                "Redis URL configured but redis package not installed. "
                "Falling back to in-memory store. Install with: pip install redis"
            )
        except Exception as e:
            logger.warning(
                f"Failed to connect to Redis ({e}). "
                "Falling back to in-memory store."
            )

    return InMemorySessionStore()


# Singleton session store instance
_session_store: Optional[SessionStore] = None
_session_store_lock = threading.Lock()


def get_session_store() -> SessionStore:
    """
    Get the global session store instance.

    Lazily creates the store on first access.
    Thread-safe via double-checked locking.

    Returns:
        Global SessionStore instance
    """
    global _session_store
    if _session_store is None:
        with _session_store_lock:
            if _session_store is None:  # Double-check
                _session_store = create_session_store()
    return _session_store


def reset_session_store() -> None:
    """
    Reset the global session store.

    Useful for testing or reconfiguration.
    """
    global _session_store
    _session_store = None
