# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Negotiation Pressure Module.

Tests counter-proposal caps, exponential delay costs, and deadline enforcement.
"""

import pytest
from datetime import datetime, timedelta

from rra.negotiation.pressure import (
    PressureConfig,
    NegotiationPressure,
    NegotiationState,
    NegotiationStatus,
    CounterProposal,
    PressureStatus,
    calculate_delay_cost,
)


class TestCalculateDelayCost:
    """Tests for the delay cost calculation function."""

    def test_zero_elapsed_days(self):
        """No cost for zero elapsed time."""
        cost = calculate_delay_cost(
            total_stake=1.0,
            elapsed_days=0,
            base_rate_bps=10,
            half_life_days=7
        )
        assert cost == 0.0

    def test_negative_elapsed_days(self):
        """No cost for negative elapsed time."""
        cost = calculate_delay_cost(
            total_stake=1.0,
            elapsed_days=-1,
            base_rate_bps=10,
            half_life_days=7
        )
        assert cost == 0.0

    def test_one_day_elapsed(self):
        """Cost after one day."""
        cost = calculate_delay_cost(
            total_stake=1.0,
            elapsed_days=1,
            base_rate_bps=10,
            half_life_days=7
        )
        # 0.001 * (2^(1/7) - 1) ≈ 0.0001
        assert cost > 0
        assert cost < 0.001

    def test_half_life_doubling(self):
        """Cost should approximately double after half_life_days."""
        cost_7 = calculate_delay_cost(
            total_stake=1.0,
            elapsed_days=7,
            base_rate_bps=10,
            half_life_days=7
        )
        cost_14 = calculate_delay_cost(
            total_stake=1.0,
            elapsed_days=14,
            base_rate_bps=10,
            half_life_days=7
        )

        # At 7 days: multiplier = 1 (base cost)
        # At 14 days: multiplier = 2^1 = 2 (doubles)
        # Ratio should be approximately 2 (true doubling)
        ratio = cost_14 / cost_7
        assert 1.5 < ratio < 2.5

    def test_stake_proportional(self):
        """Cost should be proportional to stake."""
        cost_1 = calculate_delay_cost(
            total_stake=1.0,
            elapsed_days=7,
            base_rate_bps=10,
            half_life_days=7
        )
        cost_2 = calculate_delay_cost(
            total_stake=2.0,
            elapsed_days=7,
            base_rate_bps=10,
            half_life_days=7
        )

        assert abs(cost_2 - 2 * cost_1) < 0.0001

    def test_exponential_growth(self):
        """Cost should grow exponentially."""
        costs = [
            calculate_delay_cost(1.0, days, 10, 7)
            for days in range(0, 28, 7)
        ]

        # Each week should roughly double
        for i in range(1, len(costs) - 1):
            if costs[i] > 0:
                ratio = costs[i + 1] / costs[i]
                assert 1.5 < ratio < 2.5


class TestPressureConfig:
    """Tests for PressureConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PressureConfig()
        assert config.max_counter_proposals == 5
        assert config.base_delay_rate_bps == 10
        assert config.half_life_days == 7
        assert config.counter_proposal_penalty_bps == 500
        assert config.expiration_penalty_bps == 2000
        assert config.min_stake_eth == 0.01
        assert config.max_duration_days == 90

    def test_custom_values(self):
        """Test custom configuration."""
        config = PressureConfig(
            max_counter_proposals=3,
            half_life_days=14,
            min_stake_eth=0.1
        )
        assert config.max_counter_proposals == 3
        assert config.half_life_days == 14
        assert config.min_stake_eth == 0.1

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = PressureConfig()
        data = config.to_dict()
        assert data["max_counter_proposals"] == 5
        assert "base_delay_rate_bps" in data

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {"max_counter_proposals": 10, "half_life_days": 3}
        config = PressureConfig.from_dict(data)
        assert config.max_counter_proposals == 10
        assert config.half_life_days == 3


