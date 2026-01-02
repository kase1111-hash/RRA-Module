# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Treasury Voting for Multi-Treasury Dispute Resolution.

Provides specialized voting mechanisms for treasury coordination:
- Stake-weighted voting for dispute resolution
- Treasury signer consensus
- Fund allocation decisions
- Mediation escalation voting
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import secrets


class TreasuryVoteType(Enum):
    """Types of treasury votes."""

    RESOLUTION = "resolution"  # Vote on dispute resolution
    FUND_ALLOCATION = "fund_allocation"  # Vote on fund distribution
    MEDIATION = "mediation"  # Vote to escalate to mediation
    SETTLEMENT = "settlement"  # Vote on settlement offer
    EMERGENCY = "emergency"  # Emergency action vote


class TreasuryVoteStatus(Enum):
    """Status of a treasury vote."""

    PENDING = "pending"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class VoteChoice(Enum):
    """Voting options."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass
class TreasuryVote:
    """A vote cast by a treasury or signer."""

    voter_id: str  # Treasury ID or signer address
    voter_type: str  # "treasury" or "signer"
    stake_weight: int
    choice: VoteChoice
    voted_at: datetime
    signature: Optional[str] = None  # Cryptographic signature
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voter_id": self.voter_id,
            "voter_type": self.voter_type,
            "stake_weight": self.stake_weight,
            "choice": self.choice.value,
            "voted_at": self.voted_at.isoformat(),
            "signature": self.signature,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreasuryVote":
        return cls(
            voter_id=data["voter_id"],
            voter_type=data["voter_type"],
            stake_weight=data["stake_weight"],
            choice=VoteChoice(data["choice"]),
            voted_at=datetime.fromisoformat(data["voted_at"]),
            signature=data.get("signature"),
            reason=data.get("reason"),
        )


@dataclass
class TreasuryProposal:
    """A proposal for treasury decision."""

    proposal_id: str
    dispute_id: str
    treasury_id: str  # Proposing treasury
    vote_type: TreasuryVoteType
    title: str
    description: str
    ipfs_uri: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    voting_start: datetime = field(default_factory=datetime.now)
    voting_end: Optional[datetime] = None
    executed_at: Optional[datetime] = None

    # Status
    status: TreasuryVoteStatus = TreasuryVoteStatus.PENDING

    # Thresholds
    quorum_stake: int = 0  # Minimum stake required
    approval_threshold: float = 50.0  # % of stake needed

    # Proposal data (e.g., payout shares, settlement terms)
    data: Dict[str, Any] = field(default_factory=dict)

    # Votes by voter_id
    _votes: Dict[str, TreasuryVote] = field(default_factory=dict)

    @property
    def total_stake_voted(self) -> int:
        return sum(v.stake_weight for v in self._votes.values())

    @property
    def stake_approved(self) -> int:
        return sum(v.stake_weight for v in self._votes.values() if v.choice == VoteChoice.APPROVE)

    @property
    def stake_rejected(self) -> int:
        return sum(v.stake_weight for v in self._votes.values() if v.choice == VoteChoice.REJECT)

    @property
    def stake_abstained(self) -> int:
        return sum(v.stake_weight for v in self._votes.values() if v.choice == VoteChoice.ABSTAIN)

    @property
    def voter_count(self) -> int:
        return len(self._votes)

    @property
    def is_active(self) -> bool:
        now = datetime.now()
        if self.status != TreasuryVoteStatus.ACTIVE:
            return False
        if now < self.voting_start:
            return False
        if self.voting_end and now > self.voting_end:
            return False
        return True

    def add_vote(self, vote: TreasuryVote) -> bool:
        """Add a vote to this proposal."""
        if not self.is_active:
            return False
        self._votes[vote.voter_id] = vote
        return True

    def get_vote(self, voter_id: str) -> Optional[TreasuryVote]:
        return self._votes.get(voter_id)

    def calculate_result(self, total_stake: int) -> Dict[str, Any]:
        """Calculate voting result."""
        quorum_met = self.total_stake_voted >= self.quorum_stake

        # Calculate approval based on approve vs reject (not counting abstain)
        decisive_stake = self.stake_approved + self.stake_rejected
        approval_pct = (self.stake_approved / decisive_stake * 100) if decisive_stake > 0 else 0

        passed = quorum_met and approval_pct >= self.approval_threshold

        return {
            "stake_approved": self.stake_approved,
            "stake_rejected": self.stake_rejected,
            "stake_abstained": self.stake_abstained,
            "total_stake_voted": self.total_stake_voted,
            "total_stake": total_stake,
            "participation_pct": (
                (self.total_stake_voted / total_stake * 100) if total_stake > 0 else 0
            ),
            "voter_count": self.voter_count,
            "quorum_stake": self.quorum_stake,
            "quorum_met": quorum_met,
            "approval_pct": approval_pct,
            "approval_threshold": self.approval_threshold,
            "passed": passed,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "dispute_id": self.dispute_id,
            "treasury_id": self.treasury_id,
            "vote_type": self.vote_type.value,
            "title": self.title,
            "description": self.description,
            "ipfs_uri": self.ipfs_uri,
            "created_at": self.created_at.isoformat(),
            "voting_start": self.voting_start.isoformat(),
            "voting_end": self.voting_end.isoformat() if self.voting_end else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "status": self.status.value,
            "quorum_stake": self.quorum_stake,
            "approval_threshold": self.approval_threshold,
            "data": self.data,
            "votes": {vid: v.to_dict() for vid, v in self._votes.items()},
            "stake_approved": self.stake_approved,
            "stake_rejected": self.stake_rejected,
            "stake_abstained": self.stake_abstained,
            "total_stake_voted": self.total_stake_voted,
            "voter_count": self.voter_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreasuryProposal":
        proposal = cls(
            proposal_id=data["proposal_id"],
            dispute_id=data["dispute_id"],
            treasury_id=data["treasury_id"],
            vote_type=TreasuryVoteType(data["vote_type"]),
            title=data["title"],
            description=data["description"],
            ipfs_uri=data.get("ipfs_uri"),
            created_at=datetime.fromisoformat(data["created_at"]),
            voting_start=datetime.fromisoformat(data["voting_start"]),
            status=TreasuryVoteStatus(data["status"]),
            quorum_stake=data.get("quorum_stake", 0),
            approval_threshold=data.get("approval_threshold", 50.0),
            data=data.get("data", {}),
        )

        if data.get("voting_end"):
            proposal.voting_end = datetime.fromisoformat(data["voting_end"])
        if data.get("executed_at"):
            proposal.executed_at = datetime.fromisoformat(data["executed_at"])

        for vid, vote_data in data.get("votes", {}).items():
            proposal._votes[vid] = TreasuryVote.from_dict(vote_data)

        return proposal


@dataclass
class TreasurySigner:
    """A signer authorized for a treasury."""

    address: str
    weight: int = 1
    added_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "weight": self.weight,
            "added_at": self.added_at.isoformat(),
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreasurySigner":
        return cls(
            address=data["address"],
            weight=data.get("weight", 1),
            added_at=datetime.fromisoformat(data["added_at"]),
            is_active=data.get("is_active", True),
        )


@dataclass
class VotingTreasury:
    """A treasury participating in voting."""

    treasury_id: str
    name: str
    stake: int = 0
    signers: List[TreasurySigner] = field(default_factory=list)
    signer_threshold: int = 1  # Required signer weight to authorize vote

    @property
    def total_signer_weight(self) -> int:
        return sum(s.weight for s in self.signers if s.is_active)

    def add_signer(self, address: str, weight: int = 1) -> TreasurySigner:
        """Add a signer to the treasury."""
        signer = TreasurySigner(address=address.lower(), weight=weight)
        self.signers.append(signer)
        return signer

    def remove_signer(self, address: str) -> bool:
        """Deactivate a signer."""
        for signer in self.signers:
            if signer.address == address.lower():
                signer.is_active = False
                return True
        return False

    def is_authorized_signer(self, address: str) -> bool:
        """Check if address is an active signer."""
        return any(s.address == address.lower() and s.is_active for s in self.signers)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "treasury_id": self.treasury_id,
            "name": self.name,
            "stake": self.stake,
            "signers": [s.to_dict() for s in self.signers],
            "signer_threshold": self.signer_threshold,
            "total_signer_weight": self.total_signer_weight,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VotingTreasury":
        treasury = cls(
            treasury_id=data["treasury_id"],
            name=data["name"],
            stake=data.get("stake", 0),
            signer_threshold=data.get("signer_threshold", 1),
        )
        treasury.signers = [TreasurySigner.from_dict(s) for s in data.get("signers", [])]
        return treasury


class TreasuryVotingManager:
    """Manages treasury voting for dispute resolution."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        voting_period_hours: int = 72,
        quorum_percentage: float = 50.0,
        approval_threshold: float = 50.0,
    ):
        self.data_dir = data_dir
        self.voting_period_hours = voting_period_hours
        self.quorum_percentage = quorum_percentage
        self.approval_threshold = approval_threshold

        # State
        self.treasuries: Dict[str, VotingTreasury] = {}
        self.proposals: Dict[str, TreasuryProposal] = {}
        self.dispute_stakes: Dict[str, Dict[str, int]] = {}  # dispute_id -> treasury_id -> stake

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    # =========================================================================
    # Treasury Management
    # =========================================================================

    def register_treasury(
        self,
        name: str,
        signers: List[str],
        signer_threshold: int = 1,
    ) -> VotingTreasury:
        """Register a treasury for voting."""
        treasury = VotingTreasury(
            treasury_id=self._generate_id("trs_"),
            name=name,
            signer_threshold=signer_threshold,
        )

        for signer_addr in signers:
            treasury.add_signer(signer_addr)

        self.treasuries[treasury.treasury_id] = treasury
        self._save_state()

        return treasury

    def get_treasury(self, treasury_id: str) -> Optional[VotingTreasury]:
        return self.treasuries.get(treasury_id)

    def add_treasury_signer(
        self,
        treasury_id: str,
        address: str,
        weight: int = 1,
    ) -> Optional[TreasurySigner]:
        """Add a signer to a treasury."""
        treasury = self.treasuries.get(treasury_id)
        if not treasury:
            return None

        signer = treasury.add_signer(address, weight)
        self._save_state()
        return signer

    # =========================================================================
    # Stake Management
    # =========================================================================

    def stake_for_dispute(
        self,
        dispute_id: str,
        treasury_id: str,
        amount: int,
    ) -> int:
        """Stake funds for a dispute."""
        if dispute_id not in self.dispute_stakes:
            self.dispute_stakes[dispute_id] = {}

        current = self.dispute_stakes[dispute_id].get(treasury_id, 0)
        self.dispute_stakes[dispute_id][treasury_id] = current + amount

        # Update treasury total stake
        treasury = self.treasuries.get(treasury_id)
        if treasury:
            treasury.stake += amount

        self._save_state()
        return self.dispute_stakes[dispute_id][treasury_id]

    def get_dispute_stakes(self, dispute_id: str) -> Dict[str, int]:
        """Get stakes for a dispute."""
        return self.dispute_stakes.get(dispute_id, {})

    def get_total_stake(self, dispute_id: str) -> int:
        """Get total stake for a dispute."""
        stakes = self.dispute_stakes.get(dispute_id, {})
        return sum(stakes.values())

    # =========================================================================
    # Proposal Management
    # =========================================================================

    def create_proposal(
        self,
        dispute_id: str,
        treasury_id: str,
        proposer_address: str,
        vote_type: TreasuryVoteType,
        title: str,
        description: str,
        ipfs_uri: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        voting_delay_hours: int = 0,
    ) -> Optional[TreasuryProposal]:
        """Create a proposal for treasury vote."""
        treasury = self.treasuries.get(treasury_id)
        if not treasury:
            return None

        # Verify proposer is authorized signer
        if not treasury.is_authorized_signer(proposer_address):
            return None

        # Calculate quorum based on total dispute stake
        total_stake = self.get_total_stake(dispute_id)
        quorum_stake = int(total_stake * self.quorum_percentage / 100)

        now = datetime.now()
        proposal = TreasuryProposal(
            proposal_id=self._generate_id("tprop_"),
            dispute_id=dispute_id,
            treasury_id=treasury_id,
            vote_type=vote_type,
            title=title,
            description=description,
            ipfs_uri=ipfs_uri,
            created_at=now,
            voting_start=now + timedelta(hours=voting_delay_hours),
            voting_end=now + timedelta(hours=voting_delay_hours + self.voting_period_hours),
            status=TreasuryVoteStatus.ACTIVE,
            quorum_stake=quorum_stake,
            approval_threshold=self.approval_threshold,
            data=data or {},
        )

        self.proposals[proposal.proposal_id] = proposal
        self._save_state()

        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[TreasuryProposal]:
        return self.proposals.get(proposal_id)

    def list_proposals(
        self,
        dispute_id: Optional[str] = None,
        treasury_id: Optional[str] = None,
        status: Optional[TreasuryVoteStatus] = None,
    ) -> List[TreasuryProposal]:
        """List proposals with filters."""
        proposals = list(self.proposals.values())

        if dispute_id:
            proposals = [p for p in proposals if p.dispute_id == dispute_id]
        if treasury_id:
            proposals = [p for p in proposals if p.treasury_id == treasury_id]
        if status:
            proposals = [p for p in proposals if p.status == status]

        return sorted(proposals, key=lambda p: p.created_at, reverse=True)

    # =========================================================================
    # Voting
    # =========================================================================

    def vote(
        self,
        proposal_id: str,
        treasury_id: str,
        voter_address: str,
        choice: VoteChoice,
        signature: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[TreasuryVote]:
        """Cast a vote on a proposal."""
        proposal = self.proposals.get(proposal_id)
        if not proposal or not proposal.is_active:
            return None

        treasury = self.treasuries.get(treasury_id)
        if not treasury:
            return None

        # Verify voter is authorized signer
        if not treasury.is_authorized_signer(voter_address):
            return None

        # Get treasury stake for this dispute
        stake = self.dispute_stakes.get(proposal.dispute_id, {}).get(treasury_id, 0)
        if stake <= 0:
            return None  # No stake, no vote

        vote = TreasuryVote(
            voter_id=treasury_id,
            voter_type="treasury",
            stake_weight=stake,
            choice=choice,
            voted_at=datetime.now(),
            signature=signature,
            reason=reason,
        )

        if proposal.add_vote(vote):
            self._save_state()
            return vote

        return None

    def vote_as_signer(
        self,
        proposal_id: str,
        treasury_id: str,
        signer_address: str,
        choice: VoteChoice,
        signature: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[TreasuryVote]:
        """
        Cast a signer-level vote (for internal treasury consensus).

        This allows individual signers to vote within a treasury,
        enabling multi-sig style voting before committing the treasury's vote.
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        treasury = self.treasuries.get(treasury_id)
        if not treasury:
            return None

        # Find signer
        signer = None
        for s in treasury.signers:
            if s.address == signer_address.lower() and s.is_active:
                signer = s
                break

        if not signer:
            return None

        # Signer vote uses their weight
        vote = TreasuryVote(
            voter_id=f"{treasury_id}:{signer_address.lower()}",
            voter_type="signer",
            stake_weight=signer.weight,
            choice=choice,
            voted_at=datetime.now(),
            signature=signature,
            reason=reason,
        )

        # Store separately for signer consensus tracking
        # This doesn't directly affect proposal outcome
        if proposal.add_vote(vote):
            self._save_state()
            return vote

        return None

    def check_signer_consensus(
        self,
        proposal_id: str,
        treasury_id: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if signers have reached consensus for a treasury's vote.

        Returns (consensus_reached, details).
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return False, {"error": "Proposal not found"}

        treasury = self.treasuries.get(treasury_id)
        if not treasury:
            return False, {"error": "Treasury not found"}

        # Collect signer votes for this treasury
        prefix = f"{treasury_id}:"
        signer_votes = {
            vid: v
            for vid, v in proposal._votes.items()
            if vid.startswith(prefix) and v.voter_type == "signer"
        }

        # Calculate weighted votes by choice
        approve_weight = sum(
            v.stake_weight for v in signer_votes.values() if v.choice == VoteChoice.APPROVE
        )
        reject_weight = sum(
            v.stake_weight for v in signer_votes.values() if v.choice == VoteChoice.REJECT
        )
        total_weight = sum(v.stake_weight for v in signer_votes.values())

        # Check threshold
        consensus_reached = approve_weight >= treasury.signer_threshold
        majority_choice = (
            VoteChoice.APPROVE if approve_weight > reject_weight else VoteChoice.REJECT
        )

        return consensus_reached, {
            "treasury_id": treasury_id,
            "signer_count": len(signer_votes),
            "approve_weight": approve_weight,
            "reject_weight": reject_weight,
            "total_weight": total_weight,
            "threshold": treasury.signer_threshold,
            "consensus_reached": consensus_reached,
            "majority_choice": majority_choice.value,
        }

    # =========================================================================
    # Finalization
    # =========================================================================

    def finalize_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Finalize voting on a proposal."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        if proposal.status != TreasuryVoteStatus.ACTIVE:
            return {"error": f"Proposal not active: {proposal.status.value}"}

        # Check if voting period ended
        now = datetime.now()
        if proposal.voting_end and now < proposal.voting_end:
            return {"error": "Voting period not ended"}

        total_stake = self.get_total_stake(proposal.dispute_id)
        result = proposal.calculate_result(total_stake)

        if result["passed"]:
            proposal.status = TreasuryVoteStatus.PASSED
        else:
            proposal.status = TreasuryVoteStatus.REJECTED

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

        if proposal.status != TreasuryVoteStatus.PASSED:
            return {"error": f"Proposal not passed: {proposal.status.value}"}

        proposal.status = TreasuryVoteStatus.EXECUTED
        proposal.executed_at = datetime.now()

        self._save_state()

        return {
            "proposal_id": proposal_id,
            "status": proposal.status.value,
            "executed_at": proposal.executed_at.isoformat(),
            "data": proposal.data,
        }

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_voting_stats(self, dispute_id: str) -> Dict[str, Any]:
        """Get voting statistics for a dispute."""
        proposals = [p for p in self.proposals.values() if p.dispute_id == dispute_id]
        stakes = self.get_dispute_stakes(dispute_id)

        return {
            "dispute_id": dispute_id,
            "total_stake": sum(stakes.values()),
            "treasury_count": len(stakes),
            "stakes_by_treasury": stakes,
            "proposal_count": len(proposals),
            "active_proposals": len(
                [p for p in proposals if p.status == TreasuryVoteStatus.ACTIVE]
            ),
            "passed_proposals": len(
                [p for p in proposals if p.status == TreasuryVoteStatus.PASSED]
            ),
            "executed_proposals": len(
                [p for p in proposals if p.status == TreasuryVoteStatus.EXECUTED]
            ),
        }

    def get_treasury_voting_history(
        self,
        treasury_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get voting history for a treasury."""
        history = []

        for proposal in self.proposals.values():
            vote = proposal.get_vote(treasury_id)
            if vote:
                history.append(
                    {
                        "proposal_id": proposal.proposal_id,
                        "dispute_id": proposal.dispute_id,
                        "vote_type": proposal.vote_type.value,
                        "title": proposal.title,
                        "status": proposal.status.value,
                        "choice": vote.choice.value,
                        "stake_weight": vote.stake_weight,
                        "voted_at": vote.voted_at.isoformat(),
                    }
                )

        # Sort by vote time, most recent first
        history.sort(key=lambda x: x["voted_at"], reverse=True)
        return history[:limit]

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "treasuries": {tid: t.to_dict() for tid, t in self.treasuries.items()},
            "proposals": {pid: p.to_dict() for pid, p in self.proposals.items()},
            "dispute_stakes": self.dispute_stakes,
            "config": {
                "voting_period_hours": self.voting_period_hours,
                "quorum_percentage": self.quorum_percentage,
                "approval_threshold": self.approval_threshold,
            },
        }

        state_file = self.data_dir / "treasury_votes_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        if not self.data_dir:
            return

        state_file = self.data_dir / "treasury_votes_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.treasuries = {
                tid: VotingTreasury.from_dict(t) for tid, t in state.get("treasuries", {}).items()
            }
            self.proposals = {
                pid: TreasuryProposal.from_dict(p) for pid, p in state.get("proposals", {}).items()
            }
            self.dispute_stakes = state.get("dispute_stakes", {})

            config = state.get("config", {})
            self.voting_period_hours = config.get("voting_period_hours", 72)
            self.quorum_percentage = config.get("quorum_percentage", 50.0)
            self.approval_threshold = config.get("approval_threshold", 50.0)

        except (json.JSONDecodeError, KeyError):
            pass


def create_treasury_voting_manager(
    data_dir: Optional[str] = None,
    voting_period_hours: int = 72,
    quorum_percentage: float = 50.0,
    approval_threshold: float = 50.0,
) -> TreasuryVotingManager:
    """Factory function to create a treasury voting manager."""
    path = Path(data_dir) if data_dir else None
    return TreasuryVotingManager(
        data_dir=path,
        voting_period_hours=voting_period_hours,
        quorum_percentage=quorum_percentage,
        approval_threshold=approval_threshold,
    )
