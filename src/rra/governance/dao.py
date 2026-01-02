# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
DAO Governance for IP Portfolios.

Enables collective ownership and governance of IP asset portfolios
through voting mechanisms and treasury management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json
import secrets


class ProposalStatus(Enum):
    """Status of a governance proposal."""

    DRAFT = "draft"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ProposalType(Enum):
    """Types of governance proposals."""

    ADD_ASSET = "add_asset"
    REMOVE_ASSET = "remove_asset"
    SET_PRICING = "set_pricing"
    DISTRIBUTE_REVENUE = "distribute_revenue"
    UPDATE_GOVERNANCE = "update_governance"
    TREASURY_SPEND = "treasury_spend"
    PARAMETER_CHANGE = "parameter_change"
    CUSTOM = "custom"


class VoteChoice(Enum):
    """Voting options."""

    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """A vote on a proposal."""

    voter_address: str
    voting_power: int
    choice: VoteChoice
    voted_at: datetime
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voter_address": self.voter_address,
            "voting_power": self.voting_power,
            "choice": self.choice.value,
            "voted_at": self.voted_at.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vote":
        return cls(
            voter_address=data["voter_address"],
            voting_power=data["voting_power"],
            choice=VoteChoice(data["choice"]),
            voted_at=datetime.fromisoformat(data["voted_at"]),
            reason=data.get("reason"),
        )


