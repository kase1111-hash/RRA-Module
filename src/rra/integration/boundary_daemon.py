# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Boundary Daemon Integration for NatLangChain.

Provides permission management and access control for RRA agents,
integrating with the NatLangChain boundary-daemon (Agent Smith) system.

This module supports:
- Connection to external Boundary-Daemon via Unix socket or HTTP
- Six boundary modes (OPEN, RESTRICTED, TRUSTED, AIRGAP, COLDROOM, LOCKDOWN)
- Cryptographic event logging with Ed25519 signatures
- SIEM event forwarding in CEF format
- Policy-based access control with fail-closed behavior
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, Flag, auto
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from pathlib import Path
import json
import secrets
import hashlib
import socket
import os
import logging
import threading
import time
from contextlib import contextmanager

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)


class Permission(Flag):
    """Permission flags for agent capabilities."""
    NONE = 0
    READ = auto()          # Read repository content
    NEGOTIATE = auto()     # Conduct license negotiations
    QUOTE = auto()         # Provide price quotes
    ACCEPT = auto()        # Accept license offers
    TRANSFER = auto()      # Transfer license ownership
    MINT = auto()          # Mint new license NFTs
    BURN = auto()          # Revoke/burn licenses
    ADMIN = auto()         # Administrative operations
    WEBHOOK = auto()       # Receive webhook callbacks
    STREAM = auto()        # Manage payment streams
    ANALYTICS = auto()     # Access analytics data

    # Common permission sets
    BASIC = READ | QUOTE
    STANDARD = READ | NEGOTIATE | QUOTE | ACCEPT
    FULL = READ | NEGOTIATE | QUOTE | ACCEPT | TRANSFER | MINT
    ALL = READ | NEGOTIATE | QUOTE | ACCEPT | TRANSFER | MINT | BURN | ADMIN | WEBHOOK | STREAM | ANALYTICS


class ResourceType(Enum):
    """Types of protected resources."""
    REPOSITORY = "repository"
    LICENSE = "license"
    AGENT = "agent"
    POOL = "pool"
    DAO = "dao"
    STREAM = "stream"
    WEBHOOK = "webhook"
    API = "api"


class BoundaryMode(str, Enum):
    """
    Boundary modes as defined by Boundary-Daemon (Agent Smith).

    Each mode represents progressively restrictive constraints on
    network access, memory classification, and tool availability.
    """
    OPEN = "open"           # Full access, minimal restrictions
    RESTRICTED = "restricted"  # Limited network, monitored operations
    TRUSTED = "trusted"     # Verified operations only
    AIRGAP = "airgap"       # No external network access
    COLDROOM = "coldroom"   # Isolated execution, encrypted storage
    LOCKDOWN = "lockdown"   # Emergency mode, all operations halted


class EventSeverity(Enum):
    """Security event severity levels."""
    DEBUG = 0
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


@dataclass
class BoundaryEvent:
    """
    Immutable, cryptographically-signed security event.

    Events are hash-chained for tamper detection and can be
    forwarded to SIEM systems in CEF format.
    """
    event_id: str
    timestamp: datetime
    event_type: str
    source: str
    action: str
    outcome: str  # "success", "failure", "blocked"
    severity: EventSeverity
    mode: BoundaryMode
    principal_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    previous_hash: Optional[str] = None
    signature: Optional[bytes] = None

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of event data."""
        data = {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "source": self.source,
            "action": self.action,
            "outcome": self.outcome,
            "severity": self.severity.value,
            "mode": self.mode.value,
            "principal_id": self.principal_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "context": self.context,
            "previous_hash": self.previous_hash,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_cef(self) -> str:
        """Convert event to CEF (Common Event Format) for SIEM."""
        # CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        severity_map = {
            EventSeverity.DEBUG: 0,
            EventSeverity.INFO: 1,
            EventSeverity.LOW: 3,
            EventSeverity.MEDIUM: 5,
            EventSeverity.HIGH: 7,
            EventSeverity.CRITICAL: 10,
        }

        extensions = [
            f"rt={int(self.timestamp.timestamp() * 1000)}",
            f"src={self.source}",
            f"act={self.action}",
            f"outcome={self.outcome}",
            f"cs1={self.mode.value}",
            f"cs1Label=BoundaryMode",
        ]

        if self.principal_id:
            extensions.append(f"suser={self.principal_id}")
        if self.resource_type:
            extensions.append(f"cs2={self.resource_type}")
            extensions.append(f"cs2Label=ResourceType")
        if self.resource_id:
            extensions.append(f"cs3={self.resource_id}")
            extensions.append(f"cs3Label=ResourceId")

        return (
            f"CEF:0|NatLangChain|RRA-Module|0.1.0|{self.event_type}|"
            f"{self.event_type}|{severity_map[self.severity]}|{' '.join(extensions)}"
        )

    def to_json(self) -> Dict[str, Any]:
        """Convert event to JSON format for SIEM."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "source": self.source,
            "action": self.action,
            "outcome": self.outcome,
            "severity": self.severity.name,
            "severity_value": self.severity.value,
            "mode": self.mode.value,
            "principal_id": self.principal_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "context": self.context,
            "hash": self.compute_hash(),
            "previous_hash": self.previous_hash,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.to_json()


