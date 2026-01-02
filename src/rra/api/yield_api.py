# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Yield-Bearing License Tokens API endpoints.

Provides REST API endpoints for:
- Creating and managing yield pools
- Staking and unstaking licenses
- Claiming yield rewards
- Pool and staker analytics
"""

import re
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field, field_validator

from rra.api.auth import verify_api_key

from rra.defi.yield_tokens import (
    StakingManager,
    YieldPool,
    YieldStrategy,
    StakedLicense,
    create_staking_manager,
)


# =============================================================================
# Input Validation
# =============================================================================

ETH_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")


def validate_eth_address(address: str) -> bool:
    """Validate Ethereum address format."""
    return bool(ETH_ADDRESS_PATTERN.match(address))


router = APIRouter(prefix="/api/yield", tags=["yield-tokens"])

# Initialize staking manager
staking_manager = create_staking_manager("data/staking")


# =============================================================================
# Request/Response Models
# =============================================================================


class CreatePoolRequest(BaseModel):
    """Request model for creating a yield pool."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    strategy: str = Field(default="hybrid")
    base_apy: float = Field(default=0.05, ge=0, le=1.0)  # 0-100% APY
    min_stake_duration_days: int = Field(default=0, ge=0, le=365)
    max_stakes: int = Field(default=0, ge=0)  # 0 = unlimited

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate yield strategy."""
        valid = [s.value for s in YieldStrategy]
        if v not in valid:
            raise ValueError(f"Invalid strategy. Must be one of: {valid}")
        return v


class PoolResponse(BaseModel):
    """Response model for pool information."""

    pool_id: str
    name: str
    description: str
    strategy: str
    base_apy: float
    min_stake_duration_days: int
    max_stakes: int
    total_value_locked: float
    stake_count: int
    total_revenue: float
    pending_revenue: float
    active: bool
    created_at: str


class StakeLicenseRequest(BaseModel):
    """Request model for staking a license."""

    pool_id: str = Field(..., min_length=1, max_length=50)
    license_id: str = Field(..., min_length=1, max_length=100)
    token_id: int = Field(..., ge=0)
    repo_url: str = Field(..., min_length=1, max_length=500)
    license_value: float = Field(..., gt=0, le=1000000)  # Max 1M ETH
    staker_address: str
    lock_days: int = Field(default=0, ge=0, le=365)

    @field_validator("staker_address")
    @classmethod
    def validate_staker_address(cls, v: str) -> str:
        """Validate Ethereum address format."""
        if not ETH_ADDRESS_PATTERN.match(v):
            raise ValueError("Invalid Ethereum address format")
        return v.lower()

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Validate repository URL."""
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Invalid repository URL format")
        return v


class StakeResponse(BaseModel):
    """Response model for stake information."""

    stake_id: str
    license_id: str
    token_id: int
    repo_url: str
    license_value: float
    staker_address: str
    pool_id: str
    staked_at: str
    unlock_time: Optional[str]
    earned_yield: float
    total_claimed: float
    active: bool
    is_locked: bool
    stake_duration_days: float


class ClaimYieldResponse(BaseModel):
    """Response model for yield claim."""

    stake_id: str
    claimed_amount: float
    new_balance: float
    total_claimed: float
    claimed_at: str


class StakerSummaryResponse(BaseModel):
    """Response model for staker summary."""

    staker_address: str
    active_stakes: int
    total_stakes: int
    total_value_staked: float
    unclaimed_yield: float
    total_claimed: float
    projected_earnings: dict
    stakes: List[dict]


class PoolStatsResponse(BaseModel):
    """Response model for pool statistics."""

    pool_id: str
    name: str
    strategy: str
    base_apy: float
    total_value_locked: float
    active_stake_count: int
    total_stake_count: int
    total_yield_distributed: float
    average_stake_duration_days: float
    unique_stakers: int
    pending_revenue: float


