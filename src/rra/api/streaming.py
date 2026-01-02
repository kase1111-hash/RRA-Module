# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Streaming Payments API endpoints for RRA Module.

Provides REST API endpoints for:
- Creating streaming subscriptions
- Managing payment streams
- Checking access status
- Stream analytics
"""

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel, Field, field_validator

from rra.api.auth import verify_api_key

from rra.integrations.superfluid import (
    SuperfluidManager,
)
from rra.access.stream_controller import StreamAccessController, AccessLevel


# =============================================================================
# Input Validation Utilities
# =============================================================================

ETH_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")


def validate_eth_address(address: str) -> bool:
    """
    Validate Ethereum address format.

    Args:
        address: Address to validate

    Returns:
        True if valid Ethereum address format
    """
    return bool(ETH_ADDRESS_PATTERN.match(address))


router = APIRouter(prefix="/api/streaming", tags=["streaming-payments"])

# Initialize managers
sf_manager = SuperfluidManager()
access_controller = StreamAccessController(sf_manager)


# Request/Response models
class CreateStreamRequest(BaseModel):
    repo_id: str = Field(..., min_length=1, max_length=100)
    buyer_address: str
    seller_address: str
    monthly_price_usd: float = Field(..., gt=0, le=1000000)
    token: str = Field(default="USDCx", pattern=r"^[A-Za-z0-9]+x?$")
    grace_period_hours: int = Field(default=24, ge=0, le=8760)  # Max 1 year

    @field_validator("buyer_address", "seller_address")
    @classmethod
    def validate_eth_addresses(cls, v: str) -> str:
        """Validate Ethereum address format."""
        if not ETH_ADDRESS_PATTERN.match(v):
            raise ValueError(
                "Invalid Ethereum address format. Expected: 0x followed by 40 hex characters"
            )
        return v.lower()

    @field_validator("repo_id")
    @classmethod
    def validate_repo_id(cls, v: str) -> str:
        """Validate repo ID format."""
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid repo_id format")
        return v


class CreateStreamResponse(BaseModel):
    license_id: str
    repo_id: str
    buyer_address: str
    seller_address: str
    flow_rate: int
    monthly_cost: float
    token: str
    status: str
    created_at: str


class StreamStatusResponse(BaseModel):
    license_id: str
    status: str
    flow_rate: int
    monthly_cost: float
    elapsed_seconds: int
    total_paid: float
    buyer: str
    seller: str
    grace_period_remaining: Optional[int] = None
    will_revoke_at: Optional[str] = None


class AccessCheckResponse(BaseModel):
    has_access: bool
    reason: str
    license_id: Optional[str] = None
    repo_id: Optional[str] = None
    buyer: Optional[str] = None
    status: Optional[str] = None
    grace_ends_at: Optional[str] = None
    grace_remaining_seconds: Optional[int] = None


class StreamProposalRequest(BaseModel):
    repo_name: str
    monthly_price: float
    token: str = "USDCx"


class StreamProposalResponse(BaseModel):
    proposal_text: str
    monthly_price: float
    flow_rate: int
    per_second_rate: float
    token: str
    network: str


class StreamStatsResponse(BaseModel):
    total_licenses: int
    active_streams: int
    stopped_streams: int
    revoked_licenses: int
    total_monthly_revenue_usd: float
    network: str


class FlowRateCalculation(BaseModel):
    monthly_usd: float
    flow_rate_wei: int
    per_second_usd: float
    token: str


# Endpoints
@router.post("/create", response_model=CreateStreamResponse)
async def create_streaming_license(
    request: CreateStreamRequest,
    background_tasks: BackgroundTasks,
    authenticated: bool = Depends(verify_api_key),
) -> CreateStreamResponse:
    """
    Create a new streaming subscription license.

    This creates a pending streaming license that can be activated
    once the buyer approves the Superfluid stream on-chain.

    Args:
        request: Stream creation parameters

    Returns:
        Created license details
    """
    try:
        license = sf_manager.create_streaming_license(
            repo_id=request.repo_id,
            buyer_address=request.buyer_address,
            seller_address=request.seller_address,
            monthly_price_usd=request.monthly_price_usd,
            token=request.token,
            grace_period_hours=request.grace_period_hours,
        )

        return CreateStreamResponse(
            license_id=license.license_id,
            repo_id=license.repo_id,
            buyer_address=license.buyer_address,
            seller_address=license.seller_address,
            flow_rate=license.flow_rate,
            monthly_cost=license.monthly_cost_usd,
            token=license.token,
            status=license.status.value,
            created_at=license.start_time.isoformat(),
        )

    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/activate/{license_id}")
async def activate_stream(
    license_id: str,
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Activate a pending streaming license.

    In production, this confirms the on-chain Superfluid stream
    has been created and starts the access grant.

    Args:
        license_id: License to activate

    Returns:
        Activation result
    """
    try:
        result = await sf_manager.activate_stream(license_id)

        # Grant access
        await access_controller.grant_access(license_id, AccessLevel.FULL)

        return result

    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/stop/{license_id}")
