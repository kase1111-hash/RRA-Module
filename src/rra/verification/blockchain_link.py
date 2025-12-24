# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Blockchain link generator module.

Generates purchase links to Story Protocol entries for software licensing.
Creates links that allow buyers to purchase licenses directly on-chain.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class NetworkType(str, Enum):
    """Supported blockchain networks."""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    LOCALHOST = "localhost"


class LicenseTier(str, Enum):
    """Available license tiers."""
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


@dataclass
class PurchaseLink:
    """Generated purchase link for blockchain licensing."""
    url: str
    network: NetworkType
    ip_asset_id: str
    license_terms_id: Optional[str] = None
    tier: LicenseTier = LicenseTier.STANDARD
    price_wei: int = 0
    price_display: str = "0 ETH"
    currency: str = "ETH"
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "network": self.network.value,
            "ip_asset_id": self.ip_asset_id,
            "license_terms_id": self.license_terms_id,
            "tier": self.tier.value,
            "price_wei": self.price_wei,
            "price_display": self.price_display,
            "currency": self.currency,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Generate markdown-formatted link."""
        return f"[Purchase {self.tier.value.capitalize()} License - {self.price_display}]({self.url})"

    def to_html(self) -> str:
        """Generate HTML button for embedding."""
        return f'''<a href="{self.url}"
            class="rra-purchase-btn"
            data-tier="{self.tier.value}"
            data-price="{self.price_display}"
            target="_blank"
            rel="noopener noreferrer">
            Purchase {self.tier.value.capitalize()} License - {self.price_display}
        </a>'''


@dataclass
class MarketplaceListing:
    """Complete marketplace listing for a repository."""
    repo_url: str
    repo_name: str
    description: str
    category: str
    ip_asset_id: str
    owner_address: str
    purchase_links: List[PurchaseLink] = field(default_factory=list)
    verification_score: float = 0.0
    verified_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "description": self.description,
            "category": self.category,
            "ip_asset_id": self.ip_asset_id,
            "owner_address": self.owner_address,
            "purchase_links": [link.to_dict() for link in self.purchase_links],
            "verification_score": self.verification_score,
            "verified_at": self.verified_at,
            "tags": self.tags,
            "technologies": self.technologies,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class BlockchainLinkGenerator:
    """
    Generates purchase links to Story Protocol blockchain entries.

    Creates links that allow buyers to:
    - View the IP Asset on Story Protocol
    - Purchase license tokens
    - View license terms
    - Connect wallet and complete transaction
    """

    # Story Protocol explorer URLs
    EXPLORER_URLS = {
        NetworkType.MAINNET: "https://explorer.story.foundation",
        NetworkType.TESTNET: "https://aeneid.explorer.story.foundation",
        NetworkType.LOCALHOST: "http://localhost:3000",
    }

    # Story Protocol Chain IDs
    CHAIN_IDS = {
        NetworkType.MAINNET: 1514,  # Story Homer
        NetworkType.TESTNET: 1315,  # Story Aeneid
        NetworkType.LOCALHOST: 31337,
    }

    # RRA Marketplace URLs (frontend)
    MARKETPLACE_URLS = {
        NetworkType.MAINNET: "https://marketplace.rra.io",
        NetworkType.TESTNET: "https://testnet.marketplace.rra.io",
        NetworkType.LOCALHOST: "http://localhost:3001",
    }

    def __init__(
        self,
        network: NetworkType = NetworkType.TESTNET,
        marketplace_base_url: Optional[str] = None,
    ):
        """
        Initialize the blockchain link generator.

        Args:
            network: Target blockchain network
            marketplace_base_url: Custom marketplace URL (overrides defaults)
        """
        self.network = network
        self.marketplace_url = marketplace_base_url or self.MARKETPLACE_URLS[network]
        self.explorer_url = self.EXPLORER_URLS[network]
        self.chain_id = self.CHAIN_IDS[network]

    def generate_ip_asset_id(self, repo_url: str, owner_address: str) -> str:
        """
        Generate a deterministic IP Asset ID from repository URL and owner.

        This creates a consistent ID that can be used before the asset is
        actually registered on-chain.

        Args:
            repo_url: Repository URL
            owner_address: Owner's Ethereum address

        Returns:
            Deterministic IP Asset ID (bytes32 hex)
        """
        # Create deterministic hash from repo URL and owner
        data = f"{repo_url.lower().strip().rstrip('.git')}:{owner_address.lower()}"
        hash_bytes = hashlib.sha256(data.encode()).digest()
        return f"0x{hash_bytes.hex()}"

    def generate_purchase_link(
        self,
        repo_url: str,
        ip_asset_id: str,
        tier: LicenseTier = LicenseTier.STANDARD,
        license_terms_id: Optional[str] = None,
        price_eth: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PurchaseLink:
        """
        Generate a purchase link for a specific license tier.

        Args:
            repo_url: Repository URL
            ip_asset_id: Story Protocol IP Asset ID
            tier: License tier
            license_terms_id: Optional specific license terms ID
            price_eth: Price in ETH
            metadata: Additional metadata to include

        Returns:
            PurchaseLink with URL and details
        """
        # Generate repo ID for URL
        repo_id = self._generate_repo_id(repo_url)

        # Build purchase URL
        params = {
            "ipAsset": ip_asset_id,
            "tier": tier.value,
            "chain": self.chain_id,
        }
        if license_terms_id:
            params["terms"] = license_terms_id

        # Create URL with query params
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.marketplace_url}/purchase/{repo_id}?{query_string}"

        # Calculate price in wei
        price_wei = int(price_eth * 10**18)
        price_display = f"{price_eth} ETH" if price_eth > 0 else "Contact for pricing"

        return PurchaseLink(
            url=url,
            network=self.network,
            ip_asset_id=ip_asset_id,
            license_terms_id=license_terms_id,
            tier=tier,
            price_wei=price_wei,
            price_display=price_display,
            currency="ETH",
            metadata=metadata or {},
        )

    def generate_all_tier_links(
        self,
        repo_url: str,
        ip_asset_id: str,
        pricing: Dict[str, float],
        license_terms: Optional[Dict[str, str]] = None,
    ) -> List[PurchaseLink]:
        """
        Generate purchase links for all license tiers.

        Args:
            repo_url: Repository URL
            ip_asset_id: Story Protocol IP Asset ID
            pricing: Dict mapping tier name to price in ETH
            license_terms: Optional dict mapping tier to license terms ID

        Returns:
            List of PurchaseLinks for each tier
        """
        links = []
        license_terms = license_terms or {}

        tier_map = {
            "standard": LicenseTier.STANDARD,
            "premium": LicenseTier.PREMIUM,
            "enterprise": LicenseTier.ENTERPRISE,
            "custom": LicenseTier.CUSTOM,
        }

        for tier_name, price in pricing.items():
            tier = tier_map.get(tier_name.lower(), LicenseTier.CUSTOM)
            terms_id = license_terms.get(tier_name)

            link = self.generate_purchase_link(
                repo_url=repo_url,
                ip_asset_id=ip_asset_id,
                tier=tier,
                license_terms_id=terms_id,
                price_eth=price,
            )
            links.append(link)

        return links

    def generate_explorer_link(self, ip_asset_id: str) -> str:
        """
        Generate a link to view the IP Asset on Story Protocol explorer.

        Args:
            ip_asset_id: Story Protocol IP Asset ID

        Returns:
            Explorer URL
        """
        return f"{self.explorer_url}/ip-asset/{ip_asset_id}"

    def generate_license_terms_link(self, license_terms_id: str) -> str:
        """
        Generate a link to view license terms on Story Protocol.

        Args:
            license_terms_id: License terms ID

        Returns:
            License terms URL
        """
        return f"{self.explorer_url}/license-terms/{license_terms_id}"

    def generate_marketplace_listing(
        self,
        repo_url: str,
        repo_name: str,
        description: str,
        category: str,
        owner_address: str,
        pricing: Dict[str, float],
        verification_score: float = 0.0,
        tags: Optional[List[str]] = None,
        technologies: Optional[List[str]] = None,
        license_terms: Optional[Dict[str, str]] = None,
    ) -> MarketplaceListing:
        """
        Generate a complete marketplace listing with purchase links.

        Args:
            repo_url: Repository URL
            repo_name: Repository name
            description: Short description
            category: Primary category
            owner_address: Owner's Ethereum address
            pricing: Dict mapping tier to price in ETH
            verification_score: Verification score (0-100)
            tags: List of tags
            technologies: List of technologies
            license_terms: Optional dict mapping tier to license terms ID

        Returns:
            MarketplaceListing with all purchase links
        """
        # Generate IP Asset ID
        ip_asset_id = self.generate_ip_asset_id(repo_url, owner_address)

        # Generate purchase links for all tiers
        purchase_links = self.generate_all_tier_links(
            repo_url=repo_url,
            ip_asset_id=ip_asset_id,
            pricing=pricing,
            license_terms=license_terms,
        )

        now = datetime.now().isoformat()

        return MarketplaceListing(
            repo_url=repo_url,
            repo_name=repo_name,
            description=description,
            category=category,
            ip_asset_id=ip_asset_id,
            owner_address=owner_address,
            purchase_links=purchase_links,
            verification_score=verification_score,
            verified_at=now if verification_score > 0 else None,
            tags=tags or [],
            technologies=technologies or [],
            created_at=now,
            updated_at=now,
        )

    def generate_embed_widget(
        self,
        listing: MarketplaceListing,
        theme: str = "light",
    ) -> str:
        """
        Generate an embeddable widget HTML for the listing.

        Args:
            listing: MarketplaceListing to embed
            theme: Widget theme ('light' or 'dark')

        Returns:
            HTML string for embedding
        """
        links_html = "\n".join(
            f'<div class="rra-tier">{link.to_html()}</div>'
            for link in listing.purchase_links
        )

        explorer_link = self.generate_explorer_link(listing.ip_asset_id)

        return f'''
<div class="rra-widget" data-theme="{theme}">
    <div class="rra-header">
        <h3>{listing.repo_name}</h3>
        <span class="rra-category">{listing.category}</span>
    </div>
    <p class="rra-description">{listing.description}</p>
    <div class="rra-verification">
        <span class="rra-score">Verification Score: {listing.verification_score:.1f}%</span>
    </div>
    <div class="rra-tiers">
        {links_html}
    </div>
    <div class="rra-footer">
        <a href="{explorer_link}" target="_blank" rel="noopener">View on Story Protocol</a>
        <span class="rra-powered">Powered by RRA Module</span>
    </div>
</div>
<style>
.rra-widget {{
    font-family: system-ui, sans-serif;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
    max-width: 400px;
    background: {('#ffffff' if theme == 'light' else '#1a1a2e')};
    color: {('#1a1a2e' if theme == 'light' else '#ffffff')};
}}
.rra-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}}
.rra-header h3 {{
    margin: 0;
    font-size: 18px;
}}
.rra-category {{
    font-size: 12px;
    background: #6366f1;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
}}
.rra-description {{
    font-size: 14px;
    color: #64748b;
    margin: 8px 0;
}}
.rra-verification {{
    font-size: 12px;
    margin: 8px 0;
}}
.rra-tiers {{
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 12px 0;
}}
.rra-purchase-btn {{
    display: block;
    text-align: center;
    padding: 10px 16px;
    background: #6366f1;
    color: white;
    text-decoration: none;
    border-radius: 6px;
    font-weight: 500;
}}
.rra-purchase-btn:hover {{
    background: #4f46e5;
}}
.rra-footer {{
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #e2e8f0;
}}
.rra-footer a {{
    color: #6366f1;
}}
.rra-powered {{
    color: #94a3b8;
}}
</style>
'''

    def _generate_repo_id(self, repo_url: str) -> str:
        """Generate a short repository ID from URL."""
        normalized = repo_url.lower().strip().rstrip('.git')
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]

    def generate_deep_link(
        self,
        ip_asset_id: str,
        action: str = "view",
        wallet_address: Optional[str] = None,
    ) -> str:
        """
        Generate a deep link for specific actions.

        Args:
            ip_asset_id: Story Protocol IP Asset ID
            action: Action type ('view', 'purchase', 'license')
            wallet_address: Optional wallet address to pre-fill

        Returns:
            Deep link URL
        """
        base = f"{self.marketplace_url}/{action}/{ip_asset_id}"
        params = [f"chain={self.chain_id}"]

        if wallet_address:
            params.append(f"wallet={wallet_address}")

        if params:
            return f"{base}?{'&'.join(params)}"
        return base

    def generate_qr_data(self, purchase_link: PurchaseLink) -> str:
        """
        Generate data for QR code (URL + metadata).

        Args:
            purchase_link: PurchaseLink to encode

        Returns:
            JSON string for QR code
        """
        return json.dumps({
            "url": purchase_link.url,
            "network": purchase_link.network.value,
            "tier": purchase_link.tier.value,
            "price": purchase_link.price_display,
            "asset": purchase_link.ip_asset_id,
        })