class TestNegotiationPressure:
    """Tests for NegotiationPressure manager."""

    @pytest.fixture
    def pressure(self):
        """Create pressure manager with default config."""
        return NegotiationPressure()

    @pytest.fixture
    def custom_pressure(self):
        """Create pressure manager with custom config."""
        config = PressureConfig(
            max_counter_proposals=3,
            base_delay_rate_bps=100,
            half_life_days=3
        )
        return NegotiationPressure(config)

    def test_start_negotiation(self, pressure):
        """Test starting a new negotiation."""
        state = pressure.start_negotiation(
            negotiation_id="test_001",
            initiator_id="alice@example.com",
            responder_id="bob@example.com",
            initiator_stake=1.0,
            duration_days=30
        )

        assert state.negotiation_id == "test_001"
        assert state.status == NegotiationStatus.PENDING
        assert state.initiator_stake == 1.0
        assert state.responder_stake == 0.0
        assert state.initiator_proposals == 0
        assert state.responder_proposals == 0

    def test_start_negotiation_low_stake(self, pressure):
        """Test rejection of stake below minimum."""
        with pytest.raises(ValueError, match="Stake must be at least"):
            pressure.start_negotiation(
                negotiation_id="test_002",
                initiator_id="alice",
                responder_id="bob",
                initiator_stake=0.001,  # Below minimum
                duration_days=30
            )

    def test_start_negotiation_long_duration(self, pressure):
        """Test rejection of duration above maximum."""
        with pytest.raises(ValueError, match="Duration cannot exceed"):
            pressure.start_negotiation(
                negotiation_id="test_003",
                initiator_id="alice",
                responder_id="bob",
                initiator_stake=1.0,
                duration_days=100  # Above maximum
            )

    def test_join_negotiation(self, pressure):
        """Test responder joining negotiation."""
        pressure.start_negotiation(
            negotiation_id="test_004",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=30
        )

        state = pressure.join_negotiation("test_004", responder_stake=0.5)

        assert state.status == NegotiationStatus.ACTIVE
        assert state.responder_stake == 0.5

    def test_join_negotiation_not_found(self, pressure):
        """Test joining non-existent negotiation."""
        with pytest.raises(ValueError, match="Negotiation not found"):
            pressure.join_negotiation("nonexistent", responder_stake=1.0)

    def test_submit_counter_proposal(self, pressure):
        """Test submitting counter-proposals."""
        # Setup
        pressure.start_negotiation(
            negotiation_id="test_005",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=30
        )
        pressure.join_negotiation("test_005", responder_stake=1.0)

        # Submit proposal
        cp, penalty = pressure.submit_counter_proposal(
            negotiation_id="test_005",
            party="initiator",
            proposal_hash="0xabc123"
        )

        assert cp.party == "initiator"
        assert cp.proposal_number == 1
        assert penalty is None  # No penalty yet

        # Check state updated
        state = pressure.get_negotiation("test_005")
        assert state.initiator_proposals == 1

    def test_counter_proposal_cap_exceeded(self, custom_pressure):
        """Test penalty when exceeding counter-proposal cap."""
        # Setup with max 3 proposals
        custom_pressure.start_negotiation(
            negotiation_id="test_006",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=30
        )
        custom_pressure.join_negotiation("test_006", responder_stake=1.0)

        # Submit max proposals (no penalty)
        for i in range(3):
            cp, penalty = custom_pressure.submit_counter_proposal(
                "test_006", "initiator", f"0x{i}"
            )
            assert penalty is None

        # 4th proposal should incur penalty
        cp, penalty = custom_pressure.submit_counter_proposal(
            "test_006", "initiator", "0x999"
        )
        assert penalty is not None
        assert penalty > 0

        # Check stake reduced
        state = custom_pressure.get_negotiation("test_006")
        assert state.initiator_stake < 1.0

    def test_record_agreement(self, pressure):
        """Test recording agreement."""
        # Setup
        pressure.start_negotiation(
            negotiation_id="test_007",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=30
        )
        pressure.join_negotiation("test_007", responder_stake=1.0)

        # Record agreement
        init_refund, resp_refund, delay_cost = pressure.record_agreement(
            "test_007", "0xfinal_agreement"
        )

        assert init_refund >= 0
        assert resp_refund >= 0
        assert delay_cost >= 0

        state = pressure.get_negotiation("test_007")
        assert state.status == NegotiationStatus.AGREED
        assert state.agreement_hash == "0xfinal_agreement"

    def test_process_expiration(self, pressure):
        """Test processing expired negotiation."""
        # Setup with mocked time
        pressure.start_negotiation(
            negotiation_id="test_008",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=1  # 1 day duration
        )
        pressure.join_negotiation("test_008", responder_stake=1.0)

        # Fast forward past deadline
        state = pressure.get_negotiation("test_008")
        state.deadline = datetime.utcnow() - timedelta(hours=1)

        init_penalty, resp_penalty = pressure.process_expiration("test_008")

        assert init_penalty > 0
        assert resp_penalty > 0

        state = pressure.get_negotiation("test_008")
        assert state.status == NegotiationStatus.EXPIRED

    def test_get_pressure_status(self, pressure):
        """Test getting pressure status."""
        pressure.start_negotiation(
            negotiation_id="test_009",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=30
        )
        pressure.join_negotiation("test_009", responder_stake=1.0)

        status = pressure.get_pressure_status("test_009")

        assert status.negotiation_id == "test_009"
        assert status.status == NegotiationStatus.ACTIVE
        assert status.remaining_proposals_initiator == 5
        assert status.remaining_proposals_responder == 5
        assert status.time_remaining.total_seconds() > 0
        assert status.urgency_level in ("low", "medium", "high", "critical")

    def test_get_pressure_status_urgency(self, pressure):
        """Test urgency level calculation."""
        pressure.start_negotiation(
            negotiation_id="test_010",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=30
        )
        pressure.join_negotiation("test_010", responder_stake=1.0)

        # Initially should be low urgency
        status = pressure.get_pressure_status("test_010")
        assert status.urgency_level == "low"

        # Modify deadline to be soon
        state = pressure.get_negotiation("test_010")
        state.deadline = datetime.utcnow() + timedelta(hours=12)

        status = pressure.get_pressure_status("test_010")
        assert status.urgency_level == "critical"

    def test_get_all_active(self, pressure):
        """Test getting all active negotiations."""
        # Create multiple negotiations
        for i in range(3):
            pressure.start_negotiation(
                negotiation_id=f"test_{100 + i}",
                initiator_id=f"alice_{i}",
                responder_id=f"bob_{i}",
                initiator_stake=1.0,
                duration_days=30
            )

        active = pressure.get_all_active()
        assert len(active) == 3

    def test_get_statistics(self, pressure):
        """Test getting aggregate statistics."""
        # Create and process negotiations
        pressure.start_negotiation(
            negotiation_id="test_200",
            initiator_id="alice",
            responder_id="bob",
            initiator_stake=1.0,
            duration_days=30
        )
        pressure.join_negotiation("test_200", responder_stake=1.0)
        pressure.record_agreement("test_200", "0xagreement")

        stats = pressure.get_statistics()
        assert stats["total_negotiations"] == 1
        assert stats["agreed"] == 1
        assert stats["agreement_rate"] == 1.0