class AddRevenueRequest(BaseModel):
    """Request model for adding revenue to a pool."""

    amount: float = Field(..., gt=0, le=1000000)


class DistributionResponse(BaseModel):
    """Response model for revenue distribution."""

    pool_id: str
    total_distributed: float
    stake_count: int
    distributions: dict
    distributed_at: str


# =============================================================================
# Pool Management Endpoints
# =============================================================================


@router.post("/pools", response_model=PoolResponse)
async def create_pool(
    request: CreatePoolRequest,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Create a new yield pool.

    Pools allow license holders to stake their licenses and earn yield
    from licensing revenue distribution.
    """
    try:
        strategy = YieldStrategy(request.strategy)
        pool = staking_manager.create_pool(
            name=request.name,
            description=request.description,
            strategy=strategy,
            base_apy=request.base_apy,
            min_stake_duration_days=request.min_stake_duration_days,
            max_stakes=request.max_stakes,
        )

        return PoolResponse(
            pool_id=pool.pool_id,
            name=pool.name,
            description=pool.description,
            strategy=pool.strategy.value,
            base_apy=pool.base_apy,
            min_stake_duration_days=pool.min_stake_duration_days,
            max_stakes=pool.max_stakes,
            total_value_locked=pool.total_value_locked,
            stake_count=pool.stake_count,
            total_revenue=pool.total_revenue,
            pending_revenue=pool.pending_revenue,
            active=pool.active,
            created_at=pool.created_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pools", response_model=List[PoolResponse])
async def list_pools(
    active_only: bool = Query(True),
    authenticated: bool = Depends(verify_api_key),
):
    """List all yield pools."""
    pools = staking_manager.list_pools(active_only=active_only)

    return [
        PoolResponse(
            pool_id=p.pool_id,
            name=p.name,
            description=p.description,
            strategy=p.strategy.value,
            base_apy=p.base_apy,
            min_stake_duration_days=p.min_stake_duration_days,
            max_stakes=p.max_stakes,
            total_value_locked=p.total_value_locked,
            stake_count=p.stake_count,
            total_revenue=p.total_revenue,
            pending_revenue=p.pending_revenue,
            active=p.active,
            created_at=p.created_at.isoformat(),
        )
        for p in pools
    ]


@router.get("/pools/{pool_id}", response_model=PoolResponse)
async def get_pool(
    pool_id: str,
    authenticated: bool = Depends(verify_api_key),
):
    """Get details of a specific pool."""
    pool = staking_manager.get_pool(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")

    return PoolResponse(
        pool_id=pool.pool_id,
        name=pool.name,
        description=pool.description,
        strategy=pool.strategy.value,
        base_apy=pool.base_apy,
        min_stake_duration_days=pool.min_stake_duration_days,
        max_stakes=pool.max_stakes,
        total_value_locked=pool.total_value_locked,
        stake_count=pool.stake_count,
        total_revenue=pool.total_revenue,
        pending_revenue=pool.pending_revenue,
        active=pool.active,
        created_at=pool.created_at.isoformat(),
    )


@router.get("/pools/{pool_id}/stats", response_model=PoolStatsResponse)
async def get_pool_stats(
    pool_id: str,
    authenticated: bool = Depends(verify_api_key),
):
    """Get detailed statistics for a pool."""
    try:
        stats = staking_manager.get_pool_stats(pool_id)
        return PoolStatsResponse(**stats)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/pools/{pool_id}/revenue", response_model=PoolResponse)
async def add_pool_revenue(
    pool_id: str,
    request: AddRevenueRequest,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Add revenue to a pool for distribution.

    This revenue will be distributed to stakers based on the pool's strategy.
    """
    try:
        staking_manager.add_pool_revenue(pool_id, request.amount)
        pool = staking_manager.get_pool(pool_id)
        if pool is None:
            raise HTTPException(status_code=404, detail=f"Pool {pool_id} not found")

        return PoolResponse(
            pool_id=pool.pool_id,
            name=pool.name,
            description=pool.description,
            strategy=pool.strategy.value,
            base_apy=pool.base_apy,
            min_stake_duration_days=pool.min_stake_duration_days,
            max_stakes=pool.max_stakes,
            total_value_locked=pool.total_value_locked,
            stake_count=pool.stake_count,
            total_revenue=pool.total_revenue,
            pending_revenue=pool.pending_revenue,
            active=pool.active,
            created_at=pool.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/pools/{pool_id}/distribute", response_model=DistributionResponse)
async def distribute_pool_revenue(
    pool_id: str,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Distribute pending revenue to all stakers in the pool.

    Revenue is distributed proportionally based on the pool's yield strategy.
    """
    try:
        distributions = staking_manager.distribute_pool_revenue(pool_id)

        return DistributionResponse(
            pool_id=pool_id,
            total_distributed=sum(distributions.values()),
            stake_count=len(distributions),
            distributions=distributions,
            distributed_at=datetime.now().isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# Staking Endpoints
# =============================================================================


@router.post("/stake", response_model=StakeResponse)
async def stake_license(
    request: StakeLicenseRequest,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Stake a license in a yield pool.

    Staked licenses earn yield based on the pool's strategy.
    Lock periods provide bonus yield multipliers.
    """
    try:
        stake = staking_manager.stake_license(
            pool_id=request.pool_id,
            license_id=request.license_id,
            token_id=request.token_id,
            repo_url=request.repo_url,
            license_value=request.license_value,
            staker_address=request.staker_address,
            lock_days=request.lock_days,
        )

        return StakeResponse(
            stake_id=stake.stake_id,
            license_id=stake.license_id,
            token_id=stake.token_id,
            repo_url=stake.repo_url,
            license_value=stake.license_value,
            staker_address=stake.staker_address,
            pool_id=stake.pool_id,
            staked_at=stake.staked_at.isoformat(),
            unlock_time=stake.unlock_time.isoformat() if stake.unlock_time else None,
            earned_yield=stake.earned_yield,
            total_claimed=stake.total_claimed,
            active=stake.active,
            is_locked=stake.is_locked,
            stake_duration_days=stake.stake_duration_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/stake/{stake_id}", response_model=StakeResponse)
async def unstake_license(
    stake_id: str,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Unstake a license.

    Cannot unstake if the license is still in its lock period.
    Any unclaimed yield will be added to the stake before unstaking.
    """
    try:
        stake = staking_manager.unstake_license(stake_id)

        return StakeResponse(
            stake_id=stake.stake_id,
            license_id=stake.license_id,
            token_id=stake.token_id,
            repo_url=stake.repo_url,
            license_value=stake.license_value,
            staker_address=stake.staker_address,
            pool_id=stake.pool_id,
            staked_at=stake.staked_at.isoformat(),
            unlock_time=stake.unlock_time.isoformat() if stake.unlock_time else None,
            earned_yield=stake.earned_yield,
            total_claimed=stake.total_claimed,
            active=stake.active,
            is_locked=stake.is_locked,
            stake_duration_days=stake.stake_duration_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stake/{stake_id}", response_model=StakeResponse)
async def get_stake(
    stake_id: str,
    authenticated: bool = Depends(verify_api_key),
):
    """Get details of a specific stake."""
    stake = staking_manager.get_stake(stake_id)
    if not stake:
        raise HTTPException(status_code=404, detail="Stake not found")

    return StakeResponse(
        stake_id=stake.stake_id,
        license_id=stake.license_id,
        token_id=stake.token_id,
        repo_url=stake.repo_url,
        license_value=stake.license_value,
        staker_address=stake.staker_address,
        pool_id=stake.pool_id,
        staked_at=stake.staked_at.isoformat(),
        unlock_time=stake.unlock_time.isoformat() if stake.unlock_time else None,
        earned_yield=stake.earned_yield,
        total_claimed=stake.total_claimed,
        active=stake.active,
        is_locked=stake.is_locked,
        stake_duration_days=stake.stake_duration_days,
    )


@router.post("/stake/{stake_id}/claim", response_model=ClaimYieldResponse)
async def claim_yield(
    stake_id: str,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Claim earned yield for a stake.

    Calculates pending yield based on time since last claim and adds it
    to the claimable balance before processing the claim.
    """
    try:
        stake = staking_manager.get_stake(stake_id)
        if not stake:
            raise HTTPException(status_code=404, detail="Stake not found")

        claimed = staking_manager.claim_yield(stake_id)
        updated_stake = staking_manager.get_stake(stake_id)
        if updated_stake is None:
            raise HTTPException(status_code=404, detail="Stake not found after claim")

        return ClaimYieldResponse(
            stake_id=stake_id,
            claimed_amount=claimed,
            new_balance=updated_stake.earned_yield,
            total_claimed=updated_stake.total_claimed,
            claimed_at=datetime.now().isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Staker Analytics Endpoints
# =============================================================================


@router.get("/staker/{staker_address}", response_model=StakerSummaryResponse)
async def get_staker_summary(
    staker_address: str,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Get staking summary for an address.

    Includes all active stakes, total value staked, unclaimed yield,
    and projected future earnings.
    """
    if not validate_eth_address(staker_address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

    summary = staking_manager.get_staker_summary(staker_address)
    return StakerSummaryResponse(**summary)


@router.get("/staker/{staker_address}/stakes", response_model=List[StakeResponse])
async def get_staker_stakes(
    staker_address: str,
    active_only: bool = Query(True),
    authenticated: bool = Depends(verify_api_key),
):
    """Get all stakes for a staker."""
    if not validate_eth_address(staker_address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

    stakes = staking_manager.get_stakes_by_staker(staker_address)

    if active_only:
        stakes = [s for s in stakes if s.active]

    return [
        StakeResponse(
            stake_id=s.stake_id,
            license_id=s.license_id,
            token_id=s.token_id,
            repo_url=s.repo_url,
            license_value=s.license_value,
            staker_address=s.staker_address,
            pool_id=s.pool_id,
            staked_at=s.staked_at.isoformat(),
            unlock_time=s.unlock_time.isoformat() if s.unlock_time else None,
            earned_yield=s.earned_yield,
            total_claimed=s.total_claimed,
            active=s.active,
            is_locked=s.is_locked,
            stake_duration_days=s.stake_duration_days,
        )
        for s in stakes
    ]


# =============================================================================
# Overview Endpoints
# =============================================================================


@router.get("/overview")
async def get_yield_overview(
    authenticated: bool = Depends(verify_api_key),
):
    """
    Get overview of the yield-bearing license token system.

    Returns aggregate statistics across all pools and stakes.
    """
    pools = staking_manager.list_pools(active_only=False)
    all_stakes = list(staking_manager.stakes.values())
    active_stakes = [s for s in all_stakes if s.active]

    total_tvl = sum(p.total_value_locked for p in pools)
    total_revenue = sum(p.total_revenue for p in pools)
    total_distributed = sum(p.distributed_revenue for p in pools)
    pending_distribution = sum(p.pending_revenue for p in pools)

    unique_stakers = len(set(s.staker_address for s in active_stakes))

    return {
        "total_pools": len(pools),
        "active_pools": len([p for p in pools if p.active]),
        "total_stakes": len(all_stakes),
        "active_stakes": len(active_stakes),
        "unique_stakers": unique_stakers,
        "total_value_locked": total_tvl,
        "total_revenue_collected": total_revenue,
        "total_yield_distributed": total_distributed,
        "pending_distribution": pending_distribution,
        "strategies_available": [s.value for s in YieldStrategy],
        "timestamp": datetime.now().isoformat(),
    }
