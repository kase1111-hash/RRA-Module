# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Treasury Coordination API Endpoints.

Provides REST API for multi-treasury dispute coordination:
- Treasury registration and management
- Multi-treasury dispute creation
- Stake-weighted voting
- Proposal management
- Fund distribution and resolution
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from rra.treasury.coordinator import (
    TreasuryCoordinator,
    TreasuryConfig,
    Treasury,
    TreasuryType,
    TreasuryDispute,
    DisputeStatus,
    Proposal,
    ProposalType,
    ProposalStatus,
    VoteChoice,
    create_treasury_coordinator,
)
from rra.governance.treasury_votes import (
    TreasuryVotingManager,
    TreasuryVoteType,
    TreasuryVoteStatus,
    VoteChoice as VotingChoice,
    create_treasury_voting_manager,
)


router = APIRouter(prefix="/treasury", tags=["treasury"])

# Singleton instances
_treasury_coordinator: Optional[TreasuryCoordinator] = None
_voting_manager: Optional[TreasuryVotingManager] = None


def get_treasury_coordinator() -> TreasuryCoordinator:
    """Get or create treasury coordinator instance."""
    global _treasury_coordinator
    if _treasury_coordinator is None:
        _treasury_coordinator = create_treasury_coordinator()
    return _treasury_coordinator


def get_voting_manager() -> TreasuryVotingManager:
    """Get or create voting manager instance."""
    global _voting_manager
    if _voting_manager is None:
        _voting_manager = create_treasury_voting_manager(
            data_dir="data/treasury/votes"
        )
    return _voting_manager


# =============================================================================
# Request/Response Models
# =============================================================================

class TreasuryRegisterRequest(BaseModel):
    """Request to register a treasury."""
    name: str = Field(..., min_length=1, max_length=100)
    treasury_type: str = Field(default="corporate")
    signers: List[str] = Field(..., min_length=1, max_length=20)
    signer_threshold: int = Field(default=1, ge=1)
    metadata: Optional[Dict[str, Any]] = None


class TreasuryResponse(BaseModel):
    """Response with treasury details."""
    treasury_id: str
    name: str
    treasury_type: str
    signers: List[str]
    signer_threshold: int
    total_stake: int
    created_at: str


class DisputeCreateRequest(BaseModel):
    """Request to create a multi-treasury dispute."""
    creator_treasury_id: str
    involved_treasury_ids: List[str] = Field(..., min_length=1)
    title: str = Field(..., min_length=5, max_length=200)
    description_uri: str
    is_binding: bool = Field(default=False)
    creator_address: str


class DisputeResponse(BaseModel):
    """Response with dispute details."""
    dispute_id: str
    creator_treasury: str
    involved_treasuries: List[str]
    title: str
    description_uri: str
    status: str
    is_binding: bool
    total_stake: int
    created_at: str


class StakeRequest(BaseModel):
    """Request to stake funds for a dispute."""
    dispute_id: str
    treasury_id: str
    stake_amount: int = Field(..., gt=0)
    staker_address: str


class StakeResponse(BaseModel):
    """Response with stake details."""
    dispute_id: str
    treasury_id: str
    total_stake: int
    stake_amount: int


class ProposalCreateRequest(BaseModel):
    """Request to create a resolution proposal."""
    dispute_id: str
    treasury_id: str
    proposal_type: str = Field(default="resolution")
    title: str = Field(..., min_length=5, max_length=200)
    description: str
    ipfs_uri: Optional[str] = None
    payout_shares: Optional[Dict[str, int]] = None
    proposer_address: str


class ProposalResponse(BaseModel):
    """Response with proposal details."""
    proposal_id: str
    dispute_id: str
    treasury_id: str
    proposal_type: str
    title: str
    description: str
    status: str
    stake_approved: int
    stake_rejected: int
    stake_abstained: int
    created_at: str


class VoteRequest(BaseModel):
    """Request to cast a vote."""
    dispute_id: str
    proposal_id: str
    treasury_id: str
    choice: str = Field(pattern="^(approve|reject|abstain)$")
    voter_address: str
    reason: Optional[str] = None


