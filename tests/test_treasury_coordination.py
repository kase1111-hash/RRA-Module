# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Treasury Coordination (Phase 6.8).

Tests multi-treasury dispute resolution:
- Treasury registration and management
- Multi-treasury dispute creation
- Stake-weighted voting
- Proposal lifecycle
- Fund distribution
- Mediation escalation
"""

import pytest
from datetime import datetime, timedelta

from rra.treasury.coordinator import (
    TreasuryType,
    DisputeStatus,
    ProposalType,
    VoteChoice,
    create_treasury_coordinator,
)
from rra.governance.treasury_votes import (
    TreasuryVoteType,
    TreasuryVoteStatus,
    VoteChoice as VotingChoice,
    create_treasury_voting_manager,
)


# =============================================================================
# TreasuryCoordinator Tests
# =============================================================================


class TestTreasuryCoordinator:
    """Test treasury coordinator functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create a coordinator without persistence."""
        return create_treasury_coordinator()

    @pytest.fixture
    def persistent_coordinator(self, tmp_path):
        """Create a coordinator with persistence."""
        # Note: TreasuryCoordinator doesn't support persistence yet
        return create_treasury_coordinator()

    def test_create_coordinator(self, coordinator):
        """Test coordinator creation."""
        assert coordinator is not None
        assert coordinator.config is not None

    def test_register_treasury(self, coordinator):
        """Test treasury registration."""
        treasury = coordinator.register_treasury(
            name="Test Corp Treasury",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )

        assert treasury is not None
        assert len(treasury.treasury_id) == 24  # SHA256 truncated to 24 chars
        assert treasury.name == "Test Corp Treasury"
        assert treasury.treasury_type == TreasuryType.CORPORATE
        assert len(treasury.signers) == 1

    def test_register_treasury_multiple_signers(self, coordinator):
        """Test treasury with multi-sig."""
        treasury = coordinator.register_treasury(
            name="Multi-Sig Treasury",
            treasury_type=TreasuryType.DAO,
            signers=[
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                "0x3333333333333333333333333333333333333333",
            ],
            signer_threshold=2,
        )

        assert len(treasury.signers) == 3
        assert treasury.signer_threshold == 2

    def test_get_treasury(self, coordinator):
        """Test getting treasury by ID."""
        treasury = coordinator.register_treasury(
            name="Test Treasury",
            treasury_type=TreasuryType.INDIVIDUAL,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )

        found = coordinator.get_treasury(treasury.treasury_id)
        assert found is not None
        assert found.treasury_id == treasury.treasury_id

        not_found = coordinator.get_treasury("trs_nonexistent")
        assert not_found is None

    def test_create_dispute(self, coordinator):
        """Test multi-treasury dispute creation."""
        # Register treasuries
        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        # Create dispute
        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Licensing Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        assert dispute is not None
        assert len(dispute.dispute_id) == 24  # SHA256 truncated to 24 chars
        assert dispute.creator_treasury == treasury1.treasury_id
        assert treasury2.treasury_id in dispute.involved_treasuries
        assert dispute.status == DisputeStatus.CREATED

    def test_create_binding_dispute(self, coordinator):
        """Test creating binding vs advisory dispute."""
        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        # Advisory dispute (default)
        dispute1 = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Advisory Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )
        assert dispute1.is_binding is False

        # Binding dispute
        dispute2 = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Binding Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
            is_binding=True,
        )
        assert dispute2.is_binding is True

    def test_stake_for_dispute(self, coordinator):
        """Test staking funds for a dispute."""
        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Test Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Stake from both treasuries (MIN_STAKE is 10**16)
        success1 = coordinator.stake(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            stake_amount=2 * 10**16,  # 0.02 ETH
            staker_address="0x1111111111111111111111111111111111111111",
        )
        assert success1 is True

        success2 = coordinator.stake(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury2.treasury_id,
            stake_amount=10**16,  # 0.01 ETH (MIN_STAKE)
            staker_address="0x2222222222222222222222222222222222222222",
        )
        assert success2 is True

        # Check dispute stakes
        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert dispute.total_stake == 3 * 10**16
        assert dispute.participants[treasury1.treasury_id].stake_amount == 2 * 10**16
        assert dispute.participants[treasury2.treasury_id].stake_amount == 10**16

    def test_create_proposal(self, coordinator):
        """Test creating a resolution proposal."""
        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Test Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Stake from BOTH treasuries to enter VOTING state (MIN_STAKE is 10**16)
        coordinator.stake(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            stake_amount=10**16,
            staker_address="0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury2.treasury_id,
            stake_amount=10**16,
            staker_address="0x2222222222222222222222222222222222222222",
        )

        # Create proposal
        proposal = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="50/50 Split",
            description="Split funds equally",
            ipfs_uri="ipfs://Qm...",
            payout_shares=[5000, 5000],  # Basis points, must sum to 10000
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        assert proposal is not None
        assert isinstance(proposal.proposal_id, int)
        assert not proposal.executed

    def test_vote_on_proposal(self, coordinator):
        """Test voting on a proposal."""
        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Test Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Stake from both (MIN_STAKE is 10**16)
        coordinator.stake(
            dispute.dispute_id,
            treasury1.treasury_id,
            2 * 10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            treasury2.treasury_id,
            10**16,
            "0x2222222222222222222222222222222222222222",
        )

        # Create proposal
        proposal = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Resolution",
            description="Settlement",
            ipfs_uri="ipfs://Qm...",
            payout_shares=[6000, 4000],  # Basis points
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        # Vote
        success = coordinator.vote(
            dispute_id=dispute.dispute_id,
            proposal_id=proposal.proposal_id,
            treasury_id=treasury1.treasury_id,
            choice=VoteChoice.SUPPORT,
            voter_address="0x1111111111111111111111111111111111111111",
        )
        assert success is True

        # Check vote recorded
        dispute = coordinator.get_dispute(dispute.dispute_id)
        prop = dispute.proposals[proposal.proposal_id]
        assert prop.support_weight == 2 * 10**16

    def test_execute_resolution(self, coordinator):
        """Test executing a passed resolution."""
        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Test Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Stake from both (MIN_STAKE is 10**16)
        coordinator.stake(
            dispute.dispute_id,
            treasury1.treasury_id,
            2 * 10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            treasury2.treasury_id,
            10**16,
            "0x2222222222222222222222222222222222222222",
        )

        # Create and pass proposal
        proposal = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Resolution",
            description="Settlement",
            ipfs_uri="ipfs://Qm...",
            payout_shares=[6000, 4000],  # Basis points
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        # Both vote support (majority stake)
        coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            treasury1.treasury_id,
            VoteChoice.SUPPORT,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            treasury2.treasury_id,
            VoteChoice.SUPPORT,
            "0x2222222222222222222222222222222222222222",
        )

        # Execute resolution
        payout = coordinator.execute_resolution(dispute.dispute_id)

        assert payout is not None
        assert treasury1.treasury_id in payout
        assert treasury2.treasury_id in payout

        # Check dispute status (EXECUTED after execute_resolution)
        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert dispute.status == DisputeStatus.EXECUTED

    def test_request_mediation(self, coordinator):
        """Test requesting mediation."""
        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Test Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Stake to move to voting
        coordinator.stake(
            dispute.dispute_id,
            treasury1.treasury_id,
            10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            treasury2.treasury_id,
            10**16,
            "0x2222222222222222222222222222222222222222",
        )

        # Request mediation (only works in VOTING or EXPIRED state)
        success = coordinator.request_mediation(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            requester_address="0x1111111111111111111111111111111111111111",
        )

        assert success is True

        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert dispute.status == DisputeStatus.MEDIATION

    def test_treasury_registration_stores_data(self, coordinator):
        """Test that treasury registration stores data correctly."""
        # Register treasury
        treasury = coordinator.register_treasury(
            name="Test Treasury",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )

        # Check treasury can be retrieved
        found = coordinator.get_treasury(treasury.treasury_id)
        assert found is not None
        assert found.name == "Test Treasury"
        assert found.treasury_type == TreasuryType.CORPORATE


# =============================================================================
# TreasuryVotingManager Tests
# =============================================================================


class TestTreasuryVotingManager:
    """Test treasury voting manager functionality."""

    @pytest.fixture
    def voting_manager(self):
        """Create a voting manager without persistence."""
        return create_treasury_voting_manager()

    def test_create_manager(self, voting_manager):
        """Test manager creation."""
        assert voting_manager is not None
        assert voting_manager.voting_period_hours == 72

    def test_register_treasury(self, voting_manager):
        """Test treasury registration."""
        treasury = voting_manager.register_treasury(
            name="Test Treasury",
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )

        assert treasury is not None
        assert treasury.treasury_id.startswith("trs_")

    def test_stake_for_dispute(self, voting_manager):
        """Test staking for dispute."""
        treasury = voting_manager.register_treasury(
            name="Test Treasury",
            signers=["0x1111111111111111111111111111111111111111"],
        )

        stake = voting_manager.stake_for_dispute(
            dispute_id="dispute_123",
            treasury_id=treasury.treasury_id,
            amount=1000,
        )

        assert stake == 1000
        assert voting_manager.get_total_stake("dispute_123") == 1000

    def test_create_proposal(self, voting_manager):
        """Test creating a voting proposal."""
        treasury = voting_manager.register_treasury(
            name="Test Treasury",
            signers=["0x1111111111111111111111111111111111111111"],
        )

        # Stake first
        voting_manager.stake_for_dispute("dispute_123", treasury.treasury_id, 1000)

        proposal = voting_manager.create_proposal(
            dispute_id="dispute_123",
            treasury_id=treasury.treasury_id,
            proposer_address="0x1111111111111111111111111111111111111111",
            vote_type=TreasuryVoteType.RESOLUTION,
            title="Resolution Proposal",
            description="Proposed settlement",
        )

        assert proposal is not None
        assert proposal.proposal_id.startswith("tprop_")
        assert proposal.status == TreasuryVoteStatus.ACTIVE

    def test_vote_on_proposal(self, voting_manager):
        """Test voting on a proposal."""
        treasury1 = voting_manager.register_treasury(
            name="Treasury 1",
            signers=["0x1111111111111111111111111111111111111111"],
        )
        treasury2 = voting_manager.register_treasury(
            name="Treasury 2",
            signers=["0x2222222222222222222222222222222222222222"],
        )

        # Stake
        voting_manager.stake_for_dispute("dispute_123", treasury1.treasury_id, 1000)
        voting_manager.stake_for_dispute("dispute_123", treasury2.treasury_id, 500)

        # Create proposal
        proposal = voting_manager.create_proposal(
            dispute_id="dispute_123",
            treasury_id=treasury1.treasury_id,
            proposer_address="0x1111111111111111111111111111111111111111",
            vote_type=TreasuryVoteType.RESOLUTION,
            title="Resolution",
            description="Settlement",
        )

        # Vote
        vote = voting_manager.vote(
            proposal_id=proposal.proposal_id,
            treasury_id=treasury1.treasury_id,
            voter_address="0x1111111111111111111111111111111111111111",
            choice=VotingChoice.APPROVE,
        )

        assert vote is not None
        assert vote.stake_weight == 1000

        # Check proposal updated
        proposal = voting_manager.get_proposal(proposal.proposal_id)
        assert proposal.stake_approved == 1000

    def test_finalize_proposal(self, voting_manager):
        """Test finalizing a proposal."""

        treasury = voting_manager.register_treasury(
            name="Treasury",
            signers=["0x1111111111111111111111111111111111111111"],
        )

        voting_manager.stake_for_dispute("dispute_123", treasury.treasury_id, 1000)

        # Use normal voting period for now (so voting works)
        proposal = voting_manager.create_proposal(
            dispute_id="dispute_123",
            treasury_id=treasury.treasury_id,
            proposer_address="0x1111111111111111111111111111111111111111",
            vote_type=TreasuryVoteType.RESOLUTION,
            title="Resolution",
            description="Settlement",
        )

        # Vote during the voting period
        vote = voting_manager.vote(
            proposal_id=proposal.proposal_id,
            treasury_id=treasury.treasury_id,
            voter_address="0x1111111111111111111111111111111111111111",
            choice=VotingChoice.APPROVE,
        )
        assert vote is not None, "Vote should be recorded"

        # Manually end the voting period by setting voting_end to the past
        proposal = voting_manager.get_proposal(proposal.proposal_id)
        proposal.voting_end = datetime.now() - timedelta(hours=1)

        # Finalize
        result = voting_manager.finalize_proposal(proposal.proposal_id)

        assert result is not None
        assert result.get("passed") is True

    def test_signer_consensus(self, voting_manager):
        """Test multi-sig signer consensus."""
        treasury = voting_manager.register_treasury(
            name="Multi-Sig Treasury",
            signers=[
                "0x1111111111111111111111111111111111111111",
                "0x2222222222222222222222222222222222222222",
                "0x3333333333333333333333333333333333333333",
            ],
            signer_threshold=2,
        )

        voting_manager.stake_for_dispute("dispute_123", treasury.treasury_id, 1000)

        proposal = voting_manager.create_proposal(
            dispute_id="dispute_123",
            treasury_id=treasury.treasury_id,
            proposer_address="0x1111111111111111111111111111111111111111",
            vote_type=TreasuryVoteType.RESOLUTION,
            title="Resolution",
            description="Settlement",
        )

        # First signer vote
        voting_manager.vote_as_signer(
            proposal_id=proposal.proposal_id,
            treasury_id=treasury.treasury_id,
            signer_address="0x1111111111111111111111111111111111111111",
            choice=VotingChoice.APPROVE,
        )

        # Check consensus not reached yet
        reached, details = voting_manager.check_signer_consensus(
            proposal.proposal_id, treasury.treasury_id
        )
        assert reached is False

        # Second signer vote
        voting_manager.vote_as_signer(
            proposal_id=proposal.proposal_id,
            treasury_id=treasury.treasury_id,
            signer_address="0x2222222222222222222222222222222222222222",
            choice=VotingChoice.APPROVE,
        )

        # Check consensus reached
        reached, details = voting_manager.check_signer_consensus(
            proposal.proposal_id, treasury.treasury_id
        )
        assert reached is True
        assert details["approve_weight"] >= 2

    def test_voting_stats(self, voting_manager):
        """Test voting statistics."""
        treasury1 = voting_manager.register_treasury(
            name="Treasury 1",
            signers=["0x1111111111111111111111111111111111111111"],
        )
        treasury2 = voting_manager.register_treasury(
            name="Treasury 2",
            signers=["0x2222222222222222222222222222222222222222"],
        )

        voting_manager.stake_for_dispute("dispute_123", treasury1.treasury_id, 1000)
        voting_manager.stake_for_dispute("dispute_123", treasury2.treasury_id, 500)

        voting_manager.create_proposal(
            dispute_id="dispute_123",
            treasury_id=treasury1.treasury_id,
            proposer_address="0x1111111111111111111111111111111111111111",
            vote_type=TreasuryVoteType.RESOLUTION,
            title="Resolution",
            description="Settlement",
        )

        stats = voting_manager.get_voting_stats("dispute_123")

        assert stats["total_stake"] == 1500
        assert stats["treasury_count"] == 2
        assert stats["proposal_count"] == 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestTreasuryIntegration:
    """Integration tests for treasury coordination."""

    def test_full_dispute_lifecycle(self):
        """Test complete dispute lifecycle from creation to resolution."""
        coordinator = create_treasury_coordinator()

        # 1. Register treasuries
        corp_treasury = coordinator.register_treasury(
            name="Corporate Treasury",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )

        dao_treasury = coordinator.register_treasury(
            name="DAO Treasury",
            treasury_type=TreasuryType.DAO,
            signers=[
                "0x2222222222222222222222222222222222222222",
                "0x3333333333333333333333333333333333333333",
            ],
            signer_threshold=2,
        )

        # 2. Create dispute
        dispute = coordinator.create_dispute(
            creator_treasury=corp_treasury.treasury_id,
            involved_treasuries=[dao_treasury.treasury_id],
            title="Licensing Fee Dispute",
            description_uri="ipfs://QmXyz...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        assert dispute.status == DisputeStatus.CREATED

        # 3. Stake funds
        coordinator.stake(
            dispute.dispute_id,
            corp_treasury.treasury_id,
            2 * 10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            dao_treasury.treasury_id,
            10**16,
            "0x2222222222222222222222222222222222222222",
        )

        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert dispute.total_stake == 3 * 10**16

        # 4. Create proposal
        proposal = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=corp_treasury.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Settlement: 70/30 Split",
            description="Corporate gets 70%, DAO gets 30%",
            ipfs_uri="ipfs://QmXyz...",
            payout_shares=[7000, 3000],  # Basis points
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        # 5. Vote
        coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            corp_treasury.treasury_id,
            VoteChoice.SUPPORT,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            dao_treasury.treasury_id,
            VoteChoice.SUPPORT,
            "0x2222222222222222222222222222222222222222",
        )

        # 6. Execute resolution
        payout = coordinator.execute_resolution(dispute.dispute_id)

        assert payout is not None
        # Payout shares are based on escrow which is 0 in this test
        # Just verify the keys are present
        assert corp_treasury.treasury_id in payout
        assert dao_treasury.treasury_id in payout

        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert dispute.status == DisputeStatus.EXECUTED

    def test_disputed_resolution_with_mediation(self):
        """Test dispute that escalates to mediation."""
        coordinator = create_treasury_coordinator()

        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Contentious Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Stake (MIN_STAKE is 10**16)
        coordinator.stake(
            dispute.dispute_id,
            treasury1.treasury_id,
            10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            treasury2.treasury_id,
            10**16,
            "0x2222222222222222222222222222222222222222",
        )

        # Create proposal
        proposal = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Resolution",
            description="Settlement",
            ipfs_uri="ipfs://Qm...",
            payout_shares=[5000, 5000],  # Basis points
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        # Treasury 1 supports, Treasury 2 opposes (deadlock)
        coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            treasury1.treasury_id,
            VoteChoice.SUPPORT,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            treasury2.treasury_id,
            VoteChoice.OPPOSE,
            "0x2222222222222222222222222222222222222222",
        )

        # Request mediation
        coordinator.request_mediation(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            requester_address="0x1111111111111111111111111111111111111111",
        )

        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert dispute.status == DisputeStatus.MEDIATION

    def test_multiple_proposals_competition(self):
        """Test multiple competing proposals."""
        coordinator = create_treasury_coordinator()

        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Multi-Proposal Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        coordinator.stake(
            dispute.dispute_id,
            treasury1.treasury_id,
            10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            treasury2.treasury_id,
            15 * 10**15,  # 1.5x min stake
            "0x2222222222222222222222222222222222222222",
        )

        # Proposal from Treasury 1
        coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Treasury 1 Proposal: 60/40",
            description="Treasury 1 gets 60%",
            ipfs_uri="ipfs://Qm1...",
            payout_shares=[6000, 4000],  # Basis points
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        # Proposal from Treasury 2
        proposal2 = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury2.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Treasury 2 Proposal: 40/60",
            description="Treasury 2 gets 60%",
            ipfs_uri="ipfs://Qm2...",
            payout_shares=[4000, 6000],  # Basis points
            proposer_address="0x2222222222222222222222222222222222222222",
        )

        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert len(dispute.proposals) == 2

        # Treasury 2 has more stake, votes for own proposal
        coordinator.vote(
            dispute.dispute_id,
            proposal2.proposal_id,
            treasury2.treasury_id,
            VoteChoice.SUPPORT,
            "0x2222222222222222222222222222222222222222",
        )

        # Check proposal 2 has more support
        dispute = coordinator.get_dispute(dispute.dispute_id)
        assert dispute.proposals[proposal2.proposal_id].support_weight == 15 * 10**15


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestTreasuryEdgeCases:
    """Test edge cases and error handling."""

    def test_vote_without_stake(self):
        """Test that voting without stake fails."""
        coordinator = create_treasury_coordinator()

        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )
        treasury3 = coordinator.register_treasury(
            name="Treasury 3",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x3333333333333333333333333333333333333333"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id, treasury3.treasury_id],
            title="Test Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Only treasury1 and treasury2 stake - treasury3 does not stake
        coordinator.stake(
            dispute.dispute_id,
            treasury1.treasury_id,
            10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            treasury2.treasury_id,
            10**16,
            "0x2222222222222222222222222222222222222222",
        )
        # Note: treasury3 doesn't stake, so all_staked is False, voting won't start

        # Check that proposal creation fails because not all have staked
        proposal = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Resolution",
            description="Settlement",
            ipfs_uri="ipfs://Qm...",
            payout_shares=[3333, 3333, 3334],  # Basis points
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        # Proposal should be None because not in VOTING state
        assert proposal is None

    def test_unauthorized_signer(self):
        """Test that unauthorized signers cannot act."""
        coordinator = create_treasury_coordinator()

        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        # Try to create dispute with unauthorized address - should raise
        try:
            coordinator.create_dispute(
                creator_treasury=treasury1.treasury_id,
                involved_treasuries=[treasury2.treasury_id],
                title="Test Dispute",
                description_uri="ipfs://Qm...",
                creator_address="0x9999999999999999999999999999999999999999",  # Not a signer
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid creator or not authorized" in str(e)

    def test_double_vote(self):
        """Test that double voting is handled."""
        coordinator = create_treasury_coordinator()

        treasury1 = coordinator.register_treasury(
            name="Treasury 1",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x1111111111111111111111111111111111111111"],
            signer_threshold=1,
        )
        treasury2 = coordinator.register_treasury(
            name="Treasury 2",
            treasury_type=TreasuryType.CORPORATE,
            signers=["0x2222222222222222222222222222222222222222"],
            signer_threshold=1,
        )

        dispute = coordinator.create_dispute(
            creator_treasury=treasury1.treasury_id,
            involved_treasuries=[treasury2.treasury_id],
            title="Test Dispute",
            description_uri="ipfs://Qm...",
            creator_address="0x1111111111111111111111111111111111111111",
        )

        # Both treasuries stake to enter VOTING state
        coordinator.stake(
            dispute.dispute_id,
            treasury1.treasury_id,
            10**16,
            "0x1111111111111111111111111111111111111111",
        )
        coordinator.stake(
            dispute.dispute_id,
            treasury2.treasury_id,
            10**16,
            "0x2222222222222222222222222222222222222222",
        )

        proposal = coordinator.create_proposal(
            dispute_id=dispute.dispute_id,
            treasury_id=treasury1.treasury_id,
            proposal_type=ProposalType.FUND_DISTRIBUTION,
            title="Resolution",
            description="Settlement",
            ipfs_uri="ipfs://Qm...",
            payout_shares=[5000, 5000],  # Two treasuries, 50% each
            proposer_address="0x1111111111111111111111111111111111111111",
        )

        # First vote from treasury1
        coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            treasury1.treasury_id,
            VoteChoice.SUPPORT,
            "0x1111111111111111111111111111111111111111",
        )

        # Second vote from same treasury (should be rejected since already voted)
        second_vote_result = coordinator.vote(
            dispute.dispute_id,
            proposal.proposal_id,
            treasury1.treasury_id,
            VoteChoice.OPPOSE,
            "0x1111111111111111111111111111111111111111",
        )

        dispute = coordinator.get_dispute(dispute.dispute_id)
        prop = dispute.proposals[proposal.proposal_id]

        # Only first vote should count (second rejected)
        assert second_vote_result is False
        # Treasury1's stake was 10**16, should only count once
        assert prop.support_weight == 10**16
        assert prop.oppose_weight == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
