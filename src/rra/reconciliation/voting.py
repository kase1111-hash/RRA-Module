# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Weighted Voting Mechanisms.

Provides flexible voting infrastructure for multi-party disputes:
- Stake-weighted voting
- Quadratic voting support
- Configurable quorum thresholds
- Amendment and delegation support
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class VoteChoice(Enum):
    """Voting choices for proposals."""

    ABSTAIN = "abstain"
    ENDORSE = "endorse"
    REJECT = "reject"
    AMEND = "amend"  # Request amendments


class ProposalStatus(Enum):
    """Status of a proposal."""

    ACTIVE = "active"
    ENDORSED = "endorsed"      # Reached quorum
    REJECTED = "rejected"
    SUPERSEDED = "superseded"  # Replaced by another proposal
    EXECUTED = "executed"      # Settlement executed


class VotingStrategy(Enum):
    """Voting weight strategies."""

    LINEAR = "linear"          # 1 stake = 1 vote
    QUADRATIC = "quadratic"    # sqrt(stake) = vote power
    CONVICTION = "conviction"  # Weight increases with lock time


@dataclass
class QuorumConfig:
    """Configuration for quorum requirements."""

    threshold_percentage: float = 60.0  # Percentage of weight needed
    require_majority: bool = True       # Must have more endorse than reject
    minimum_voters: int = 2             # Minimum number of voters
    minimum_weight: Optional[Decimal] = None  # Minimum total weight to vote

    def is_quorum_reached(
        self,
        endorse_weight: Decimal,
        reject_weight: Decimal,
        total_weight: Decimal,
        voter_count: int,
    ) -> bool:
        """Check if quorum requirements are met."""
        if voter_count < self.minimum_voters:
            return False

        if self.minimum_weight and (endorse_weight + reject_weight) < self.minimum_weight:
            return False

        endorse_percentage = (
            (endorse_weight / total_weight) * 100
            if total_weight > 0
            else 0
        )

        if endorse_percentage < self.threshold_percentage:
            return False

        if self.require_majority and endorse_weight <= reject_weight:
            return False

        return True


@dataclass
class Vote:
    """A vote cast by a party."""

    id: str
    proposal_id: str
    voter_id: str
    choice: VoteChoice
    weight: Decimal
    timestamp: datetime
    delegation_from: Optional[str] = None  # If voting on behalf of another
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    """A proposal for dispute resolution."""

    id: str
    proposer_id: str
    content_hash: str
    created_at: datetime
    status: ProposalStatus = ProposalStatus.ACTIVE
    endorse_weight: Decimal = Decimal("0")
    reject_weight: Decimal = Decimal("0")
    abstain_weight: Decimal = Decimal("0")
    amend_weight: Decimal = Decimal("0")
    voter_count: int = 0
    is_coalition: bool = False
    parent_proposals: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_voted_weight(self) -> Decimal:
        """Total weight of all votes (excluding abstain)."""
        return self.endorse_weight + self.reject_weight + self.amend_weight


@dataclass
class VotingResult:
    """Result of voting on a proposal."""

    proposal_id: str
    endorse_weight: Decimal
    reject_weight: Decimal
    abstain_weight: Decimal
    amend_weight: Decimal
    total_weight: Decimal
    voter_count: int
    quorum_reached: bool
    approved: bool
    margin: Decimal  # Difference between endorse and reject
    participation_rate: float  # Percentage of total weight that voted


