# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Analytics Dashboard API for RRA Module.

Provides comprehensive analytics and insights for:
- Repository/agent performance metrics
- License sales and revenue tracking
- Negotiation funnel analysis
- Widget usage statistics
- Fork tracking and derivative metrics
- Historical trends and time-series data
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from collections import defaultdict
from enum import Enum

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from rra.api.auth import verify_api_key


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# =============================================================================
# Configuration
# =============================================================================

ANALYTICS_DATA_PATH = Path(os.environ.get("RRA_ANALYTICS_PATH", "data/analytics"))


# =============================================================================
# Models
# =============================================================================

class TimeRange(str, Enum):
    """Time range for analytics queries."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL = "all"


class MetricType(str, Enum):
    """Types of metrics tracked."""
    PAGE_VIEW = "page_view"
    NEGOTIATION_START = "negotiation_start"
    NEGOTIATION_MESSAGE = "negotiation_message"
    NEGOTIATION_COMPLETE = "negotiation_complete"
    LICENSE_PURCHASE = "license_purchase"
    WIDGET_OPEN = "widget_open"
    WIDGET_MESSAGE = "widget_message"
    WEBHOOK_TRIGGER = "webhook_trigger"
    FORK_DETECTED = "fork_detected"
    DERIVATIVE_REGISTERED = "derivative_registered"


class AnalyticsEvent(BaseModel):
    """Single analytics event."""
    event_type: MetricType
    agent_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    value: Optional[float] = None


class AgentMetrics(BaseModel):
    """Aggregated metrics for an agent."""
    agent_id: str
    period: str
    total_views: int = 0
    unique_visitors: int = 0
    negotiations_started: int = 0
    negotiations_completed: int = 0
    conversion_rate: float = 0.0
    total_messages: int = 0
    avg_messages_per_negotiation: float = 0.0
    licenses_sold: int = 0
    total_revenue_eth: float = 0.0
    widget_opens: int = 0
    webhook_triggers: int = 0
    forks_detected: int = 0
    derivatives_registered: int = 0


class RevenueMetrics(BaseModel):
    """Revenue-specific metrics."""
    period: str
    total_revenue_eth: float = 0.0
    total_revenue_usd: float = 0.0
    license_count: int = 0
    avg_license_price_eth: float = 0.0
    streaming_revenue_eth: float = 0.0
    one_time_revenue_eth: float = 0.0
    top_agents: List[Dict[str, Any]] = []


class FunnelMetrics(BaseModel):
    """Negotiation funnel metrics."""
    period: str
    views: int = 0
    negotiations_started: int = 0
    offers_made: int = 0
    offers_accepted: int = 0
    purchases_completed: int = 0
    view_to_negotiation_rate: float = 0.0
    negotiation_to_offer_rate: float = 0.0
    offer_to_purchase_rate: float = 0.0
    overall_conversion_rate: float = 0.0


# =============================================================================
# Analytics Storage
# =============================================================================

class AnalyticsStore:
    """Persistent storage for analytics events."""

    def __init__(self, base_path: Path = ANALYTICS_DATA_PATH):
        """Initialize the analytics store."""
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._events: List[Dict[str, Any]] = []
        self._load_events()

    def _get_events_file(self) -> Path:
        """Get the events file path."""
        return self.base_path / "events.json"

    def _load_events(self) -> None:
        """Load events from storage."""
        events_file = self._get_events_file()
        if events_file.exists():
            try:
                with open(events_file, 'r') as f:
                    self._events = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._events = []

    def _save_events(self) -> None:
        """Save events to storage."""
        with open(self._get_events_file(), 'w') as f:
            json.dump(self._events, f, indent=2, default=str)

    def record_event(self, event: AnalyticsEvent) -> None:
        """Record a new analytics event."""
        self._events.append(event.model_dump())
        self._save_events()

    def get_events(
        self,
        agent_id: Optional[str] = None,
        event_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Query events with optional filters."""
        events = self._events

        if agent_id:
            events = [e for e in events if e.get("agent_id") == agent_id]

        if event_type:
            events = [e for e in events if e.get("event_type") == event_type.value]

        if start_time:
            events = [
                e for e in events
                if datetime.fromisoformat(e.get("timestamp", "")) >= start_time
            ]

        if end_time:
            events = [
                e for e in events
                if datetime.fromisoformat(e.get("timestamp", "")) <= end_time
            ]

        return events

    def get_unique_agents(self) -> List[str]:
        """Get list of unique agent IDs."""
        return list(set(e.get("agent_id") for e in self._events if e.get("agent_id")))


