# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Treasury Coordination System.

Orchestrates multi-treasury dispute resolution:
- Treasury registration and signer management
- Dispute creation and lifecycle management
- Stake-weighted voting coordination
- Escrow and fund distribution
- Advisory resolution (economic pressure)

This module provides the off-chain coordination layer that works
with the TreasuryCoordinator smart contract.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class TreasuryType(Enum):
    """Types of treasuries."""

    DAO = "dao"                  # DAO-controlled treasury
    MULTISIG = "multisig"        # Multi-signature wallet
    INDIVIDUAL = "individual"    # Single-owner treasury
    PROTOCOL = "protocol"        # Protocol-owned treasury


class DisputeStatus(Enum):
    """Status of a treasury dispute."""

    CREATED = "created"          # Initial creation
    STAKING = "staking"          # Awaiting treasury stakes
    VOTING = "voting"            # Active voting period
    MEDIATION = "mediation"      # Escalated to mediator
    RESOLVED = "resolved"        # Resolution reached
    EXECUTED = "executed"        # Funds distributed
    EXPIRED = "expired"          # Voting period expired
    CANCELLED = "cancelled"      # Cancelled by creator


class ProposalType(Enum):
    """Types of resolution proposals."""

    FUND_DISTRIBUTION = "fund_distribution"      # Distribute disputed funds
    COMPENSATION_AWARD = "compensation_award"    # Award compensation
    LICENSE_TERMS = "license_terms"              # Set licensing terms
    CONTRIBUTOR_PAYMENT = "contributor_payment"  # Contributor payment
    CUSTOM = "custom"                            # Custom resolution


class VoteChoice(Enum):
    """Voting choices."""

    ABSTAIN = "abstain"
    SUPPORT = "support"
    OPPOSE = "oppose"
    AMEND = "amend"


@dataclass
class Treasury:
    """A registered treasury."""

    treasury_id: str
    name: str
    treasury_type: TreasuryType
    signers: List[str]              # Signer addresses
    signer_threshold: int           # Required signatures
    registered_at: datetime
    total_disputes: int = 0
    resolved_disputes: int = 0
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_signer(self, address: str) -> bool:
        """Check if address is a signer."""
        return address.lower() in [s.lower() for s in self.signers]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "treasury_id": self.treasury_id,
            "name": self.name,
            "treasury_type": self.treasury_type.value,
            "signers": self.signers,
            "signer_threshold": self.signer_threshold,
            "registered_at": self.registered_at.isoformat(),
            "total_disputes": self.total_disputes,
            "resolved_disputes": self.resolved_disputes,
            "is_active": self.is_active,
        }


@dataclass
class TreasuryParticipant:
    """A treasury participating in a dispute."""

    treasury_id: str
    stake_amount: int = 0           # In wei
    voting_weight: int = 0
    has_staked: bool = False
    has_voted: bool = False
    vote: VoteChoice = VoteChoice.ABSTAIN
    escrowed_amount: int = 0        # Escrowed funds
    escrow_token: Optional[str] = None  # Token address or None for ETH

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "treasury_id": self.treasury_id,
            "stake_amount": self.stake_amount,
            "voting_weight": self.voting_weight,
            "has_staked": self.has_staked,
            "has_voted": self.has_voted,
            "vote": self.vote.value,
            "escrowed_amount": self.escrowed_amount,
            "escrow_token": self.escrow_token,
        }


@dataclass
class Proposal:
    """A resolution proposal."""

    proposal_id: int
    dispute_id: str
    proposer_treasury: str
    proposal_type: ProposalType
    content_hash: str               # IPFS hash
    ipfs_uri: str
    title: str
    description: str
    created_at: datetime
    support_weight: int = 0
    oppose_weight: int = 0
    payout_shares: List[int] = field(default_factory=list)  # Basis points
    executed: bool = False
    votes: Dict[str, VoteChoice] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "proposal_id": self.proposal_id,
            "dispute_id": self.dispute_id,
            "proposer_treasury": self.proposer_treasury,
            "proposal_type": self.proposal_type.value,
            "content_hash": self.content_hash,
            "ipfs_uri": self.ipfs_uri,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "support_weight": self.support_weight,
            "oppose_weight": self.oppose_weight,
            "payout_shares": self.payout_shares,
            "executed": self.executed,
            "vote_count": len(self.votes),
        }


