# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Negotiation Pressure Module for NatLangChain.

Implements economic pressure mechanisms to encourage timely resolution
of license negotiations. This module works alongside the NegotiationPressure.sol
smart contract to provide both on-chain and off-chain pressure tracking.

Key Mechanisms:
1. Counter-Proposal Caps: Limits the number of counter-proposals per party
2. Exponential Delay Costs: Time-based penalties that accelerate
3. Deadline Enforcement: Hard limits with stake penalties

Economic Model:
- Delay cost = baseRate * 2^(daysElapsed/halfLifeDays) - baseRate
- Counter-proposal penalty applied when cap is exceeded
- Expiration penalty if deadline passes without agreement

Usage:
    config = PressureConfig(max_counter_proposals=5, half_life_days=7)
    pressure = NegotiationPressure(config)

    # Start tracking a negotiation
    pressure.start_negotiation(
        negotiation_id="neg_123",
        initiator_stake=1.0,
        responder_stake=1.0,
        duration_days=30
    )

    # Submit counter-proposal
    result = pressure.submit_counter_proposal(
        negotiation_id="neg_123",
        party="initiator",
        proposal_hash="0x..."
    )

    # Check pressure status
    status = pressure.get_pressure_status("neg_123")
    print(f"Delay cost: {status.current_delay_cost} ETH")
    print(f"Remaining proposals: {status.remaining_proposals}")
