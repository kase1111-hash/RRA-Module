# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Tests for Automated Clause Hardening (Phase 6.5).

Tests cover:
- Clause hardener rule application
- Hardening level behavior
- Template rendering
- Template library search
- Validation and pipeline
"""

import pytest
from decimal import Decimal

from src.rra.negotiation.clause_hardener import (
    ClauseHardener,
    HardeningLevel,
    HardeningStrategy,
    HardeningRule,
    HardeningResult,
    HardeningSession,
    HardeningPipeline,
)
from src.rra.templates.hardened_clauses import (
    ClauseTemplate,
    TemplateCategory,
    TemplateLibrary,
    TemplateParameter,
    LicenseType,
    get_default_library,
)
from src.rra.analytics.clause_patterns import ClausePatternAnalyzer, ClauseCategory


# =============================================================================
# ClauseHardener Tests
# =============================================================================


class TestClauseHardener:
    """Tests for the clause hardening engine."""

    @pytest.fixture
    def hardener(self):
        """Create a clause hardener instance."""
        return ClauseHardener()

    def test_harden_reasonable_time(self, hardener):
        """Test hardening 'reasonable time' language."""
        clause = "The Licensee shall respond within a reasonable time."
        result = hardener.harden_clause(clause)

        assert result.was_modified
        assert "reasonable time" not in result.hardened.lower()
        assert "calendar days" in result.hardened.lower()
        assert result.risk_after < result.risk_before

    def test_harden_promptly(self, hardener):
        """Test hardening 'promptly' language."""
        clause = "Licensor shall promptly notify Licensee of any issues."
        result = hardener.harden_clause(clause)

        assert result.was_modified
        assert "promptly" not in result.hardened.lower()
        assert "business days" in result.hardened.lower()

    def test_harden_best_efforts(self, hardener):
        """Test hardening 'best efforts' language."""
        clause = "The Provider shall use best efforts to maintain uptime."
        result = hardener.harden_clause(clause)

        assert result.was_modified
        assert "best efforts" not in result.hardened.lower()
        assert "commercially reasonable" in result.hardened.lower()

    def test_harden_including_but_not_limited(self, hardener):
        """Test hardening open-ended lists."""
        clause = "Services include, but are not limited to, hosting and support."
        result = hardener.harden_clause(clause)

        assert result.was_modified
        assert "including, but not limited to" not in result.hardened.lower()

    def test_harden_material_breach(self, hardener):
        """Test hardening 'material breach' language."""
        clause = "Either party may terminate upon material breach."
        result = hardener.harden_clause(clause)

        assert result.was_modified
        assert "material breach (meaning" in result.hardened.lower()

    def test_hardening_levels(self, hardener):
        """Test different hardening levels."""
        clause = "Respond promptly using best efforts within reasonable time."

        # Minimal level should skip low-risk-reduction rules
        minimal_result = hardener.harden_clause(clause, level=HardeningLevel.MINIMAL)

        # Moderate level should apply more rules
        moderate_result = hardener.harden_clause(clause, level=HardeningLevel.MODERATE)

        # Aggressive applies even more
        aggressive_result = hardener.harden_clause(clause, level=HardeningLevel.AGGRESSIVE)

        # More aggressive = more changes
        assert len(aggressive_result.rules_applied) >= len(moderate_result.rules_applied)
        assert len(moderate_result.rules_applied) >= len(minimal_result.rules_applied)

    def test_custom_values(self, hardener):
        """Test providing custom values for placeholders."""
        clause = "Response must be provided within reasonable time."

        result = hardener.harden_clause(
            clause,
            custom_values={"time_reasonable": {"days": "45"}},
        )

        assert "45 calendar days" in result.hardened

    def test_no_modifications_needed(self, hardener):
        """Test clause that doesn't need hardening."""
        clause = "Licensee shall pay $100 within 30 calendar days of invoice date."
        result = hardener.harden_clause(clause)

        assert not result.was_modified
        assert result.original == result.hardened
        assert len(result.rules_applied) == 0

    def test_multiple_rules_applied(self, hardener):
        """Test that multiple rules can be applied to one clause."""
        clause = (
            "Licensor shall use best efforts to respond promptly "
            "and notify within reasonable time of any material breach."
        )
        result = hardener.harden_clause(clause)

        assert result.was_modified
        assert len(result.rules_applied) >= 3
        assert result.risk_reduction > 0

    def test_changes_tracking(self, hardener):
        """Test that changes are properly tracked."""
        clause = "Respond within reasonable time."
        result = hardener.harden_clause(clause)

        assert len(result.changes) == 1
        change = result.changes[0]
        assert "rule_id" in change
        assert "before" in change
        assert "after" in change
        assert "risk_reduction" in change

    def test_get_rule_suggestions(self, hardener):
        """Test getting rule suggestions for a clause."""
        clause = "Use best efforts to respond promptly."
        suggestions = hardener.get_rule_suggestions(clause)

        assert len(suggestions) >= 2
        assert any(s["rule_id"] == "effort_best" for s in suggestions)
        assert any(s["rule_id"] == "time_promptly" for s in suggestions)