@dataclass
class TreasuryDispute:
    """A multi-treasury dispute."""

    dispute_id: str
    creator_treasury: str
    involved_treasuries: List[str]
    title: str
    description_uri: str
    status: DisputeStatus
    created_at: datetime
    staking_deadline: datetime
    voting_deadline: Optional[datetime] = None
    total_stake: int = 0
    total_escrow: int = 0
    winning_proposal: Optional[int] = None
    is_binding: bool = False        # Advisory vs binding
    participants: Dict[str, TreasuryParticipant] = field(default_factory=dict)
    proposals: List[Proposal] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_staked(self) -> bool:
        """Check if all treasuries have staked."""
        return all(p.has_staked for p in self.participants.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dispute_id": self.dispute_id,
            "creator_treasury": self.creator_treasury,
            "involved_treasuries": self.involved_treasuries,
            "title": self.title,
            "description_uri": self.description_uri,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "staking_deadline": self.staking_deadline.isoformat(),
            "voting_deadline": self.voting_deadline.isoformat() if self.voting_deadline else None,
            "total_stake": self.total_stake,
            "total_escrow": self.total_escrow,
            "winning_proposal": self.winning_proposal,
            "is_binding": self.is_binding,
            "participants": {k: v.to_dict() for k, v in self.participants.items()},
            "proposal_count": len(self.proposals),
        }


