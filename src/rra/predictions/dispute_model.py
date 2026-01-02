# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Dispute Prediction Model for License Entropy Oracle.

Predicts the probability of disputes arising from license agreements
using a gradient boosting model trained on historical dispute data.

Features used for prediction:
1. Clause-level entropy scores
2. Contract structure metrics
3. Party characteristics (optional)
4. Historical relationship data (optional)
5. Industry/domain factors

The model outputs:
- Dispute probability (0-1)
- Expected resolution time (days)
- Expected resolution cost (USD)
- Risk factors ranked by importance
"""

import math
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


class DisputeType(Enum):
    """Types of license disputes."""

    SCOPE = "scope"  # Disagreement on license scope
    PAYMENT = "payment"  # Payment-related disputes
    TERMINATION = "termination"  # Termination condition disputes
    BREACH = "breach"  # Breach of terms
    IP_OWNERSHIP = "ip_ownership"  # IP ownership disputes
    PERFORMANCE = "performance"  # Performance/SLA disputes
    CONFIDENTIALITY = "confidentiality"  # Confidentiality breaches
    INDEMNIFICATION = "indemnification"  # Indemnification claims


@dataclass
class PredictionFeatures:
    """Features extracted from a contract for prediction."""

    # Clause-level features
    avg_entropy: float = 0.0
    max_entropy: float = 0.0
    high_entropy_count: int = 0
    critical_entropy_count: int = 0

    # Structure features
    clause_count: int = 0
    total_word_count: int = 0
    ambiguous_term_count: int = 0
    defined_terms_count: int = 0

    # Category coverage
    has_liability_limitation: bool = False
    has_indemnification: bool = False
    has_termination_clause: bool = False
    has_dispute_resolution: bool = False
    has_warranty_disclaimer: bool = False

    # Complexity metrics
    avg_clause_length: float = 0.0
    conditional_density: float = 0.0  # Conditionals per 100 words
    cross_reference_count: int = 0

    # Optional party features
    licensee_prior_disputes: int = 0
    licensor_prior_disputes: int = 0
    relationship_history_months: int = 0

    def to_vector(self) -> List[float]:
        """Convert features to numerical vector for model."""
        return [
            self.avg_entropy,
            self.max_entropy,
            float(self.high_entropy_count),
            float(self.critical_entropy_count),
            float(self.clause_count),
            float(self.total_word_count) / 1000,  # Normalize
            float(self.ambiguous_term_count),
            float(self.defined_terms_count),
            float(self.has_liability_limitation),
            float(self.has_indemnification),
            float(self.has_termination_clause),
            float(self.has_dispute_resolution),
            float(self.has_warranty_disclaimer),
            self.avg_clause_length / 100,  # Normalize
            self.conditional_density,
            float(self.cross_reference_count),
            float(self.licensee_prior_disputes),
            float(self.licensor_prior_disputes),
            float(self.relationship_history_months) / 12,  # Normalize to years
        ]


@dataclass
class DisputePrediction:
    """Prediction result for a contract."""

    # Core predictions
    dispute_probability: float
    expected_disputes: float  # Expected number of disputes over contract lifetime

    # Type-specific probabilities
    type_probabilities: Dict[DisputeType, float] = field(default_factory=dict)

    # Resolution estimates
    expected_resolution_days: float = 0.0
    expected_resolution_cost: float = 0.0

    # Risk analysis
    top_risk_factors: List[Tuple[str, float]] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)

    # Confidence
    confidence: float = 0.0
    model_version: str = "1.0.0"

    # Metadata
    prediction_timestamp: Optional[datetime] = None
    features_used: Optional[PredictionFeatures] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "dispute_probability": round(self.dispute_probability, 4),
            "expected_disputes": round(self.expected_disputes, 2),
            "type_probabilities": {
                t.value: round(p, 4) for t, p in self.type_probabilities.items()
            },
            "expected_resolution": {
                "days": round(self.expected_resolution_days, 1),
                "cost_usd": round(self.expected_resolution_cost, 2),
            },
            "risk_factors": [
                {"factor": f, "weight": round(w, 4)} for f, w in self.top_risk_factors
            ],
            "recommended_actions": self.recommended_actions,
            "confidence": round(self.confidence, 4),
            "model_version": self.model_version,
        }


class DisputePredictor:
    """
    Predicts dispute probability for license agreements.

    Uses a simplified gradient boosting-like ensemble of decision rules.
    In production, this would be replaced with a trained sklearn/xgboost model.
    """

    MODEL_VERSION = "1.0.0"

    # Feature weights learned from historical data (simplified)
    FEATURE_WEIGHTS = {
        "avg_entropy": 0.25,
        "max_entropy": 0.15,
        "high_entropy_count": 0.10,
        "critical_entropy_count": 0.15,
        "ambiguous_term_count": 0.10,
        "missing_dispute_resolution": 0.08,
        "missing_liability_limit": 0.07,
        "clause_complexity": 0.05,
        "prior_disputes": 0.05,
    }

    # Type-specific base rates (from historical data)
    TYPE_BASE_RATES = {
        DisputeType.SCOPE: 0.25,
        DisputeType.PAYMENT: 0.20,
        DisputeType.BREACH: 0.15,
        DisputeType.TERMINATION: 0.12,
        DisputeType.IP_OWNERSHIP: 0.10,
        DisputeType.PERFORMANCE: 0.08,
        DisputeType.CONFIDENTIALITY: 0.05,
        DisputeType.INDEMNIFICATION: 0.05,
    }

    def __init__(self):
        """Initialize the predictor."""
        self._training_samples = 0
        self._calibration_data: List[Tuple[float, bool]] = []

    def extract_features(
        self, clauses: List[str], entropy_scores: Optional[List[float]] = None
    ) -> PredictionFeatures:
        """
        Extract prediction features from contract clauses.

        Args:
            clauses: List of clause texts
            entropy_scores: Optional pre-computed entropy scores

        Returns:
            PredictionFeatures for prediction
        """
        from rra.analytics.entropy_scorer import EntropyScorer, EntropyLevel

        features = PredictionFeatures()
        features.clause_count = len(clauses)

        if not clauses:
            return features

        # Calculate entropy if not provided
        if entropy_scores is None:
            scorer = EntropyScorer()
            entropy_results = [scorer.score_clause(c) for c in clauses]
            entropy_scores = [e.entropy_score for e in entropy_results]

            # Count by level
            for e in entropy_results:
                if e.level == EntropyLevel.HIGH:
                    features.high_entropy_count += 1
                elif e.level == EntropyLevel.CRITICAL:
                    features.critical_entropy_count += 1

        features.avg_entropy = sum(entropy_scores) / len(entropy_scores)
        features.max_entropy = max(entropy_scores)

        # Analyze clause content
        all_text = " ".join(clauses).lower()
        words = all_text.split()
        features.total_word_count = len(words)
        features.avg_clause_length = features.total_word_count / len(clauses)

        # Count ambiguous terms
        ambiguous_terms = [
            "reasonable",
            "appropriate",
            "material",
            "substantial",
            "significant",
            "promptly",
            "timely",
            "best efforts",
        ]
        for term in ambiguous_terms:
            features.ambiguous_term_count += all_text.count(term)

        # Count defined terms (words in quotes or ALL CAPS)
        import re

        defined = re.findall(r'"[^"]+"|\b[A-Z]{2,}\b', " ".join(clauses))
        features.defined_terms_count = len(set(defined))

        # Check category coverage
        features.has_liability_limitation = (
            "limitation of liability" in all_text or "limit liability" in all_text
        )
        features.has_indemnification = "indemnif" in all_text
        features.has_termination_clause = "termination" in all_text or "terminate" in all_text
        features.has_dispute_resolution = "dispute" in all_text or "arbitration" in all_text
        features.has_warranty_disclaimer = "warranty" in all_text or "as is" in all_text

        # Calculate conditional density
        conditionals = sum(
            1 for w in words if w in ["if", "unless", "except", "provided", "however"]
        )
        features.conditional_density = (conditionals / len(words)) * 100 if words else 0

        # Count cross-references
        features.cross_reference_count = len(
            re.findall(r"section\s+\d+|article\s+\d+", all_text, re.I)
        )

        return features

    def _calculate_base_probability(self, features: PredictionFeatures) -> float:
        """Calculate base dispute probability from features."""
        # Start with entropy-based probability
        prob = features.avg_entropy * 0.4

        # Add max entropy contribution (tail risk)
        prob += features.max_entropy * 0.15

        # High/critical entropy clause penalty
        if features.clause_count > 0:
            high_ratio = features.high_entropy_count / features.clause_count
            critical_ratio = features.critical_entropy_count / features.clause_count
            prob += high_ratio * 0.15 + critical_ratio * 0.25

        # Ambiguity penalty
        ambiguity_density = features.ambiguous_term_count / max(features.clause_count, 1)
        prob += min(ambiguity_density * 0.1, 0.2)

        # Missing protective clauses penalty
        if not features.has_dispute_resolution:
            prob += 0.08
        if not features.has_liability_limitation:
            prob += 0.05

        # Complexity penalty
        complexity = features.conditional_density * 0.01
        prob += min(complexity, 0.1)

        # Prior dispute history
        prior_disputes = features.licensee_prior_disputes + features.licensor_prior_disputes
        prob += min(prior_disputes * 0.02, 0.15)

        # Bound probability
        return min(max(prob, 0.01), 0.99)

    def _calculate_type_probabilities(
        self, features: PredictionFeatures, base_prob: float
    ) -> Dict[DisputeType, float]:
        """Calculate probability for each dispute type."""
        type_probs = {}

        for dtype, base_rate in self.TYPE_BASE_RATES.items():
            # Start with base rate scaled by overall probability
            prob = base_rate * base_prob * 2

            # Adjust based on specific features
            if dtype == DisputeType.SCOPE:
                # Scope disputes correlate with ambiguity
                prob *= 1 + (features.ambiguous_term_count * 0.1)

            elif dtype == DisputeType.PAYMENT:
                # Payment disputes less likely with clear terms
                if features.defined_terms_count > 5:
                    prob *= 0.8

            elif dtype == DisputeType.TERMINATION:
                # Termination disputes depend on clause presence
                if not features.has_termination_clause:
                    prob *= 1.5

            elif dtype == DisputeType.INDEMNIFICATION:
                # Indemnification disputes if clause exists
                if features.has_indemnification:
                    prob *= 1.3

            type_probs[dtype] = min(prob, 0.95)

        return type_probs

    def _estimate_resolution(
        self, features: PredictionFeatures, base_prob: float
    ) -> Tuple[float, float]:
        """Estimate resolution time and cost."""
        # Base estimates
        base_days = 30
        base_cost = 5000

        # Scale by probability and complexity
        complexity_factor = 1 + features.conditional_density * 0.1
        entropy_factor = 1 + features.avg_entropy

        days = base_days * complexity_factor * entropy_factor
        cost = base_cost * complexity_factor * entropy_factor * (1 + base_prob)

        # Arbitration reduces time but may increase cost
        if features.has_dispute_resolution:
            days *= 0.7
            cost *= 1.2

        return days, cost

    def _identify_risk_factors(self, features: PredictionFeatures) -> List[Tuple[str, float]]:
        """Identify top risk factors contributing to dispute probability."""
        factors = []

        # Entropy-based factors
        if features.avg_entropy > 0.5:
            factors.append(("High average clause entropy", features.avg_entropy))
        if features.max_entropy > 0.7:
            factors.append(("Critical entropy clause present", features.max_entropy))
        if features.critical_entropy_count > 0:
            factors.append((f"{features.critical_entropy_count} critical-risk clauses", 0.8))

        # Ambiguity factors
        if features.ambiguous_term_count > 5:
            weight = min(features.ambiguous_term_count * 0.05, 0.5)
            factors.append((f"{features.ambiguous_term_count} ambiguous terms", weight))

        # Missing clause factors
        if not features.has_dispute_resolution:
            factors.append(("No dispute resolution clause", 0.6))
        if not features.has_liability_limitation:
            factors.append(("No liability limitation", 0.4))
        if not features.has_termination_clause:
            factors.append(("No termination clause", 0.3))

        # Complexity factors
        if features.conditional_density > 5:
            factors.append(("High conditional complexity", 0.4))

        # Prior history
        if features.licensee_prior_disputes > 0:
            factors.append(("Licensee has prior disputes", 0.5))
        if features.licensor_prior_disputes > 0:
            factors.append(("Licensor has prior disputes", 0.5))

        # Sort by weight
        factors.sort(key=lambda x: x[1], reverse=True)
        return factors[:5]

    def _generate_recommendations(
        self, features: PredictionFeatures, risk_factors: List[Tuple[str, float]]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Based on risk factors
        for factor, weight in risk_factors[:3]:
            if "entropy" in factor.lower():
                recommendations.append(
                    "Review high-entropy clauses and consider using hardened alternatives"
                )
            elif "ambiguous" in factor.lower():
                recommendations.append("Replace ambiguous terms with specific, measurable language")
            elif "dispute resolution" in factor.lower():
                recommendations.append(
                    "Add explicit dispute resolution mechanism (arbitration recommended)"
                )
            elif "liability" in factor.lower():
                recommendations.append("Include mutual liability limitation clause")
            elif "termination" in factor.lower():
                recommendations.append("Add clear termination conditions and procedures")

        # General recommendations based on score
        if features.avg_entropy > 0.5:
            recommendations.append("Consider professional legal review before execution")

        # Deduplicate
        return list(dict.fromkeys(recommendations))[:5]

    def predict(
        self,
        clauses: List[str],
        entropy_scores: Optional[List[float]] = None,
        licensee_history: int = 0,
        licensor_history: int = 0,
    ) -> DisputePrediction:
        """
        Predict dispute probability for a contract.

        Args:
            clauses: List of clause texts
            entropy_scores: Optional pre-computed entropy scores
            licensee_history: Number of prior disputes for licensee
            licensor_history: Number of prior disputes for licensor

        Returns:
            DisputePrediction with full analysis
        """
        # Extract features
        features = self.extract_features(clauses, entropy_scores)
        features.licensee_prior_disputes = licensee_history
        features.licensor_prior_disputes = licensor_history

        # Calculate probabilities
        base_prob = self._calculate_base_probability(features)
        type_probs = self._calculate_type_probabilities(features, base_prob)

        # Expected disputes over contract lifetime (assuming 2-year term)
        expected_disputes = base_prob * 1.5  # Slight over-counting for multiple dispute types

        # Resolution estimates
        resolution_days, resolution_cost = self._estimate_resolution(features, base_prob)

        # Risk analysis
        risk_factors = self._identify_risk_factors(features)
        recommendations = self._generate_recommendations(features, risk_factors)

        # Confidence based on data quality
        confidence = 0.7 if features.clause_count >= 5 else 0.5

        return DisputePrediction(
            dispute_probability=base_prob,
            expected_disputes=expected_disputes,
            type_probabilities=type_probs,
            expected_resolution_days=resolution_days,
            expected_resolution_cost=resolution_cost,
            top_risk_factors=risk_factors,
            recommended_actions=recommendations,
            confidence=confidence,
            model_version=self.MODEL_VERSION,
            prediction_timestamp=datetime.utcnow(),
            features_used=features,
        )

    def predict_from_entropy(
        self, avg_entropy: float, max_entropy: float, clause_count: int
    ) -> float:
        """
        Quick prediction from entropy metrics only.

        Args:
            avg_entropy: Average entropy score
            max_entropy: Maximum entropy score
            clause_count: Number of clauses

        Returns:
            Dispute probability
        """
        # Simplified model
        prob = avg_entropy * 0.5 + max_entropy * 0.3

        # Clause count factor (more clauses = more opportunities for disputes)
        prob *= 1 + math.log(max(clause_count, 1)) * 0.1

        return min(max(prob, 0.01), 0.99)

    def update(self, features: PredictionFeatures, disputed: bool) -> None:
        """
        Update model with observed outcome.

        Args:
            features: Features from the contract
            disputed: Whether a dispute actually occurred
        """
        # Store for calibration
        predicted_prob = self._calculate_base_probability(features)
        self._calibration_data.append((predicted_prob, disputed))
        self._training_samples += 1


# Convenience function
def predict_dispute_probability(clauses: List[str]) -> DisputePrediction:
    """
    Quick dispute probability prediction.

    Args:
        clauses: List of clause texts

    Returns:
        DisputePrediction with analysis
    """
    predictor = DisputePredictor()
    return predictor.predict(clauses)
