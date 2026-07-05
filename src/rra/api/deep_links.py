# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Deep Links API endpoints for RRA Module.

Provides REST API endpoints for:
- Generating purchase links for repositories
- Resolving repo IDs to repository info
- Getting badges and embeddable buy buttons
- QR code generation
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from rra.api.auth import verify_api_key, optional_api_key
from rra.services.deep_links import DeepLinkService

router = APIRouter(prefix="/api/links", tags=["deep-links"])

# Initialize service
link_service = DeepLinkService()


# Request/Response models
class GenerateLinksRequest(BaseModel):
    repo_url: str


class LinksResponse(BaseModel):
    repo_id: str
    purchase_page: str
    explorer_url: Optional[str] = None
    license_standard: str
    license_premium: str
    license_enterprise: str
    qr_code: str
    qr_code_svg: str
    badge_markdown: str
    badge_html: str
    embed_button: str


class ResolveResponse(BaseModel):
    repo_url: str
    created_at: str
    active: bool
    metadata: dict = {}


class BadgeRequest(BaseModel):
    repo_url: str
    style: str = "flat"
    label: str = "Buy License"


class BadgeResponse(BaseModel):
    markdown: str
    html: str
    url: str


class QRCodeResponse(BaseModel):
    png_url: str
    svg_url: str
    size: int


class RegisterRepoRequest(BaseModel):
    repo_url: str
    owner: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    ip_asset_id: Optional[str] = None
    license_terms_id: Optional[int] = None
    network: Optional[str] = None


class RegisterRepoResponse(BaseModel):
    repo_id: str
    links: LinksResponse


# Endpoints
@router.post("/generate", response_model=LinksResponse)
async def generate_links(
    request: GenerateLinksRequest,
    _auth: bool = Depends(verify_api_key),
) -> LinksResponse:
    """
    Generate all purchase links for a repository.

    Returns:
        All available link types for the repository
    """
    links = link_service.get_all_links(request.repo_url)
    return LinksResponse(**links)


@router.get("/resolve/{repo_id}", response_model=ResolveResponse)
async def resolve_repo_id(
    repo_id: str,
    _auth: Optional[bool] = Depends(optional_api_key),
) -> ResolveResponse:
    """
    Resolve a repository ID to its original URL and metadata.

    Args:
        repo_id: 12-character repository ID

    Returns:
        Repository URL and registration info
    """
    mapping = link_service.resolve_repo_id(repo_id)

    if not mapping:
        raise HTTPException(status_code=404, detail="Repository ID not found")

    return ResolveResponse(
        repo_url=mapping["repo_url"],
        created_at=mapping["created_at"],
        active=mapping.get("active", mapping.get("agent_active", True)),
        metadata={
            k: v
            for k, v in mapping.items()
            if k not in ("repo_url", "created_at", "active", "agent_active")
        },
    )


@router.post("/register", response_model=RegisterRepoResponse)
async def register_repo(
    request: RegisterRepoRequest,
    _auth: bool = Depends(verify_api_key),
) -> RegisterRepoResponse:
    """
    Register a repository for deep linking.

    This creates a permanent mapping from repo ID to URL and returns all
    generated links. Passing ip_asset_id / license_terms_id / network makes
    purchase links target the registered Story Protocol IP asset directly.

    Args:
        request: Repository URL and optional metadata

    Returns:
        Repository ID and all generated links
    """
    metadata = {}
    if request.owner:
        metadata["owner"] = request.owner
    if request.name:
        metadata["name"] = request.name
    if request.description:
        metadata["description"] = request.description
    if request.ip_asset_id:
        metadata["ip_asset_id"] = request.ip_asset_id
    if request.license_terms_id:
        metadata["license_terms_id"] = request.license_terms_id
    if request.network:
        metadata["network"] = request.network

    repo_id = link_service.register_repo(request.repo_url, metadata)
    links = link_service.get_all_links(request.repo_url)

    return RegisterRepoResponse(repo_id=repo_id, links=LinksResponse(**links))


@router.get("/id/{repo_url:path}")
async def get_repo_id(
    repo_url: str,
    _auth: Optional[bool] = Depends(optional_api_key),
) -> dict:
    """
    Get the repository ID for a given URL without registration.

    Args:
        repo_url: Repository URL

    Returns:
        Repository ID
    """
    return {"repo_id": link_service.generate_repo_id(repo_url), "repo_url": repo_url}


@router.post("/badge", response_model=BadgeResponse)
async def generate_badge(
    request: BadgeRequest,
    _auth: Optional[bool] = Depends(optional_api_key),
) -> BadgeResponse:
    """
    Generate a README badge for a repository.

    Args:
        request: Badge configuration

    Returns:
        Badge in multiple formats
    """
    from urllib.parse import quote

    badge_url = (
        f"https://img.shields.io/badge/{quote(request.label)}-Story_Protocol-6366f1"
        f"?style={request.style}"
    )

    return BadgeResponse(
        markdown=link_service.generate_badge_markdown(
            request.repo_url, request.style, request.label
        ),
        html=link_service.generate_badge_html(request.repo_url, request.style, request.label),
        url=badge_url,
    )


@router.get("/qr/{repo_id}", response_model=QRCodeResponse)
async def get_qr_code(
    repo_id: str,
    size: int = Query(200, ge=50, le=1000, description="QR code size in pixels"),
    _auth: Optional[bool] = Depends(optional_api_key),
) -> QRCodeResponse:
    """
    Get QR code URLs for a repository.

    Args:
        repo_id: Repository ID
        size: QR code size (50-1000 pixels)

    Returns:
        URLs to PNG and SVG QR codes encoding the purchase page URL
    """
    from urllib.parse import quote

    mapping = link_service.resolve_repo_id(repo_id)
    if mapping:
        purchase_url = link_service.get_purchase_url(mapping["repo_url"])
    else:
        # Not registered: the purchase page can still resolve by repo ID
        purchase_url = f"{link_service.base_url}?repo={repo_id}"

    encoded_url = quote(purchase_url, safe="")

    return QRCodeResponse(
        png_url=f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}",
        svg_url=f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&format=svg&data={encoded_url}",
        size=size,
    )


@router.get("/embed/{repo_id}")
async def get_embed_code(
    repo_id: str,
    _auth: Optional[bool] = Depends(optional_api_key),
) -> dict:
    """
    Get an embeddable buy button for a repository.

    Args:
        repo_id: Repository ID

    Returns:
        HTML buy-button embed code linking to the purchase page
    """
    mapping = link_service.resolve_repo_id(repo_id)

    if mapping:
        button_html = link_service.generate_embed_button(mapping["repo_url"])
        purchase_url = link_service.get_purchase_url(mapping["repo_url"])
    else:
        purchase_url = f"{link_service.base_url}?repo={repo_id}"
        button_html = (
            f'<a href="{purchase_url}" target="_blank" rel="noopener noreferrer" '
            'style="display: inline-block; padding: 12px 24px; background: #6366f1; '
            'color: white; text-decoration: none; border-radius: 6px; font-weight: 500;">'
            "Buy License</a>"
        )

    return {
        "repo_id": repo_id,
        "button_html": button_html,
        "purchase_url": purchase_url,
        "repo_url": mapping["repo_url"] if mapping else None,
    }


@router.get("/stats")
async def get_link_stats(
    _auth: bool = Depends(verify_api_key),
) -> dict:
    """
    Get statistics about registered deep links.

    Returns:
        Stats on registered repositories
    """
    return link_service.get_stats()
