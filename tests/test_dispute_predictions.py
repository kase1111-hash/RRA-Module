# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Predictive Dispute Warnings (Phase 6.6).

Tests cover:
- Dispute warning generation
- Warning severity classification
- Mitigation suggestions
- Term entropy analysis
- High-risk term detection
- API endpoints
"""

import pytest

from src.rra.predictions.dispute_warning import (
    DisputeWarningGenerator,
    WarningReport,
    WarningSeverity,
    WarningCategory,
    generate_dispute_warnings,
)
from src.rra.analytics.term_analysis import (
    TermAnalyzer,
    TermAnalysis,
    TermReport,
    TermRiskLevel,
    TermCategory,
    find_high_entropy_terms,
)


# =============================================================================
# DisputeWarningGenerator Tests
# =============================================================================


class TestDisputeWarningGenerator:
    """Tests for the dispute warning generator."""

    @pytest.fixture
    def generator(self):
        """Create a warning generator instance."""
        return DisputeWarningGenerator()

    @pytest.fixture
    def sample_clauses(self):
        """Sample contract clauses for testing."""
        return [
            "The Licensor grants to Licensee a non-exclusive license to use the Software.",
            "Licensee shall respond to any inquiries within a reasonable time.",
            "The Licensor shall use best efforts to maintain service availability.",
            "This agreement includes, but is not limited to, support and maintenance.",
            "Either party may terminate upon material breach by the other party.",
        ]

    @pytest.fixture
    def clean_clauses(self):
        """Clean contract clauses without common issues."""
        return [
            "The Licensor grants to Licensee a non-exclusive license to use the Software.",
            "Licensee shall respond to any inquiries within 14 business days.",
            "Either party may terminate with 30 days written notice.",
            "Disputes shall be resolved through binding arbitration.",
            "Liability is limited to the amount paid under this agreement.",
        ]

    def test_generate_warnings_basic(self, generator, sample_clauses):
        """Test basic warning generation."""
        report = generator.generate_warnings(sample_clauses)

        assert isinstance(report, WarningReport)
        assert report.contract_id is not None
        assert len(report.warnings) > 0
        assert 0 <= report.overall_risk_score <= 1
        assert 0 <= report.dispute_probability <= 1

    def test_ambiguous_term_detection(self, generator, sample_clauses):
        """Test detection of ambiguous terms."""
        report = generator.generate_warnings(sample_clauses)

        # Check for ambiguity warnings
        ambiguity_warnings = [w for w in report.warnings if w.category == WarningCategory.AMBIGUITY]
        assert len(ambiguity_warnings) > 0

        # Should detect "reasonable time"
        reasonable_warning = next(
            (w for w in ambiguity_warnings if "reasonable" in w.title.lower()), None
        )
        assert reasonable_warning is not None
        assert reasonable_warning.severity in [WarningSeverity.HIGH, WarningSeverity.MEDIUM]

    def test_best_efforts_detection(self, generator, sample_clauses):
        """Test detection of 'best efforts' language."""
        report = generator.generate_warnings(sample_clauses)

        best_efforts_warning = next(
            (w for w in report.warnings if "best efforts" in w.title.lower()), None
        )
        assert best_efforts_warning is not None
        assert len(best_efforts_warning.mitigations) > 0

    def test_including_but_not_limited_detection(self, generator, sample_clauses):
        """Test detection of open-ended lists."""
        report = generator.generate_warnings(sample_clauses)

        scope_warning = next(
            (w for w in report.warnings if "including but not limited" in w.title.lower()), None
        )
        assert scope_warning is not None

    def test_material_breach_detection(self, generator, sample_clauses):
        """Test detection of 'material breach' language."""
        report = generator.generate_warnings(sample_clauses)

        material_warning = next((w for w in report.warnings if "material" in w.title.lower()), None)
        assert material_warning is not None

    def test_clean_clauses_fewer_warnings(self, generator, sample_clauses, clean_clauses):
        """Test that clean clauses generate fewer warnings."""
        dirty_report = generator.generate_warnings(sample_clauses)
        clean_report = generator.generate_warnings(clean_clauses)

        # Clean clauses should have fewer ambiguity warnings
        dirty_ambiguity = sum(
            1 for w in dirty_report.warnings if w.category == WarningCategory.AMBIGUITY
        )
        clean_ambiguity = sum(
            1 for w in clean_report.warnings if w.category == WarningCategory.AMBIGUITY
        )
        assert clean_ambiguity < dirty_ambiguity

    def test_missing_clause_detection(self, generator):
        """Test detection of missing required clauses."""
        # Minimal clauses missing common provisions
        minimal_clauses = [
            "The Licensor grants to Licensee a license to use the Software.",
        ]

        report = generator.generate_warnings(minimal_clauses, license_type="commercial")

        missing_warnings = [
            w for w in report.warnings if w.category == WarningCategory.MISSING_CLAUSE
        ]
        assert len(missing_warnings) > 0

        # Should warn about missing dispute resolution
        dispute_warning = next((w for w in missing_warnings if "dispute" in w.title.lower()), None)
        assert dispute_warning is not None

    def test_severity_levels(self, generator):
        """Test warning severity classification."""
        high_risk_clauses = [
            "Respond within a reasonable time using best efforts.",
            "Material breaches shall be handled promptly.",
        ]

        report = generator.generate_warnings(high_risk_clauses)

        # Should have various severity levels
        severities = set(w.severity for w in report.warnings)
        assert len(severities) > 1

    def test_mitigations_provided(self, generator, sample_clauses):
        """Test that warnings include mitigations."""
        report = generator.generate_warnings(sample_clauses)

        for warning in report.warnings:
            assert len(warning.mitigations) > 0
            for mitigation in warning.mitigations:
                assert mitigation.id is not None
                assert mitigation.description
                assert mitigation.action
                assert 0 <= mitigation.impact <= 1
                assert mitigation.effort in ["low", "medium", "high"]

    def test_warning_acknowledge(self, generator, sample_clauses):
        """Test warning acknowledgment."""
        report = generator.generate_warnings(sample_clauses)

        if report.warnings:
            warning_id = report.warnings[0].id
            success = generator.acknowledge_warning(warning_id)
            assert success

            warning = generator.get_warning(warning_id)
            assert warning.acknowledged

    def test_warning_resolve(self, generator, sample_clauses):
        """Test warning resolution."""
        report = generator.generate_warnings(sample_clauses)

        if report.warnings:
            warning_id = report.warnings[0].id
            success = generator.resolve_warning(warning_id)
            assert success

            warning = generator.get_warning(warning_id)
            assert warning.resolved

    def test_unknown_warning_returns_false(self, generator):
        """Test handling of unknown warning ID."""
        success = generator.acknowledge_warning("unknown_id")
        assert not success

        success = generator.resolve_warning("unknown_id")
        assert not success

    def test_complexity_warning(self, generator):
        """Test detection of overly complex clauses."""
        complex_clause = " ".join(["word"] * 250)  # Very long clause

        report = generator.generate_warnings([complex_clause])

        complexity_warning = next(
            (w for w in report.warnings if w.category == WarningCategory.COMPLEXITY), None
        )
        assert complexity_warning is not None

    def test_undefined_reference_detection(self, generator):
        """Test detection of undefined references."""
        clause_with_placeholder = "As defined in Section [X], the parties agree to Schedule [A]."

        report = generator.generate_warnings([clause_with_placeholder])

        undefined_warnings = [w for w in report.warnings if w.category == WarningCategory.UNDEFINED]
        assert len(undefined_warnings) > 0

    def test_license_type_affects_required_clauses(self, generator):
        """Test that license type affects required clause checks."""
        minimal_clauses = ["The Licensor grants a license."]

        commercial_report = generator.generate_warnings(minimal_clauses, license_type="commercial")
        saas_report = generator.generate_warnings(minimal_clauses, license_type="saas")
        oss_report = generator.generate_warnings(minimal_clauses, license_type="open_source")

        # Different license types should have different requirements
        commercial_missing = sum(
            1 for w in commercial_report.warnings if w.category == WarningCategory.MISSING_CLAUSE
        )
        saas_missing = sum(
            1 for w in saas_report.warnings if w.category == WarningCategory.MISSING_CLAUSE
        )
        sum(1 for w in oss_report.warnings if w.category == WarningCategory.MISSING_CLAUSE)

        # All should have some missing clauses, but counts may differ
        assert commercial_missing > 0
        assert saas_missing > 0

    def test_convenience_function(self, sample_clauses):
        """Test the convenience function."""
        report = generate_dispute_warnings(sample_clauses)

        assert isinstance(report, WarningReport)
        assert len(report.warnings) > 0

    def test_report_summary_properties(self, generator, sample_clauses):
        """Test report summary properties."""
        report = generator.generate_warnings(sample_clauses)

        assert isinstance(report.critical_count, int)
        assert isinstance(report.high_count, int)
        assert isinstance(report.total_count, int)
        assert isinstance(report.unresolved_count, int)
        assert report.total_count == len(report.warnings)

    def test_warnings_sorted_by_severity(self, generator, sample_clauses):
        """Test that warnings are sorted by severity."""
        report = generator.generate_warnings(sample_clauses)

        if len(report.warnings) > 1:
            # Higher severity warnings should come first
            severity_order = list(WarningSeverity)
            for i in range(len(report.warnings) - 1):
                current_idx = severity_order.index(report.warnings[i].severity)
                next_idx = severity_order.index(report.warnings[i + 1].severity)
                # Lower index means higher severity
                assert current_idx <= next_idx or (
                    current_idx == next_idx
                    and report.warnings[i].dispute_probability
                    >= report.warnings[i + 1].dispute_probability
                )


# =============================================================================
# TermAnalyzer Tests
# =============================================================================


class TestTermAnalyzer:
    """Tests for the term analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create a term analyzer instance."""
        return TermAnalyzer()

    @pytest.fixture
    def sample_clauses(self):
        """Sample clauses with various terms."""
        return [
            "The Licensee shall respond within a reasonable time.",
            "Provider shall use best efforts to maintain uptime.",
            "Material breaches shall be reported promptly.",
            "Services include, but are not limited to, hosting.",
        ]

    def test_analyze_contract_basic(self, analyzer, sample_clauses):
        """Test basic contract analysis."""
        report = analyzer.analyze_contract(sample_clauses)

        assert isinstance(report, TermReport)
        assert report.contract_id is not None
        assert len(report.terms) > 0

    def test_known_terms_detected(self, analyzer, sample_clauses):
        """Test that known high-risk terms are detected."""
        report = analyzer.analyze_contract(sample_clauses)

        term_names = [t.term.lower() for t in report.terms]
        assert any("reasonable" in t for t in term_names)
        assert any("best efforts" in t for t in term_names)
        assert any("promptly" in t for t in term_names)

    def test_term_categories(self, analyzer, sample_clauses):
        """Test that terms are properly categorized."""
        report = analyzer.analyze_contract(sample_clauses)

        categories = set(t.category for t in report.terms)
        # Should have multiple categories
        assert len(categories) > 1

    def test_term_risk_levels(self, analyzer, sample_clauses):
        """Test that terms have risk levels assigned."""
        report = analyzer.analyze_contract(sample_clauses)

        for term in report.terms:
            assert term.risk_level in TermRiskLevel

    def test_entropy_scores_in_range(self, analyzer, sample_clauses):
        """Test that entropy scores are in valid range."""
        report = analyzer.analyze_contract(sample_clauses)

        for term in report.terms:
            assert 0 <= term.entropy_score <= 1
            assert 0 <= term.dispute_rate <= 1

    def test_alternatives_provided(self, analyzer, sample_clauses):
        """Test that alternatives are suggested for known terms."""
        report = analyzer.analyze_contract(sample_clauses)

        terms_with_alternatives = [t for t in report.terms if t.alternatives]
        assert len(terms_with_alternatives) > 0

    def test_single_term_analysis(self, analyzer):
        """Test analyzing a single term."""
        analysis = analyzer.analyze_term("reasonable time")

        assert analysis.term == "reasonable time"
        assert analysis.category == TermCategory.TEMPORAL
        assert analysis.entropy_score > 0
        assert len(analysis.alternatives) > 0

    def test_unknown_term_analysis(self, analyzer):
        """Test analyzing an unknown term."""
        analysis = analyzer.analyze_term("unknown_legal_term")

        assert analysis.term == "unknown_legal_term"
        assert analysis.risk_level == TermRiskLevel.MODERATE
        assert analysis.explanation == "Unknown term - requires manual review"

    def test_get_high_entropy_terms(self, analyzer, sample_clauses):
        """Test filtering high-entropy terms."""
        high_entropy = analyzer.get_high_entropy_terms(sample_clauses, threshold=0.6)

        for term in high_entropy:
            assert term.entropy_score >= 0.6

    def test_suggest_alternatives(self, analyzer):
        """Test getting alternatives for a term."""
        alternatives = analyzer.suggest_alternatives("reasonable time")
        assert len(alternatives) > 0
        assert any("days" in alt.lower() for alt in alternatives)

    def test_add_custom_term(self, analyzer):
        """Test adding a custom term."""
        analyzer.add_custom_term(
            term="proprietary methodology",
            category=TermCategory.SCOPE,
            entropy=0.7,
            dispute_rate=0.3,
            explanation="Custom IP term",
            alternatives=["methodology as defined in Exhibit A"],
        )

        analysis = analyzer.analyze_term("proprietary methodology")
        assert analysis.entropy_score == 0.7
        assert analysis.category == TermCategory.SCOPE
        assert len(analysis.alternatives) > 0

    def test_record_outcome(self, analyzer):
        """Test recording dispute outcomes."""
        analyzer.record_outcome("reasonable time", "contract_123", disputed=True)
        analyzer.record_outcome("reasonable time", "contract_456", disputed=False)

        # Should not affect rate with too few samples
        rate = analyzer.get_updated_dispute_rate("reasonable time")
        # With < 5 samples, should return base rate
        base_rate = analyzer.TERM_DATABASE["reasonable time"]["dispute_rate"]
        assert rate == base_rate

    def test_updated_dispute_rate_with_samples(self, analyzer):
        """Test dispute rate updates with sufficient samples."""
        for i in range(10):
            analyzer.record_outcome("reasonable time", f"contract_{i}", disputed=i < 5)

        rate = analyzer.get_updated_dispute_rate("reasonable time")
        # Rate should be influenced by recorded outcomes (50% disputed)
        assert rate != analyzer.TERM_DATABASE["reasonable time"]["dispute_rate"]

    def test_term_occurrences_tracked(self, analyzer, sample_clauses):
        """Test that term occurrences are tracked."""
        report = analyzer.analyze_contract(sample_clauses)

        for term in report.terms:
            assert term.frequency > 0
            assert len(term.occurrences) == term.frequency

    def test_occurrence_context_captured(self, analyzer):
        """Test that context is captured for occurrences."""
        clauses = ["The party shall respond within a reasonable time frame."]
        report = analyzer.analyze_contract(clauses)

        reasonable_term = next((t for t in report.terms if "reasonable" in t.term.lower()), None)
        if reasonable_term and reasonable_term.occurrences:
            assert reasonable_term.occurrences[0].context
            assert "reasonable" in reasonable_term.occurrences[0].context.lower()

    def test_report_statistics(self, analyzer, sample_clauses):
        """Test report statistics."""
        report = analyzer.analyze_contract(sample_clauses)

        assert report.total_entropy >= 0
        assert report.avg_entropy >= 0
        assert isinstance(report.risk_distribution, dict)
        assert isinstance(report.category_distribution, dict)

    def test_top_concerns_generated(self, analyzer, sample_clauses):
        """Test that top concerns are generated."""
        report = analyzer.analyze_contract(sample_clauses)

        # May or may not have concerns depending on content
        assert isinstance(report.top_concerns, list)
        assert len(report.top_concerns) <= 5

    def test_convenience_function(self, sample_clauses):
        """Test the convenience function."""
        high_entropy = find_high_entropy_terms(sample_clauses)

        assert isinstance(high_entropy, list)
        for term in high_entropy:
            assert isinstance(term, TermAnalysis)

    def test_to_dict_methods(self, analyzer, sample_clauses):
        """Test dictionary conversion methods."""
        report = analyzer.analyze_contract(sample_clauses)

        report_dict = report.to_dict()
        assert "contract_id" in report_dict
        assert "summary" in report_dict
        assert "terms" in report_dict

        if report.terms:
            term_dict = report.terms[0].to_dict()
            assert "term" in term_dict
            assert "category" in term_dict
            assert "entropy_score" in term_dict


# =============================================================================
# Warning and Report Serialization Tests
# =============================================================================


class TestSerialization:
    """Tests for serialization of warnings and reports."""

    @pytest.fixture
    def generator(self):
        return DisputeWarningGenerator()

    def test_warning_to_dict(self, generator):
        """Test warning dictionary conversion."""
        report = generator.generate_warnings(
            ["Respond within a reasonable time using best efforts."]
        )

        if report.warnings:
            warning_dict = report.warnings[0].to_dict()
            assert "id" in warning_dict
            assert "severity" in warning_dict
            assert "category" in warning_dict
            assert "title" in warning_dict
            assert "description" in warning_dict
            assert "mitigations" in warning_dict
            assert "dispute_probability" in warning_dict

    def test_report_to_dict(self, generator):
        """Test report dictionary conversion."""
        report = generator.generate_warnings(
            ["The Licensee shall respond within a reasonable time."]
        )

        report_dict = report.to_dict()
        assert "contract_id" in report_dict
        assert "overall_risk_score" in report_dict
        assert "dispute_probability" in report_dict
        assert "summary" in report_dict
        assert "warnings" in report_dict
        assert "prediction" in report_dict

    def test_mitigation_serialization(self, generator):
        """Test mitigation serialization."""
        report = generator.generate_warnings(["Respond within a reasonable time."])

        if report.warnings:
            warning_dict = report.warnings[0].to_dict()
            if warning_dict["mitigations"]:
                mitigation = warning_dict["mitigations"][0]
                assert "id" in mitigation
                assert "description" in mitigation
                assert "action" in mitigation
                assert "impact" in mitigation
                assert "effort" in mitigation


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for warning and term analysis."""

    def test_warning_generator_with_term_analyzer(self):
        """Test that warning generator integrates with term analysis."""
        generator = DisputeWarningGenerator()
        analyzer = TermAnalyzer()

        clauses = [
            "Provider shall use best efforts to deliver within a reasonable time.",
            "Material changes require prior written approval.",
        ]

        warnings = generator.generate_warnings(clauses)
        terms = analyzer.analyze_contract(clauses)

        # Both should identify similar issues
        warning_terms = set()
        for w in warnings.warnings:
            if w.matched_text:
                warning_terms.add(w.matched_text.lower())

        term_names = set(t.term.lower() for t in terms.terms)

        # Should have some overlap
        assert any(any(t in wt for wt in warning_terms) for t in term_names) or (
            len(term_names) > 0
        )

    def test_complete_contract_analysis_flow(self):
        """Test complete analysis flow for a contract."""
        generator = DisputeWarningGenerator()
        analyzer = TermAnalyzer()

        clauses = [
            "The Licensor grants to Licensee a perpetual, non-exclusive license.",
            "Licensee shall notify Licensor of any issues promptly.",
            "Either party may terminate upon material breach.",
            "Disputes shall be resolved through good faith negotiation.",
            "Provider shall use best efforts to maintain 99.9% uptime.",
        ]

        # Generate warnings
        warning_report = generator.generate_warnings(
            clauses,
            license_type="saas",
            context={"licensee_prior_disputes": 2},
        )

        # Analyze terms
        term_report = analyzer.analyze_contract(clauses)

        # Verify comprehensive coverage
        assert warning_report.total_count > 0
        assert len(term_report.terms) > 0
        assert 0 <= warning_report.overall_risk_score <= 1
        assert term_report.avg_entropy > 0

        # Higher-risk scenarios should be detected
        high_risk_warnings = [
            w
            for w in warning_report.warnings
            if w.severity in [WarningSeverity.HIGH, WarningSeverity.CRITICAL]
        ]
        high_risk_terms = [
            t
            for t in term_report.terms
            if t.risk_level in [TermRiskLevel.HIGH, TermRiskLevel.CRITICAL]
        ]

        # Should identify some high-risk items
        assert len(high_risk_warnings) > 0 or len(high_risk_terms) > 0


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def generator(self):
        return DisputeWarningGenerator()

    @pytest.fixture
    def analyzer(self):
        return TermAnalyzer()

    def test_empty_clauses(self, generator, analyzer):
        """Test handling of empty clause list."""
        # Warning generator should handle empty input
        report = generator.generate_warnings([])
        assert report.total_count >= 0  # May have missing clause warnings

        # Term analyzer should handle empty input
        term_report = analyzer.analyze_contract([])
        assert len(term_report.terms) == 0

    def test_very_short_clause(self, generator, analyzer):
        """Test handling of very short clauses."""
        short_clause = ["OK."]

        report = generator.generate_warnings(short_clause)
        term_report = analyzer.analyze_contract(short_clause)

        assert isinstance(report, WarningReport)
        assert isinstance(term_report, TermReport)

    def test_very_long_clause(self, generator, analyzer):
        """Test handling of very long clauses."""
        long_clause = [" ".join(["word"] * 1000)]

        report = generator.generate_warnings(long_clause)
        term_report = analyzer.analyze_contract(long_clause)

        assert isinstance(report, WarningReport)
        assert isinstance(term_report, TermReport)

    def test_special_characters(self, generator, analyzer):
        """Test handling of special characters."""
        clause_with_special = ["The Licensee agrees to pay $100,000 @ 5% interest."]

        report = generator.generate_warnings(clause_with_special)
        term_report = analyzer.analyze_contract(clause_with_special)

        assert isinstance(report, WarningReport)
        assert isinstance(term_report, TermReport)

    def test_unicode_characters(self, generator, analyzer):
        """Test handling of unicode characters."""
        unicode_clause = ["The Licensée agrees to the términos and conditions."]

        report = generator.generate_warnings(unicode_clause)
        term_report = analyzer.analyze_contract(unicode_clause)

        assert isinstance(report, WarningReport)
        assert isinstance(term_report, TermReport)

    def test_multiple_same_terms(self, analyzer):
        """Test handling of multiple occurrences of same term."""
        clause = ["Respond promptly. Act promptly. Deliver promptly."]

        report = analyzer.analyze_contract(clause)

        promptly_term = next((t for t in report.terms if "promptly" in t.term.lower()), None)
        if promptly_term:
            assert promptly_term.frequency >= 3
