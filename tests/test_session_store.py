# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for session storage module."""

import time
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from rra.storage.session_store import (
    SessionData,
    InMemorySessionStore,
    RedisSessionStore,
    create_session_store,
    get_session_store,
    reset_session_store,
)


class TestSessionData:
    """Tests for SessionData class."""

    def test_session_data_creation(self):
        """Test creating session data."""
        payload = {"test": "data"}
        session = SessionData(payload=payload, expiry_hours=1.0)

        assert session.payload == payload
        assert session.expiry_hours == 1.0
        assert session.created_at is not None
        assert session.last_activity is not None
        assert session.metadata == {}

    def test_session_data_with_metadata(self):
        """Test session data with metadata."""
        session = SessionData(
            payload="test",
            metadata={"user_id": "123", "ip": "127.0.0.1"},
        )

        assert session.metadata["user_id"] == "123"
        assert session.metadata["ip"] == "127.0.0.1"

    def test_session_expiry(self):
        """Test session expiry detection."""
        session = SessionData(payload="test", expiry_hours=0.0001)  # ~0.36 seconds

        assert not session.is_expired()

        # Wait for expiry
        time.sleep(0.5)
        assert session.is_expired()

    def test_session_touch(self):
        """Test updating session activity."""
        session = SessionData(payload="test", expiry_hours=0.0001)

        original_activity = session.last_activity
        time.sleep(0.1)
        session.touch()

        assert session.last_activity > original_activity

    def test_session_to_dict(self):
        """Test session serialization."""
        session = SessionData(
            payload="test",
            expiry_hours=24.0,
            metadata={"key": "value"},
        )

        data = session.to_dict()

        assert "created_at" in data
        assert "last_activity" in data
        assert data["expiry_hours"] == 24.0
        assert data["metadata"] == {"key": "value"}
        assert "is_expired" in data


class TestInMemorySessionStore:
    """Tests for in-memory session storage."""

    def test_set_and_get(self):
        """Test storing and retrieving sessions."""
        store = InMemorySessionStore()
        session = SessionData(payload={"user": "test"})

        store.set("session-123", session)
        retrieved = store.get("session-123")

        assert retrieved is not None
        assert retrieved.payload == {"user": "test"}

    def test_get_nonexistent(self):
        """Test getting nonexistent session."""
        store = InMemorySessionStore()

        assert store.get("nonexistent") is None

    def test_get_expired(self):
        """Test that expired sessions are not returned."""
        store = InMemorySessionStore()
        session = SessionData(payload="test", expiry_hours=0.0001)

        store.set("expired-session", session)
        time.sleep(0.5)

        assert store.get("expired-session") is None

    def test_delete(self):
        """Test deleting sessions."""
        store = InMemorySessionStore()
        session = SessionData(payload="test")

        store.set("to-delete", session)
        assert store.exists("to-delete")

        result = store.delete("to-delete")
        assert result is True
        assert not store.exists("to-delete")

    def test_delete_nonexistent(self):
        """Test deleting nonexistent session."""
        store = InMemorySessionStore()

        assert store.delete("nonexistent") is False

    def test_exists(self):
        """Test checking session existence."""
        store = InMemorySessionStore()
        session = SessionData(payload="test")

        assert not store.exists("new-session")

        store.set("new-session", session)
        assert store.exists("new-session")

    def test_touch(self):
        """Test updating session activity."""
        store = InMemorySessionStore()
        session = SessionData(payload="test")

        store.set("touch-test", session)
        original_activity = store.get("touch-test").last_activity

        time.sleep(0.1)
        result = store.touch("touch-test")

        assert result is True
        assert store.get("touch-test").last_activity > original_activity

    def test_touch_nonexistent(self):
        """Test touching nonexistent session."""
        store = InMemorySessionStore()

        assert store.touch("nonexistent") is False

    def test_cleanup_expired(self):
        """Test cleaning up expired sessions."""
        store = InMemorySessionStore()

        # Create some sessions
        store.set("active", SessionData(payload="a", expiry_hours=24))
        store.set("expired-1", SessionData(payload="b", expiry_hours=0.0001))
        store.set("expired-2", SessionData(payload="c", expiry_hours=0.0001))

        time.sleep(0.5)

        count = store.cleanup_expired()

        assert count == 2
        assert store.exists("active")
        assert not store.exists("expired-1")
        assert not store.exists("expired-2")

    def test_count(self):
        """Test counting active sessions."""
        store = InMemorySessionStore()

        assert store.count() == 0

        store.set("s1", SessionData(payload="a"))
        store.set("s2", SessionData(payload="b"))
        store.set("s3", SessionData(payload="c"))

        assert store.count() == 3


class TestRedisSessionStore:
    """Tests for Redis session storage (with mocking)."""

    @patch("rra.storage.session_store.redis")
    def test_redis_initialization(self, mock_redis_module):
        """Test Redis store initialization."""
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client
        mock_client.ping.return_value = True

        store = RedisSessionStore(redis_url="redis://localhost:6379/0")

        mock_redis_module.from_url.assert_called_once()
        mock_client.ping.assert_called_once()

    @patch("rra.storage.session_store.redis")
    def test_redis_set_and_get(self, mock_redis_module):
        """Test Redis set and get operations."""
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client
        mock_client.ping.return_value = True

        store = RedisSessionStore(redis_url="redis://localhost:6379/0")
        session = SessionData(payload="test")

        # Mock serialization
        store.set("test-session", session)

        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        assert call_args[0][0] == "rra:session:test-session"

    @patch("rra.storage.session_store.redis")
    def test_redis_delete(self, mock_redis_module):
        """Test Redis delete operation."""
        mock_client = MagicMock()
        mock_redis_module.from_url.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.delete.return_value = 1

        store = RedisSessionStore(redis_url="redis://localhost:6379/0")

        result = store.delete("test-session")

        assert result is True
        mock_client.delete.assert_called_with("rra:session:test-session")


class TestSessionStoreFactory:
    """Tests for session store factory functions."""

    def setup_method(self):
        """Reset global state before each test."""
        reset_session_store()

    def teardown_method(self):
        """Clean up after each test."""
        reset_session_store()

    def test_create_in_memory_by_default(self):
        """Test that in-memory store is created when no Redis URL set."""
        with patch.dict("os.environ", {}, clear=True):
            store = create_session_store()
            assert isinstance(store, InMemorySessionStore)

    def test_get_session_store_singleton(self):
        """Test that get_session_store returns same instance."""
        store1 = get_session_store()
        store2 = get_session_store()

        assert store1 is store2

    def test_reset_session_store(self):
        """Test resetting the global store."""
        store1 = get_session_store()
        reset_session_store()
        store2 = get_session_store()

        assert store1 is not store2

    @patch("rra.storage.session_store.RedisSessionStore")
    def test_create_redis_when_url_set(self, mock_redis_class):
        """Test that Redis store is created when URL is set."""
        mock_redis_class.return_value = MagicMock()

        with patch.dict("os.environ", {"RRA_REDIS_URL": "redis://localhost:6379"}):
            store = create_session_store()

        mock_redis_class.assert_called_once_with(redis_url="redis://localhost:6379")

    @patch("rra.storage.session_store.RedisSessionStore")
    def test_fallback_to_memory_on_redis_error(self, mock_redis_class):
        """Test fallback to in-memory when Redis fails."""
        mock_redis_class.side_effect = Exception("Connection failed")

        with patch.dict("os.environ", {"RRA_REDIS_URL": "redis://localhost:6379"}):
            store = create_session_store()

        assert isinstance(store, InMemorySessionStore)
