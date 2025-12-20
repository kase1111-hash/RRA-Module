# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Multi-Party Dispute Orchestration.

Coordinates N-party dispute resolution with:
- Party management and stake tracking
- Proposal lifecycle management
- Coalition formation and aggregation
- Resolution execution
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .voting import (
    VotingSystem,
    Vote,
    VoteChoice,
    Proposal,
    ProposalStatus,
    QuorumConfig,
)


class DisputePhase(Enum):
    """Phases of a multi-party dispute."""

    CREATED = "created"           # Awaiting party stakes
    ACTIVE = "active"             # All parties staked, proposals accepted
    VOTING = "voting"             # Voting on proposals
    MEDIATION = "mediation"       # Escalated to mediator
    ARBITRATION = "arbitration"   # Escalated to arbitrator
    RESOLVED = "resolved"         # Settlement reached
    DISMISSED = "dismissed"       # Dispute dismissed/expired


class PartyRole(Enum):
    """Role of a party in the dispute."""

    INITIATOR = "initiator"
    COUNTERPARTY = "counterparty"
    PARTICIPANT = "participant"


@dataclass
class DisputeParty:
    """A party in a multi-party dispute."""

    identity_hash: str
    role: PartyRole
    stake_amount: Decimal = Decimal("0")
    voting_weight: Decimal = Decimal("0")
    has_staked: bool = False
    is_verified: bool = False
    joined_at: Optional[datetime] = None
    claim_address: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def stake_wei(self) -> int:
        """Get stake amount in wei."""
        return int(self.stake_amount * Decimal("1e18"))