@dataclass
class VoteDelegation:
    """Delegation of voting power."""

    id: str
    delegator_id: str
    delegate_id: str
    weight: Decimal
    proposal_ids: Optional[List[str]] = None  # None = all proposals
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class VotingSystem:
    """
    Manages voting on proposals with weighted votes.

    Features:
    - Stake-weighted voting
    - Quadratic voting option
    - Vote delegation
    - Configurable quorum
    - Amendment proposals
    """

    def __init__(
        self,
        quorum_config: Optional[QuorumConfig] = None,
        voting_strategy: VotingStrategy = VotingStrategy.LINEAR,
    ):
        """
        Initialize voting system.

        Args:
            quorum_config: Quorum configuration
            voting_strategy: How to calculate vote weight
        """
        self.quorum_config = quorum_config or QuorumConfig()
        self.voting_strategy = voting_strategy

        # Storage
        self._proposals: Dict[str, Proposal] = {}
        self._votes: Dict[str, Dict[str, Vote]] = {}  # proposal_id -> voter_id -> vote
        self._delegations: Dict[str, VoteDelegation] = {}
        self._voter_delegations: Dict[str, List[str]] = {}  # voter_id -> delegation_ids

        # Total registered weight (for participation calculation)
        self._total_registered_weight: Decimal = Decimal("0")
        self._registered_voters: Set[str] = set()

    def register_voter(self, voter_id: str, weight: Decimal) -> None:
        """
        Register a voter with their voting weight.

        Args:
            voter_id: Voter identifier
            weight: Voting weight (stake)
        """
        if voter_id not in self._registered_voters:
            self._registered_voters.add(voter_id)
            effective_weight = self._apply_strategy(weight)
            self._total_registered_weight += effective_weight

    def create_proposal(
        self,
        proposer_id: str,
        content_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_proposals: Optional[List[str]] = None,
    ) -> Proposal:
        """
        Create a new proposal.

        Args:
            proposer_id: Who is proposing
            content_hash: Hash of proposal content
            metadata: Additional metadata
            parent_proposals: Parent proposals if this is a merger

        Returns:
            Created Proposal
        """
        proposal_id = secrets.token_urlsafe(12)

        proposal = Proposal(
            id=proposal_id,
            proposer_id=proposer_id,
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc),
            is_coalition=bool(parent_proposals),
            parent_proposals=parent_proposals or [],
            metadata=metadata or {},
        )

        self._proposals[proposal_id] = proposal
        self._votes[proposal_id] = {}

        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        voter_id: str,
        weight: Decimal,
        choice: VoteChoice,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Vote:
        """
        Cast a vote on a proposal.

        Args:
            proposal_id: Proposal to vote on
            voter_id: Voter identifier
            weight: Voter's weight
            choice: Vote choice
            metadata: Additional vote metadata

        Returns:
            Recorded Vote

        Raises:
            ValueError: If vote is invalid
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        if proposal.status != ProposalStatus.ACTIVE:
            raise ValueError("Proposal is not active")

        if voter_id in self._votes[proposal_id]:
            raise ValueError("Voter has already voted on this proposal")

        # Apply voting strategy
        effective_weight = self._apply_strategy(weight)

        # Create vote
        vote = Vote(
            id=secrets.token_urlsafe(8),
            proposal_id=proposal_id,
            voter_id=voter_id,
            choice=choice,
            weight=effective_weight,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        # Record vote
        self._votes[proposal_id][voter_id] = vote

        # Update tallies
        if choice == VoteChoice.ENDORSE:
            proposal.endorse_weight += effective_weight
        elif choice == VoteChoice.REJECT:
            proposal.reject_weight += effective_weight
        elif choice == VoteChoice.ABSTAIN:
            proposal.abstain_weight += effective_weight
        elif choice == VoteChoice.AMEND:
            proposal.amend_weight += effective_weight

        proposal.voter_count += 1

        return vote

    def cast_delegated_vote(
        self,
        proposal_id: str,
        delegate_id: str,
        delegator_id: str,
        choice: VoteChoice,
    ) -> Vote:
        """
        Cast a vote using delegated power.

        Args:
            proposal_id: Proposal to vote on
            delegate_id: Who is casting the vote
            delegator_id: Whose power is being used
            choice: Vote choice

        Returns:
            Recorded Vote

        Raises:
            ValueError: If delegation is invalid
        """
        # Find valid delegation
        delegation = self._find_active_delegation(delegator_id, delegate_id, proposal_id)
        if not delegation:
            raise ValueError("No valid delegation found")

        # Cast vote with delegated weight
        vote = Vote(
            id=secrets.token_urlsafe(8),
            proposal_id=proposal_id,
            voter_id=delegator_id,
            choice=choice,
            weight=delegation.weight,
            timestamp=datetime.now(timezone.utc),
            delegation_from=delegate_id,
        )

        # Record as if delegator voted
        self._votes[proposal_id][delegator_id] = vote

        # Update proposal tallies
        proposal = self._proposals[proposal_id]
        if choice == VoteChoice.ENDORSE:
            proposal.endorse_weight += delegation.weight
        elif choice == VoteChoice.REJECT:
            proposal.reject_weight += delegation.weight
        elif choice == VoteChoice.ABSTAIN:
            proposal.abstain_weight += delegation.weight
        elif choice == VoteChoice.AMEND:
            proposal.amend_weight += delegation.weight

        proposal.voter_count += 1

        return vote

    def create_delegation(
        self,
        delegator_id: str,
        delegate_id: str,
        weight: Decimal,
        proposal_ids: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> VoteDelegation:
        """
        Create a vote delegation.

        Args:
            delegator_id: Who is delegating
            delegate_id: Who receives the delegation
            weight: Weight to delegate
            proposal_ids: Specific proposals (None = all)
            expires_at: Expiration time

        Returns:
            Created VoteDelegation
        """
        delegation_id = secrets.token_urlsafe(8)

        delegation = VoteDelegation(
            id=delegation_id,
            delegator_id=delegator_id,
            delegate_id=delegate_id,
            weight=self._apply_strategy(weight),
            proposal_ids=proposal_ids,
            expires_at=expires_at,
        )

        self._delegations[delegation_id] = delegation

        if delegator_id not in self._voter_delegations:
            self._voter_delegations[delegator_id] = []
        self._voter_delegations[delegator_id].append(delegation_id)

        return delegation

    def revoke_delegation(self, delegation_id: str) -> bool:
        """
        Revoke a delegation.

        Args:
            delegation_id: Delegation to revoke

        Returns:
            True if revoked
        """
        delegation = self._delegations.get(delegation_id)
        if not delegation:
            return False

        delegation.is_active = False
        return True

    def get_proposal_result(
        self,
        proposal_id: str,
        total_weight: Optional[Decimal] = None,
    ) -> Optional[VotingResult]:
        """
        Get voting result for a proposal.

        Args:
            proposal_id: Proposal ID
            total_weight: Override total weight for calculation

        Returns:
            VotingResult or None if proposal not found
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None

        total = total_weight or self._total_registered_weight
        if total == 0:
            total = Decimal("1")  # Avoid division by zero

        quorum_reached = self.quorum_config.is_quorum_reached(
            endorse_weight=proposal.endorse_weight,
            reject_weight=proposal.reject_weight,
            total_weight=total,
            voter_count=proposal.voter_count,
        )

        margin = proposal.endorse_weight - proposal.reject_weight
        approved = quorum_reached and margin > 0

        voted_weight = proposal.endorse_weight + proposal.reject_weight + proposal.abstain_weight
        participation = float(voted_weight / total * 100) if total > 0 else 0

        return VotingResult(
            proposal_id=proposal_id,
            endorse_weight=proposal.endorse_weight,
            reject_weight=proposal.reject_weight,
            abstain_weight=proposal.abstain_weight,
            amend_weight=proposal.amend_weight,
            total_weight=total,
            voter_count=proposal.voter_count,
            quorum_reached=quorum_reached,
            approved=approved,
            margin=margin,
            participation_rate=participation,
        )

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get proposal by ID."""
        return self._proposals.get(proposal_id)

    def get_votes(self, proposal_id: str) -> List[Vote]:
        """Get all votes for a proposal."""
        return list(self._votes.get(proposal_id, {}).values())

    def get_voter_votes(self, voter_id: str) -> List[Vote]:
        """Get all votes by a voter."""
        votes = []
        for proposal_votes in self._votes.values():
            if voter_id in proposal_votes:
                votes.append(proposal_votes[voter_id])
        return votes

    def has_voted(self, proposal_id: str, voter_id: str) -> bool:
        """Check if voter has voted on proposal."""
        return voter_id in self._votes.get(proposal_id, {})

    def merge_proposals(
        self,
        proposal_ids: List[str],
        merger_id: str,
        content_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Proposal:
        """
        Merge multiple proposals into a coalition proposal.

        Args:
            proposal_ids: Proposals to merge
            merger_id: Who is creating the merger
            content_hash: Hash of merged content
            metadata: Additional metadata

        Returns:
            New merged Proposal
        """
        # Mark parent proposals as superseded
        for pid in proposal_ids:
            proposal = self._proposals.get(pid)
            if proposal:
                proposal.status = ProposalStatus.SUPERSEDED

        # Create merged proposal
        return self.create_proposal(
            proposer_id=merger_id,
            content_hash=content_hash,
            metadata=metadata,
            parent_proposals=proposal_ids,
        )

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _apply_strategy(self, weight: Decimal) -> Decimal:
        """Apply voting strategy to weight."""
        if self.voting_strategy == VotingStrategy.LINEAR:
            return weight
        elif self.voting_strategy == VotingStrategy.QUADRATIC:
            # Quadratic voting: vote power = sqrt(stake)
            return Decimal(str(weight.sqrt()))
        else:
            # Default to linear
            return weight

    def _find_active_delegation(
        self,
        delegator_id: str,
        delegate_id: str,
        proposal_id: str,
    ) -> Optional[VoteDelegation]:
        """Find an active delegation."""
        delegation_ids = self._voter_delegations.get(delegator_id, [])
        now = datetime.now(timezone.utc)

        for did in delegation_ids:
            delegation = self._delegations.get(did)
            if not delegation or not delegation.is_active:
                continue
            if delegation.delegate_id != delegate_id:
                continue
            if delegation.expires_at and now > delegation.expires_at:
                continue
            if delegation.proposal_ids and proposal_id not in delegation.proposal_ids:
                continue
            return delegation

        return None


class ConvictionVoting(VotingSystem):
    """
    Conviction voting where vote weight increases with lock time.

    The longer a vote is locked, the more weight it carries.
    This encourages long-term thinking and commitment.
    """

    DECAY_CONSTANT = Decimal("0.9")  # Decay factor per time unit
    MAX_CONVICTION_MULTIPLIER = Decimal("10")  # Maximum multiplier

    def __init__(self, quorum_config: Optional[QuorumConfig] = None):
        super().__init__(quorum_config, VotingStrategy.CONVICTION)
        self._vote_lock_times: Dict[str, Dict[str, datetime]] = {}

    def cast_vote_with_lock(
        self,
        proposal_id: str,
        voter_id: str,
        weight: Decimal,
        choice: VoteChoice,
        lock_until: datetime,
    ) -> Vote:
        """
        Cast a vote with a lock period.

        Args:
            proposal_id: Proposal to vote on
            voter_id: Voter identifier
            weight: Base weight
            choice: Vote choice
            lock_until: When the vote unlocks

        Returns:
            Recorded Vote
        """
        # Calculate conviction multiplier based on lock time
        now = datetime.now(timezone.utc)
        lock_seconds = (lock_until - now).total_seconds()

        # Longer lock = higher multiplier (up to max)
        days_locked = Decimal(lock_seconds) / Decimal(86400)
        multiplier = min(
            Decimal("1") + (days_locked / Decimal("30")),  # 1 month = 2x
            self.MAX_CONVICTION_MULTIPLIER,
        )

        effective_weight = weight * multiplier

        vote = self.cast_vote(proposal_id, voter_id, effective_weight, choice)

        # Track lock time
        if proposal_id not in self._vote_lock_times:
            self._vote_lock_times[proposal_id] = {}
        self._vote_lock_times[proposal_id][voter_id] = lock_until

        return vote

    def get_conviction(self, proposal_id: str, voter_id: str) -> Optional[datetime]:
        """Get lock end time for a vote."""
        return self._vote_lock_times.get(proposal_id, {}).get(voter_id)