class TestNegotiationState:
    """Tests for NegotiationState."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = NegotiationState(
            negotiation_id="test_state",
            initiator_hash="abc123",
            responder_hash="def456",
            initiator_stake=1.0,
            responder_stake=0.5,
            start_time=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=30),
            status=NegotiationStatus.ACTIVE,
            config=PressureConfig(),
        )

        data = state.to_dict()
        assert data["negotiation_id"] == "test_state"
        assert data["initiator_stake"] == 1.0
        assert data["status"] == "active"


class TestCounterProposal:
    """Tests for CounterProposal."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        cp = CounterProposal(
            proposal_hash="0xtest",
            party="initiator",
            timestamp=datetime.utcnow(),
            delay_cost_at_time=0.01,
            proposal_number=1,
            penalty_applied=0.0
        )

        data = cp.to_dict()
        assert data["proposal_hash"] == "0xtest"
        assert data["party"] == "initiator"
        assert data["proposal_number"] == 1


class TestPressureStatus:
    """Tests for PressureStatus."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        status = PressureStatus(
            negotiation_id="test",
            status=NegotiationStatus.ACTIVE,
            current_delay_cost=0.001,
            projected_delay_cost_24h=0.002,
            remaining_proposals_initiator=5,
            remaining_proposals_responder=4,
            time_remaining=timedelta(days=10),
            stake_at_risk_initiator=0.0005,
            stake_at_risk_responder=0.0005,
            urgency_level="low"
        )

        data = status.to_dict()
        assert data["negotiation_id"] == "test"
        assert data["status"] == "active"
        assert data["urgency_level"] == "low"
        assert "time_remaining_human" in data


class TestIntegration:
    """Integration tests for full negotiation flows."""

    def test_full_negotiation_flow(self):
        """Test complete negotiation from start to agreement."""
        pressure = NegotiationPressure()

        # Start
        state = pressure.start_negotiation(
            negotiation_id="integration_001",
            initiator_id="seller@example.com",
            responder_id="buyer@example.com",
            initiator_stake=0.5,
            duration_days=14
        )
        assert state.status == NegotiationStatus.PENDING

        # Join
        state = pressure.join_negotiation("integration_001", responder_stake=0.5)
        assert state.status == NegotiationStatus.ACTIVE

        # Exchange proposals
        for i in range(3):
            pressure.submit_counter_proposal(
                "integration_001", "initiator", f"proposal_{i}_init"
            )
            pressure.submit_counter_proposal(
                "integration_001", "responder", f"proposal_{i}_resp"
            )

        # Check status
        status = pressure.get_pressure_status("integration_001")
        assert status.remaining_proposals_initiator == 2
        assert status.remaining_proposals_responder == 2

        # Agree
        init_refund, resp_refund, delay = pressure.record_agreement(
            "integration_001", "0xfinal"
        )

        state = pressure.get_negotiation("integration_001")
        assert state.status == NegotiationStatus.AGREED
        assert len(state.counter_proposals) == 6  # 3 each

    def test_negotiation_with_penalty(self):
        """Test negotiation where cap is exceeded."""
        config = PressureConfig(max_counter_proposals=2)
        pressure = NegotiationPressure(config)

        pressure.start_negotiation(
            negotiation_id="penalty_test",
            initiator_id="seller",
            responder_id="buyer",
            initiator_stake=1.0,
            duration_days=7
        )
        pressure.join_negotiation("penalty_test", responder_stake=1.0)

        initial_stake = 1.0
        penalties = []

        # Submit 4 proposals (2 over cap)
        for i in range(4):
            _, penalty = pressure.submit_counter_proposal(
                "penalty_test", "initiator", f"p{i}"
            )
            if penalty:
                penalties.append(penalty)

        # Should have 2 penalties
        assert len(penalties) == 2

        state = pressure.get_negotiation("penalty_test")
        assert state.initiator_stake < initial_stake
