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
import re
import urllib.parse

from rra.integration.boundary_daemon import (
    BoundaryEvent,
    EventSeverity,
    BoundaryMode,
)

logger = logging.getLogger(__name__)


class SIEMProtocol(str, Enum):
    """Supported SIEM ingestion protocols."""

    CEF_UDP = "cef_udp"  # CEF over UDP (port 514)
    CEF_TCP = "cef_tcp"  # CEF over TCP (port 1514)
    JSON_HTTP = "json_http"  # JSON over HTTP REST API
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
        host = os.environ.get("BOUNDARY_SIEM_HOST", "localhost")

        # Validate host to prevent SSRF attacks
        cls._validate_host(host)

        return cls(
            host=host,
            port=int(os.environ.get("BOUNDARY_SIEM_PORT", "8514")),
            protocol=SIEMProtocol(os.environ.get("BOUNDARY_SIEM_PROTOCOL", "json_http")),
            api_key=os.environ.get("BOUNDARY_SIEM_API_KEY"),
            tls_enabled=os.environ.get("BOUNDARY_SIEM_TLS", "false").lower() == "true",
            tls_cert_path=os.environ.get("BOUNDARY_SIEM_TLS_CERT"),
        )

    @staticmethod
    def _validate_host(host: str) -> None:
        """Validate host to prevent SSRF attacks."""
        # Block cloud metadata endpoints
        blocked_hosts = {
            "169.254.169.254",  # AWS/GCP metadata
            "metadata.google.internal",
            "metadata.goog",
        }

        if host.lower() in blocked_hosts:
            raise ValueError(f"Blocked host (cloud metadata): {host}")

        # Block private IP ranges for SIEM (unless explicitly localhost)
        if host != "localhost" and host != "127.0.0.1":
            private_patterns = [
                r"^10\.",
                r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
                r"^192\.168\.",
                r"^127\.",
            ]
            for pattern in private_patterns:
                if re.match(pattern, host):
                    raise ValueError(f"Private IP not allowed for SIEM host: {host}")


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


class PersistentEventQueue:
    """
    Persistent event queue that spills to disk when memory buffer is full.

    Prevents event loss during SIEM outages or high event volume.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        memory_limit: int = 1000,
        disk_limit: int = 100000,
    ):
        self.data_dir = data_dir or Path("data/siem_queue")
        self.memory_limit = memory_limit
        self.disk_limit = disk_limit
        self._memory_buffer: List[BoundaryEvent] = []
        self._lock = threading.Lock()
        self._disk_queue_file: Optional[Path] = None
        self._disk_event_count = 0

        # Create data directory if needed
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._disk_queue_file = self.data_dir / "pending_events.jsonl"

        # Load any existing events from disk on startup
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load pending events from disk on startup."""
        if not self._disk_queue_file or not self._disk_queue_file.exists():
            return

        try:
            with open(self._disk_queue_file, "r") as f:
                for line in f:
                    if line.strip():
                        self._disk_event_count += 1

            if self._disk_event_count > 0:
                logger.info(f"Loaded {self._disk_event_count} pending events from disk queue")
        except Exception as e:
            logger.error(f"Failed to load disk queue: {e}")

    def add(self, event: BoundaryEvent) -> bool:
        """
        Add event to queue. Returns True if added, False if queue is full.

        Events are first added to memory. When memory is full, they spill to disk.
        """
        with self._lock:
            # Try memory buffer first
            if len(self._memory_buffer) < self.memory_limit:
                self._memory_buffer.append(event)
                return True

            # Spill to disk
            if self._disk_event_count >= self.disk_limit:
                logger.warning("Persistent event queue full - event dropped")
                return False

            return self._write_to_disk(event)

    def _write_to_disk(self, event: BoundaryEvent) -> bool:
        """Write event to disk queue."""
        if not self._disk_queue_file:
            return False

        try:
            with open(self._disk_queue_file, "a") as f:
                f.write(json.dumps(event.to_json()) + "\n")
            self._disk_event_count += 1
            return True
        except Exception as e:
            logger.error(f"Failed to write event to disk: {e}")
            return False

    def get_batch(self, batch_size: int = 100) -> List[BoundaryEvent]:
        """
        Get a batch of events for sending.

        Prioritizes memory events, then reads from disk.
        """
        events: List[BoundaryEvent] = []

        with self._lock:
            # Get from memory first
            if self._memory_buffer:
                events = self._memory_buffer[:batch_size]
                self._memory_buffer = self._memory_buffer[batch_size:]
                remaining = batch_size - len(events)
            else:
                remaining = batch_size

            # If we need more, read from disk
            if remaining > 0 and self._disk_event_count > 0:
                disk_events = self._read_from_disk(remaining)
                events.extend(disk_events)

        return events

    def _read_from_disk(self, count: int) -> List[BoundaryEvent]:
        """Read events from disk queue."""
        if not self._disk_queue_file or not self._disk_queue_file.exists():
            return []

        events: List[BoundaryEvent] = []
        remaining_lines: List[str] = []

        try:
            with open(self._disk_queue_file, "r") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if i < count and line.strip():
                    try:
                        data = json.loads(line.strip())
                        event = BoundaryEvent(
                            event_id=data["event_id"],
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            event_type=data["event_type"],
                            source=data["source"],
                            action=data["action"],
                            outcome=data["outcome"],
                            severity=EventSeverity[data["severity"]],
                            mode=BoundaryMode(data["mode"]),
                            principal_id=data.get("principal_id"),
                            resource_type=data.get("resource_type"),
                            resource_id=data.get("resource_id"),
                            context=data.get("context", {}),
                            previous_hash=data.get("previous_hash"),
                        )
                        events.append(event)
                    except Exception as e:
                        logger.warning(f"Failed to parse disk event: {e}")
                else:
                    remaining_lines.append(line)

            # Rewrite file with remaining lines
            with open(self._disk_queue_file, "w") as f:
                f.writelines(remaining_lines)

            self._disk_event_count = len(remaining_lines)

        except Exception as e:
            logger.error(f"Failed to read from disk queue: {e}")

        return events

    def acknowledge(self, events: List[BoundaryEvent]) -> None:
        """
        Acknowledge that events were successfully sent.

        In the current implementation, events are removed when get_batch is called,
        so this is a no-op. Future versions may implement two-phase commit.
        """
        pass

    def requeue(self, events: List[BoundaryEvent]) -> None:
        """Requeue events that failed to send."""
        with self._lock:
            # Add back to front of memory buffer
            self._memory_buffer = events + self._memory_buffer

            # If memory overflows, spill excess to disk
            while len(self._memory_buffer) > self.memory_limit:
                event = self._memory_buffer.pop()
                self._write_to_disk(event)

    def size(self) -> int:
        """Get total queue size (memory + disk)."""
        with self._lock:
            return len(self._memory_buffer) + self._disk_event_count

    def memory_size(self) -> int:
        """Get memory buffer size."""
        with self._lock:
            return len(self._memory_buffer)

    def disk_size(self) -> int:
        """Get disk queue size."""
        with self._lock:
            return self._disk_event_count

    def clear(self) -> int:
        """Clear all events and return count of cleared events."""
        with self._lock:
            count = len(self._memory_buffer) + self._disk_event_count
            self._memory_buffer = []
            self._disk_event_count = 0

            if self._disk_queue_file and self._disk_queue_file.exists():
                self._disk_queue_file.unlink()

            return count

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        with self._lock:
            return {
                "memory_count": len(self._memory_buffer),
                "disk_count": self._disk_event_count,
                "total_count": len(self._memory_buffer) + self._disk_event_count,
                "memory_limit": self.memory_limit,
                "disk_limit": self.disk_limit,
                "disk_queue_path": str(self._disk_queue_file) if self._disk_queue_file else None,
            }


