# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
High-Entropy Term Detection and Analysis.

Identifies and analyzes terms in contracts that contribute to dispute risk:
- Semantic entropy analysis
- Historical dispute correlation
- Term clustering and categorization
- Trend detection across contracts

Part of Phase 6.6: Predictive Dispute Warnings
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TermRiskLevel(Enum):
    """Risk level for a term."""

    SAFE = "safe"  # Low dispute correlation
    MODERATE = "moderate"  # Some dispute potential
    HIGH = "high"  # Frequently disputed
    CRITICAL = "critical"  # Almost always disputed


class TermCategory(Enum):
    """Categories of legal terms."""

    TEMPORAL = "temporal"  # Time-related terms
    QUANTITATIVE = "quantitative"  # Amount/quantity terms
    OBLIGATORY = "obligatory"  # Obligation terms (shall, must, etc.)
    PERMISSIVE = "permissive"  # Permission terms (may, can, etc.)
    CONDITIONAL = "conditional"  # Conditional terms (if, unless, etc.)
    DEFINITIONAL = "definitional"  # Defining terms
    SCOPE = "scope"  # Scope-related terms
    STANDARD = "standard"  # Standard of care terms


@dataclass
class TermOccurrence:
    """An occurrence of a term in a contract."""

    term: str
    position: int  # Character position
    clause_index: int  # Which clause
    context: str  # Surrounding text
    normalized: str  # Normalized form


@dataclass
class TermAnalysis:
    """Analysis result for a term."""

    term: str
    normalized_form: str
    category: TermCategory
    risk_level: TermRiskLevel
    entropy_score: float  # 0-1, how ambiguous
    dispute_rate: float  # Historical dispute rate
    frequency: int  # How often it appears
    occurrences: List[TermOccurrence] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "term": self.term,
            "normalized_form": self.normalized_form,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "entropy_score": round(self.entropy_score, 4),
            "dispute_rate": round(self.dispute_rate, 4),
            "frequency": self.frequency,
            "occurrence_count": len(self.occurrences),
            "alternatives": self.alternatives,
            "explanation": self.explanation,
        }


