# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for the Analytics Dashboard API.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import os

# Set up authentication for tests and disable rate limiting
os.environ["RRA_DEV_MODE"] = "true"
os.environ["RRA_API_KEY"] = "test-key"
os.environ["RRA_RATE_LIMIT_ENABLED"] = "false"

from rra.api.server import create_app

# Create fresh app with rate limiting disabled
app = create_app()
from rra.api.analytics import (
    AnalyticsStore,
    AnalyticsEvent,
    MetricType,
    TimeRange,
    get_time_range_bounds,
    calculate_rate,
)


client = TestClient(app, headers={"X-API-Key": "test-key"})


class TestAnalyticsStore:
    """Test the analytics storage layer."""

    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.store = AnalyticsStore(base_path=Path(self.temp_dir))

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_event(self):
        """Test recording an analytics event."""
        event = AnalyticsEvent(
            event_type=MetricType.PAGE_VIEW,
            agent_id="test-agent-1",
            metadata={"source": "test"},
        )
        self.store.record_event(event)

        events = self.store.get_events()
        assert len(events) == 1
        assert events[0]["event_type"] == MetricType.PAGE_VIEW.value
        assert events[0]["agent_id"] == "test-agent-1"

    def test_get_events_by_agent(self):
        """Test filtering events by agent ID."""
        for i in range(5):
            self.store.record_event(AnalyticsEvent(
                event_type=MetricType.PAGE_VIEW,
                agent_id=f"agent-{i % 2}",  # Alternates between 0 and 1
            ))

        agent_0_events = self.store.get_events(agent_id="agent-0")
        agent_1_events = self.store.get_events(agent_id="agent-1")

        assert len(agent_0_events) == 3
        assert len(agent_1_events) == 2

    def test_get_events_by_type(self):
        """Test filtering events by event type."""
        self.store.record_event(AnalyticsEvent(
            event_type=MetricType.PAGE_VIEW,
            agent_id="test",
        ))
        self.store.record_event(AnalyticsEvent(
            event_type=MetricType.NEGOTIATION_START,
            agent_id="test",
        ))
        self.store.record_event(AnalyticsEvent(
            event_type=MetricType.PAGE_VIEW,
            agent_id="test",
        ))

        view_events = self.store.get_events(event_type=MetricType.PAGE_VIEW)
        assert len(view_events) == 2

    def test_get_events_by_time_range(self):
        """Test filtering events by time range."""
        now = datetime.utcnow()

        # Record event with past timestamp
        old_event = AnalyticsEvent(
            event_type=MetricType.PAGE_VIEW,
            agent_id="test",
            timestamp=(now - timedelta(days=10)).isoformat(),
        )
        self.store.record_event(old_event)

        # Record recent event
        new_event = AnalyticsEvent(
            event_type=MetricType.PAGE_VIEW,
            agent_id="test",
            timestamp=now.isoformat(),
        )
        self.store.record_event(new_event)

        # Query last week
        start_time = now - timedelta(days=7)
        recent_events = self.store.get_events(start_time=start_time)

        assert len(recent_events) == 1

    def test_persistence(self):
        """Test that events persist across store instances."""
        # Record event
        self.store.record_event(AnalyticsEvent(
            event_type=MetricType.LICENSE_PURCHASE,
            agent_id="persist-test",
            value=0.05,
        ))

        # Create new store instance with same path
        new_store = AnalyticsStore(base_path=Path(self.temp_dir))
        events = new_store.get_events()

        assert len(events) == 1
        assert events[0]["agent_id"] == "persist-test"
        assert events[0]["value"] == 0.05

    def test_get_unique_agents(self):
        """Test getting list of unique agents."""
        for agent in ["agent-1", "agent-2", "agent-1", "agent-3"]:
            self.store.record_event(AnalyticsEvent(
                event_type=MetricType.PAGE_VIEW,
                agent_id=agent,
            ))

        agents = self.store.get_unique_agents()
        assert len(agents) == 3
        assert set(agents) == {"agent-1", "agent-2", "agent-3"}


class TestHelperFunctions:
    """Test helper functions."""

    def test_calculate_rate_normal(self):
        """Test rate calculation with normal values."""
        assert calculate_rate(50, 100) == 50.0
        assert calculate_rate(1, 4) == 25.0
        assert calculate_rate(3, 10) == 30.0

    def test_calculate_rate_zero_denominator(self):
        """Test rate calculation with zero denominator."""
        assert calculate_rate(10, 0) == 0.0
        assert calculate_rate(0, 0) == 0.0

    def test_get_time_range_bounds_day(self):
        """Test time range bounds for day."""
        start, end = get_time_range_bounds(TimeRange.DAY)
        diff = end - start
        assert diff.days == 1 or (diff.days == 0 and diff.seconds > 86000)

    def test_get_time_range_bounds_week(self):
        """Test time range bounds for week."""
        start, end = get_time_range_bounds(TimeRange.WEEK)
        diff = end - start
        assert diff.days == 7 or diff.days == 6

    def test_get_time_range_bounds_month(self):
        """Test time range bounds for month."""
        start, end = get_time_range_bounds(TimeRange.MONTH)
        diff = end - start
        assert diff.days == 30 or diff.days == 29