class TestHardeningSession:
    """Tests for interactive hardening sessions."""

    @pytest.fixture
    def hardener(self):
        return ClauseHardener()

    def test_create_session(self, hardener):
        """Test creating a hardening session."""
        clauses = [
            "Respond within reasonable time.",
            "Use best efforts to maintain uptime.",
        ]

        session = hardener.create_session(clauses)

        assert session is not None
        assert len(session.original_clauses) == 2
        assert len(session.hardened_clauses) == 2
        assert len(session.results) == 2
        assert not session.completed

    def test_update_session_custom_values(self, hardener):
        """Test updating a session with custom values."""
        clauses = ["Respond within reasonable time."]
        session = hardener.create_session(clauses)

        result = hardener.update_session(
            session.id,
            clause_index=0,
            custom_values={"days": "60"},
        )

        assert result is not None

    def test_update_session_override(self, hardener):
        """Test manual override in a session."""
        clauses = ["Respond within reasonable time."]
        session = hardener.create_session(clauses)

        override = "Respond within 7 business days."
        result = hardener.update_session(
            session.id,
            clause_index=0,
            override_text=override,
        )

        assert result.hardened == override
        assert session.user_overrides[0] == override

    def test_finalize_session(self, hardener):
        """Test finalizing a session."""
        clauses = ["Respond within reasonable time."]
        session = hardener.create_session(clauses)

        final_clauses = hardener.finalize_session(session.id)

        assert len(final_clauses) == 1
        assert session.completed


class TestHardeningValidation:
    """Tests for hardening validation."""

    @pytest.fixture
    def hardener(self):
        return ClauseHardener()

    def test_validate_good_hardening(self, hardener):
        """Test validation of properly hardened clause."""
        original = "Respond within reasonable time."
        hardened = "Respond within 30 calendar days."

        validation = hardener.validate_hardening(original, hardened)

        assert validation["valid"]
        assert len(validation["issues"]) == 0

    def test_validate_unfilled_placeholders(self, hardener):
        """Test detection of unfilled placeholders."""
        original = "Respond within reasonable time."
        hardened = "Respond within {days} calendar days."

        validation = hardener.validate_hardening(original, hardened)

        assert not validation["valid"]
        assert any("placeholder" in issue.lower() for issue in validation["issues"])

    def test_validate_undefined_references(self, hardener):
        """Test detection of undefined references."""
        original = "Follow the process."
        hardened = "Follow the process defined in Section [X]."

        validation = hardener.validate_hardening(original, hardened)

        assert any("reference" in issue.lower() for issue in validation["issues"])

    def test_validate_significant_shortening(self, hardener):
        """Test warning for significant shortening."""
        original = "This is a very long clause with lots of detailed text " * 5
        hardened = "Short clause."

        validation = hardener.validate_hardening(original, hardened)

        assert any("shortened" in w.lower() for w in validation["warnings"])