@dataclass
class ModeConstraints:
    """Constraints applied in each boundary mode."""
    mode: BoundaryMode
    network_allowed: bool
    external_apis_allowed: bool
    blockchain_write_allowed: bool
    file_write_allowed: bool
    tool_allowlist: Set[str]
    memory_classification: str  # "public", "internal", "confidential", "restricted"
    max_transaction_value_eth: Optional[float] = None
    require_human_approval: bool = False

    @classmethod
    def for_mode(cls, mode: BoundaryMode) -> "ModeConstraints":
        """Get default constraints for a boundary mode."""
        constraints = {
            BoundaryMode.OPEN: cls(
                mode=BoundaryMode.OPEN,
                network_allowed=True,
                external_apis_allowed=True,
                blockchain_write_allowed=True,
                file_write_allowed=True,
                tool_allowlist={"*"},
                memory_classification="public",
                max_transaction_value_eth=None,
                require_human_approval=False,
            ),
            BoundaryMode.RESTRICTED: cls(
                mode=BoundaryMode.RESTRICTED,
                network_allowed=True,
                external_apis_allowed=True,
                blockchain_write_allowed=True,
                file_write_allowed=True,
                tool_allowlist={"read", "negotiate", "quote", "analyze"},
                memory_classification="internal",
                max_transaction_value_eth=1.0,
                require_human_approval=False,
            ),
            BoundaryMode.TRUSTED: cls(
                mode=BoundaryMode.TRUSTED,
                network_allowed=True,
                external_apis_allowed=False,
                blockchain_write_allowed=True,
                file_write_allowed=True,
                tool_allowlist={"read", "negotiate", "mint", "transfer"},
                memory_classification="confidential",
                max_transaction_value_eth=10.0,
                require_human_approval=False,
            ),
            BoundaryMode.AIRGAP: cls(
                mode=BoundaryMode.AIRGAP,
                network_allowed=False,
                external_apis_allowed=False,
                blockchain_write_allowed=False,
                file_write_allowed=True,
                tool_allowlist={"read", "analyze"},
                memory_classification="confidential",
                max_transaction_value_eth=0,
                require_human_approval=True,
            ),
            BoundaryMode.COLDROOM: cls(
                mode=BoundaryMode.COLDROOM,
                network_allowed=False,
                external_apis_allowed=False,
                blockchain_write_allowed=False,
                file_write_allowed=False,
                tool_allowlist={"read"},
                memory_classification="restricted",
                max_transaction_value_eth=0,
                require_human_approval=True,
            ),
            BoundaryMode.LOCKDOWN: cls(
                mode=BoundaryMode.LOCKDOWN,
                network_allowed=False,
                external_apis_allowed=False,
                blockchain_write_allowed=False,
                file_write_allowed=False,
                tool_allowlist=set(),
                memory_classification="restricted",
                max_transaction_value_eth=0,
                require_human_approval=True,
            ),
        }
        return constraints[mode]


