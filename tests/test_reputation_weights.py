# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Reputation-Weighted Participation (Phase 6.10).

Tests reputation-based voting:
- Reputation score management
- Voting power calculation
- Good-faith behavior incentives
- Bad actor penalties
- Reputation-weighted governance
"""

import pytest
from datetime import datetime, timedelta

from rra.reputation.weighted import (
    ReputationAction,
    create_reputation_manager,
)
from rra.governance.rep_voting import (
    ProposalStatus,
    VoteChoice,
    create_rep_weighted_governance,
)


# =============================================================================
# ReputationManager Tests
# =============================================================================


class TestReputationManager:
    """Test reputation manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a reputation manager without persistence."""
        return create_reputation_manager()

    @pytest.fixture
    def persistent_manager(self, tmp_path):
        """Create a reputation manager with persistence."""
        return create_reputation_manager(data_dir=str(tmp_path))

    def test_create_manager(self, manager):
        """Test manager creation."""
        assert manager is not None
        assert manager.config.base_reputation == 1000

    def test_create_participant(self, manager):
        """Test participant creation."""
        participant = manager.get_or_create_participant("0x1111")

        assert participant is not None
        assert participant.score == 1000
        assert participant.total_disputes == 0

    def test_get_nonexistent_participant(self, manager):
        """Test getting nonexistent participant."""
        participant = manager.get_participant("0x9999")
        assert participant is None

    def test_update_reputation_positive(self, manager):
        """Test positive reputation update."""
        manager.get_or_create_participant("0x1111")

        participant = manager.update_reputation(
            "0x1111",
            ReputationAction.RESOLUTION_SUCCESS,
            dispute_id="dispute_123",
        )

        assert participant.score > 1000
        assert len(participant.history) == 1
        assert participant.history[0].action == ReputationAction.RESOLUTION_SUCCESS

    def test_update_reputation_negative(self, manager):
        """Test negative reputation update."""
        manager.get_or_create_participant("0x1111")

        participant = manager.update_reputation(
            "0x1111",
            ReputationAction.RESOLUTION_FAILURE,
        )

        assert participant.score < 1000

    def test_reputation_bounds(self, manager):
        """Test reputation bounds are enforced."""
        participant = manager.get_or_create_participant("0x1111")

        # Try to exceed max
        for _ in range(100):
            manager.update_reputation(
                "0x1111",
                ReputationAction.RESOLUTION_SUCCESS,
            )

        participant = manager.get_participant("0x1111")
        assert participant.score <= manager.config.max_reputation

        # Try to go below min
        for _ in range(200):
            manager.update_reputation(
                "0x1111",
                ReputationAction.MALICIOUS_BEHAVIOR,
            )

        participant = manager.get_participant("0x1111")
        assert participant.score >= manager.config.min_reputation

    def test_custom_delta(self, manager):
        """Test custom delta values."""
        manager.get_or_create_participant("0x1111")

        participant = manager.update_reputation(
            "0x1111",
            ReputationAction.GOOD_FAITH_BONUS,
            custom_delta=100,
        )

        assert participant.score == 1100

    def test_record_dispute_participation(self, manager):
        """Test dispute participation recording."""
        manager.record_dispute_participation("dispute_1", "0x1111")

        participant = manager.get_participant("0x1111")
        assert participant.total_disputes == 1

        # Recording again shouldn't increment
        manager.record_dispute_participation("dispute_1", "0x1111")
        participant = manager.get_participant("0x1111")
        assert participant.total_disputes == 1

    def test_record_dispute_resolution(self, manager):
        """Test dispute resolution recording."""
        manager.record_dispute_resolution(
            "dispute_1",
            winners=["0x1111", "0x2222"],
            losers=["0x3333"],
        )

        winner = manager.get_participant("0x1111")
        assert winner.successful_disputes == 1
        assert winner.score > 1000

        loser = manager.get_participant("0x3333")
        assert loser.score < 1000

    def test_early_voting_bonus(self, manager):
        """Test early voting reputation bonus."""
        manager.get_or_create_participant("0x1111")
        initial_score = manager.get_reputation_score("0x1111")

        manager.record_early_voting("0x1111", "dispute_1")

        new_score = manager.get_reputation_score("0x1111")
        assert new_score > initial_score

    def test_late_voting_penalty(self, manager):
        """Test late voting reputation penalty."""
        manager.get_or_create_participant("0x1111")
        initial_score = manager.get_reputation_score("0x1111")

        manager.record_late_voting("0x1111", "dispute_1")

        new_score = manager.get_reputation_score("0x1111")
        assert new_score < initial_score

    def test_malicious_behavior_penalty(self, manager):
        """Test malicious behavior detection."""
        manager.get_or_create_participant("0x1111")

        manager.record_malicious_behavior("0x1111", "dispute_1", "stake_manipulation")

        participant = manager.get_participant("0x1111")
        assert participant.score < 1000 - 50  # Significant penalty

    def test_reputation_decay(self, manager):
        """Test reputation decay for inactive participants."""
        # Create participant with old last activity
        participant = manager.get_or_create_participant("0x1111")
        participant.last_activity_at = datetime.now() - timedelta(days=60)

        decay_amount = manager.apply_decay("0x1111")

        assert decay_amount is not None
        assert decay_amount > 0
        assert manager.get_reputation_score("0x1111") < 1000

    def test_persistence(self, persistent_manager, tmp_path):
        """Test state persistence."""
        persistent_manager.get_or_create_participant("0x1111")
        persistent_manager.update_reputation(
            "0x1111",
            ReputationAction.RESOLUTION_SUCCESS,
        )

        # Create new manager with same data dir
        new_manager = create_reputation_manager(data_dir=str(tmp_path))

        participant = new_manager.get_participant("0x1111")
        assert participant is not None
        assert participant.score > 1000


# =============================================================================
# Voting Power Calculation Tests
# =============================================================================


class TestVotingPower:
    """Test voting power calculations."""

    @pytest.fixture
    def manager(self):
        return create_reputation_manager()

    def test_base_voting_power(self, manager):
        """Test base voting power calculation."""
        power = manager.calculate_voting_power("0x1111", stake=1000)

        assert power.base_stake == 1000
        # Base reputation (1000) maps to ~1.18 multiplier
        # Formula: min_multiplier + (normalized_score * multiplier_range)
        # where normalized_score = (1000-100)/(10000-100) ≈ 0.0909
        assert 1.0 < power.reputation_multiplier < 1.25
        assert power.tenure_bonus == 0.0  # New participant
        assert power.total_power > 1000  # Due to reputation multiplier

    def test_high_reputation_multiplier(self, manager):
        """Test high reputation gives multiplier."""
        # Boost reputation
        for _ in range(50):
            manager.update_reputation(
                "0x1111",
                ReputationAction.RESOLUTION_SUCCESS,
            )

        power = manager.calculate_voting_power("0x1111", stake=1000)

        assert power.reputation_multiplier > 1.0
        assert power.total_power > 1000

    def test_low_reputation_multiplier(self, manager):
        """Test low reputation gives minimal multiplier."""
        # Tank reputation
        for _ in range(20):
            manager.update_reputation(
                "0x1111",
                ReputationAction.MALICIOUS_BEHAVIOR,
            )

        power = manager.calculate_voting_power("0x1111", stake=1000)

        assert power.reputation_multiplier >= 1.0  # Min is 1.0
        assert power.total_power >= 1000

    def test_tenure_bonus(self, manager):
        """Test tenure provides bonus."""
        participant = manager.get_or_create_participant("0x1111")
        # Set old creation date
        participant.created_at = datetime.now() - timedelta(days=365)

        power = manager.calculate_voting_power("0x1111", stake=1000)

        assert power.tenure_bonus > 0
        assert power.total_power > 1000

    def test_batch_voting_power(self, manager):
        """Test batch voting power calculation."""
        participants = [
            ("0x1111", 1000),
            ("0x2222", 2000),
            ("0x3333", 500),
        ]

        powers = manager.calculate_batch_voting_power(participants)

        assert len(powers) == 3
        assert all(addr in powers for addr, _ in participants)

    def test_power_distribution(self, manager):
        """Test voting power distribution calculation."""
        participants = [
            ("0x1111", 1000),
            ("0x2222", 1000),
            ("0x3333", 1000),
        ]

        distribution = manager.get_power_distribution(participants)

        # Equal stakes and new participants = equal distribution
        assert abs(distribution["0x1111"] - 33.33) < 1
        assert abs(distribution["0x2222"] - 33.33) < 1
        assert abs(distribution["0x3333"] - 33.33) < 1


# =============================================================================
# Analytics Tests
# =============================================================================


class TestReputationAnalytics:
    """Test reputation analytics."""

    @pytest.fixture
    def manager_with_data(self):
        """Create manager with sample data."""
        manager = create_reputation_manager()

        # Create participants with varying reputations
        for i in range(10):
            addr = f"0x{i:04d}"
            manager.get_or_create_participant(addr)

            # Vary reputations
            for j in range(i * 2):
                manager.update_reputation(
                    addr,
                    ReputationAction.RESOLUTION_SUCCESS,
                )

        return manager

    def test_get_participant_stats(self, manager_with_data):
        """Test getting participant statistics."""
        stats = manager_with_data.get_participant_stats("0x0009")

        assert stats is not None
        assert "rank" in stats
        assert "percentile" in stats

    def test_get_leaderboard(self, manager_with_data):
        """Test getting leaderboard."""
        leaderboard = manager_with_data.get_leaderboard(limit=5)

        assert len(leaderboard) == 5
        assert leaderboard[0]["rank"] == 1
        # First should have highest score
        assert leaderboard[0]["score"] >= leaderboard[1]["score"]

    def test_get_stats(self, manager_with_data):
        """Test getting overall stats."""
        stats = manager_with_data.get_stats()

        assert stats["total_participants"] == 10
        assert "avg_score" in stats
        assert "median_score" in stats


# =============================================================================
# RepWeightedGovernance Tests
# =============================================================================


class TestRepWeightedGovernance:
    """Test reputation-weighted governance."""

    @pytest.fixture
    def governance(self):
        """Create governance without persistence."""
        return create_rep_weighted_governance()

    def test_create_governance(self, governance):
        """Test governance creation."""
        assert governance is not None
        assert governance.voting_period_hours == 72

    def test_register_stake(self, governance):
        """Test stake registration."""
        governance.register_stake("0x1111", 1000)

        assert governance.get_stake("0x1111") == 1000
        assert governance.total_staked == 1000

    def test_create_proposal(self, governance):
        """Test proposal creation."""
        governance.register_stake("0x1111", 1000)

        proposal = governance.create_proposal(
            title="Test Proposal",
            description="Description",
            proposer_address="0x1111",
        )

        assert proposal is not None
        assert proposal.proposal_id.startswith("rprop_")
        assert proposal.status == ProposalStatus.ACTIVE

    def test_vote_on_proposal(self, governance):
        """Test voting on proposal."""
        governance.register_stake("0x1111", 1000)
        governance.register_stake("0x2222", 500)

        proposal = governance.create_proposal(
            title="Test",
            description="Desc",
            proposer_address="0x1111",
            voting_delay_hours=0,  # Start immediately
        )

        vote = governance.vote(
            proposal.proposal_id,
            "0x2222",
            VoteChoice.FOR,
        )

        assert vote is not None
        assert vote.choice == VoteChoice.FOR
        assert vote.effective_power > 0

    def test_early_vote_bonus(self, governance):
        """Test early voting triggers reputation bonus."""
        governance.register_stake("0x1111", 1000)

        proposal = governance.create_proposal(
            title="Test",
            description="Desc",
            proposer_address="0x1111",
            voting_delay_hours=0,
        )

        initial_score = governance.reputation_manager.get_reputation_score("0x1111")

        # Vote early
        governance.vote(proposal.proposal_id, "0x1111", VoteChoice.FOR)

        new_score = governance.reputation_manager.get_reputation_score("0x1111")
        assert new_score >= initial_score  # Early vote bonus

    def test_finalize_passed_proposal(self, governance):
        """Test finalizing a passed proposal."""
        from datetime import datetime, timedelta

        governance.register_stake("0x1111", 1000)
        governance.register_stake("0x2222", 1000)

        proposal = governance.create_proposal(
            title="Test",
            description="Desc",
            proposer_address="0x1111",
            voting_delay_hours=0,
            # Note: 0 is falsy so we use a positive value and manually set voting_end
        )

        # Both vote for
        vote1 = governance.vote(proposal.proposal_id, "0x1111", VoteChoice.FOR)
        vote2 = governance.vote(proposal.proposal_id, "0x2222", VoteChoice.FOR)
        assert vote1 is not None, "Vote should be cast"
        assert vote2 is not None, "Vote should be cast"

        # Manually end voting period
        proposal = governance.get_proposal(proposal.proposal_id)
        proposal.voting_end = datetime.now() - timedelta(hours=1)

        result = governance.finalize_proposal(proposal.proposal_id)

        assert result is not None
        assert result["passed"] is True
        assert governance.get_proposal(proposal.proposal_id).status == ProposalStatus.PASSED

    def test_finalize_rejected_proposal(self, governance):
        """Test finalizing a rejected proposal."""
        from datetime import datetime, timedelta

        governance.register_stake("0x1111", 1000)
        governance.register_stake("0x2222", 1000)

        proposal = governance.create_proposal(
            title="Test",
            description="Desc",
            proposer_address="0x1111",
            voting_delay_hours=0,
        )

        # Both vote against
        vote1 = governance.vote(proposal.proposal_id, "0x1111", VoteChoice.AGAINST)
        vote2 = governance.vote(proposal.proposal_id, "0x2222", VoteChoice.AGAINST)
        assert vote1 is not None, "Vote should be cast"
        assert vote2 is not None, "Vote should be cast"

        # Manually end voting period
        proposal = governance.get_proposal(proposal.proposal_id)
        proposal.voting_end = datetime.now() - timedelta(hours=1)

        result = governance.finalize_proposal(proposal.proposal_id)

        assert result["passed"] is False
        assert governance.get_proposal(proposal.proposal_id).status == ProposalStatus.REJECTED

    def test_execute_proposal(self, governance):
        """Test executing a passed proposal."""
        from datetime import datetime, timedelta

        governance.register_stake("0x1111", 1000)

        proposal = governance.create_proposal(
            title="Test",
            description="Desc",
            proposer_address="0x1111",
            voting_delay_hours=0,
        )

        vote = governance.vote(proposal.proposal_id, "0x1111", VoteChoice.FOR)
        assert vote is not None, "Vote should be cast"

        # Manually end voting period
        proposal = governance.get_proposal(proposal.proposal_id)
        proposal.voting_end = datetime.now() - timedelta(hours=1)

        result = governance.finalize_proposal(proposal.proposal_id)
        assert result is not None
        assert result.get("passed") is True, f"Proposal should pass: {result}"

        result = governance.execute_proposal(proposal.proposal_id)

        assert result is not None
        assert governance.get_proposal(proposal.proposal_id).status == ProposalStatus.EXECUTED

    def test_dispute_proposals(self, governance):
        """Test proposals linked to disputes."""
        governance.register_stake("0x1111", 1000)

        proposal = governance.create_proposal(
            title="Dispute Resolution",
            description="Settle dispute",
            proposer_address="0x1111",
            dispute_id="dispute_123",
        )

        dispute_proposals = governance.get_dispute_proposals("dispute_123")
        assert len(dispute_proposals) == 1
        assert dispute_proposals[0].proposal_id == proposal.proposal_id


# =============================================================================
# Integration Tests
# =============================================================================


class TestReputationIntegration:
    """Integration tests for reputation system."""

    def test_full_reputation_lifecycle(self):
        """Test complete reputation lifecycle."""
        manager = create_reputation_manager()

        # 1. New participant joins
        participant = manager.get_or_create_participant("0x1111")
        assert participant.score == 1000

        # 2. Participates in dispute
        manager.record_dispute_participation("dispute_1", "0x1111")
        assert participant.total_disputes == 1

        # 3. Provides evidence (good faith)
        manager.record_evidence_provided("0x1111", "dispute_1")

        # 4. Votes early (good faith)
        manager.record_early_voting("0x1111", "dispute_1")

        # 5. Dispute resolves in their favor
        manager.record_dispute_resolution(
            "dispute_1",
            winners=["0x1111"],
            losers=["0x2222"],
        )

        # Check reputation improved
        participant = manager.get_participant("0x1111")
        assert participant.score > 1000
        assert participant.successful_disputes == 1

        # Check voting power increased
        power = manager.calculate_voting_power("0x1111", stake=1000)
        assert power.total_power > 1000

    def test_bad_actor_dampening(self):
        """Test bad actor reputation dampening."""
        manager = create_reputation_manager()

        # Start with good reputation
        for _ in range(10):
            manager.update_reputation(
                "0xbad",
                ReputationAction.RESOLUTION_SUCCESS,
            )

        initial_score = manager.get_reputation_score("0xbad")
        initial_power = manager.calculate_voting_power("0xbad", stake=1000).total_power

        # Bad behavior detected
        manager.record_malicious_behavior("0xbad", "dispute_1", "stake_manipulation")
        manager.record_malicious_behavior("0xbad", "dispute_2", "spamming")

        final_score = manager.get_reputation_score("0xbad")
        final_power = manager.calculate_voting_power("0xbad", stake=1000).total_power

        assert final_score < initial_score
        assert final_power < initial_power

    def test_governance_reputation_integration(self):
        """Test governance and reputation integration."""
        governance = create_rep_weighted_governance()

        # Setup participants with different reputations
        governance.register_stake("0xhigh", 1000)
        governance.register_stake("0xlow", 1000)

        # Boost high reputation
        for _ in range(20):
            governance.reputation_manager.update_reputation(
                "0xhigh",
                ReputationAction.RESOLUTION_SUCCESS,
            )

        # Tank low reputation
        for _ in range(5):
            governance.reputation_manager.update_reputation(
                "0xlow",
                ReputationAction.MALICIOUS_BEHAVIOR,
            )

        # Create proposal
        proposal = governance.create_proposal(
            title="Test",
            description="Desc",
            proposer_address="0xhigh",
            voting_delay_hours=0,
        )

        # Both vote with same stake
        vote_high = governance.vote(proposal.proposal_id, "0xhigh", VoteChoice.FOR)
        vote_low = governance.vote(proposal.proposal_id, "0xlow", VoteChoice.AGAINST)

        # High rep voter should have more power
        assert vote_high.effective_power > vote_low.effective_power


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
