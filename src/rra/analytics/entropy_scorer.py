# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Clause Entropy Scorer for License Entropy Oracle.

Scores clauses by their historical instability - how often they lead to
disputes, renegotiations, or conflicts. High entropy clauses are those
that frequently cause problems and should be flagged during negotiation.

Entropy Factors:
1. Historical dispute rate - How often this clause type leads to disputes
2. Ambiguity score - Linguistic ambiguity analysis
3. Modification frequency - How often parties request changes
4. Resolution difficulty - Average time/cost to resolve disputes
5. Semantic volatility - Variation in interpretation across contexts

Usage:
    scorer = EntropyScorer()
    entropy = scorer.score_clause("Licensee may use the software...")
    if entropy.level == EntropyLevel.HIGH:
        print(f"Warning: {entropy.warning}")
"""

import hashlib
import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


class EntropyLevel(Enum):
    """Entropy classification levels."""
    LOW = "low"           # < 0.3 - Stable, well-understood clauses
    MEDIUM = "medium"     # 0.3-0.6 - Some historical issues
    HIGH = "high"         # 0.6-0.8 - Frequent disputes
    CRITICAL = "critical" # > 0.8 - Almost always problematic


@dataclass
class ClauseEntropy:
    """Entropy analysis result for a clause."""
    clause_hash: str
    clause_text: str
    entropy_score: float  # 0.0 to 1.0
    level: EntropyLevel

    # Component scores
    dispute_rate: float
    ambiguity_score: float
    modification_frequency: float
    resolution_difficulty: float
    semantic_volatility: float

    # Actionable insights
    warning: Optional[str] = None
    suggested_alternatives: List[str] = field(default_factory=list)
    similar_disputes: List[str] = field(default_factory=list)

    # Metadata
    confidence: float = 0.0  # How confident we are in this score
    sample_size: int = 0     # Number of historical examples
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "clause_hash": self.clause_hash,
            "entropy_score": round(self.entropy_score, 4),
            "level": self.level.value,
            "components": {
                "dispute_rate": round(self.dispute_rate, 4),
                "ambiguity_score": round(self.ambiguity_score, 4),
                "modification_frequency": round(self.modification_frequency, 4),
                "resolution_difficulty": round(self.resolution_difficulty, 4),
                "semantic_volatility": round(self.semantic_volatility, 4),
            },
            "warning": self.warning,
            "suggested_alternatives": self.suggested_alternatives,
            "confidence": round(self.confidence, 4),
            "sample_size": self.sample_size,
        }


@dataclass
class DisputeRecord:
    """Historical dispute record for training."""
    clause_hash: str
    clause_text: str
    dispute_type: str
    resolution_time_days: float
    resolution_cost_usd: float
    outcome: str  # "settled", "escalated", "abandoned"
    timestamp: datetime


class EntropyScorer:
    """
    Scores clause entropy based on historical data and linguistic analysis.

    The entropy score represents the probability that a clause will lead
    to disputes or require renegotiation. Higher entropy = more risk.
    """

    # Weights for component scores (must sum to 1.0)
    WEIGHTS = {
        "dispute_rate": 0.35,
        "ambiguity_score": 0.25,
        "modification_frequency": 0.15,
        "resolution_difficulty": 0.15,
        "semantic_volatility": 0.10,
    }

    # Ambiguous terms that often cause disputes
    AMBIGUOUS_TERMS = {
        # Vague quantifiers
        "reasonable": 0.7,
        "appropriate": 0.6,
        "sufficient": 0.5,
        "adequate": 0.5,
        "substantial": 0.6,
        "significant": 0.5,
        "material": 0.4,

        # Time ambiguity
        "promptly": 0.6,
        "timely": 0.5,
        "as soon as practicable": 0.7,
        "without undue delay": 0.6,
        "reasonable time": 0.8,

        # Effort ambiguity
        "best efforts": 0.5,
        "commercially reasonable efforts": 0.4,
        "reasonable efforts": 0.6,
        "good faith": 0.5,

        # Scope ambiguity
        "including but not limited to": 0.4,
        "and/or": 0.3,
        "may": 0.4,
        "generally": 0.5,
        "typically": 0.5,
        "substantially similar": 0.7,
    }

    # High-risk clause types (based on historical dispute data)
    HIGH_RISK_PATTERNS = {
        r"indemnif": 0.6,  # Indemnification clauses
        r"limitation of liability": 0.5,
        r"consequential damages": 0.5,
        r"termination for cause": 0.4,
        r"intellectual property": 0.4,
        r"confidential": 0.3,
        r"warranty": 0.4,
        r"force majeure": 0.3,
        r"governing law": 0.3,
        r"arbitration": 0.3,
    }

    def __init__(self, dispute_history: Optional[List[DisputeRecord]] = None):
        """
        Initialize scorer with optional historical dispute data.

        Args:
            dispute_history: List of historical dispute records for training
        """
        self.dispute_history = dispute_history or []
        self._clause_stats: Dict[str, Dict] = defaultdict(lambda: {
            "disputes": 0,
            "modifications": 0,
            "total_uses": 0,
            "resolution_times": [],
            "resolution_costs": [],
        })
        self._build_statistics()

    def _build_statistics(self) -> None:
        """Build statistical model from dispute history."""
        for record in self.dispute_history:
            stats = self._clause_stats[record.clause_hash]
            stats["disputes"] += 1
            stats["total_uses"] += 1
            stats["resolution_times"].append(record.resolution_time_days)
            stats["resolution_costs"].append(record.resolution_cost_usd)

    def _hash_clause(self, clause_text: str) -> str:
        """Generate consistent hash for clause comparison."""
        # Normalize: lowercase, remove extra whitespace
        normalized = " ".join(clause_text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _calculate_dispute_rate(self, clause_hash: str, clause_text: str) -> float:
        """Calculate historical dispute rate for this clause type."""
        stats = self._clause_stats.get(clause_hash)

        if stats and stats["total_uses"] > 0:
            # Historical rate with Bayesian smoothing
            alpha = 1  # Prior disputes
            beta = 10  # Prior non-disputes
            rate = (stats["disputes"] + alpha) / (stats["total_uses"] + alpha + beta)
            return min(rate, 1.0)

        # No history - use pattern-based estimation
        base_rate = 0.1
        for pattern, weight in self.HIGH_RISK_PATTERNS.items():
            if re.search(pattern, clause_text, re.IGNORECASE):
                base_rate = max(base_rate, weight)

        return base_rate

    def _calculate_ambiguity_score(self, clause_text: str) -> float:
        """Calculate linguistic ambiguity score."""
        text_lower = clause_text.lower()
        scores = []

        # Check for ambiguous terms
        for term, weight in self.AMBIGUOUS_TERMS.items():
            if term in text_lower:
                scores.append(weight)

        if not scores:
            return 0.1  # Low baseline ambiguity

        # Combine scores (diminishing returns for multiple issues)
        combined = 0.0
        for i, score in enumerate(sorted(scores, reverse=True)):
            combined += score * (0.7 ** i)  # Each subsequent issue adds less

        return min(combined, 1.0)

    def _calculate_modification_frequency(self, clause_hash: str) -> float:
        """Calculate how often this clause type gets modified."""
        stats = self._clause_stats.get(clause_hash)

        if stats and stats["total_uses"] > 0:
            return stats["modifications"] / stats["total_uses"]

        return 0.2  # Default moderate modification rate

    def _calculate_resolution_difficulty(self, clause_hash: str) -> float:
        """Calculate average difficulty of resolving disputes for this clause."""
        stats = self._clause_stats.get(clause_hash)

        if stats and stats["resolution_times"]:
            avg_time = sum(stats["resolution_times"]) / len(stats["resolution_times"])
            avg_cost = sum(stats["resolution_costs"]) / len(stats["resolution_costs"])

            # Normalize: 30 days = 0.5, $10k = 0.5
            time_score = min(avg_time / 60, 1.0)
            cost_score = min(avg_cost / 20000, 1.0)

            return (time_score + cost_score) / 2

        return 0.3  # Default moderate difficulty

    def _calculate_semantic_volatility(self, clause_text: str) -> float:
        """Calculate semantic interpretation variance."""
        # Simple heuristic: longer clauses with more conditionals = more volatility
        words = clause_text.split()
        word_count = len(words)

        # Count conditional/exception terms
        conditionals = sum(1 for w in words if w.lower() in [
            "if", "unless", "except", "provided", "however",
            "notwithstanding", "subject", "conditional"
        ])

        # Normalize
        length_factor = min(word_count / 100, 1.0) * 0.3
        conditional_factor = min(conditionals / 5, 1.0) * 0.7

        return length_factor + conditional_factor

    def _determine_level(self, score: float) -> EntropyLevel:
        """Determine entropy level from score."""
        if score < 0.3:
            return EntropyLevel.LOW
        elif score < 0.6:
            return EntropyLevel.MEDIUM
        elif score < 0.8:
            return EntropyLevel.HIGH
        else:
            return EntropyLevel.CRITICAL

    def _generate_warning(self, entropy: ClauseEntropy) -> Optional[str]:
        """Generate actionable warning based on entropy analysis."""
        warnings = []

        if entropy.ambiguity_score > 0.6:
            warnings.append("Contains highly ambiguous language")

        if entropy.dispute_rate > 0.5:
            warnings.append("High historical dispute rate")

        if entropy.resolution_difficulty > 0.7:
            warnings.append("Disputes are costly to resolve")

        if not warnings:
            return None

        return "; ".join(warnings) + ". Consider using hardened alternatives."

    def _suggest_alternatives(self, clause_text: str) -> List[str]:
        """Suggest less ambiguous alternative phrasings."""
        suggestions = []
        text_lower = clause_text.lower()

        # Common replacements
        replacements = {
            "reasonable time": "within 30 calendar days",
            "best efforts": "commercially reasonable efforts as defined in Section X",
            "promptly": "within 5 business days",
            "substantial": "more than 50%",
            "material": "affecting more than 10% of value",
            "as soon as practicable": "within 14 calendar days",
        }

        for vague, specific in replacements.items():
            if vague in text_lower:
                suggestions.append(f"Replace '{vague}' with '{specific}'")

        return suggestions[:3]  # Top 3 suggestions

    def score_clause(self, clause_text: str) -> ClauseEntropy:
        """
        Calculate entropy score for a clause.

        Args:
            clause_text: The clause text to analyze

        Returns:
            ClauseEntropy with detailed analysis
        """
        clause_hash = self._hash_clause(clause_text)

        # Calculate component scores
        dispute_rate = self._calculate_dispute_rate(clause_hash, clause_text)
        ambiguity_score = self._calculate_ambiguity_score(clause_text)
        modification_frequency = self._calculate_modification_frequency(clause_hash)
        resolution_difficulty = self._calculate_resolution_difficulty(clause_hash)
        semantic_volatility = self._calculate_semantic_volatility(clause_text)

        # Weighted combination
        entropy_score = (
            self.WEIGHTS["dispute_rate"] * dispute_rate +
            self.WEIGHTS["ambiguity_score"] * ambiguity_score +
            self.WEIGHTS["modification_frequency"] * modification_frequency +
            self.WEIGHTS["resolution_difficulty"] * resolution_difficulty +
            self.WEIGHTS["semantic_volatility"] * semantic_volatility
        )

        # Determine confidence based on sample size
        stats = self._clause_stats.get(clause_hash, {})
        sample_size = stats.get("total_uses", 0)
        confidence = min(sample_size / 100, 1.0) if sample_size > 0 else 0.3

        entropy = ClauseEntropy(
            clause_hash=clause_hash,
            clause_text=clause_text[:200],  # Truncate for storage
            entropy_score=entropy_score,
            level=self._determine_level(entropy_score),
            dispute_rate=dispute_rate,
            ambiguity_score=ambiguity_score,
            modification_frequency=modification_frequency,
            resolution_difficulty=resolution_difficulty,
            semantic_volatility=semantic_volatility,
            confidence=confidence,
            sample_size=sample_size,
            last_updated=datetime.utcnow(),
        )

        # Add actionable insights
        entropy.warning = self._generate_warning(entropy)
        entropy.suggested_alternatives = self._suggest_alternatives(clause_text)

        return entropy

    def score_contract(self, clauses: List[str]) -> Dict[str, Any]:
        """
        Score all clauses in a contract.

        Args:
            clauses: List of clause texts

        Returns:
            Contract-level entropy analysis
        """
        clause_scores = [self.score_clause(c) for c in clauses]

        # Aggregate metrics
        total_entropy = sum(c.entropy_score for c in clause_scores) / len(clause_scores)
        high_risk_clauses = [c for c in clause_scores if c.level in (EntropyLevel.HIGH, EntropyLevel.CRITICAL)]

        return {
            "overall_entropy": round(total_entropy, 4),
            "overall_level": self._determine_level(total_entropy).value,
            "total_clauses": len(clauses),
            "high_risk_count": len(high_risk_clauses),
            "high_risk_clauses": [c.to_dict() for c in high_risk_clauses],
            "all_clauses": [c.to_dict() for c in clause_scores],
            "dispute_probability": round(1 - (1 - total_entropy) ** len(clauses), 4),
        }

    def record_dispute(self, record: DisputeRecord) -> None:
        """
        Record a dispute for model improvement.

        Args:
            record: Dispute record to add to history
        """
        self.dispute_history.append(record)

        # Update statistics
        stats = self._clause_stats[record.clause_hash]
        stats["disputes"] += 1
        stats["total_uses"] += 1
        stats["resolution_times"].append(record.resolution_time_days)
        stats["resolution_costs"].append(record.resolution_cost_usd)

    def record_modification(self, clause_hash: str) -> None:
        """Record that a clause was modified during negotiation."""
        self._clause_stats[clause_hash]["modifications"] += 1
        self._clause_stats[clause_hash]["total_uses"] += 1

    def record_acceptance(self, clause_hash: str) -> None:
        """Record that a clause was accepted without modification."""
        self._clause_stats[clause_hash]["total_uses"] += 1


# Convenience function
def calculate_clause_entropy(clause_text: str) -> ClauseEntropy:
    """
    Quick entropy calculation for a single clause.

    Args:
        clause_text: The clause to analyze

    Returns:
        ClauseEntropy analysis
    """
    scorer = EntropyScorer()
    return scorer.score_clause(clause_text)
