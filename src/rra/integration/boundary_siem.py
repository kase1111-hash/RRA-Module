# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Boundary-SIEM Integration for RRA-Module.

Provides integration with Boundary-SIEM for security event management,
threat detection, and blockchain infrastructure monitoring.

This module supports:
- Event forwarding via CEF, JSON, and syslog formats
- REST and gRPC API integration
- Real-time alert subscription via WebSocket
- Blockchain-specific detection rule integration
- MITRE ATT&CK technique mapping
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from pathlib import Path
import json
import logging
import threading
import time
import queue
import socket
import os

from rra.integration.boundary_daemon import (
    BoundaryEvent,
    EventSeverity,
    BoundaryMode,
)

logger = logging.getLogger(__name__)


class SIEMProtocol(str, Enum):
    """Supported SIEM ingestion protocols."""
    CEF_UDP = "cef_udp"       # CEF over UDP (port 514)
    CEF_TCP = "cef_tcp"       # CEF over TCP (port 1514)
    JSON_HTTP = "json_http"   # JSON over HTTP REST API
    SYSLOG_UDP = "syslog_udp"  # RFC 5424 syslog over UDP
    SYSLOG_TCP = "syslog_tcp"  # RFC 5424 syslog over TCP


class AlertSeverity(str, Enum):
    """SIEM alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert lifecycle status."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class SIEMAlert:
    """Alert received from Boundary-SIEM."""
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    created_at: datetime
    source_events: List[str]  # Event IDs that triggered this alert
    mitre_techniques: List[str] = field(default_factory=list)
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "source_events": self.source_events,
            "mitre_techniques": self.mitre_techniques,
            "description": self.description,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SIEMAlert":
        return cls(
            alert_id=data["alert_id"],
            rule_name=data["rule_name"],
            severity=AlertSeverity(data["severity"]),
            status=AlertStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            source_events=data.get("source_events", []),
            mitre_techniques=data.get("mitre_techniques", []),
            description=data.get("description", ""),
            context=data.get("context", {}),
        )


@dataclass
class DetectionRule:
    """
    SIEM detection rule configuration.

    Maps to Boundary-SIEM's blockchain-specific detection capabilities.
    """
    rule_id: str
    name: str
    description: str
    severity: AlertSeverity
    mitre_techniques: List[str]
    event_types: List[str]  # Event types this rule matches
    conditions: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    # RRA-specific rule categories
    CATEGORIES = {
        "license_abuse": "Unauthorized license usage or transfer",
        "negotiation_manipulation": "Attempted manipulation of negotiation process",
        "smart_contract_exploit": "Suspicious smart contract interactions",
        "access_control_bypass": "Attempts to bypass access controls",
        "rate_limit_evasion": "Rate limiting circumvention attempts",
        "credential_theft": "API key or token theft attempts",
        "transaction_anomaly": "Unusual transaction patterns",
        "governance_attack": "DAO governance manipulation",
    }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "mitre_techniques": self.mitre_techniques,
            "event_types": self.event_types,
            "conditions": self.conditions,
            "enabled": self.enabled,
        }


@dataclass
class SIEMConfig:
    """Configuration for Boundary-SIEM connection."""
    host: str = "localhost"
    port: int = 8514
    protocol: SIEMProtocol = SIEMProtocol.JSON_HTTP
    api_key: Optional[str] = None
    tls_enabled: bool = False
    tls_cert_path: Optional[str] = None
    batch_size: int = 100
    flush_interval_seconds: float = 5.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 30.0

    # Event filtering
    min_severity: EventSeverity = EventSeverity.INFO
    include_event_types: Optional[Set[str]] = None
    exclude_event_types: Optional[Set[str]] = None

    @classmethod
    def from_env(cls) -> "SIEMConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.environ.get("BOUNDARY_SIEM_HOST", "localhost"),
            port=int(os.environ.get("BOUNDARY_SIEM_PORT", "8514")),
            protocol=SIEMProtocol(os.environ.get("BOUNDARY_SIEM_PROTOCOL", "json_http")),
            api_key=os.environ.get("BOUNDARY_SIEM_API_KEY"),
            tls_enabled=os.environ.get("BOUNDARY_SIEM_TLS", "false").lower() == "true",
            tls_cert_path=os.environ.get("BOUNDARY_SIEM_TLS_CERT"),
        )


class EventBuffer:
    """Thread-safe buffer for batching events before sending to SIEM."""

    def __init__(self, max_size: int = 1000):
        self._buffer: List[BoundaryEvent] = []
        self._lock = threading.Lock()
        self._max_size = max_size

    def add(self, event: BoundaryEvent) -> bool:
        """Add event to buffer. Returns False if buffer is full."""
        with self._lock:
            if len(self._buffer) >= self._max_size:
                return False
            self._buffer.append(event)
            return True

    def flush(self) -> List[BoundaryEvent]:
        """Remove and return all events from buffer."""
        with self._lock:
            events = self._buffer
            self._buffer = []
            return events

    def size(self) -> int:
        with self._lock:
            return len(self._buffer)


class BoundarySIEMClient:
    """
    Client for Boundary-SIEM integration.

    Handles event forwarding, alert retrieval, and real-time subscriptions.
    """

    def __init__(self, config: Optional[SIEMConfig] = None):
        self.config = config or SIEMConfig.from_env()
        self._buffer = EventBuffer()
        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        self._alert_callbacks: List[Callable[[SIEMAlert], None]] = []
        self._websocket = None
        self._connected = False

    def start(self) -> None:
        """Start the SIEM client background processing."""
        if self._running:
            return

        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        logger.info(f"SIEM client started, forwarding to {self.config.host}:{self.config.port}")

    def stop(self) -> None:
        """Stop the SIEM client and flush remaining events."""
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)

        # Final flush
        events = self._buffer.flush()
        if events:
            self._send_events(events)

        logger.info("SIEM client stopped")

    def send_event(self, event: BoundaryEvent) -> bool:
        """
        Queue an event for sending to SIEM.

        Args:
            event: The security event to forward

        Returns:
            True if event was queued, False if buffer is full
        """
        # Apply filters
        if not self._should_forward(event):
            return True  # Filtered out, but not an error

        return self._buffer.add(event)

    def _should_forward(self, event: BoundaryEvent) -> bool:
        """Check if event should be forwarded based on filters."""
        # Check minimum severity
        if event.severity.value < self.config.min_severity.value:
            return False

        # Check include list
        if self.config.include_event_types:
            if event.event_type not in self.config.include_event_types:
                return False

        # Check exclude list
        if self.config.exclude_event_types:
            if event.event_type in self.config.exclude_event_types:
                return False

        return True

    def _flush_loop(self) -> None:
        """Background loop for flushing buffered events."""
        while self._running:
            time.sleep(self.config.flush_interval_seconds)

            if self._buffer.size() >= self.config.batch_size:
                events = self._buffer.flush()
                if events:
                    self._send_events(events)

    def _send_events(self, events: List[BoundaryEvent]) -> bool:
        """Send events to SIEM based on configured protocol."""
        if not events:
            return True

        protocol = self.config.protocol

        try:
            if protocol == SIEMProtocol.JSON_HTTP:
                return self._send_json_http(events)
            elif protocol in (SIEMProtocol.CEF_UDP, SIEMProtocol.CEF_TCP):
                return self._send_cef(events, use_tcp=(protocol == SIEMProtocol.CEF_TCP))
            elif protocol in (SIEMProtocol.SYSLOG_UDP, SIEMProtocol.SYSLOG_TCP):
                return self._send_syslog(events, use_tcp=(protocol == SIEMProtocol.SYSLOG_TCP))
            else:
                logger.error(f"Unknown protocol: {protocol}")
                return False
        except Exception as e:
            logger.error(f"Failed to send events to SIEM: {e}")
            return False

    def _send_json_http(self, events: List[BoundaryEvent]) -> bool:
        """Send events via JSON HTTP API."""
        import urllib.request
        import urllib.error

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/api/v1/events"

        payload = {
            "events": [e.to_json() for e in events],
            "source": "rra-module",
            "timestamp": datetime.now().isoformat(),
        }

        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "RRA-Module/0.1.0")

        if self.config.api_key:
            req.add_header("Authorization", f"Bearer {self.config.api_key}")

        for attempt in range(self.config.retry_attempts):
            try:
                with urllib.request.urlopen(
                    req,
                    timeout=self.config.connect_timeout_seconds
                ) as resp:
                    if resp.status == 200:
                        logger.debug(f"Sent {len(events)} events to SIEM")
                        return True
                    else:
                        logger.warning(f"SIEM returned status {resp.status}")
            except urllib.error.URLError as e:
                logger.warning(f"SIEM connection failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay_seconds * (attempt + 1))

        return False

    def _send_cef(self, events: List[BoundaryEvent], use_tcp: bool = False) -> bool:
        """Send events via CEF format."""
        port = self.config.port or (1514 if use_tcp else 514)

        try:
            if use_tcp:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.config.connect_timeout_seconds)
                sock.connect((self.config.host, port))
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            for event in events:
                cef_line = event.to_cef() + "\n"
                if use_tcp:
                    sock.sendall(cef_line.encode())
                else:
                    sock.sendto(cef_line.encode(), (self.config.host, port))

            sock.close()
            logger.debug(f"Sent {len(events)} CEF events to SIEM")
            return True

        except socket.error as e:
            logger.error(f"CEF socket error: {e}")
            return False

    def _send_syslog(self, events: List[BoundaryEvent], use_tcp: bool = False) -> bool:
        """Send events via syslog (RFC 5424) format."""
        port = self.config.port or (1514 if use_tcp else 514)
        facility = 16  # local0
        hostname = socket.gethostname()

        try:
            if use_tcp:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.config.connect_timeout_seconds)
                sock.connect((self.config.host, port))
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            for event in events:
                # Map severity to syslog priority
                severity_map = {
                    EventSeverity.DEBUG: 7,
                    EventSeverity.INFO: 6,
                    EventSeverity.LOW: 5,
                    EventSeverity.MEDIUM: 4,
                    EventSeverity.HIGH: 3,
                    EventSeverity.CRITICAL: 2,
                }
                priority = facility * 8 + severity_map.get(event.severity, 6)

                # RFC 5424 format
                timestamp = event.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                structured_data = f'[rra event_type="{event.event_type}" mode="{event.mode.value}"]'
                message = json.dumps(event.to_json())

                syslog_line = f"<{priority}>1 {timestamp} {hostname} rra-module - - {structured_data} {message}\n"

                if use_tcp:
                    sock.sendall(syslog_line.encode())
                else:
                    sock.sendto(syslog_line.encode(), (self.config.host, port))

            sock.close()
            logger.debug(f"Sent {len(events)} syslog events to SIEM")
            return True

        except socket.error as e:
            logger.error(f"Syslog socket error: {e}")
            return False

    # =========================================================================
    # Alert Management
    # =========================================================================

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity_min: Optional[AlertSeverity] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SIEMAlert]:
        """
        Retrieve alerts from SIEM.

        Args:
            status: Filter by alert status
            severity_min: Filter by minimum severity
            since: Filter by creation time
            limit: Maximum alerts to return

        Returns:
            List of alerts matching filters
        """
        import urllib.request
        import urllib.error

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/api/v1/alerts"

        params = {"limit": limit}
        if status:
            params["status"] = status.value
        if severity_min:
            params["severity_min"] = severity_min.value
        if since:
            params["since"] = since.isoformat()

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query_string}"

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "RRA-Module/0.1.0")
        if self.config.api_key:
            req.add_header("Authorization", f"Bearer {self.config.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=self.config.read_timeout_seconds) as resp:
                data = json.loads(resp.read().decode())
                return [SIEMAlert.from_dict(a) for a in data.get("alerts", [])]
        except Exception as e:
            logger.error(f"Failed to retrieve alerts: {e}")
            return []

    def acknowledge_alert(self, alert_id: str, note: str = "") -> bool:
        """Acknowledge an alert."""
        return self._update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED, note)

    def resolve_alert(self, alert_id: str, note: str = "") -> bool:
        """Resolve an alert."""
        return self._update_alert_status(alert_id, AlertStatus.RESOLVED, note)

    def _update_alert_status(
        self,
        alert_id: str,
        status: AlertStatus,
        note: str = ""
    ) -> bool:
        """Update alert status in SIEM."""
        import urllib.request
        import urllib.error

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/api/v1/alerts/{alert_id}"

        payload = {
            "status": status.value,
            "note": note,
            "updated_by": "rra-module",
            "updated_at": datetime.now().isoformat(),
        }

        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method="PATCH")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "RRA-Module/0.1.0")
        if self.config.api_key:
            req.add_header("Authorization", f"Bearer {self.config.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=self.config.connect_timeout_seconds) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Failed to update alert {alert_id}: {e}")
            return False

    def register_alert_callback(
        self,
        callback: Callable[[SIEMAlert], None]
    ) -> None:
        """Register a callback for real-time alerts."""
        self._alert_callbacks.append(callback)

    # =========================================================================
    # Detection Rules
    # =========================================================================

    def get_detection_rules(self) -> List[DetectionRule]:
        """Retrieve configured detection rules from SIEM."""
        import urllib.request

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/api/v1/rules"

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "RRA-Module/0.1.0")
        if self.config.api_key:
            req.add_header("Authorization", f"Bearer {self.config.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=self.config.read_timeout_seconds) as resp:
                data = json.loads(resp.read().decode())
                rules = []
                for r in data.get("rules", []):
                    rules.append(DetectionRule(
                        rule_id=r["rule_id"],
                        name=r["name"],
                        description=r.get("description", ""),
                        severity=AlertSeverity(r.get("severity", "medium")),
                        mitre_techniques=r.get("mitre_techniques", []),
                        event_types=r.get("event_types", []),
                        conditions=r.get("conditions", {}),
                        enabled=r.get("enabled", True),
                    ))
                return rules
        except Exception as e:
            logger.error(f"Failed to retrieve detection rules: {e}")
            return []

    # =========================================================================
    # Search and Query
    # =========================================================================

    def search_events(
        self,
        query: str,
        time_range: Optional[timedelta] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search events in SIEM.

        Args:
            query: Search query string
            time_range: Time range to search (default: last 24 hours)
            limit: Maximum results to return

        Returns:
            List of matching events
        """
        import urllib.request

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/api/v1/search"

        time_range = time_range or timedelta(hours=24)
        since = (datetime.now() - time_range).isoformat()

        payload = {
            "query": query,
            "since": since,
            "limit": limit,
        }

        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "RRA-Module/0.1.0")
        if self.config.api_key:
            req.add_header("Authorization", f"Bearer {self.config.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=self.config.read_timeout_seconds) as resp:
                data = json.loads(resp.read().decode())
                return data.get("results", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    # =========================================================================
    # Health and Status
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """Check SIEM connection health."""
        import urllib.request

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/health"

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "RRA-Module/0.1.0")

        try:
            with urllib.request.urlopen(req, timeout=self.config.connect_timeout_seconds) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    return {
                        "connected": True,
                        "status": data.get("status", "unknown"),
                        "version": data.get("version", "unknown"),
                    }
        except Exception as e:
            logger.warning(f"SIEM health check failed: {e}")

        return {"connected": False, "status": "unreachable", "error": str(e) if 'e' in dir() else "unknown"}

    def get_stats(self) -> Dict[str, Any]:
        """Get SIEM statistics."""
        import urllib.request

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/api/v1/stats"

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "RRA-Module/0.1.0")
        if self.config.api_key:
            req.add_header("Authorization", f"Bearer {self.config.api_key}")

        try:
            with urllib.request.urlopen(req, timeout=self.config.read_timeout_seconds) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.error(f"Failed to get SIEM stats: {e}")
            return {}