# Global analytics store instance
_analytics_store = AnalyticsStore()


# =============================================================================
# Helper Functions
# =============================================================================

def get_time_range_bounds(time_range: TimeRange) -> tuple[datetime, datetime]:
    """Get start and end datetime for a time range."""
    now = datetime.utcnow()
    end_time = now

    if time_range == TimeRange.HOUR:
        start_time = now - timedelta(hours=1)
    elif time_range == TimeRange.DAY:
        start_time = now - timedelta(days=1)
    elif time_range == TimeRange.WEEK:
        start_time = now - timedelta(weeks=1)
    elif time_range == TimeRange.MONTH:
        start_time = now - timedelta(days=30)
    elif time_range == TimeRange.QUARTER:
        start_time = now - timedelta(days=90)
    elif time_range == TimeRange.YEAR:
        start_time = now - timedelta(days=365)
    else:  # ALL
        start_time = datetime.min

    return start_time, end_time


def calculate_rate(numerator: int, denominator: int) -> float:
    """Calculate a rate/percentage safely."""
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/event")
async def record_analytics_event(
    event: AnalyticsEvent,
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, str]:
    """
    Record an analytics event.

    Use this endpoint to track user actions and system events.
    """
    _analytics_store.record_event(event)
    return {"status": "recorded", "event_type": event.event_type.value}


