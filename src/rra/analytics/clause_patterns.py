# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Clause Pattern Analysis for License Entropy Oracle.

Identifies patterns in license clauses to:
1. Cluster similar clauses across different licenses
2. Detect clause templates and variations
3. Find "what causes fights" - common dispute triggers
4. Recommend hardened alternatives based on successful patterns

Uses TF-IDF and semantic similarity for clustering.
"""

import hashlib
import re
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import math


class ClauseCategory(Enum):
    """Standard license clause categories."""

    GRANT = "grant"  # License grant
    RESTRICTIONS = "restrictions"  # Usage restrictions
    ATTRIBUTION = "attribution"  # Attribution requirements
    WARRANTY = "warranty"  # Warranty provisions
    LIABILITY = "liability"  # Liability limitations
    INDEMNIFICATION = "indemnification"  # Indemnity clauses
    TERMINATION = "termination"  # Termination conditions
    CONFIDENTIALITY = "confidentiality"  # Confidentiality obligations
    IP_OWNERSHIP = "ip_ownership"  # IP ownership terms
    PAYMENT = "payment"  # Payment terms
    SUPPORT = "support"  # Support obligations
    AUDIT = "audit"  # Audit rights
    GOVERNING_LAW = "governing_law"  # Jurisdiction
    DISPUTE_RESOLUTION = "dispute"  # Dispute resolution
    FORCE_MAJEURE = "force_majeure"  # Force majeure
    MISCELLANEOUS = "miscellaneous"  # Other


@dataclass
class ClausePattern:
    """A pattern identified across multiple clauses."""

    pattern_id: str
    category: ClauseCategory
    template: str  # Normalized template with placeholders
    examples: List[str] = field(default_factory=list)
    dispute_rate: float = 0.0  # Historical dispute rate
    success_rate: float = 0.0  # Rate of successful resolutions
    frequency: int = 0  # How often this pattern appears
    variations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "category": self.category.value,
            "template": self.template,
            "dispute_rate": round(self.dispute_rate, 4),
            "success_rate": round(self.success_rate, 4),
            "frequency": self.frequency,
            "example_count": len(self.examples),
        }


@dataclass
class PatternCluster:
    """A cluster of similar clauses."""

    cluster_id: str
    category: ClauseCategory
    centroid: str  # Representative clause
    members: List[str] = field(default_factory=list)
    avg_entropy: float = 0.0
    dispute_triggers: List[str] = field(default_factory=list)
    hardened_alternative: Optional[str] = None


class ClausePatternAnalyzer:
    """
    Analyzes clause patterns to identify dispute-prone language.

    Uses a combination of:
    - Keyword matching for category classification
    - TF-IDF for term importance
    - Jaccard similarity for clustering
    - Historical data for dispute correlation
    """

    # Category detection keywords
    CATEGORY_KEYWORDS = {
        ClauseCategory.GRANT: ["grant", "license", "permission", "right to use", "authorize"],
        ClauseCategory.RESTRICTIONS: [
            "shall not",
            "prohibited",
            "restricted",
            "limitation",
            "exclude",
        ],
        ClauseCategory.ATTRIBUTION: [
            "attribution",
            "credit",
            "acknowledge",
            "notice",
            "copyright notice",
        ],
        ClauseCategory.WARRANTY: ["warranty", "warrant", "as is", "merchantability", "fitness"],
        ClauseCategory.LIABILITY: [
            "liability",
            "liable",
            "damages",
            "consequential",
            "limitation of",
        ],
        ClauseCategory.INDEMNIFICATION: ["indemnify", "indemnification", "hold harmless", "defend"],
        ClauseCategory.TERMINATION: ["termination", "terminate", "expiration", "cancel", "revoke"],
        ClauseCategory.CONFIDENTIALITY: ["confidential", "proprietary", "non-disclosure", "secret"],
        ClauseCategory.IP_OWNERSHIP: [
            "intellectual property",
            "ownership",
            "title",
            "patent",
            "trademark",
        ],
        ClauseCategory.PAYMENT: ["payment", "fee", "royalty", "price", "compensation"],
        ClauseCategory.SUPPORT: ["support", "maintenance", "updates", "assistance"],
        ClauseCategory.AUDIT: ["audit", "inspection", "review", "examine"],
        ClauseCategory.GOVERNING_LAW: ["governing law", "jurisdiction", "venue", "applicable law"],
        ClauseCategory.DISPUTE_RESOLUTION: ["dispute", "arbitration", "mediation", "resolution"],
        ClauseCategory.FORCE_MAJEURE: ["force majeure", "act of god", "beyond control"],
    }

    # Common dispute triggers (phrases that correlate with disputes)
    DISPUTE_TRIGGERS = {
        # Ambiguous scope
        "including but not limited to": "Scope ambiguity - disputes over what's included",
        "reasonable": "Subjective standard - parties disagree on what's reasonable",
        "material": "Threshold ambiguity - disputes over materiality",
        # Unclear obligations
        "best efforts": "Effort level disputes",
        "promptly": "Timing disputes - what counts as prompt",
        "as soon as practicable": "Timing disputes",
        # Scope creep
        "and related": "Scope creep - disputes over what's related",
        "substantially similar": "Similarity disputes",
        "derivative": "Derivative work scope disputes",
        # Financial ambiguity
        "fair market value": "Valuation disputes",
        "reasonable compensation": "Compensation disputes",
    }

    # Hardened alternatives for common problem patterns
    HARDENED_ALTERNATIVES = {
        "reasonable time": [
            "within 30 calendar days",
            "within 14 business days",
            "within the timeframe specified in Schedule A",
        ],
        "best efforts": [
            "commercially reasonable efforts, which shall include [specific actions]",
            "efforts consistent with industry standard practices as documented in [reference]",
        ],
        "material breach": [
            "a breach that results in damages exceeding $[amount] or prevents [specific outcome]",
            "failure to perform any obligation listed in Section [X] as material",
        ],
        "reasonable notice": [
            "written notice delivered at least 30 days prior",
            "notice via registered mail at least 14 days prior",
        ],
    }

    def __init__(self):
        """Initialize the pattern analyzer."""
        self._patterns: Dict[str, ClausePattern] = {}
        self._clusters: Dict[str, PatternCluster] = {}
        self._idf_cache: Dict[str, float] = {}
        self._document_count = 0

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for analysis."""
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r"\b[a-z]+\b", text.lower())
        # Remove common stopwords
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "such",
            "any",
            "all",
            "each",
            "every",
        }
        return [t for t in tokens if t not in stopwords and len(t) > 2]

    def _calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Calculate term frequency."""
        tf = defaultdict(int)
        for token in tokens:
            tf[token] += 1

        # Normalize by document length
        total = len(tokens) or 1
        return {k: v / total for k, v in tf.items()}

    def _update_idf(self, tokens: Set[str]) -> None:
        """Update IDF cache with new document."""
        self._document_count += 1
        for token in tokens:
            self._idf_cache[token] = self._idf_cache.get(token, 0) + 1

    def _get_idf(self, token: str) -> float:
        """Get IDF for a token."""
        if self._document_count == 0:
            return 1.0
        doc_freq = self._idf_cache.get(token, 1)
        return math.log(self._document_count / doc_freq) + 1

    def _calculate_tfidf(self, text: str) -> Dict[str, float]:
        """Calculate TF-IDF vector for text."""
        tokens = self._tokenize(text)
        tf = self._calculate_tf(tokens)
        return {k: v * self._get_idf(k) for k, v in tf.items()}

    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two token sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculate cosine similarity between TF-IDF vectors."""
        all_terms = set(vec1.keys()) | set(vec2.keys())

        dot_product = sum(vec1.get(t, 0) * vec2.get(t, 0) for t in all_terms)
        norm1 = math.sqrt(sum(v**2 for v in vec1.values())) or 1
        norm2 = math.sqrt(sum(v**2 for v in vec2.values())) or 1

        return dot_product / (norm1 * norm2)

    def classify_category(self, clause_text: str) -> ClauseCategory:
        """
        Classify a clause into a category.

        Args:
            clause_text: The clause to classify

        Returns:
            ClauseCategory enum value
        """
        text_lower = clause_text.lower()
        scores = defaultdict(int)

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[category] += 1

        if not scores:
            return ClauseCategory.MISCELLANEOUS

        return max(scores, key=scores.get)

    def find_dispute_triggers(self, clause_text: str) -> List[Dict[str, str]]:
        """
        Find potential dispute triggers in a clause.

        Args:
            clause_text: The clause to analyze

        Returns:
            List of trigger phrases and their risk descriptions
        """
        text_lower = clause_text.lower()
        triggers = []

        for trigger, description in self.DISPUTE_TRIGGERS.items():
            if trigger in text_lower:
                triggers.append(
                    {
                        "trigger": trigger,
                        "description": description,
                        "position": text_lower.find(trigger),
                    }
                )

        return triggers

    def suggest_hardening(self, clause_text: str) -> List[Dict[str, Any]]:
        """
        Suggest hardened alternatives for ambiguous language.

        Args:
            clause_text: The clause to analyze

        Returns:
            List of suggestions with original phrase and alternatives
        """
        text_lower = clause_text.lower()
        suggestions = []

        for problem_phrase, alternatives in self.HARDENED_ALTERNATIVES.items():
            if problem_phrase in text_lower:
                suggestions.append(
                    {
                        "original": problem_phrase,
                        "alternatives": alternatives,
                        "rationale": f"'{problem_phrase}' is often disputed; consider specific language",
                    }
                )

        return suggestions

    def extract_pattern(self, clause_text: str) -> str:
        """
        Extract a normalized pattern from a clause.

        Replaces specific values with placeholders to identify templates.

        Args:
            clause_text: The clause to analyze

        Returns:
            Normalized pattern template
        """
        pattern = clause_text

        # Replace numbers with placeholder
        pattern = re.sub(r"\b\d+\b", "[NUMBER]", pattern)

        # Replace dates
        pattern = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "[DATE]", pattern)

        # Replace currency amounts
        pattern = re.sub(r"\$[\d,]+(?:\.\d{2})?", "[AMOUNT]", pattern)

        # Replace email addresses
        pattern = re.sub(r"\b[\w.-]+@[\w.-]+\.\w+\b", "[EMAIL]", pattern)

        # Replace URLs
        pattern = re.sub(r"https?://\S+", "[URL]", pattern)

        # Replace quoted strings (company names, etc.)
        pattern = re.sub(r'"[^"]*"', "[QUOTED]", pattern)

        return pattern

    def add_clause(self, clause_text: str, disputed: bool = False) -> str:
        """
        Add a clause to the pattern database.

        Args:
            clause_text: The clause to add
            disputed: Whether this clause led to a dispute

        Returns:
            Pattern ID for the clause
        """
        # Extract pattern and categorize
        pattern_template = self.extract_pattern(clause_text)
        category = self.classify_category(clause_text)

        # Generate pattern ID from template
        pattern_id = hashlib.sha256(pattern_template.encode()).hexdigest()[:12]

        # Update or create pattern
        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            pattern.examples.append(clause_text[:200])
            pattern.frequency += 1
            if disputed:
                pattern.dispute_rate = (
                    pattern.dispute_rate * (pattern.frequency - 1) + 1
                ) / pattern.frequency
        else:
            pattern = ClausePattern(
                pattern_id=pattern_id,
                category=category,
                template=pattern_template,
                examples=[clause_text[:200]],
                frequency=1,
                dispute_rate=1.0 if disputed else 0.0,
            )
            self._patterns[pattern_id] = pattern

        # Update IDF
        tokens = set(self._tokenize(clause_text))
        self._update_idf(tokens)

        return pattern_id

    def find_similar_patterns(
        self, clause_text: str, threshold: float = 0.5, limit: int = 5
    ) -> List[Tuple[ClausePattern, float]]:
        """
        Find similar patterns to a given clause.

        Args:
            clause_text: The clause to match
            threshold: Minimum similarity (0-1)
            limit: Maximum results

        Returns:
            List of (pattern, similarity_score) tuples
        """
        query_tfidf = self._calculate_tfidf(clause_text)
        query_tokens = set(self._tokenize(clause_text))

        results = []
        for pattern in self._patterns.values():
            # Calculate similarity using both methods
            pattern_tfidf = self._calculate_tfidf(pattern.template)
            pattern_tokens = set(self._tokenize(pattern.template))

            cosine_sim = self._cosine_similarity(query_tfidf, pattern_tfidf)
            jaccard_sim = self._jaccard_similarity(query_tokens, pattern_tokens)

            # Combined score
            similarity = 0.7 * cosine_sim + 0.3 * jaccard_sim

            if similarity >= threshold:
                results.append((pattern, similarity))

        # Sort by similarity and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_category_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each clause category."""
        stats = defaultdict(
            lambda: {
                "count": 0,
                "total_disputes": 0,
                "avg_dispute_rate": 0.0,
                "patterns": [],
            }
        )

        for pattern in self._patterns.values():
            cat_stats = stats[pattern.category.value]
            cat_stats["count"] += pattern.frequency
            cat_stats["total_disputes"] += int(pattern.dispute_rate * pattern.frequency)
            cat_stats["patterns"].append(pattern.pattern_id)

        # Calculate averages
        for cat, cat_stats in stats.items():
            if cat_stats["count"] > 0:
                cat_stats["avg_dispute_rate"] = cat_stats["total_disputes"] / cat_stats["count"]

        return dict(stats)

    def get_high_risk_patterns(self, min_frequency: int = 3) -> List[ClausePattern]:
        """Get patterns with high dispute rates."""
        return sorted(
            [
                p
                for p in self._patterns.values()
                if p.frequency >= min_frequency and p.dispute_rate > 0.3
            ],
            key=lambda p: p.dispute_rate,
            reverse=True,
        )

    def analyze_clause(self, clause_text: str) -> Dict[str, Any]:
        """
        Comprehensive clause analysis.

        Args:
            clause_text: The clause to analyze

        Returns:
            Complete analysis including category, triggers, and suggestions
        """
        category = self.classify_category(clause_text)
        triggers = self.find_dispute_triggers(clause_text)
        suggestions = self.suggest_hardening(clause_text)
        similar = self.find_similar_patterns(clause_text)

        return {
            "category": category.value,
            "dispute_triggers": triggers,
            "hardening_suggestions": suggestions,
            "similar_patterns": [
                {"pattern_id": p.pattern_id, "similarity": s, "dispute_rate": p.dispute_rate}
                for p, s in similar
            ],
            "risk_level": "high" if len(triggers) > 2 else "medium" if triggers else "low",
        }