@dataclass
class Proposal:
    """A governance proposal."""

    proposal_id: str
    dao_id: str
    title: str
    description: str
    proposal_type: ProposalType
    proposer: str
    status: ProposalStatus

    # Timing
    created_at: datetime
    voting_start: datetime
    voting_end: datetime
    executed_at: Optional[datetime] = None

    # Voting thresholds
    quorum_percentage: float = 20.0  # % of total voting power needed
    approval_percentage: float = 50.0  # % of votes needed to pass

    # Proposal data
    data: Dict[str, Any] = field(default_factory=dict)

    # Votes
    _votes: Dict[str, Vote] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        now = datetime.now()
        return self.status == ProposalStatus.ACTIVE and self.voting_start <= now <= self.voting_end

    @property
    def votes_for(self) -> int:
        return sum(v.voting_power for v in self._votes.values() if v.choice == VoteChoice.FOR)

    @property
    def votes_against(self) -> int:
        return sum(v.voting_power for v in self._votes.values() if v.choice == VoteChoice.AGAINST)

    @property
    def votes_abstain(self) -> int:
        return sum(v.voting_power for v in self._votes.values() if v.choice == VoteChoice.ABSTAIN)

    @property
    def total_votes(self) -> int:
        return sum(v.voting_power for v in self._votes.values())

    @property
    def voter_count(self) -> int:
        return len(self._votes)

    def add_vote(self, vote: Vote) -> None:
        """Add a vote to this proposal."""
        if not self.is_active:
            raise ValueError("Voting is not active")

        self._votes[vote.voter_address.lower()] = vote

    def get_result(self, total_voting_power: int) -> Dict[str, Any]:
        """Calculate voting result."""
        quorum_met = (
            (self.total_votes / total_voting_power * 100) >= self.quorum_percentage
            if total_voting_power > 0
            else False
        )

        votes_cast = self.votes_for + self.votes_against
        approval = (self.votes_for / votes_cast * 100) if votes_cast > 0 else 0

        passed = quorum_met and approval >= self.approval_percentage

        return {
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "votes_abstain": self.votes_abstain,
            "total_votes": self.total_votes,
            "voter_count": self.voter_count,
            "quorum_percentage": (
                (self.total_votes / total_voting_power * 100) if total_voting_power > 0 else 0
            ),
            "quorum_met": quorum_met,
            "approval_percentage": approval,
            "passed": passed,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "dao_id": self.dao_id,
            "title": self.title,
            "description": self.description,
            "proposal_type": self.proposal_type.value,
            "proposer": self.proposer,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "voting_start": self.voting_start.isoformat(),
            "voting_end": self.voting_end.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "quorum_percentage": self.quorum_percentage,
            "approval_percentage": self.approval_percentage,
            "data": self.data,
            "votes": {addr: v.to_dict() for addr, v in self._votes.items()},
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "votes_abstain": self.votes_abstain,
            "total_votes": self.total_votes,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proposal":
        proposal = cls(
            proposal_id=data["proposal_id"],
            dao_id=data["dao_id"],
            title=data["title"],
            description=data["description"],
            proposal_type=ProposalType(data["proposal_type"]),
            proposer=data["proposer"],
            status=ProposalStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            voting_start=datetime.fromisoformat(data["voting_start"]),
            voting_end=datetime.fromisoformat(data["voting_end"]),
            quorum_percentage=data.get("quorum_percentage", 20.0),
            approval_percentage=data.get("approval_percentage", 50.0),
            data=data.get("data", {}),
        )
        if data.get("executed_at"):
            proposal.executed_at = datetime.fromisoformat(data["executed_at"])

        for addr, vote_data in data.get("votes", {}).items():
            proposal._votes[addr] = Vote.from_dict(vote_data)

        return proposal


@dataclass
class DAOMember:
    """A DAO member with voting power."""

    address: str
    voting_power: int
    joined_at: datetime
    delegated_to: Optional[str] = None
    delegated_power: int = 0  # Power delegated TO this member

    @property
    def effective_voting_power(self) -> int:
        """Voting power including delegations."""
        if self.delegated_to:
            return 0  # Delegated away
        return self.voting_power + self.delegated_power

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "voting_power": self.voting_power,
            "joined_at": self.joined_at.isoformat(),
            "delegated_to": self.delegated_to,
            "delegated_power": self.delegated_power,
            "effective_voting_power": self.effective_voting_power,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DAOMember":
        return cls(
            address=data["address"],
            voting_power=data["voting_power"],
            joined_at=datetime.fromisoformat(data["joined_at"]),
            delegated_to=data.get("delegated_to"),
            delegated_power=data.get("delegated_power", 0),
        )


@dataclass
class IPDAO:
    """An IP Portfolio DAO."""

    dao_id: str
    name: str
    description: str
    creator: str
    created_at: datetime

    # Assets managed by this DAO
    asset_ids: List[str] = field(default_factory=list)

    # Treasury
    treasury_balance: float = 0.0

    # Governance parameters
    voting_period_days: int = 7
    proposal_threshold: int = 100  # Min voting power to create proposal
    quorum_percentage: float = 20.0
    approval_percentage: float = 50.0

    # Members
    _members: Dict[str, DAOMember] = field(default_factory=dict)

    @property
    def total_voting_power(self) -> int:
        return sum(m.voting_power for m in self._members.values())

    @property
    def member_count(self) -> int:
        return len(self._members)

    def add_member(self, address: str, voting_power: int) -> DAOMember:
        """Add or update a DAO member."""
        address = address.lower()
        if address in self._members:
            self._members[address].voting_power += voting_power
        else:
            self._members[address] = DAOMember(
                address=address,
                voting_power=voting_power,
                joined_at=datetime.now(),
            )
        return self._members[address]

    def get_member(self, address: str) -> Optional[DAOMember]:
        return self._members.get(address.lower())

    def delegate_votes(self, from_address: str, to_address: str) -> tuple[DAOMember, DAOMember]:
        """Delegate voting power to another member."""
        from_member = self._members.get(from_address.lower())
        to_member = self._members.get(to_address.lower())

        if not from_member:
            raise ValueError(f"Member not found: {from_address}")
        if not to_member:
            raise ValueError(f"Delegate not found: {to_address}")

        # Remove previous delegation
        if from_member.delegated_to:
            old_delegate = self._members.get(from_member.delegated_to)
            if old_delegate:
                old_delegate.delegated_power -= from_member.voting_power

        # Add new delegation
        from_member.delegated_to = to_address.lower()
        to_member.delegated_power += from_member.voting_power

        return from_member, to_member

    def revoke_delegation(self, address: str) -> DAOMember:
        """Revoke vote delegation."""
        member = self._members.get(address.lower())
        if not member:
            raise ValueError(f"Member not found: {address}")

        if member.delegated_to:
            delegate = self._members.get(member.delegated_to)
            if delegate:
                delegate.delegated_power -= member.voting_power
            member.delegated_to = None

        return member

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dao_id": self.dao_id,
            "name": self.name,
            "description": self.description,
            "creator": self.creator,
            "created_at": self.created_at.isoformat(),
            "asset_ids": self.asset_ids,
            "treasury_balance": self.treasury_balance,
            "voting_period_days": self.voting_period_days,
            "proposal_threshold": self.proposal_threshold,
            "quorum_percentage": self.quorum_percentage,
            "approval_percentage": self.approval_percentage,
            "members": {addr: m.to_dict() for addr, m in self._members.items()},
            "total_voting_power": self.total_voting_power,
            "member_count": self.member_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPDAO":
        dao = cls(
            dao_id=data["dao_id"],
            name=data["name"],
            description=data["description"],
            creator=data["creator"],
            created_at=datetime.fromisoformat(data["created_at"]),
            asset_ids=data.get("asset_ids", []),
            treasury_balance=data.get("treasury_balance", 0.0),
            voting_period_days=data.get("voting_period_days", 7),
            proposal_threshold=data.get("proposal_threshold", 100),
            quorum_percentage=data.get("quorum_percentage", 20.0),
            approval_percentage=data.get("approval_percentage", 50.0),
        )

        for addr, member_data in data.get("members", {}).items():
            dao._members[addr] = DAOMember.from_dict(member_data)

        return dao


class DAOGovernanceManager:
    """Manages DAO governance operations."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/governance")
        self.daos: Dict[str, IPDAO] = {}
        self.proposals: Dict[str, Proposal] = {}

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    # =========================================================================
    # DAO Management
    # =========================================================================

    def create_dao(
        self,
        name: str,
        description: str,
        creator: str,
        initial_voting_power: int = 1000,
        voting_period_days: int = 7,
        proposal_threshold: int = 100,
        quorum_percentage: float = 20.0,
        approval_percentage: float = 50.0,
    ) -> IPDAO:
        """Create a new DAO."""
        dao = IPDAO(
            dao_id=self._generate_id("dao_"),
            name=name,
            description=description,
            creator=creator,
            created_at=datetime.now(),
            voting_period_days=voting_period_days,
            proposal_threshold=proposal_threshold,
            quorum_percentage=quorum_percentage,
            approval_percentage=approval_percentage,
        )

        # Creator gets initial voting power
        dao.add_member(creator, initial_voting_power)

        self.daos[dao.dao_id] = dao
        self._save_state()

        return dao

    def get_dao(self, dao_id: str) -> Optional[IPDAO]:
        return self.daos.get(dao_id)

    def list_daos(self) -> List[IPDAO]:
        return list(self.daos.values())

    def add_dao_member(self, dao_id: str, address: str, voting_power: int) -> DAOMember:
        """Add a member to a DAO."""
        dao = self.daos.get(dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {dao_id}")

        member = dao.add_member(address, voting_power)
        self._save_state()

        return member

    def add_asset_to_dao(self, dao_id: str, asset_id: str) -> IPDAO:
        """Add an IP asset to a DAO's portfolio."""
        dao = self.daos.get(dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {dao_id}")

        if asset_id not in dao.asset_ids:
            dao.asset_ids.append(asset_id)
            self._save_state()

        return dao

    def add_to_treasury(self, dao_id: str, amount: float) -> IPDAO:
        """Add funds to DAO treasury."""
        dao = self.daos.get(dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {dao_id}")

        dao.treasury_balance += amount
        self._save_state()

        return dao

    # =========================================================================
    # Proposal Management
    # =========================================================================

    def create_proposal(
        self,
        dao_id: str,
        title: str,
        description: str,
        proposal_type: ProposalType,
        proposer: str,
        data: Optional[Dict[str, Any]] = None,
        voting_delay_hours: int = 24,
    ) -> Proposal:
        """Create a new governance proposal."""
        dao = self.daos.get(dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {dao_id}")

        # Check proposer has enough voting power
        member = dao.get_member(proposer)
        if not member or member.effective_voting_power < dao.proposal_threshold:
            raise ValueError(
                f"Insufficient voting power. Required: {dao.proposal_threshold}, "
                f"Have: {member.effective_voting_power if member else 0}"
            )

        now = datetime.now()
        proposal = Proposal(
            proposal_id=self._generate_id("prop_"),
            dao_id=dao_id,
            title=title,
            description=description,
            proposal_type=proposal_type,
            proposer=proposer,
            status=ProposalStatus.ACTIVE,
            created_at=now,
            voting_start=now + timedelta(hours=voting_delay_hours),
            voting_end=now + timedelta(hours=voting_delay_hours, days=dao.voting_period_days),
            quorum_percentage=dao.quorum_percentage,
            approval_percentage=dao.approval_percentage,
            data=data or {},
        )

        self.proposals[proposal.proposal_id] = proposal
        self._save_state()

        return proposal

    def vote(
        self, proposal_id: str, voter_address: str, choice: VoteChoice, reason: Optional[str] = None
    ) -> Vote:
        """Cast a vote on a proposal."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        dao = self.daos.get(proposal.dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {proposal.dao_id}")

        member = dao.get_member(voter_address)
        if not member:
            raise ValueError(f"Not a DAO member: {voter_address}")

        voting_power = member.effective_voting_power
        if voting_power <= 0:
            raise ValueError("No voting power (may have delegated)")

        vote = Vote(
            voter_address=voter_address,
            voting_power=voting_power,
            choice=choice,
            voted_at=datetime.now(),
            reason=reason,
        )

        proposal.add_vote(vote)
        self._save_state()

        return vote

    def finalize_proposal(self, proposal_id: str) -> Proposal:
        """Finalize voting on a proposal."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.ACTIVE:
            raise ValueError(f"Proposal is not active: {proposal.status.value}")

        if datetime.now() < proposal.voting_end:
            raise ValueError("Voting period has not ended")

        dao = self.daos.get(proposal.dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {proposal.dao_id}")

        result = proposal.get_result(dao.total_voting_power)

        if result["passed"]:
            proposal.status = ProposalStatus.PASSED
        else:
            proposal.status = ProposalStatus.REJECTED

        self._save_state()

        return proposal

    def execute_proposal(self, proposal_id: str) -> Proposal:
        """Execute a passed proposal."""
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status != ProposalStatus.PASSED:
            raise ValueError(f"Proposal has not passed: {proposal.status.value}")

        # Execute based on proposal type
        dao = self.daos.get(proposal.dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {proposal.dao_id}")

        self._execute_proposal_action(dao, proposal)

        proposal.status = ProposalStatus.EXECUTED
        proposal.executed_at = datetime.now()
        self._save_state()

        return proposal

    def _execute_proposal_action(self, dao: IPDAO, proposal: Proposal) -> None:
        """Execute the action specified in the proposal."""
        if proposal.proposal_type == ProposalType.ADD_ASSET:
            asset_id = proposal.data.get("asset_id")
            if asset_id:
                dao.asset_ids.append(asset_id)

        elif proposal.proposal_type == ProposalType.REMOVE_ASSET:
            asset_id = proposal.data.get("asset_id")
            if asset_id and asset_id in dao.asset_ids:
                dao.asset_ids.remove(asset_id)

        elif proposal.proposal_type == ProposalType.TREASURY_SPEND:
            amount = proposal.data.get("amount", 0)
            recipient = proposal.data.get("recipient")
            if amount > 0 and amount <= dao.treasury_balance:
                dao.treasury_balance -= amount
                # In production, would transfer to recipient

        elif proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
            param = proposal.data.get("parameter")
            value = proposal.data.get("value")
            if param == "voting_period_days":
                dao.voting_period_days = int(value)
            elif param == "quorum_percentage":
                dao.quorum_percentage = float(value)
            elif param == "approval_percentage":
                dao.approval_percentage = float(value)
            elif param == "proposal_threshold":
                dao.proposal_threshold = int(value)

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        return self.proposals.get(proposal_id)

    def list_proposals(
        self, dao_id: Optional[str] = None, status: Optional[ProposalStatus] = None
    ) -> List[Proposal]:
        """List proposals with optional filters."""
        proposals = list(self.proposals.values())

        if dao_id:
            proposals = [p for p in proposals if p.dao_id == dao_id]

        if status:
            proposals = [p for p in proposals if p.status == status]

        return proposals

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_dao_stats(self, dao_id: str) -> Dict[str, Any]:
        """Get statistics for a DAO."""
        dao = self.daos.get(dao_id)
        if not dao:
            raise ValueError(f"DAO not found: {dao_id}")

        proposals = [p for p in self.proposals.values() if p.dao_id == dao_id]

        return {
            **dao.to_dict(),
            "total_proposals": len(proposals),
            "active_proposals": len([p for p in proposals if p.status == ProposalStatus.ACTIVE]),
            "passed_proposals": len([p for p in proposals if p.status == ProposalStatus.PASSED]),
            "executed_proposals": len(
                [p for p in proposals if p.status == ProposalStatus.EXECUTED]
            ),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "daos": {did: d.to_dict() for did, d in self.daos.items()},
            "proposals": {pid: p.to_dict() for pid, p in self.proposals.items()},
        }

        with open(self.data_dir / "governance_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        state_file = self.data_dir / "governance_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.daos = {did: IPDAO.from_dict(d) for did, d in state.get("daos", {}).items()}
            self.proposals = {
                pid: Proposal.from_dict(p) for pid, p in state.get("proposals", {}).items()
            }
        except (json.JSONDecodeError, KeyError):
            pass


def create_governance_manager(data_dir: Optional[str] = None) -> DAOGovernanceManager:
    """Factory function to create a governance manager."""
    path = Path(data_dir) if data_dir else None
    return DAOGovernanceManager(data_dir=path)
