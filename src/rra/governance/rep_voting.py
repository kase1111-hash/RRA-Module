# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Reputation-Based Governance Voting.

Integrates reputation weights with governance proposals:
- Reputation-weighted voting power
- Proposal lifecycle with reputation tracking
- Consensus calculation with weighted votes
- Good-faith behavior incentives
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import json
import secrets

from rra.reputation.weighted import (
    ReputationManager,
    ReputationConfig,
    VotingPower,
    ReputationAction,
    create_reputation_manager,
)


class ProposalStatus(Enum):
    """Status of a governance proposal."""
    DRAFT = "draft"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class VoteChoice(Enum):
    """Voting options."""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclass
class WeightedVote:
    """A reputation-weighted vote."""
    voter_address: str
    choice: VoteChoice
    stake: int
    voting_power: VotingPower
    voted_at: datetime
    early_vote: bool = False  # Voted in first 25% of period
    reason: Optional[str] = None

    @property
    def effective_power(self) -> int:
        """Get effective voting power."""
        return self.voting_power.total_power

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voter_address": self.voter_address,
            "choice": self.choice.value,
            "stake": self.stake,
            "voting_power": self.voting_power.to_dict(),
            "voted_at": self.voted_at.isoformat(),
            "early_vote": self.early_vote,
            "reason": self.reason,
            "effective_power": self.effective_power,
        }


@dataclass
class RepWeightedProposal:
    """A reputation-weighted governance proposal."""
    proposal_id: str
    title: str
    description: str
    proposer_address: str
    status: ProposalStatus
    created_at: datetime
    voting_start: datetime
    voting_end: datetime
    executed_at: Optional[datetime] = None

    # Thresholds
    quorum_power: int = 0  # Minimum total power for quorum
    approval_threshold: float = 50.0  # % of power needed to pass

    # Proposal data
    data: Dict[str, Any] = field(default_factory=dict)

    # Votes
    votes: Dict[str, WeightedVote] = field(default_factory=dict)

    # Dispute reference (if any)
    dispute_id: Optional[str] = None

    @property
    def power_for(self) -> int:
        """Total power voting for."""
        return sum(
            v.effective_power for v in self.votes.values()
            if v.choice == VoteChoice.FOR
        )

    @property
    def power_against(self) -> int:
        """Total power voting against."""
        return sum(
            v.effective_power for v in self.votes.values()
            if v.choice == VoteChoice.AGAINST
        )

    @property
    def power_abstain(self) -> int:
        """Total power abstaining."""
        return sum(
            v.effective_power for v in self.votes.values()
            if v.choice == VoteChoice.ABSTAIN
        )

    @property
    def total_power(self) -> int:
        """Total power voted."""
        return sum(v.effective_power for v in self.votes.values())

    @property
    def voter_count(self) -> int:
        """Number of voters."""
        return len(self.votes)

    @property
    def early_voter_count(self) -> int:
        """Number of early voters."""
        return sum(1 for v in self.votes.values() if v.early_vote)

    @property
    def is_active(self) -> bool:
        """Check if voting is currently active."""
        now = datetime.now()
        return (
            self.status == ProposalStatus.ACTIVE and
            self.voting_start <= now <= self.voting_end
        )

    @property
    def early_voting_deadline(self) -> datetime:
        """Get deadline for early voting bonus."""
        duration = self.voting_end - self.voting_start
        return self.voting_start + (duration * 0.25)

    def get_result(self) -> Dict[str, Any]:
        """Calculate voting result."""
        quorum_met = self.total_power >= self.quorum_power

        # Calculate approval based on for vs against (not counting abstain)
        decisive_power = self.power_for + self.power_against
        approval_pct = (self.power_for / decisive_power * 100) if decisive_power > 0 else 0

        passed = quorum_met and approval_pct >= self.approval_threshold

        return {
            "power_for": self.power_for,
            "power_against": self.power_against,
            "power_abstain": self.power_abstain,
            "total_power": self.total_power,
            "voter_count": self.voter_count,
            "early_voter_count": self.early_voter_count,
            "quorum_power": self.quorum_power,
            "quorum_met": quorum_met,
            "approval_pct": approval_pct,
            "approval_threshold": self.approval_threshold,
            "passed": passed,
        }

    def to_dict(self) -> Dict[str, Any]:
        result = self.get_result()
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "proposer_address": self.proposer_address,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "voting_start": self.voting_start.isoformat(),
            "voting_end": self.voting_end.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "quorum_power": self.quorum_power,
            "approval_threshold": self.approval_threshold,
            "data": self.data,
            "votes": {addr: v.to_dict() for addr, v in self.votes.items()},
            "dispute_id": self.dispute_id,
            **result,
        }


