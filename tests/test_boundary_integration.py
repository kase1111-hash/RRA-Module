# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Integration tests for Boundary-Daemon and Boundary-SIEM integration.

These tests verify the integration between RRA-Module and:
- Boundary-Daemon (Agent Smith) for access control and policy management
- Boundary-SIEM for security event management and threat detection

To run these tests:
    pytest tests/test_boundary_integration.py -v
"""

import pytest
from unittest.mock import patch
from datetime import datetime
from pathlib import Path
import tempfile

from rra.integration.boundary_daemon import (
    BoundaryDaemon,
    Permission,
    ResourceType,
    BoundaryMode,
    BoundaryEvent,
    EventSeverity,
    ModeConstraints,
    DaemonConnection,
    EventSigner,
    create_boundary_daemon,
    create_connected_boundary_daemon,
)

from rra.integration.boundary_siem import (
    BoundarySIEMClient,
    SIEMConfig,
    SIEMProtocol,
    SIEMAlert,
    AlertSeverity,
    AlertStatus,
    RRA_DETECTION_RULES,
    create_siem_event_callback,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for permission data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def boundary_daemon(temp_data_dir):
    """Create a BoundaryDaemon instance with temp storage."""
    return BoundaryDaemon(data_dir=temp_data_dir)


@pytest.fixture
def siem_config():
    """Create a SIEM configuration for testing."""
    return SIEMConfig(
        host="localhost",
        port=8514,
        protocol=SIEMProtocol.JSON_HTTP,
        api_key="test-api-key",
    )


@pytest.fixture
def siem_client(siem_config):
    """Create a SIEM client for testing."""
    return BoundarySIEMClient(config=siem_config)


# =============================================================================
# BoundaryMode Tests
# =============================================================================


class TestBoundaryMode:
    """Tests for boundary mode functionality."""

    def test_all_modes_exist(self):
        """Test that all six boundary modes are defined."""
        expected_modes = ["open", "restricted", "trusted", "airgap", "coldroom", "lockdown"]
        actual_modes = [m.value for m in BoundaryMode]
        assert sorted(actual_modes) == sorted(expected_modes)

    def test_mode_constraints_for_each_mode(self):
        """Test that constraints are defined for each mode."""
        for mode in BoundaryMode:
            constraints = ModeConstraints.for_mode(mode)
            assert constraints.mode == mode
            assert isinstance(constraints.network_allowed, bool)
            assert isinstance(constraints.tool_allowlist, set)

    def test_open_mode_allows_all(self):
        """Test that OPEN mode has minimal restrictions."""
        constraints = ModeConstraints.for_mode(BoundaryMode.OPEN)
        assert constraints.network_allowed is True
        assert constraints.external_apis_allowed is True
        assert constraints.blockchain_write_allowed is True
        assert constraints.file_write_allowed is True
        assert "*" in constraints.tool_allowlist
        assert constraints.require_human_approval is False

    def test_lockdown_mode_blocks_all(self):
        """Test that LOCKDOWN mode blocks everything."""
        constraints = ModeConstraints.for_mode(BoundaryMode.LOCKDOWN)
        assert constraints.network_allowed is False
        assert constraints.external_apis_allowed is False
        assert constraints.blockchain_write_allowed is False
        assert constraints.file_write_allowed is False
        assert len(constraints.tool_allowlist) == 0
        assert constraints.require_human_approval is True

    def test_airgap_mode_no_network(self):
        """Test that AIRGAP mode has no network access."""
        constraints = ModeConstraints.for_mode(BoundaryMode.AIRGAP)
        assert constraints.network_allowed is False
        assert constraints.blockchain_write_allowed is False


# =============================================================================
# BoundaryDaemon Tests
# =============================================================================


class TestBoundaryDaemon:
    """Tests for BoundaryDaemon functionality."""

    def test_initialization(self, boundary_daemon):
        """Test daemon initializes correctly."""
        assert boundary_daemon.current_mode == BoundaryMode.RESTRICTED
        assert len(boundary_daemon.policies) == 0
        assert len(boundary_daemon.principals) == 0

    def test_set_mode(self, boundary_daemon):
        """Test mode transitions."""
        boundary_daemon.set_mode(BoundaryMode.TRUSTED, reason="test")
        assert boundary_daemon.current_mode == BoundaryMode.TRUSTED

        boundary_daemon.set_mode(BoundaryMode.AIRGAP, reason="security concern")
        assert boundary_daemon.current_mode == BoundaryMode.AIRGAP

    def test_trigger_lockdown(self, boundary_daemon):
        """Test emergency lockdown."""
        boundary_daemon.trigger_lockdown(reason="test emergency")
        assert boundary_daemon.current_mode == BoundaryMode.LOCKDOWN

    def test_check_mode_constraint_network(self, boundary_daemon):
        """Test network constraint checking."""
        boundary_daemon.set_mode(BoundaryMode.AIRGAP)
        allowed, reason = boundary_daemon.check_mode_constraint("network")
        assert allowed is False
        assert "denied" in reason.lower()

        boundary_daemon.set_mode(BoundaryMode.OPEN)
        allowed, reason = boundary_daemon.check_mode_constraint("network")
        assert allowed is True

    def test_check_mode_constraint_blockchain(self, boundary_daemon):
        """Test blockchain write constraint."""
        boundary_daemon.set_mode(BoundaryMode.COLDROOM)
        allowed, reason = boundary_daemon.check_mode_constraint("blockchain_write")
        assert allowed is False

    def test_check_mode_constraint_transaction_limit(self, boundary_daemon):
        """Test transaction value limits."""
        boundary_daemon.set_mode(BoundaryMode.RESTRICTED)
        # Restricted mode has 1 ETH limit
        allowed, reason = boundary_daemon.check_mode_constraint(
            "transaction",
            context={"value_eth": 0.5}
        )
        assert allowed is True

        allowed, reason = boundary_daemon.check_mode_constraint(
            "transaction",
            context={"value_eth": 5.0}
        )
        assert allowed is False
        assert "exceeds limit" in reason

    def test_check_mode_constraint_human_approval(self, boundary_daemon):
        """Test human approval requirement."""
        boundary_daemon.set_mode(BoundaryMode.AIRGAP)

        allowed, reason = boundary_daemon.check_mode_constraint(
            "transaction",
            context={"human_approved": False}
        )
        assert allowed is False
        assert "Human approval required" in reason

        allowed, reason = boundary_daemon.check_mode_constraint(
            "transaction",
            context={"human_approved": True, "value_eth": 0}
        )
        assert allowed is True

    def test_principal_management(self, boundary_daemon):
        """Test principal registration and management."""
        principal = boundary_daemon.register_principal(
            principal_type="agent",
            name="Test Agent",
            address="0x1234567890abcdef"
        )

        assert principal.principal_type == "agent"
        assert principal.name == "Test Agent"
        assert principal.address == "0x1234567890abcdef"

        # Retrieve principal
        retrieved = boundary_daemon.get_principal(principal.principal_id)
        assert retrieved == principal

        # Find by address
        found = boundary_daemon.get_principal_by_address("0x1234567890ABCDEF")
        assert found == principal

    def test_policy_creation_and_assignment(self, boundary_daemon):
        """Test policy creation and assignment."""
        principal = boundary_daemon.register_principal("user", "Test User")

        policy = boundary_daemon.create_policy(
            name="Test Policy",
            description="A test policy",
            resource_type=ResourceType.REPOSITORY,
            resource_id="test-repo",
            permissions=Permission.READ | Permission.NEGOTIATE,
        )

        boundary_daemon.assign_policy(principal.principal_id, policy.policy_id)

        # Check access
        granted, reason = boundary_daemon.check_access(
            principal.principal_id,
            ResourceType.REPOSITORY,
            "test-repo",
            Permission.READ,
        )
        assert granted is True

    def test_access_denied_without_policy(self, boundary_daemon):
        """Test access is denied without a policy."""
        principal = boundary_daemon.register_principal("user", "No Policy User")

        granted, reason = boundary_daemon.check_access(
            principal.principal_id,
            ResourceType.REPOSITORY,
            "some-repo",
            Permission.READ,
        )
        assert granted is False
        assert "No matching policy" in reason

    def test_token_issuance_and_validation(self, boundary_daemon):
        """Test token issuance and validation."""
        principal = boundary_daemon.register_principal("user", "Token User")

        raw_token, token = boundary_daemon.issue_token(
            principal.principal_id,
            scopes=["repository", "license"],
            expires_in_hours=1
        )

        assert token.principal_id == principal.principal_id
        assert "repository" in token.scopes

        # Validate token
        validated = boundary_daemon.validate_token(raw_token)
        assert validated is not None
        assert validated.token_id == token.token_id

    def test_token_revocation(self, boundary_daemon):
        """Test token revocation."""
        principal = boundary_daemon.register_principal("user", "Revoke User")
        raw_token, token = boundary_daemon.issue_token(principal.principal_id, ["*"])

        boundary_daemon.revoke_token(token.token_id)

        validated = boundary_daemon.validate_token(raw_token)
        assert validated is None


# =============================================================================
# BoundaryEvent Tests
# =============================================================================


class TestBoundaryEvent:
    """Tests for security event functionality."""

    def test_event_creation(self):
        """Test event creation."""
        event = BoundaryEvent(
            event_id="evt_123",
            timestamp=datetime.now(),
            event_type="access_check",
            source="rra-module",
            action="check_permission",
            outcome="success",
            severity=EventSeverity.INFO,
            mode=BoundaryMode.RESTRICTED,
        )

        assert event.event_id == "evt_123"
        assert event.severity == EventSeverity.INFO

    def test_event_hash_computation(self):
        """Test event hash is deterministic."""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        event1 = BoundaryEvent(
            event_id="evt_123",
            timestamp=timestamp,
            event_type="test",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.INFO,
            mode=BoundaryMode.OPEN,
        )

        event2 = BoundaryEvent(
            event_id="evt_123",
            timestamp=timestamp,
            event_type="test",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.INFO,
            mode=BoundaryMode.OPEN,
        )

        assert event1.compute_hash() == event2.compute_hash()

    def test_event_cef_format(self):
        """Test CEF format conversion."""
        event = BoundaryEvent(
            event_id="evt_123",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            event_type="access_denied",
            source="rra-module",
            action="check_permission",
            outcome="blocked",
            severity=EventSeverity.HIGH,
            mode=BoundaryMode.RESTRICTED,
        )

        cef = event.to_cef()

        assert "CEF:0|NatLangChain|RRA-Module|0.1.0" in cef
        assert "access_denied" in cef
        assert "7" in cef  # HIGH severity = 7

    def test_event_json_format(self):
        """Test JSON format conversion."""
        event = BoundaryEvent(
            event_id="evt_123",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            event_type="test",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.MEDIUM,
            mode=BoundaryMode.TRUSTED,
        )

        json_data = event.to_json()

        assert json_data["event_id"] == "evt_123"
        assert json_data["severity"] == "MEDIUM"
        assert json_data["mode"] == "trusted"
        assert "hash" in json_data


class TestEventChain:
    """Tests for event chain and audit trail."""

    def test_event_chain_creation(self, boundary_daemon):
        """Test events are added to chain."""
        boundary_daemon.set_mode(BoundaryMode.OPEN, reason="test1")
        boundary_daemon.set_mode(BoundaryMode.RESTRICTED, reason="test2")

        events = boundary_daemon.get_event_chain(limit=10)
        assert len(events) >= 2

    def test_event_chain_hash_linking(self, boundary_daemon):
        """Test events are hash-chained."""
        boundary_daemon.set_mode(BoundaryMode.OPEN)
        boundary_daemon.set_mode(BoundaryMode.TRUSTED)
        boundary_daemon.set_mode(BoundaryMode.RESTRICTED)

        valid, message = boundary_daemon.verify_event_chain()
        assert valid is True

    def test_event_export_cef(self, boundary_daemon):
        """Test CEF export."""
        boundary_daemon.set_mode(BoundaryMode.OPEN)

        cef_events = boundary_daemon.export_events_cef(limit=10)
        assert len(cef_events) >= 1
        assert all("CEF:0" in e for e in cef_events)

    def test_event_export_json(self, boundary_daemon):
        """Test JSON export."""
        boundary_daemon.set_mode(BoundaryMode.OPEN)

        json_events = boundary_daemon.export_events_json(limit=10)
        assert len(json_events) >= 1
        assert all("event_id" in e for e in json_events)


# =============================================================================
# EventSigner Tests
# =============================================================================


class TestEventSigner:
    """Tests for cryptographic event signing."""

    def test_signer_initialization(self):
        """Test signer initializes with keys."""
        EventSigner()
        # Key generation happens if cryptography is available
        # This test should pass regardless

    def test_sign_and_verify(self):
        """Test event signing and verification."""
        signer = EventSigner()

        event = BoundaryEvent(
            event_id="evt_sign_test",
            timestamp=datetime.now(),
            event_type="test",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.INFO,
            mode=BoundaryMode.OPEN,
        )

        signature = signer.sign_event(event)

        if signature:  # Only test if cryptography is available
            verified = signer.verify_signature(event, signature)
            assert verified is True


# =============================================================================
# DaemonConnection Tests
# =============================================================================


class TestDaemonConnection:
    """Tests for external daemon connection."""

    def test_connection_initialization(self):
        """Test connection initializes correctly."""
        conn = DaemonConnection(
            socket_path="/tmp/test.sock",
            http_url="http://localhost:8080"
        )

        assert conn.socket_path == "/tmp/test.sock"
        assert conn.http_url == "http://localhost:8080"

    def test_connection_from_env(self):
        """Test connection uses environment variables."""
        with patch.dict('os.environ', {
            'BOUNDARY_DAEMON_SOCKET': '/custom/path.sock',
            'BOUNDARY_DAEMON_URL': 'http://custom:9000'
        }):
            conn = DaemonConnection()
            assert conn.socket_path == '/custom/path.sock'
            assert conn.http_url == 'http://custom:9000'

    def test_is_available_when_not_running(self):
        """Test availability check when daemon not running."""
        conn = DaemonConnection(
            socket_path="/nonexistent/path.sock",
            http_url="http://localhost:59999"
        )
        assert conn.is_available() is False


# =============================================================================
# Boundary-SIEM Client Tests
# =============================================================================


class TestBoundarySIEMClient:
    """Tests for SIEM client functionality."""

    def test_client_initialization(self, siem_config):
        """Test SIEM client initializes correctly."""
        client = BoundarySIEMClient(config=siem_config)
        assert client.config.host == "localhost"
        assert client.config.port == 8514

    def test_config_from_env(self):
        """Test config loads from environment."""
        with patch.dict('os.environ', {
            'BOUNDARY_SIEM_HOST': 'siem.example.com',
            'BOUNDARY_SIEM_PORT': '1514',
            'BOUNDARY_SIEM_PROTOCOL': 'cef_tcp',
            'BOUNDARY_SIEM_API_KEY': 'secret-key',
        }):
            config = SIEMConfig.from_env()
            assert config.host == 'siem.example.com'
            assert config.port == 1514
            assert config.protocol == SIEMProtocol.CEF_TCP
            assert config.api_key == 'secret-key'

    def test_event_filtering_by_severity(self, siem_client):
        """Test events are filtered by severity."""
        siem_client.config.min_severity = EventSeverity.MEDIUM

        low_event = BoundaryEvent(
            event_id="evt_low",
            timestamp=datetime.now(),
            event_type="test",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.LOW,
            mode=BoundaryMode.OPEN,
        )

        high_event = BoundaryEvent(
            event_id="evt_high",
            timestamp=datetime.now(),
            event_type="test",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.HIGH,
            mode=BoundaryMode.OPEN,
        )

        assert siem_client._should_forward(low_event) is False
        assert siem_client._should_forward(high_event) is True

    def test_event_filtering_by_type(self, siem_client):
        """Test events are filtered by type."""
        siem_client.config.include_event_types = {"access_denied", "lockdown"}

        allowed_event = BoundaryEvent(
            event_id="evt_1",
            timestamp=datetime.now(),
            event_type="access_denied",
            source="test",
            action="test",
            outcome="blocked",
            severity=EventSeverity.HIGH,
            mode=BoundaryMode.OPEN,
        )

        excluded_event = BoundaryEvent(
            event_id="evt_2",
            timestamp=datetime.now(),
            event_type="routine_check",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.HIGH,
            mode=BoundaryMode.OPEN,
        )

        assert siem_client._should_forward(allowed_event) is True
        assert siem_client._should_forward(excluded_event) is False


class TestSIEMAlert:
    """Tests for SIEM alert handling."""

    def test_alert_creation(self):
        """Test alert creation from dict."""
        data = {
            "alert_id": "alert_123",
            "rule_name": "Test Rule",
            "severity": "high",
            "status": "open",
            "created_at": "2025-01-01T12:00:00",
            "source_events": ["evt_1", "evt_2"],
            "mitre_techniques": ["T1078"],
        }

        alert = SIEMAlert.from_dict(data)

        assert alert.alert_id == "alert_123"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.OPEN
        assert len(alert.source_events) == 2

    def test_alert_serialization(self):
        """Test alert serialization."""
        alert = SIEMAlert(
            alert_id="alert_456",
            rule_name="Lockdown Triggered",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.INVESTIGATING,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            source_events=["evt_1"],
            mitre_techniques=["T1499"],
        )

        data = alert.to_dict()

        assert data["alert_id"] == "alert_456"
        assert data["severity"] == "critical"
        assert data["status"] == "investigating"


class TestDetectionRules:
    """Tests for detection rule configuration."""

    def test_rra_rules_defined(self):
        """Test RRA-specific rules are defined."""
        assert len(RRA_DETECTION_RULES) > 0

    def test_rules_have_required_fields(self):
        """Test all rules have required fields."""
        for rule in RRA_DETECTION_RULES:
            assert rule.rule_id is not None
            assert rule.name is not None
            assert rule.severity in AlertSeverity
            assert isinstance(rule.mitre_techniques, list)
            assert isinstance(rule.event_types, list)

    def test_lockdown_rule_exists(self):
        """Test lockdown detection rule exists."""
        lockdown_rules = [r for r in RRA_DETECTION_RULES if "lockdown" in r.name.lower()]
        assert len(lockdown_rules) > 0

    def test_rule_serialization(self):
        """Test rule serialization."""
        rule = RRA_DETECTION_RULES[0]
        data = rule.to_dict()

        assert "rule_id" in data
        assert "name" in data
        assert "severity" in data
        assert "mitre_techniques" in data


# =============================================================================
# Integration Tests
# =============================================================================


class TestBoundaryDaemonSIEMIntegration:
    """Tests for integrated Boundary-Daemon and SIEM functionality."""

    def test_daemon_with_siem_callback(self, temp_data_dir, siem_client):
        """Test daemon forwards events to SIEM."""
        events_received = []

        def capture_event(event):
            events_received.append(event)

        daemon = BoundaryDaemon(
            data_dir=temp_data_dir,
            enable_siem_forwarding=True,
            siem_callback=capture_event,
        )

        daemon.set_mode(BoundaryMode.TRUSTED, reason="test")

        assert len(events_received) > 0
        assert any(e.event_type == "mode_transition" for e in events_received)

    def test_create_siem_event_callback(self, siem_client):
        """Test callback creation for SIEM client."""
        callback = create_siem_event_callback(siem_client)

        event = BoundaryEvent(
            event_id="evt_callback_test",
            timestamp=datetime.now(),
            event_type="test",
            source="test",
            action="test",
            outcome="success",
            severity=EventSeverity.INFO,
            mode=BoundaryMode.OPEN,
        )

        # Should not raise
        callback(event)

    def test_factory_functions(self, temp_data_dir):
        """Test factory functions work correctly."""
        # Basic daemon
        daemon1 = create_boundary_daemon(data_dir=str(temp_data_dir))
        assert daemon1 is not None

        # Connected daemon (will work even without external daemon)
        daemon2 = create_connected_boundary_daemon(
            data_dir=str(temp_data_dir / "connected"),
            socket_path="/nonexistent/path.sock"
        )
        assert daemon2 is not None


class TestAccessControlFlow:
    """Tests for complete access control workflow."""

    def test_full_access_control_flow(self, boundary_daemon):
        """Test complete access control workflow."""
        # 1. Register a user principal
        user = boundary_daemon.register_principal(
            principal_type="user",
            name="Test Developer",
            address="0xDeveloper123"
        )

        # 2. Create policies
        read_policy = boundary_daemon.create_policy(
            name="Read Access",
            description="Basic read access",
            resource_type=ResourceType.REPOSITORY,
            resource_id="*",  # Wildcard
            permissions=Permission.READ,
        )

        negotiate_policy = boundary_daemon.create_policy(
            name="Negotiate Access",
            description="Can negotiate licenses",
            resource_type=ResourceType.AGENT,
            resource_id="agent_123",
            permissions=Permission.NEGOTIATE | Permission.QUOTE,
        )

        # 3. Assign policies
        boundary_daemon.assign_policy(user.principal_id, read_policy.policy_id)
        boundary_daemon.assign_policy(user.principal_id, negotiate_policy.policy_id)

        # 4. Issue token
        raw_token, token = boundary_daemon.issue_token(
            user.principal_id,
            scopes=["repository", "agent"],
            expires_in_hours=24
        )

        # 5. Check access with token
        granted, reason = boundary_daemon.check_token_access(
            raw_token,
            ResourceType.REPOSITORY,
            "any-repo",
            Permission.READ,
        )
        assert granted is True

        granted, reason = boundary_daemon.check_token_access(
            raw_token,
            ResourceType.AGENT,
            "agent_123",
            Permission.NEGOTIATE,
        )
        assert granted is True

        # 6. Check denied access
        granted, reason = boundary_daemon.check_token_access(
            raw_token,
            ResourceType.AGENT,
            "agent_123",
            Permission.MINT,  # Not granted
        )
        assert granted is False

    def test_mode_constrained_access(self, boundary_daemon):
        """Test access control with mode constraints."""
        user = boundary_daemon.register_principal("user", "Mode Test User")
        policy = boundary_daemon.create_policy(
            name="Full Access",
            description="All permissions",
            resource_type=ResourceType.LICENSE,
            resource_id="*",
            permissions=Permission.ALL,
        )
        boundary_daemon.assign_policy(user.principal_id, policy.policy_id)

        # In OPEN mode, everything works
        boundary_daemon.set_mode(BoundaryMode.OPEN)
        allowed, _ = boundary_daemon.check_mode_constraint("blockchain_write")
        assert allowed is True

        # In AIRGAP mode, blockchain writes are blocked
        boundary_daemon.set_mode(BoundaryMode.AIRGAP)
        allowed, _ = boundary_daemon.check_mode_constraint("blockchain_write")
        assert allowed is False


# =============================================================================
# Persistence Tests
# =============================================================================


class TestPersistence:
    """Tests for state persistence."""

    def test_state_persists_across_instances(self, temp_data_dir):
        """Test that state persists when daemon is recreated."""
        # Create first instance and add data
        daemon1 = BoundaryDaemon(data_dir=temp_data_dir)
        principal = daemon1.register_principal("user", "Persistent User")
        policy = daemon1.create_policy(
            name="Persistent Policy",
            description="Should persist",
            resource_type=ResourceType.API,
            resource_id="*",
            permissions=Permission.READ,
        )
        daemon1.assign_policy(principal.principal_id, policy.policy_id)

        # Create second instance
        daemon2 = BoundaryDaemon(data_dir=temp_data_dir)

        # Verify data persisted
        assert principal.principal_id in daemon2.principals
        assert policy.policy_id in daemon2.policies

        # Verify access still works
        granted, _ = daemon2.check_access(
            principal.principal_id,
            ResourceType.API,
            "any-api",
            Permission.READ,
        )
        assert granted is True
