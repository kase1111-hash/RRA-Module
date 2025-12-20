# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Deep Links API endpoints for RRA Module.

Provides REST API endpoints for:
- Generating deep links for repositories
- Resolving repo IDs to repository info
- Getting badges and embed codes
- QR code generation
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, HttpUrl

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
    agent_page: str
    chat_direct: str
    license_individual: str
    license_team: str
    license_enterprise: str
    qr_code: str
    qr_code_svg: str
    badge_markdown: str
    badge_html: str
    embed_script: str


class ResolveResponse(BaseModel):
    repo_url: str
    created_at: str
    agent_active: bool
    metadata: dict = {}


class BadgeRequest(BaseModel):
    repo_url: str
    style: str = "flat"
    label: str = "License This Repo"


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
    Generate all deep links for a repository.

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
        repo_url=mapping['repo_url'],
        created_at=mapping['created_at'],
        agent_active=mapping.get('agent_active', True),
        metadata={k: v for k, v in mapping.items()
                  if k not in ('repo_url', 'created_at', 'agent_active')}
    )


@router.post("/register", response_model=RegisterRepoResponse)
async def register_repo(
    request: RegisterRepoRequest,
    _auth: bool = Depends(verify_api_key),
) -> RegisterRepoResponse:
    """
    Register a repository for deep linking.

    This creates a permanent mapping from repo ID to URL and returns all generated links.

    Args:
        request: Repository URL and optional metadata

    Returns:
        Repository ID and all generated links
    """
    metadata = {}
    if request.owner:
        metadata['owner'] = request.owner
    if request.name:
        metadata['name'] = request.name
    if request.description:
        metadata['description'] = request.description

    repo_id = link_service.register_repo(request.repo_url, metadata)
    links = link_service.get_all_links(request.repo_url)

    return RegisterRepoResponse(
        repo_id=repo_id,
        links=LinksResponse(**links)
    )


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
    return {
        "repo_id": link_service.generate_repo_id(repo_url),
        "repo_url": repo_url
    }


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

    agent_url = link_service.get_agent_url(request.repo_url)
    badge_url = f"https://img.shields.io/badge/{quote(request.label)}-RRA-blue?style={request.style}"

    return BadgeResponse(
        markdown=link_service.generate_badge_markdown(
            request.repo_url, request.style, request.label
        ),
        html=link_service.generate_badge_html(
            request.repo_url, request.style, request.label
        ),
        url=badge_url
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
        URLs to PNG and SVG QR codes
    """
    # Resolve repo_id to URL first
    mapping = link_service.resolve_repo_id(repo_id)
    if mapping:
        repo_url = mapping['repo_url']
    else:
        # If not registered, construct URL from ID
        # This allows QR codes for any repo_id
        repo_url = repo_id

    from urllib.parse import quote
    agent_url = link_service.get_agent_url(repo_url) if mapping else f"{link_service.base_url}/agent/{repo_id}"
    encoded_url = quote(agent_url)

    return QRCodeResponse(
        png_url=f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}",
        svg_url=f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&format=svg&data={encoded_url}",
        size=size
    )


@router.get("/embed/{repo_id}")
async def get_embed_code(
    repo_id: str,
    _auth: Optional[bool] = Depends(optional_api_key),
) -> dict:
    """
    Get embeddable widget code for a repository.

    Args:
        repo_id: Repository ID

    Returns:
        JavaScript and HTML embed codes
    """
    mapping = link_service.resolve_repo_id(repo_id)
    base_url = link_service.base_url

    js_embed = f'''<!-- RRA Negotiation Widget -->
<div id="rra-widget-{repo_id}"></div>
<script src="{base_url}/embed.js" data-repo-id="{repo_id}"></script>'''

    iframe_embed = f'''<!-- RRA Negotiation iFrame -->
<iframe
  src="{base_url}/agent/{repo_id}/embed"
  width="400"
  height="600"
  frameborder="0"
  style="border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);"
></iframe>'''

    button_html = f'''<!-- RRA License Button -->
<a href="{base_url}/agent/{repo_id}"
   style="display: inline-block; padding: 12px 24px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-weight: 500;">
  License This Repository
</a>'''

    return {
        "repo_id": repo_id,
        "js_embed": js_embed,
        "iframe_embed": iframe_embed,
        "button_html": button_html,
        "repo_url": mapping['repo_url'] if mapping else None
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