@router.get("/overview")
async def get_analytics_overview(
    time_range: TimeRange = Query(default=TimeRange.WEEK),
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Get high-level analytics overview.

    Returns summary metrics across all agents for the specified time range.
    """
    start_time, end_time = get_time_range_bounds(time_range)
    events = _analytics_store.get_events(start_time=start_time, end_time=end_time)

    # Count by event type
    event_counts = defaultdict(int)
    for event in events:
        event_counts[event.get("event_type", "unknown")] += 1

    # Calculate revenue
    purchase_events = [e for e in events if e.get("event_type") == MetricType.LICENSE_PURCHASE.value]
    total_revenue = sum(e.get("value", 0) or 0 for e in purchase_events)

    # Unique agents and sessions
    unique_agents = len(set(e.get("agent_id") for e in events if e.get("agent_id")))
    unique_sessions = len(set(e.get("session_id") for e in events if e.get("session_id")))

    return {
        "period": time_range.value,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "total_events": len(events),
        "unique_agents": unique_agents,
        "unique_sessions": unique_sessions,
        "metrics": {
            "page_views": event_counts.get(MetricType.PAGE_VIEW.value, 0),
            "negotiations_started": event_counts.get(MetricType.NEGOTIATION_START.value, 0),
            "negotiations_completed": event_counts.get(MetricType.NEGOTIATION_COMPLETE.value, 0),
            "licenses_purchased": event_counts.get(MetricType.LICENSE_PURCHASE.value, 0),
            "widget_opens": event_counts.get(MetricType.WIDGET_OPEN.value, 0),
            "webhook_triggers": event_counts.get(MetricType.WEBHOOK_TRIGGER.value, 0),
            "forks_detected": event_counts.get(MetricType.FORK_DETECTED.value, 0),
            "derivatives_registered": event_counts.get(MetricType.DERIVATIVE_REGISTERED.value, 0),
        },
        "revenue": {
            "total_eth": total_revenue,
            "license_count": len(purchase_events),
            "avg_price_eth": total_revenue / len(purchase_events) if purchase_events else 0,
        },
    }


@router.get("/agent/{agent_id}")
async def get_agent_analytics(
    agent_id: str,
    time_range: TimeRange = Query(default=TimeRange.WEEK),
    authenticated: bool = Depends(verify_api_key),
) -> AgentMetrics:
    """
    Get detailed analytics for a specific agent.

    Returns comprehensive metrics for the specified agent and time range.
    """
    start_time, end_time = get_time_range_bounds(time_range)
    events = _analytics_store.get_events(
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
    )

    # Count by event type
    event_counts = defaultdict(int)
    for event in events:
        event_counts[event.get("event_type", "unknown")] += 1

    # Unique visitors
    unique_visitors = len(set(
        e.get("session_id") or e.get("user_id")
        for e in events
        if e.get("event_type") == MetricType.PAGE_VIEW.value
    ))

    # Revenue calculation
    purchase_events = [e for e in events if e.get("event_type") == MetricType.LICENSE_PURCHASE.value]
    total_revenue = sum(e.get("value", 0) or 0 for e in purchase_events)

    # Message count
    message_events = [
        e for e in events
        if e.get("event_type") in [MetricType.NEGOTIATION_MESSAGE.value, MetricType.WIDGET_MESSAGE.value]
    ]

    negotiations_started = event_counts.get(MetricType.NEGOTIATION_START.value, 0)
    negotiations_completed = event_counts.get(MetricType.NEGOTIATION_COMPLETE.value, 0)

    return AgentMetrics(
        agent_id=agent_id,
        period=time_range.value,
        total_views=event_counts.get(MetricType.PAGE_VIEW.value, 0),
        unique_visitors=unique_visitors,
        negotiations_started=negotiations_started,
        negotiations_completed=negotiations_completed,
        conversion_rate=calculate_rate(negotiations_completed, negotiations_started),
        total_messages=len(message_events),
        avg_messages_per_negotiation=(
            len(message_events) / negotiations_started if negotiations_started > 0 else 0
        ),
        licenses_sold=len(purchase_events),
        total_revenue_eth=total_revenue,
        widget_opens=event_counts.get(MetricType.WIDGET_OPEN.value, 0),
        webhook_triggers=event_counts.get(MetricType.WEBHOOK_TRIGGER.value, 0),
        forks_detected=event_counts.get(MetricType.FORK_DETECTED.value, 0),
        derivatives_registered=event_counts.get(MetricType.DERIVATIVE_REGISTERED.value, 0),
    )


@router.get("/funnel")
async def get_funnel_analytics(
    agent_id: Optional[str] = None,
    time_range: TimeRange = Query(default=TimeRange.WEEK),
    authenticated: bool = Depends(verify_api_key),
) -> FunnelMetrics:
    """
    Get negotiation funnel analytics.

    Shows conversion rates at each stage of the negotiation process.
    """
    start_time, end_time = get_time_range_bounds(time_range)
    events = _analytics_store.get_events(
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
    )

    # Count funnel stages
    views = len([e for e in events if e.get("event_type") == MetricType.PAGE_VIEW.value])
    negotiations_started = len([e for e in events if e.get("event_type") == MetricType.NEGOTIATION_START.value])
    negotiations_completed = len([e for e in events if e.get("event_type") == MetricType.NEGOTIATION_COMPLETE.value])
    purchases = len([e for e in events if e.get("event_type") == MetricType.LICENSE_PURCHASE.value])

    # Offers made/accepted from metadata
    offers_made = len([
        e for e in events
        if (e.get("metadata") or {}).get("action") == "offer_made"
    ])
    offers_accepted = len([
        e for e in events
        if (e.get("metadata") or {}).get("action") == "offer_accepted"
    ])

    return FunnelMetrics(
        period=time_range.value,
        views=views,
        negotiations_started=negotiations_started,
        offers_made=offers_made or negotiations_completed,  # Fallback
        offers_accepted=offers_accepted or purchases,  # Fallback
        purchases_completed=purchases,
        view_to_negotiation_rate=calculate_rate(negotiations_started, views),
        negotiation_to_offer_rate=calculate_rate(negotiations_completed, negotiations_started),
        offer_to_purchase_rate=calculate_rate(purchases, negotiations_completed) if negotiations_completed else 0,
        overall_conversion_rate=calculate_rate(purchases, views),
    )


@router.get("/revenue")
async def get_revenue_analytics(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    authenticated: bool = Depends(verify_api_key),
) -> RevenueMetrics:
    """
    Get revenue analytics.

    Returns revenue metrics across all agents for the specified time range.
    """
    start_time, end_time = get_time_range_bounds(time_range)
    events = _analytics_store.get_events(
        event_type=MetricType.LICENSE_PURCHASE,
        start_time=start_time,
        end_time=end_time,
    )

    # Calculate totals
    total_revenue = sum(e.get("value", 0) or 0 for e in events)
    license_count = len(events)

    # Revenue by type (from metadata)
    streaming_revenue = sum(
        e.get("value", 0) or 0
        for e in events
        if (e.get("metadata") or {}).get("license_type") == "streaming"
    )
    one_time_revenue = total_revenue - streaming_revenue

    # Top agents by revenue
    agent_revenue: Dict[str, float] = defaultdict(float)
    for event in events:
        agent_id = event.get("agent_id", "unknown")
        agent_revenue[agent_id] += event.get("value", 0) or 0

    top_agents = sorted(
        [{"agent_id": k, "revenue_eth": v} for k, v in agent_revenue.items()],
        key=lambda x: x["revenue_eth"],
        reverse=True,
    )[:10]

    # ETH to USD conversion (placeholder rate)
    eth_usd_rate = 2000.0  # Would use real oracle in production

    return RevenueMetrics(
        period=time_range.value,
        total_revenue_eth=total_revenue,
        total_revenue_usd=total_revenue * eth_usd_rate,
        license_count=license_count,
        avg_license_price_eth=total_revenue / license_count if license_count > 0 else 0,
        streaming_revenue_eth=streaming_revenue,
        one_time_revenue_eth=one_time_revenue,
        top_agents=top_agents,
    )


@router.get("/timeseries")
async def get_timeseries_data(
    metric: MetricType = Query(default=MetricType.PAGE_VIEW),
    agent_id: Optional[str] = None,
    time_range: TimeRange = Query(default=TimeRange.WEEK),
    granularity: str = Query(default="day", pattern="^(hour|day|week)$"),
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Get time-series data for a specific metric.

    Returns data points grouped by the specified granularity.
    """
    start_time, end_time = get_time_range_bounds(time_range)
    events = _analytics_store.get_events(
        agent_id=agent_id,
        event_type=metric,
        start_time=start_time,
        end_time=end_time,
    )

    # Group by time bucket
    buckets: Dict[str, int] = defaultdict(int)

    for event in events:
        timestamp = datetime.fromisoformat(event.get("timestamp", datetime.utcnow().isoformat()))

        if granularity == "hour":
            bucket = timestamp.strftime("%Y-%m-%d %H:00")
        elif granularity == "day":
            bucket = timestamp.strftime("%Y-%m-%d")
        else:  # week
            # Get start of week
            week_start = timestamp - timedelta(days=timestamp.weekday())
            bucket = week_start.strftime("%Y-%m-%d")

        buckets[bucket] += 1

    # Convert to sorted list
    data_points = sorted(
        [{"time": k, "count": v} for k, v in buckets.items()],
        key=lambda x: x["time"],
    )

    return {
        "metric": metric.value,
        "agent_id": agent_id,
        "period": time_range.value,
        "granularity": granularity,
        "data": data_points,
        "total": sum(d["count"] for d in data_points),
    }


@router.get("/agents")
async def list_agents_with_metrics(
    time_range: TimeRange = Query(default=TimeRange.WEEK),
    sort_by: str = Query(default="revenue", pattern="^(revenue|views|conversions|licenses)$"),
    limit: int = Query(default=20, ge=1, le=100),
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    List all agents with their metrics.

    Returns a ranked list of agents by the specified metric.
    """
    start_time, end_time = get_time_range_bounds(time_range)
    events = _analytics_store.get_events(start_time=start_time, end_time=end_time)

    # Aggregate metrics by agent
    agent_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "views": 0,
        "negotiations": 0,
        "licenses": 0,
        "revenue": 0.0,
    })

    for event in events:
        agent_id = event.get("agent_id")
        if not agent_id:
            continue

        event_type = event.get("event_type")
        if event_type == MetricType.PAGE_VIEW.value:
            agent_metrics[agent_id]["views"] += 1
        elif event_type == MetricType.NEGOTIATION_START.value:
            agent_metrics[agent_id]["negotiations"] += 1
        elif event_type == MetricType.LICENSE_PURCHASE.value:
            agent_metrics[agent_id]["licenses"] += 1
            agent_metrics[agent_id]["revenue"] += event.get("value", 0) or 0

    # Convert to list and sort
    agents_list = [
        {
            "agent_id": k,
            "views": v["views"],
            "negotiations": v["negotiations"],
            "licenses": v["licenses"],
            "revenue_eth": v["revenue"],
            "conversion_rate": calculate_rate(v["licenses"], v["negotiations"]),
        }
        for k, v in agent_metrics.items()
    ]

    sort_key_map = {
        "revenue": "revenue_eth",
        "views": "views",
        "conversions": "conversion_rate",
        "licenses": "licenses",
    }

    agents_list.sort(key=lambda x: x[sort_key_map[sort_by]], reverse=True)

    return {
        "period": time_range.value,
        "total_agents": len(agents_list),
        "sort_by": sort_by,
        "agents": agents_list[:limit],
    }


@router.get("/export")
async def export_analytics(
    agent_id: Optional[str] = None,
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    format: str = Query(default="json", pattern="^(json|csv)$"),
    authenticated: bool = Depends(verify_api_key),
) -> Dict[str, Any]:
    """
    Export analytics data.

    Returns raw event data for the specified filters in JSON or CSV format.
    """
    start_time, end_time = get_time_range_bounds(time_range)
    events = _analytics_store.get_events(
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
    )

    if format == "csv":
        # Generate CSV content
        if not events:
            csv_content = "timestamp,event_type,agent_id,value,session_id\n"
        else:
            headers = ["timestamp", "event_type", "agent_id", "value", "session_id"]
            rows = [",".join(headers)]
            for event in events:
                row = [
                    str(event.get("timestamp", "")),
                    str(event.get("event_type", "")),
                    str(event.get("agent_id", "")),
                    str(event.get("value", "")),
                    str(event.get("session_id", "")),
                ]
                rows.append(",".join(row))
            csv_content = "\n".join(rows)

        return {
            "format": "csv",
            "content": csv_content,
            "event_count": len(events),
        }

    return {
        "format": "json",
        "events": events,
        "event_count": len(events),
        "period": time_range.value,
    }


@router.get("/dashboard")
async def get_dashboard_html() -> HTMLResponse:
    """
    Serve the analytics dashboard HTML page.

    Provides a visual dashboard for viewing analytics.
    """
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RRA Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        .header {
            background: linear-gradient(135deg, #0066ff, #0052cc);
            color: white;
            padding: 24px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 24px; font-weight: 600; }
        .time-selector {
            display: flex;
            gap: 8px;
        }
        .time-selector button {
            padding: 8px 16px;
            border: 1px solid rgba(255,255,255,0.3);
            background: transparent;
            color: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .time-selector button.active {
            background: white;
            color: #0066ff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .metric-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .metric-card .label {
            font-size: 13px;
            color: #666;
            margin-bottom: 8px;
        }
        .metric-card .value {
            font-size: 28px;
            font-weight: 700;
            color: #0066ff;
        }
        .metric-card .change {
            font-size: 12px;
            color: #22c55e;
            margin-top: 4px;
        }
        .metric-card .change.negative { color: #ef4444; }
        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }
        .chart-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .chart-card h3 {
            font-size: 16px;
            margin-bottom: 16px;
            color: #333;
        }
        .table-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .table-card h3 {
            font-size: 16px;
            margin-bottom: 16px;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            font-size: 12px;
            color: #666;
            font-weight: 600;
            text-transform: uppercase;
        }
        .funnel {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .funnel-step {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .funnel-bar {
            height: 32px;
            background: linear-gradient(90deg, #0066ff, #00a3ff);
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 12px;
            color: white;
            font-size: 12px;
            font-weight: 600;
            min-width: 40px;
        }
        .funnel-label {
            font-size: 13px;
            color: #666;
            min-width: 120px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 16px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>RRA Analytics Dashboard</h1>
        <div class="time-selector">
            <button onclick="setTimeRange('day')">24h</button>
            <button onclick="setTimeRange('week')" class="active">7d</button>
            <button onclick="setTimeRange('month')">30d</button>
            <button onclick="setTimeRange('quarter')">90d</button>
        </div>
    </div>

    <div class="container">
        <div class="metrics-grid" id="metrics-grid">
            <div class="loading">Loading metrics...</div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3>Activity Over Time</h3>
                <canvas id="activity-chart"></canvas>
            </div>
            <div class="chart-card">
                <h3>Conversion Funnel</h3>
                <div class="funnel" id="funnel"></div>
            </div>
        </div>

        <div class="table-card">
            <h3>Top Performing Agents</h3>
            <table id="agents-table">
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Views</th>
                        <th>Negotiations</th>
                        <th>Licenses</th>
                        <th>Revenue (ETH)</th>
                        <th>Conversion</th>
                    </tr>
                </thead>
                <tbody id="agents-tbody">
                    <tr><td colspan="6" class="loading">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let currentTimeRange = 'week';
        let activityChart = null;

        async function fetchData(endpoint, params = {}) {
            const url = new URL(endpoint, window.location.origin);
            Object.entries(params).forEach(([k, v]) => url.searchParams.append(k, v));
            const response = await fetch(url);
            return response.json();
        }

        async function loadDashboard() {
            try {
                // Load overview
                const overview = await fetchData('/api/analytics/overview', { time_range: currentTimeRange });
                renderMetrics(overview);

                // Load funnel
                const funnel = await fetchData('/api/analytics/funnel', { time_range: currentTimeRange });
                renderFunnel(funnel);

                // Load timeseries
                const timeseries = await fetchData('/api/analytics/timeseries', {
                    time_range: currentTimeRange,
                    metric: 'page_view',
                    granularity: currentTimeRange === 'day' ? 'hour' : 'day'
                });
                renderActivityChart(timeseries);

                // Load agents
                const agents = await fetchData('/api/analytics/agents', { time_range: currentTimeRange });
                renderAgentsTable(agents);

            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        function renderMetrics(data) {
            const metrics = data.metrics;
            const revenue = data.revenue;

            document.getElementById('metrics-grid').innerHTML = `
                <div class="metric-card">
                    <div class="label">Page Views</div>
                    <div class="value">${metrics.page_views.toLocaleString()}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Negotiations Started</div>
                    <div class="value">${metrics.negotiations_started.toLocaleString()}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Licenses Sold</div>
                    <div class="value">${metrics.licenses_purchased.toLocaleString()}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Revenue (ETH)</div>
                    <div class="value">${revenue.total_eth.toFixed(4)}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Widget Opens</div>
                    <div class="value">${metrics.widget_opens.toLocaleString()}</div>
                </div>
                <div class="metric-card">
                    <div class="label">Forks Detected</div>
                    <div class="value">${metrics.forks_detected.toLocaleString()}</div>
                </div>
            `;
        }

        function renderFunnel(data) {
            const maxValue = Math.max(data.views, 1);
            document.getElementById('funnel').innerHTML = `
                <div class="funnel-step">
                    <span class="funnel-label">Views</span>
                    <div class="funnel-bar" style="width: 100%">${data.views}</div>
                </div>
                <div class="funnel-step">
                    <span class="funnel-label">Negotiations</span>
                    <div class="funnel-bar" style="width: ${(data.negotiations_started / maxValue) * 100}%">${data.negotiations_started}</div>
                </div>
                <div class="funnel-step">
                    <span class="funnel-label">Offers Made</span>
                    <div class="funnel-bar" style="width: ${(data.offers_made / maxValue) * 100}%">${data.offers_made}</div>
                </div>
                <div class="funnel-step">
                    <span class="funnel-label">Purchases</span>
                    <div class="funnel-bar" style="width: ${(data.purchases_completed / maxValue) * 100}%">${data.purchases_completed}</div>
                </div>
            `;
        }

        function renderActivityChart(data) {
            const ctx = document.getElementById('activity-chart').getContext('2d');

            if (activityChart) {
                activityChart.destroy();
            }

            activityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.data.map(d => d.time),
                    datasets: [{
                        label: 'Page Views',
                        data: data.data.map(d => d.count),
                        borderColor: '#0066ff',
                        backgroundColor: 'rgba(0, 102, 255, 0.1)',
                        fill: true,
                        tension: 0.4,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }

        function renderAgentsTable(data) {
            const tbody = document.getElementById('agents-tbody');

            if (data.agents.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No data available</td></tr>';
                return;
            }

            tbody.innerHTML = data.agents.map(agent => `
                <tr>
                    <td>${agent.agent_id}</td>
                    <td>${agent.views.toLocaleString()}</td>
                    <td>${agent.negotiations.toLocaleString()}</td>
                    <td>${agent.licenses.toLocaleString()}</td>
                    <td>${agent.revenue_eth.toFixed(4)}</td>
                    <td>${agent.conversion_rate.toFixed(1)}%</td>
                </tr>
            `).join('');
        }

        function setTimeRange(range) {
            currentTimeRange = range;
            document.querySelectorAll('.time-selector button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            loadDashboard();
        }

        // Initial load
        loadDashboard();

        // Refresh every 60 seconds
        setInterval(loadDashboard, 60000);
    </script>
</body>
</html>
'''
    return HTMLResponse(content=html)


# =============================================================================
# Helper function to get the analytics store
# =============================================================================

def get_analytics_store() -> AnalyticsStore:
    """Get the global analytics store instance."""
    return _analytics_store