"""

import hashlib
import math
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal


class NegotiationStatus(Enum):
    """Status of a negotiation."""
    PENDING = "pending"      # Waiting for responder
    ACTIVE = "active"        # Both parties engaged
    AGREED = "agreed"        # Agreement reached
    EXPIRED = "expired"      # Deadline passed
    CANCELLED = "cancelled"  # Voluntarily cancelled


@dataclass
class PressureConfig:
    """Configuration for negotiation pressure parameters."""

    # Counter-proposal limits
    max_counter_proposals: int = 5

    # Delay cost parameters (in basis points, 100 = 1%)
    base_delay_rate_bps: int = 10  # 0.1% per day base
    half_life_days: int = 7        # Cost doubles every 7 days

    # Penalty rates (in basis points)
    counter_proposal_penalty_bps: int = 500   # 5% for exceeding cap
    expiration_penalty_bps: int = 2000        # 20% for expiration

    # Stake requirements
    min_stake_eth: float = 0.01
    max_duration_days: int = 90

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_counter_proposals": self.max_counter_proposals,
            "base_delay_rate_bps": self.base_delay_rate_bps,
            "half_life_days": self.half_life_days,
            "counter_proposal_penalty_bps": self.counter_proposal_penalty_bps,
            "expiration_penalty_bps": self.expiration_penalty_bps,
            "min_stake_eth": self.min_stake_eth,
            "max_duration_days": self.max_duration_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PressureConfig":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class CounterProposal:
    """Record of a counter-proposal."""
    proposal_hash: str
    party: str  # "initiator" or "responder"
    timestamp: datetime
    delay_cost_at_time: float
    proposal_number: int
    penalty_applied: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "proposal_hash": self.proposal_hash,
            "party": self.party,
            "timestamp": self.timestamp.isoformat(),
            "delay_cost_at_time": self.delay_cost_at_time,
            "proposal_number": self.proposal_number,
            "penalty_applied": self.penalty_applied,
        }


@dataclass
class NegotiationState:
    """State of a tracked negotiation."""
    negotiation_id: str
    initiator_hash: str
    responder_hash: str
    initiator_stake: float
    responder_stake: float
    start_time: datetime
    deadline: datetime
    status: NegotiationStatus
    config: PressureConfig

    # Counter-proposal tracking
    initiator_proposals: int = 0
    responder_proposals: int = 0

    # Cost tracking
    accrued_delay_cost: float = 0.0
    total_penalties: float = 0.0

    # Activity tracking
    last_activity: Optional[datetime] = None
    counter_proposals: List[CounterProposal] = field(default_factory=list)

    # Agreement
    agreement_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "negotiation_id": self.negotiation_id,
            "initiator_hash": self.initiator_hash,
            "responder_hash": self.responder_hash,
            "initiator_stake": self.initiator_stake,
            "responder_stake": self.responder_stake,
            "start_time": self.start_time.isoformat(),
            "deadline": self.deadline.isoformat(),
            "status": self.status.value,
            "initiator_proposals": self.initiator_proposals,
            "responder_proposals": self.responder_proposals,
            "accrued_delay_cost": self.accrued_delay_cost,
            "total_penalties": self.total_penalties,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "counter_proposals": [cp.to_dict() for cp in self.counter_proposals],
            "agreement_hash": self.agreement_hash,
        }


@dataclass
class PressureStatus:
    """Current pressure status for a negotiation."""
    negotiation_id: str
    status: NegotiationStatus
    current_delay_cost: float
    projected_delay_cost_24h: float
    remaining_proposals_initiator: int
    remaining_proposals_responder: int
    time_remaining: timedelta
    stake_at_risk_initiator: float
    stake_at_risk_responder: float
    urgency_level: str  # "low", "medium", "high", "critical"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "negotiation_id": self.negotiation_id,
            "status": self.status.value,
            "current_delay_cost": round(self.current_delay_cost, 6),
            "projected_delay_cost_24h": round(self.projected_delay_cost_24h, 6),
            "remaining_proposals_initiator": self.remaining_proposals_initiator,
            "remaining_proposals_responder": self.remaining_proposals_responder,
            "time_remaining_seconds": self.time_remaining.total_seconds(),
            "time_remaining_human": str(self.time_remaining),
            "stake_at_risk_initiator": round(self.stake_at_risk_initiator, 6),
            "stake_at_risk_responder": round(self.stake_at_risk_responder, 6),
            "urgency_level": self.urgency_level,
        }


def calculate_delay_cost(
    total_stake: float,
    elapsed_days: float,
    base_rate_bps: int = 10,
    half_life_days: int = 7
) -> float:
    """
    Calculate exponential delay cost.

    The cost starts at 0 and ramps up linearly in the first half-life period,
    then doubles every half_life_days thereafter:
    - For days <= half_life: linear ramp to base cost
    - For days > half_life: exponential growth (doubles each period)

    This creates exponential pressure that doubles every half_life_days.

    Args:
        total_stake: Combined stake of both parties (ETH)
        elapsed_days: Days since negotiation started
        base_rate_bps: Base rate in basis points (10 = 0.1%)
        half_life_days: Days for cost to double

    Returns:
        Delay cost in ETH
    """
    if elapsed_days <= 0:
        return 0.0

    base_rate = base_rate_bps / 10000  # Convert basis points to decimal

    if elapsed_days <= half_life_days:
        # Linear ramp-up in first period (from 0 to base_rate)
        multiplier = elapsed_days / half_life_days
    else:
        # Exponential growth after first period (doubles each half_life)
        periods = (elapsed_days / half_life_days) - 1
        multiplier = 2 ** periods

    cost = total_stake * base_rate * multiplier

    return cost


class NegotiationPressure:
    """
    Manages negotiation pressure for multiple negotiations.

    This class tracks counter-proposals, calculates delay costs,
    and enforces pressure mechanisms to encourage timely resolution.
    """

    def __init__(self, default_config: Optional[PressureConfig] = None):
        """
        Initialize the pressure manager.

        Args:
            default_config: Default pressure configuration
        """
        self.default_config = default_config or PressureConfig()
        self._negotiations: Dict[str, NegotiationState] = {}
        self._total_delay_costs_collected = 0.0
        self._total_penalties_collected = 0.0

    def start_negotiation(
        self,
        negotiation_id: str,
        initiator_id: str,
        responder_id: str,
        initiator_stake: float,
        duration_days: int,
        config: Optional[PressureConfig] = None
    ) -> NegotiationState:
        """
        Start tracking a new negotiation.

        Args:
            negotiation_id: Unique identifier
            initiator_id: Initiator's identity (will be hashed)
            responder_id: Responder's identity (will be hashed)
            initiator_stake: Initiator's stake in ETH
            duration_days: Negotiation duration
            config: Optional custom pressure config

        Returns:
            NegotiationState for the new negotiation
        """
        config = config or self.default_config

        if initiator_stake < config.min_stake_eth:
            raise ValueError(f"Stake must be at least {config.min_stake_eth} ETH")

        if duration_days > config.max_duration_days:
            raise ValueError(f"Duration cannot exceed {config.max_duration_days} days")

        # Hash identities for privacy
        initiator_hash = hashlib.sha256(initiator_id.encode()).hexdigest()[:16]
        responder_hash = hashlib.sha256(responder_id.encode()).hexdigest()[:16]

        now = datetime.utcnow()

        state = NegotiationState(
            negotiation_id=negotiation_id,
            initiator_hash=initiator_hash,
            responder_hash=responder_hash,
            initiator_stake=initiator_stake,
            responder_stake=0.0,
            start_time=now,
            deadline=now + timedelta(days=duration_days),
            status=NegotiationStatus.PENDING,
            config=config,
            last_activity=now,
        )

        self._negotiations[negotiation_id] = state
        return state

    def join_negotiation(
        self,
        negotiation_id: str,
        responder_stake: float
    ) -> NegotiationState:
        """
        Responder joins the negotiation.

        Args:
            negotiation_id: The negotiation to join
            responder_stake: Responder's stake in ETH

        Returns:
            Updated NegotiationState
        """
        state = self._get_negotiation(negotiation_id)

        if state.status != NegotiationStatus.PENDING:
            raise ValueError("Negotiation is not pending")

        if responder_stake < state.config.min_stake_eth:
            raise ValueError(f"Stake must be at least {state.config.min_stake_eth} ETH")

        state.responder_stake = responder_stake
        state.status = NegotiationStatus.ACTIVE
        state.last_activity = datetime.utcnow()

        # Accrue any delay cost since start
        self._accrue_delay_cost(state)

        return state

    def submit_counter_proposal(
        self,
        negotiation_id: str,
        party: str,
        proposal_hash: str
    ) -> Tuple[CounterProposal, Optional[float]]:
        """
        Submit a counter-proposal.

        Args:
            negotiation_id: The negotiation
            party: "initiator" or "responder"
            proposal_hash: Hash of proposal content

        Returns:
            Tuple of (CounterProposal, penalty_amount or None)
        """
        state = self._get_negotiation(negotiation_id)

        if state.status != NegotiationStatus.ACTIVE:
            raise ValueError("Negotiation is not active")

        if datetime.utcnow() >= state.deadline:
            raise ValueError("Negotiation has expired")

        if party not in ("initiator", "responder"):
            raise ValueError("Party must be 'initiator' or 'responder'")

        # Accrue delay cost
        self._accrue_delay_cost(state)

        # Get current count and check cap
        if party == "initiator":
            current_count = state.initiator_proposals
            stake = state.initiator_stake
        else:
            current_count = state.responder_proposals
            stake = state.responder_stake

        penalty = None

        # Check if exceeding cap
        if current_count >= state.config.max_counter_proposals:
            # Apply penalty
            penalty_rate = state.config.counter_proposal_penalty_bps / 10000
            penalty = stake * penalty_rate

            if party == "initiator":
                state.initiator_stake -= penalty
            else:
                state.responder_stake -= penalty

            state.total_penalties += penalty
            self._total_penalties_collected += penalty

        # Increment counter
        if party == "initiator":
            state.initiator_proposals += 1
            proposal_number = state.initiator_proposals
        else:
            state.responder_proposals += 1
            proposal_number = state.responder_proposals

        # Create counter-proposal record
        cp = CounterProposal(
            proposal_hash=proposal_hash,
            party=party,
            timestamp=datetime.utcnow(),
            delay_cost_at_time=state.accrued_delay_cost,
            proposal_number=proposal_number,
            penalty_applied=penalty or 0.0,
        )

        state.counter_proposals.append(cp)
        state.last_activity = datetime.utcnow()

        return cp, penalty

    def record_agreement(
        self,
        negotiation_id: str,
        agreement_hash: str
    ) -> Tuple[float, float, float]:
        """
        Record agreement and calculate final costs.

        Args:
            negotiation_id: The negotiation
            agreement_hash: Hash of the final agreement

        Returns:
            Tuple of (initiator_refund, responder_refund, total_delay_cost)
        """
        state = self._get_negotiation(negotiation_id)

        if state.status != NegotiationStatus.ACTIVE:
            raise ValueError("Negotiation is not active")

        # Final delay cost accrual
        self._accrue_delay_cost(state)

        # Calculate proportional delay costs
        total_stake = state.initiator_stake + state.responder_stake
        delay_cost = state.accrued_delay_cost

        if total_stake > 0:
            initiator_delay = (delay_cost * state.initiator_stake) / total_stake
            responder_delay = delay_cost - initiator_delay
        else:
            initiator_delay = responder_delay = 0

        # Calculate refunds
        initiator_refund = max(0, state.initiator_stake - initiator_delay)
        responder_refund = max(0, state.responder_stake - responder_delay)

        # Update state
        state.status = NegotiationStatus.AGREED
        state.agreement_hash = agreement_hash
        state.initiator_stake = 0
        state.responder_stake = 0

        self._total_delay_costs_collected += delay_cost

        return initiator_refund, responder_refund, delay_cost

    def process_expiration(
        self,
        negotiation_id: str
    ) -> Tuple[float, float]:
        """
        Process an expired negotiation.

        Args:
            negotiation_id: The negotiation

        Returns:
            Tuple of (initiator_penalty, responder_penalty)
        """
        state = self._get_negotiation(negotiation_id)

        if state.status != NegotiationStatus.ACTIVE:
            raise ValueError("Negotiation is not active")

        if datetime.utcnow() < state.deadline:
            raise ValueError("Negotiation has not expired")

        # Final delay cost
        self._accrue_delay_cost(state)

        # Apply expiration penalties
        penalty_rate = state.config.expiration_penalty_bps / 10000
        initiator_penalty = state.initiator_stake * penalty_rate
        responder_penalty = state.responder_stake * penalty_rate

        # Update state
        state.status = NegotiationStatus.EXPIRED
        state.total_penalties += initiator_penalty + responder_penalty

        self._total_penalties_collected += initiator_penalty + responder_penalty
        self._total_delay_costs_collected += state.accrued_delay_cost

        return initiator_penalty, responder_penalty

    def get_pressure_status(self, negotiation_id: str) -> PressureStatus:
        """
        Get current pressure status for a negotiation.

        Args:
            negotiation_id: The negotiation

        Returns:
            PressureStatus with current metrics
        """
        state = self._get_negotiation(negotiation_id)

        now = datetime.utcnow()

        # Calculate current delay cost
        elapsed = (now - state.start_time).total_seconds() / 86400  # days
        total_stake = state.initiator_stake + state.responder_stake
        current_cost = calculate_delay_cost(
            total_stake,
            elapsed,
            state.config.base_delay_rate_bps,
            state.config.half_life_days
        )

        # Project cost 24h ahead
        projected_cost = calculate_delay_cost(
            total_stake,
            elapsed + 1,
            state.config.base_delay_rate_bps,
            state.config.half_life_days
        )

        # Remaining proposals
        remaining_init = max(0, state.config.max_counter_proposals - state.initiator_proposals)
        remaining_resp = max(0, state.config.max_counter_proposals - state.responder_proposals)

        # Time remaining
        time_remaining = max(timedelta(0), state.deadline - now)

        # Stake at risk (delay cost share + potential penalties)
        stake_risk_init = (current_cost * state.initiator_stake / total_stake) if total_stake > 0 else 0
        stake_risk_resp = (current_cost * state.responder_stake / total_stake) if total_stake > 0 else 0

        # Urgency level
        days_remaining = time_remaining.total_seconds() / 86400
        cost_ratio = current_cost / total_stake if total_stake > 0 else 0

        if days_remaining <= 1 or cost_ratio > 0.15:
            urgency = "critical"
        elif days_remaining <= 3 or cost_ratio > 0.10:
            urgency = "high"
        elif days_remaining <= 7 or cost_ratio > 0.05:
            urgency = "medium"
        else:
            urgency = "low"

        return PressureStatus(
            negotiation_id=negotiation_id,
            status=state.status,
            current_delay_cost=current_cost,
            projected_delay_cost_24h=projected_cost,
            remaining_proposals_initiator=remaining_init,
            remaining_proposals_responder=remaining_resp,
            time_remaining=time_remaining,
            stake_at_risk_initiator=stake_risk_init,
            stake_at_risk_responder=stake_risk_resp,
            urgency_level=urgency,
        )

    def get_negotiation(self, negotiation_id: str) -> NegotiationState:
        """Get negotiation state."""
        return self._get_negotiation(negotiation_id)

    def get_all_active(self) -> List[NegotiationState]:
        """Get all active negotiations."""
        return [
            n for n in self._negotiations.values()
            if n.status in (NegotiationStatus.PENDING, NegotiationStatus.ACTIVE)
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        active = len([n for n in self._negotiations.values()
                     if n.status == NegotiationStatus.ACTIVE])
        agreed = len([n for n in self._negotiations.values()
                     if n.status == NegotiationStatus.AGREED])
        expired = len([n for n in self._negotiations.values()
                      if n.status == NegotiationStatus.EXPIRED])

        return {
            "total_negotiations": len(self._negotiations),
            "active": active,
            "agreed": agreed,
            "expired": expired,
            "total_delay_costs_collected": round(self._total_delay_costs_collected, 6),
            "total_penalties_collected": round(self._total_penalties_collected, 6),
            "agreement_rate": agreed / len(self._negotiations) if self._negotiations else 0,
        }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _get_negotiation(self, negotiation_id: str) -> NegotiationState:
        """Get negotiation or raise error."""
        state = self._negotiations.get(negotiation_id)
        if not state:
            raise ValueError(f"Negotiation not found: {negotiation_id}")
        return state

    def _accrue_delay_cost(self, state: NegotiationState) -> float:
        """
        Accrue delay cost based on time elapsed.

        Args:
            state: Negotiation state to update

        Returns:
            New delay cost accrued
        """
        now = datetime.utcnow()
        elapsed = (now - state.start_time).total_seconds() / 86400

        total_stake = state.initiator_stake + state.responder_stake
        new_cost = calculate_delay_cost(
            total_stake,
            elapsed,
            state.config.base_delay_rate_bps,
            state.config.half_life_days
        )

        accrued = new_cost - state.accrued_delay_cost
        state.accrued_delay_cost = new_cost

        return accrued
