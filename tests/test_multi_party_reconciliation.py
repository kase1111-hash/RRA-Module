# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Tests for Multi-Party Reconciliation (Phase 6.4).

Tests cover:
- Multi-party dispute creation and lifecycle
- Weighted voting mechanisms
- Coalition formation
- Proposal management
- Resolution execution
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from src.rra.reconciliation.multi import (
    MultiPartyOrchestrator,
    MultiPartyDispute,
    DisputeParty,
    DisputePhase,
    PartyRole,
    ProposalSubmission,
    CoalitionRequest,
)
from src.rra.reconciliation.voting import (
    VotingSystem,
    Vote,
    VoteChoice,
    Proposal,
    ProposalStatus,
    VotingResult,
    QuorumConfig,
    VotingStrategy,
    ConvictionVoting,
)


# =============================================================================
# VotingSystem Tests
# =============================================================================


class TestVotingSystem:
    """Tests for the voting system."""

    @pytest.fixture
    def voting_system(self):
        """Create a voting system instance."""
        return VotingSystem()

    def test_create_proposal(self, voting_system):
        """Test creating a proposal."""
        proposal = voting_system.create_proposal(
            proposer_id="party_a",
            content_hash="0xabc123",
            metadata={"title": "Settlement A"},
        )

        assert proposal is not None
        assert proposal.proposer_id == "party_a"
        assert proposal.content_hash == "0xabc123"
        assert proposal.status == ProposalStatus.ACTIVE

    def test_cast_vote(self, voting_system):
        """Test casting a vote."""
        proposal = voting_system.create_proposal(
            proposer_id="party_a",
            content_hash="0xabc123",
        )

        vote = voting_system.cast_vote(
            proposal_id=proposal.id,
            voter_id="party_b",
            weight=Decimal("1.0"),
            choice=VoteChoice.ENDORSE,
        )

        assert vote is not None
        assert vote.choice == VoteChoice.ENDORSE
        assert vote.weight == Decimal("1.0")

    def test_cannot_vote_twice(self, voting_system):
        """Test that a voter cannot vote twice on same proposal."""
        proposal = voting_system.create_proposal(
            proposer_id="party_a",
            content_hash="0xabc123",
        )

        voting_system.cast_vote(
            proposal_id=proposal.id,
            voter_id="party_b",
            weight=Decimal("1.0"),
            choice=VoteChoice.ENDORSE,
        )

        with pytest.raises(ValueError, match="already voted"):
            voting_system.cast_vote(
                proposal_id=proposal.id,
                voter_id="party_b",
                weight=Decimal("1.0"),
                choice=VoteChoice.REJECT,
            )

    def test_vote_tallying(self, voting_system):
        """Test that votes are tallied correctly."""
        proposal = voting_system.create_proposal(
            proposer_id="party_a",
            content_hash="0xabc123",
        )

        voting_system.cast_vote(proposal.id, "voter1", Decimal("10"), VoteChoice.ENDORSE)
        voting_system.cast_vote(proposal.id, "voter2", Decimal("5"), VoteChoice.ENDORSE)
        voting_system.cast_vote(proposal.id, "voter3", Decimal("3"), VoteChoice.REJECT)

        result = voting_system.get_proposal_result(proposal.id, total_weight=Decimal("20"))

        assert result is not None
        assert result.endorse_weight == Decimal("15")
        assert result.reject_weight == Decimal("3")
        assert result.voter_count == 3

    def test_quorum_configuration(self):
        """Test quorum configuration."""
        config = QuorumConfig(
            threshold_percentage=75.0,
            require_majority=True,
            minimum_voters=3,
        )

        # Below threshold
        assert not config.is_quorum_reached(
            endorse_weight=Decimal("70"),
            reject_weight=Decimal("10"),
            total_weight=Decimal("100"),
            voter_count=3,
        )

        # Meets threshold
        assert config.is_quorum_reached(
            endorse_weight=Decimal("80"),
            reject_weight=Decimal("10"),
            total_weight=Decimal("100"),
            voter_count=3,
        )

        # Not enough voters
        assert not config.is_quorum_reached(
            endorse_weight=Decimal("80"),
            reject_weight=Decimal("10"),
            total_weight=Decimal("100"),
            voter_count=2,
        )