async def stop_stream(
    license_id: str,
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Stop a streaming license.

    The license will enter the grace period before full revocation.

    Args:
        license_id: License to stop

    Returns:
        Stop result with grace period info
    """
    try:
        result = await sf_manager.stop_stream(license_id)

        license = sf_manager.get_license(license_id)
        if license:
            result["grace_period_hours"] = license.grace_period_seconds / 3600
            result["grace_ends_at"] = (
                (
                    license.stop_time
                    + __import__("datetime").timedelta(seconds=license.grace_period_seconds)
                ).isoformat()
                if license.stop_time
                else None
            )

        return result

    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/status/{license_id}", response_model=StreamStatusResponse)
async def get_stream_status(
    license_id: str,
    authenticated: bool = Depends(verify_api_key),
) -> StreamStatusResponse:
    """
    Get the current status of a streaming license.

    Args:
        license_id: License to check

    Returns:
        Current status and payment details
    """
    try:
        result = await sf_manager.check_stream_status(license_id)
        return StreamStatusResponse(**result)

    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/access/{license_id}", response_model=AccessCheckResponse)
async def check_access(
    license_id: str,
    authenticated: bool = Depends(verify_api_key),
) -> AccessCheckResponse:
    """
    Check if a license has valid access.

    Args:
        license_id: License to check

    Returns:
        Access status
    """
    result = await access_controller.check_access(license_id)
    return AccessCheckResponse(**result)


@router.get("/access/buyer/{repo_id}", response_model=AccessCheckResponse)
async def check_access_by_buyer(
    repo_id: str,
    buyer: str = Query(..., description="Buyer wallet address"),
    authenticated: bool = Depends(verify_api_key),
) -> AccessCheckResponse:
    """
    Check if a buyer has access to a specific repository.

    Args:
        repo_id: Repository ID
        buyer: Buyer wallet address

    Returns:
        Access status
    """
    result = await access_controller.check_access_by_buyer(repo_id, buyer)
    return AccessCheckResponse(**result)


@router.get("/licenses/buyer/{buyer_address}")
async def get_buyer_licenses(
    buyer_address: str,
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Get all streaming licenses for a buyer.

    Args:
        buyer_address: Buyer wallet address

    Returns:
        List of licenses
    """
    licenses = sf_manager.get_licenses_for_buyer(buyer_address)
    return {
        "buyer": buyer_address,
        "licenses": [license.to_dict() for license in licenses],
        "total": len(licenses),
    }


@router.get("/licenses/repo/{repo_id}")
async def get_repo_licenses(
    repo_id: str,
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Get all streaming licenses for a repository.

    Args:
        repo_id: Repository ID

    Returns:
        List of licenses
    """
    licenses = sf_manager.get_licenses_for_repo(repo_id)
    return {
        "repo_id": repo_id,
        "licenses": [license.to_dict() for license in licenses],
        "total": len(licenses),
    }


@router.get("/active")
async def get_active_licenses(
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Get all active streaming licenses.

    Returns:
        List of active licenses
    """
    licenses = sf_manager.get_active_licenses()
    return {
        "licenses": [license.to_dict() for license in licenses],
        "total": len(licenses),
    }


@router.post("/revoke-expired")
async def revoke_expired_licenses(
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Revoke all licenses that have exceeded their grace period.

    Returns:
        List of revoked license IDs
    """
    revoked = await sf_manager.revoke_expired_licenses()

    for license_id in revoked:
        await access_controller.revoke_access(license_id)

    return {
        "revoked": revoked,
        "count": len(revoked),
    }


@router.post("/proposal", response_model=StreamProposalResponse)
async def generate_stream_proposal(
    request: StreamProposalRequest,
    authenticated: bool = Depends(verify_api_key),
) -> StreamProposalResponse:
    """
    Generate a negotiation proposal for streaming subscription.

    Args:
        request: Proposal parameters

    Returns:
        Formatted proposal text and details
    """
    flow_rate = sf_manager.calculate_flow_rate(request.monthly_price)
    per_second = request.monthly_price / sf_manager.SECONDS_PER_MONTH

    proposal_text = sf_manager.generate_stream_proposal(
        repo_name=request.repo_name,
        monthly_price=request.monthly_price,
        token=request.token,
    )

    return StreamProposalResponse(
        proposal_text=proposal_text,
        monthly_price=request.monthly_price,
        flow_rate=flow_rate,
        per_second_rate=per_second,
        token=request.token,
        network=sf_manager.network.value,
    )


@router.get("/calculate-rate", response_model=FlowRateCalculation)
async def calculate_flow_rate(
    monthly_usd: float = Query(..., gt=0, description="Monthly price in USD"),
    token: str = Query("USDCx", description="Super token"),
    authenticated: bool = Depends(verify_api_key),
) -> FlowRateCalculation:
    """
    Calculate Superfluid flow rate from monthly price.

    Args:
        monthly_usd: Monthly price in USD
        token: Super token name

    Returns:
        Flow rate calculation
    """
    flow_rate = sf_manager.calculate_flow_rate(monthly_usd)
    per_second = monthly_usd / sf_manager.SECONDS_PER_MONTH

    return FlowRateCalculation(
        monthly_usd=monthly_usd,
        flow_rate_wei=flow_rate,
        per_second_usd=per_second,
        token=token,
    )


@router.get("/tokens")
async def get_supported_tokens(
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Get list of supported super tokens on current network.

    Returns:
        List of token names and addresses
    """
    tokens = sf_manager.get_supported_tokens()
    return {
        "network": sf_manager.network.value,
        "tokens": tokens,
        "addresses": {token: sf_manager.get_token_address(token) for token in tokens},
    }


@router.get("/stats", response_model=StreamStatsResponse)
async def get_streaming_stats(
    authenticated: bool = Depends(verify_api_key),
) -> StreamStatsResponse:
    """
    Get streaming payment statistics.

    Returns:
        Overall streaming stats
    """
    stats = sf_manager.get_stats()
    return StreamStatsResponse(**stats)


@router.get("/summary/{repo_id}")
async def get_repo_streaming_summary(
    repo_id: str,
    authenticated: bool = Depends(verify_api_key),
) -> dict:
    """
    Get streaming summary for a repository.

    Args:
        repo_id: Repository ID

    Returns:
        Comprehensive streaming summary
    """
    summary = await access_controller.get_access_summary(repo_id)
    return summary
