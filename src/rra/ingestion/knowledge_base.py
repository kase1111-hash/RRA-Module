# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Agent Knowledge Base (AKB) for storing parsed repository information.

The AKB serves as the structured knowledge store that agents use for
reasoning about repositories during negotiations.

Supports optional gzip compression for reduced disk usage.
"""

import gzip
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field

from rra.config.market_config import MarketConfig

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBase:
    """
    Structured knowledge base for a repository.

    Contains all parsed information about a repository that agents
    need for intelligent negotiations and licensing decisions.
    """

    repo_path: Path
    repo_url: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Configuration
    market_config: Optional[MarketConfig] = None

    # Repository metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Code structure (extension -> file paths)
    code_structure: Dict[str, List[str]] = field(default_factory=dict)

    # Dependencies by language
    dependencies: Dict[str, List[str]] = field(default_factory=dict)

    # Documentation content
    documentation: Dict[str, str] = field(default_factory=dict)

    # API endpoints
    api_endpoints: List[Dict[str, Any]] = field(default_factory=list)

    # Test information
    tests: Dict[str, int] = field(default_factory=dict)

    # Repository statistics
    statistics: Dict[str, Any] = field(default_factory=dict)

    # Embeddings for semantic search (future enhancement)
    embeddings: Optional[Dict[str, Any]] = None

    # Verification results
    verification: Optional[Dict[str, Any]] = None

    # README metadata (parsed description, features, etc.)
    readme_metadata: Optional[Dict[str, Any]] = None

    # Category classification
    category: Optional[Dict[str, Any]] = None

    # Blockchain/marketplace links
    blockchain_links: Optional[Dict[str, Any]] = None

    def get_summary(self) -> str:
        """
        Generate a human-readable summary of the repository.

        Returns:
            Formatted summary string
        """
        lines = [
            f"Repository: {self.repo_url}",
            f"Last Updated: {self.updated_at.isoformat()}",
            "",
            "=== Overview ===",
        ]

        if self.market_config:
            lines.extend([
                f"License Model: {self.market_config.license_model.value}",
                f"Target Price: {self.market_config.target_price}",
                f"Floor Price: {self.market_config.floor_price}",
                "",
            ])

        if self.statistics:
            lines.append("=== Statistics ===")
            lines.append(f"Total Files: {self.statistics.get('total_files', 0)}")
            lines.append(f"Code Files: {self.statistics.get('code_files', 0)}")
            lines.append(f"Total Lines: {self.statistics.get('total_lines', 0)}")

            languages = self.statistics.get('languages', [])
            if languages:
                lines.append(f"Languages: {', '.join(languages)}")
            lines.append("")

        if self.dependencies:
            lines.append("=== Dependencies ===")
            for lang, deps in self.dependencies.items():
                lines.append(f"{lang.capitalize()}: {len(deps)} packages")
            lines.append("")

        if self.api_endpoints:
            lines.append(f"=== API Endpoints ({len(self.api_endpoints)}) ===")
            for endpoint in self.api_endpoints[:5]:  # Show first 5
                lines.append(f"  {endpoint['method']} {endpoint['path']}")
            if len(self.api_endpoints) > 5:
                lines.append(f"  ... and {len(self.api_endpoints) - 5} more")
            lines.append("")

        if self.tests:
            lines.append("=== Tests ===")
            lines.append(f"Test Files: {self.tests.get('test_files', 0)}")
            lines.append(f"Test Functions: {self.tests.get('test_functions', 0)}")
            lines.append("")

        if "README.md" in self.documentation:
            readme = self.documentation["README.md"]
            lines.append("=== README (excerpt) ===")
            lines.append(readme[:300] + "..." if len(readme) > 300 else readme)

        if self.verification:
            lines.append("")
            lines.append("=== Verification ===")
            lines.append(f"Score: {self.verification.get('score', 0)}/100")
            lines.append(f"Status: {self.verification.get('overall_status', 'unknown')}")

        if self.category:
            lines.append("")
            lines.append("=== Category ===")
            lines.append(f"Primary: {self.category.get('primary_category', 'unknown')}")
            if self.category.get('subcategory'):
                lines.append(f"Subcategory: {self.category.get('subcategory')}")
            if self.category.get('tags'):
                lines.append(f"Tags: {', '.join(self.category.get('tags', [])[:5])}")

        if self.blockchain_links:
            lines.append("")
            lines.append("=== Marketplace ===")
            if self.blockchain_links.get('ip_asset_id'):
                lines.append(f"IP Asset ID: {self.blockchain_links.get('ip_asset_id')}")
            if self.blockchain_links.get('purchase_links'):
                lines.append(f"Purchase Links: {len(self.blockchain_links.get('purchase_links', []))} tiers available")

        return "\n".join(lines)

    def get_negotiation_context(self) -> Dict[str, Any]:
        """
        Generate context for negotiation agents.

        Returns:
            Dictionary of key information for negotiations
        """
        context = {
            "repo_url": self.repo_url,
            "value_propositions": [],
            "technical_details": {},
            "pricing": {},
            "strengths": [],
        }

        # Pricing information
        if self.market_config:
            context["pricing"] = {
                "model": self.market_config.license_model.value,
                "target_price": self.market_config.target_price,
                "floor_price": self.market_config.floor_price,
                "negotiation_style": self.market_config.negotiation_style.value,
                "features": self.market_config.features,
            }

        # Technical details
        if self.statistics:
            context["technical_details"] = {
                "languages": self.statistics.get('languages', []),
                "lines_of_code": self.statistics.get('total_lines', 0),
                "file_count": self.statistics.get('code_files', 0),
            }

        # Value propositions based on repository characteristics
        if self.api_endpoints:
            context["value_propositions"].append(
                f"Production-ready API with {len(self.api_endpoints)} endpoints"
            )

        if self.tests.get('test_files', 0) > 0:
            context["value_propositions"].append(
                f"Well-tested with {self.tests['test_functions']} test cases"
            )

        if self.metadata.get('total_commits', 0) > 100:
            context["value_propositions"].append(
                f"Mature codebase with {self.metadata['total_commits']} commits"
            )

        if len(self.statistics.get('languages', [])) > 1:
            context["strengths"].append("Multi-language support")

        if self.dependencies:
            total_deps = sum(len(deps) for deps in self.dependencies.values())
            if total_deps > 10:
                context["strengths"].append("Well-integrated with popular libraries")

        return context

    def save(self, output_path: Optional[Path] = None, compress: bool = True) -> Path:
        """
        Save knowledge base to JSON file with optional compression.

        Args:
            output_path: Optional custom output path
            compress: Whether to gzip compress the output (default: True)

        Returns:
            Path where the knowledge base was saved
        """
        if output_path is None:
            kb_dir = Path("agent_knowledge_bases")
            kb_dir.mkdir(exist_ok=True)

            # Generate filename from repo URL
            repo_name = self.repo_url.split('/')[-1].replace('.git', '')
            # Use .json.gz extension for compressed files
            ext = ".json.gz" if compress else ".json"
            output_path = kb_dir / f"{repo_name}_kb{ext}"

        # Convert to dict for JSON serialization
        data = {
            "repo_path": str(self.repo_path),
            "repo_url": self.repo_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "market_config": self.market_config.model_dump() if self.market_config else None,
            "metadata": self.metadata,
            "code_structure": self.code_structure,
            "dependencies": self.dependencies,
            "documentation": self.documentation,
            "api_endpoints": self.api_endpoints,
            "tests": self.tests,
            "statistics": self.statistics,
            "embeddings": self.embeddings,
            "verification": self.verification,
            "readme_metadata": self.readme_metadata,
            "category": self.category,
            "blockchain_links": self.blockchain_links,
        }

        json_bytes = json.dumps(data, indent=2, default=str).encode('utf-8')
        original_size = len(json_bytes)

        if compress:
            # Use gzip compression for significant space savings
            compressed_bytes = gzip.compress(json_bytes, compresslevel=6)
            compressed_size = len(compressed_bytes)
            savings = 1 - (compressed_size / original_size) if original_size > 0 else 0

            with open(output_path, 'wb') as f:
                f.write(compressed_bytes)

            logger.debug(
                f"Knowledge base saved (compressed): {output_path} "
                f"({original_size} -> {compressed_size} bytes, {savings:.1%} reduction)"
            )
        else:
            with open(output_path, 'w') as f:
                f.write(json_bytes.decode('utf-8'))
            logger.debug(f"Knowledge base saved: {output_path} ({original_size} bytes)")

        return output_path

    @classmethod
    def load(cls, file_path: Path) -> "KnowledgeBase":
        """
        Load knowledge base from JSON file (supports both compressed and uncompressed).

        Args:
            file_path: Path to the saved knowledge base (.json or .json.gz)

        Returns:
            KnowledgeBase instance
        """
        file_path = Path(file_path)

        # Check if file is gzip compressed (by extension or magic bytes)
        is_compressed = str(file_path).endswith('.gz')

        if is_compressed:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"Loaded compressed knowledge base: {file_path}")
        else:
            # Try reading as regular JSON first
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            except UnicodeDecodeError:
                # File might be gzip without .gz extension, try decompressing
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"Loaded gzip-compressed knowledge base (no .gz extension): {file_path}")

        # Reconstruct market config if present
        market_config = None
        if data.get("market_config"):
            market_config = MarketConfig(**data["market_config"])

        # Create instance
        kb = cls(
            repo_path=Path(data["repo_path"]),
            repo_url=data["repo_url"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            market_config=market_config,
            metadata=data.get("metadata", {}),
            code_structure=data.get("code_structure", {}),
            dependencies=data.get("dependencies", {}),
            documentation=data.get("documentation", {}),
            api_endpoints=data.get("api_endpoints", []),
            tests=data.get("tests", {}),
            statistics=data.get("statistics", {}),
            embeddings=data.get("embeddings"),
            verification=data.get("verification"),
            readme_metadata=data.get("readme_metadata"),
            category=data.get("category"),
            blockchain_links=data.get("blockchain_links"),
        )

        return kb

    def refresh(self, new_data: Dict[str, Any]) -> None:
        """
        Update knowledge base with new data.

        Args:
            new_data: Dictionary of updated fields
        """
        self.updated_at = datetime.now()

        for key, value in new_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