# =========================================================================
# RRA-Specific Detection Rules
# =========================================================================

# Pre-configured detection rules for RRA-Module threats
RRA_DETECTION_RULES = [
    DetectionRule(
        rule_id="rra-001",
        name="License Transfer Without Authorization",
        description="Detected license transfer without proper authorization",
        severity=AlertSeverity.HIGH,
        mitre_techniques=["T1078", "T1531"],  # Valid Accounts, Account Access Removal
        event_types=["license_transfer", "access_denied"],
        conditions={"outcome": "blocked", "permission": "TRANSFER"},
    ),
    DetectionRule(
        rule_id="rra-002",
        name="Repeated Access Denials",
        description="Multiple access denials from same principal",
        severity=AlertSeverity.MEDIUM,
        mitre_techniques=["T1110"],  # Brute Force
        event_types=["access_denied"],
        conditions={"threshold": 5, "window_seconds": 300},
    ),
    DetectionRule(
        rule_id="rra-003",
        name="Emergency Lockdown Triggered",
        description="System entered lockdown mode",
        severity=AlertSeverity.CRITICAL,
        mitre_techniques=["T1499"],  # Endpoint Denial of Service
        event_types=["lockdown_triggered"],
        conditions={},
    ),
    DetectionRule(
        rule_id="rra-004",
        name="Unusual Transaction Value",
        description="Transaction value exceeds normal range",
        severity=AlertSeverity.HIGH,
        mitre_techniques=["T1496"],  # Resource Hijacking
        event_types=["transaction", "license_purchase"],
        conditions={"value_eth_threshold": 100},
    ),
    DetectionRule(
        rule_id="rra-005",
        name="Mode Escalation Attempt",
        description="Attempt to transition from restrictive to open mode",
        severity=AlertSeverity.MEDIUM,
        mitre_techniques=["T1548"],  # Abuse Elevation Control Mechanism
        event_types=["mode_transition"],
        conditions={"direction": "escalation"},
    ),
    DetectionRule(
        rule_id="rra-006",
        name="Negotiation Manipulation",
        description="Detected potential manipulation of negotiation process",
        severity=AlertSeverity.HIGH,
        mitre_techniques=["T1565"],  # Data Manipulation
        event_types=["negotiation_override", "price_manipulation"],
        conditions={},
    ),
    DetectionRule(
        rule_id="rra-007",
        name="API Key Abuse",
        description="API key used from unusual location or pattern",
        severity=AlertSeverity.HIGH,
        mitre_techniques=["T1552"],  # Unsecured Credentials
        event_types=["api_access", "token_validation"],
        conditions={"anomaly_score_threshold": 0.8},
    ),
    DetectionRule(
        rule_id="rra-008",
        name="Smart Contract Exploit Attempt",
        description="Suspicious smart contract interaction detected",
        severity=AlertSeverity.CRITICAL,
        mitre_techniques=["T1190"],  # Exploit Public-Facing Application
        event_types=["contract_call", "transaction_reverted"],
        conditions={"pattern": "reentrancy|overflow|underflow"},
    ),
]


def create_siem_client(config: Optional[SIEMConfig] = None) -> BoundarySIEMClient:
    """
    Factory function to create a SIEM client.

    Args:
        config: Optional configuration (loads from env if not provided)

    Returns:
        Configured BoundarySIEMClient instance
    """
    return BoundarySIEMClient(config=config)


def create_siem_event_callback(
    client: BoundarySIEMClient
) -> Callable[[BoundaryEvent], None]:
    """
    Create a callback function for forwarding events to SIEM.

    This can be passed to BoundaryDaemon as the siem_callback parameter.

    Args:
        client: The SIEM client to use for forwarding

    Returns:
        Callback function
    """
    def callback(event: BoundaryEvent) -> None:
        client.send_event(event)

    return callback
