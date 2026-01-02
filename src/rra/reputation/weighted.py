# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Reputation Weight Calculation for Voting.

Provides reputation-based weight calculations for dispute resolution:
- Historical resolution success tracking
- Reputation score management
- Voting power calculation with reputation multipliers
- Good-faith behavior bonuses
- Bad actor penalties
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import math


class ReputationAction(Enum):
    """Actions that affect reputation."""

    RESOLUTION_SUCCESS = "resolution_success"
    RESOLUTION_FAILURE = "resolution_failure"
    EARLY_VOTING = "early_voting"
    EVIDENCE_PROVIDED = "evidence_provided"
    CONSENSUS_ALIGNMENT = "consensus_alignment"
    GOOD_FAITH_BONUS = "good_faith_bonus"
    LATE_VOTING_PENALTY = "late_voting_penalty"
    STAKE_MANIPULATION = "stake_manipulation"
    DISPUTE_SPAMMING = "dispute_spamming"
    MALICIOUS_BEHAVIOR = "malicious_behavior"
    DECAY_ADJUSTMENT = "decay_adjustment"


@dataclass
class ReputationChange:
    """Record of a reputation change."""

    action: ReputationAction
    delta: int
    timestamp: datetime
    dispute_id: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "delta": self.delta,
            "timestamp": self.timestamp.isoformat(),
            "dispute_id": self.dispute_id,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReputationChange":
        return cls(
            action=ReputationAction(data["action"]),
            delta=data["delta"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            dispute_id=data.get("dispute_id"),
            reason=data.get("reason"),
        )


@dataclass
class ParticipantReputation:
    """Reputation data for a participant."""

    address: str
    score: int
    total_disputes: int = 0
    successful_disputes: int = 0
    proposals_submitted: int = 0
    proposals_accepted: int = 0
    votes_aligned: int = 0
    total_votes: int = 0
    last_activity_at: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    history: List[ReputationChange] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate dispute success rate."""
        if self.total_disputes == 0:
            return 0.5  # Default for new participants
        return self.successful_disputes / self.total_disputes

    @property
    def alignment_rate(self) -> float:
        """Calculate consensus alignment rate."""
        if self.total_votes == 0:
            return 0.5  # Default for new participants
        return self.votes_aligned / self.total_votes

    @property
    def proposal_acceptance_rate(self) -> float:
        """Calculate proposal acceptance rate."""
        if self.proposals_submitted == 0:
            return 0.5
        return self.proposals_accepted / self.proposals_submitted

    @property
    def tenure_days(self) -> int:
        """Calculate participant tenure in days."""
        return (datetime.now() - self.created_at).days

    @property
    def days_since_activity(self) -> int:
        """Calculate days since last activity."""
        return (datetime.now() - self.last_activity_at).days

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "score": self.score,
            "total_disputes": self.total_disputes,
            "successful_disputes": self.successful_disputes,
            "proposals_submitted": self.proposals_submitted,
            "proposals_accepted": self.proposals_accepted,
            "votes_aligned": self.votes_aligned,
            "total_votes": self.total_votes,
            "last_activity_at": self.last_activity_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "history": [h.to_dict() for h in self.history[-50:]],  # Keep last 50
            "success_rate": self.success_rate,
            "alignment_rate": self.alignment_rate,
            "tenure_days": self.tenure_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParticipantReputation":
        rep = cls(
            address=data["address"],
            score=data["score"],
            total_disputes=data.get("total_disputes", 0),
            successful_disputes=data.get("successful_disputes", 0),
            proposals_submitted=data.get("proposals_submitted", 0),
            proposals_accepted=data.get("proposals_accepted", 0),
            votes_aligned=data.get("votes_aligned", 0),
            total_votes=data.get("total_votes", 0),
            last_activity_at=datetime.fromisoformat(data["last_activity_at"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
        rep.history = [ReputationChange.from_dict(h) for h in data.get("history", [])]
        return rep


@dataclass
class VotingPower:
    """Calculated voting power for a participant."""

    base_stake: int
    reputation_multiplier: float  # 1.0 to 3.0
    tenure_bonus: float  # 0.0 to 0.2
    total_power: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_stake": self.base_stake,
            "reputation_multiplier": round(self.reputation_multiplier, 4),
            "tenure_bonus": round(self.tenure_bonus, 4),
            "total_power": self.total_power,
        }


@dataclass
class ReputationConfig:
    """Configuration for reputation system."""

    base_reputation: int = 1000
    max_reputation: int = 10000
    min_reputation: int = 100
    decay_period_days: int = 30
    decay_rate: float = 0.01  # 1% per period
    max_multiplier: float = 3.0
    min_multiplier: float = 1.0
    tenure_bonus_max: float = 0.2  # 20% max bonus
    tenure_max_days: int = 365

    # Action deltas
    deltas: Dict[ReputationAction, int] = field(
        default_factory=lambda: {
            ReputationAction.RESOLUTION_SUCCESS: 50,
            ReputationAction.RESOLUTION_FAILURE: -30,
            ReputationAction.EARLY_VOTING: 10,
            ReputationAction.EVIDENCE_PROVIDED: 20,
            ReputationAction.CONSENSUS_ALIGNMENT: 15,
            ReputationAction.GOOD_FAITH_BONUS: 25,
            ReputationAction.LATE_VOTING_PENALTY: -20,
            ReputationAction.STAKE_MANIPULATION: -100,
            ReputationAction.DISPUTE_SPAMMING: -50,
            ReputationAction.MALICIOUS_BEHAVIOR: -200,
            ReputationAction.DECAY_ADJUSTMENT: 0,  # Calculated dynamically
        }
    )


class ReputationManager:
    """
    Manages participant reputation and voting power calculations.

    Implements reputation-weighted participation where:
    - Historical success increases vote weight
    - Good-faith actors have more influence
    - Bad actors are dampened
    - Calculations are transparent and auditable
    """

    def __init__(
        self,
        config: Optional[ReputationConfig] = None,
        data_dir: Optional[Path] = None,
    ):
        self.config = config or ReputationConfig()
        self.data_dir = data_dir

        # Participant storage
        self.participants: Dict[str, ParticipantReputation] = {}

        # Dispute tracking
        self.dispute_participants: Dict[str, List[str]] = {}

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    # =========================================================================
    # Participant Management
    # =========================================================================

    def get_or_create_participant(self, address: str) -> ParticipantReputation:
        """Get or create a participant."""
        address = address.lower()
        if address not in self.participants:
            self.participants[address] = ParticipantReputation(
                address=address,
                score=self.config.base_reputation,
            )
            self._save_state()
        return self.participants[address]

    def get_participant(self, address: str) -> Optional[ParticipantReputation]:
        """Get participant if exists."""
        return self.participants.get(address.lower())

    def get_reputation_score(self, address: str) -> int:
        """Get reputation score for address."""
        participant = self.get_participant(address)
        if participant:
            return participant.score
        return self.config.base_reputation

    # =========================================================================
    # Reputation Updates
    # =========================================================================

    def update_reputation(
        self,
        address: str,
        action: ReputationAction,
        dispute_id: Optional[str] = None,
        reason: Optional[str] = None,
        custom_delta: Optional[int] = None,
    ) -> ParticipantReputation:
        """
        Update participant reputation.

        Args:
            address: Participant address
            action: Action type
            dispute_id: Related dispute (optional)
            reason: Human-readable reason
            custom_delta: Override default delta

        Returns:
            Updated participant reputation
        """
        participant = self.get_or_create_participant(address)

        delta = custom_delta if custom_delta is not None else self.config.deltas.get(action, 0)

        # Apply change with bounds
        new_score = participant.score + delta
        new_score = max(self.config.min_reputation, min(self.config.max_reputation, new_score))

        participant.score = new_score
        participant.last_activity_at = datetime.now()

        # Record change
        change = ReputationChange(
            action=action,
            delta=delta,
            timestamp=datetime.now(),
            dispute_id=dispute_id,
            reason=reason or f"Action: {action.value}",
        )
        participant.history.append(change)

        self._save_state()
        return participant

    def apply_decay(self, address: str) -> Optional[int]:
        """
        Apply inactivity decay to participant.

        Returns decay amount applied, or None if no decay.
        """
        participant = self.get_participant(address)
        if not participant:
            return None

        days_inactive = participant.days_since_activity
        periods = days_inactive // self.config.decay_period_days

        if periods == 0:
            return None

        decay_amount = int(participant.score * self.config.decay_rate * periods)
        if decay_amount == 0:
            return None

        self.update_reputation(
            address,
            ReputationAction.DECAY_ADJUSTMENT,
            custom_delta=-decay_amount,
            reason=f"Inactivity decay: {periods} periods",
        )

        return decay_amount

    def apply_decay_all(self) -> Dict[str, int]:
        """Apply decay to all inactive participants."""
        decayed = {}
        for address in list(self.participants.keys()):
            amount = self.apply_decay(address)
            if amount:
                decayed[address] = amount
        return decayed

    # =========================================================================
    # Dispute Resolution Recording
    # =========================================================================

    def record_dispute_participation(
        self,
        dispute_id: str,
        address: str,
    ) -> None:
        """Record that a participant joined a dispute."""
        address = address.lower()
        participant = self.get_or_create_participant(address)

        if dispute_id not in self.dispute_participants:
            self.dispute_participants[dispute_id] = []

        if address not in self.dispute_participants[dispute_id]:
            self.dispute_participants[dispute_id].append(address)
            participant.total_disputes += 1
            participant.last_activity_at = datetime.now()
            self._save_state()

    def record_dispute_resolution(
        self,
        dispute_id: str,
        winners: List[str],
        losers: List[str],
    ) -> None:
        """
        Record dispute resolution outcome.

        Winners get reputation boost, losers get penalty.
        """
        for winner in winners:
            winner = winner.lower()
            participant = self.get_or_create_participant(winner)
            participant.successful_disputes += 1
            participant.votes_aligned += 1
            participant.total_votes += 1

            # Apply success bonus
            self.update_reputation(
                winner,
                ReputationAction.RESOLUTION_SUCCESS,
                dispute_id=dispute_id,
                reason="Dispute resolved successfully",
            )

            # Apply consensus alignment bonus
            self.update_reputation(
                winner,
                ReputationAction.CONSENSUS_ALIGNMENT,
                dispute_id=dispute_id,
                reason="Voted with consensus",
            )

        for loser in losers:
            loser = loser.lower()
            participant = self.get_or_create_participant(loser)
            participant.total_votes += 1

            # Apply failure penalty
            self.update_reputation(
                loser,
                ReputationAction.RESOLUTION_FAILURE,
                dispute_id=dispute_id,
                reason="Proposal/position rejected",
            )

    def record_proposal_outcome(
        self,
        address: str,
        dispute_id: str,
        accepted: bool,
    ) -> None:
        """Record proposal submission and outcome."""
        participant = self.get_or_create_participant(address)
        participant.proposals_submitted += 1

        if accepted:
            participant.proposals_accepted += 1
            self.update_reputation(
                address,
                ReputationAction.RESOLUTION_SUCCESS,
                dispute_id=dispute_id,
                custom_delta=70,  # Extra bonus for accepted proposal
                reason="Proposal accepted",
            )

    def record_early_voting(self, address: str, dispute_id: str) -> None:
        """Record early voting behavior (good faith)."""
        self.update_reputation(
            address,
            ReputationAction.EARLY_VOTING,
            dispute_id=dispute_id,
            reason="Voted early in voting period",
        )

    def record_late_voting(self, address: str, dispute_id: str) -> None:
        """Record late voting behavior (potential gaming)."""
        self.update_reputation(
            address,
            ReputationAction.LATE_VOTING_PENALTY,
            dispute_id=dispute_id,
            reason="Voted at last minute",
        )

    def record_evidence_provided(self, address: str, dispute_id: str) -> None:
        """Record evidence provision (good faith)."""
        self.update_reputation(
            address,
            ReputationAction.EVIDENCE_PROVIDED,
            dispute_id=dispute_id,
            reason="Provided quality evidence",
        )

    def record_malicious_behavior(
        self,
        address: str,
        dispute_id: str,
        behavior_type: str,
    ) -> None:
        """Record malicious behavior detection."""
        action = ReputationAction.MALICIOUS_BEHAVIOR

        if behavior_type == "stake_manipulation":
            action = ReputationAction.STAKE_MANIPULATION
        elif behavior_type == "spamming":
            action = ReputationAction.DISPUTE_SPAMMING

        self.update_reputation(
            address,
            action,
            dispute_id=dispute_id,
            reason=f"Detected: {behavior_type}",
        )

    # =========================================================================
    # Voting Power Calculation
    # =========================================================================

    def calculate_voting_power(
        self,
        address: str,
        stake: int,
    ) -> VotingPower:
        """
        Calculate voting power for a participant.

        Power = stake * reputation_multiplier * (1 + tenure_bonus)

        Args:
            address: Participant address
            stake: Amount staked

        Returns:
            VotingPower with breakdown
        """
        participant = self.get_participant(address)

        # Get reputation score (default to base)
        rep_score = self.config.base_reputation
        tenure_days = 0

        if participant:
            rep_score = participant.score
            tenure_days = participant.tenure_days

        # Calculate reputation multiplier (1.0 to 3.0)
        # Score 100 = 1.0, Score 10000 = 3.0
        score_range = self.config.max_reputation - self.config.min_reputation
        score_normalized = (rep_score - self.config.min_reputation) / score_range
        multiplier_range = self.config.max_multiplier - self.config.min_multiplier
        reputation_multiplier = self.config.min_multiplier + (score_normalized * multiplier_range)

        # Cap multiplier
        reputation_multiplier = min(reputation_multiplier, self.config.max_multiplier)

        # Calculate tenure bonus (0% to 20%)
        tenure_ratio = min(tenure_days / self.config.tenure_max_days, 1.0)
        tenure_bonus = tenure_ratio * self.config.tenure_bonus_max

        # Calculate total power
        base_power = stake * reputation_multiplier
        total_power = int(base_power * (1 + tenure_bonus))

        return VotingPower(
            base_stake=stake,
            reputation_multiplier=reputation_multiplier,
            tenure_bonus=tenure_bonus,
            total_power=total_power,
        )

    def calculate_batch_voting_power(
        self,
        participants: List[Tuple[str, int]],
    ) -> Dict[str, VotingPower]:
        """
        Calculate voting power for multiple participants.

        Args:
            participants: List of (address, stake) tuples

        Returns:
            Dict mapping address to VotingPower
        """
        return {
            address: self.calculate_voting_power(address, stake) for address, stake in participants
        }

    def get_power_distribution(
        self,
        participants: List[Tuple[str, int]],
    ) -> Dict[str, float]:
        """
        Get voting power distribution as percentages.

        Args:
            participants: List of (address, stake) tuples

        Returns:
            Dict mapping address to percentage of total power
        """
        powers = self.calculate_batch_voting_power(participants)
        total = sum(p.total_power for p in powers.values())

        if total == 0:
            return {addr: 0.0 for addr, _ in participants}

        return {addr: (power.total_power / total) * 100 for addr, power in powers.items()}

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_participant_stats(self, address: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive stats for a participant."""
        participant = self.get_participant(address)
        if not participant:
            return None

        # Calculate rank
        all_scores = [p.score for p in self.participants.values()]
        all_scores.sort(reverse=True)
        rank = all_scores.index(participant.score) + 1

        return {
            **participant.to_dict(),
            "rank": rank,
            "total_participants": len(self.participants),
            "percentile": ((len(all_scores) - rank) / len(all_scores)) * 100 if all_scores else 0,
        }

    def get_leaderboard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top participants by reputation."""
        sorted_participants = sorted(
            self.participants.values(),
            key=lambda p: p.score,
            reverse=True,
        )

        return [
            {
                "rank": i + 1,
                "address": p.address,
                "score": p.score,
                "success_rate": p.success_rate,
                "alignment_rate": p.alignment_rate,
                "tenure_days": p.tenure_days,
            }
            for i, p in enumerate(sorted_participants[:limit])
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get overall reputation system stats."""
        if not self.participants:
            return {
                "total_participants": 0,
                "avg_score": self.config.base_reputation,
                "median_score": self.config.base_reputation,
            }

        scores = [p.score for p in self.participants.values()]
        scores.sort()

        return {
            "total_participants": len(self.participants),
            "avg_score": sum(scores) / len(scores),
            "median_score": scores[len(scores) // 2],
            "min_score": min(scores),
            "max_score": max(scores),
            "total_disputes": sum(p.total_disputes for p in self.participants.values()),
            "total_successful": sum(p.successful_disputes for p in self.participants.values()),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "participants": {addr: p.to_dict() for addr, p in self.participants.items()},
            "dispute_participants": self.dispute_participants,
            "config": {
                "base_reputation": self.config.base_reputation,
                "max_reputation": self.config.max_reputation,
                "min_reputation": self.config.min_reputation,
            },
        }

        state_file = self.data_dir / "reputation_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        if not self.data_dir:
            return

        state_file = self.data_dir / "reputation_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.participants = {
                addr: ParticipantReputation.from_dict(data)
                for addr, data in state.get("participants", {}).items()
            }
            self.dispute_participants = state.get("dispute_participants", {})

        except (json.JSONDecodeError, KeyError):
            pass


def create_reputation_manager(
    data_dir: Optional[str] = None,
    config: Optional[ReputationConfig] = None,
) -> ReputationManager:
    """Factory function to create a reputation manager."""
    path = Path(data_dir) if data_dir else None
    return ReputationManager(config=config, data_dir=path)
