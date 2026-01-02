# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Reputation tracking system for RRA Module.

Tracks on-chain and off-chain metrics to build verifiable
reputation for repositories and their negotiation agents.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class ReputationMetrics:
    """
    Reputation metrics for a repository.

    These metrics are used to enhance negotiation leverage
    and pricing power.
    """

    repo_url: str

    # Transaction metrics
    total_licenses_sold: int = 0
    total_revenue_eth: float = 0.0
    average_sale_price_eth: float = 0.0

    # Quality metrics
    bug_resolution_rate: float = 0.0
    average_response_time_hours: float = 0.0
    code_reuse_count: int = 0  # Number of downstream projects

    # Feedback metrics
    positive_ratings: int = 0
    negative_ratings: int = 0
    average_rating: float = 0.0

    # Negotiation metrics
    successful_negotiations: int = 0
    failed_negotiations: int = 0
    negotiation_success_rate: float = 0.0

    # Uptime/Availability
    uptime_percentage: float = 100.0
    last_update_timestamp: Optional[datetime] = None

    # On-chain verification
    on_chain_verified: bool = False
    verification_tx_hash: Optional[str] = None

    # Historical data
    reputation_history: List[Dict[str, Any]] = field(default_factory=list)

    def calculate_reputation_score(self) -> float:
        """
        Calculate overall reputation score (0-100).

        Weighted combination of various metrics.

        Returns:
            Reputation score between 0 and 100
        """
        # Weights for different factors
        weights = {
            "transactions": 0.25,
            "quality": 0.30,
            "feedback": 0.25,
            "negotiations": 0.15,
            "uptime": 0.05,
        }

        # Transaction score (0-100)
        transaction_score = min(100, (self.total_licenses_sold / 10) * 100)

        # Quality score (0-100)
        quality_score = (self.bug_resolution_rate * 100 * 0.6) + (
            min(100, (1 / (self.average_response_time_hours + 1)) * 100) * 0.4
        )

        # Feedback score (0-100)
        if (self.positive_ratings + self.negative_ratings) > 0:
            feedback_score = (
                self.positive_ratings / (self.positive_ratings + self.negative_ratings)
            ) * 100
        else:
            feedback_score = 50  # Neutral

        # Negotiation score (0-100)
        negotiation_score = self.negotiation_success_rate * 100

        # Uptime score (0-100)
        uptime_score = self.uptime_percentage

        # Calculate weighted score
        total_score = (
            weights["transactions"] * transaction_score
            + weights["quality"] * quality_score
            + weights["feedback"] * feedback_score
            + weights["negotiations"] * negotiation_score
            + weights["uptime"] * uptime_score
        )

        return round(total_score, 2)

    def get_reputation_level(self) -> str:
        """
        Get reputation level based on score.

        Returns:
            Level string (Bronze, Silver, Gold, Platinum, Diamond)
        """
        score = self.calculate_reputation_score()

        if score >= 90:
            return "Diamond"
        elif score >= 75:
            return "Platinum"
        elif score >= 60:
            return "Gold"
        elif score >= 40:
            return "Silver"
        else:
            return "Bronze"