class TreasuryCoordinator:
    """
    Multi-treasury coordination system.

    Manages the off-chain coordination for treasury disputes,
    working in conjunction with the TreasuryCoordinator smart contract.
    """

    PERCENTAGE_BASE = 10000  # Basis points
    MIN_STAKE = 10**16       # 0.01 ETH in wei
    CONSENSUS_THRESHOLD = 6666  # 66.66% in basis points

    def __init__(
        self,
        staking_period_days: int = 3,
        voting_period_days: int = 7,
    ):
        """
        Initialize the treasury coordinator.

        Args:
            staking_period_days: Days for staking period
            voting_period_days: Days for voting period
        """
        self.staking_period = timedelta(days=staking_period_days)
        self.voting_period = timedelta(days=voting_period_days)

        # Storage
        self._treasuries: Dict[str, Treasury] = {}
        self._disputes: Dict[str, TreasuryDispute] = {}
        self._signer_to_treasury: Dict[str, str] = {}

        # Callbacks
        self._on_dispute_created: Optional[Callable[[TreasuryDispute], None]] = None
        self._on_voting_started: Optional[Callable[[TreasuryDispute], None]] = None
        self._on_dispute_resolved: Optional[Callable[[TreasuryDispute], None]] = None

    # =========================================================================
    # Treasury Management
    # =========================================================================

    def register_treasury(
        self,
        name: str,
        treasury_type: TreasuryType,
        signers: List[str],
        signer_threshold: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Treasury:
        """
        Register a new treasury.

        Args:
            name: Treasury name
            treasury_type: Type of treasury
            signers: List of signer addresses
            signer_threshold: Required signatures
            metadata: Optional metadata

        Returns:
            Registered Treasury
        """
        if not signers:
            raise ValueError("At least one signer required")

        if signer_threshold < 1 or signer_threshold > len(signers):
            raise ValueError("Invalid signer threshold")

        treasury_id = hashlib.sha256(
            f"{name}:{secrets.token_hex(8)}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:24]

        treasury = Treasury(
            treasury_id=treasury_id,
            name=name,
            treasury_type=treasury_type,
            signers=[s.lower() for s in signers],
            signer_threshold=signer_threshold,
            registered_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        self._treasuries[treasury_id] = treasury

        # Map signers to treasury
        for signer in signers:
            signer_lower = signer.lower()
            if signer_lower not in self._signer_to_treasury:
                self._signer_to_treasury[signer_lower] = treasury_id

        return treasury

    def get_treasury(self, treasury_id: str) -> Optional[Treasury]:
        """Get a treasury by ID."""
        return self._treasuries.get(treasury_id)

    def get_treasury_by_signer(self, signer: str) -> Optional[Treasury]:
        """Get primary treasury for a signer."""
        treasury_id = self._signer_to_treasury.get(signer.lower())
        if treasury_id:
            return self._treasuries.get(treasury_id)
        return None

    def update_treasury_signers(
        self,
        treasury_id: str,
        new_signers: List[str],
        new_threshold: int,
        requester: str,
    ) -> bool:
        """
        Update treasury signers.

        Args:
            treasury_id: Treasury to update
            new_signers: New signer list
            new_threshold: New threshold
            requester: Address requesting update

        Returns:
            True if updated successfully
        """
        treasury = self._treasuries.get(treasury_id)
        if not treasury:
            return False

        if not treasury.is_signer(requester):
            return False

        if new_threshold < 1 or new_threshold > len(new_signers):
            return False

        treasury.signers = [s.lower() for s in new_signers]
        treasury.signer_threshold = new_threshold

        return True

    def deactivate_treasury(self, treasury_id: str, requester: str) -> bool:
        """Deactivate a treasury."""
        treasury = self._treasuries.get(treasury_id)
        if not treasury or not treasury.is_signer(requester):
            return False

        treasury.is_active = False
        return True

    # =========================================================================
    # Dispute Management
    # =========================================================================

    def create_dispute(
        self,
        creator_treasury: str,
        involved_treasuries: List[str],
        title: str,
        description_uri: str,
        creator_address: str,
        is_binding: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TreasuryDispute:
        """
        Create a new treasury dispute.

        Args:
            creator_treasury: Creator treasury ID
            involved_treasuries: Other involved treasury IDs
            title: Dispute title
            description_uri: IPFS URI for description
            creator_address: Address of creator
            is_binding: Whether resolution is binding
            metadata: Optional metadata

        Returns:
            Created TreasuryDispute
        """
        creator = self._treasuries.get(creator_treasury)
        if not creator or not creator.is_signer(creator_address):
            raise ValueError("Invalid creator or not authorized")

        if not creator.is_active:
            raise ValueError("Creator treasury not active")

        # Validate involved treasuries
        if len(involved_treasuries) < 1:
            raise ValueError("At least 2 treasuries required")

        all_treasury_ids = [creator_treasury] + involved_treasuries
        if len(all_treasury_ids) > 10:
            raise ValueError("Too many treasuries (max 10)")

        for tid in involved_treasuries:
            treasury = self._treasuries.get(tid)
            if not treasury or not treasury.is_active:
                raise ValueError(f"Invalid or inactive treasury: {tid}")

        dispute_id = hashlib.sha256(
            f"{creator_treasury}:{secrets.token_hex(8)}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:24]

        now = datetime.now(timezone.utc)

        # Initialize participants
        participants = {}
        for tid in all_treasury_ids:
            participants[tid] = TreasuryParticipant(treasury_id=tid)

        dispute = TreasuryDispute(
            dispute_id=dispute_id,
            creator_treasury=creator_treasury,
            involved_treasuries=all_treasury_ids,
            title=title,
            description_uri=description_uri,
            status=DisputeStatus.CREATED,
            created_at=now,
            staking_deadline=now + self.staking_period,
            is_binding=is_binding,
            participants=participants,
            metadata=metadata or {},
        )

        self._disputes[dispute_id] = dispute

        # Update treasury stats
        creator.total_disputes += 1

        if self._on_dispute_created:
            self._on_dispute_created(dispute)

        return dispute

    def get_dispute(self, dispute_id: str) -> Optional[TreasuryDispute]:
        """Get a dispute by ID."""
        return self._disputes.get(dispute_id)

    def stake(
        self,
        dispute_id: str,
        treasury_id: str,
        stake_amount: int,
        staker_address: str,
    ) -> bool:
        """
        Stake to participate in dispute.

        Args:
            dispute_id: Dispute ID
            treasury_id: Treasury staking
            stake_amount: Amount in wei
            staker_address: Address of staker

        Returns:
            True if stake successful
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return False

        if dispute.status != DisputeStatus.CREATED:
            return False

        if datetime.now(timezone.utc) > dispute.staking_deadline:
            return False

        treasury = self._treasuries.get(treasury_id)
        if not treasury or not treasury.is_signer(staker_address):
            return False

        if treasury_id not in dispute.participants:
            return False

        participant = dispute.participants[treasury_id]
        if participant.has_staked:
            return False

        if stake_amount < self.MIN_STAKE:
            return False

        participant.stake_amount = stake_amount
        participant.has_staked = True
        dispute.total_stake += stake_amount

        # Check if all treasuries have staked
        if dispute.all_staked:
            self._start_voting(dispute)

        return True

    def escrow_funds(
        self,
        dispute_id: str,
        treasury_id: str,
        amount: int,
        token: Optional[str],
        depositor: str,
    ) -> bool:
        """
        Escrow funds for the dispute.

        Args:
            dispute_id: Dispute ID
            treasury_id: Treasury escrowing
            amount: Amount to escrow
            token: Token address (None for ETH)
            depositor: Address depositing

        Returns:
            True if successful
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return False

        if dispute.status not in (
            DisputeStatus.CREATED,
            DisputeStatus.STAKING,
            DisputeStatus.VOTING,
        ):
            return False

        treasury = self._treasuries.get(treasury_id)
        if not treasury or not treasury.is_signer(depositor):
            return False

        participant = dispute.participants.get(treasury_id)
        if not participant:
            return False

        participant.escrowed_amount += amount
        participant.escrow_token = token
        dispute.total_escrow += amount

        return True

    def _start_voting(self, dispute: TreasuryDispute) -> None:
        """Start the voting phase."""
        dispute.status = DisputeStatus.VOTING
        dispute.voting_deadline = datetime.now(timezone.utc) + self.voting_period

        # Calculate voting weights (stake-based)
        for participant in dispute.participants.values():
            participant.voting_weight = participant.stake_amount

        if self._on_voting_started:
            self._on_voting_started(dispute)

    # =========================================================================
    # Proposals & Voting
    # =========================================================================

    def create_proposal(
        self,
        dispute_id: str,
        treasury_id: str,
        proposal_type: ProposalType,
        title: str,
        description: str,
        ipfs_uri: str,
        payout_shares: List[int],
        proposer_address: str,
    ) -> Optional[Proposal]:
        """
        Create a resolution proposal.

        Args:
            dispute_id: Dispute ID
            treasury_id: Proposer treasury
            proposal_type: Type of proposal
            title: Proposal title
            description: Proposal description
            ipfs_uri: IPFS URI for details
            payout_shares: Payout shares (basis points)
            proposer_address: Address of proposer

        Returns:
            Created Proposal or None
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return None

        if dispute.status != DisputeStatus.VOTING:
            return None

        if dispute.voting_deadline and datetime.now(timezone.utc) > dispute.voting_deadline:
            return None

        treasury = self._treasuries.get(treasury_id)
        if not treasury or not treasury.is_signer(proposer_address):
            return None

        participant = dispute.participants.get(treasury_id)
        if not participant or not participant.has_staked:
            return None

        # Validate payout shares
        if payout_shares:
            if len(payout_shares) != len(dispute.involved_treasuries):
                return None
            if sum(payout_shares) != self.PERCENTAGE_BASE:
                return None

        content_hash = hashlib.sha256(
            f"{title}:{description}:{ipfs_uri}".encode()
        ).hexdigest()[:32]

        proposal = Proposal(
            proposal_id=len(dispute.proposals),
            dispute_id=dispute_id,
            proposer_treasury=treasury_id,
            proposal_type=proposal_type,
            content_hash=content_hash,
            ipfs_uri=ipfs_uri,
            title=title,
            description=description,
            created_at=datetime.now(timezone.utc),
            payout_shares=payout_shares,
        )

        dispute.proposals.append(proposal)

        return proposal

    def vote(
        self,
        dispute_id: str,
        proposal_id: int,
        treasury_id: str,
        choice: VoteChoice,
        voter_address: str,
    ) -> bool:
        """
        Vote on a proposal.

        Args:
            dispute_id: Dispute ID
            proposal_id: Proposal ID
            treasury_id: Voting treasury
            choice: Vote choice
            voter_address: Address of voter

        Returns:
            True if vote recorded
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return False

        if dispute.status != DisputeStatus.VOTING:
            return False

        if dispute.voting_deadline and datetime.now(timezone.utc) > dispute.voting_deadline:
            return False

        treasury = self._treasuries.get(treasury_id)
        if not treasury or not treasury.is_signer(voter_address):
            return False

        if proposal_id >= len(dispute.proposals):
            return False

        proposal = dispute.proposals[proposal_id]

        if treasury_id in proposal.votes:
            return False  # Already voted

        participant = dispute.participants.get(treasury_id)
        if not participant or not participant.has_staked:
            return False

        # Record vote
        proposal.votes[treasury_id] = choice
        weight = participant.voting_weight

        if choice == VoteChoice.SUPPORT:
            proposal.support_weight += weight
        elif choice == VoteChoice.OPPOSE:
            proposal.oppose_weight += weight

        # Check for consensus (>66% support)
        if dispute.total_stake > 0:
            support_percentage = (proposal.support_weight * self.PERCENTAGE_BASE) // dispute.total_stake
            if support_percentage > self.CONSENSUS_THRESHOLD:
                self._resolve_dispute(dispute, proposal_id)

        return True

    # =========================================================================
    # Resolution
    # =========================================================================

    def finalize_voting(self, dispute_id: str) -> bool:
        """
        Finalize voting and resolve dispute.

        Args:
            dispute_id: Dispute ID

        Returns:
            True if finalized
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return False

        if dispute.status != DisputeStatus.VOTING:
            return False

        if dispute.voting_deadline and datetime.now(timezone.utc) < dispute.voting_deadline:
            return False

        # Find winning proposal
        winning_id = None
        highest_support = 0

        for i, proposal in enumerate(dispute.proposals):
            if proposal.support_weight > highest_support:
                if proposal.support_weight > proposal.oppose_weight:
                    highest_support = proposal.support_weight
                    winning_id = i

        if winning_id is not None:
            self._resolve_dispute(dispute, winning_id)
            return True
        else:
            dispute.status = DisputeStatus.EXPIRED
            return False

    def request_mediation(
        self,
        dispute_id: str,
        treasury_id: str,
        requester_address: str,
    ) -> bool:
        """
        Request mediation for a dispute.

        Args:
            dispute_id: Dispute ID
            treasury_id: Requesting treasury
            requester_address: Address of requester

        Returns:
            True if mediation requested
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return False

        if dispute.status not in (DisputeStatus.VOTING, DisputeStatus.EXPIRED):
            return False

        treasury = self._treasuries.get(treasury_id)
        if not treasury or not treasury.is_signer(requester_address):
            return False

        dispute.status = DisputeStatus.MEDIATION
        return True

    def mediator_resolve(
        self,
        dispute_id: str,
        proposal_id: int,
    ) -> bool:
        """
        Mediator resolves dispute.

        Args:
            dispute_id: Dispute ID
            proposal_id: Winning proposal ID

        Returns:
            True if resolved
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return False

        if dispute.status != DisputeStatus.MEDIATION:
            return False

        if proposal_id >= len(dispute.proposals):
            return False

        self._resolve_dispute(dispute, proposal_id)
        return True

    def _resolve_dispute(self, dispute: TreasuryDispute, winning_proposal: int) -> None:
        """Resolve a dispute with winning proposal."""
        dispute.status = DisputeStatus.RESOLVED
        dispute.winning_proposal = winning_proposal

        # Update treasury stats
        for tid in dispute.involved_treasuries:
            treasury = self._treasuries.get(tid)
            if treasury:
                treasury.resolved_disputes += 1

        if self._on_dispute_resolved:
            self._on_dispute_resolved(dispute)

    def execute_resolution(self, dispute_id: str) -> Optional[Dict[str, int]]:
        """
        Execute resolution and calculate fund distribution.

        Args:
            dispute_id: Dispute ID

        Returns:
            Distribution map (treasury_id -> amount) or None
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return None

        if dispute.status != DisputeStatus.RESOLVED:
            return None

        if dispute.winning_proposal is None:
            return None

        proposal = dispute.proposals[dispute.winning_proposal]
        if proposal.executed:
            return None

        if not proposal.payout_shares:
            return None

        proposal.executed = True
        dispute.status = DisputeStatus.EXECUTED

        # Calculate distribution
        distribution = {}
        for i, tid in enumerate(dispute.involved_treasuries):
            share = proposal.payout_shares[i]
            amount = (dispute.total_escrow * share) // self.PERCENTAGE_BASE
            distribution[tid] = amount

        return distribution

    def cancel_dispute(
        self,
        dispute_id: str,
        requester_address: str,
    ) -> bool:
        """
        Cancel a dispute (only creator before voting starts).

        Args:
            dispute_id: Dispute ID
            requester_address: Address of requester

        Returns:
            True if cancelled
        """
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            return False

        if dispute.status not in (DisputeStatus.CREATED, DisputeStatus.STAKING):
            return False

        creator_treasury = self._treasuries.get(dispute.creator_treasury)
        if not creator_treasury or not creator_treasury.is_signer(requester_address):
            return False

        dispute.status = DisputeStatus.CANCELLED
        return True

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_disputes_by_treasury(self, treasury_id: str) -> List[TreasuryDispute]:
        """Get all disputes involving a treasury."""
        return [
            d for d in self._disputes.values()
            if treasury_id in d.involved_treasuries
        ]

    def get_active_disputes(self) -> List[TreasuryDispute]:
        """Get all active disputes."""
        return [
            d for d in self._disputes.values()
            if d.status in (
                DisputeStatus.CREATED,
                DisputeStatus.STAKING,
                DisputeStatus.VOTING,
                DisputeStatus.MEDIATION,
            )
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        status_counts = {}
        for status in DisputeStatus:
            status_counts[status.value] = sum(
                1 for d in self._disputes.values() if d.status == status
            )

        return {
            "total_treasuries": len(self._treasuries),
            "active_treasuries": sum(1 for t in self._treasuries.values() if t.is_active),
            "total_disputes": len(self._disputes),
            "dispute_status_counts": status_counts,
            "total_staked": sum(d.total_stake for d in self._disputes.values()),
            "total_escrowed": sum(d.total_escrow for d in self._disputes.values()),
        }

    # =========================================================================
    # Callbacks
    # =========================================================================

    def set_on_dispute_created(
        self,
        callback: Callable[[TreasuryDispute], None],
    ) -> None:
        """Set callback for dispute creation."""
        self._on_dispute_created = callback

    def set_on_voting_started(
        self,
        callback: Callable[[TreasuryDispute], None],
    ) -> None:
        """Set callback for voting start."""
        self._on_voting_started = callback

    def set_on_dispute_resolved(
        self,
        callback: Callable[[TreasuryDispute], None],
    ) -> None:
        """Set callback for dispute resolution."""
        self._on_dispute_resolved = callback


def create_treasury_coordinator(
    staking_period_days: int = 3,
    voting_period_days: int = 7,
) -> TreasuryCoordinator:
    """
    Create a treasury coordinator.

    Args:
        staking_period_days: Days for staking period
        voting_period_days: Days for voting period

    Returns:
        Configured TreasuryCoordinator
    """
    return TreasuryCoordinator(
        staking_period_days=staking_period_days,
        voting_period_days=voting_period_days,
    )