@dataclass
class TermReport:
    """Complete term analysis report for a contract."""

    contract_id: str
    terms: List[TermAnalysis]
    high_risk_count: int
    total_entropy: float
    avg_entropy: float
    risk_distribution: Dict[TermRiskLevel, int]
    category_distribution: Dict[TermCategory, int]
    top_concerns: List[str]
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "contract_id": self.contract_id,
            "summary": {
                "term_count": len(self.terms),
                "high_risk_count": self.high_risk_count,
                "total_entropy": round(self.total_entropy, 4),
                "avg_entropy": round(self.avg_entropy, 4),
            },
            "risk_distribution": {k.value: v for k, v in self.risk_distribution.items()},
            "category_distribution": {k.value: v for k, v in self.category_distribution.items()},
            "top_concerns": self.top_concerns,
            "terms": [t.to_dict() for t in self.terms],
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class TermAnalyzer:
    """
    Analyzes terms in contracts for dispute risk.

    Identifies high-entropy terms that historically correlate
    with disputes and provides actionable insights.
    """

    # Known high-risk terms with metadata
    TERM_DATABASE = {
        # Temporal terms
        "reasonable time": {
            "category": TermCategory.TEMPORAL,
            "entropy": 0.8,
            "dispute_rate": 0.35,
            "explanation": "Subjective time standard with no clear definition",
            "alternatives": ["within 30 days", "within 14 business days"],
        },
        "promptly": {
            "category": TermCategory.TEMPORAL,
            "entropy": 0.7,
            "dispute_rate": 0.28,
            "explanation": "Vague timing requirement",
            "alternatives": ["within 5 business days", "within 48 hours"],
        },
        "timely": {
            "category": TermCategory.TEMPORAL,
            "entropy": 0.65,
            "dispute_rate": 0.25,
            "explanation": "Undefined time expectation",
            "alternatives": ["within [X] days", "by [specific date]"],
        },
        "as soon as practicable": {
            "category": TermCategory.TEMPORAL,
            "entropy": 0.75,
            "dispute_rate": 0.32,
            "explanation": "Combines timing and feasibility ambiguity",
            "alternatives": ["within 10 business days", "by [date] or with written explanation"],
        },
        # Standard of care terms
        "best efforts": {
            "category": TermCategory.STANDARD,
            "entropy": 0.85,
            "dispute_rate": 0.42,
            "explanation": "Highest effort standard with unclear requirements",
            "alternatives": [
                "commercially reasonable efforts",
                "efforts including [specific actions]",
            ],
        },
        "reasonable efforts": {
            "category": TermCategory.STANDARD,
            "entropy": 0.7,
            "dispute_rate": 0.30,
            "explanation": "Moderate effort standard, still subjective",
            "alternatives": ["efforts consistent with industry practice"],
        },
        "commercially reasonable": {
            "category": TermCategory.STANDARD,
            "entropy": 0.5,
            "dispute_rate": 0.18,
            "explanation": "Better defined but still has interpretation room",
            "alternatives": ["as defined in Section [X]"],
        },
        "good faith": {
            "category": TermCategory.STANDARD,
            "entropy": 0.55,
            "dispute_rate": 0.22,
            "explanation": "Behavioral standard open to interpretation",
            "alternatives": ["in accordance with the terms hereof"],
        },
        # Quantitative terms
        "material": {
            "category": TermCategory.QUANTITATIVE,
            "entropy": 0.75,
            "dispute_rate": 0.38,
            "explanation": "Undefined significance threshold",
            "alternatives": ["exceeding $[amount]", "affecting more than [X]%"],
        },
        "substantial": {
            "category": TermCategory.QUANTITATIVE,
            "entropy": 0.7,
            "dispute_rate": 0.32,
            "explanation": "Undefined quantity threshold",
            "alternatives": ["more than 25%", "exceeding [specific amount]"],
        },
        "significant": {
            "category": TermCategory.QUANTITATIVE,
            "entropy": 0.65,
            "dispute_rate": 0.28,
            "explanation": "Vague importance qualifier",
            "alternatives": ["material as defined in Section [X]"],
        },
        "de minimis": {
            "category": TermCategory.QUANTITATIVE,
            "entropy": 0.6,
            "dispute_rate": 0.25,
            "explanation": "Undefined minimal threshold",
            "alternatives": ["less than $[amount]", "under [X]%"],
        },
        # Scope terms
        "including but not limited to": {
            "category": TermCategory.SCOPE,
            "entropy": 0.8,
            "dispute_rate": 0.35,
            "explanation": "Open-ended scope creates uncertainty",
            "alternatives": ["including: [exhaustive list]", "specifically including"],
        },
        "and related": {
            "category": TermCategory.SCOPE,
            "entropy": 0.7,
            "dispute_rate": 0.30,
            "explanation": "Unclear relationship definition",
            "alternatives": ["as listed in Schedule [X]"],
        },
        "substantially similar": {
            "category": TermCategory.SCOPE,
            "entropy": 0.75,
            "dispute_rate": 0.33,
            "explanation": "Similarity threshold undefined",
            "alternatives": ["sharing [X]% of features", "as defined in Section [X]"],
        },
        "derivative": {
            "category": TermCategory.SCOPE,
            "entropy": 0.65,
            "dispute_rate": 0.28,
            "explanation": "Derivative work scope can be disputed",
            "alternatives": ["incorporating more than [X]% of the original"],
        },
        # Conditional terms
        "unless otherwise agreed": {
            "category": TermCategory.CONDITIONAL,
            "entropy": 0.5,
            "dispute_rate": 0.18,
            "explanation": "Creates uncertainty about actual terms",
            "alternatives": ["[remove if agreement is definitive]"],
        },
        "subject to": {
            "category": TermCategory.CONDITIONAL,
            "entropy": 0.45,
            "dispute_rate": 0.15,
            "explanation": "Dependency creates complexity",
            "alternatives": ["provided that [specific condition]"],
        },
        # Permissive terms
        "sole discretion": {
            "category": TermCategory.PERMISSIVE,
            "entropy": 0.7,
            "dispute_rate": 0.30,
            "explanation": "Unbounded decision authority",
            "alternatives": ["reasonable discretion", "discretion exercised in good faith"],
        },
        "may": {
            "category": TermCategory.PERMISSIVE,
            "entropy": 0.4,
            "dispute_rate": 0.12,
            "explanation": "Permissive language can create ambiguity about obligations",
            "alternatives": ["shall for obligations", "clarify as optional"],
        },
    }

    # Regex patterns for term detection
    TERM_PATTERNS = {
        TermCategory.TEMPORAL: [
            r"\b(within\s+)?a?\s*reasonable\s+(time|period)\b",
            r"\bpromptly\b",
            r"\btimely\b",
            r"\bas\s+soon\s+as\s+(reasonably\s+)?practicable\b",
            r"\bwithout\s+delay\b",
            r"\bforthwith\b",
        ],
        TermCategory.STANDARD: [
            r"\bbest\s+efforts?\b",
            r"\breasonable\s+efforts?\b",
            r"\bcommercially\s+reasonable\b",
            r"\bgood\s+faith\b",
            r"\bdue\s+diligence\b",
        ],
        TermCategory.QUANTITATIVE: [
            r"\bmaterial(ly)?\b",
            r"\bsubstantial(ly)?\b",
            r"\bsignificant(ly)?\b",
            r"\bde\s+minimis\b",
            r"\bnominal\b",
        ],
        TermCategory.SCOPE: [
            r"\bincluding,?\s*but\s+not\s+limited\s+to\b",
            r"\band\s+related\b",
            r"\bsubstantially\s+similar\b",
            r"\bderivative\b",
            r"\band\s+the\s+like\b",
        ],
    }

    def __init__(self):
        """Initialize the term analyzer."""
        self._term_history: Dict[str, List[Tuple[str, bool]]] = defaultdict(list)
        self._custom_terms: Dict[str, Dict[str, Any]] = {}

    def analyze_contract(
        self,
        clauses: List[str],
        contract_id: Optional[str] = None,
    ) -> TermReport:
        """
        Analyze all terms in a contract.

        Args:
            clauses: List of clause texts
            contract_id: Optional identifier

        Returns:
            TermReport with complete analysis
        """
        import secrets

        contract_id = contract_id or secrets.token_urlsafe(8)

        all_terms: List[TermAnalysis] = []
        all_text = " ".join(clauses)

        # Find all known high-risk terms
        for term, info in self.TERM_DATABASE.items():
            occurrences = self._find_occurrences(term, clauses)
            if occurrences:
                analysis = TermAnalysis(
                    term=term,
                    normalized_form=term.lower(),
                    category=info["category"],
                    risk_level=self._get_risk_level(info["entropy"], info["dispute_rate"]),
                    entropy_score=info["entropy"],
                    dispute_rate=info["dispute_rate"],
                    frequency=len(occurrences),
                    occurrences=occurrences,
                    alternatives=info.get("alternatives", []),
                    explanation=info["explanation"],
                )
                all_terms.append(analysis)

        # Find additional patterns
        for category, patterns in self.TERM_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, all_text, re.IGNORECASE)
                for match in matches:
                    term = match.group()
                    # Skip if already in database
                    if any(term.lower() == t.term.lower() for t in all_terms):
                        continue

                    # Create basic analysis for pattern match
                    occurrences = self._find_occurrences(term, clauses)
                    if occurrences:
                        analysis = TermAnalysis(
                            term=term,
                            normalized_form=term.lower(),
                            category=category,
                            risk_level=TermRiskLevel.MODERATE,
                            entropy_score=0.5,
                            dispute_rate=0.2,
                            frequency=len(occurrences),
                            occurrences=occurrences,
                            explanation=f"Pattern-matched term in {category.value} category",
                        )
                        all_terms.append(analysis)

        # Calculate statistics
        risk_dist = Counter(t.risk_level for t in all_terms)
        cat_dist = Counter(t.category for t in all_terms)
        total_entropy = sum(t.entropy_score * t.frequency for t in all_terms)
        total_freq = sum(t.frequency for t in all_terms)
        avg_entropy = total_entropy / total_freq if total_freq > 0 else 0

        high_risk_count = sum(
            1 for t in all_terms if t.risk_level in (TermRiskLevel.HIGH, TermRiskLevel.CRITICAL)
        )

        # Generate top concerns
        top_concerns = self._generate_concerns(all_terms)

        return TermReport(
            contract_id=contract_id,
            terms=sorted(all_terms, key=lambda t: (-t.entropy_score, -t.frequency)),
            high_risk_count=high_risk_count,
            total_entropy=total_entropy,
            avg_entropy=avg_entropy,
            risk_distribution=dict(risk_dist),
            category_distribution=dict(cat_dist),
            top_concerns=top_concerns,
        )

    def analyze_term(
        self,
        term: str,
        context: Optional[str] = None,
    ) -> TermAnalysis:
        """
        Analyze a single term.

        Args:
            term: Term to analyze
            context: Optional surrounding context

        Returns:
            TermAnalysis for the term
        """
        term_lower = term.lower()

        # Check database
        if term_lower in self.TERM_DATABASE:
            info = self.TERM_DATABASE[term_lower]
            return TermAnalysis(
                term=term,
                normalized_form=term_lower,
                category=info["category"],
                risk_level=self._get_risk_level(info["entropy"], info["dispute_rate"]),
                entropy_score=info["entropy"],
                dispute_rate=info["dispute_rate"],
                frequency=1,
                alternatives=info.get("alternatives", []),
                explanation=info["explanation"],
            )

        # Check custom terms
        if term_lower in self._custom_terms:
            info = self._custom_terms[term_lower]
            return TermAnalysis(
                term=term,
                normalized_form=term_lower,
                category=info.get("category", TermCategory.SCOPE),
                risk_level=self._get_risk_level(
                    info.get("entropy", 0.5),
                    info.get("dispute_rate", 0.2),
                ),
                entropy_score=info.get("entropy", 0.5),
                dispute_rate=info.get("dispute_rate", 0.2),
                frequency=1,
                alternatives=info.get("alternatives", []),
                explanation=info.get("explanation", "Custom term"),
            )

        # Classify unknown term
        category = self._classify_term(term, context)
        return TermAnalysis(
            term=term,
            normalized_form=term_lower,
            category=category,
            risk_level=TermRiskLevel.MODERATE,
            entropy_score=0.5,
            dispute_rate=0.2,
            frequency=1,
            explanation="Unknown term - requires manual review",
        )

    def get_high_entropy_terms(
        self,
        clauses: List[str],
        threshold: float = 0.6,
    ) -> List[TermAnalysis]:
        """
        Get only high-entropy terms from a contract.

        Args:
            clauses: Contract clauses
            threshold: Minimum entropy threshold

        Returns:
            List of high-entropy terms
        """
        report = self.analyze_contract(clauses)
        return [t for t in report.terms if t.entropy_score >= threshold]

    def suggest_alternatives(
        self,
        term: str,
    ) -> List[str]:
        """
        Get suggested alternatives for a term.

        Args:
            term: Term to find alternatives for

        Returns:
            List of alternative phrasings
        """
        term_lower = term.lower()

        if term_lower in self.TERM_DATABASE:
            return self.TERM_DATABASE[term_lower].get("alternatives", [])

        if term_lower in self._custom_terms:
            return self._custom_terms[term_lower].get("alternatives", [])

        return []

    def add_custom_term(
        self,
        term: str,
        category: TermCategory,
        entropy: float,
        dispute_rate: float,
        explanation: str = "",
        alternatives: Optional[List[str]] = None,
    ) -> None:
        """
        Add a custom term to the analyzer.

        Args:
            term: Term to add
            category: Term category
            entropy: Entropy score (0-1)
            dispute_rate: Historical dispute rate (0-1)
            explanation: Explanation of the risk
            alternatives: Suggested alternatives
        """
        self._custom_terms[term.lower()] = {
            "category": category,
            "entropy": entropy,
            "dispute_rate": dispute_rate,
            "explanation": explanation,
            "alternatives": alternatives or [],
        }

    def record_outcome(
        self,
        term: str,
        contract_id: str,
        disputed: bool,
    ) -> None:
        """
        Record whether a term led to a dispute.

        Used to update dispute rate estimates over time.

        Args:
            term: The term
            contract_id: Contract identifier
            disputed: Whether it led to a dispute
        """
        self._term_history[term.lower()].append((contract_id, disputed))

    def get_updated_dispute_rate(self, term: str) -> float:
        """
        Get updated dispute rate based on recorded outcomes.

        Args:
            term: Term to check

        Returns:
            Updated dispute rate
        """
        term_lower = term.lower()

        # Get historical base rate
        base_rate = 0.2
        if term_lower in self.TERM_DATABASE:
            base_rate = self.TERM_DATABASE[term_lower]["dispute_rate"]
        elif term_lower in self._custom_terms:
            base_rate = self._custom_terms[term_lower]["dispute_rate"]

        # Check recorded outcomes
        outcomes = self._term_history.get(term_lower, [])
        if len(outcomes) < 5:
            return base_rate  # Not enough data

        # Calculate observed rate with Bayesian update
        disputed_count = sum(1 for _, d in outcomes if d)
        observed_rate = disputed_count / len(outcomes)

        # Weighted average with prior
        weight = min(len(outcomes) / 50, 1.0)  # More data = more weight on observed
        return base_rate * (1 - weight) + observed_rate * weight

    def _find_occurrences(
        self,
        term: str,
        clauses: List[str],
    ) -> List[TermOccurrence]:
        """Find all occurrences of a term in clauses."""
        occurrences = []
        pattern = re.compile(re.escape(term), re.IGNORECASE)

        for i, clause in enumerate(clauses):
            for match in pattern.finditer(clause):
                # Extract context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(clause), match.end() + 50)
                context = clause[start:end]

                occurrences.append(
                    TermOccurrence(
                        term=match.group(),
                        position=match.start(),
                        clause_index=i,
                        context=context,
                        normalized=term.lower(),
                    )
                )

        return occurrences

    def _get_risk_level(self, entropy: float, dispute_rate: float) -> TermRiskLevel:
        """Determine risk level from entropy and dispute rate."""
        combined = entropy * 0.6 + dispute_rate * 0.4

        if combined >= 0.7:
            return TermRiskLevel.CRITICAL
        elif combined >= 0.5:
            return TermRiskLevel.HIGH
        elif combined >= 0.3:
            return TermRiskLevel.MODERATE
        else:
            return TermRiskLevel.SAFE

    def _classify_term(self, term: str, context: Optional[str]) -> TermCategory:
        """Classify an unknown term into a category."""
        term_lower = term.lower()
        context_lower = (context or "").lower()

        # Check for temporal indicators
        if any(w in term_lower or w in context_lower for w in ["time", "day", "period", "date"]):
            return TermCategory.TEMPORAL

        # Check for quantity indicators
        if any(
            w in term_lower or w in context_lower
            for w in ["amount", "number", "percent", "quantity"]
        ):
            return TermCategory.QUANTITATIVE

        # Check for obligation indicators
        if any(w in term_lower for w in ["shall", "must", "require", "oblig"]):
            return TermCategory.OBLIGATORY

        # Check for permission indicators
        if any(w in term_lower for w in ["may", "can", "option", "right"]):
            return TermCategory.PERMISSIVE

        # Default to scope
        return TermCategory.SCOPE

    def _generate_concerns(self, terms: List[TermAnalysis]) -> List[str]:
        """Generate top concerns from term analysis."""
        concerns = []

        # Count high-risk terms by category
        cat_risk = defaultdict(int)
        for t in terms:
            if t.risk_level in (TermRiskLevel.HIGH, TermRiskLevel.CRITICAL):
                cat_risk[t.category] += t.frequency

        # Generate concern messages
        for cat, count in sorted(cat_risk.items(), key=lambda x: -x[1]):
            if cat == TermCategory.TEMPORAL:
                concerns.append(f"{count} vague timing terms that should be quantified")
            elif cat == TermCategory.STANDARD:
                concerns.append(f"{count} ambiguous effort standards that need definition")
            elif cat == TermCategory.QUANTITATIVE:
                concerns.append(f"{count} undefined thresholds that need specific values")
            elif cat == TermCategory.SCOPE:
                concerns.append(f"{count} open-ended scope terms that create uncertainty")

        # Add general concerns
        critical_terms = [t for t in terms if t.risk_level == TermRiskLevel.CRITICAL]
        if critical_terms:
            concerns.insert(
                0, f"{len(critical_terms)} critical-risk terms require immediate attention"
            )

        return concerns[:5]


# Convenience function
def find_high_entropy_terms(clauses: List[str]) -> List[TermAnalysis]:
    """
    Find high-entropy terms in contract clauses.

    Args:
        clauses: List of clause texts

    Returns:
        List of high-entropy terms
    """
    analyzer = TermAnalyzer()
    return analyzer.get_high_entropy_terms(clauses)