class BoundarySIEMClient:
    """
    Client for Boundary-SIEM integration.

    Handles event forwarding, alert retrieval, and real-time subscriptions.

    Features:
    - Optional persistent queue for event overflow
    - Graceful shutdown with event draining
    - Correlation ID propagation
    """

    def __init__(
        self,
        config: Optional[SIEMConfig] = None,
        use_persistent_queue: bool = False,
        queue_data_dir: Optional[Path] = None,
    ):
        self.config = config or SIEMConfig.from_env()
        self._use_persistent_queue = use_persistent_queue

        if use_persistent_queue:
            self._queue: PersistentEventQueue = PersistentEventQueue(
                data_dir=queue_data_dir,
            )
            self._buffer = None
        else:
            self._buffer = EventBuffer()
            self._queue = None

        self._running = False
        self._flush_thread: Optional[threading.Thread] = None
        self._alert_callbacks: List[Callable[[SIEMAlert], None]] = []
        self._websocket = None
        self._connected = False
        self._shutdown_event = threading.Event()
        self._events_sent = 0
        self._events_failed = 0

    def start(self) -> None:
        """Start the SIEM client background processing."""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
        logger.info(f"SIEM client started, forwarding to {self.config.host}:{self.config.port}")

    def stop(self, drain_timeout: float = 30.0) -> int:
        """
        Stop the SIEM client and flush remaining events.

        Args:
            drain_timeout: Maximum seconds to wait for event draining

        Returns:
            Number of events remaining in queue (0 if fully drained)
        """
        self._running = False
        self._shutdown_event.set()

        if self._flush_thread:
            self._flush_thread.join(timeout=drain_timeout)

        # Final flush - drain as many events as possible
        remaining = 0
        start_time = time.time()

        while time.time() - start_time < drain_timeout:
            if self._use_persistent_queue and self._queue:
                events = self._queue.get_batch(self.config.batch_size)
                if not events:
                    break
                if not self._send_events(events):
                    self._queue.requeue(events)
                    remaining = self._queue.size()
                    break
            elif self._buffer:
                events = self._buffer.flush()
                if not events:
                    break
                if not self._send_events(events):
                    remaining = len(events)
                    break
            else:
                break

        if self._use_persistent_queue and self._queue:
            remaining = self._queue.size()

        if remaining > 0:
            logger.warning(f"SIEM client stopped with {remaining} events remaining in queue")
        else:
            logger.info("SIEM client stopped, all events drained")

        return remaining

    def send_event(self, event: BoundaryEvent) -> bool:
        """
        Queue an event for sending to SIEM.

        Args:
            event: The security event to forward

        Returns:
            True if event was queued, False if buffer/queue is full
        """
        # Apply filters
        if not self._should_forward(event):
            return True  # Filtered out, but not an error

        if self._use_persistent_queue and self._queue:
            return self._queue.add(event)
        elif self._buffer:
            return self._buffer.add(event)
        return False

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
            # Use event-based wait for responsive shutdown
            self._shutdown_event.wait(timeout=self.config.flush_interval_seconds)

            if not self._running:
                break

            if self._use_persistent_queue and self._queue:
                if self._queue.size() >= self.config.batch_size:
                    events = self._queue.get_batch(self.config.batch_size)
                    if events:
                        if not self._send_events(events):
                            self._queue.requeue(events)
            elif self._buffer and self._buffer.size() >= self.config.batch_size:
                events = self._buffer.flush()
                if events:
                    self._send_events(events)

    def _send_events(self, events: List[BoundaryEvent]) -> bool:
        """Send events to SIEM based on configured protocol."""
        if not events:
            return True

        protocol = self.config.protocol
        success = False

        try:
            if protocol == SIEMProtocol.JSON_HTTP:
                success = self._send_json_http(events)
            elif protocol in (SIEMProtocol.CEF_UDP, SIEMProtocol.CEF_TCP):
                success = self._send_cef(events, use_tcp=(protocol == SIEMProtocol.CEF_TCP))
            elif protocol in (SIEMProtocol.SYSLOG_UDP, SIEMProtocol.SYSLOG_TCP):
                success = self._send_syslog(events, use_tcp=(protocol == SIEMProtocol.SYSLOG_TCP))
            else:
                logger.error(f"Unknown protocol: {protocol}")
                success = False
        except Exception as e:
            logger.error(f"Failed to send events to SIEM: {e}")
            success = False

        # Track metrics
        if success:
            self._events_sent += len(events)
        else:
            self._events_failed += len(events)

        return success

    def get_client_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        stats = {
            "running": self._running,
            "events_sent": self._events_sent,
            "events_failed": self._events_failed,
            "protocol": self.config.protocol.value,
            "host": self.config.host,
            "port": self.config.port,
        }

        if self._use_persistent_queue and self._queue:
            stats["queue"] = self._queue.get_stats()
        elif self._buffer:
            stats["buffer_size"] = self._buffer.size()

        return stats

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
                    req, timeout=self.config.connect_timeout_seconds
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

    @staticmethod
    def _validate_identifier(identifier: str, name: str = "identifier") -> str:
        """
        Validate and sanitize an identifier to prevent path injection.

        Args:
            identifier: The identifier to validate
            name: Name of the identifier for error messages

        Returns:
            The validated identifier

        Raises:
            ValueError: If identifier contains invalid characters
        """
        if not identifier:
            raise ValueError(f"Empty {name}")

        # Only allow alphanumeric, underscore, hyphen
        if not re.match(r"^[a-zA-Z0-9_-]+$", identifier):
            raise ValueError(f"Invalid {name} format: contains forbidden characters")

        # Limit length to prevent DoS
        if len(identifier) > 256:
            raise ValueError(f"Invalid {name}: exceeds maximum length")

        return identifier

    def _update_alert_status(self, alert_id: str, status: AlertStatus, note: str = "") -> bool:
        """Update alert status in SIEM."""
        import urllib.request
        import urllib.error

        # Validate alert_id to prevent path injection
        safe_alert_id = self._validate_identifier(alert_id, "alert_id")
        safe_alert_id = urllib.parse.quote(safe_alert_id, safe="")

        url = f"{'https' if self.config.tls_enabled else 'http'}://{self.config.host}:{self.config.port}/api/v1/alerts/{safe_alert_id}"

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

    def register_alert_callback(self, callback: Callable[[SIEMAlert], None]) -> None:
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
                    rules.append(
                        DetectionRule(
                            rule_id=r["rule_id"],
                            name=r["name"],
                            description=r.get("description", ""),
                            severity=AlertSeverity(r.get("severity", "medium")),
                            mitre_techniques=r.get("mitre_techniques", []),
                            event_types=r.get("event_types", []),
                            conditions=r.get("conditions", {}),
                            enabled=r.get("enabled", True),
                        )
                    )
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

        error_msg = "unknown"
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
            error_msg = str(e)
            logger.warning(f"SIEM health check failed: {e}")

        return {
            "connected": False,
            "status": "unreachable",
            "error": error_msg,
        }

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


def create_siem_event_callback(client: BoundarySIEMClient) -> Callable[[BoundaryEvent], None]:
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