class TestHardeningPipeline:
    """Tests for the hardening pipeline."""

    @pytest.fixture
    def pipeline(self):
        return HardeningPipeline(auto_validate=True, require_review=True)

    def test_process_clauses(self, pipeline):
        """Test processing clauses through the pipeline."""
        clauses = [
            "Respond within reasonable time.",
            "Use best efforts to perform.",
        ]

        results = pipeline.process("contract_1", clauses)

        assert len(results) == 2
        assert all(isinstance(r, HardeningResult) for r in results)

    def test_pending_review(self, pipeline):
        """Test tracking of pending reviews."""
        clauses = ["Respond promptly."]
        pipeline.process("contract_1", clauses)

        pending = pipeline.get_pending_review("contract_1")
        assert 0 in pending

    def test_mark_reviewed(self, pipeline):
        """Test marking clauses as reviewed."""
        clauses = ["Respond promptly."]
        pipeline.process("contract_1", clauses)

        pipeline.mark_reviewed("contract_1", [0])
        pending = pipeline.get_pending_review("contract_1")

        assert 0 not in pending

    def test_finalize_requires_review(self, pipeline):
        """Test that finalization requires review."""
        clauses = ["Respond promptly."]
        pipeline.process("contract_1", clauses)

        with pytest.raises(ValueError, match="Review required"):
            pipeline.finalize("contract_1")

    def test_finalize_after_review(self, pipeline):
        """Test finalization after review."""
        clauses = ["Respond promptly."]
        pipeline.process("contract_1", clauses)
        pipeline.mark_reviewed("contract_1", [0])

        final = pipeline.finalize("contract_1")
        assert len(final) == 1

    def test_get_summary(self, pipeline):
        """Test getting pipeline summary."""
        clauses = ["Respond promptly.", "Use best efforts."]
        pipeline.process("contract_1", clauses)

        summary = pipeline.get_summary("contract_1")

        assert summary["contract_id"] == "contract_1"
        assert summary["clause_count"] == 2
        assert "risk_reduction_percent" in summary
        assert "rules_applied" in summary


# =============================================================================
# Template Tests
# =============================================================================


class TestClauseTemplate:
    """Tests for clause templates."""

    def test_render_with_defaults(self):
        """Test rendering template with default values."""
        template = ClauseTemplate(
            id="test_template",
            name="Test Template",
            category=TemplateCategory.GRANT,
            license_types=[LicenseType.COMMERCIAL],
            template_text="License for {max_users} users.",
            parameters=[
                TemplateParameter(
                    name="max_users",
                    description="Maximum users",
                    default_value="10",
                ),
            ],
        )

        rendered = template.render()
        assert rendered == "License for 10 users."

    def test_render_with_custom_values(self):
        """Test rendering template with custom values."""
        template = ClauseTemplate(
            id="test_template",
            name="Test Template",
            category=TemplateCategory.GRANT,
            license_types=[LicenseType.COMMERCIAL],
            template_text="License for {max_users} users.",
            parameters=[
                TemplateParameter(
                    name="max_users",
                    description="Maximum users",
                    default_value="10",
                ),
            ],
        )

        rendered = template.render({"max_users": "50"})
        assert rendered == "License for 50 users."

    def test_validate_required_parameters(self):
        """Test validation of required parameters."""
        template = ClauseTemplate(
            id="test_template",
            name="Test Template",
            category=TemplateCategory.GRANT,
            license_types=[LicenseType.COMMERCIAL],
            template_text="License for {max_users} users.",
            parameters=[
                TemplateParameter(
                    name="max_users",
                    description="Maximum users",
                    default_value="10",
                    required=True,
                ),
            ],
        )

        errors = template.validate_values({})
        assert any("max_users" in e for e in errors)

        errors = template.validate_values({"max_users": "5"})
        assert len(errors) == 0

    def test_get_required_parameters(self):
        """Test getting required parameters."""
        template = ClauseTemplate(
            id="test_template",
            name="Test Template",
            category=TemplateCategory.GRANT,
            license_types=[LicenseType.COMMERCIAL],
            template_text="License.",
            parameters=[
                TemplateParameter(name="a", description="A", default_value="1", required=True),
                TemplateParameter(name="b", description="B", default_value="2", required=False),
                TemplateParameter(name="c", description="C", default_value="3", required=True),
            ],
        )

        required = template.get_required_parameters()
        assert required == ["a", "c"]