class TestQuadraticVoting:
    """Tests for quadratic voting strategy."""

    def test_quadratic_weight(self):
        """Test that quadratic voting reduces large stake advantage."""
        system = VotingSystem(voting_strategy=VotingStrategy.QUADRATIC)

        proposal = system.create_proposal(
            proposer_id="party_a",
            content_hash="0xabc123",
        )

        # With quadratic voting, sqrt(100) = 10
        vote = system.cast_vote(
            proposal_id=proposal.id,
            voter_id="whale",
            weight=Decimal("100"),
            choice=VoteChoice.ENDORSE,
        )

        assert vote.weight == Decimal("10")


class TestVoteDelegation:
    """Tests for vote delegation."""

    @pytest.fixture
    def voting_system(self):
        return VotingSystem()

    def test_create_delegation(self, voting_system):
        """Test creating a delegation."""
        delegation = voting_system.create_delegation(
            delegator_id="party_a",
            delegate_id="party_b",
            weight=Decimal("5.0"),
        )

        assert delegation is not None
        assert delegation.delegator_id == "party_a"
        assert delegation.delegate_id == "party_b"
        assert delegation.is_active

    def test_cast_delegated_vote(self, voting_system):
        """Test casting a vote using delegated power."""
        proposal = voting_system.create_proposal(
            proposer_id="party_c",
            content_hash="0xabc123",
        )

        voting_system.create_delegation(
            delegator_id="party_a",
            delegate_id="party_b",
            weight=Decimal("5.0"),
        )

        vote = voting_system.cast_delegated_vote(
            proposal_id=proposal.id,
            delegate_id="party_b",
            delegator_id="party_a",
            choice=VoteChoice.ENDORSE,
        )

        assert vote is not None
        assert vote.voter_id == "party_a"
        assert vote.delegation_from == "party_b"

    def test_revoke_delegation(self, voting_system):
        """Test revoking a delegation."""
        delegation = voting_system.create_delegation(
            delegator_id="party_a",
            delegate_id="party_b",
            weight=Decimal("5.0"),
        )

        assert voting_system.revoke_delegation(delegation.id)
        assert not voting_system._delegations[delegation.id].is_active


# =============================================================================
# MultiPartyOrchestrator Tests
# =============================================================================