class ReputationTracker:
    """
    Tracks and manages reputation for repositories.

    Handles both on-chain and off-chain reputation data.
    """

    def __init__(self, storage_dir: Path = Path("./reputation_data")):
        """
        Initialize ReputationTracker.

        Args:
            storage_dir: Directory for storing reputation data
        """
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def get_reputation(self, repo_url: str) -> ReputationMetrics:
        """
        Get reputation metrics for a repository.

        Args:
            repo_url: Repository URL

        Returns:
            ReputationMetrics instance
        """
        file_path = self._get_reputation_file(repo_url)

        if file_path.exists():
            with open(file_path, "r") as f:
                data = json.load(f)

                # Reconstruct datetime objects
                if data.get("last_update_timestamp"):
                    data["last_update_timestamp"] = datetime.fromisoformat(
                        data["last_update_timestamp"]
                    )

                return ReputationMetrics(**data)

        # Return new metrics if not found
        return ReputationMetrics(repo_url=repo_url)

    def update_reputation(self, repo_url: str, updates: Dict[str, Any]) -> ReputationMetrics:
        """
        Update reputation metrics.

        Args:
            repo_url: Repository URL
            updates: Dictionary of metric updates

        Returns:
            Updated ReputationMetrics
        """
        metrics = self.get_reputation(repo_url)

        # Apply updates
        for key, value in updates.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

        # Recalculate derived metrics
        if metrics.total_licenses_sold > 0:
            metrics.average_sale_price_eth = metrics.total_revenue_eth / metrics.total_licenses_sold

        total_negotiations = metrics.successful_negotiations + metrics.failed_negotiations
        if total_negotiations > 0:
            metrics.negotiation_success_rate = metrics.successful_negotiations / total_negotiations

        if (metrics.positive_ratings + metrics.negative_ratings) > 0:
            metrics.average_rating = (
                metrics.positive_ratings / (metrics.positive_ratings + metrics.negative_ratings)
            ) * 5.0  # Scale to 5-star rating

        # Update timestamp
        metrics.last_update_timestamp = datetime.now()

        # Record history
        metrics.reputation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "score": metrics.calculate_reputation_score(),
                "updates": updates,
            }
        )

        # Save
        self._save_reputation(metrics)

        return metrics

    def record_sale(self, repo_url: str, price_eth: float, buyer_address: str) -> ReputationMetrics:
        """
        Record a license sale.

        Args:
            repo_url: Repository URL
            price_eth: Sale price in ETH
            buyer_address: Buyer's Ethereum address

        Returns:
            Updated ReputationMetrics
        """
        metrics = self.get_reputation(repo_url)

        metrics.total_licenses_sold += 1
        metrics.total_revenue_eth += price_eth

        if metrics.total_licenses_sold > 0:
            metrics.average_sale_price_eth = metrics.total_revenue_eth / metrics.total_licenses_sold

        metrics.last_update_timestamp = datetime.now()

        # Record in history
        metrics.reputation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": "sale",
                "price_eth": price_eth,
                "buyer": buyer_address,
                "score": metrics.calculate_reputation_score(),
            }
        )

        self._save_reputation(metrics)

        return metrics

    def record_feedback(
        self, repo_url: str, rating: int, comment: Optional[str] = None
    ) -> ReputationMetrics:
        """
        Record buyer feedback.

        Args:
            repo_url: Repository URL
            rating: Rating (1-5)
            comment: Optional comment

        Returns:
            Updated ReputationMetrics
        """
        metrics = self.get_reputation(repo_url)

        if rating >= 4:
            metrics.positive_ratings += 1
        else:
            metrics.negative_ratings += 1

        total_ratings = metrics.positive_ratings + metrics.negative_ratings
        if total_ratings > 0:
            metrics.average_rating = (metrics.positive_ratings / total_ratings) * 5.0

        metrics.reputation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": "feedback",
                "rating": rating,
                "comment": comment,
                "score": metrics.calculate_reputation_score(),
            }
        )

        self._save_reputation(metrics)

        return metrics

    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top repositories by reputation score.

        Args:
            limit: Maximum number of repositories to return

        Returns:
            List of top repositories with their scores
        """
        repos = []

        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    metrics = ReputationMetrics(
                        **{k: v for k, v in data.items() if k != "last_update_timestamp"}
                    )

                    repos.append(
                        {
                            "repo_url": metrics.repo_url,
                            "score": metrics.calculate_reputation_score(),
                            "level": metrics.get_reputation_level(),
                            "total_sales": metrics.total_licenses_sold,
                            "revenue_eth": metrics.total_revenue_eth,
                        }
                    )
            except (json.JSONDecodeError, TypeError, KeyError, OSError):
                # Skip corrupted or invalid reputation files
                continue

        # Sort by score
        repos.sort(key=lambda x: x["score"], reverse=True)

        return repos[:limit]

    def _get_reputation_file(self, repo_url: str) -> Path:
        """Get file path for repository reputation data."""
        # Sanitize URL to create filename
        filename = repo_url.replace("https://", "").replace("http://", "")
        filename = filename.replace("/", "_").replace(":", "_") + ".json"

        return self.storage_dir / filename

    def _save_reputation(self, metrics: ReputationMetrics) -> None:
        """Save reputation metrics to file."""
        file_path = self._get_reputation_file(metrics.repo_url)

        # Convert to dict for JSON serialization
        data = {
            "repo_url": metrics.repo_url,
            "total_licenses_sold": metrics.total_licenses_sold,
            "total_revenue_eth": metrics.total_revenue_eth,
            "average_sale_price_eth": metrics.average_sale_price_eth,
            "bug_resolution_rate": metrics.bug_resolution_rate,
            "average_response_time_hours": metrics.average_response_time_hours,
            "code_reuse_count": metrics.code_reuse_count,
            "positive_ratings": metrics.positive_ratings,
            "negative_ratings": metrics.negative_ratings,
            "average_rating": metrics.average_rating,
            "successful_negotiations": metrics.successful_negotiations,
            "failed_negotiations": metrics.failed_negotiations,
            "negotiation_success_rate": metrics.negotiation_success_rate,
            "uptime_percentage": metrics.uptime_percentage,
            "last_update_timestamp": (
                metrics.last_update_timestamp.isoformat() if metrics.last_update_timestamp else None
            ),
            "on_chain_verified": metrics.on_chain_verified,
            "verification_tx_hash": metrics.verification_tx_hash,
            "reputation_history": metrics.reputation_history,
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