class RepWeightedGovernance:
    """
    Reputation-weighted governance system.

    Integrates with ReputationManager for weighted voting power.
    """

    def __init__(
        self,
        reputation_manager: Optional[ReputationManager] = None,
        data_dir: Optional[Path] = None,
        voting_period_hours: int = 72,
        quorum_percentage: float = 20.0,
        approval_threshold: float = 50.0,
    ):
        self.reputation_manager = reputation_manager or create_reputation_manager()
        self.data_dir = data_dir
        self.voting_period_hours = voting_period_hours
        self.quorum_percentage = quorum_percentage
        self.approval_threshold = approval_threshold

        # State
        self.proposals: Dict[str, RepWeightedProposal] = {}
        self.dispute_proposals: Dict[str, List[str]] = {}
        self.participant_stakes: Dict[str, int] = {}  # For tracking stakes
        self.total_staked: int = 0

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    # =========================================================================
    # Stake Management
    # =========================================================================

    def register_stake(self, address: str, stake: int) -> int:
        """Register or update stake for a participant."""
        address = address.lower()
        old_stake = self.participant_stakes.get(address, 0)
        self.participant_stakes[address] = stake
        self.total_staked = self.total_staked - old_stake + stake
        self._save_state()
        return stake

    def get_stake(self, address: str) -> int:
        """Get stake for address."""
        return self.participant_stakes.get(address.lower(), 0)

    # =========================================================================
    # Proposal Management
    # =========================================================================

    def create_proposal(
        self,
        title: str,
        description: str,
        proposer_address: str,
        data: Optional[Dict[str, Any]] = None,
        dispute_id: Optional[str] = None,
        voting_delay_hours: int = 24,
        custom_voting_period_hours: Optional[int] = None,
    ) -> RepWeightedProposal:
        """
        Create a new governance proposal.

        Args:
            title: Proposal title
            description: Proposal description
            proposer_address: Address of proposer
            data: Additional proposal data
            dispute_id: Related dispute ID (optional)
            voting_delay_hours: Delay before voting starts
            custom_voting_period_hours: Override default voting period

        Returns:
            Created proposal
        """
        proposer_address = proposer_address.lower()

        # Ensure proposer has reputation
        self.reputation_manager.get_or_create_participant(proposer_address)

        now = datetime.now()
        voting_period = custom_voting_period_hours or self.voting_period_hours

        # Calculate quorum based on total staked
        quorum_power = int(self.total_staked * self.quorum_percentage / 100)

        proposal = RepWeightedProposal(
            proposal_id=self._generate_id("rprop_"),
            title=title,
            description=description,
            proposer_address=proposer_address,
            status=ProposalStatus.ACTIVE,
            created_at=now,
            voting_start=now + timedelta(hours=voting_delay_hours),
            voting_end=now + timedelta(hours=voting_delay_hours + voting_period),
            quorum_power=quorum_power,
            approval_threshold=self.approval_threshold,
            data=data or {},
            dispute_id=dispute_id,
        )

        self.proposals[proposal.proposal_id] = proposal

        # Track proposal for dispute
        if dispute_id:
            if dispute_id not in self.dispute_proposals:
                self.dispute_proposals[dispute_id] = []
            self.dispute_proposals[dispute_id].append(proposal.proposal_id)

        # Record proposer activity
        self.reputation_manager.get_or_create_participant(proposer_address)

        self._save_state()
        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[RepWeightedProposal]:
        """Get proposal by ID."""
        return self.proposals.get(proposal_id)

    def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
        dispute_id: Optional[str] = None,
        proposer: Optional[str] = None,
        limit: int = 50,
    ) -> List[RepWeightedProposal]:
        """List proposals with filters."""
        proposals = list(self.proposals.values())

        if status:
            proposals = [p for p in proposals if p.status == status]
        if dispute_id:
            proposals = [p for p in proposals if p.dispute_id == dispute_id]
        if proposer:
            proposals = [p for p in proposals if p.proposer_address == proposer.lower()]

        proposals.sort(key=lambda p: p.created_at, reverse=True)
        return proposals[:limit]

    # =========================================================================
    # Voting
    # =========================================================================

    def vote(
        self,
        proposal_id: str,
        voter_address: str,
        choice: VoteChoice,
        stake: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Optional[WeightedVote]:
        """
        Cast a reputation-weighted vote.

        Args:
            proposal_id: Proposal to vote on
            voter_address: Voter's address
            choice: Vote choice
            stake: Override stake amount (uses registered stake if not provided)
            reason: Optional reason for vote

        Returns:
            WeightedVote or None if failed
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal or not proposal.is_active:
            return None

        voter_address = voter_address.lower()

        # Get stake
        voter_stake = stake if stake is not None else self.get_stake(voter_address)
        if voter_stake <= 0:
            return None

        # Calculate voting power
        voting_power = self.reputation_manager.calculate_voting_power(
            voter_address, voter_stake
        )

        # Check if early vote
        now = datetime.now()
        is_early = now <= proposal.early_voting_deadline

        # Create vote
        vote = WeightedVote(
            voter_address=voter_address,
            choice=choice,
            stake=voter_stake,
            voting_power=voting_power,
            voted_at=now,
            early_vote=is_early,
            reason=reason,
        )

        # Record vote
        proposal.votes[voter_address] = vote

        # Update reputation based on voting behavior
        if is_early:
            self.reputation_manager.record_early_voting(
                voter_address, proposal.dispute_id or proposal.proposal_id
            )
        elif now > proposal.voting_end - timedelta(hours=1):
            # Last-minute voting penalty
            self.reputation_manager.record_late_voting(
                voter_address, proposal.dispute_id or proposal.proposal_id
            )

        self._save_state()
        return vote

    def has_voted(self, proposal_id: str, voter_address: str) -> bool:
        """Check if address has voted on proposal."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False
        return voter_address.lower() in proposal.votes

    def get_vote(
        self, proposal_id: str, voter_address: str
    ) -> Optional[WeightedVote]:
        """Get vote for a proposal by address."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None
        return proposal.votes.get(voter_address.lower())

    # =========================================================================
    # Finalization
    # =========================================================================

    def finalize_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        Finalize voting on a proposal.

        Updates proposal status and participant reputations.
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        if proposal.status != ProposalStatus.ACTIVE:
            return {"error": f"Proposal not active: {proposal.status.value}"}

        if datetime.now() < proposal.voting_end:
            return {"error": "Voting period not ended"}

        result = proposal.get_result()

        if result["passed"]:
            proposal.status = ProposalStatus.PASSED

            # Update proposer reputation
            self.reputation_manager.record_proposal_outcome(
                proposal.proposer_address,
                proposal.dispute_id or proposal.proposal_id,
                accepted=True,
            )

            # Update voter reputations
            for vote in proposal.votes.values():
                if vote.choice == VoteChoice.FOR:
                    self.reputation_manager.update_reputation(
                        vote.voter_address,
                        ReputationAction.CONSENSUS_ALIGNMENT,
                        dispute_id=proposal.dispute_id,
                        reason="Voted with winning side",
                    )
        else:
            proposal.status = ProposalStatus.REJECTED

            # Update proposer reputation
            self.reputation_manager.record_proposal_outcome(
                proposal.proposer_address,
                proposal.dispute_id or proposal.proposal_id,
                accepted=False,
            )

        self._save_state()

        return {
            "proposal_id": proposal_id,
            "status": proposal.status.value,
            **result,
        }

    def execute_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Mark proposal as executed."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        if proposal.status != ProposalStatus.PASSED:
            return {"error": f"Proposal not passed: {proposal.status.value}"}

        proposal.status = ProposalStatus.EXECUTED
        proposal.executed_at = datetime.now()

        self._save_state()

        return {
            "proposal_id": proposal_id,
            "status": proposal.status.value,
            "executed_at": proposal.executed_at.isoformat(),
        }

    def expire_proposals(self) -> List[str]:
        """Expire proposals that passed voting end without finalization."""
        expired = []
        now = datetime.now()

        for proposal in self.proposals.values():
            if proposal.status == ProposalStatus.ACTIVE and now > proposal.voting_end:
                proposal.status = ProposalStatus.EXPIRED
                expired.append(proposal.proposal_id)

        if expired:
            self._save_state()

        return expired

    # =========================================================================
    # Dispute Integration
    # =========================================================================

    def get_dispute_proposals(self, dispute_id: str) -> List[RepWeightedProposal]:
        """Get all proposals for a dispute."""
        proposal_ids = self.dispute_proposals.get(dispute_id, [])
        return [
            self.proposals[pid] for pid in proposal_ids
            if pid in self.proposals
        ]

    def record_dispute_resolution(
        self,
        dispute_id: str,
        winning_proposal_id: Optional[str] = None,
    ) -> None:
        """
        Record dispute resolution and update reputations.

        Args:
            dispute_id: Resolved dispute ID
            winning_proposal_id: Proposal that won (if any)
        """
        proposals = self.get_dispute_proposals(dispute_id)
        if not proposals:
            return

        # Collect winners (voted for winning proposal) and losers
        winners = []
        losers = []

        for proposal in proposals:
            if proposal.proposal_id == winning_proposal_id:
                # This proposal won
                winners.extend([
                    v.voter_address for v in proposal.votes.values()
                    if v.choice == VoteChoice.FOR
                ])
                losers.extend([
                    v.voter_address for v in proposal.votes.values()
                    if v.choice == VoteChoice.AGAINST
                ])
            else:
                # This proposal lost
                losers.extend([
                    v.voter_address for v in proposal.votes.values()
                    if v.choice == VoteChoice.FOR
                ])

        # Update reputations
        if winners or losers:
            self.reputation_manager.record_dispute_resolution(
                dispute_id, winners, losers
            )

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_voter_stats(self, address: str) -> Dict[str, Any]:
        """Get voting statistics for an address."""
        address = address.lower()

        proposals_voted = [
            p for p in self.proposals.values()
            if address in p.votes
        ]

        if not proposals_voted:
            return {
                "address": address,
                "proposals_voted": 0,
                "total_power_used": 0,
            }

        total_power = sum(
            p.votes[address].effective_power
            for p in proposals_voted
        )

        early_votes = sum(
            1 for p in proposals_voted
            if p.votes[address].early_vote
        )

        winning_votes = sum(
            1 for p in proposals_voted
            if (
                p.status == ProposalStatus.PASSED and
                p.votes[address].choice == VoteChoice.FOR
            ) or (
                p.status == ProposalStatus.REJECTED and
                p.votes[address].choice == VoteChoice.AGAINST
            )
        )

        return {
            "address": address,
            "proposals_voted": len(proposals_voted),
            "total_power_used": total_power,
            "early_votes": early_votes,
            "early_vote_rate": early_votes / len(proposals_voted) if proposals_voted else 0,
            "winning_votes": winning_votes,
            "win_rate": winning_votes / len(proposals_voted) if proposals_voted else 0,
        }

    def get_governance_stats(self) -> Dict[str, Any]:
        """Get overall governance statistics."""
        proposals = list(self.proposals.values())

        return {
            "total_proposals": len(proposals),
            "active": len([p for p in proposals if p.status == ProposalStatus.ACTIVE]),
            "passed": len([p for p in proposals if p.status == ProposalStatus.PASSED]),
            "rejected": len([p for p in proposals if p.status == ProposalStatus.REJECTED]),
            "executed": len([p for p in proposals if p.status == ProposalStatus.EXECUTED]),
            "total_staked": self.total_staked,
            "unique_voters": len(set(
                addr for p in proposals
                for addr in p.votes.keys()
            )),
            "avg_participation": (
                sum(len(p.votes) for p in proposals) / len(proposals)
                if proposals else 0
            ),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "proposals": {pid: p.to_dict() for pid, p in self.proposals.items()},
            "dispute_proposals": self.dispute_proposals,
            "participant_stakes": self.participant_stakes,
            "total_staked": self.total_staked,
            "config": {
                "voting_period_hours": self.voting_period_hours,
                "quorum_percentage": self.quorum_percentage,
                "approval_threshold": self.approval_threshold,
            },
        }

        state_file = self.data_dir / "rep_governance_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        if not self.data_dir:
            return

        state_file = self.data_dir / "rep_governance_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            # Restore proposals (simplified for brevity)
            self.dispute_proposals = state.get("dispute_proposals", {})
            self.participant_stakes = state.get("participant_stakes", {})
            self.total_staked = state.get("total_staked", 0)

            config = state.get("config", {})
            self.voting_period_hours = config.get("voting_period_hours", 72)
            self.quorum_percentage = config.get("quorum_percentage", 20.0)
            self.approval_threshold = config.get("approval_threshold", 50.0)

        except (json.JSONDecodeError, KeyError):
            pass


def create_rep_weighted_governance(
    data_dir: Optional[str] = None,
    reputation_manager: Optional[ReputationManager] = None,
    voting_period_hours: int = 72,
    quorum_percentage: float = 20.0,
    approval_threshold: float = 50.0,
) -> RepWeightedGovernance:
    """Factory function to create reputation-weighted governance."""
    path = Path(data_dir) if data_dir else None
    return RepWeightedGovernance(
        reputation_manager=reputation_manager,
        data_dir=path,
        voting_period_hours=voting_period_hours,
        quorum_percentage=quorum_percentage,
        approval_threshold=approval_threshold,
    )
