# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Marketplace API endpoints for RRA Module.

Provides REST API endpoints for:
- Repository discovery and search
- Agent details and statistics
- Featured repositories
- Categories and filtering
"""

import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from rra.api.auth import verify_api_key, optional_api_key
from rra.ingestion.knowledge_base import KnowledgeBase
from rra.config.market_config import MarketConfig


router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# Response models
class RepositoryListing(BaseModel):
    id: str
    url: str
    name: str
    owner: str
    description: str
    kb_path: str
    updated_at: str
    languages: List[str]
    files: int
    stars: Optional[int] = None
    forks: Optional[int] = None
    price_eth: Optional[float] = None  # Target price in ETH for sorting


class MarketConfigResponse(BaseModel):
    license_identifier: str
    license_model: str
    target_price: str
    floor_price: str
    negotiation_style: Optional[str] = None
    features: List[str] = []
    developer_wallet: Optional[str] = None
    copyright_holder: Optional[str] = None


class AgentDetailsResponse(BaseModel):
    repository: RepositoryListing
    market_config: Optional[MarketConfigResponse] = None
    statistics: Dict[str, Any]
    reputation: Dict[str, Any]


class AgentStatsResponse(BaseModel):
    total_sales: int
    total_revenue: str
    average_price: str
    reputation_score: float
    active_negotiations: int


class SearchResponse(BaseModel):
    repositories: List[RepositoryListing]
    total: int
    page: int
    per_page: int


# Helper functions
def generate_repo_id(repo_url: str) -> str:
    """Generate a unique, stable repo ID from URL."""
    normalized = repo_url.lower().strip().rstrip('.git')
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def parse_repo_url(url: str) -> Dict[str, str]:
    """Extract owner and name from GitHub URL."""
    import re
    match = re.search(r'github\.com/([^/]+)/([^/\.]+)', url)
    if match:
        return {'owner': match.group(1), 'name': match.group(2)}
    return {'owner': 'unknown', 'name': url.split('/')[-1]}


def kb_to_listing(kb: KnowledgeBase) -> RepositoryListing:
    """Convert a KnowledgeBase to a RepositoryListing."""
    parsed = parse_repo_url(kb.repo_url)

    # Extract price from market_config if available
    price_eth: Optional[float] = None
    if kb.market_config:
        try:
            price_str = kb.market_config.target_price
            # Handle formats like "0.05 ETH" or "0.05"
            price_eth = float(price_str.replace(' ETH', '').replace('ETH', '').strip())
        except (ValueError, AttributeError):
            pass

    return RepositoryListing(
        id=generate_repo_id(kb.repo_url),
        url=kb.repo_url,
        name=parsed['name'],
        owner=parsed['owner'],
        description=kb.get_summary().get('description', 'No description'),
        kb_path=str(kb.kb_path) if hasattr(kb, 'kb_path') else '',
        updated_at=kb.updated_at.isoformat() if hasattr(kb, 'updated_at') else datetime.now().isoformat(),
        languages=kb.statistics.get('languages', []),
        files=kb.statistics.get('code_files', 0),
        stars=None,  # Would need GitHub API integration
        forks=None,
        price_eth=price_eth,
    )


def market_config_to_response(config: MarketConfig) -> MarketConfigResponse:
    """Convert a MarketConfig to response model."""
    return MarketConfigResponse(
        license_identifier=config.license_identifier,
        license_model=config.license_model.value if hasattr(config.license_model, 'value') else str(config.license_model),
        target_price=config.target_price,
        floor_price=config.floor_price,
        negotiation_style=config.negotiation_style.value if hasattr(config, 'negotiation_style') and hasattr(config.negotiation_style, 'value') else None,
        features=config.features if hasattr(config, 'features') else [],
        developer_wallet=config.developer_wallet if hasattr(config, 'developer_wallet') else None,
        copyright_holder=config.copyright_holder if hasattr(config, 'copyright_holder') else None,
    )


# Endpoints
@router.get("/repos", response_model=SearchResponse)
async def list_marketplace_repos(
    q: Optional[str] = Query(None, description="Search query"),
    language: Optional[str] = Query(None, description="Filter by language"),
    category: Optional[str] = Query(None, description="Filter by category"),
    price_min: Optional[float] = Query(None, description="Minimum price in ETH"),
    price_max: Optional[float] = Query(None, description="Maximum price in ETH"),
    sort_by: str = Query("recent", description="Sort by: recent, popular, price_low, price_high"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    _auth: Optional[bool] = Depends(optional_api_key),
) -> SearchResponse:
    """
    List all repositories in the marketplace with optional filtering.

    Supports:
    - Text search across name, description, and languages
    - Language filtering
    - Price range filtering
    - Multiple sort options
    - Pagination
    """
    kb_dir = Path("agent_knowledge_bases")

    if not kb_dir.exists():
        return SearchResponse(repositories=[], total=0, page=page, per_page=per_page)

    repositories: List[RepositoryListing] = []

    for kb_file in kb_dir.glob("*_kb.json"):
        try:
            kb = KnowledgeBase.load(kb_file)
            listing = kb_to_listing(kb)

            # Apply filters
            if q:
                q_lower = q.lower()
                searchable = f"{listing.name} {listing.description} {' '.join(listing.languages)}".lower()
                if q_lower not in searchable:
                    continue

            if language:
                if not any(lang.lower() == language.lower() for lang in listing.languages):
                    continue

            # Price filtering would need market_config
            if kb.market_config and (price_min is not None or price_max is not None):
                try:
                    price = float(kb.market_config.target_price.replace(' ETH', ''))
                    if price_min is not None and price < price_min:
                        continue
                    if price_max is not None and price > price_max:
                        continue
                except (ValueError, AttributeError):
                    pass

            repositories.append(listing)

        except Exception:
            continue

    # Sort
    if sort_by == "popular":
        repositories.sort(key=lambda r: r.stars or 0, reverse=True)
    elif sort_by == "price_low":
        # Sort by price ascending, repos without price go to end
        repositories.sort(key=lambda r: (r.price_eth is None, r.price_eth or 0))
    elif sort_by == "price_high":
        # Sort by price descending, repos without price go to end
        repositories.sort(key=lambda r: (r.price_eth is None, -(r.price_eth or 0)))
    else:  # recent
        repositories.sort(key=lambda r: r.updated_at, reverse=True)

    # Pagination
    total = len(repositories)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = repositories[start:end]

    return SearchResponse(
        repositories=paginated,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/featured", response_model=List[RepositoryListing])
async def get_featured_repos(
    _auth: Optional[bool] = Depends(optional_api_key),
) -> List[RepositoryListing]:
    """
    Get featured repositories for the homepage.

    Returns top repositories based on activity and quality metrics.
    """
    kb_dir = Path("agent_knowledge_bases")

    if not kb_dir.exists():
        return []

    repositories: List[RepositoryListing] = []

    for kb_file in kb_dir.glob("*_kb.json"):
        try:
            kb = KnowledgeBase.load(kb_file)
            repositories.append(kb_to_listing(kb))
        except Exception:
            continue

    # Sort by files (as proxy for quality) and return top 6
    repositories.sort(key=lambda r: r.files, reverse=True)
    return repositories[:6]


@router.get("/categories", response_model=List[str])
async def get_categories(
    _auth: Optional[bool] = Depends(optional_api_key),
) -> List[str]:
    """
    Get available repository categories.

    Returns unique languages/categories found in the marketplace.
    """
    kb_dir = Path("agent_knowledge_bases")
    categories = set()

    if kb_dir.exists():
        for kb_file in kb_dir.glob("*_kb.json"):
            try:
                kb = KnowledgeBase.load(kb_file)
                categories.update(kb.statistics.get('languages', []))
            except Exception:
                continue

    return sorted(list(categories))


@router.get("/agent/{repo_id}/details", response_model=AgentDetailsResponse)
async def get_agent_details(
    repo_id: str,
    _auth: Optional[bool] = Depends(optional_api_key),
) -> AgentDetailsResponse:
    """
    Get detailed information about a specific agent/repository.

    Args:
        repo_id: Unique repository ID

    Returns:
        Complete agent details including config, stats, and reputation
    """
    kb_dir = Path("agent_knowledge_bases")

    if not kb_dir.exists():
        raise HTTPException(status_code=404, detail="Repository not found")

    # Find the matching KB
    for kb_file in kb_dir.glob("*_kb.json"):
        try:
            kb = KnowledgeBase.load(kb_file)
            if generate_repo_id(kb.repo_url) == repo_id:
                listing = kb_to_listing(kb)

                market_config_response = None
                if kb.market_config:
                    market_config_response = market_config_to_response(kb.market_config)

                return AgentDetailsResponse(
                    repository=listing,
                    market_config=market_config_response,
                    statistics={
                        "code_files": kb.statistics.get('code_files', 0),
                        "languages": kb.statistics.get('languages', []),
                        "total_lines": kb.statistics.get('total_lines', 0),
                        "test_coverage": kb.statistics.get('test_coverage'),
                    },
                    reputation={
                        "score": 4.5,  # Placeholder - would come from reputation tracker
                        "total_sales": 0,
                        "total_revenue": "0 ETH",
                    },
                )
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="Repository not found")


@router.get("/agent/{repo_id}/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    repo_id: str,
    _auth: bool = Depends(verify_api_key),
) -> AgentStatsResponse:
    """
    Get statistics for a specific agent.

    Args:
        repo_id: Unique repository ID

    Returns:
        Agent statistics including sales, revenue, and reputation
    """
    # In production, this would query the blockchain and database
    # For now, return placeholder data
    return AgentStatsResponse(
        total_sales=0,
        total_revenue="0 ETH",
        average_price="0 ETH",
        reputation_score=4.5,
        active_negotiations=0,
    )