class TestAnalyticsAPI:
    """Test analytics API endpoints."""

    def test_record_event_endpoint(self):
        """Test recording an event via API."""
        response = client.post(
            "/api/analytics/event",
            json={
                "event_type": "page_view",
                "agent_id": "api-test-agent",
                "metadata": {"page": "home"},
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recorded"
        assert data["event_type"] == "page_view"

    def test_overview_endpoint(self):
        """Test analytics overview endpoint."""
        response = client.get("/api/analytics/overview?time_range=week")
        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "metrics" in data
        assert "revenue" in data
        assert "total_events" in data

    def test_agent_analytics_endpoint(self):
        """Test agent-specific analytics."""
        # First record some events
        client.post("/api/analytics/event", json={
            "event_type": "page_view",
            "agent_id": "analytics-test-agent",
        })

        response = client.get("/api/analytics/agent/analytics-test-agent?time_range=week")
        assert response.status_code == 200
        data = response.json()

        assert data["agent_id"] == "analytics-test-agent"
        assert "total_views" in data
        assert "negotiations_started" in data
        assert "conversion_rate" in data

    def test_funnel_endpoint(self):
        """Test funnel analytics endpoint."""
        response = client.get("/api/analytics/funnel?time_range=week")
        assert response.status_code == 200
        data = response.json()

        assert "views" in data
        assert "negotiations_started" in data
        assert "purchases_completed" in data
        assert "overall_conversion_rate" in data

    def test_revenue_endpoint(self):
        """Test revenue analytics endpoint."""
        response = client.get("/api/analytics/revenue?time_range=month")
        assert response.status_code == 200
        data = response.json()

        assert "total_revenue_eth" in data
        assert "total_revenue_usd" in data
        assert "license_count" in data
        assert "top_agents" in data

    def test_timeseries_endpoint(self):
        """Test time-series data endpoint."""
        response = client.get(
            "/api/analytics/timeseries",
            params={
                "metric": "page_view",
                "time_range": "week",
                "granularity": "day",
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["metric"] == "page_view"
        assert data["granularity"] == "day"
        assert "data" in data
        assert "total" in data

    def test_agents_list_endpoint(self):
        """Test listing agents with metrics."""
        response = client.get("/api/analytics/agents?time_range=week&sort_by=revenue")
        assert response.status_code == 200
        data = response.json()

        assert "agents" in data
        assert "total_agents" in data
        assert data["sort_by"] == "revenue"

    def test_export_json(self):
        """Test exporting data as JSON."""
        response = client.get("/api/analytics/export?time_range=week&format=json")
        assert response.status_code == 200
        data = response.json()

        assert data["format"] == "json"
        assert "events" in data
        assert "event_count" in data

    def test_export_csv(self):
        """Test exporting data as CSV."""
        response = client.get("/api/analytics/export?time_range=week&format=csv")
        assert response.status_code == 200
        data = response.json()

        assert data["format"] == "csv"
        assert "content" in data
        assert "timestamp" in data["content"]  # CSV header

    def test_dashboard_html(self):
        """Test dashboard HTML endpoint."""
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "RRA Analytics Dashboard" in response.text
        assert "chart.js" in response.text


class TestAnalyticsMetrics:
    """Test metric calculations."""

    def test_conversion_rate_calculation(self):
        """Test that conversion rates are calculated correctly."""
        # Record a funnel of events
        for _ in range(100):
            client.post("/api/analytics/event", json={
                "event_type": "page_view",
                "agent_id": "conversion-test",
            })

        for _ in range(25):
            client.post("/api/analytics/event", json={
                "event_type": "negotiation_start",
                "agent_id": "conversion-test",
            })

        for _ in range(5):
            client.post("/api/analytics/event", json={
                "event_type": "license_purchase",
                "agent_id": "conversion-test",
                "value": 0.01,
            })

        response = client.get("/api/analytics/agent/conversion-test?time_range=day")
        data = response.json()

        # Should have reasonable conversion rate
        assert data["negotiations_started"] >= 25
        assert data["licenses_sold"] >= 5

    def test_revenue_tracking(self):
        """Test that revenue is tracked correctly."""
        # Record purchase events with values
        for i in range(3):
            client.post("/api/analytics/event", json={
                "event_type": "license_purchase",
                "agent_id": "revenue-test",
                "value": 0.1 * (i + 1),  # 0.1, 0.2, 0.3
            })

        response = client.get("/api/analytics/agent/revenue-test?time_range=day")
        data = response.json()

        # Total should be 0.6 ETH
        assert data["licenses_sold"] >= 3
        assert data["total_revenue_eth"] >= 0.6


class TestAnalyticsValidation:
    """Test input validation."""

    def test_invalid_time_range(self):
        """Test that invalid time range is rejected."""
        response = client.get("/api/analytics/overview?time_range=invalid")
        assert response.status_code == 422

    def test_invalid_metric_type(self):
        """Test that invalid metric type is rejected."""
        response = client.get("/api/analytics/timeseries?metric=invalid_metric")
        assert response.status_code == 422

    def test_invalid_granularity(self):
        """Test that invalid granularity is rejected."""
        response = client.get("/api/analytics/timeseries?granularity=minute")
        assert response.status_code == 422

    def test_invalid_sort_by(self):
        """Test that invalid sort_by is rejected."""
        response = client.get("/api/analytics/agents?sort_by=invalid")
        assert response.status_code == 422

    def test_invalid_export_format(self):
        """Test that invalid export format is rejected."""
        response = client.get("/api/analytics/export?format=xml")
        assert response.status_code == 422
