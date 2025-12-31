# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Predictive Dispute Warning System.

Generates real-time warnings for high-risk contract terms:
- Identifies dispute-prone language patterns
- Calculates dispute probability scores
- Suggests specific mitigations
- Tracks warning history for learning

Integrates with the License Entropy Oracle and Clause Hardener
to provide actionable guidance during contract negotiation.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .dispute_model import DisputePredictor, DisputePrediction, DisputeType, PredictionFeatures


class WarningSeverity(Enum):
    """Severity levels for dispute warnings.

    Ordered from highest to lowest severity (index 0 = most severe).
    """

    CRITICAL = "critical"   # Critical risk, do not proceed without addressing
    HIGH = "high"           # High risk, action required
    MEDIUM = "medium"       # Moderate risk, action recommended
    LOW = "low"             # Minor risk, consider reviewing
    INFO = "info"           # Informational, no immediate action needed


class WarningCategory(Enum):
    """Categories of dispute warnings."""

    AMBIGUITY = "ambiguity"           # Ambiguous language
    MISSING_CLAUSE = "missing_clause"  # Required clause missing
    HIGH_ENTROPY = "high_entropy"      # High entropy score
    PATTERN_MATCH = "pattern_match"    # Matches historical dispute pattern
    IMBALANCE = "imbalance"           # Unfair/imbalanced terms
    COMPLEXITY = "complexity"          # Excessive complexity
    CONTRADICTION = "contradiction"    # Contradictory terms
    UNDEFINED = "undefined"           # Undefined terms/references


@dataclass
class Mitigation:
    """A suggested mitigation for a warning."""

    id: str
    description: str
    action: str                       # Specific action to take
    impact: float                     # Estimated risk reduction (0-1)
    effort: str                       # "low", "medium", "high"
    template_id: Optional[str] = None  # Reference to hardened template
    example: Optional[str] = None      # Example of mitigated language


@dataclass
class DisputeWarning:
    """A warning about potential dispute risk."""

    id: str
    severity: WarningSeverity
    category: WarningCategory
    title: str
    description: str
    location: str                     # Where in the contract (clause number/text)
    matched_text: Optional[str]       # The problematic text
    dispute_probability: float        # Probability this leads to dispute
    dispute_types: List[DisputeType]  # Types of disputes this could cause
    mitigations: List[Mitigation]     # Suggested fixes
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "matched_text": self.matched_text,
            "dispute_probability": round(self.dispute_probability, 4),
            "dispute_types": [dt.value for dt in self.dispute_types],
            "mitigations": [
                {
                    "id": m.id,
                    "description": m.description,
                    "action": m.action,
                    "impact": round(m.impact, 3),
                    "effort": m.effort,
                    "template_id": m.template_id,
                    "example": m.example,
                }
                for m in self.mitigations
            ],
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
        }


@dataclass
class WarningReport:
    """Complete warning report for a contract."""

    contract_id: str
    warnings: List[DisputeWarning]
    overall_risk_score: float         # 0-1, aggregate risk
    dispute_probability: float        # Overall dispute probability
    prediction: DisputePrediction
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        """Count of critical warnings."""
        return sum(1 for w in self.warnings if w.severity == WarningSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        """Count of high severity warnings."""
        return sum(1 for w in self.warnings if w.severity == WarningSeverity.HIGH)

    @property
    def total_count(self) -> int:
        """Total warning count."""
        return len(self.warnings)

    @property
    def unresolved_count(self) -> int:
        """Count of unresolved warnings."""
        return sum(1 for w in self.warnings if not w.resolved)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "contract_id": self.contract_id,
            "overall_risk_score": round(self.overall_risk_score, 4),
            "dispute_probability": round(self.dispute_probability, 4),
            "summary": {
                "total": self.total_count,
                "critical": self.critical_count,
                "high": self.high_count,
                "unresolved": self.unresolved_count,
            },
            "warnings": [w.to_dict() for w in self.warnings],
            "prediction": self.prediction.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }


class DisputeWarningGenerator:
    """
    Generates predictive dispute warnings for contracts.

    Analyzes contract clauses in real-time to identify potential
    dispute risks and suggest mitigations before problems occur.
    """

    # Severity thresholds (ordered from highest to lowest)
    SEVERITY_THRESHOLDS = [
        (WarningSeverity.CRITICAL, 0.8),
        (WarningSeverity.HIGH, 0.6),
        (WarningSeverity.MEDIUM, 0.4),
        (WarningSeverity.LOW, 0.2),
        (WarningSeverity.INFO, 0.0),
    ]

    # Ambiguous terms and their risk weights
    AMBIGUOUS_TERMS = {
        "reasonable": {
            "weight": 0.7,
            "description": "Subjective standard open to interpretation",
            "mitigation": "Replace with specific, measurable criteria",
            "example": "'within 30 calendar days' instead of 'within a reasonable time'",
        },
        "material": {
            "weight": 0.6,
            "description": "Undefined threshold for significance",
            "mitigation": "Define specific threshold (e.g., dollar amount, percentage)",
            "example": "'breach resulting in damages exceeding $10,000' instead of 'material breach'",
        },
        "best efforts": {
            "weight": 0.65,
            "description": "Vague effort standard with no clear measure",
            "mitigation": "Define specific actions that constitute compliance",
            "example": "'commercially reasonable efforts including [specific actions]'",
        },
        "promptly": {
            "weight": 0.5,
            "description": "Undefined timing that often leads to disputes",
            "mitigation": "Specify exact timeframe",
            "example": "'within 5 business days' instead of 'promptly'",
        },
        "substantial": {
            "weight": 0.55,
            "description": "Undefined magnitude threshold",
            "mitigation": "Quantify with specific amounts or percentages",
            "example": "'more than 25% of the contract value'",
        },
        "including but not limited to": {
            "weight": 0.6,
            "description": "Open-ended list creates scope ambiguity",
            "mitigation": "Use closed enumeration or explicit scope",
            "example": "Enumerate all items explicitly",
            "pattern": r"\binclud(?:e|es|ing),?\s*but\s*(?:is\s+|are\s+)?not\s*limited\s*to\b",
        },
        "sole discretion": {
            "weight": 0.5,
            "description": "Unbounded decision-making authority",
            "mitigation": "Add 'reasonable' or 'good faith' qualifiers",
            "example": "'in its reasonable discretion, exercised in good faith'",
        },
        "may": {
            "weight": 0.3,
            "description": "Permissive language creating uncertainty",
            "mitigation": "Clarify whether this creates an obligation",
            "example": "Use 'shall' for obligations, 'may' only for true options",
        },
    }

    # Required clauses by license type
    REQUIRED_CLAUSES = {
        "commercial": [
            ("dispute_resolution", "Dispute Resolution", 0.7),
            ("liability_limitation", "Liability Limitation", 0.6),
            ("termination", "Termination Rights", 0.5),
            ("warranty", "Warranty/Disclaimer", 0.4),
            ("indemnification", "Indemnification", 0.4),
        ],
        "saas": [
            ("dispute_resolution", "Dispute Resolution", 0.7),
            ("liability_limitation", "Liability Limitation", 0.6),
            ("sla", "Service Level Agreement", 0.6),
            ("data_protection", "Data Protection", 0.5),
            ("termination", "Termination Rights", 0.5),
        ],
        "open_source": [
            ("attribution", "Attribution Requirements", 0.4),
            ("warranty_disclaimer", "Warranty Disclaimer", 0.5),
            ("patent_grant", "Patent Grant/Exclusion", 0.4),
        ],
    }

    # Historical dispute patterns
    DISPUTE_PATTERNS = [
        {
            "pattern": r"intellectual property.*(?:created|developed).*(?:during|under)",
            "category": WarningCategory.PATTERN_MATCH,
            "title": "IP Ownership Ambiguity",
            "description": "Work product ownership disputes are common when creation context is unclear",
            "dispute_types": [DisputeType.IP_OWNERSHIP],
            "weight": 0.7,
        },
        {
            "pattern": r"terminat.*(?:convenience|any reason|without cause)",
            "category": WarningCategory.IMBALANCE,
            "title": "Unilateral Termination Risk",
            "description": "One-sided termination rights often lead to disputes",
            "dispute_types": [DisputeType.TERMINATION],
            "weight": 0.5,
        },
        {
            "pattern": r"(?:all|any|entire).*(?:liability|damages).*(?:excluded|waived)",
            "category": WarningCategory.IMBALANCE,
            "title": "Excessive Liability Exclusion",
            "description": "Broad liability waivers may be unenforceable and cause disputes",
            "dispute_types": [DisputeType.INDEMNIFICATION],
            "weight": 0.6,
        },
        {
            "pattern": r"(?:perpetual|irrevocable|forever).*(?:license|right|grant)",
            "category": WarningCategory.PATTERN_MATCH,
            "title": "Perpetual Rights Grant",
            "description": "Perpetual grants often disputed when relationships deteriorate",
            "dispute_types": [DisputeType.SCOPE],
            "weight": 0.45,
        },
    ]

    def __init__(
        self,
        predictor: Optional[DisputePredictor] = None,
        pattern_analyzer: Optional[Any] = None,
    ):
        """
        Initialize the warning generator.

        Args:
            predictor: DisputePredictor instance
            pattern_analyzer: ClausePatternAnalyzer instance
        """
        self.predictor = predictor or DisputePredictor()
        self.pattern_analyzer = pattern_analyzer

        # Warning history for learning
        self._warning_history: Dict[str, DisputeWarning] = {}

    def generate_warnings(
        self,
        clauses: List[str],
        contract_id: Optional[str] = None,
        license_type: str = "commercial",
        context: Optional[Dict[str, Any]] = None,
    ) -> WarningReport:
        """
        Generate dispute warnings for a contract.

        Args:
            clauses: List of clause texts
            contract_id: Optional contract identifier
            license_type: Type of license (commercial, saas, open_source)
            context: Additional context (party history, etc.)

        Returns:
            WarningReport with all warnings
        """
        contract_id = contract_id or secrets.token_urlsafe(8)
        context = context or {}
        warnings: List[DisputeWarning] = []

        # Get dispute prediction first
        prediction = self.predictor.predict(
            clauses,
            licensee_history=context.get("licensee_prior_disputes", 0),
            licensor_history=context.get("licensor_prior_disputes", 0),
        )

        # Analyze each clause
        for i, clause in enumerate(clauses):
            clause_warnings = self._analyze_clause(clause, i + 1, prediction)
            warnings.extend(clause_warnings)

        # Check for missing required clauses
        missing_warnings = self._check_missing_clauses(clauses, license_type)
        warnings.extend(missing_warnings)

        # Check for pattern matches
        pattern_warnings = self._check_patterns(clauses)
        warnings.extend(pattern_warnings)

        # Add prediction-based warnings
        prediction_warnings = self._generate_prediction_warnings(prediction)
        warnings.extend(prediction_warnings)

        # Calculate overall risk score
        overall_risk = self._calculate_overall_risk(warnings, prediction)

        # Store warnings in history
        for warning in warnings:
            self._warning_history[warning.id] = warning

        return WarningReport(
            contract_id=contract_id,
            warnings=sorted(warnings, key=lambda w: (
                list(WarningSeverity).index(w.severity),
                -w.dispute_probability,
            )),
            overall_risk_score=overall_risk,
            dispute_probability=prediction.dispute_probability,
            prediction=prediction,
        )

    def _analyze_clause(
        self,
        clause: str,
        clause_num: int,
        prediction: DisputePrediction,
    ) -> List[DisputeWarning]:
        """Analyze a single clause for warnings."""
        import re
        warnings = []
        clause_lower = clause.lower()

        # Check for ambiguous terms
        for term, info in self.AMBIGUOUS_TERMS.items():
            # Use regex pattern if provided, otherwise simple string match
            pattern = info.get("pattern")
            if pattern:
                match = re.search(pattern, clause_lower, re.IGNORECASE)
                found = match is not None
                if found:
                    pos = match.start()
                    matched_len = len(match.group())
                else:
                    pos = -1
                    matched_len = len(term)
            else:
                found = term in clause_lower
                pos = clause_lower.find(term) if found else -1
                matched_len = len(term)

            if found:
                # Find position for context
                start = max(0, pos - 30)
                end = min(len(clause), pos + matched_len + 30)
                matched_text = clause[start:end]

                severity = self._get_severity(info["weight"])

                warning = DisputeWarning(
                    id=self._generate_warning_id(clause_num, term),
                    severity=severity,
                    category=WarningCategory.AMBIGUITY,
                    title=f"Ambiguous Term: '{term}'",
                    description=info["description"],
                    location=f"Clause {clause_num}",
                    matched_text=matched_text,
                    dispute_probability=info["weight"] * prediction.dispute_probability,
                    dispute_types=[DisputeType.SCOPE, DisputeType.BREACH],
                    mitigations=[
                        Mitigation(
                            id=f"mit_{term.replace(' ', '_')}",
                            description=info["mitigation"],
                            action=f"Replace '{term}' with specific language",
                            impact=info["weight"] * 0.6,
                            effort="low",
                            example=info.get("example"),
                        )
                    ],
                )
                warnings.append(warning)

        # Check for high complexity
        word_count = len(clause.split())
        if word_count > 200:
            warnings.append(DisputeWarning(
                id=self._generate_warning_id(clause_num, "complexity"),
                severity=WarningSeverity.MEDIUM,
                category=WarningCategory.COMPLEXITY,
                title="Excessive Clause Length",
                description=f"Clause has {word_count} words, making it difficult to understand",
                location=f"Clause {clause_num}",
                matched_text=None,
                dispute_probability=0.3,
                dispute_types=[DisputeType.SCOPE],
                mitigations=[
                    Mitigation(
                        id="mit_split_clause",
                        description="Break into multiple focused clauses",
                        action="Split this clause into 2-3 shorter clauses",
                        impact=0.2,
                        effort="medium",
                    )
                ],
            ))

        # Check for undefined references
        undefined_refs = re.findall(r'Section\s+\[?\d*[A-Z]?\]?|Schedule\s+\[?[A-Z]?\]?|Exhibit\s+\[?[A-Z]?\]?', clause)
        for ref in undefined_refs:
            if '[' in ref:
                warnings.append(DisputeWarning(
                    id=self._generate_warning_id(clause_num, f"undef_{ref}"),
                    severity=WarningSeverity.HIGH,
                    category=WarningCategory.UNDEFINED,
                    title="Undefined Reference",
                    description=f"Reference '{ref}' appears to be a placeholder",
                    location=f"Clause {clause_num}",
                    matched_text=ref,
                    dispute_probability=0.5,
                    dispute_types=[DisputeType.SCOPE],
                    mitigations=[
                        Mitigation(
                            id="mit_define_ref",
                            description="Complete the reference",
                            action=f"Replace '{ref}' with actual section/schedule number",
                            impact=0.5,
                            effort="low",
                        )
                    ],
                ))

        return warnings

    def _check_missing_clauses(
        self,
        clauses: List[str],
        license_type: str,
    ) -> List[DisputeWarning]:
        """Check for missing required clauses."""
        warnings = []
        all_text = " ".join(clauses).lower()

        required = self.REQUIRED_CLAUSES.get(license_type, self.REQUIRED_CLAUSES["commercial"])

        clause_indicators = {
            "dispute_resolution": ["arbitration", "mediation", "dispute resolution", "jurisdiction"],
            "liability_limitation": ["limitation of liability", "limit liability", "cap on liability"],
            "termination": ["termination", "terminate", "cancellation"],
            "warranty": ["warranty", "disclaim", "as is", "as-is"],
            "indemnification": ["indemnif", "hold harmless"],
            "sla": ["service level", "uptime", "availability"],
            "data_protection": ["data protection", "privacy", "gdpr", "personal data"],
            "attribution": ["attribution", "credit", "notice", "acknowledge"],
            "warranty_disclaimer": ["warranty", "disclaim", "as is"],
            "patent_grant": ["patent", "patent license"],
        }

        for clause_id, clause_name, weight in required:
            indicators = clause_indicators.get(clause_id, [])
            found = any(ind in all_text for ind in indicators)

            if not found:
                severity = self._get_severity(weight)
                warnings.append(DisputeWarning(
                    id=self._generate_warning_id(0, f"missing_{clause_id}"),
                    severity=severity,
                    category=WarningCategory.MISSING_CLAUSE,
                    title=f"Missing: {clause_name}",
                    description=f"No {clause_name} clause detected in the contract",
                    location="Contract-wide",
                    matched_text=None,
                    dispute_probability=weight,
                    dispute_types=self._get_dispute_types_for_clause(clause_id),
                    mitigations=[
                        Mitigation(
                            id=f"mit_add_{clause_id}",
                            description=f"Add a {clause_name} clause",
                            action=f"Include a standard {clause_name} provision",
                            impact=weight * 0.7,
                            effort="medium",
                            template_id=f"template_{clause_id}",
                        )
                    ],
                ))

        return warnings

    def _check_patterns(self, clauses: List[str]) -> List[DisputeWarning]:
        """Check for historical dispute patterns."""
        import re
        warnings = []
        all_text = " ".join(clauses)

        for pattern_info in self.DISPUTE_PATTERNS:
            matches = re.findall(pattern_info["pattern"], all_text, re.IGNORECASE)
            if matches:
                severity = self._get_severity(pattern_info["weight"])
                warnings.append(DisputeWarning(
                    id=self._generate_warning_id(0, f"pattern_{pattern_info['title'][:10]}"),
                    severity=severity,
                    category=pattern_info["category"],
                    title=pattern_info["title"],
                    description=pattern_info["description"],
                    location="Pattern detected",
                    matched_text=matches[0] if matches else None,
                    dispute_probability=pattern_info["weight"],
                    dispute_types=pattern_info["dispute_types"],
                    mitigations=[
                        Mitigation(
                            id=f"mit_pattern_{pattern_info['title'][:10]}",
                            description="Review and clarify this language",
                            action="Consider revising to reduce dispute risk",
                            impact=pattern_info["weight"] * 0.5,
                            effort="medium",
                        )
                    ],
                ))

        return warnings

    def _generate_prediction_warnings(
        self,
        prediction: DisputePrediction,
    ) -> List[DisputeWarning]:
        """Generate warnings from prediction results."""
        warnings = []

        # High overall probability warning
        if prediction.dispute_probability > 0.5:
            severity = self._get_severity(prediction.dispute_probability)
            warnings.append(DisputeWarning(
                id=self._generate_warning_id(0, "high_overall_risk"),
                severity=severity,
                category=WarningCategory.HIGH_ENTROPY,
                title="High Overall Dispute Risk",
                description=f"Contract has {prediction.dispute_probability:.0%} probability of dispute",
                location="Contract-wide",
                matched_text=None,
                dispute_probability=prediction.dispute_probability,
                dispute_types=list(prediction.type_probabilities.keys())[:3],
                mitigations=[
                    Mitigation(
                        id="mit_professional_review",
                        description="Seek professional legal review",
                        action="Have the contract reviewed by legal counsel",
                        impact=0.3,
                        effort="high",
                    ),
                    Mitigation(
                        id="mit_use_hardened",
                        description="Use hardened clause templates",
                        action="Replace high-risk clauses with pre-vetted templates",
                        impact=0.4,
                        effort="medium",
                    ),
                ],
            ))

        # Warnings from risk factors
        for factor, weight in prediction.top_risk_factors[:3]:
            if weight > 0.4:
                warnings.append(DisputeWarning(
                    id=self._generate_warning_id(0, f"risk_{factor[:15]}"),
                    severity=self._get_severity(weight),
                    category=WarningCategory.HIGH_ENTROPY,
                    title=f"Risk Factor: {factor}",
                    description=f"This factor contributes significantly to dispute risk",
                    location="Model prediction",
                    matched_text=None,
                    dispute_probability=weight,
                    dispute_types=[DisputeType.SCOPE],
                    mitigations=[
                        Mitigation(
                            id=f"mit_risk_{factor[:10]}",
                            description="Address this risk factor",
                            action=self._get_action_for_factor(factor),
                            impact=weight * 0.5,
                            effort="medium",
                        )
                    ],
                ))

        return warnings

    def _get_severity(self, probability: float) -> WarningSeverity:
        """Get severity level from probability."""
        for severity, threshold in self.SEVERITY_THRESHOLDS:
            if probability >= threshold:
                return severity
        return WarningSeverity.INFO

    def _generate_warning_id(self, clause_num: int, context: str) -> str:
        """Generate unique warning ID."""
        hash_input = f"{clause_num}:{context}:{datetime.now().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    def _get_dispute_types_for_clause(self, clause_id: str) -> List[DisputeType]:
        """Get relevant dispute types for a missing clause."""
        mapping = {
            "dispute_resolution": [DisputeType.SCOPE, DisputeType.BREACH],
            "liability_limitation": [DisputeType.INDEMNIFICATION],
            "termination": [DisputeType.TERMINATION],
            "warranty": [DisputeType.PERFORMANCE],
            "indemnification": [DisputeType.INDEMNIFICATION],
            "sla": [DisputeType.PERFORMANCE],
            "data_protection": [DisputeType.CONFIDENTIALITY],
            "attribution": [DisputeType.SCOPE],
        }
        return mapping.get(clause_id, [DisputeType.SCOPE])

    def _get_action_for_factor(self, factor: str) -> str:
        """Get recommended action for a risk factor."""
        factor_lower = factor.lower()

        if "entropy" in factor_lower:
            return "Review high-entropy clauses and use hardened alternatives"
        elif "ambiguous" in factor_lower:
            return "Replace ambiguous terms with specific language"
        elif "dispute resolution" in factor_lower:
            return "Add explicit dispute resolution mechanism"
        elif "liability" in factor_lower:
            return "Include balanced liability limitation"
        elif "prior disputes" in factor_lower:
            return "Consider additional protective clauses given dispute history"
        else:
            return "Review and address this risk factor"

    def _calculate_overall_risk(
        self,
        warnings: List[DisputeWarning],
        prediction: DisputePrediction,
    ) -> float:
        """Calculate overall risk score from warnings and prediction."""
        if not warnings:
            return prediction.dispute_probability

        # Weight by severity
        severity_weights = {
            WarningSeverity.CRITICAL: 1.0,
            WarningSeverity.HIGH: 0.8,
            WarningSeverity.MEDIUM: 0.5,
            WarningSeverity.LOW: 0.2,
            WarningSeverity.INFO: 0.1,
        }

        warning_risk = sum(
            w.dispute_probability * severity_weights[w.severity]
            for w in warnings
        ) / max(len(warnings), 1)

        # Combine with prediction
        overall = (prediction.dispute_probability * 0.6 + warning_risk * 0.4)

        return min(overall, 1.0)

    def acknowledge_warning(self, warning_id: str) -> bool:
        """Acknowledge a warning."""
        if warning_id in self._warning_history:
            self._warning_history[warning_id].acknowledged = True
            return True
        return False

    def resolve_warning(self, warning_id: str) -> bool:
        """Mark a warning as resolved."""
        if warning_id in self._warning_history:
            self._warning_history[warning_id].resolved = True
            return True
        return False

    def get_warning(self, warning_id: str) -> Optional[DisputeWarning]:
        """Get a warning by ID."""
        return self._warning_history.get(warning_id)


# Convenience function
def generate_dispute_warnings(
    clauses: List[str],
    license_type: str = "commercial",
) -> WarningReport:
    """
    Generate dispute warnings for contract clauses.

    Args:
        clauses: List of clause texts
        license_type: Type of license

    Returns:
        WarningReport with all warnings
    """
    generator = DisputeWarningGenerator()
    return generator.generate_warnings(clauses, license_type=license_type)
