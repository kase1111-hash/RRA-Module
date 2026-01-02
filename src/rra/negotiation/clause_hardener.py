# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
AI-Powered Clause Hardening Module.

Automatically improves license clauses to reduce dispute risk:
1. Identifies ambiguous language
2. Suggests specific, measurable alternatives
3. Applies hardening rules based on historical dispute data
4. Validates improvements maintain legal intent

Uses pattern analysis and rule-based transformations with
optional LLM enhancement for complex clauses.
"""

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

from ..analytics.clause_patterns import (
    ClausePatternAnalyzer,
    ClauseCategory,
    ClausePattern,
)


class HardeningLevel(Enum):
    """Level of hardening to apply."""

    MINIMAL = "minimal"  # Only fix critical ambiguities
    MODERATE = "moderate"  # Fix common dispute triggers
    AGGRESSIVE = "aggressive"  # Full hardening, may change meaning


class HardeningStrategy(Enum):
    """Strategies for hardening clauses."""

    QUANTIFY = "quantify"  # Add specific numbers/timeframes
    DEFINE = "define"  # Add definitions for ambiguous terms
    ENUMERATE = "enumerate"  # Replace open lists with closed lists
    REFERENCE = "reference"  # Add external references/standards
    PROCEDURALIZE = "proceduralize"  # Add specific procedures
    BOUND = "bound"  # Add upper/lower bounds


@dataclass
class HardeningRule:
    """A rule for hardening a specific pattern."""

    id: str
    name: str
    pattern: str  # Regex pattern to match
    strategy: HardeningStrategy
    replacement_template: str  # Template with {placeholders}
    default_values: Dict[str, str] = field(default_factory=dict)
    priority: int = 0  # Higher = apply first
    categories: List[ClauseCategory] = field(default_factory=list)
    risk_reduction: float = 0.0  # Estimated dispute risk reduction

    def apply(self, text: str, values: Optional[Dict[str, str]] = None) -> str:
        """Apply this rule to text."""
        merged_values = {**self.default_values, **(values or {})}
        replacement = self.replacement_template.format(**merged_values)
        return re.sub(self.pattern, replacement, text, flags=re.IGNORECASE)


@dataclass
class HardeningResult:
    """Result of hardening a clause."""

    original: str
    hardened: str
    changes: List[Dict[str, Any]]
    risk_before: float
    risk_after: float
    rules_applied: List[str]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def risk_reduction(self) -> float:
        """Calculate risk reduction percentage."""
        if self.risk_before == 0:
            return 0.0
        return (self.risk_before - self.risk_after) / self.risk_before * 100

    @property
    def was_modified(self) -> bool:
        """Check if the clause was modified."""
        return self.original != self.hardened


@dataclass
class HardeningSession:
    """A session for interactive clause hardening."""

    id: str
    original_clauses: List[str]
    hardened_clauses: List[str] = field(default_factory=list)
    results: List[HardeningResult] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed: bool = False
    user_overrides: Dict[int, str] = field(default_factory=dict)


class ClauseHardener:
    """
    AI-powered clause hardening engine.

    Analyzes license clauses and suggests improvements to reduce
    ambiguity and dispute risk. Uses a combination of:

    1. Pattern-based rules for common issues
    2. Historical dispute data for risk assessment
    3. Template library for hardened alternatives
    4. Optional LLM enhancement for complex cases
    """

    # Core hardening rules
    DEFAULT_RULES: List[HardeningRule] = [
        # Time-related ambiguities
        HardeningRule(
            id="time_reasonable",
            name="Reasonable Time → Specific Days",
            pattern=r"\b(within a )?reasonable (time|period)\b",
            strategy=HardeningStrategy.QUANTIFY,
            replacement_template="within {days} calendar days",
            default_values={"days": "30"},
            priority=10,
            risk_reduction=0.35,
        ),
        HardeningRule(
            id="time_promptly",
            name="Promptly → Specific Days",
            pattern=r"\bpromptly\b",
            strategy=HardeningStrategy.QUANTIFY,
            replacement_template="within {days} business days",
            default_values={"days": "5"},
            priority=10,
            risk_reduction=0.30,
        ),
        HardeningRule(
            id="time_timely",
            name="Timely → Specific Days",
            pattern=r"\b(in a )?timely (manner|fashion)\b",
            strategy=HardeningStrategy.QUANTIFY,
            replacement_template="within {days} calendar days",
            default_values={"days": "14"},
            priority=10,
            risk_reduction=0.25,
        ),
        HardeningRule(
            id="time_soon",
            name="As Soon As Practicable → Specific",
            pattern=r"\bas soon as (reasonably )?practicable\b",
            strategy=HardeningStrategy.QUANTIFY,
            replacement_template="within {days} business days, or if impracticable, with written notice explaining the delay",
            default_values={"days": "10"},
            priority=10,
            risk_reduction=0.40,
        ),
        # Effort-related ambiguities
        HardeningRule(
            id="effort_best",
            name="Best Efforts → Commercially Reasonable",
            pattern=r"\bbest efforts?\b",
            strategy=HardeningStrategy.DEFINE,
            replacement_template="commercially reasonable efforts (meaning efforts consistent with industry standard practices, {specifics})",
            default_values={"specifics": "without requiring expenditure of more than {amount}"},
            priority=8,
            risk_reduction=0.45,
        ),
        HardeningRule(
            id="effort_reasonable",
            name="Reasonable Efforts Definition",
            pattern=r"\breasonable efforts?\b(?!\s*\()",
            strategy=HardeningStrategy.DEFINE,
            replacement_template="reasonable efforts (as defined in Section {section})",
            default_values={"section": "1.X"},
            priority=7,
            risk_reduction=0.30,
        ),
        # Scope ambiguities
        HardeningRule(
            id="scope_including",
            name="Including But Not Limited To → Enumerated",
            pattern=r"\binclud(?:e|es|ing),?\s*but\s*(?:are\s+)?not\s*limited\s*to,?\b",
            strategy=HardeningStrategy.ENUMERATE,
            replacement_template="including the following: {items}, and no other items unless mutually agreed in writing",
            default_values={"items": "[enumerate specific items]"},
            priority=9,
            risk_reduction=0.50,
        ),
        HardeningRule(
            id="scope_related",
            name="And Related → Specifically Defined",
            pattern=r"\band\s+related\s+(services?|materials?|works?|items?)\b",
            strategy=HardeningStrategy.DEFINE,
            replacement_template="and {type} specifically listed in Schedule {schedule}",
            default_values={"type": "related items", "schedule": "A"},
            priority=8,
            risk_reduction=0.40,
        ),
        HardeningRule(
            id="scope_derivative",
            name="Derivative Works Definition",
            pattern=r"\bderivative\s+works?\b(?!\s*\()",
            strategy=HardeningStrategy.DEFINE,
            replacement_template="derivative works (meaning works that {definition})",
            default_values={
                "definition": "incorporate more than 10% of the original code by line count or functionality"
            },
            priority=7,
            risk_reduction=0.35,
        ),
        # Materiality thresholds
        HardeningRule(
            id="material_breach",
            name="Material Breach → Defined Threshold",
            pattern=r"\bmaterial\s+breach\b(?!\s*\()",
            strategy=HardeningStrategy.BOUND,
            replacement_template="material breach (meaning a breach that {threshold})",
            default_values={
                "threshold": "results in damages exceeding ${amount} or prevents the non-breaching party from receiving the substantial benefit of this Agreement"
            },
            priority=9,
            risk_reduction=0.55,
        ),
        HardeningRule(
            id="material_change",
            name="Material Change → Percentage Bound",
            pattern=r"\bmaterial\s+change\b(?!\s*\()",
            strategy=HardeningStrategy.BOUND,
            replacement_template="material change (meaning a change that affects more than {percentage}% of {scope})",
            default_values={"percentage": "20", "scope": "the functionality or value"},
            priority=8,
            risk_reduction=0.40,
        ),
        # Notice requirements
        HardeningRule(
            id="notice_reasonable",
            name="Reasonable Notice → Specific Period",
            pattern=r"\b(with\s+)?reasonable\s+(prior\s+)?notice\b",
            strategy=HardeningStrategy.QUANTIFY,
            replacement_template="with at least {days} days' prior written notice delivered to {address}",
            default_values={"days": "30", "address": "the address specified in Section [X]"},
            priority=10,
            risk_reduction=0.45,
        ),
        HardeningRule(
            id="notice_written",
            name="Written Notice Method",
            pattern=r"\bwritten\s+notice\b(?!\s*(sent|delivered|via))",
            strategy=HardeningStrategy.PROCEDURALIZE,
            replacement_template="written notice sent via {method}",
            default_values={
                "method": "registered mail, courier with tracking, or email with read receipt confirmation"
            },
            priority=6,
            risk_reduction=0.25,
        ),
        # Financial terms
        HardeningRule(
            id="fin_fair_market",
            name="Fair Market Value → Valuation Method",
            pattern=r"\bfair\s+market\s+value\b(?!\s*(as\s+determined|calculated))",
            strategy=HardeningStrategy.PROCEDURALIZE,
            replacement_template="fair market value as determined by {method}",
            default_values={
                "method": "an independent third-party appraiser mutually agreed upon by the parties, or if no agreement within 10 days, appointed by [arbitration body]"
            },
            priority=9,
            risk_reduction=0.50,
        ),
        HardeningRule(
            id="fin_reasonable_comp",
            name="Reasonable Compensation → Formula",
            pattern=r"\breasonable\s+compensation\b",
            strategy=HardeningStrategy.QUANTIFY,
            replacement_template="compensation calculated as {formula}",
            default_values={
                "formula": "[base rate] multiplied by [usage metric] as specified in Schedule B"
            },
            priority=8,
            risk_reduction=0.45,
        ),
        # Subjective standards
        HardeningRule(
            id="subj_satisfaction",
            name="To Satisfaction → Objective Standard",
            pattern=r"\bto\s+(the\s+)?(reasonable\s+)?satisfaction\s+of\b",
            strategy=HardeningStrategy.REFERENCE,
            replacement_template="meeting the acceptance criteria specified in {reference}",
            default_values={"reference": "Schedule C"},
            priority=7,
            risk_reduction=0.40,
        ),
        HardeningRule(
            id="subj_discretion",
            name="Sole Discretion → Bounded Discretion",
            pattern=r"\b(in\s+)?(its?\s+)?sole\s+(and\s+absolute\s+)?discretion\b",
            strategy=HardeningStrategy.BOUND,
            replacement_template="in its reasonable discretion, exercised in good faith and not arbitrarily withheld",
            default_values={},
            priority=6,
            risk_reduction=0.35,
        ),
        # Termination
        HardeningRule(
            id="term_cause",
            name="For Cause → Enumerated Causes",
            pattern=r"\bfor\s+cause\b(?!\s*\()",
            strategy=HardeningStrategy.ENUMERATE,
            replacement_template="for cause (meaning {causes})",
            default_values={
                "causes": "material breach that remains uncured after 30 days' written notice, bankruptcy, or assignment without consent"
            },
            priority=8,
            risk_reduction=0.45,
        ),
    ]

    def __init__(
        self,
        pattern_analyzer: Optional[ClausePatternAnalyzer] = None,
        custom_rules: Optional[List[HardeningRule]] = None,
        default_level: HardeningLevel = HardeningLevel.MODERATE,
    ):
        """
        Initialize the clause hardener.

        Args:
            pattern_analyzer: Pattern analyzer for risk assessment
            custom_rules: Additional hardening rules
            custom_rules: Additional hardening rules
            default_level: Default hardening level
        """
        self.pattern_analyzer = pattern_analyzer or ClausePatternAnalyzer()
        self.default_level = default_level

        # Combine default and custom rules
        self.rules = sorted(
            self.DEFAULT_RULES + (custom_rules or []),
            key=lambda r: r.priority,
            reverse=True,
        )

        # Sessions
        self._sessions: Dict[str, HardeningSession] = {}

    def harden_clause(
        self,
        clause: str,
        level: Optional[HardeningLevel] = None,
        custom_values: Optional[Dict[str, Dict[str, str]]] = None,
        category: Optional[ClauseCategory] = None,
    ) -> HardeningResult:
        """
        Harden a single clause.

        Args:
            clause: The clause text to harden
            level: Hardening level to apply
            custom_values: Custom values for rule placeholders {rule_id: {placeholder: value}}
            category: Override clause category

        Returns:
            HardeningResult with original and hardened clause
        """
        level = level or self.default_level
        custom_values = custom_values or {}

        # Analyze original clause
        analysis = self.pattern_analyzer.analyze_clause(clause)
        detected_category = category or ClauseCategory(analysis["category"])
        risk_before = self._calculate_risk_score(analysis)

        # Apply rules
        hardened = clause
        changes = []
        rules_applied = []
        warnings = []

        for rule in self.rules:
            # Check if rule applies to this category
            if rule.categories and detected_category not in rule.categories:
                continue

            # Check if rule matches
            if not re.search(rule.pattern, hardened, re.IGNORECASE):
                continue

            # Skip aggressive rules in minimal mode
            if level == HardeningLevel.MINIMAL and rule.risk_reduction < 0.4:
                continue

            # Apply rule
            values = custom_values.get(rule.id, {})
            new_text = rule.apply(hardened, values)

            if new_text != hardened:
                changes.append(
                    {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "strategy": rule.strategy.value,
                        "before": self._extract_match(hardened, rule.pattern),
                        "after": self._extract_replacement(new_text, hardened, rule.pattern),
                        "risk_reduction": rule.risk_reduction,
                    }
                )
                rules_applied.append(rule.id)
                hardened = new_text

                # Check for placeholder warnings
                if "{" in hardened and "}" in hardened:
                    warnings.append(
                        f"Rule '{rule.name}' contains unfilled placeholders. "
                        "Please provide specific values."
                    )

        # Recalculate risk
        post_analysis = self.pattern_analyzer.analyze_clause(hardened)
        risk_after = self._calculate_risk_score(post_analysis)

        return HardeningResult(
            original=clause,
            hardened=hardened,
            changes=changes,
            risk_before=risk_before,
            risk_after=risk_after,
            rules_applied=rules_applied,
            warnings=warnings,
            metadata={
                "category": detected_category.value,
                "level": level.value,
                "trigger_count_before": len(analysis["dispute_triggers"]),
                "trigger_count_after": len(post_analysis["dispute_triggers"]),
            },
        )

    def harden_contract(
        self,
        clauses: List[str],
        level: Optional[HardeningLevel] = None,
        custom_values: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> List[HardeningResult]:
        """
        Harden all clauses in a contract.

        Args:
            clauses: List of clause texts
            level: Hardening level
            custom_values: Custom values for placeholders

        Returns:
            List of HardeningResults
        """
        return [self.harden_clause(clause, level, custom_values) for clause in clauses]

    def create_session(
        self,
        clauses: List[str],
    ) -> HardeningSession:
        """
        Create an interactive hardening session.

        Args:
            clauses: Clauses to harden

        Returns:
            New HardeningSession
        """
        import secrets

        session_id = secrets.token_urlsafe(12)

        session = HardeningSession(
            id=session_id,
            original_clauses=clauses.copy(),
        )

        # Generate initial hardening
        for clause in clauses:
            result = self.harden_clause(clause)
            session.results.append(result)
            session.hardened_clauses.append(result.hardened)

        self._sessions[session_id] = session
        return session

    def update_session(
        self,
        session_id: str,
        clause_index: int,
        override_text: Optional[str] = None,
        custom_values: Optional[Dict[str, str]] = None,
    ) -> HardeningResult:
        """
        Update a clause in an existing session.

        Args:
            session_id: Session ID
            clause_index: Index of clause to update
            override_text: Manual override text
            custom_values: Custom values for re-hardening

        Returns:
            Updated HardeningResult
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if clause_index >= len(session.original_clauses):
            raise ValueError(f"Invalid clause index {clause_index}")

        if override_text:
            # Manual override
            session.user_overrides[clause_index] = override_text
            session.hardened_clauses[clause_index] = override_text

            # Create result for override
            result = HardeningResult(
                original=session.original_clauses[clause_index],
                hardened=override_text,
                changes=[{"type": "user_override"}],
                risk_before=session.results[clause_index].risk_before,
                risk_after=self._calculate_risk_score(
                    self.pattern_analyzer.analyze_clause(override_text)
                ),
                rules_applied=["user_override"],
                metadata={"user_override": True},
            )
        else:
            # Re-harden with custom values
            result = self.harden_clause(
                session.original_clauses[clause_index],
                custom_values=(
                    {rule.id: custom_values for rule in self.rules} if custom_values else None
                ),
            )
            session.hardened_clauses[clause_index] = result.hardened

        session.results[clause_index] = result
        return result

    def finalize_session(self, session_id: str) -> List[str]:
        """
        Finalize a session and return hardened clauses.

        Args:
            session_id: Session ID

        Returns:
            List of final hardened clauses
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.completed = True
        return session.hardened_clauses.copy()

    def get_rule_suggestions(
        self,
        clause: str,
    ) -> List[Dict[str, Any]]:
        """
        Get applicable rules and their default values for a clause.

        Args:
            clause: Clause to analyze

        Returns:
            List of applicable rules with placeholders
        """
        suggestions = []

        for rule in self.rules:
            if re.search(rule.pattern, clause, re.IGNORECASE):
                match = re.search(rule.pattern, clause, re.IGNORECASE)
                suggestions.append(
                    {
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "strategy": rule.strategy.value,
                        "matched_text": match.group() if match else "",
                        "replacement_template": rule.replacement_template,
                        "default_values": rule.default_values,
                        "required_values": self._extract_placeholders(rule.replacement_template),
                        "risk_reduction": rule.risk_reduction,
                    }
                )

        return suggestions

    def validate_hardening(
        self,
        original: str,
        hardened: str,
    ) -> Dict[str, Any]:
        """
        Validate that hardening preserves legal intent.

        Args:
            original: Original clause
            hardened: Hardened clause

        Returns:
            Validation result with any warnings
        """
        warnings = []
        issues = []

        # Check for removed key terms
        original_tokens = set(self.pattern_analyzer._tokenize(original))
        hardened_tokens = set(self.pattern_analyzer._tokenize(hardened))

        removed = original_tokens - hardened_tokens
        important_terms = {
            "shall",
            "must",
            "will",
            "may",
            "right",
            "obligation",
            "license",
            "grant",
            "terminate",
            "indemnify",
            "warrant",
        }
        removed_important = removed & important_terms
        if removed_important:
            warnings.append(
                f"Key terms removed: {', '.join(removed_important)}. "
                "Verify this doesn't change legal meaning."
            )

        # Check for significant length change
        len_ratio = len(hardened) / len(original) if original else 1
        if len_ratio < 0.5:
            warnings.append("Clause significantly shortened. Verify no critical content was lost.")
        elif len_ratio > 3.0:
            warnings.append(
                "Clause significantly expanded. Consider if this adds unnecessary complexity."
            )

        # Check for unfilled placeholders
        placeholders = re.findall(r"\{[^}]+\}", hardened)
        if placeholders:
            issues.append(f"Unfilled placeholders: {', '.join(placeholders)}")

        # Check for undefined references
        references = re.findall(r"Section\s+\[?[A-Z0-9.]+\]?|Schedule\s+\[?[A-Z]\]?", hardened)
        for ref in references:
            if "[" in ref:
                issues.append(f"Undefined reference: {ref}")

        return {
            "valid": len(issues) == 0,
            "warnings": warnings,
            "issues": issues,
            "length_ratio": len_ratio,
            "terms_added": len(hardened_tokens - original_tokens),
            "terms_removed": len(removed),
        }

    def _calculate_risk_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate numeric risk score from analysis."""
        trigger_count = len(analysis.get("dispute_triggers", []))
        suggestion_count = len(analysis.get("hardening_suggestions", []))

        # Base risk from triggers
        risk = min(1.0, trigger_count * 0.15 + suggestion_count * 0.1)

        # Adjust based on similar patterns' dispute rates
        for similar in analysis.get("similar_patterns", []):
            risk = max(risk, similar.get("dispute_rate", 0) * similar.get("similarity", 0))

        return round(risk, 3)

    def _extract_match(self, text: str, pattern: str) -> str:
        """Extract the matched text from a pattern."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group() if match else ""

    def _extract_replacement(self, new_text: str, old_text: str, pattern: str) -> str:
        """Extract what replaced the pattern."""
        old_match = re.search(pattern, old_text, re.IGNORECASE)
        if not old_match:
            return ""

        # Find what's different in new text at the same position
        start = old_match.start()
        old_len = len(old_match.group())

        # Find the new content
        for end in range(start + old_len, len(new_text) + 1):
            candidate = new_text[start:end]
            if not re.search(pattern, candidate, re.IGNORECASE):
                # We've gone past the replacement
                return new_text[start : end - 1] if end > start else candidate

        return new_text[start:]

    def _extract_placeholders(self, template: str) -> List[str]:
        """Extract placeholder names from a template."""
        return re.findall(r"\{(\w+)\}", template)


class HardeningPipeline:
    """
    Pipeline for batch hardening with quality controls.

    Provides a structured workflow for hardening multiple clauses
    with validation, review gates, and rollback capability.
    """

    def __init__(
        self,
        hardener: Optional[ClauseHardener] = None,
        auto_validate: bool = True,
        require_review: bool = False,
    ):
        """
        Initialize the pipeline.

        Args:
            hardener: ClauseHardener instance
            auto_validate: Automatically validate each result
            require_review: Require manual review before finalization
        """
        self.hardener = hardener or ClauseHardener()
        self.auto_validate = auto_validate
        self.require_review = require_review

        self._pipeline_results: Dict[str, List[HardeningResult]] = {}
        self._validations: Dict[str, List[Dict[str, Any]]] = {}
        self._reviewed: Dict[str, Set[int]] = {}

    def process(
        self,
        contract_id: str,
        clauses: List[str],
        level: Optional[HardeningLevel] = None,
    ) -> List[HardeningResult]:
        """
        Process clauses through the hardening pipeline.

        Args:
            contract_id: Unique contract identifier
            clauses: Clauses to harden
            level: Hardening level

        Returns:
            List of HardeningResults
        """
        results = self.hardener.harden_contract(clauses, level)

        self._pipeline_results[contract_id] = results
        self._reviewed[contract_id] = set()

        if self.auto_validate:
            self._validations[contract_id] = [
                self.hardener.validate_hardening(r.original, r.hardened) for r in results
            ]

        return results

    def mark_reviewed(self, contract_id: str, clause_indices: List[int]) -> None:
        """Mark clauses as reviewed."""
        if contract_id not in self._reviewed:
            raise ValueError(f"Contract {contract_id} not found")

        self._reviewed[contract_id].update(clause_indices)

    def get_pending_review(self, contract_id: str) -> List[int]:
        """Get indices of clauses pending review."""
        if contract_id not in self._pipeline_results:
            raise ValueError(f"Contract {contract_id} not found")

        all_indices = set(range(len(self._pipeline_results[contract_id])))
        return sorted(all_indices - self._reviewed.get(contract_id, set()))

    def finalize(self, contract_id: str) -> List[str]:
        """
        Finalize and return hardened clauses.

        Args:
            contract_id: Contract to finalize

        Returns:
            Final hardened clauses

        Raises:
            ValueError: If review required but not complete
        """
        if contract_id not in self._pipeline_results:
            raise ValueError(f"Contract {contract_id} not found")

        if self.require_review:
            pending = self.get_pending_review(contract_id)
            if pending:
                raise ValueError(f"Review required for clauses: {pending}")

        results = self._pipeline_results[contract_id]
        return [r.hardened for r in results]

    def get_summary(self, contract_id: str) -> Dict[str, Any]:
        """Get pipeline summary for a contract."""
        if contract_id not in self._pipeline_results:
            raise ValueError(f"Contract {contract_id} not found")

        results = self._pipeline_results[contract_id]
        validations = self._validations.get(contract_id, [])

        total_risk_before = sum(r.risk_before for r in results)
        total_risk_after = sum(r.risk_after for r in results)

        return {
            "contract_id": contract_id,
            "clause_count": len(results),
            "clauses_modified": sum(1 for r in results if r.was_modified),
            "total_risk_before": total_risk_before,
            "total_risk_after": total_risk_after,
            "risk_reduction_percent": (
                (total_risk_before - total_risk_after) / total_risk_before * 100
                if total_risk_before > 0
                else 0
            ),
            "rules_applied": list(set(rule for r in results for rule in r.rules_applied)),
            "validation_issues": sum(len(v.get("issues", [])) for v in validations),
            "pending_review": len(self.get_pending_review(contract_id)),
        }
