# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Deep Links Service for RRA Module.

Provides URL generation and resolution for:
- Agent pages
- Direct negotiation chat links
- Specific license tier links
- Search results
- Category browsing
- Developer profiles
- QR code generation
- README badge generation
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlencode, quote


class DeepLinkService:
    """
    Generate and resolve deep links for RRA agents and repositories.

    URL Structure:
    - /agent/{repo_id}                    # Agent home page
    - /agent/{repo_id}/chat               # Direct to negotiation chat
    - /agent/{repo_id}/license/{tier}     # Specific license tier
    - /search?q={query}                   # Search results
    - /category/{category}                # Browse by category
    - /user/{username}                    # Developer profile
    """

    # Story Protocol testnet explorer (live blockchain infrastructure)
    # TODO: Switch to mainnet (https://explorer.story.foundation) for production
    DEFAULT_BASE_URL = "https://aeneid.explorer.story.foundation"

    def __init__(self, base_url: Optional[str] = None, mappings_path: Optional[Path] = None):
        """
        Initialize the deep link service.

        Args:
            base_url: Base URL for generated links (default: Story Protocol testnet explorer)
                      Use https://explorer.story.foundation for mainnet
            mappings_path: Path to store repo ID mappings (default: agent_knowledge_bases/repo_mappings.json)
        """
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
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
            metadata: Optional metadata (owner, name, description, etc.)

        Returns:
            Repository ID
        """
        repo_id = self.generate_repo_id(repo_url)

        self._mappings[repo_id] = {
            "repo_url": repo_url,
            "created_at": datetime.utcnow().isoformat(),
            "agent_active": True,
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

    def get_agent_url(self, repo_url: str) -> str:
        """
        Get the agent page URL for a repository.

        Args:
            repo_url: Repository URL

        Returns:
            Full agent page URL
        """
        repo_id = self.generate_repo_id(repo_url)
        return f"{self.base_url}/agent/{repo_id}"

    def get_chat_url(self, repo_url: str) -> str:
        """
        Get the direct chat URL for a repository.

        Args:
            repo_url: Repository URL

        Returns:
            Full chat URL (opens negotiation immediately)
        """
        repo_id = self.generate_repo_id(repo_url)
        return f"{self.base_url}/agent/{repo_id}/chat"

    def get_license_url(self, repo_url: str, tier: str) -> str:
        """
        Get the license tier URL for a repository.

        Args:
            repo_url: Repository URL
            tier: License tier name (e.g., 'individual', 'team', 'enterprise')

        Returns:
            Full license tier URL
        """
        repo_id = self.generate_repo_id(repo_url)
        return f"{self.base_url}/agent/{repo_id}/license/{quote(tier)}"

    def get_search_url(self, query: str, **filters) -> str:
        """
        Get a search URL with optional filters.

        Args:
            query: Search query
            **filters: Additional filters (language, price_min, price_max, etc.)

        Returns:
            Full search URL
        """
        params = {"q": query, **filters}
        return f"{self.base_url}/search?{urlencode(params)}"

    def get_category_url(self, category: str) -> str:
        """
        Get a category browse URL.

        Args:
            category: Category name

        Returns:
            Full category URL
        """
        return f"{self.base_url}/category/{quote(category)}"

    def get_user_url(self, username: str) -> str:
        """
        Get a developer profile URL.

        Args:
            username: Developer username

        Returns:
            Full user profile URL
        """
        return f"{self.base_url}/user/{quote(username)}"

    def generate_badge_markdown(
        self, repo_url: str, style: str = "flat", label: str = "License This Repo"
    ) -> str:
        """
        Generate a README badge in Markdown format.

        Args:
            repo_url: Repository URL
            style: Badge style (flat, flat-square, plastic, for-the-badge)
            label: Badge label text

        Returns:
            Markdown badge code
        """
        agent_url = self.get_agent_url(repo_url)
        # Use shields.io for badge generation
        badge_url = f"https://img.shields.io/badge/{quote(label)}-RRA-blue?style={style}"
        return f"[![{label}]({badge_url})]({agent_url})"

    def generate_badge_html(
        self, repo_url: str, style: str = "flat", label: str = "License This Repo"
    ) -> str:
        """
        Generate a README badge in HTML format.

        Args:
            repo_url: Repository URL
            style: Badge style
            label: Badge label text

        Returns:
            HTML badge code
        """
        agent_url = self.get_agent_url(repo_url)
        badge_url = f"https://img.shields.io/badge/{quote(label)}-RRA-blue?style={style}"
        return f'<a href="{agent_url}"><img src="{badge_url}" alt="{label}"></a>'

    def generate_embed_script(self, repo_url: str) -> str:
        """
        Generate an embeddable script tag for websites.

        Args:
            repo_url: Repository URL

        Returns:
            JavaScript embed code
        """
        repo_id = self.generate_repo_id(repo_url)
        return f"""<!-- RRA Negotiation Widget -->
<div id="rra-widget-{repo_id}"></div>
<script src="{self.base_url}/embed.js" data-repo-id="{repo_id}"></script>"""

    def generate_qr_code_url(self, repo_url: str, size: int = 200) -> str:
        """
        Generate a QR code URL using a public QR code API.

        Args:
            repo_url: Repository URL
            size: QR code size in pixels

        Returns:
            URL to QR code image
        """
        agent_url = self.get_agent_url(repo_url)
        encoded_url = quote(agent_url)
        # Using QR Server API (free, no auth required)
        return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}"

    def generate_qr_code_svg(self, repo_url: str, size: int = 200) -> str:
        """
        Generate QR code as SVG (uses external API).

        Args:
            repo_url: Repository URL
            size: QR code size

        Returns:
            URL to SVG QR code
        """
        agent_url = self.get_agent_url(repo_url)
        encoded_url = quote(agent_url)
        return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&format=svg&data={encoded_url}"

    def get_all_links(self, repo_url: str) -> Dict[str, str]:
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
            "agent_page": self.get_agent_url(repo_url),
            "chat_direct": self.get_chat_url(repo_url),
            "license_individual": self.get_license_url(repo_url, "individual"),
            "license_team": self.get_license_url(repo_url, "team"),
            "license_enterprise": self.get_license_url(repo_url, "enterprise"),
            "qr_code": self.generate_qr_code_url(repo_url),
            "qr_code_svg": self.generate_qr_code_svg(repo_url),
            "badge_markdown": self.generate_badge_markdown(repo_url),
            "badge_html": self.generate_badge_html(repo_url),
            "embed_script": self.generate_embed_script(repo_url),
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered repositories.

        Returns:
            Dictionary with stats
        """
        active = sum(1 for m in self._mappings.values() if m.get("agent_active", True))
        return {
            "total_registered": len(self._mappings),
            "active_agents": active,
            "inactive_agents": len(self._mappings) - active,
        }