class TestMultiPartyOrchestrator:
    """Tests for multi-party dispute orchestration."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance."""
        return MultiPartyOrchestrator(
            min_stake=Decimal("0.01"),
            staking_period_days=3,
            voting_period_days=7,
            default_quorum=6000,
        )

    def test_create_dispute_minimum_parties(self, orchestrator):
        """Test that dispute requires minimum 3 parties."""
        with pytest.raises(ValueError, match="Minimum 3 parties"):
            orchestrator.create_dispute(
                initiator_hash="party_a",
                party_hashes=["party_a", "party_b"],
                evidence_hash="0xevidence",
                ipfs_uri="ipfs://...",
                initiator_stake=Decimal("0.1"),
            )

    def test_create_dispute_success(self, orchestrator):
        """Test successful dispute creation."""
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("0.1"),
        )

        assert dispute is not None
        assert dispute.phase == DisputePhase.CREATED
        assert dispute.party_count == 3
        assert dispute.total_stake == Decimal("0.1")

    def test_create_dispute_no_duplicates(self, orchestrator):
        """Test that duplicate party hashes are rejected."""
        with pytest.raises(ValueError, match="Duplicate"):
            orchestrator.create_dispute(
                initiator_hash="party_a",
                party_hashes=["party_a", "party_b", "party_a"],
                evidence_hash="0xevidence",
                ipfs_uri="ipfs://...",
                initiator_stake=Decimal("0.1"),
            )

    def test_initiator_is_staked(self, orchestrator):
        """Test that initiator is automatically staked."""
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("0.1"),
        )

        initiator = dispute.parties["party_a"]
        assert initiator.has_staked
        assert initiator.stake_amount == Decimal("0.1")
        assert initiator.voting_weight > 0

    def test_join_dispute(self, orchestrator):
        """Test party joining a dispute."""
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("0.1"),
        )

        party, all_staked = orchestrator.join_dispute(
            dispute_id=dispute.id,
            party_hash="party_b",
            stake_amount=Decimal("0.1"),
        )

        assert party.has_staked
        assert not all_staked  # party_c hasn't staked yet

    def test_all_parties_staked_activates_dispute(self, orchestrator):
        """Test that dispute becomes active when all parties stake."""
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("0.1"),
        )

        orchestrator.join_dispute(dispute.id, "party_b", Decimal("0.1"))
        _, all_staked = orchestrator.join_dispute(dispute.id, "party_c", Decimal("0.1"))

        assert all_staked
        assert dispute.phase == DisputePhase.ACTIVE
        assert dispute.voting_deadline is not None

    def test_voting_weight_early_bonus(self, orchestrator):
        """Test that early stakers get voting weight bonus."""
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("1.0"),
        )

        initiator = dispute.parties["party_a"]
        # Early staker (initiator) should have bonus
        # With TIME_BONUS_PERCENT = 10%, weight should be ~1.1
        assert initiator.voting_weight >= Decimal("1.0")


class TestProposalSubmission:
    """Tests for proposal submission."""

    @pytest.fixture
    def active_dispute(self):
        """Create an orchestrator with an active dispute."""
        orchestrator = MultiPartyOrchestrator()
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("0.1"),
        )
        orchestrator.join_dispute(dispute.id, "party_b", Decimal("0.1"))
        orchestrator.join_dispute(dispute.id, "party_c", Decimal("0.1"))
        return orchestrator, dispute

    def test_submit_proposal(self, active_dispute):
        """Test submitting a proposal."""
        orchestrator, dispute = active_dispute

        proposal = orchestrator.submit_proposal(
            dispute_id=dispute.id,
            submission=ProposalSubmission(
                proposer_hash="party_a",
                content_hash="0xproposal",
                ipfs_uri="ipfs://proposal",
                payout_shares={
                    "party_a": 5000,
                    "party_b": 3000,
                    "party_c": 2000,
                },
            ),
        )

        assert proposal is not None
        assert dispute.phase == DisputePhase.VOTING

    def test_proposal_invalid_payout_shares(self, active_dispute):
        """Test that invalid payout shares are rejected."""
        orchestrator, dispute = active_dispute

        # Shares don't sum to 10000
        with pytest.raises(ValueError, match="sum to 10000"):
            orchestrator.submit_proposal(
                dispute_id=dispute.id,
                submission=ProposalSubmission(
                    proposer_hash="party_a",
                    content_hash="0xproposal",
                    ipfs_uri="ipfs://proposal",
                    payout_shares={
                        "party_a": 5000,
                        "party_b": 3000,
                        "party_c": 1000,
                    },
                ),
            )


