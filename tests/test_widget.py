# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for the Embeddable Widget API.
"""

import os
from fastapi.testclient import TestClient

# Set up test environment before imports
os.environ["RRA_DEV_MODE"] = "true"
os.environ["RRA_API_KEY"] = "test-key"

from rra.api.server import app


client = TestClient(app, headers={"X-API-Key": "test-key"})


class TestWidgetAPI:
    """Test widget API endpoints."""

    def test_widget_demo_page(self):
        """Test demo page is accessible."""
        response = client.get("/api/widget/demo")
        assert response.status_code == 200
        assert "RRA Widget Demo" in response.text
        assert "RRAWidget.init" in response.text

    def test_widget_embed_js(self):
        """Test embed.js script is served correctly."""
        response = client.get("/api/widget/embed.js")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/javascript"
        assert "RRAWidget" in response.text
        assert "init" in response.text

    def test_widget_init(self):
        """Test widget initialization."""
        response = client.post(
            "/api/widget/init",
            json={
                "agent_id": "test-agent-123",
                "theme": "default",
                "position": "bottom-right",
                "primary_color": "#0066ff",
                "language": "en",
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert "widget_id" in data
        assert data["widget_id"].startswith("wgt_")
        assert data["agent_id"] == "test-agent-123"
        assert "session_token" in data
        assert "websocket_url" in data
        assert "api_base_url" in data

    def test_widget_init_with_custom_config(self):
        """Test widget initialization with custom configuration."""
        response = client.post(
            "/api/widget/init",
            json={
                "agent_id": "custom-agent",
                "theme": "dark",
                "position": "top-left",
                "primary_color": "#ff5500",
                "language": "es",
                "auto_open": True,
                "show_branding": False,
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["config"]["theme"] == "dark"
        assert data["config"]["position"] == "top-left"
        assert data["config"]["primary_color"] == "#ff5500"
        assert data["config"]["language"] == "es"
        assert data["config"]["auto_open"] is True
        assert data["config"]["show_branding"] is False

    def test_widget_config_retrieval(self):
        """Test retrieving widget configuration."""
        # First create a widget
        init_response = client.post(
            "/api/widget/init",
            json={"agent_id": "config-test-agent"}
        )
        widget_id = init_response.json()["widget_id"]

        # Then retrieve config
        response = client.get(f"/api/widget/config/{widget_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["agent_id"] == "config-test-agent"
        assert "config" in data

    def test_widget_config_not_found(self):
        """Test config retrieval for non-existent widget."""
        response = client.get("/api/widget/config/nonexistent-widget-id")
        assert response.status_code == 404

    def test_widget_event_recording(self):
        """Test recording widget analytics events."""
        # First create a widget
        init_response = client.post(
            "/api/widget/init",
            json={"agent_id": "event-test-agent"}
        )
        widget_id = init_response.json()["widget_id"]

        # Record an event
        response = client.post(
            "/api/widget/event",
            json={
                "widget_id": widget_id,
                "event_type": "widget_opened",
                "event_data": {"source": "test"},
            }
        )
        assert response.status_code == 200
        assert response.json()["status"] == "recorded"

    def test_widget_event_not_found(self):
        """Test event recording for non-existent widget."""
        response = client.post(
            "/api/widget/event",
            json={
                "widget_id": "nonexistent-widget",
                "event_type": "test_event",
            }
        )
        assert response.status_code == 404

    def test_widget_analytics(self):
        """Test retrieving widget analytics."""
        # First create a widget and record some events
        init_response = client.post(
            "/api/widget/init",
            json={"agent_id": "analytics-test-agent"}
        )
        widget_id = init_response.json()["widget_id"]

        # Record some events
        for event_type in ["widget_opened", "message_sent", "widget_closed"]:
            client.post(
                "/api/widget/event",
                json={
                    "widget_id": widget_id,
                    "event_type": event_type,
                }
            )

        # Get analytics
        response = client.get("/api/widget/analytics/analytics-test-agent")
        assert response.status_code == 200
        data = response.json()

        assert data["agent_id"] == "analytics-test-agent"
        assert "metrics" in data
        assert "total_opens" in data["metrics"]
        assert "total_messages" in data["metrics"]
        assert "unique_sessions" in data["metrics"]


class TestWidgetValidation:
    """Test widget input validation."""

    def test_invalid_theme(self):
        """Test validation rejects invalid theme."""
        response = client.post(
            "/api/widget/init",
            json={
                "agent_id": "test",
                "theme": "invalid-theme",
            }
        )
        assert response.status_code == 422

    def test_invalid_position(self):
        """Test validation rejects invalid position."""
        response = client.post(
            "/api/widget/init",
            json={
                "agent_id": "test",
                "position": "center",
            }
        )
        assert response.status_code == 422

    def test_invalid_color(self):
        """Test validation rejects invalid hex color."""
        response = client.post(
            "/api/widget/init",
            json={
                "agent_id": "test",
                "primary_color": "not-a-color",
            }
        )
        assert response.status_code == 422

    def test_invalid_language(self):
        """Test validation rejects invalid language."""
        response = client.post(
            "/api/widget/init",
            json={
                "agent_id": "test",
                "language": "xyz",
            }
        )
        assert response.status_code == 422


class TestWidgetSecurity:
    """Test widget security features."""

    def test_widget_id_entropy(self):
        """Test widget IDs have sufficient entropy."""
        # Create multiple widgets
        widget_ids = []
        for i in range(100):
            response = client.post(
                "/api/widget/init",
                json={"agent_id": f"entropy-test-{i}"}
            )
            widget_ids.append(response.json()["widget_id"])

        # All should be unique
        assert len(widget_ids) == len(set(widget_ids))

        # All should have sufficient length
        for widget_id in widget_ids:
            # wgt_ prefix + 24 hex chars
            assert len(widget_id) >= 28

    def test_session_token_entropy(self):
        """Test session tokens have sufficient entropy."""
        tokens = []
        for i in range(50):
            response = client.post(
                "/api/widget/init",
                json={"agent_id": f"token-test-{i}"}
            )
            tokens.append(response.json()["session_token"])

        # All should be unique
        assert len(tokens) == len(set(tokens))

        # All should be at least 32 characters
        for token in tokens:
            assert len(token) >= 32

    def test_embed_js_cors_headers(self):
        """Test embed.js has proper CORS headers."""
        response = client.get("/api/widget/embed.js")
        assert response.headers.get("access-control-allow-origin") == "*"
        assert "max-age" in response.headers.get("cache-control", "")
