# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Deep Links Service for RRA Module.

Generates shareable purchase links for repositories licensed on Story
Protocol. Every link points at a real surface:

- The hosted purchase page (buy-license.html), which reads
  ``?ipAsset=…&terms=…&network=…`` query parameters and lets a buyer mint
  a license token in one wallet interaction.
- The Story Protocol explorer page for the registered IP asset.

Also provides README badge, QR code, and embeddable buy-button generation,
all targeting the purchase URL.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlencode, quote


class DeepLinkService:
    """
    Generate and resolve purchase deep links for RRA repositories.

    Repositories are identified by a short stable ID derived from their
    URL. Registering a repository can attach its on-chain details
    (``ip_asset_id``, ``license_terms_id``, ``network``) so generated
    links carry everything the purchase page needs.
    """

    # Hosted purchase page (a static buy-license.html served from GitHub
    # Pages). Override with your own hosting via base_url.
    DEFAULT_BASE_URL = "https://kase1111-hash.github.io/RRA-Module/buy-license.html"

    # Story Protocol explorers
    EXPLORER_URLS = {
        "mainnet": "https://explorer.story.foundation",
        "testnet": "https://aeneid.explorer.story.foundation",
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        mappings_path: Optional[Path] = None,
        network: str = "mainnet",
    ):
        """
        Initialize the deep link service.

        Args:
            base_url: URL of the hosted purchase page (default: this repo's
                      GitHub Pages buy-license.html)
            mappings_path: Path to store repo ID mappings (default: agent_knowledge_bases/repo_mappings.json)
            network: Default Story Protocol network for explorer links
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.network = network if network in self.EXPLORER_URLS else "mainnet"
        self.mappings_path = mappings_path or Path("agent_knowledge_bases/repo_mappings.json")
        self._mappings: Dict[str, Dict[str, Any]] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """Load repo ID mappings from file."""
        if self.mappings_path.exists():
            try:
                with open(self.mappings_path, "r") as f:
                    self._mappings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._mappings = {}

    def _save_mappings(self) -> None:
        """Save repo ID mappings to file."""
        self.mappings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.mappings_path, "w") as f:
            json.dump(self._mappings, f, indent=2, default=str)

    def generate_repo_id(self, repo_url: str) -> str:
        """
        Generate a unique, stable repository ID from URL.

        Uses SHA-256 hash of normalized URL truncated to 12 characters.
        This ensures:
        - Consistent IDs for the same URL
        - Short, shareable IDs
        - Collision resistance for practical usage

        Args:
            repo_url: Repository URL (GitHub, GitLab, etc.)

        Returns:
            12-character hex ID
        """
        normalized = repo_url.lower().strip().rstrip(".git").rstrip("/")
        return hashlib.sha256(normalized.encode()).hexdigest()[:12]

    def register_repo(self, repo_url: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a repository and get its deep link ID.

        Args:
            repo_url: Repository URL
            metadata: Optional metadata. Recognized keys include
                      ``ip_asset_id``, ``license_terms_id``, and ``network``
                      (used to enrich purchase links), plus anything else
                      the caller wants to store (owner, name, description).

        Returns:
            Repository ID
        """
        repo_id = self.generate_repo_id(repo_url)

        self._mappings[repo_id] = {
            "repo_url": repo_url,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
            **(metadata or {}),
        }

        self._save_mappings()
        return repo_id

    def resolve_repo_id(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a repository ID to its mapping.

        Args:
            repo_id: Repository ID

        Returns:
            Mapping dict or None if not found
        """
        return self._mappings.get(repo_id)

    def get_purchase_url(self, repo_url: str, tier: Optional[str] = None) -> str:
        """
        Get the purchase page URL for a repository.

        If the repository was registered with on-chain details
        (ip_asset_id / license_terms_id / network), they are embedded as
        query parameters so the purchase page targets the right IP asset.

        Args:
            repo_url: Repository URL
            tier: Optional license tier name (e.g. 'standard', 'premium')

        Returns:
            Full purchase page URL
        """
        repo_id = self.generate_repo_id(repo_url)
        mapping = self._mappings.get(repo_id, {})

        params: Dict[str, Any] = {"repo": repo_id}
        if mapping.get("ip_asset_id"):
            params["ipAsset"] = mapping["ip_asset_id"]
        if mapping.get("license_terms_id"):
            params["terms"] = mapping["license_terms_id"]
        network = mapping.get("network", self.network)
        if network:
            params["network"] = network
        if tier:
            params["tier"] = tier

        return f"{self.base_url}?{urlencode(params)}"

    def get_license_url(self, repo_url: str, tier: str) -> str:
        """
        Get the purchase URL for a specific license tier.

        Args:
            repo_url: Repository URL
            tier: License tier name (e.g., 'standard', 'premium', 'enterprise')

        Returns:
            Purchase page URL for the tier
        """
        return self.get_purchase_url(repo_url, tier=tier)

    def get_explorer_url(self, repo_url: str) -> Optional[str]:
        """
        Get the Story Protocol explorer URL for a repository's IP asset.

        Args:
            repo_url: Repository URL

        Returns:
            Explorer IPA page URL, or None if no IP asset is registered
        """
        repo_id = self.generate_repo_id(repo_url)
        mapping = self._mappings.get(repo_id, {})
        ip_asset_id = mapping.get("ip_asset_id")
        if not ip_asset_id:
            return None
        network = mapping.get("network", self.network)
        explorer = self.EXPLORER_URLS.get(network, self.EXPLORER_URLS["mainnet"])
        return f"{explorer}/ipa/{ip_asset_id}"

    def generate_badge_markdown(
        self, repo_url: str, style: str = "flat", label: str = "Buy License"
    ) -> str:
        """
        Generate a README badge in Markdown format.

        Args:
            repo_url: Repository URL
            style: Badge style (flat, flat-square, plastic, for-the-badge)
            label: Badge label text

        Returns:
            Markdown badge code linking to the purchase page
        """
        purchase_url = self.get_purchase_url(repo_url)
        # Use shields.io for badge generation
        badge_url = (
            f"https://img.shields.io/badge/{quote(label)}-Story_Protocol-6366f1?style={style}"
        )
        return f"[![{label}]({badge_url})]({purchase_url})"

    def generate_badge_html(
        self, repo_url: str, style: str = "flat", label: str = "Buy License"
    ) -> str:
        """
        Generate a README badge in HTML format.

        Args:
            repo_url: Repository URL
            style: Badge style
            label: Badge label text

        Returns:
            HTML badge code linking to the purchase page
        """
        purchase_url = self.get_purchase_url(repo_url)
        badge_url = (
            f"https://img.shields.io/badge/{quote(label)}-Story_Protocol-6366f1?style={style}"
        )
        return f'<a href="{purchase_url}"><img src="{badge_url}" alt="{label}"></a>'

    def generate_embed_button(self, repo_url: str, label: str = "Buy License") -> str:
        """
        Generate an embeddable HTML buy button for websites.

        Args:
            repo_url: Repository URL
            label: Button label text

        Returns:
            Self-contained HTML anchor styled as a button
        """
        purchase_url = self.get_purchase_url(repo_url)
        return (
            f'<a href="{purchase_url}" target="_blank" rel="noopener noreferrer" '
            'style="display: inline-block; padding: 12px 24px; background: #6366f1; '
            'color: white; text-decoration: none; border-radius: 6px; font-weight: 500;">'
            f"{label}</a>"
        )

    def generate_qr_code_url(self, repo_url: str, size: int = 200) -> str:
        """
        Generate a QR code URL using a public QR code API.

        Args:
            repo_url: Repository URL
            size: QR code size in pixels

        Returns:
            URL to QR code image encoding the purchase page URL
        """
        purchase_url = self.get_purchase_url(repo_url)
        encoded_url = quote(purchase_url, safe="")
        # Using QR Server API (free, no auth required)
        return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}"

    def generate_qr_code_svg(self, repo_url: str, size: int = 200) -> str:
        """
        Generate QR code as SVG (uses external API).

        Args:
            repo_url: Repository URL
            size: QR code size

        Returns:
            URL to SVG QR code encoding the purchase page URL
        """
        purchase_url = self.get_purchase_url(repo_url)
        encoded_url = quote(purchase_url, safe="")
        return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&format=svg&data={encoded_url}"

    def get_all_links(self, repo_url: str) -> Dict[str, Any]:
        """
        Get all available links for a repository.

        Args:
            repo_url: Repository URL

        Returns:
            Dictionary of all link types and their URLs
        """
        repo_id = self.generate_repo_id(repo_url)

        return {
            "repo_id": repo_id,
            "purchase_page": self.get_purchase_url(repo_url),
            "explorer_url": self.get_explorer_url(repo_url),
            "license_standard": self.get_license_url(repo_url, "standard"),
            "license_premium": self.get_license_url(repo_url, "premium"),
            "license_enterprise": self.get_license_url(repo_url, "enterprise"),
            "qr_code": self.generate_qr_code_url(repo_url),
            "qr_code_svg": self.generate_qr_code_svg(repo_url),
            "badge_markdown": self.generate_badge_markdown(repo_url),
            "badge_html": self.generate_badge_html(repo_url),
            "embed_button": self.generate_embed_button(repo_url),
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered repositories.

        Returns:
            Dictionary with stats
        """
        active = sum(
            1 for m in self._mappings.values() if m.get("active", m.get("agent_active", True))
        )
        with_ip_asset = sum(1 for m in self._mappings.values() if m.get("ip_asset_id"))
        return {
            "total_registered": len(self._mappings),
            "active": active,
            "inactive": len(self._mappings) - active,
            "with_ip_asset": with_ip_asset,
        }