@dataclass
class AccessPolicy:
    """Defines access rules for a resource."""
    policy_id: str
    name: str
    description: str
    resource_type: ResourceType
    resource_id: str  # "*" for wildcard
    permissions: Permission
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    active: bool = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.active and not self.is_expired

    def matches_resource(self, resource_type: ResourceType, resource_id: str) -> bool:
        """Check if policy applies to a resource."""
        if self.resource_type != resource_type:
            return False
        if self.resource_id == "*":
            return True
        return self.resource_id == resource_id

    def check_conditions(self, context: Dict[str, Any]) -> bool:
        """Evaluate policy conditions against context."""
        for key, expected in self.conditions.items():
            if key not in context:
                return False

            actual = context[key]

            # Handle different condition types
            if isinstance(expected, dict):
                if "min" in expected and actual < expected["min"]:
                    return False
                if "max" in expected and actual > expected["max"]:
                    return False
                if "in" in expected and actual not in expected["in"]:
                    return False
                if "not_in" in expected and actual in expected["not_in"]:
                    return False
            elif actual != expected:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "permissions": self.permissions.value,
            "conditions": self.conditions,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessPolicy":
        return cls(
            policy_id=data["policy_id"],
            name=data["name"],
            description=data["description"],
            resource_type=ResourceType(data["resource_type"]),
            resource_id=data["resource_id"],
            permissions=Permission(data["permissions"]),
            conditions=data.get("conditions", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            active=data.get("active", True),
        )


@dataclass
class Principal:
    """An entity that can be granted permissions."""
    principal_id: str
    principal_type: str  # "user", "agent", "service", "contract"
    address: Optional[str] = None  # Ethereum address if applicable
    name: str = ""
    policies: List[str] = field(default_factory=list)  # Policy IDs
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "address": self.address,
            "name": self.name,
            "policies": self.policies,
            "created_at": self.created_at.isoformat(),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Principal":
        return cls(
            principal_id=data["principal_id"],
            principal_type=data["principal_type"],
            address=data.get("address"),
            name=data.get("name", ""),
            policies=data.get("policies", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            active=data.get("active", True),
        )


@dataclass
class AccessToken:
    """A temporary access token for authentication."""
    token_id: str
    token_hash: str  # Hashed token value
    principal_id: str
    scopes: List[str]
    issued_at: datetime
    expires_at: datetime
    revoked: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.revoked and datetime.now() < self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "token_hash": self.token_hash,
            "principal_id": self.principal_id,
            "scopes": self.scopes,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "revoked": self.revoked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessToken":
        return cls(
            token_id=data["token_id"],
            token_hash=data["token_hash"],
            principal_id=data["principal_id"],
            scopes=data["scopes"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            revoked=data.get("revoked", False),
        )


@dataclass
class AccessLog:
    """Log entry for access attempts."""
    log_id: str
    timestamp: datetime
    principal_id: str
    resource_type: ResourceType
    resource_id: str
    permission: Permission
    granted: bool
    reason: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "principal_id": self.principal_id,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "permission": self.permission.value,
            "granted": self.granted,
            "reason": self.reason,
            "context": self.context,
        }


class DaemonConnection:
    """
    Connection manager for external Boundary-Daemon (Agent Smith) service.

    Supports connection via:
    - Unix socket (preferred for local deployment)
    - HTTP REST API (for remote deployment)
    """

    DEFAULT_SOCKET_PATH = "/var/run/boundary-daemon/boundary.sock"
    DEFAULT_HTTP_URL = "http://localhost:8080"

    def __init__(
        self,
        socket_path: Optional[str] = None,
        http_url: Optional[str] = None,
        connect_timeout: float = 5.0,
        read_timeout: float = 30.0,
    ):
        self.socket_path = socket_path or os.environ.get(
            "BOUNDARY_DAEMON_SOCKET", self.DEFAULT_SOCKET_PATH
        )
        self.http_url = http_url or os.environ.get(
            "BOUNDARY_DAEMON_URL", self.DEFAULT_HTTP_URL
        )
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self._socket: Optional[socket.socket] = None
        self._connected = False
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """Check if external daemon is available."""
        # Try Unix socket first
        if os.path.exists(self.socket_path):
            try:
                with self._create_socket_connection() as sock:
                    return True
            except Exception:
                pass

        # Try HTTP
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.http_url}/health",
                method="GET"
            )
            req.add_header("User-Agent", "RRA-Module/0.1.0")
            with urllib.request.urlopen(req, timeout=self.connect_timeout) as resp:
                return resp.status == 200
        except Exception:
            pass

        return False

    @contextmanager
    def _create_socket_connection(self):
        """Create and yield a Unix socket connection."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.connect_timeout)
        try:
            sock.connect(self.socket_path)
            sock.settimeout(self.read_timeout)
            yield sock
        finally:
            sock.close()

    def send_request(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send request to external daemon.

        Args:
            action: The action to perform (e.g., "check_access", "get_mode")
            payload: Request payload

        Returns:
            Response from daemon
        """
        request_data = {
            "action": action,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
        }

        # Try Unix socket first
        if os.path.exists(self.socket_path):
            try:
                return self._send_socket_request(request_data)
            except Exception as e:
                logger.warning(f"Socket request failed: {e}, falling back to HTTP")

        # Fall back to HTTP
        return self._send_http_request(action, payload)

    def _send_socket_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request via Unix socket."""
        with self._lock:
            with self._create_socket_connection() as sock:
                # Send request
                request_bytes = json.dumps(request_data).encode() + b"\n"
                sock.sendall(request_bytes)

                # Read response
                response_bytes = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_bytes += chunk
                    if b"\n" in response_bytes:
                        break

                response_str = response_bytes.decode().strip()
                return json.loads(response_str)

    def _send_http_request(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send request via HTTP API."""
        import urllib.request
        import urllib.error

        url = f"{self.http_url}/api/v1/{action}"
        data = json.dumps(payload).encode()

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "RRA-Module/0.1.0")

        try:
            with urllib.request.urlopen(req, timeout=self.read_timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            raise RuntimeError(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Connection failed: {e.reason}")

    def get_current_mode(self) -> BoundaryMode:
        """Get current boundary mode from daemon."""
        try:
            response = self.send_request("get_mode", {})
            return BoundaryMode(response.get("mode", "open"))
        except Exception as e:
            logger.warning(f"Failed to get mode from daemon: {e}")
            return BoundaryMode.RESTRICTED  # Fail to restricted mode

    def check_permission(
        self,
        principal_id: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Check permission with external daemon."""
        try:
            response = self.send_request("check_permission", {
                "principal_id": principal_id,
                "action": action,
                "resource": resource,
                "context": context or {},
            })
            return response.get("allowed", False), response.get("reason", "")
        except Exception as e:
            logger.warning(f"Permission check failed: {e}")
            return False, f"Daemon unavailable: {e}"  # Fail closed

    def submit_event(self, event: BoundaryEvent) -> bool:
        """Submit security event to daemon for logging."""
        try:
            response = self.send_request("log_event", event.to_dict())
            return response.get("success", False)
        except Exception as e:
            logger.warning(f"Event submission failed: {e}")
            return False


class EventSigner:
    """Cryptographic signer for security events using Ed25519."""

    def __init__(self, private_key: Optional[bytes] = None):
        if not HAS_CRYPTO:
            logger.warning("cryptography package not available, signatures disabled")
            self._private_key = None
            self._public_key = None
            return

        if private_key:
            self._private_key = Ed25519PrivateKey.from_private_bytes(private_key)
        else:
            self._private_key = Ed25519PrivateKey.generate()

        self._public_key = self._private_key.public_key()

    @property
    def public_key_bytes(self) -> Optional[bytes]:
        """Get public key bytes for verification."""
        if not self._public_key:
            return None
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def sign_event(self, event: BoundaryEvent) -> bytes:
        """Sign an event and return signature."""
        if not self._private_key:
            return b""

        event_hash = event.compute_hash()
        return self._private_key.sign(event_hash.encode())

    def verify_signature(self, event: BoundaryEvent, signature: bytes) -> bool:
        """Verify event signature."""
        if not self._public_key or not signature:
            return False

        try:
            event_hash = event.compute_hash()
            self._public_key.verify(signature, event_hash.encode())
            return True
        except Exception:
            return False


class BoundaryDaemon:
    """
    Boundary Daemon for permission management.

    Integrates with NatLangChain's access control system to manage
    permissions for RRA agents and resources.

    Supports both:
    - Standalone mode: Local policy enforcement
    - Connected mode: Integration with external Boundary-Daemon (Agent Smith)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        external_daemon: Optional[DaemonConnection] = None,
        enable_siem_forwarding: bool = False,
        siem_callback: Optional[Callable[[BoundaryEvent], None]] = None,
    ):
        self.data_dir = data_dir or Path("data/permissions")
        self.policies: Dict[str, AccessPolicy] = {}
        self.principals: Dict[str, Principal] = {}
        self.tokens: Dict[str, AccessToken] = {}
        self.access_logs: List[AccessLog] = []

        # External daemon connection
        self._external_daemon = external_daemon
        self._use_external = False
        if external_daemon and external_daemon.is_available():
            self._use_external = True
            logger.info("Connected to external Boundary-Daemon")

        # Current boundary mode
        self._current_mode = BoundaryMode.RESTRICTED
        self._mode_constraints = ModeConstraints.for_mode(self._current_mode)

        # Event chain for audit trail
        self._event_chain: List[BoundaryEvent] = []
        self._last_event_hash: Optional[str] = None
        self._event_signer = EventSigner()

        # SIEM forwarding
        self._enable_siem = enable_siem_forwarding
        self._siem_callback = siem_callback

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    # =========================================================================
    # Boundary Mode Management
    # =========================================================================

    @property
    def current_mode(self) -> BoundaryMode:
        """Get current boundary mode."""
        if self._use_external and self._external_daemon:
            return self._external_daemon.get_current_mode()
        return self._current_mode

    @property
    def constraints(self) -> ModeConstraints:
        """Get current mode constraints."""
        return ModeConstraints.for_mode(self.current_mode)

    def set_mode(self, mode: BoundaryMode, reason: str = "") -> None:
        """
        Set boundary mode.

        Args:
            mode: New boundary mode
            reason: Reason for mode change (for audit)
        """
        old_mode = self._current_mode
        self._current_mode = mode
        self._mode_constraints = ModeConstraints.for_mode(mode)

        # Log mode transition
        self._create_event(
            event_type="mode_transition",
            action=f"transition_{old_mode.value}_to_{mode.value}",
            outcome="success",
            severity=EventSeverity.INFO if mode.value <= old_mode.value else EventSeverity.MEDIUM,
            context={"old_mode": old_mode.value, "new_mode": mode.value, "reason": reason}
        )

        logger.info(f"Boundary mode changed: {old_mode.value} -> {mode.value}")

    def trigger_lockdown(self, reason: str) -> None:
        """
        Trigger emergency lockdown mode.

        This immediately halts all operations and requires manual intervention.
        """
        self._create_event(
            event_type="lockdown_triggered",
            action="emergency_lockdown",
            outcome="success",
            severity=EventSeverity.CRITICAL,
            context={"reason": reason, "previous_mode": self._current_mode.value}
        )

        self._current_mode = BoundaryMode.LOCKDOWN
        self._mode_constraints = ModeConstraints.for_mode(BoundaryMode.LOCKDOWN)
        logger.critical(f"LOCKDOWN triggered: {reason}")

    def check_mode_constraint(
        self,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Check if an operation is allowed under current mode constraints.

        Args:
            operation: Operation type (network, blockchain_write, etc.)
            context: Additional context (e.g., transaction value)

        Returns:
            Tuple of (allowed, reason)
        """
        constraints = self.constraints
        context = context or {}

        # Check lockdown - nothing allowed
        if constraints.mode == BoundaryMode.LOCKDOWN:
            return False, "System in LOCKDOWN mode - all operations halted"

        # Check specific constraints
        if operation == "network" and not constraints.network_allowed:
            return False, f"Network access denied in {constraints.mode.value} mode"

        if operation == "external_api" and not constraints.external_apis_allowed:
            return False, f"External API access denied in {constraints.mode.value} mode"

        if operation == "blockchain_write" and not constraints.blockchain_write_allowed:
            return False, f"Blockchain writes denied in {constraints.mode.value} mode"

        if operation == "file_write" and not constraints.file_write_allowed:
            return False, f"File writes denied in {constraints.mode.value} mode"

        # Check tool allowlist
        if operation == "tool":
            tool_name = context.get("tool_name", "")
            if "*" not in constraints.tool_allowlist and tool_name not in constraints.tool_allowlist:
                return False, f"Tool '{tool_name}' not in allowlist for {constraints.mode.value} mode"

        # Check transaction value limits
        if operation == "transaction":
            value_eth = context.get("value_eth", 0)
            if constraints.max_transaction_value_eth is not None:
                if value_eth > constraints.max_transaction_value_eth:
                    return False, (
                        f"Transaction value {value_eth} ETH exceeds limit "
                        f"{constraints.max_transaction_value_eth} ETH in {constraints.mode.value} mode"
                    )

        # Check human approval requirement
        if constraints.require_human_approval:
            if not context.get("human_approved", False):
                return False, f"Human approval required in {constraints.mode.value} mode"

        return True, "Allowed"

    # =========================================================================
    # Event Management
    # =========================================================================

    def _create_event(
        self,
        event_type: str,
        action: str,
        outcome: str,
        severity: EventSeverity,
        principal_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> BoundaryEvent:
        """Create and log a security event."""
        event = BoundaryEvent(
            event_id=self._generate_id("evt_"),
            timestamp=datetime.now(),
            event_type=event_type,
            source="rra-module",
            action=action,
            outcome=outcome,
            severity=severity,
            mode=self._current_mode,
            principal_id=principal_id,
            resource_type=resource_type,
            resource_id=resource_id,
            context=context or {},
            previous_hash=self._last_event_hash,
        )

        # Sign event
        event.signature = self._event_signer.sign_event(event)

        # Update chain
        self._last_event_hash = event.compute_hash()
        self._event_chain.append(event)

        # Keep only last 10000 events in memory
        if len(self._event_chain) > 10000:
            self._event_chain = self._event_chain[-10000:]

        # Forward to external daemon if connected
        if self._use_external and self._external_daemon:
            self._external_daemon.submit_event(event)

        # Forward to SIEM if enabled
        if self._enable_siem and self._siem_callback:
            try:
                self._siem_callback(event)
            except Exception as e:
                logger.warning(f"SIEM forwarding failed: {e}")

        return event

    def get_event_chain(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        severity_min: Optional[EventSeverity] = None,
    ) -> List[BoundaryEvent]:
        """
        Get events from the audit chain.

        Args:
            limit: Maximum events to return
            event_type: Filter by event type
            severity_min: Filter by minimum severity

        Returns:
            List of events (newest first)
        """
        events = list(reversed(self._event_chain))

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if severity_min:
            events = [e for e in events if e.severity.value >= severity_min.value]

        return events[:limit]

    def verify_event_chain(self) -> Tuple[bool, str]:
        """
        Verify integrity of the event chain.

        Returns:
            Tuple of (valid, message)
        """
        if not self._event_chain:
            return True, "Empty chain"

        for i, event in enumerate(self._event_chain):
            # Verify hash chain
            if i > 0:
                expected_prev_hash = self._event_chain[i - 1].compute_hash()
                if event.previous_hash != expected_prev_hash:
                    return False, f"Hash chain broken at event {event.event_id}"

            # Verify signature
            if event.signature and not self._event_signer.verify_signature(event, event.signature):
                return False, f"Invalid signature on event {event.event_id}"

        return True, f"Chain valid ({len(self._event_chain)} events)"

    def export_events_cef(self, limit: int = 1000) -> List[str]:
        """Export events in CEF format for SIEM ingestion."""
        return [e.to_cef() for e in self.get_event_chain(limit=limit)]

    def export_events_json(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Export events in JSON format for SIEM ingestion."""
        return [e.to_json() for e in self.get_event_chain(limit=limit)]

    # =========================================================================
    # Policy Management
    # =========================================================================

    def create_policy(
        self,
        name: str,
        description: str,
        resource_type: ResourceType,
        resource_id: str,
        permissions: Permission,
        conditions: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None
    ) -> AccessPolicy:
        """Create a new access policy."""
        policy = AccessPolicy(
            policy_id=self._generate_id("policy_"),
            name=name,
            description=description,
            resource_type=resource_type,
            resource_id=resource_id,
            permissions=permissions,
            conditions=conditions or {},
            expires_at=datetime.now() + timedelta(days=expires_in_days) if expires_in_days else None,
        )

        self.policies[policy.policy_id] = policy
        self._save_state()

        return policy

    def get_policy(self, policy_id: str) -> Optional[AccessPolicy]:
        return self.policies.get(policy_id)

    def revoke_policy(self, policy_id: str) -> AccessPolicy:
        """Revoke an access policy."""
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")

        policy.active = False
        self._save_state()

        return policy

    def list_policies(
        self,
        resource_type: Optional[ResourceType] = None,
        active_only: bool = True
    ) -> List[AccessPolicy]:
        """List policies with optional filters."""
        policies = list(self.policies.values())

        if resource_type:
            policies = [p for p in policies if p.resource_type == resource_type]

        if active_only:
            policies = [p for p in policies if p.is_valid]

        return policies

    # =========================================================================
    # Principal Management
    # =========================================================================

    def register_principal(
        self,
        principal_type: str,
        name: str,
        address: Optional[str] = None
    ) -> Principal:
        """Register a new principal (user, agent, service)."""
        principal = Principal(
            principal_id=self._generate_id("principal_"),
            principal_type=principal_type,
            address=address,
            name=name,
        )

        self.principals[principal.principal_id] = principal
        self._save_state()

        return principal

    def get_principal(self, principal_id: str) -> Optional[Principal]:
        return self.principals.get(principal_id)

    def get_principal_by_address(self, address: str) -> Optional[Principal]:
        """Find principal by Ethereum address."""
        address = address.lower()
        for principal in self.principals.values():
            if principal.address and principal.address.lower() == address:
                return principal
        return None

    def assign_policy(self, principal_id: str, policy_id: str) -> Principal:
        """Assign a policy to a principal."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")

        if policy_id not in principal.policies:
            principal.policies.append(policy_id)
            self._save_state()

        return principal

    def remove_policy(self, principal_id: str, policy_id: str) -> Principal:
        """Remove a policy from a principal."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        if policy_id in principal.policies:
            principal.policies.remove(policy_id)
            self._save_state()

        return principal

    # =========================================================================
    # Token Management
    # =========================================================================

    def issue_token(
        self,
        principal_id: str,
        scopes: List[str],
        expires_in_hours: int = 24
    ) -> tuple[str, AccessToken]:
        """Issue an access token for a principal."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        if not principal.active:
            raise ValueError("Principal is not active")

        # Generate token
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)

        token = AccessToken(
            token_id=self._generate_id("token_"),
            token_hash=token_hash,
            principal_id=principal_id,
            scopes=scopes,
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=expires_in_hours),
        )

        self.tokens[token.token_id] = token
        self._save_state()

        return raw_token, token

    def validate_token(self, raw_token: str) -> Optional[AccessToken]:
        """Validate an access token."""
        token_hash = self._hash_token(raw_token)

        for token in self.tokens.values():
            if token.token_hash == token_hash:
                if token.is_valid:
                    return token
                break

        return None

    def revoke_token(self, token_id: str) -> AccessToken:
        """Revoke an access token."""
        token = self.tokens.get(token_id)
        if not token:
            raise ValueError(f"Token not found: {token_id}")

        token.revoked = True
        self._save_state()

        return token

    # =========================================================================
    # Access Control
    # =========================================================================

    def check_access(
        self,
        principal_id: str,
        resource_type: ResourceType,
        resource_id: str,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str]:
        """
        Check if a principal has access to a resource.

        Returns:
            Tuple of (granted, reason)
        """
        context = context or {}

        principal = self.principals.get(principal_id)
        if not principal:
            reason = "Principal not found"
            self._log_access(principal_id, resource_type, resource_id, permission, False, reason, context)
            return False, reason

        if not principal.active:
            reason = "Principal is not active"
            self._log_access(principal_id, resource_type, resource_id, permission, False, reason, context)
            return False, reason

        # Check each policy assigned to the principal
        for policy_id in principal.policies:
            policy = self.policies.get(policy_id)
            if not policy or not policy.is_valid:
                continue

            # Check if policy applies to this resource
            if not policy.matches_resource(resource_type, resource_id):
                continue

            # Check if policy grants the required permission
            if not (policy.permissions & permission):
                continue

            # Check conditions
            if not policy.check_conditions(context):
                continue

            # Access granted
            reason = f"Granted by policy: {policy.name}"
            self._log_access(principal_id, resource_type, resource_id, permission, True, reason, context)
            return True, reason

        reason = "No matching policy found"
        self._log_access(principal_id, resource_type, resource_id, permission, False, reason, context)
        return False, reason

    def check_token_access(
        self,
        raw_token: str,
        resource_type: ResourceType,
        resource_id: str,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str]:
        """Check access using a token."""
        token = self.validate_token(raw_token)
        if not token:
            return False, "Invalid or expired token"

        # Check if token scope allows this resource type
        scope_name = resource_type.value
        if scope_name not in token.scopes and "*" not in token.scopes:
            return False, f"Token scope does not include: {scope_name}"

        return self.check_access(
            token.principal_id,
            resource_type,
            resource_id,
            permission,
            context
        )

    def _log_access(
        self,
        principal_id: str,
        resource_type: ResourceType,
        resource_id: str,
        permission: Permission,
        granted: bool,
        reason: str,
        context: Dict[str, Any]
    ) -> None:
        """Log an access attempt."""
        log = AccessLog(
            log_id=self._generate_id("log_"),
            timestamp=datetime.now(),
            principal_id=principal_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
            granted=granted,
            reason=reason,
            context=context,
        )
        self.access_logs.append(log)

        # Keep only last 1000 logs in memory
        if len(self.access_logs) > 1000:
            self.access_logs = self.access_logs[-1000:]

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def grant_repository_access(
        self,
        principal_id: str,
        repo_id: str,
        permissions: Permission = Permission.STANDARD
    ) -> AccessPolicy:
        """Grant access to a repository."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        policy = self.create_policy(
            name=f"Repo access: {repo_id}",
            description=f"Access policy for repository {repo_id}",
            resource_type=ResourceType.REPOSITORY,
            resource_id=repo_id,
            permissions=permissions,
        )

        self.assign_policy(principal_id, policy.policy_id)

        return policy

    def grant_agent_access(
        self,
        principal_id: str,
        agent_id: str,
        permissions: Permission = Permission.NEGOTIATE | Permission.QUOTE
    ) -> AccessPolicy:
        """Grant access to an agent."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        policy = self.create_policy(
            name=f"Agent access: {agent_id}",
            description=f"Access policy for agent {agent_id}",
            resource_type=ResourceType.AGENT,
            resource_id=agent_id,
            permissions=permissions,
        )

        self.assign_policy(principal_id, policy.policy_id)

        return policy

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_access_stats(self) -> Dict[str, Any]:
        """Get access control statistics."""
        recent_logs = [l for l in self.access_logs if l.timestamp > datetime.now() - timedelta(hours=24)]

        return {
            "total_policies": len(self.policies),
            "active_policies": len([p for p in self.policies.values() if p.is_valid]),
            "total_principals": len(self.principals),
            "active_principals": len([p for p in self.principals.values() if p.active]),
            "total_tokens": len(self.tokens),
            "valid_tokens": len([t for t in self.tokens.values() if t.is_valid]),
            "access_logs_24h": len(recent_logs),
            "granted_24h": len([l for l in recent_logs if l.granted]),
            "denied_24h": len([l for l in recent_logs if not l.granted]),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "policies": {pid: p.to_dict() for pid, p in self.policies.items()},
            "principals": {pid: p.to_dict() for pid, p in self.principals.items()},
            "tokens": {tid: t.to_dict() for tid, t in self.tokens.items()},
        }

        with open(self.data_dir / "permissions_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        state_file = self.data_dir / "permissions_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.policies = {pid: AccessPolicy.from_dict(p) for pid, p in state.get("policies", {}).items()}
            self.principals = {pid: Principal.from_dict(p) for pid, p in state.get("principals", {}).items()}
            self.tokens = {tid: AccessToken.from_dict(t) for tid, t in state.get("tokens", {}).items()}
        except (json.JSONDecodeError, KeyError):
            pass


def create_boundary_daemon(
    data_dir: Optional[str] = None,
    connect_external: bool = False,
    enable_siem: bool = False,
    siem_callback: Optional[Callable[[BoundaryEvent], None]] = None,
) -> BoundaryDaemon:
    """
    Factory function to create a boundary daemon.

    Args:
        data_dir: Directory for storing permission state
        connect_external: Whether to try connecting to external daemon
        enable_siem: Whether to enable SIEM event forwarding
        siem_callback: Callback function for SIEM events

    Returns:
        Configured BoundaryDaemon instance
    """
    path = Path(data_dir) if data_dir else None

    external_daemon = None
    if connect_external:
        external_daemon = DaemonConnection()

    return BoundaryDaemon(
        data_dir=path,
        external_daemon=external_daemon,
        enable_siem_forwarding=enable_siem,
        siem_callback=siem_callback,
    )


def create_connected_boundary_daemon(
    socket_path: Optional[str] = None,
    http_url: Optional[str] = None,
    data_dir: Optional[str] = None,
    enable_siem: bool = True,
    siem_callback: Optional[Callable[[BoundaryEvent], None]] = None,
) -> BoundaryDaemon:
    """
    Factory function to create a boundary daemon connected to external daemon.

    Args:
        socket_path: Unix socket path for daemon connection
        http_url: HTTP URL for daemon connection
        data_dir: Directory for storing permission state
        enable_siem: Whether to enable SIEM event forwarding
        siem_callback: Callback function for SIEM events

    Returns:
        Configured BoundaryDaemon instance connected to external daemon
    """
    path = Path(data_dir) if data_dir else None
    external_daemon = DaemonConnection(
        socket_path=socket_path,
        http_url=http_url,
    )

    return BoundaryDaemon(
        data_dir=path,
        external_daemon=external_daemon,
        enable_siem_forwarding=enable_siem,
        siem_callback=siem_callback,
    )