@dataclass
class Coalition:
    """A coalition of parties with combined voting power."""

    id: str
    dispute_id: str
    member_hashes: List[str]
    combined_weight: Decimal
    proposal_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProposalSubmission:
    """Request to submit a proposal."""

    proposer_hash: str
    content_hash: str
    ipfs_uri: str
    payout_shares: Dict[str, int]  # identity_hash -> basis points (sum to 10000)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoalitionRequest:
    """Request to form a coalition."""

    member_hashes: List[str]
    proposal_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionResult:
    """Result of dispute resolution."""

    dispute_id: str
    winning_proposal_id: Optional[str]
    payouts: Dict[str, Decimal]  # identity_hash -> amount
    resolved_at: datetime
    resolved_by: str  # "quorum", "mediator", "arbitrator"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiPartyDispute:
    """A dispute involving 3+ parties."""

    id: str
    initiator_hash: str
    evidence_hash: str
    ipfs_metadata_uri: str
    created_at: datetime
    stake_deadline: datetime
    voting_deadline: Optional[datetime]
    phase: DisputePhase
    total_stake: Decimal
    total_voting_weight: Decimal
    quorum_threshold: int  # Basis points (e.g., 6000 = 60%)
    parties: Dict[str, DisputeParty]
    proposals: Dict[str, Proposal]
    coalitions: Dict[str, Coalition]
    winning_proposal_id: Optional[str] = None
    mediator: Optional[str] = None
    arbitrator: Optional[str] = None
    resolution: Optional[ResolutionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def party_count(self) -> int:
        """Get number of parties."""
        return len(self.parties)

    @property
    def staked_party_count(self) -> int:
        """Get number of parties that have staked."""
        return sum(1 for p in self.parties.values() if p.has_staked)

    @property
    def all_parties_staked(self) -> bool:
        """Check if all parties have staked."""
        return all(p.has_staked for p in self.parties.values())


class MultiPartyOrchestrator:
    """
    Orchestrates multi-party dispute resolution.

    Manages the lifecycle of N-party disputes:
    1. Dispute creation with party list
    2. Stake collection from all parties
    3. Proposal submission and voting
    4. Coalition formation
    5. Resolution execution
    """

    MIN_PARTIES = 3
    MAX_PARTIES = 20
    PERCENTAGE_BASE = 10000

    # Default configuration
    DEFAULT_STAKING_PERIOD_DAYS = 3
    DEFAULT_VOTING_PERIOD_DAYS = 7
    DEFAULT_QUORUM = 6000  # 60%
    DEFAULT_MIN_STAKE = Decimal("0.01")  # ETH

    # Weight calculation
    STAKE_WEIGHT_MULTIPLIER = Decimal("1.0")
    TIME_BONUS_PERCENT = Decimal("0.1")  # 10% max bonus for early stakers

    def __init__(
        self,
        min_stake: Decimal = DEFAULT_MIN_STAKE,
        staking_period_days: int = DEFAULT_STAKING_PERIOD_DAYS,
        voting_period_days: int = DEFAULT_VOTING_PERIOD_DAYS,
        default_quorum: int = DEFAULT_QUORUM,
    ):
        """
        Initialize the orchestrator.

        Args:
            min_stake: Minimum stake amount in ETH
            staking_period_days: Days for parties to stake
            voting_period_days: Days for voting period
            default_quorum: Default quorum threshold (basis points)
        """
        self.min_stake = min_stake
        self.staking_period = timedelta(days=staking_period_days)
        self.voting_period = timedelta(days=voting_period_days)
        self.default_quorum = default_quorum

        # Storage
        self._disputes: Dict[str, MultiPartyDispute] = {}
        self._voting_systems: Dict[str, VotingSystem] = {}

    def create_dispute(
        self,
        initiator_hash: str,
        party_hashes: List[str],
        evidence_hash: str,
        ipfs_uri: str,
        initiator_stake: Decimal,
        quorum_threshold: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MultiPartyDispute:
        """
        Create a new multi-party dispute.

        Args:
            initiator_hash: Identity hash of initiator
            party_hashes: All party identity hashes (including initiator first)
            evidence_hash: Hash of dispute evidence
            ipfs_uri: IPFS URI for metadata
            initiator_stake: Initiator's stake amount
            quorum_threshold: Custom quorum (None for default)
            metadata: Additional metadata

        Returns:
            Created MultiPartyDispute

        Raises:
            ValueError: If validation fails
        """
        # Validate party count
        if len(party_hashes) < self.MIN_PARTIES:
            raise ValueError(f"Minimum {self.MIN_PARTIES} parties required")
        if len(party_hashes) > self.MAX_PARTIES:
            raise ValueError(f"Maximum {self.MAX_PARTIES} parties allowed")

        # Validate initiator
        if party_hashes[0] != initiator_hash:
            raise ValueError("Initiator must be first in party list")

        # Validate uniqueness
        if len(set(party_hashes)) != len(party_hashes):
            raise ValueError("Duplicate party hashes not allowed")

        # Validate stake
        if initiator_stake < self.min_stake:
            raise ValueError(f"Minimum stake is {self.min_stake} ETH")

        # Generate dispute ID
        dispute_id = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)

        # Calculate initiator weight
        initiator_weight = self._calculate_voting_weight(
            initiator_stake, now, now
        )

        # Create parties
        parties: Dict[str, DisputeParty] = {}
        for i, party_hash in enumerate(party_hashes):
            if i == 0:
                # Initiator
                parties[party_hash] = DisputeParty(
                    identity_hash=party_hash,
                    role=PartyRole.INITIATOR,
                    stake_amount=initiator_stake,
                    voting_weight=initiator_weight,
                    has_staked=True,
                    joined_at=now,
                )
            else:
                # Other parties
                role = PartyRole.COUNTERPARTY if i == 1 else PartyRole.PARTICIPANT
                parties[party_hash] = DisputeParty(
                    identity_hash=party_hash,
                    role=role,
                )

        # Create dispute
        quorum = quorum_threshold if quorum_threshold else self.default_quorum
        if quorum > self.PERCENTAGE_BASE:
            raise ValueError("Invalid quorum threshold")

        dispute = MultiPartyDispute(
            id=dispute_id,
            initiator_hash=initiator_hash,
            evidence_hash=evidence_hash,
            ipfs_metadata_uri=ipfs_uri,
            created_at=now,
            stake_deadline=now + self.staking_period,
            voting_deadline=None,
            phase=DisputePhase.CREATED,
            total_stake=initiator_stake,
            total_voting_weight=initiator_weight,
            quorum_threshold=quorum,
            parties=parties,
            proposals={},
            coalitions={},
            metadata=metadata or {},
        )

        # Create voting system
        quorum_config = QuorumConfig(
            threshold_percentage=quorum / 100,  # Convert to percentage
            require_majority=True,
        )
        self._voting_systems[dispute_id] = VotingSystem(quorum_config)

        self._disputes[dispute_id] = dispute
        return dispute

    def join_dispute(
        self,
        dispute_id: str,
        party_hash: str,
        stake_amount: Decimal,
    ) -> Tuple[DisputeParty, bool]:
        """
        Join an existing dispute as a named party.

        Args:
            dispute_id: Dispute to join
            party_hash: Party's identity hash
            stake_amount: Stake amount

        Returns:
            Tuple of (party, all_parties_staked)

        Raises:
            ValueError: If validation fails
        """
        dispute = self._get_dispute(dispute_id)

        if dispute.phase != DisputePhase.CREATED:
            raise ValueError("Dispute not accepting stakes")

        now = datetime.now(timezone.utc)
        if now > dispute.stake_deadline:
            raise ValueError("Staking period ended")

        if stake_amount < self.min_stake:
            raise ValueError(f"Minimum stake is {self.min_stake} ETH")

        party = dispute.parties.get(party_hash)
        if not party:
            raise ValueError("Not a named party in this dispute")

        if party.has_staked:
            raise ValueError("Party has already staked")

        # Calculate voting weight
        weight = self._calculate_voting_weight(
            stake_amount, now, dispute.created_at
        )

        # Update party
        party.stake_amount = stake_amount
        party.voting_weight = weight
        party.has_staked = True
        party.joined_at = now

        # Update dispute totals
        dispute.total_stake += stake_amount
        dispute.total_voting_weight += weight

        # Check if all parties have staked
        if dispute.all_parties_staked:
            dispute.phase = DisputePhase.ACTIVE
            dispute.voting_deadline = now + self.voting_period

        return party, dispute.all_parties_staked

    def submit_proposal(
        self,
        dispute_id: str,
        submission: ProposalSubmission,
    ) -> Proposal:
        """
        Submit a settlement proposal.

        Args:
            dispute_id: Dispute ID
            submission: Proposal submission details

        Returns:
            Created Proposal

        Raises:
            ValueError: If validation fails
        """
        dispute = self._get_dispute(dispute_id)

        if dispute.phase not in (DisputePhase.ACTIVE, DisputePhase.VOTING):
            raise ValueError("Dispute not accepting proposals")

        now = datetime.now(timezone.utc)
        if dispute.voting_deadline and now > dispute.voting_deadline:
            raise ValueError("Voting period ended")

        party = dispute.parties.get(submission.proposer_hash)
        if not party or not party.has_staked:
            raise ValueError("Proposer is not a staked party")

        # Validate payout shares
        if set(submission.payout_shares.keys()) != set(dispute.parties.keys()):
            raise ValueError("Payout shares must include all parties")

        total_shares = sum(submission.payout_shares.values())
        if total_shares != self.PERCENTAGE_BASE:
            raise ValueError(f"Payout shares must sum to {self.PERCENTAGE_BASE}")

        # Create proposal
        voting_system = self._voting_systems[dispute_id]
        proposal = voting_system.create_proposal(
            proposer_id=submission.proposer_hash,
            content_hash=submission.content_hash,
            metadata={
                "ipfs_uri": submission.ipfs_uri,
                "payout_shares": submission.payout_shares,
                **submission.metadata,
            },
        )

        dispute.proposals[proposal.id] = proposal

        # Transition to voting if first proposal
        if dispute.phase == DisputePhase.ACTIVE:
            dispute.phase = DisputePhase.VOTING

        return proposal

    def cast_vote(
        self,
        dispute_id: str,
        proposal_id: str,
        voter_hash: str,
        choice: VoteChoice,
        amendment_hash: Optional[str] = None,
    ) -> Vote:
        """
        Cast a vote on a proposal.

        Args:
            dispute_id: Dispute ID
            proposal_id: Proposal to vote on
            voter_hash: Voter's identity hash
            choice: Vote choice
            amendment_hash: Hash of amendments if choice is AMEND

        Returns:
            Recorded Vote

        Raises:
            ValueError: If validation fails
        """
        dispute = self._get_dispute(dispute_id)

        if dispute.phase != DisputePhase.VOTING:
            raise ValueError("Not in voting phase")

        now = datetime.now(timezone.utc)
        if dispute.voting_deadline and now > dispute.voting_deadline:
            raise ValueError("Voting period ended")

        party = dispute.parties.get(voter_hash)
        if not party or not party.has_staked:
            raise ValueError("Voter is not a staked party")

        proposal = dispute.proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.ACTIVE:
            raise ValueError("Proposal not active")

        # Cast vote
        voting_system = self._voting_systems[dispute_id]
        vote = voting_system.cast_vote(
            proposal_id=proposal_id,
            voter_id=voter_hash,
            weight=party.voting_weight,
            choice=choice,
            metadata={"amendment_hash": amendment_hash} if amendment_hash else {},
        )

        # Check for quorum
        self._check_quorum(dispute, proposal_id)

        return vote

    def form_coalition(
        self,
        dispute_id: str,
        request: CoalitionRequest,
    ) -> Coalition:
        """
        Form a coalition with combined voting power.

        Args:
            dispute_id: Dispute ID
            request: Coalition formation request

        Returns:
            Created Coalition

        Raises:
            ValueError: If validation fails
        """
        dispute = self._get_dispute(dispute_id)

        if dispute.phase != DisputePhase.VOTING:
            raise ValueError("Not in voting phase")

        if len(request.member_hashes) < 2:
            raise ValueError("Coalition needs 2+ members")

        proposal = dispute.proposals.get(request.proposal_id)
        if not proposal or proposal.status != ProposalStatus.ACTIVE:
            raise ValueError("Invalid proposal")

        # Validate all members are staked parties
        combined_weight = Decimal("0")
        for member_hash in request.member_hashes:
            party = dispute.parties.get(member_hash)
            if not party or not party.has_staked:
                raise ValueError(f"Member {member_hash[:8]} not a staked party")
            combined_weight += party.voting_weight

        # Create coalition
        coalition_id = secrets.token_urlsafe(12)
        coalition = Coalition(
            id=coalition_id,
            dispute_id=dispute_id,
            member_hashes=request.member_hashes.copy(),
            combined_weight=combined_weight,
            proposal_id=request.proposal_id,
            metadata=request.metadata,
        )

        dispute.coalitions[coalition_id] = coalition
        return coalition

    def execute_resolution(
        self,
        dispute_id: str,
    ) -> ResolutionResult:
        """
        Execute resolution for an endorsed proposal.

        Args:
            dispute_id: Dispute ID

        Returns:
            ResolutionResult

        Raises:
            ValueError: If no winning proposal
        """
        dispute = self._get_dispute(dispute_id)

        if dispute.phase != DisputePhase.VOTING:
            raise ValueError("Not in voting phase")

        if not dispute.winning_proposal_id:
            raise ValueError("No winning proposal")

        proposal = dispute.proposals[dispute.winning_proposal_id]
        if proposal.status != ProposalStatus.ENDORSED:
            raise ValueError("Proposal not endorsed")

        # Calculate payouts
        payout_shares = proposal.metadata.get("payout_shares", {})
        payouts: Dict[str, Decimal] = {}

        for party_hash, share_bps in payout_shares.items():
            payout = (dispute.total_stake * Decimal(share_bps)) / Decimal(self.PERCENTAGE_BASE)
            payouts[party_hash] = payout

        # Update proposal and dispute
        proposal.status = ProposalStatus.EXECUTED
        dispute.phase = DisputePhase.RESOLVED

        now = datetime.now(timezone.utc)
        result = ResolutionResult(
            dispute_id=dispute_id,
            winning_proposal_id=dispute.winning_proposal_id,
            payouts=payouts,
            resolved_at=now,
            resolved_by="quorum",
        )
        dispute.resolution = result

        return result

    def escalate_to_mediation(self, dispute_id: str) -> None:
        """
        Escalate dispute to mediation.

        Args:
            dispute_id: Dispute ID

        Raises:
            ValueError: If cannot escalate
        """
        dispute = self._get_dispute(dispute_id)

        if dispute.phase != DisputePhase.VOTING:
            raise ValueError("Cannot escalate from this phase")

        now = datetime.now(timezone.utc)
        if dispute.voting_deadline and now <= dispute.voting_deadline:
            raise ValueError("Voting not ended")

        if dispute.winning_proposal_id:
            raise ValueError("Already has winning proposal")

        dispute.phase = DisputePhase.MEDIATION

    def mediator_resolve(
        self,
        dispute_id: str,
        mediator_id: str,
        payout_shares: Dict[str, int],
    ) -> ResolutionResult:
        """
        Mediator resolves the dispute.

        Args:
            dispute_id: Dispute ID
            mediator_id: Mediator's identifier
            payout_shares: Mediator-determined payouts (basis points)

        Returns:
            ResolutionResult

        Raises:
            ValueError: If validation fails
        """
        dispute = self._get_dispute(dispute_id)

        if dispute.phase != DisputePhase.MEDIATION:
            raise ValueError("Not in mediation phase")

        # Validate payout shares
        if set(payout_shares.keys()) != set(dispute.parties.keys()):
            raise ValueError("Payout shares must include all parties")

        total_shares = sum(payout_shares.values())
        if total_shares != self.PERCENTAGE_BASE:
            raise ValueError(f"Payout shares must sum to {self.PERCENTAGE_BASE}")

        # Calculate payouts
        payouts: Dict[str, Decimal] = {}
        for party_hash, share_bps in payout_shares.items():
            payout = (dispute.total_stake * Decimal(share_bps)) / Decimal(self.PERCENTAGE_BASE)
            payouts[party_hash] = payout

        # Update dispute
        dispute.phase = DisputePhase.RESOLVED
        dispute.mediator = mediator_id

        now = datetime.now(timezone.utc)
        result = ResolutionResult(
            dispute_id=dispute_id,
            winning_proposal_id=None,
            payouts=payouts,
            resolved_at=now,
            resolved_by="mediator",
            metadata={"mediator_id": mediator_id},
        )
        dispute.resolution = result

        return result

    def get_dispute(self, dispute_id: str) -> Optional[MultiPartyDispute]:
        """Get dispute by ID."""
        return self._disputes.get(dispute_id)

    def get_party_disputes(self, party_hash: str) -> List[MultiPartyDispute]:
        """Get all disputes involving a party."""
        return [
            d for d in self._disputes.values()
            if party_hash in d.parties
        ]

    def get_active_disputes(self) -> List[MultiPartyDispute]:
        """Get all active disputes."""
        return [
            d for d in self._disputes.values()
            if d.phase not in (DisputePhase.RESOLVED, DisputePhase.DISMISSED)
        ]

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _get_dispute(self, dispute_id: str) -> MultiPartyDispute:
        """Get dispute or raise error."""
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute {dispute_id} not found")
        return dispute

    def _calculate_voting_weight(
        self,
        stake: Decimal,
        join_time: datetime,
        dispute_start: datetime,
    ) -> Decimal:
        """Calculate voting weight based on stake and timing."""
        # Base weight from stake
        base_weight = stake * self.STAKE_WEIGHT_MULTIPLIER

        # Time bonus for early stakers
        elapsed = (join_time - dispute_start).total_seconds()
        staking_seconds = self.staking_period.total_seconds()

        if elapsed < staking_seconds:
            bonus_factor = Decimal(1) - Decimal(elapsed) / Decimal(staking_seconds)
            max_bonus = base_weight * self.TIME_BONUS_PERCENT
            bonus = max_bonus * bonus_factor
        else:
            bonus = Decimal("0")

        return base_weight + bonus

    def _check_quorum(self, dispute: MultiPartyDispute, proposal_id: str) -> None:
        """Check if a proposal has reached quorum."""
        voting_system = self._voting_systems[dispute.id]
        result = voting_system.get_proposal_result(proposal_id)

        if not result:
            return

        # Calculate endorsement percentage
        if dispute.total_voting_weight > 0:
            endorse_percentage = (
                result.endorse_weight / dispute.total_voting_weight
            ) * self.PERCENTAGE_BASE

            if endorse_percentage >= dispute.quorum_threshold:
                proposal = dispute.proposals[proposal_id]
                proposal.status = ProposalStatus.ENDORSED
                dispute.winning_proposal_id = proposal_id
