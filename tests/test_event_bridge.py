# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Off-Chain Event Bridging (Phase 6.9).

Tests event bridging and validation:
- Event requests and fetching
- Attestation submission and consensus
- Event validators
- Data integrity verification
"""

import pytest
from datetime import datetime, timedelta
import json
import hashlib

from rra.oracles.event_bridge import (
    EventSource,
    EventStatus,
    BridgedEvent,
    APIEventFetcher,
    IPFSEventFetcher,
    GitHubEventFetcher,
    create_event_bridge,
)
from rra.oracles.validators import (
    ValidationResult,
    SchemaValidator,
    HashValidator,
    TimestampValidator,
    SignatureValidator,
    CompositeValidator,
    GitHubEventValidator,
    FinancialEventValidator,
)


# =============================================================================
# EventBridge Tests
# =============================================================================

class TestEventBridge:
    """Test EventBridge functionality."""

    @pytest.fixture
    def bridge(self):
        """Create an event bridge without persistence."""
        return create_event_bridge()

    @pytest.fixture
    def persistent_bridge(self, tmp_path):
        """Create an event bridge with persistence."""
        return create_event_bridge(data_dir=str(tmp_path))

    def test_create_bridge(self, bridge):
        """Test bridge creation."""
        assert bridge is not None
        assert bridge.consensus_threshold == 2

    @pytest.mark.asyncio
    async def test_request_event_no_fetch(self, bridge):
        """Test requesting event without immediate fetch."""
        event = await bridge.request_event(
            source=EventSource.API,
            source_uri="https://api.example.com/data",
            dispute_id="dispute_123",
            requester="0x1111111111111111111111111111111111111111",
            fetch_immediately=False,
        )

        assert event is not None
        assert event.event_id.startswith("evt_")
        assert event.source == EventSource.API
        assert event.status == EventStatus.PENDING
        assert event.dispute_id == "dispute_123"
        assert event.data is None

    @pytest.mark.asyncio
    async def test_request_event_with_dispute_link(self, bridge):
        """Test event linked to dispute."""
        event = await bridge.request_event(
            source=EventSource.IPFS,
            source_uri="ipfs://QmTest123",
            dispute_id="dispute_456",
            fetch_immediately=False,
        )

        # Check dispute link
        dispute_events = bridge.get_dispute_events("dispute_456")
        assert len(dispute_events) == 1
        assert dispute_events[0].event_id == event.event_id

    def test_submit_attestation(self, bridge):
        """Test attestation submission."""
        # Create event synchronously for testing
        event = BridgedEvent(
            event_id="evt_test123",
            source=EventSource.API,
            status=EventStatus.PENDING,
            consensus_threshold=2,
        )
        bridge.events[event.event_id] = event

        # Submit attestation
        attestation = bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x1111111111111111111111111111111111111111",
            is_valid=True,
            evidence_uri="ipfs://QmEvidence1",
        )

        assert attestation is not None
        assert attestation.is_valid is True

        # Check event updated
        event = bridge.get_event(event.event_id)
        assert event.valid_count == 1
        assert event.invalid_count == 0
        assert event.status == EventStatus.PENDING  # Not enough for consensus

    def test_attestation_consensus_valid(self, bridge):
        """Test consensus reached for valid event."""
        event = BridgedEvent(
            event_id="evt_consensus1",
            source=EventSource.GITHUB,
            status=EventStatus.PENDING,
            consensus_threshold=2,
        )
        bridge.events[event.event_id] = event

        # First attestation
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x1111111111111111111111111111111111111111",
            is_valid=True,
            evidence_uri="ipfs://evidence1",
        )

        assert bridge.get_event(event.event_id).status == EventStatus.PENDING

        # Second attestation (reaches consensus)
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x2222222222222222222222222222222222222222",
            is_valid=True,
            evidence_uri="ipfs://evidence2",
        )

        event = bridge.get_event(event.event_id)
        assert event.status == EventStatus.VERIFIED
        assert event.valid_count == 2

    def test_attestation_consensus_invalid(self, bridge):
        """Test consensus reached for invalid event."""
        event = BridgedEvent(
            event_id="evt_consensus2",
            source=EventSource.API,
            status=EventStatus.PENDING,
            consensus_threshold=2,
        )
        bridge.events[event.event_id] = event

        # Two invalid attestations
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x1111111111111111111111111111111111111111",
            is_valid=False,
            evidence_uri="ipfs://evidence1",
        )
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x2222222222222222222222222222222222222222",
            is_valid=False,
            evidence_uri="ipfs://evidence2",
        )

        event = bridge.get_event(event.event_id)
        assert event.status == EventStatus.REJECTED
        assert event.invalid_count == 2

    def test_attestation_disputed(self, bridge):
        """Test conflicting attestations leading to disputed status."""
        event = BridgedEvent(
            event_id="evt_disputed",
            source=EventSource.API,
            status=EventStatus.PENDING,
            consensus_threshold=2,
        )
        bridge.events[event.event_id] = event

        # Mixed attestations
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x1111111111111111111111111111111111111111",
            is_valid=True,
            evidence_uri="ipfs://evidence1",
        )
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x2222222222222222222222222222222222222222",
            is_valid=False,
            evidence_uri="ipfs://evidence2",
        )
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x3333333333333333333333333333333333333333",
            is_valid=True,
            evidence_uri="ipfs://evidence3",
        )
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x4444444444444444444444444444444444444444",
            is_valid=False,
            evidence_uri="ipfs://evidence4",
        )

        event = bridge.get_event(event.event_id)
        assert event.status == EventStatus.DISPUTED

    def test_duplicate_attestation_rejected(self, bridge):
        """Test that duplicate attestations are rejected."""
        event = BridgedEvent(
            event_id="evt_dup",
            source=EventSource.API,
            status=EventStatus.PENDING,
            consensus_threshold=2,
        )
        bridge.events[event.event_id] = event

        # First attestation
        att1 = bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x1111111111111111111111111111111111111111",
            is_valid=True,
            evidence_uri="ipfs://evidence1",
        )
        assert att1 is not None

        # Duplicate from same validator
        att2 = bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0x1111111111111111111111111111111111111111",
            is_valid=False,  # Different choice
            evidence_uri="ipfs://evidence2",
        )
        assert att2 is None  # Rejected

        # Check only first attestation counted
        event = bridge.get_event(event.event_id)
        assert event.total_attestations == 1
        assert event.valid_count == 1

    def test_register_validator(self, bridge):
        """Test validator registration."""
        bridge.register_validator(
            address="0x1111111111111111111111111111111111111111",
            stake=1000,
            metadata={"name": "Validator 1"},
        )

        assert bridge.is_registered_validator("0x1111111111111111111111111111111111111111")
        stats = bridge.get_validator_stats("0x1111111111111111111111111111111111111111")
        assert stats["stake"] == 1000

    def test_finalize_expired_events(self, bridge):
        """Test expiring old events."""
        # Create old event
        event = BridgedEvent(
            event_id="evt_old",
            source=EventSource.API,
            status=EventStatus.PENDING,
            requested_at=datetime.now() - timedelta(hours=48),  # 2 days old
            consensus_threshold=2,
        )
        bridge.events[event.event_id] = event

        # Finalize expired
        expired = bridge.finalize_expired_events()

        assert "evt_old" in expired
        assert bridge.get_event("evt_old").status == EventStatus.EXPIRED

    def test_get_stats(self, bridge):
        """Test bridge statistics."""
        # Create some events
        for i in range(5):
            event = BridgedEvent(
                event_id=f"evt_stat{i}",
                source=EventSource.API if i % 2 == 0 else EventSource.GITHUB,
                status=EventStatus.VERIFIED if i < 2 else EventStatus.PENDING,
            )
            bridge.events[event.event_id] = event

        stats = bridge.get_stats()

        assert stats["total_events"] == 5
        assert stats["verified"] == 2
        assert stats["pending"] == 3

    def test_persistence(self, persistent_bridge, tmp_path):
        """Test state persistence."""
        # Create event
        event = BridgedEvent(
            event_id="evt_persist",
            source=EventSource.IPFS,
            status=EventStatus.PENDING,
            dispute_id="dispute_persist",
        )
        persistent_bridge.events[event.event_id] = event
        persistent_bridge.dispute_events["dispute_persist"] = [event.event_id]
        persistent_bridge._save_state()

        # Create new bridge with same data dir
        new_bridge = create_event_bridge(data_dir=str(tmp_path))

        # Check event persisted
        found = new_bridge.get_event("evt_persist")
        assert found is not None
        assert found.source == EventSource.IPFS


# =============================================================================
# Event Fetcher Tests
# =============================================================================

class TestAPIEventFetcher:
    """Test API event fetcher."""

    def test_validate_uri(self):
        """Test URI validation."""
        fetcher = APIEventFetcher()

        assert fetcher.validate_uri("https://api.example.com/data") is True
        assert fetcher.validate_uri("http://localhost:8000/api") is True
        assert fetcher.validate_uri("ftp://example.com") is False
        assert fetcher.validate_uri("ipfs://Qm123") is False


class TestIPFSEventFetcher:
    """Test IPFS event fetcher."""

    def test_validate_uri(self):
        """Test URI validation."""
        fetcher = IPFSEventFetcher()

        assert fetcher.validate_uri("ipfs://QmTest123") is True
        assert fetcher.validate_uri("/ipfs/QmTest123") is True
        assert fetcher.validate_uri("QmTest123456789") is True
        assert fetcher.validate_uri("bafytest123") is True
        assert fetcher.validate_uri("https://example.com") is False

    def test_extract_cid(self):
        """Test CID extraction."""
        fetcher = IPFSEventFetcher()

        assert fetcher._extract_cid("ipfs://QmTest") == "QmTest"
        assert fetcher._extract_cid("/ipfs/QmTest") == "QmTest"
        assert fetcher._extract_cid("QmTest") == "QmTest"


class TestGitHubEventFetcher:
    """Test GitHub event fetcher."""

    def test_validate_uri(self):
        """Test URI validation."""
        fetcher = GitHubEventFetcher()

        assert fetcher.validate_uri("github://repos/owner/repo") is True
        assert fetcher.validate_uri("https://github.com/owner/repo") is True
        assert fetcher.validate_uri("repos/owner/repo") is True
        assert fetcher.validate_uri("https://example.com") is False

    def test_parse_github_uri(self):
        """Test GitHub URI parsing."""
        fetcher = GitHubEventFetcher()

        assert fetcher._parse_github_uri("github://repos/owner/repo") == "repos/owner/repo"
        assert fetcher._parse_github_uri("https://github.com/owner/repo") == "repos/owner/repo"


# =============================================================================
# Validator Tests
# =============================================================================

class TestSchemaValidator:
    """Test schema validator."""

    def test_validate_required_fields(self):
        """Test required field validation."""
        schema = {
            "required": ["name", "value"],
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
        }
        validator = SchemaValidator(schema)

        # Valid data
        report = validator.validate({"name": "test", "value": 123})
        assert report.result == ValidationResult.VALID

        # Missing required field
        report = validator.validate({"name": "test"})
        assert report.result == ValidationResult.INVALID
        assert "required_field:value" in report.checks_failed

    def test_validate_field_types(self):
        """Test field type validation."""
        schema = {
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
                "active": {"type": "boolean"},
            },
        }
        validator = SchemaValidator(schema)

        # Correct types
        report = validator.validate({"name": "test", "count": 5, "active": True})
        assert report.result == ValidationResult.VALID

        # Wrong types
        report = validator.validate({"name": 123, "count": "five", "active": "yes"})
        assert "type_check:name" in report.checks_failed
        assert "type_check:count" in report.checks_failed

    def test_validate_string_constraints(self):
        """Test string length and pattern constraints."""
        schema = {
            "properties": {
                "code": {
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 10,
                    "pattern": "^[A-Z]+$",
                },
            },
        }
        validator = SchemaValidator(schema)

        # Valid
        report = validator.validate({"code": "ABC"})
        assert report.result == ValidationResult.VALID

        # Too short
        report = validator.validate({"code": "AB"})
        assert "min_length:code" in report.checks_failed

        # Wrong pattern
        report = validator.validate({"code": "abc123"})
        assert "pattern:code" in report.checks_failed


class TestHashValidator:
    """Test hash validator."""

    def test_validate_hash_match(self):
        """Test hash matching."""
        validator = HashValidator()

        data = {"key": "value"}
        expected_hash = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()

        report = validator.validate(data, expected_hash=expected_hash)
        assert report.result == ValidationResult.VALID
        assert "hash_match" in report.checks_passed

    def test_validate_hash_mismatch(self):
        """Test hash mismatch detection."""
        validator = HashValidator()

        data = {"key": "value"}
        wrong_hash = "0" * 64

        report = validator.validate(data, expected_hash=wrong_hash)
        assert report.result == ValidationResult.INVALID
        assert "hash_match" in report.checks_failed


class TestTimestampValidator:
    """Test timestamp validator."""

    def test_validate_recent_timestamp(self):
        """Test recent timestamp validation."""
        validator = TimestampValidator(max_age_days=30)

        data = {"timestamp": datetime.now().isoformat()}
        report = validator.validate(data)

        assert report.result == ValidationResult.VALID
        assert "timestamp_not_stale" in report.checks_passed

    def test_validate_stale_timestamp(self):
        """Test stale timestamp detection."""
        validator = TimestampValidator(max_age_days=7)

        old_time = datetime.now() - timedelta(days=30)
        data = {"timestamp": old_time.isoformat()}
        report = validator.validate(data)

        assert report.result == ValidationResult.INVALID
        assert "timestamp_not_stale" in report.checks_failed

    def test_validate_future_timestamp(self):
        """Test future timestamp detection."""
        validator = TimestampValidator(allow_future=False)

        future_time = datetime.now() + timedelta(hours=1)
        data = {"timestamp": future_time.isoformat()}
        report = validator.validate(data)

        assert report.result == ValidationResult.INVALID
        assert "timestamp_not_future" in report.checks_failed


class TestSignatureValidator:
    """Test signature validator."""

    def test_validate_signature_format(self):
        """Test signature format validation."""
        validator = SignatureValidator()

        # Valid hex signature
        data = {"signature": "0x" + "a1b2c3d4" * 16, "signer": "0x1234"}
        report = validator.validate(data)
        assert "signature_format" in report.checks_passed

        # Invalid format
        data = {"signature": "not-hex", "signer": "0x1234"}
        report = validator.validate(data)
        assert "signature_format" in report.checks_failed

    def test_validate_trusted_signer(self):
        """Test trusted signer validation."""
        validator = SignatureValidator(
            trusted_signers={"0x1111111111111111111111111111111111111111"}
        )

        # Trusted signer
        data = {
            "signature": "0x" + "ab" * 32,
            "signer": "0x1111111111111111111111111111111111111111",
        }
        report = validator.validate(data)
        assert "signer_trusted" in report.checks_passed

        # Untrusted signer
        data = {
            "signature": "0x" + "ab" * 32,
            "signer": "0x2222222222222222222222222222222222222222",
        }
        report = validator.validate(data)
        assert "signer_trusted" in report.checks_failed


class TestCompositeValidator:
    """Test composite validator."""

    def test_validate_all_required(self):
        """Test composite with all required."""
        validators = [
            HashValidator(),
            TimestampValidator(max_age_days=30),
        ]
        composite = CompositeValidator(validators, require_all=True)

        data = {
            "key": "value",
            "timestamp": datetime.now().isoformat(),
        }

        report = composite.validate(data)
        assert report.metadata["validators_run"] == 2

    def test_validate_partial_pass(self):
        """Test composite with partial pass allowed."""
        validators = [
            HashValidator(),
            TimestampValidator(max_age_days=1),  # Will fail for old data
        ]
        composite = CompositeValidator(validators, require_all=False, min_pass_ratio=0.5)

        old_time = datetime.now() - timedelta(days=10)
        data = {
            "key": "value",
            "timestamp": old_time.isoformat(),
        }

        report = composite.validate(data)
        # Hash passes, timestamp fails - 50% pass rate
        assert report.metadata["validators_passed"] >= 1


class TestGitHubEventValidator:
    """Test GitHub event validator."""

    def test_validate_github_event(self):
        """Test GitHub event validation."""
        validator = GitHubEventValidator()

        event = {
            "repository": {
                "full_name": "owner/repo",
                "id": 12345,
            },
            "sender": {
                "login": "username",
            },
            "type": "push",
        }

        report = validator.validate(event)
        assert report.result == ValidationResult.VALID
        assert "repository_present" in report.checks_passed
        assert "valid_event_type" in report.checks_passed

    def test_validate_missing_repository(self):
        """Test validation without repository."""
        validator = GitHubEventValidator()

        event = {
            "sender": {"login": "username"},
        }

        report = validator.validate(event)
        assert "repository_present" in report.checks_failed


class TestFinancialEventValidator:
    """Test financial event validator."""

    def test_validate_financial_event(self):
        """Test financial event validation."""
        validator = FinancialEventValidator(min_amount=0, max_amount=1000000)

        event = {
            "amount": 500,
            "currency": "USD",
            "transaction_id": "tx_123",
            "sender": "0x1111",
            "recipient": "0x2222",
        }

        report = validator.validate(event)
        assert report.result == ValidationResult.VALID
        assert "amount_present" in report.checks_passed
        assert "amount_min" in report.checks_passed
        assert "amount_max" in report.checks_passed

    def test_validate_amount_out_of_range(self):
        """Test amount range validation."""
        validator = FinancialEventValidator(min_amount=100, max_amount=1000)

        # Too low
        report = validator.validate({"amount": 50})
        assert "amount_min" in report.checks_failed

        # Too high
        report = validator.validate({"amount": 5000})
        assert "amount_max" in report.checks_failed


# =============================================================================
# Integration Tests
# =============================================================================

class TestEventBridgeIntegration:
    """Integration tests for event bridge."""

    @pytest.mark.asyncio
    async def test_full_event_lifecycle(self):
        """Test complete event lifecycle from request to verification."""
        bridge = create_event_bridge(consensus_threshold=2)

        # 1. Request event
        event = await bridge.request_event(
            source=EventSource.GITHUB,
            source_uri="github://repos/owner/repo/commits",
            dispute_id="integration_dispute",
            requester="0x1111111111111111111111111111111111111111",
            fetch_immediately=False,
        )

        assert event.status == EventStatus.PENDING

        # 2. Register validators
        bridge.register_validator("0xv1", stake=1000)
        bridge.register_validator("0xv2", stake=1000)
        bridge.register_validator("0xv3", stake=500)

        # 3. Submit attestations
        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0xv1",
            is_valid=True,
            evidence_uri="ipfs://evidence1",
            reason="Data verified against GitHub API",
        )

        bridge.submit_attestation(
            event_id=event.event_id,
            validator_address="0xv2",
            is_valid=True,
            evidence_uri="ipfs://evidence2",
            reason="Confirmed via webhook",
        )

        # 4. Check verification
        event = bridge.get_event(event.event_id)
        assert event.status == EventStatus.VERIFIED
        assert event.valid_count == 2

        # 5. Check dispute link
        dispute_events = bridge.get_dispute_events("integration_dispute")
        assert len(dispute_events) == 1

    @pytest.mark.asyncio
    async def test_multi_event_dispute(self):
        """Test multiple events for same dispute."""
        bridge = create_event_bridge(consensus_threshold=1)

        dispute_id = "multi_event_dispute"

        # Create multiple events for same dispute
        event1 = await bridge.request_event(
            source=EventSource.GITHUB,
            source_uri="github://issue/1",
            dispute_id=dispute_id,
            fetch_immediately=False,
        )

        event2 = await bridge.request_event(
            source=EventSource.IPFS,
            source_uri="ipfs://QmContract",
            dispute_id=dispute_id,
            fetch_immediately=False,
        )

        event3 = await bridge.request_event(
            source=EventSource.API,
            source_uri="https://api.payment.com/tx/123",
            dispute_id=dispute_id,
            fetch_immediately=False,
        )

        # Check all linked
        dispute_events = bridge.get_dispute_events(dispute_id)
        assert len(dispute_events) == 3

        # Verify some events
        bridge.submit_attestation(event1.event_id, "0xv1", True, "ipfs://e1")
        bridge.submit_attestation(event2.event_id, "0xv1", True, "ipfs://e2")
        bridge.submit_attestation(event3.event_id, "0xv1", False, "ipfs://e3")

        # Check mixed results
        assert bridge.get_event(event1.event_id).status == EventStatus.VERIFIED
        assert bridge.get_event(event2.event_id).status == EventStatus.VERIFIED
        assert bridge.get_event(event3.event_id).status == EventStatus.REJECTED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
