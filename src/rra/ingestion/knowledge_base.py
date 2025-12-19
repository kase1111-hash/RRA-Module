# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Agent Knowledge Base (AKB) for storing parsed repository information.

The AKB serves as the structured knowledge store that agents use for
reasoning about repositories during negotiations.
"""

import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field

from rra.config.market_config import MarketConfig


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

    def save(self, output_path: Optional[Path] = None) -> Path:
        """
        Save knowledge base to JSON file.

        Args:
            output_path: Optional custom output path

        Returns:
            Path where the knowledge base was saved
        """
        if output_path is None:
            kb_dir = Path("agent_knowledge_bases")
            kb_dir.mkdir(exist_ok=True)

            # Generate filename from repo URL
            repo_name = self.repo_url.split('/')[-1].replace('.git', '')
            output_path = kb_dir / f"{repo_name}_kb.json"

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
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return output_path

    @classmethod
    def load(cls, file_path: Path) -> "KnowledgeBase":
        """
        Load knowledge base from JSON file.

        Args:
            file_path: Path to the saved knowledge base

        Returns:
            KnowledgeBase instance
        """
        with open(file_path, 'r') as f:
            data = json.load(f)

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