class VoteResponse(BaseModel):
    """Response with vote confirmation."""
    proposal_id: str
    treasury_id: str
    choice: str
    stake_weight: int
    voted_at: str


class ResolutionRequest(BaseModel):
    """Request to execute resolution."""
    dispute_id: str
    executor_address: str


class ResolutionResponse(BaseModel):
    """Response with resolution details."""
    dispute_id: str
    status: str
    payout_shares: Dict[str, int]
    executed_at: str


class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    version: str
    treasuries_count: int
    active_disputes: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check for the treasury API.

    Returns:
        API status and statistics
    """
    coordinator = get_treasury_coordinator()
    disputes = coordinator.list_disputes()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        treasuries_count=len(coordinator.treasuries),
        active_disputes=len([d for d in disputes if d.status in [
            DisputeStatus.OPEN, DisputeStatus.VOTING, DisputeStatus.MEDIATION
        ]]),
    )


# -----------------------------------------------------------------------------
# Treasury Management
# -----------------------------------------------------------------------------

@router.post("/register", response_model=TreasuryResponse)
async def register_treasury(request: TreasuryRegisterRequest) -> TreasuryResponse:
    """
    Register a new treasury for dispute coordination.

    Args:
        request: Treasury details

    Returns:
        Registered treasury
    """
    coordinator = get_treasury_coordinator()

    try:
        treasury_type = TreasuryType(request.treasury_type)
    except ValueError:
        raise HTTPException(400, f"Invalid treasury type: {request.treasury_type}")

    treasury = coordinator.register_treasury(
        name=request.name,
        treasury_type=treasury_type,
        signers=request.signers,
        signer_threshold=request.signer_threshold,
        metadata=request.metadata,
    )

    return TreasuryResponse(
        treasury_id=treasury.treasury_id,
        name=treasury.name,
        treasury_type=treasury.treasury_type.value,
        signers=treasury.signers,
        signer_threshold=treasury.signer_threshold,
        total_stake=treasury.total_stake,
        created_at=treasury.created_at.isoformat(),
    )


@router.get("/list", response_model=List[TreasuryResponse])
async def list_treasuries(
    treasury_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> List[TreasuryResponse]:
    """
    List registered treasuries.

    Args:
        treasury_type: Filter by type
        limit: Max results

    Returns:
        List of treasuries
    """
    coordinator = get_treasury_coordinator()
    treasuries = list(coordinator.treasuries.values())

    if treasury_type:
        try:
            t_type = TreasuryType(treasury_type)
            treasuries = [t for t in treasuries if t.treasury_type == t_type]
        except ValueError:
            raise HTTPException(400, f"Invalid treasury type: {treasury_type}")

    return [
        TreasuryResponse(
            treasury_id=t.treasury_id,
            name=t.name,
            treasury_type=t.treasury_type.value,
            signers=t.signers,
            signer_threshold=t.signer_threshold,
            total_stake=t.total_stake,
            created_at=t.created_at.isoformat(),
        )
        for t in treasuries[:limit]
    ]


@router.get("/{treasury_id}", response_model=TreasuryResponse)
async def get_treasury(treasury_id: str) -> TreasuryResponse:
    """
    Get treasury details.

    Args:
        treasury_id: Treasury identifier

    Returns:
        Treasury details
    """
    coordinator = get_treasury_coordinator()
    treasury = coordinator.get_treasury(treasury_id)

    if not treasury:
        raise HTTPException(404, f"Treasury not found: {treasury_id}")

    return TreasuryResponse(
        treasury_id=treasury.treasury_id,
        name=treasury.name,
        treasury_type=treasury.treasury_type.value,
        signers=treasury.signers,
        signer_threshold=treasury.signer_threshold,
        total_stake=treasury.total_stake,
        created_at=treasury.created_at.isoformat(),
    )


@router.post("/{treasury_id}/signer")
async def add_treasury_signer(
    treasury_id: str,
    signer_address: str,
    admin_address: str,
) -> Dict[str, Any]:
    """
    Add a signer to a treasury.

    Args:
        treasury_id: Treasury identifier
        signer_address: New signer address
        admin_address: Admin address (must be existing signer)

    Returns:
        Updated signer list
    """
    coordinator = get_treasury_coordinator()
    treasury = coordinator.get_treasury(treasury_id)

    if not treasury:
        raise HTTPException(404, f"Treasury not found: {treasury_id}")

    if admin_address.lower() not in [s.lower() for s in treasury.signers]:
        raise HTTPException(403, "Admin address not a signer")

    if signer_address.lower() in [s.lower() for s in treasury.signers]:
        raise HTTPException(400, "Signer already exists")

    treasury.signers.append(signer_address.lower())
    coordinator._save_state()

    return {
        "treasury_id": treasury_id,
        "signers": treasury.signers,
        "signer_count": len(treasury.signers),
    }


# -----------------------------------------------------------------------------
# Dispute Management
# -----------------------------------------------------------------------------

@router.post("/dispute/create", response_model=DisputeResponse)
async def create_dispute(request: DisputeCreateRequest) -> DisputeResponse:
    """
    Create a multi-treasury dispute.

    Args:
        request: Dispute details

    Returns:
        Created dispute
    """
    coordinator = get_treasury_coordinator()

    # Validate creator treasury
    creator = coordinator.get_treasury(request.creator_treasury_id)
    if not creator:
        raise HTTPException(404, f"Creator treasury not found: {request.creator_treasury_id}")

    # Validate creator address is a signer
    if request.creator_address.lower() not in [s.lower() for s in creator.signers]:
        raise HTTPException(403, "Creator address not a signer of creator treasury")

    # Validate involved treasuries
    for tid in request.involved_treasury_ids:
        if not coordinator.get_treasury(tid):
            raise HTTPException(404, f"Involved treasury not found: {tid}")

    dispute = coordinator.create_dispute(
        creator_treasury=request.creator_treasury_id,
        involved_treasuries=request.involved_treasury_ids,
        title=request.title,
        description_uri=request.description_uri,
        creator_address=request.creator_address,
        is_binding=request.is_binding,
    )

    return DisputeResponse(
        dispute_id=dispute.dispute_id,
        creator_treasury=dispute.creator_treasury,
        involved_treasuries=dispute.involved_treasuries,
        title=dispute.title,
        description_uri=dispute.description_uri,
        status=dispute.status.value,
        is_binding=dispute.is_binding,
        total_stake=dispute.total_stake,
        created_at=dispute.created_at.isoformat(),
    )


@router.get("/disputes", response_model=List[DisputeResponse])
async def list_disputes(
    status: Optional[str] = Query(None),
    treasury_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> List[DisputeResponse]:
    """
    List disputes.

    Args:
        status: Filter by status
        treasury_id: Filter by involved treasury
        limit: Max results

    Returns:
        List of disputes
    """
    coordinator = get_treasury_coordinator()
    disputes = coordinator.list_disputes()

    if status:
        try:
            d_status = DisputeStatus(status)
            disputes = [d for d in disputes if d.status == d_status]
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    if treasury_id:
        disputes = [
            d for d in disputes
            if treasury_id in d.involved_treasuries or d.creator_treasury == treasury_id
        ]

    return [
        DisputeResponse(
            dispute_id=d.dispute_id,
            creator_treasury=d.creator_treasury,
            involved_treasuries=d.involved_treasuries,
            title=d.title,
            description_uri=d.description_uri,
            status=d.status.value,
            is_binding=d.is_binding,
            total_stake=d.total_stake,
            created_at=d.created_at.isoformat(),
        )
        for d in disputes[:limit]
    ]


@router.get("/dispute/{dispute_id}")
async def get_dispute(dispute_id: str) -> Dict[str, Any]:
    """
    Get full dispute details.

    Args:
        dispute_id: Dispute identifier

    Returns:
        Dispute details with proposals and stakes
    """
    coordinator = get_treasury_coordinator()
    dispute = coordinator.get_dispute(dispute_id)

    if not dispute:
        raise HTTPException(404, f"Dispute not found: {dispute_id}")

    return dispute.to_dict()


# -----------------------------------------------------------------------------
# Staking
# -----------------------------------------------------------------------------

@router.post("/stake", response_model=StakeResponse)
async def stake_for_dispute(request: StakeRequest) -> StakeResponse:
    """
    Stake funds for a dispute.

    Stake determines voting weight.

    Args:
        request: Stake details

    Returns:
        Updated stake
    """
    coordinator = get_treasury_coordinator()

    if not coordinator.get_dispute(request.dispute_id):
        raise HTTPException(404, f"Dispute not found: {request.dispute_id}")

    treasury = coordinator.get_treasury(request.treasury_id)
    if not treasury:
        raise HTTPException(404, f"Treasury not found: {request.treasury_id}")

    if request.staker_address.lower() not in [s.lower() for s in treasury.signers]:
        raise HTTPException(403, "Staker address not a signer")

    success = coordinator.stake(
        dispute_id=request.dispute_id,
        treasury_id=request.treasury_id,
        stake_amount=request.stake_amount,
        staker_address=request.staker_address,
    )

    if not success:
        raise HTTPException(400, "Failed to stake")

    dispute = coordinator.get_dispute(request.dispute_id)
    treasury_stake = dispute.stakes.get(request.treasury_id, 0)

    return StakeResponse(
        dispute_id=request.dispute_id,
        treasury_id=request.treasury_id,
        total_stake=dispute.total_stake,
        stake_amount=treasury_stake,
    )


@router.get("/dispute/{dispute_id}/stakes")
async def get_dispute_stakes(dispute_id: str) -> Dict[str, Any]:
    """
    Get stakes for a dispute.

    Args:
        dispute_id: Dispute identifier

    Returns:
        Stake breakdown by treasury
    """
    coordinator = get_treasury_coordinator()
    dispute = coordinator.get_dispute(dispute_id)

    if not dispute:
        raise HTTPException(404, f"Dispute not found: {dispute_id}")

    return {
        "dispute_id": dispute_id,
        "total_stake": dispute.total_stake,
        "stakes_by_treasury": dispute.stakes,
        "stake_percentages": {
            tid: round(stake / dispute.total_stake * 100, 2)
            for tid, stake in dispute.stakes.items()
        } if dispute.total_stake > 0 else {},
    }


# -----------------------------------------------------------------------------
# Proposals
# -----------------------------------------------------------------------------

@router.post("/proposal/create", response_model=ProposalResponse)
async def create_proposal(request: ProposalCreateRequest) -> ProposalResponse:
    """
    Create a resolution proposal.

    Args:
        request: Proposal details

    Returns:
        Created proposal
    """
    coordinator = get_treasury_coordinator()

    try:
        proposal_type = ProposalType(request.proposal_type)
    except ValueError:
        raise HTTPException(400, f"Invalid proposal type: {request.proposal_type}")

    proposal = coordinator.create_proposal(
        dispute_id=request.dispute_id,
        treasury_id=request.treasury_id,
        proposal_type=proposal_type,
        title=request.title,
        description=request.description,
        ipfs_uri=request.ipfs_uri,
        payout_shares=request.payout_shares,
        proposer_address=request.proposer_address,
    )

    if not proposal:
        raise HTTPException(400, "Failed to create proposal")

    return ProposalResponse(
        proposal_id=proposal.proposal_id,
        dispute_id=proposal.dispute_id,
        treasury_id=proposal.treasury_id,
        proposal_type=proposal.proposal_type.value,
        title=proposal.title,
        description=proposal.description,
        status=proposal.status.value,
        stake_approved=proposal.stake_approved,
        stake_rejected=proposal.stake_rejected,
        stake_abstained=proposal.stake_abstained,
        created_at=proposal.created_at.isoformat(),
    )


@router.get("/dispute/{dispute_id}/proposals")
async def list_proposals(
    dispute_id: str,
    status: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    """
    List proposals for a dispute.

    Args:
        dispute_id: Dispute identifier
        status: Filter by status

    Returns:
        List of proposals
    """
    coordinator = get_treasury_coordinator()
    dispute = coordinator.get_dispute(dispute_id)

    if not dispute:
        raise HTTPException(404, f"Dispute not found: {dispute_id}")

    proposals = list(dispute.proposals.values())

    if status:
        try:
            p_status = ProposalStatus(status)
            proposals = [p for p in proposals if p.status == p_status]
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    return [p.to_dict() for p in proposals]


@router.get("/proposal/{proposal_id}")
async def get_proposal(proposal_id: str) -> Dict[str, Any]:
    """
    Get proposal details.

    Args:
        proposal_id: Proposal identifier

    Returns:
        Proposal details
    """
    coordinator = get_treasury_coordinator()

    for dispute in coordinator.disputes.values():
        if proposal_id in dispute.proposals:
            return dispute.proposals[proposal_id].to_dict()

    raise HTTPException(404, f"Proposal not found: {proposal_id}")


# -----------------------------------------------------------------------------
# Voting
# -----------------------------------------------------------------------------

@router.post("/vote", response_model=VoteResponse)
async def cast_vote(request: VoteRequest) -> VoteResponse:
    """
    Cast a vote on a proposal.

    Vote weight is proportional to stake.

    Args:
        request: Vote details

    Returns:
        Vote confirmation
    """
    coordinator = get_treasury_coordinator()

    try:
        choice = VoteChoice(request.choice)
    except ValueError:
        raise HTTPException(400, f"Invalid choice: {request.choice}")

    success = coordinator.vote(
        dispute_id=request.dispute_id,
        proposal_id=request.proposal_id,
        treasury_id=request.treasury_id,
        choice=choice,
        voter_address=request.voter_address,
    )

    if not success:
        raise HTTPException(400, "Failed to cast vote")

    dispute = coordinator.get_dispute(request.dispute_id)
    stake = dispute.stakes.get(request.treasury_id, 0)

    return VoteResponse(
        proposal_id=request.proposal_id,
        treasury_id=request.treasury_id,
        choice=request.choice,
        stake_weight=stake,
        voted_at=datetime.now().isoformat(),
    )


@router.get("/proposal/{proposal_id}/votes")
async def get_votes(proposal_id: str) -> Dict[str, Any]:
    """
    Get votes for a proposal.

    Args:
        proposal_id: Proposal identifier

    Returns:
        Voting breakdown
    """
    coordinator = get_treasury_coordinator()

    for dispute in coordinator.disputes.values():
        if proposal_id in dispute.proposals:
            proposal = dispute.proposals[proposal_id]

            return {
                "proposal_id": proposal_id,
                "total_stake": dispute.total_stake,
                "stake_approved": proposal.stake_approved,
                "stake_rejected": proposal.stake_rejected,
                "stake_abstained": proposal.stake_abstained,
                "votes_by_treasury": {
                    tid: v.to_dict() for tid, v in proposal.votes.items()
                },
                "approval_percentage": (
                    round(proposal.stake_approved / dispute.total_stake * 100, 2)
                    if dispute.total_stake > 0 else 0
                ),
            }

    raise HTTPException(404, f"Proposal not found: {proposal_id}")


# -----------------------------------------------------------------------------
# Resolution
# -----------------------------------------------------------------------------

@router.post("/resolve", response_model=ResolutionResponse)
async def execute_resolution(request: ResolutionRequest) -> ResolutionResponse:
    """
    Execute resolution of a dispute.

    Only callable when a proposal has passed.

    Args:
        request: Resolution request

    Returns:
        Resolution details
    """
    coordinator = get_treasury_coordinator()

    dispute = coordinator.get_dispute(request.dispute_id)
    if not dispute:
        raise HTTPException(404, f"Dispute not found: {request.dispute_id}")

    payout_shares = coordinator.execute_resolution(request.dispute_id)

    if payout_shares is None:
        raise HTTPException(400, "No passed proposal to execute")

    return ResolutionResponse(
        dispute_id=request.dispute_id,
        status="resolved",
        payout_shares=payout_shares,
        executed_at=datetime.now().isoformat(),
    )


@router.post("/dispute/{dispute_id}/mediate")
async def escalate_to_mediation(
    dispute_id: str,
    treasury_id: str,
    mediator_address: str,
) -> Dict[str, Any]:
    """
    Escalate dispute to mediation.

    Args:
        dispute_id: Dispute identifier
        treasury_id: Requesting treasury
        mediator_address: Mediator address

    Returns:
        Updated dispute status
    """
    coordinator = get_treasury_coordinator()

    dispute = coordinator.get_dispute(dispute_id)
    if not dispute:
        raise HTTPException(404, f"Dispute not found: {dispute_id}")

    if treasury_id not in dispute.involved_treasuries and treasury_id != dispute.creator_treasury:
        raise HTTPException(403, "Treasury not involved in dispute")

    success = coordinator.escalate_to_mediation(dispute_id, mediator_address)

    if not success:
        raise HTTPException(400, "Cannot escalate to mediation")

    dispute = coordinator.get_dispute(dispute_id)

    return {
        "dispute_id": dispute_id,
        "status": dispute.status.value,
        "mediator": dispute.mediator,
        "message": "Dispute escalated to mediation",
    }


# -----------------------------------------------------------------------------
# Statistics
# -----------------------------------------------------------------------------

@router.get("/stats")
async def get_statistics() -> Dict[str, Any]:
    """
    Get treasury coordination statistics.

    Returns:
        Aggregate statistics
    """
    coordinator = get_treasury_coordinator()
    disputes = coordinator.list_disputes()

    total_stake = sum(d.total_stake for d in disputes)
    resolved = [d for d in disputes if d.status == DisputeStatus.RESOLVED]
    avg_stake = total_stake / len(disputes) if disputes else 0

    return {
        "treasury_count": len(coordinator.treasuries),
        "total_disputes": len(disputes),
        "active_disputes": len([
            d for d in disputes if d.status in [
                DisputeStatus.OPEN, DisputeStatus.VOTING, DisputeStatus.MEDIATION
            ]
        ]),
        "resolved_disputes": len(resolved),
        "total_stake_locked": total_stake,
        "average_stake": round(avg_stake, 2),
        "binding_disputes": len([d for d in disputes if d.is_binding]),
        "advisory_disputes": len([d for d in disputes if not d.is_binding]),
        "by_status": {
            status.value: len([d for d in disputes if d.status == status])
            for status in DisputeStatus
        },
    }


@router.get("/treasury/{treasury_id}/stats")
async def get_treasury_stats(treasury_id: str) -> Dict[str, Any]:
    """
    Get statistics for a treasury.

    Args:
        treasury_id: Treasury identifier

    Returns:
        Treasury statistics
    """
    coordinator = get_treasury_coordinator()
    treasury = coordinator.get_treasury(treasury_id)

    if not treasury:
        raise HTTPException(404, f"Treasury not found: {treasury_id}")

    disputes = coordinator.list_disputes()
    involved = [
        d for d in disputes
        if treasury_id in d.involved_treasuries or d.creator_treasury == treasury_id
    ]

    total_staked = sum(
        d.stakes.get(treasury_id, 0) for d in involved
    )

    return {
        "treasury_id": treasury_id,
        "name": treasury.name,
        "total_disputes": len(involved),
        "as_creator": len([d for d in involved if d.creator_treasury == treasury_id]),
        "as_participant": len([d for d in involved if treasury_id in d.involved_treasuries]),
        "total_staked": total_staked,
        "current_active": len([
            d for d in involved if d.status in [
                DisputeStatus.OPEN, DisputeStatus.VOTING, DisputeStatus.MEDIATION
            ]
        ]),
        "resolved": len([d for d in involved if d.status == DisputeStatus.RESOLVED]),
    }