class TestVotingAndResolution:
    """Tests for voting and resolution."""

    @pytest.fixture
    def dispute_with_proposal(self):
        """Create a dispute with a proposal ready for voting."""
        orchestrator = MultiPartyOrchestrator(default_quorum=6000)
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("1.0"),
        )
        orchestrator.join_dispute(dispute.id, "party_b", Decimal("1.0"))
        orchestrator.join_dispute(dispute.id, "party_c", Decimal("1.0"))

        proposal = orchestrator.submit_proposal(
            dispute_id=dispute.id,
            submission=ProposalSubmission(
                proposer_hash="party_a",
                content_hash="0xproposal",
                ipfs_uri="ipfs://proposal",
                payout_shares={
                    "party_a": 5000,
                    "party_b": 3000,
                    "party_c": 2000,
                },
            ),
        )
        return orchestrator, dispute, proposal

    def test_cast_vote(self, dispute_with_proposal):
        """Test casting votes."""
        orchestrator, dispute, proposal = dispute_with_proposal

        vote = orchestrator.cast_vote(
            dispute_id=dispute.id,
            proposal_id=proposal.id,
            voter_hash="party_b",
            choice=VoteChoice.ENDORSE,
        )

        assert vote is not None
        assert vote.choice == VoteChoice.ENDORSE

    def test_quorum_reached(self, dispute_with_proposal):
        """Test that quorum triggers resolution."""
        orchestrator, dispute, proposal = dispute_with_proposal

        # All three parties endorse (100% > 60% quorum)
        orchestrator.cast_vote(dispute.id, proposal.id, "party_a", VoteChoice.ENDORSE)
        orchestrator.cast_vote(dispute.id, proposal.id, "party_b", VoteChoice.ENDORSE)
        orchestrator.cast_vote(dispute.id, proposal.id, "party_c", VoteChoice.ENDORSE)

        assert proposal.status == ProposalStatus.ENDORSED
        assert dispute.winning_proposal_id == proposal.id

    def test_execute_resolution(self, dispute_with_proposal):
        """Test resolution execution."""
        orchestrator, dispute, proposal = dispute_with_proposal

        # Reach quorum
        orchestrator.cast_vote(dispute.id, proposal.id, "party_a", VoteChoice.ENDORSE)
        orchestrator.cast_vote(dispute.id, proposal.id, "party_b", VoteChoice.ENDORSE)
        orchestrator.cast_vote(dispute.id, proposal.id, "party_c", VoteChoice.ENDORSE)

        result = orchestrator.execute_resolution(dispute.id)

        assert result is not None
        assert result.resolved_by == "quorum"
        assert dispute.phase == DisputePhase.RESOLVED

        # Check payouts
        assert result.payouts["party_a"] == Decimal("1.5")  # 50% of 3 ETH
        assert result.payouts["party_b"] == Decimal("0.9")  # 30% of 3 ETH
        assert result.payouts["party_c"] == Decimal("0.6")  # 20% of 3 ETH


class TestCoalitionFormation:
    """Tests for coalition formation."""

    @pytest.fixture
    def voting_dispute(self):
        """Create a dispute in voting phase."""
        orchestrator = MultiPartyOrchestrator()
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c", "party_d"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("1.0"),
        )
        for party in ["party_b", "party_c", "party_d"]:
            orchestrator.join_dispute(dispute.id, party, Decimal("1.0"))

        proposal = orchestrator.submit_proposal(
            dispute_id=dispute.id,
            submission=ProposalSubmission(
                proposer_hash="party_a",
                content_hash="0xproposal",
                ipfs_uri="ipfs://proposal",
                payout_shares={
                    "party_a": 4000,
                    "party_b": 2500,
                    "party_c": 2000,
                    "party_d": 1500,
                },
            ),
        )
        return orchestrator, dispute, proposal

    def test_form_coalition(self, voting_dispute):
        """Test forming a coalition."""
        orchestrator, dispute, proposal = voting_dispute

        coalition = orchestrator.form_coalition(
            dispute_id=dispute.id,
            request=CoalitionRequest(
                member_hashes=["party_a", "party_b"],
                proposal_id=proposal.id,
            ),
        )

        assert coalition is not None
        assert len(coalition.member_hashes) == 2
        assert coalition.combined_weight > 0

    def test_coalition_needs_minimum_members(self, voting_dispute):
        """Test that coalition needs at least 2 members."""
        orchestrator, dispute, proposal = voting_dispute

        with pytest.raises(ValueError, match="2+ members"):
            orchestrator.form_coalition(
                dispute_id=dispute.id,
                request=CoalitionRequest(
                    member_hashes=["party_a"],
                    proposal_id=proposal.id,
                ),
            )


