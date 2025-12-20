# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Multi-Repo Bundling for RRA Module.

Allows packaging multiple repositories into a single licensable bundle:
- Portfolio licensing (license all repos at once)
- Discounted pricing for bundles
- Cross-repo dependency bundling
- Themed collections (e.g., "Full Stack Starter Kit")
"""

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum


class BundleType(Enum):
    """Types of repository bundles."""
    PORTFOLIO = "portfolio"  # All repos from a single owner
    COLLECTION = "collection"  # Themed collection
    DEPENDENCY = "dependency"  # Repos that work together
    SUITE = "suite"  # Complete solution bundle
    STARTER_KIT = "starter_kit"  # Getting started bundle


class DiscountType(Enum):
    """Types of bundle discounts."""
    PERCENTAGE = "percentage"  # e.g., 20% off total
    FIXED = "fixed"  # e.g., $50 off total
    PER_REPO = "per_repo"  # e.g., $10 off per repo after first
    TIERED = "tiered"  # Discount increases with count


@dataclass
class BundleDiscount:
    """Discount configuration for a bundle."""
    discount_type: DiscountType
    value: float  # Percentage (0-100) or fixed amount
    min_repos: int = 2  # Minimum repos for discount
    max_discount_percent: float = 50.0  # Cap on total discount

    def calculate_discount(
        self,
        total_price: float,
        repo_count: int
    ) -> float:
        """
        Calculate the discount amount.

        Args:
            total_price: Total price before discount
            repo_count: Number of repos in bundle

        Returns:
            Discount amount
        """
        if repo_count < self.min_repos:
            return 0.0

        if self.discount_type == DiscountType.PERCENTAGE:
            discount = total_price * (self.value / 100)

        elif self.discount_type == DiscountType.FIXED:
            discount = self.value

        elif self.discount_type == DiscountType.PER_REPO:
            # Discount per repo after the first
            discount = self.value * (repo_count - 1)

        elif self.discount_type == DiscountType.TIERED:
            # Tiered: 10% for 2, 15% for 3, 20% for 4, etc.
            tier_percent = min(10 + (repo_count - 2) * 5, 40)
            discount = total_price * (tier_percent / 100)

        else:
            discount = 0.0

        # Apply max discount cap
        max_discount = total_price * (self.max_discount_percent / 100)
        return min(discount, max_discount)


@dataclass
class BundledRepo:
    """A repository included in a bundle."""
    repo_id: str
    repo_url: str
    name: str
    description: Optional[str] = None
    individual_price: float = 0.0
    license_type: str = "commercial"
    tags: List[str] = field(default_factory=list)
    added_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RepoBundle:
    """
    A bundle of multiple repositories.

    Bundles allow licensing multiple repos together at a discount.
    """
    bundle_id: str
    name: str
    description: str
    bundle_type: BundleType
    owner_address: str
    repos: List[BundledRepo] = field(default_factory=list)
    discount: Optional[BundleDiscount] = None
    tags: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Metadata
    featured: bool = False
    cover_image_url: Optional[str] = None
    category: Optional[str] = None

    @property
    def repo_count(self) -> int:
        """Number of repos in the bundle."""
        return len(self.repos)

    @property
    def total_individual_price(self) -> float:
        """Total price if repos were purchased individually."""
        return sum(r.individual_price for r in self.repos)

    @property
    def bundle_price(self) -> float:
        """Discounted bundle price."""
        total = self.total_individual_price
        if self.discount:
            discount_amount = self.discount.calculate_discount(total, self.repo_count)
            return max(0, total - discount_amount)
        return total

    @property
    def savings(self) -> float:
        """Amount saved by purchasing the bundle."""
        return self.total_individual_price - self.bundle_price

    @property
    def savings_percent(self) -> float:
        """Percentage saved by purchasing the bundle."""
        if self.total_individual_price == 0:
            return 0.0
        return (self.savings / self.total_individual_price) * 100

    def add_repo(self, repo: BundledRepo) -> None:
        """Add a repository to the bundle."""
        self.repos.append(repo)
        self.updated_at = datetime.utcnow().isoformat()

    def remove_repo(self, repo_id: str) -> bool:
        """Remove a repository from the bundle."""
        for i, repo in enumerate(self.repos):
            if repo.repo_id == repo_id:
                del self.repos[i]
                self.updated_at = datetime.utcnow().isoformat()
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert bundle to dictionary."""
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "description": self.description,
            "bundle_type": self.bundle_type.value,
            "owner_address": self.owner_address,
            "repos": [
                {
                    "repo_id": r.repo_id,
                    "repo_url": r.repo_url,
                    "name": r.name,
                    "description": r.description,
                    "individual_price": r.individual_price,
                    "license_type": r.license_type,
                    "tags": r.tags,
                    "added_at": r.added_at,
                }
                for r in self.repos
            ],
            "discount": {
                "discount_type": self.discount.discount_type.value,
                "value": self.discount.value,
                "min_repos": self.discount.min_repos,
                "max_discount_percent": self.discount.max_discount_percent,
            } if self.discount else None,
            "tags": self.tags,
            "is_active": self.is_active,
            "featured": self.featured,
            "cover_image_url": self.cover_image_url,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            # Computed fields
            "repo_count": self.repo_count,
            "total_individual_price": self.total_individual_price,
            "bundle_price": self.bundle_price,
            "savings": self.savings,
            "savings_percent": self.savings_percent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepoBundle":
        """Create bundle from dictionary."""
        discount_data = data.get("discount")
        discount = None
        if discount_data:
            discount = BundleDiscount(
                discount_type=DiscountType(discount_data["discount_type"]),
                value=discount_data["value"],
                min_repos=discount_data.get("min_repos", 2),
                max_discount_percent=discount_data.get("max_discount_percent", 50.0),
            )

        repos = [
            BundledRepo(
                repo_id=r["repo_id"],
                repo_url=r["repo_url"],
                name=r["name"],
                description=r.get("description"),
                individual_price=r.get("individual_price", 0.0),
                license_type=r.get("license_type", "commercial"),
                tags=r.get("tags", []),
                added_at=r.get("added_at", datetime.utcnow().isoformat()),
            )
            for r in data.get("repos", [])
        ]

        return cls(
            bundle_id=data["bundle_id"],
            name=data["name"],
            description=data["description"],
            bundle_type=BundleType(data["bundle_type"]),
            owner_address=data["owner_address"],
            repos=repos,
            discount=discount,
            tags=data.get("tags", []),
            is_active=data.get("is_active", True),
            featured=data.get("featured", False),
            cover_image_url=data.get("cover_image_url"),
            category=data.get("category"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
        )


class BundleManager:
    """
    Manages repository bundles.

    Provides CRUD operations and search functionality for bundles.
    """

    def __init__(self, storage_path: Path = None):
        """
        Initialize the bundle manager.

        Args:
            storage_path: Path for bundle storage
        """
        self.storage_path = storage_path or Path("data/bundles.json")
        self._bundles: Dict[str, RepoBundle] = {}
        self._load_bundles()

    def _load_bundles(self) -> None:
        """Load bundles from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self._bundles = {
                        k: RepoBundle.from_dict(v)
                        for k, v in data.items()
                    }
            except (json.JSONDecodeError, IOError):
                self._bundles = {}

    def _save_bundles(self) -> None:
        """Save bundles to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(
                {k: v.to_dict() for k, v in self._bundles.items()},
                f, indent=2, default=str
            )

    def create_bundle(
        self,
        name: str,
        description: str,
        bundle_type: BundleType,
        owner_address: str,
        repos: List[BundledRepo] = None,
        discount: BundleDiscount = None,
        tags: List[str] = None,
    ) -> RepoBundle:
        """
        Create a new bundle.

        Args:
            name: Bundle name
            description: Bundle description
            bundle_type: Type of bundle
            owner_address: Owner's wallet address
            repos: Initial repos in bundle
            discount: Discount configuration
            tags: Bundle tags

        Returns:
            Created bundle
        """
        bundle_id = f"bnd_{secrets.token_hex(12)}"

        bundle = RepoBundle(
            bundle_id=bundle_id,
            name=name,
            description=description,
            bundle_type=bundle_type,
            owner_address=owner_address,
            repos=repos or [],
            discount=discount,
            tags=tags or [],
        )

        self._bundles[bundle_id] = bundle
        self._save_bundles()
        return bundle

    def get_bundle(self, bundle_id: str) -> Optional[RepoBundle]:
        """Get a bundle by ID."""
        return self._bundles.get(bundle_id)

    def update_bundle(self, bundle: RepoBundle) -> None:
        """Update a bundle."""
        bundle.updated_at = datetime.utcnow().isoformat()
        self._bundles[bundle.bundle_id] = bundle
        self._save_bundles()

    def delete_bundle(self, bundle_id: str) -> bool:
        """Delete a bundle."""
        if bundle_id in self._bundles:
            del self._bundles[bundle_id]
            self._save_bundles()
            return True
        return False

    def list_bundles(
        self,
        owner_address: str = None,
        bundle_type: BundleType = None,
        category: str = None,
        tags: List[str] = None,
        featured_only: bool = False,
        active_only: bool = True,
    ) -> List[RepoBundle]:
        """
        List bundles with optional filters.

        Args:
            owner_address: Filter by owner
            bundle_type: Filter by type
            category: Filter by category
            tags: Filter by tags (any match)
            featured_only: Only featured bundles
            active_only: Only active bundles

        Returns:
            List of matching bundles
        """
        bundles = list(self._bundles.values())

        if owner_address:
            bundles = [b for b in bundles if b.owner_address == owner_address]

        if bundle_type:
            bundles = [b for b in bundles if b.bundle_type == bundle_type]

        if category:
            bundles = [b for b in bundles if b.category == category]

        if tags:
            bundles = [
                b for b in bundles
                if any(t in b.tags for t in tags)
            ]

        if featured_only:
            bundles = [b for b in bundles if b.featured]

        if active_only:
            bundles = [b for b in bundles if b.is_active]

        return bundles

    def search_bundles(self, query: str) -> List[RepoBundle]:
        """
        Search bundles by name, description, or tags.

        Args:
            query: Search query

        Returns:
            Matching bundles
        """
        query_lower = query.lower()
        return [
            b for b in self._bundles.values()
            if b.is_active and (
                query_lower in b.name.lower() or
                query_lower in b.description.lower() or
                any(query_lower in tag.lower() for tag in b.tags)
            )
        ]

    def get_bundles_containing_repo(self, repo_id: str) -> List[RepoBundle]:
        """Get all bundles containing a specific repo."""
        return [
            b for b in self._bundles.values()
            if any(r.repo_id == repo_id for r in b.repos)
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get bundle statistics."""
        active_bundles = [b for b in self._bundles.values() if b.is_active]

        return {
            "total_bundles": len(self._bundles),
            "active_bundles": len(active_bundles),
            "featured_bundles": len([b for b in active_bundles if b.featured]),
            "total_repos_bundled": sum(b.repo_count for b in active_bundles),
            "avg_repos_per_bundle": (
                sum(b.repo_count for b in active_bundles) / len(active_bundles)
                if active_bundles else 0
            ),
            "avg_discount_percent": (
                sum(b.savings_percent for b in active_bundles) / len(active_bundles)
                if active_bundles else 0
            ),
            "bundles_by_type": {
                bt.value: len([b for b in active_bundles if b.bundle_type == bt])
                for bt in BundleType
            },
        }


# =============================================================================
# Global Instance
# =============================================================================

bundle_manager = BundleManager()


def get_bundle_manager() -> BundleManager:
    """Get the global bundle manager instance."""
    return bundle_manager
