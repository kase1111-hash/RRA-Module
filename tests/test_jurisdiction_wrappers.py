# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for Phase 6.12: Jurisdiction-Aware Wrappers.

Tests cover:
- Jurisdiction detection
- Per-jurisdiction compliance rules
- Legal wrapper templates
- Cross-border transaction handling
"""

import pytest
from decimal import Decimal

from rra.legal import (
    # Jurisdiction Detection
    JurisdictionCode,
    JurisdictionRegion,
    DetectionMethod,
    ConfidenceLevel,
    JurisdictionDetector,
    create_jurisdiction_detector,
    # Compliance Rules
    RegulatoryFramework,
    ContractLaw,
    DisputeResolution,
    IPLawTreaty,
    JurisdictionRulesRegistry,
    create_rules_registry,
)
from rra.templates import (
    TemplateType,
    LanguageCode,
    LegalTemplate,
    LegalTemplateLibrary,
    create_template_library,
)


# ============ Jurisdiction Detection Tests ============


class TestJurisdictionDetector:
    """Tests for JurisdictionDetector."""

    @pytest.fixture
    def detector(self) -> JurisdictionDetector:
        return create_jurisdiction_detector()

    def test_detect_from_phone_us(self, detector: JurisdictionDetector):
        """Test US phone number detection."""
        signal = detector.detect_from_phone("+1-555-123-4567")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.US
        assert signal.method == DetectionMethod.PHONE_NUMBER
        assert signal.confidence >= 0.7

    def test_detect_from_phone_uk(self, detector: JurisdictionDetector):
        """Test UK phone number detection."""
        signal = detector.detect_from_phone("+44 20 7946 0958")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.GB

    def test_detect_from_phone_singapore(self, detector: JurisdictionDetector):
        """Test Singapore phone number detection."""
        signal = detector.detect_from_phone("+65 6123 4567")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.SG

    def test_detect_from_phone_unknown(self, detector: JurisdictionDetector):
        """Test unknown phone prefix returns None."""
        signal = detector.detect_from_phone("+999 123 4567")

        assert signal is None

    def test_detect_from_address_us(self, detector: JurisdictionDetector):
        """Test US address detection."""
        signal = detector.detect_from_address("123 Main Street, New York, NY 10001")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.US
        assert signal.method == DetectionMethod.ADDRESS_PARSING

    def test_detect_from_address_uk(self, detector: JurisdictionDetector):
        """Test UK address detection."""
        signal = detector.detect_from_address("10 Downing Street, London, United Kingdom")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.GB

    def test_detect_from_address_germany(self, detector: JurisdictionDetector):
        """Test German address detection."""
        signal = detector.detect_from_address("Unter den Linden 77, Berlin, Germany")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.DE

    def test_detect_from_authority_uspto(self, detector: JurisdictionDetector):
        """Test USPTO authority detection."""
        signal = detector.detect_from_authority("USPTO")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.US
        assert signal.method == DetectionMethod.ASSET_AUTHORITY
        assert signal.confidence >= 0.9

    def test_detect_from_authority_epo(self, detector: JurisdictionDetector):
        """Test EPO authority detection."""
        signal = detector.detect_from_authority("EPO")

        assert signal is not None
        # EPO uses DE as representative
        assert signal.jurisdiction == JurisdictionCode.DE

    def test_detect_from_authority_wipo(self, detector: JurisdictionDetector):
        """Test WIPO authority detection."""
        signal = detector.detect_from_authority("WIPO")

        assert signal is not None
        assert signal.jurisdiction == JurisdictionCode.INT

    def test_declare_jurisdiction(self, detector: JurisdictionDetector):
        """Test explicit jurisdiction declaration."""
        signal = detector.declare_jurisdiction(
            participant_id="participant_1",
            jurisdiction=JurisdictionCode.CH,
            declaration_type="residence",
        )

        assert signal.jurisdiction == JurisdictionCode.CH
        assert signal.method == DetectionMethod.EXPLICIT_DECLARATION
        assert signal.confidence >= 0.9

    def test_kyc_verification(self, detector: JurisdictionDetector):
        """Test KYC-verified jurisdiction."""
        signal = detector.verify_from_kyc(
            participant_id="participant_1",
            kyc_jurisdiction=JurisdictionCode.SG,
            kyc_provider="Jumio",
        )

        assert signal.jurisdiction == JurisdictionCode.SG
        assert signal.method == DetectionMethod.KYC_VERIFICATION
        assert signal.confidence >= 0.99

    def test_aggregate_signals_single(self, detector: JurisdictionDetector):
        """Test aggregation with single signal."""
        signal = detector.declare_jurisdiction("p1", JurisdictionCode.US)
        result = detector.aggregate_signals([signal])

        assert result.primary_jurisdiction == JurisdictionCode.US
        assert result.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_aggregate_signals_multiple(self, detector: JurisdictionDetector):
        """Test aggregation with multiple signals."""
        signals = [
            detector.detect_from_phone("+1-555-123-4567"),
            detector.detect_from_address("New York, NY 10001, USA"),
            detector.declare_jurisdiction("p1", JurisdictionCode.US),
        ]

        result = detector.aggregate_signals([s for s in signals if s is not None])

        assert result.primary_jurisdiction == JurisdictionCode.US
        assert result.confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

    def test_aggregate_signals_kyc_verified(self, detector: JurisdictionDetector):
        """Test that KYC verification gives highest confidence."""
        signals = [
            detector.detect_from_phone("+44 20 7946 0958"),  # UK
            detector.verify_from_kyc("p1", JurisdictionCode.GB, "Onfido"),
        ]

        result = detector.aggregate_signals([s for s in signals if s is not None])

        assert result.primary_jurisdiction == JurisdictionCode.GB
        assert result.confidence_level == ConfidenceLevel.VERIFIED

    def test_aggregate_signals_empty(self, detector: JurisdictionDetector):
        """Test aggregation with no signals."""
        result = detector.aggregate_signals([])

        assert result.primary_jurisdiction == JurisdictionCode.XX
        assert result.confidence_level == ConfidenceLevel.LOW

    def test_register_participant(self, detector: JurisdictionDetector):
        """Test participant registration."""
        signals = [detector.declare_jurisdiction("p1", JurisdictionCode.JP)]
        profile = detector.register_participant("p1", "0x123", signals)

        assert profile.participant_id == "p1"
        assert profile.wallet_address == "0x123"
        assert profile.primary_jurisdiction == JurisdictionCode.JP

    def test_set_kyc_verification(self, detector: JurisdictionDetector):
        """Test setting KYC verification for participant."""
        detector.register_participant("p1")
        profile = detector.set_kyc_verification("p1", JurisdictionCode.AU, "IDnow")

        assert profile.kyc_verified
        assert profile.kyc_jurisdiction == JurisdictionCode.AU
        assert profile.primary_jurisdiction == JurisdictionCode.AU

    def test_get_region(self, detector: JurisdictionDetector):
        """Test region lookup."""
        assert detector.get_region(JurisdictionCode.US) == JurisdictionRegion.NORTH_AMERICA
        assert detector.get_region(JurisdictionCode.DE) == JurisdictionRegion.EUROPEAN_UNION
        assert detector.get_region(JurisdictionCode.GB) == JurisdictionRegion.EUROPE_NON_EU
        assert detector.get_region(JurisdictionCode.SG) == JurisdictionRegion.ASIA_PACIFIC
        assert detector.get_region(JurisdictionCode.KY) == JurisdictionRegion.OFFSHORE
        assert detector.get_region(JurisdictionCode.KP) == JurisdictionRegion.RESTRICTED

    def test_is_restricted(self, detector: JurisdictionDetector):
        """Test restricted jurisdiction check."""
        is_restricted, reason = detector.is_restricted(JurisdictionCode.KP)
        assert is_restricted
        assert "OFAC" in reason

        is_restricted, reason = detector.is_restricted(JurisdictionCode.US)
        assert not is_restricted
        assert reason is None

        # Partially restricted
        is_restricted, reason = detector.is_restricted(JurisdictionCode.RU)
        assert not is_restricted  # Not fully restricted
        assert "sanctions" in reason.lower()

    def test_get_eu_jurisdictions(self, detector: JurisdictionDetector):
        """Test EU jurisdiction list."""
        eu = detector.get_eu_jurisdictions()

        assert JurisdictionCode.DE in eu
        assert JurisdictionCode.FR in eu
        assert JurisdictionCode.NL in eu
        assert JurisdictionCode.GB not in eu  # Brexit
        assert JurisdictionCode.US not in eu

    def test_are_compatible(self, detector: JurisdictionDetector):
        """Test jurisdiction compatibility check."""
        # US-UK compatible
        compatible, reason = detector.are_compatible(JurisdictionCode.US, JurisdictionCode.GB)
        assert compatible

        # EU-EU highly compatible
        compatible, reason = detector.are_compatible(JurisdictionCode.DE, JurisdictionCode.FR)
        assert compatible

        # Restricted jurisdiction
        compatible, reason = detector.are_compatible(JurisdictionCode.US, JurisdictionCode.KP)
        assert not compatible
        assert "restricted" in reason.lower()


# ============ Compliance Rules Tests ============


class TestJurisdictionRulesRegistry:
    """Tests for JurisdictionRulesRegistry."""

    @pytest.fixture
    def registry(self) -> JurisdictionRulesRegistry:
        return create_rules_registry()

    def test_get_us_rules(self, registry: JurisdictionRulesRegistry):
        """Test US jurisdiction rules."""
        rules = registry.get_rules(JurisdictionCode.US)

        assert rules is not None
        assert rules.name == "United States"
        assert rules.region == JurisdictionRegion.NORTH_AMERICA
        assert rules.contract_law == ContractLaw.COMMON_LAW
        assert RegulatoryFramework.SEC_REG_D_506C in rules.regulatory_frameworks
        assert rules.investor.accreditation_required
        assert rules.investor.holding_period_days == 365

    def test_get_uk_rules(self, registry: JurisdictionRulesRegistry):
        """Test UK jurisdiction rules."""
        rules = registry.get_rules(JurisdictionCode.GB)

        assert rules is not None
        assert rules.name == "United Kingdom"
        assert RegulatoryFramework.UK_FCA in rules.regulatory_frameworks
        assert rules.disclosure.prospectus_required
        assert rules.investor.cooling_off_period_days == 14

    def test_get_germany_rules(self, registry: JurisdictionRulesRegistry):
        """Test Germany (EU) jurisdiction rules."""
        rules = registry.get_rules(JurisdictionCode.DE)

        assert rules is not None
        assert rules.region == JurisdictionRegion.EUROPEAN_UNION
        assert rules.contract_law == ContractLaw.CIVIL_LAW
        assert RegulatoryFramework.EU_MICA in rules.regulatory_frameworks
        assert RegulatoryFramework.EU_GDPR in rules.regulatory_frameworks
        assert rules.tax.vat_applicable

    def test_get_singapore_rules(self, registry: JurisdictionRulesRegistry):
        """Test Singapore jurisdiction rules."""
        rules = registry.get_rules(JurisdictionCode.SG)

        assert rules is not None
        assert RegulatoryFramework.SG_MAS in rules.regulatory_frameworks
        assert rules.investor.accreditation_required
        assert rules.investor.minimum_investment == Decimal("200000")
        assert rules.contract.dispute_resolution == DisputeResolution.ARBITRATION_SIAC

    def test_get_cayman_rules(self, registry: JurisdictionRulesRegistry):
        """Test Cayman Islands (offshore) rules."""
        rules = registry.get_rules(JurisdictionCode.KY)

        assert rules is not None
        assert rules.region == JurisdictionRegion.OFFSHORE
        assert rules.tax.withholding_rate == Decimal("0")
        assert rules.tax.capital_gains_rate == Decimal("0")
        assert not rules.disclosure.prospectus_required

    def test_get_restricted_rules(self, registry: JurisdictionRulesRegistry):
        """Test restricted jurisdiction rules."""
        rules = registry.get_rules(JurisdictionCode.KP)

        assert rules is not None
        assert rules.is_restricted
        assert "OFAC" in rules.restriction_reason
        assert "All transactions" in rules.blocked_activities

    def test_get_international_rules(self, registry: JurisdictionRulesRegistry):
        """Test international default rules."""
        rules = registry.get_rules(JurisdictionCode.INT)

        assert rules is not None
        assert rules.contract.governing_law == "UNIDROIT Principles"
        assert rules.contract.dispute_resolution == DisputeResolution.ARBITRATION_ICC

    def test_get_rules_for_region(self, registry: JurisdictionRulesRegistry):
        """Test getting all rules for a region."""
        eu_rules = registry.get_rules_for_region(JurisdictionRegion.EUROPEAN_UNION)

        assert len(eu_rules) > 0
        assert all(r.region == JurisdictionRegion.EUROPEAN_UNION for r in eu_rules)

    def test_get_compatible_rules(self, registry: JurisdictionRulesRegistry):
        """Test merged rules for cross-border transactions."""
        merged = registry.get_compatible_rules(JurisdictionCode.US, JurisdictionCode.GB)

        assert merged["compatible"]
        # US requires accreditation, UK requires prospectus above threshold
        assert merged["accreditation_required"]  # US requires
        assert merged["prospectus_required"]  # UK requires
        # Take longer holding period
        assert merged["holding_period_days"] == 365  # US has 365

    def test_get_compatible_rules_restricted(self, registry: JurisdictionRulesRegistry):
        """Test merged rules with restricted jurisdiction."""
        merged = registry.get_compatible_rules(JurisdictionCode.US, JurisdictionCode.IR)

        assert not merged["compatible"]
        assert "Restricted" in merged["reason"]

    def test_check_transaction_compliance_success(self, registry: JurisdictionRulesRegistry):
        """Test successful transaction compliance check."""
        result = registry.check_transaction_compliance(
            from_jurisdiction=JurisdictionCode.US,
            to_jurisdiction=JurisdictionCode.GB,
            transaction_type="license",
            amount=Decimal("100000"),
        )

        assert result["compliant"]
        assert len(result["issues"]) == 0
        # Should have required actions (e.g., withholding tax for US source)
        assert len(result["required_actions"]) > 0
        assert any(
            "withhold" in a.lower() or "tax" in a.lower() for a in result["required_actions"]
        )

    def test_check_transaction_compliance_restricted(self, registry: JurisdictionRulesRegistry):
        """Test transaction compliance with restricted jurisdiction."""
        result = registry.check_transaction_compliance(
            from_jurisdiction=JurisdictionCode.US,
            to_jurisdiction=JurisdictionCode.KP,
            transaction_type="license",
        )

        assert not result["compliant"]
        assert any("restricted" in i.lower() for i in result["issues"])

    def test_ip_law_requirements(self, registry: JurisdictionRulesRegistry):
        """Test IP law requirements in rules."""
        us_rules = registry.get_rules(JurisdictionCode.US)

        assert us_rules.ip_law.first_to_file
        assert us_rules.ip_law.grace_period_months == 12
        assert us_rules.ip_law.patent_term_years == 20
        assert not us_rules.ip_law.moral_rights_recognized  # Limited in US
        assert us_rules.ip_law.work_for_hire_doctrine
        assert IPLawTreaty.PCT in us_rules.ip_law.treaties


# ============ Legal Template Tests ============


class TestLegalTemplateLibrary:
    """Tests for LegalTemplateLibrary."""

    @pytest.fixture
    def library(self) -> LegalTemplateLibrary:
        return create_template_library()

    def test_get_template(self, library: LegalTemplateLibrary):
        """Test getting a specific template."""
        template = library.get_template("gov_law_us_de")

        assert template is not None
        assert template.template_type == TemplateType.GOVERNING_LAW
        assert template.jurisdiction == "US"
        assert "Delaware" in template.title

    def test_get_templates_by_type(self, library: LegalTemplateLibrary):
        """Test getting templates by type."""
        templates = library.get_templates_by_type(TemplateType.GOVERNING_LAW)

        assert len(templates) > 0
        assert all(t.template_type == TemplateType.GOVERNING_LAW for t in templates)

    def test_get_templates_by_jurisdiction(self, library: LegalTemplateLibrary):
        """Test getting templates for a jurisdiction."""
        templates = library.get_templates_by_jurisdiction("US")

        assert len(templates) > 0
        # Should include US-specific and international templates
        jurisdictions = {t.jurisdiction for t in templates}
        assert "US" in jurisdictions or "INT" in jurisdictions

    def test_render_template_simple(self, library: LegalTemplateLibrary):
        """Test rendering a template without variables."""
        clause = library.render_template("gov_law_us_de", {})

        assert clause.template_id == "gov_law_us_de"
        assert "Delaware" in clause.content
        assert clause.language == LanguageCode.EN

    def test_render_template_with_variables(self, library: LegalTemplateLibrary):
        """Test rendering a template with variables."""
        clause = library.render_template(
            "disp_arb_icc",
            {
                "number_of_arbitrators": "three",
                "arbitration_seat": "London, United Kingdom",
                "arbitration_language": "English",
            },
        )

        assert "three" in clause.content
        assert "London" in clause.content
        assert "English" in clause.content

    def test_render_template_default_values(self, library: LegalTemplateLibrary):
        """Test rendering with default values."""
        clause = library.render_template(
            "disp_arb_icc",
            {
                "arbitration_seat": "Singapore",
            },
        )

        # Should use defaults for number_of_arbitrators and arbitration_language
        assert "Singapore" in clause.content
        assert "one" in clause.content or "English" in clause.content

    def test_render_template_missing_required(self, library: LegalTemplateLibrary):
        """Test that missing required variables raise error."""
        # license_grant_exclusive has required variables without defaults
        with pytest.raises(ValueError):
            library.render_template("license_grant_exclusive", {})

    def test_render_template_validation(self, library: LegalTemplateLibrary):
        """Test variable validation patterns."""
        # Smart contract template requires valid contract address
        with pytest.raises(ValueError) as exc_info:
            library.render_template(
                "smart_contract_integration",
                {
                    "contract_address": "invalid-address",
                    "blockchain_network": "Ethereum",
                    "token_id": "1",
                },
            )

        assert "pattern" in str(exc_info.value).lower()

    def test_render_smart_contract_template(self, library: LegalTemplateLibrary):
        """Test smart contract integration template."""
        clause = library.render_template(
            "smart_contract_integration",
            {
                "contract_address": "0x1234567890123456789012345678901234567890",
                "blockchain_network": "Ethereum",
                "token_id": "42",
            },
        )

        assert "0x1234567890123456789012345678901234567890" in clause.content
        assert "Ethereum" in clause.content
        assert "42" in clause.content
        assert "royalty" in clause.content.lower()

    def test_render_gdpr_template(self, library: LegalTemplateLibrary):
        """Test GDPR data protection template."""
        clause = library.render_template(
            "data_protection_gdpr",
            {
                "licensor_data_types": "user contact information",
                "licensee_data_types": "end user behavior data",
            },
        )

        assert "GDPR" in clause.content
        assert "user contact information" in clause.content
        assert "end user behavior data" in clause.content
        assert clause.jurisdiction == "EU"

    def test_render_tax_withholding_template(self, library: LegalTemplateLibrary):
        """Test US tax withholding template."""
        clause = library.render_template("tax_withholding_us", {})

        assert "W-9" in clause.content
        assert "W-8BEN" in clause.content
        assert "withholding" in clause.content.lower()

    def test_render_aml_kyc_template(self, library: LegalTemplateLibrary):
        """Test AML/KYC template."""
        clause = library.render_template("aml_kyc", {})

        assert "OFAC" in clause.content
        assert "sanctions" in clause.content.lower()
        assert "anti-money laundering" in clause.content.lower()

    def test_build_wrapper_us(self, library: LegalTemplateLibrary):
        """Test building a complete wrapper for US jurisdiction."""
        clauses = library.build_wrapper(
            jurisdiction="US",
            template_types=[
                TemplateType.GOVERNING_LAW,
                TemplateType.DISPUTE_RESOLUTION,
                TemplateType.TAX_PROVISIONS,
                TemplateType.ANTI_MONEY_LAUNDERING,
            ],
            variables={
                "arbitration_city": "New York",
                "arbitration_state": "New York",
            },
        )

        assert len(clauses) >= 3  # Should have most templates

        # Check we got US-specific templates where available
        template_types = {c.template_type for c in clauses}
        assert TemplateType.GOVERNING_LAW in template_types
        assert TemplateType.DISPUTE_RESOLUTION in template_types

    def test_build_wrapper_international(self, library: LegalTemplateLibrary):
        """Test building a wrapper with international templates."""
        clauses = library.build_wrapper(
            jurisdiction="INT",
            template_types=[
                TemplateType.GOVERNING_LAW,
                TemplateType.DISPUTE_RESOLUTION,
                TemplateType.LICENSE_GRANT,
            ],
            variables={
                "governing_jurisdiction": "Switzerland",
                "number_of_arbitrators": "one",
                "arbitration_seat": "Geneva, Switzerland",
                "arbitration_language": "English",
                "licensed_ip_description": "Software Library v2.0",
                "territory": "worldwide",
                "term_years": "5",
                "renewal_years": "1",
                "notice_days": "60",
            },
        )

        assert len(clauses) >= 2

        # Check content
        content = " ".join(c.content for c in clauses)
        assert "Switzerland" in content or "ICC" in content

    def test_register_custom_template(self, library: LegalTemplateLibrary):
        """Test registering a custom template."""
        custom = LegalTemplate(
            template_id="custom_nl_test",
            template_type=TemplateType.GOVERNING_LAW,
            jurisdiction="NL",
            language=LanguageCode.EN,
            title="Governing Law (Netherlands)",
            content="This Agreement shall be governed by Dutch law.",
            variables=[],
        )

        library.register_template(custom)

        retrieved = library.get_template("custom_nl_test")
        assert retrieved is not None
        assert retrieved.jurisdiction == "NL"

    def test_list_all_templates(self, library: LegalTemplateLibrary):
        """Test listing all templates."""
        templates = library.list_templates()

        assert len(templates) > 0

        # Should have variety of template types
        template_types = {t.template_type for t in templates}
        assert len(template_types) >= 5


# ============ Integration Tests ============


class TestJurisdictionIntegration:
    """Integration tests for the complete jurisdiction-aware wrapper system."""

    def test_full_jurisdiction_workflow(self):
        """Test complete workflow: detection -> rules -> templates."""
        # Setup
        detector = create_jurisdiction_detector()
        registry = create_rules_registry()
        library = create_template_library()

        # 1. Detect participant jurisdictions
        licensor_signals = [
            detector.detect_from_phone("+1-415-555-1234"),
            detector.detect_from_address("San Francisco, CA 94105, USA"),
            detector.verify_from_kyc("licensor", JurisdictionCode.US, "Jumio"),
        ]
        licensor_result = detector.aggregate_signals([s for s in licensor_signals if s])

        licensee_signals = [
            detector.detect_from_phone("+44 20 7946 0958"),
            detector.verify_from_kyc("licensee", JurisdictionCode.GB, "Onfido"),
        ]
        licensee_result = detector.aggregate_signals([s for s in licensee_signals if s])

        assert licensor_result.primary_jurisdiction == JurisdictionCode.US
        assert licensee_result.primary_jurisdiction == JurisdictionCode.GB

        # 2. Get compliance rules
        us_rules = registry.get_rules(JurisdictionCode.US)
        gb_rules = registry.get_rules(JurisdictionCode.GB)

        assert us_rules is not None
        assert gb_rules is not None

        # 3. Check transaction compliance
        compliance = registry.check_transaction_compliance(
            from_jurisdiction=JurisdictionCode.US,
            to_jurisdiction=JurisdictionCode.GB,
            transaction_type="license",
            amount=Decimal("500000"),
        )

        assert compliance["compliant"]

        # 4. Get merged requirements
        merged = registry.get_compatible_rules(JurisdictionCode.US, JurisdictionCode.GB)

        assert merged["compatible"]

        # 5. Build legal wrapper with appropriate templates
        clauses = library.build_wrapper(
            jurisdiction="INT",  # Cross-border uses international
            template_types=[
                TemplateType.GOVERNING_LAW,
                TemplateType.DISPUTE_RESOLUTION,
                TemplateType.LICENSE_GRANT,
                TemplateType.TAX_PROVISIONS,
                TemplateType.ANTI_MONEY_LAUNDERING,
            ],
            variables={
                "governing_jurisdiction": "England and Wales",
                "number_of_arbitrators": "three",
                "arbitration_seat": "London, United Kingdom",
                "arbitration_language": "English",
                "licensed_ip_description": "Patent Portfolio ABC-123",
                "territory": "United Kingdom",
                "term_end_date": "December 31, 2035",  # Required for license template
                "term_years": "10",
                "renewal_years": "5",
                "notice_days": "90",
            },
        )

        # Expect at least 3 clauses (some templates may not have INT versions)
        assert len(clauses) >= 3

        # Verify content covers key areas
        all_content = " ".join(c.content for c in clauses)
        assert "arbitration" in all_content.lower()
        assert "license" in all_content.lower()

    def test_restricted_jurisdiction_blocked(self):
        """Test that restricted jurisdictions are properly blocked."""
        detector = create_jurisdiction_detector()
        registry = create_rules_registry()

        # Attempt transaction involving restricted jurisdiction
        compliance = registry.check_transaction_compliance(
            from_jurisdiction=JurisdictionCode.US,
            to_jurisdiction=JurisdictionCode.IR,  # Iran - restricted
            transaction_type="license",
        )

        assert not compliance["compliant"]
        assert any("restricted" in issue.lower() for issue in compliance["issues"])

        # Check compatibility
        compatible, reason = detector.are_compatible(JurisdictionCode.US, JurisdictionCode.KP)
        assert not compatible
        assert "restricted" in reason.lower()

    def test_eu_internal_transaction(self):
        """Test EU internal transaction with single market benefits."""
        detector = create_jurisdiction_detector()
        registry = create_rules_registry()

        # Get EU jurisdictions
        eu_jurisdictions = detector.get_eu_jurisdictions()
        assert JurisdictionCode.DE in eu_jurisdictions
        assert JurisdictionCode.FR in eu_jurisdictions

        # Check compatibility within EU
        compatible, reason = detector.are_compatible(JurisdictionCode.DE, JurisdictionCode.FR)
        assert compatible

        # Check compliance
        compliance = registry.check_transaction_compliance(
            from_jurisdiction=JurisdictionCode.DE,
            to_jurisdiction=JurisdictionCode.FR,
            transaction_type="license",
        )

        assert compliance["compliant"]

    def test_offshore_jurisdiction_handling(self):
        """Test offshore jurisdiction special handling."""
        registry = create_rules_registry()

        # Get Cayman Islands rules
        ky_rules = registry.get_rules(JurisdictionCode.KY)

        assert ky_rules is not None
        assert ky_rules.region == JurisdictionRegion.OFFSHORE
        assert ky_rules.tax.withholding_rate == Decimal("0")
        assert ky_rules.tax.capital_gains_rate == Decimal("0")
        assert not ky_rules.tax.vat_applicable

        # US to Cayman transaction
        compliance = registry.check_transaction_compliance(
            from_jurisdiction=JurisdictionCode.US,
            to_jurisdiction=JurisdictionCode.KY,
            transaction_type="license",
        )

        # Should be compliant but with US withholding requirements
        assert compliance["compliant"]
        assert any("withhold" in a.lower() for a in compliance["required_actions"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