class TestTemplateLibrary:
    """Tests for the template library."""

    @pytest.fixture
    def library(self):
        """Get the default template library."""
        return get_default_library()

    def test_default_library_has_templates(self, library):
        """Test that default library is populated."""
        templates = library.list_all()
        assert len(templates) > 0

    def test_get_by_category(self, library):
        """Test getting templates by category."""
        grant_templates = library.get_by_category(TemplateCategory.GRANT)
        assert len(grant_templates) > 0
        assert all(t.category == TemplateCategory.GRANT for t in grant_templates)

    def test_get_by_license_type(self, library):
        """Test getting templates by license type."""
        saas_templates = library.get_by_license_type(LicenseType.SAAS)
        assert len(saas_templates) > 0
        assert all(LicenseType.SAAS in t.license_types for t in saas_templates)

    def test_get_by_tag(self, library):
        """Test getting templates by tag."""
        termination_templates = library.get_by_tag("termination")
        assert len(termination_templates) > 0

    def test_search_with_multiple_criteria(self, library):
        """Test searching with multiple criteria."""
        results = library.search(
            category=TemplateCategory.TERMINATION,
            license_type=LicenseType.COMMERCIAL,
            max_risk_score=0.25,
        )

        assert len(results) > 0
        for template in results:
            assert template.category == TemplateCategory.TERMINATION
            assert LicenseType.COMMERCIAL in template.license_types
            assert template.risk_score <= 0.25

    def test_search_sorted_by_risk(self, library):
        """Test that search results are sorted by risk score."""
        results = library.search()

        for i in range(len(results) - 1):
            assert results[i].risk_score <= results[i + 1].risk_score

    def test_get_complete_contract(self, library):
        """Test generating a complete contract."""
        contract = library.get_complete_contract(
            license_type=LicenseType.SAAS,
            values={"warranty_period": "180 days"},
        )

        assert len(contract) > 0
        # Should have templates for key categories
        assert TemplateCategory.GRANT in contract or TemplateCategory.TERMINATION in contract


class TestDefaultTemplates:
    """Tests for specific default templates."""

    @pytest.fixture
    def library(self):
        return get_default_library()

    def test_grant_software_template(self, library):
        """Test the perpetual software grant template."""
        template = library.get_template("grant_software_perpetual")

        assert template is not None
        assert template.category == TemplateCategory.GRANT

        rendered = template.render({"max_installations": "10", "max_copies": "3"})
        assert "10 device" in rendered
        assert "3 backup" in rendered

    def test_termination_for_cause_template(self, library):
        """Test the termination for cause template."""
        template = library.get_template("termination_for_cause")

        assert template is not None
        assert template.category == TemplateCategory.TERMINATION
        assert template.risk_score < 0.25

        rendered = template.render({"cure_period": "45", "material_amount": "5,000"})
        assert "45 calendar days" in rendered
        assert "$5,000" in rendered

    def test_dispute_resolution_template(self, library):
        """Test the dispute resolution template."""
        template = library.get_template("dispute_escalation")

        assert template is not None
        assert template.category == TemplateCategory.DISPUTE_RESOLUTION

        rendered = template.render({
            "mediation_location": "New York, NY",
            "arbitration_location": "New York, NY",
        })
        assert "New York" in rendered
        assert "mediation" in rendered.lower()
        assert "arbitration" in rendered.lower()

    def test_liability_cap_template(self, library):
        """Test the liability cap template."""
        template = library.get_template("liability_limitation_cap")

        assert template is not None
        assert template.category == TemplateCategory.LIABILITY

        rendered = template.render({
            "liability_cap": "$500,000",
        })
        assert "$500,000" in rendered


# =============================================================================
# Pattern Analyzer Integration Tests
# =============================================================================


class TestPatternAnalyzerIntegration:
    """Tests for integration between hardener and pattern analyzer."""

    def test_risk_scoring(self):
        """Test that risk scoring uses pattern analyzer."""
        hardener = ClauseHardener()

        high_risk = "Use best efforts to respond within reasonable time promptly."
        low_risk = "Respond within 30 calendar days via email."

        high_result = hardener.harden_clause(high_risk)
        low_result = hardener.harden_clause(low_risk)

        assert high_result.risk_before > low_result.risk_before

    def test_category_detection(self):
        """Test that category is properly detected."""
        analyzer = ClausePatternAnalyzer()

        grant_clause = "Licensor grants Licensee a license to use the software."
        termination_clause = "Either party may terminate this agreement."

        assert analyzer.classify_category(grant_clause) == ClauseCategory.GRANT
        assert analyzer.classify_category(termination_clause) == ClauseCategory.TERMINATION