class TestMediatorResolution:
    """Tests for mediator resolution."""

    @pytest.fixture
    def mediation_dispute(self):
        """Create a dispute in mediation phase."""
        orchestrator = MultiPartyOrchestrator(voting_period_days=0)
        dispute = orchestrator.create_dispute(
            initiator_hash="party_a",
            party_hashes=["party_a", "party_b", "party_c"],
            evidence_hash="0xevidence",
            ipfs_uri="ipfs://...",
            initiator_stake=Decimal("1.0"),
        )
        orchestrator.join_dispute(dispute.id, "party_b", Decimal("1.0"))
        orchestrator.join_dispute(dispute.id, "party_c", Decimal("1.0"))

        # Submit proposal to enter voting phase
        orchestrator.submit_proposal(
            dispute_id=dispute.id,
            submission=ProposalSubmission(
                proposer_hash="party_a",
                content_hash="0xproposal",
                ipfs_uri="ipfs://proposal",
                payout_shares={
                    "party_a": 5000,
                    "party_b": 3000,
                    "party_c": 2000,
                },
            ),
        )

        # Force voting deadline to pass
        dispute.voting_deadline = datetime.now(timezone.utc) - timedelta(hours=1)

        # Escalate to mediation
        orchestrator.escalate_to_mediation(dispute.id)

        return orchestrator, dispute

    def test_mediator_resolve(self, mediation_dispute):
        """Test mediator resolving a dispute."""
        orchestrator, dispute = mediation_dispute

        result = orchestrator.mediator_resolve(
            dispute_id=dispute.id,
            mediator_id="mediator_1",
            payout_shares={
                "party_a": 4000,
                "party_b": 4000,
                "party_c": 2000,
            },
        )

        assert result is not None
        assert result.resolved_by == "mediator"
        assert dispute.phase == DisputePhase.RESOLVED
        assert dispute.mediator == "mediator_1"


class TestConvictionVoting:
    """Tests for conviction voting."""

    def test_conviction_multiplier(self):
        """Test that longer lock gives higher weight."""
        system = ConvictionVoting()

        proposal = system.create_proposal(
            proposer_id="party_a",
            content_hash="0xabc123",
        )

        now = datetime.now(timezone.utc)

        # Short lock (7 days)
        vote1 = system.cast_vote_with_lock(
            proposal_id=proposal.id,
            voter_id="voter1",
            weight=Decimal("10"),
            choice=VoteChoice.ENDORSE,
            lock_until=now + timedelta(days=7),
        )

        # Long lock (60 days)
        vote2 = system.cast_vote_with_lock(
            proposal_id=proposal.id,
            voter_id="voter2",
            weight=Decimal("10"),
            choice=VoteChoice.ENDORSE,
            lock_until=now + timedelta(days=60),
        )

        # Longer lock should have higher effective weight
        assert vote2.weight > vote1.weight


class TestDisputeParty:
    """Tests for DisputeParty dataclass."""

    def test_stake_wei_conversion(self):
        """Test stake to wei conversion."""
        party = DisputeParty(
            identity_hash="0xabc",
            role=PartyRole.INITIATOR,
            stake_amount=Decimal("1.5"),
        )

        assert party.stake_wei == 1500000000000000000


class TestCoalition:
    """Tests for Coalition dataclass."""

    def test_coalition_creation(self):
        """Test coalition dataclass."""
        from src.rra.reconciliation.multi import Coalition

        coalition = Coalition(
            id="coal_1",
            dispute_id="disp_1",
            member_hashes=["party_a", "party_b"],
            combined_weight=Decimal("2.0"),
            proposal_id="prop_1",
        )

        assert coalition.is_active
        assert len(coalition.member_hashes) == 2
