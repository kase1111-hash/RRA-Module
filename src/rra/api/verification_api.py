# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Verification API endpoints for RRA Module.

Provides REST API endpoints for:
- Code verification and quality checks
- Repository categorization
- README metadata extraction
- Blockchain purchase link generation
"""

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from rra.api.auth import verify_api_key, optional_api_key


router = APIRouter(prefix="/api/verify", tags=["verification"])


# Request/Response Models
class VerifyRequest(BaseModel):
    """Request to verify a repository."""

    repo_url: str = Field(..., description="GitHub repository URL to verify")
    owner_address: Optional[str] = Field(
        None, description="Owner's Ethereum address for blockchain registration"
    )
    network: str = Field("testnet", description="Blockchain network (mainnet, testnet, localhost)")
    skip_tests: bool = Field(False, description="Skip running actual tests")
    skip_security: bool = Field(False, description="Skip security scanning")


class CheckResult(BaseModel):
    """Result of a single verification check."""

    name: str
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None


class VerificationResponse(BaseModel):
    """Response from code verification."""

    repo_url: str
    overall_status: str
    score: float
    checks: List[CheckResult]
    verified_at: str


class CategoryResponse(BaseModel):
    """Response from repository categorization."""

    primary_category: str
    subcategory: Optional[str] = None
    confidence: float
    tags: List[str]
    technologies: List[str]
    frameworks: List[str]


class ReadmeMetadataResponse(BaseModel):
    """Response from README parsing."""

    title: str
    description: str
    short_description: str
    features: List[str]
    technologies: List[str]
    has_examples: bool
    has_api_docs: bool


class PurchaseLinkResponse(BaseModel):
    """Purchase link for a license tier."""

    url: str
    network: str
    tier: str
    price_display: str
    ip_asset_id: str


class MarketplaceListingResponse(BaseModel):
    """Complete marketplace listing."""

    repo_url: str
    repo_name: str
    description: str
    category: str
    ip_asset_id: str
    verification_score: float
    purchase_links: List[PurchaseLinkResponse]
    tags: List[str]
    technologies: List[str]


class FullVerificationResponse(BaseModel):
    """Complete verification response with all data."""

    verification: VerificationResponse
    category: CategoryResponse
    readme: ReadmeMetadataResponse
    marketplace: Optional[MarketplaceListingResponse] = None


# In-memory cache for verification results
_verification_cache: Dict[str, Dict[str, Any]] = {}


@router.post("/check", response_model=FullVerificationResponse)
async def verify_repository(
    request: VerifyRequest,
    background_tasks: BackgroundTasks,
    _auth: bool = Depends(verify_api_key),
) -> FullVerificationResponse:
    """
    Verify a GitHub repository and generate marketplace listing.

    This endpoint:
    1. Clones the repository
    2. Runs code verification (tests, linting, security)
    3. Parses README and extracts metadata
    4. Categorizes the repository
    5. Generates blockchain purchase links

    Args:
        request: Verification request parameters

    Returns:
        Complete verification results with marketplace listing
    """
    from rra.ingestion.repo_ingester import RepoIngester

    try:
        # Initialize ingester with verification enabled
        ingester = RepoIngester(
            verify_code=True,
            categorize=True,
            generate_blockchain_links=bool(request.owner_address),
            owner_address=request.owner_address,
            network=request.network,
        )

        # Override verifier settings
        ingester.verifier.skip_tests = request.skip_tests
        ingester.verifier.skip_security = request.skip_security

        # Ingest and verify the repository
        kb = ingester.ingest(request.repo_url)

        # Build response
        verification = VerificationResponse(
            repo_url=kb.repo_url,
            overall_status=(
                kb.verification.get("overall_status", "unknown") if kb.verification else "unknown"
            ),
            score=kb.verification.get("score", 0.0) if kb.verification else 0.0,
            checks=[
                CheckResult(**check)
                for check in (kb.verification.get("checks", []) if kb.verification else [])
            ],
            verified_at=kb.verification.get("verified_at", "") if kb.verification else "",
        )

        category = CategoryResponse(
            primary_category=(
                kb.category.get("primary_category", "other") if kb.category else "other"
            ),
            subcategory=kb.category.get("subcategory") if kb.category else None,
            confidence=kb.category.get("confidence", 0.0) if kb.category else 0.0,
            tags=kb.category.get("tags", []) if kb.category else [],
            technologies=kb.category.get("technologies", []) if kb.category else [],
            frameworks=kb.category.get("frameworks", []) if kb.category else [],
        )

        readme = ReadmeMetadataResponse(
            title=kb.readme_metadata.get("title", "") if kb.readme_metadata else "",
            description=kb.readme_metadata.get("description", "") if kb.readme_metadata else "",
            short_description=(
                kb.readme_metadata.get("short_description", "") if kb.readme_metadata else ""
            ),
            features=kb.readme_metadata.get("features", []) if kb.readme_metadata else [],
            technologies=kb.readme_metadata.get("technologies", []) if kb.readme_metadata else [],
            has_examples=(
                kb.readme_metadata.get("has_examples", False) if kb.readme_metadata else False
            ),
            has_api_docs=(
                kb.readme_metadata.get("has_api_docs", False) if kb.readme_metadata else False
            ),
        )

        marketplace = None
        if kb.blockchain_links:
            marketplace = MarketplaceListingResponse(
                repo_url=kb.blockchain_links.get("repo_url", ""),
                repo_name=kb.blockchain_links.get("repo_name", ""),
                description=kb.blockchain_links.get("description", ""),
                category=kb.blockchain_links.get("category", ""),
                ip_asset_id=kb.blockchain_links.get("ip_asset_id", ""),
                verification_score=kb.blockchain_links.get("verification_score", 0.0),
                purchase_links=[
                    PurchaseLinkResponse(
                        url=link.get("url", ""),
                        network=link.get("network", ""),
                        tier=link.get("tier", ""),
                        price_display=link.get("price_display", ""),
                        ip_asset_id=link.get("ip_asset_id", ""),
                    )
                    for link in kb.blockchain_links.get("purchase_links", [])
                ],
                tags=kb.blockchain_links.get("tags", []),
                technologies=kb.blockchain_links.get("technologies", []),
            )

        # Cache the result
        cache_key = kb.repo_url.lower().strip().rstrip(".git")
        _verification_cache[cache_key] = {
            "verification": verification.model_dump(),
            "category": category.model_dump(),
            "readme": readme.model_dump(),
            "marketplace": marketplace.model_dump() if marketplace else None,
        }

        return FullVerificationResponse(
            verification=verification,
            category=category,
            readme=readme,
            marketplace=marketplace,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.get("/status/{repo_id}", response_model=Optional[FullVerificationResponse])
async def get_verification_status(
    repo_id: str,
    _auth: Optional[bool] = Depends(optional_api_key),
) -> Optional[FullVerificationResponse]:
    """
    Get cached verification status for a repository.

    Args:
        repo_id: Repository ID (hash of URL)

    Returns:
        Cached verification results if available
    """
    # Check cache
    for key, value in _verification_cache.items():
        if repo_id in key or key.endswith(repo_id):
            return FullVerificationResponse(
                verification=VerificationResponse(**value["verification"]),
                category=CategoryResponse(**value["category"]),
                readme=ReadmeMetadataResponse(**value["readme"]),
                marketplace=(
                    MarketplaceListingResponse(**value["marketplace"])
                    if value["marketplace"]
                    else None
                ),
            )

    raise HTTPException(status_code=404, detail="Verification not found")


@router.get("/purchase-links/{repo_id}", response_model=List[PurchaseLinkResponse])
async def get_purchase_links(
    repo_id: str,
    owner_address: str = Query(..., description="Owner's Ethereum address"),
    network: str = Query("testnet", description="Blockchain network"),
    _auth: Optional[bool] = Depends(optional_api_key),
) -> List[PurchaseLinkResponse]:
    """
    Generate purchase links for a repository.

    Args:
        repo_id: Repository ID or URL
        owner_address: Owner's Ethereum address
        network: Blockchain network

    Returns:
        List of purchase links for different license tiers
    """
    from rra.verification.blockchain_link import BlockchainLinkGenerator, NetworkType

    try:
        network_type = NetworkType(network)
    except ValueError:
        network_type = NetworkType.TESTNET

    generator = BlockchainLinkGenerator(network=network_type)

    # Generate links with default pricing
    pricing = {
        "standard": 0.05,
        "premium": 0.15,
        "enterprise": 0.50,
    }

    # Use repo_id as the URL if it looks like a URL
    repo_url = repo_id if "github.com" in repo_id else f"https://github.com/{repo_id}"

    ip_asset_id = generator.generate_ip_asset_id(repo_url, owner_address)
    links = generator.generate_all_tier_links(
        repo_url=repo_url,
        ip_asset_id=ip_asset_id,
        pricing=pricing,
    )

    return [
        PurchaseLinkResponse(
            url=link.url,
            network=link.network.value,
            tier=link.tier.value,
            price_display=link.price_display,
            ip_asset_id=link.ip_asset_id,
        )
        for link in links
    ]


@router.get("/widget/{repo_id}")
async def get_embed_widget(
    repo_id: str,
    owner_address: str = Query(..., description="Owner's Ethereum address"),
    network: str = Query("testnet", description="Blockchain network"),
    theme: str = Query("light", description="Widget theme (light/dark)"),
    _auth: Optional[bool] = Depends(optional_api_key),
) -> Dict[str, str]:
    """
    Generate an embeddable widget for a repository.

    Args:
        repo_id: Repository ID or URL
        owner_address: Owner's Ethereum address
        network: Blockchain network
        theme: Widget theme (light/dark)

    Returns:
        HTML widget code for embedding
    """
    from rra.verification.blockchain_link import BlockchainLinkGenerator, NetworkType

    try:
        network_type = NetworkType(network)
    except ValueError:
        network_type = NetworkType.TESTNET

    generator = BlockchainLinkGenerator(network=network_type)

    # Generate listing
    repo_url = repo_id if "github.com" in repo_id else f"https://github.com/{repo_id}"

    pricing = {
        "standard": 0.05,
        "premium": 0.15,
        "enterprise": 0.50,
    }

    # Check if we have cached verification data
    cache_key = repo_url.lower().strip().rstrip(".git")
    cached = _verification_cache.get(cache_key)

    listing = generator.generate_marketplace_listing(
        repo_url=repo_url,
        repo_name=repo_url.split("/")[-1].replace(".git", ""),
        description=cached["readme"]["short_description"] if cached else "Software License",
        category=cached["category"]["primary_category"] if cached else "other",
        owner_address=owner_address,
        pricing=pricing,
        verification_score=cached["verification"]["score"] if cached else 0.0,
        tags=cached["category"]["tags"] if cached else [],
        technologies=cached["category"]["technologies"] if cached else [],
    )

    html = generator.generate_embed_widget(listing, theme=theme)

    return {"html": html, "repo_url": repo_url, "ip_asset_id": listing.ip_asset_id}


@router.post("/categorize")
async def categorize_repository(
    repo_url: str = Query(..., description="GitHub repository URL"),
    _auth: bool = Depends(verify_api_key),
) -> CategoryResponse:
    """
    Categorize a repository without full verification.

    This is a lightweight endpoint that only categorizes the repository
    without running tests or security scans.

    Args:
        repo_url: GitHub repository URL

    Returns:
        Category classification
    """
    from rra.ingestion.repo_ingester import RepoIngester

    try:
        ingester = RepoIngester(
            verify_code=False,
            categorize=True,
            generate_blockchain_links=False,
        )

        kb = ingester.ingest(repo_url)

        return CategoryResponse(
            primary_category=(
                kb.category.get("primary_category", "other") if kb.category else "other"
            ),
            subcategory=kb.category.get("subcategory") if kb.category else None,
            confidence=kb.category.get("confidence", 0.0) if kb.category else 0.0,
            tags=kb.category.get("tags", []) if kb.category else [],
            technologies=kb.category.get("technologies", []) if kb.category else [],
            frameworks=kb.category.get("frameworks", []) if kb.category else [],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")


@router.get("/explorer-link/{ip_asset_id}")
async def get_explorer_link(
    ip_asset_id: str,
    network: str = Query("testnet", description="Blockchain network"),
    _auth: Optional[bool] = Depends(optional_api_key),
) -> Dict[str, str]:
    """
    Get Story Protocol explorer link for an IP Asset.

    Args:
        ip_asset_id: Story Protocol IP Asset ID
        network: Blockchain network

    Returns:
        Explorer URL and related links
    """
    from rra.verification.blockchain_link import BlockchainLinkGenerator, NetworkType

    try:
        network_type = NetworkType(network)
    except ValueError:
        network_type = NetworkType.TESTNET

    generator = BlockchainLinkGenerator(network=network_type)

    return {
        "explorer_url": generator.generate_explorer_link(ip_asset_id),
        "view_link": generator.generate_deep_link(ip_asset_id, action="view"),
        "purchase_link": generator.generate_deep_link(ip_asset_id, action="purchase"),
        "network": network,
    }
