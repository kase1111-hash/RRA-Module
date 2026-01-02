# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Per-Jurisdiction Compliance Rules module for RRA.

Provides jurisdiction-specific:
- Regulatory requirements
- IP law considerations
- Contract law requirements
- Tax implications
- Disclosure requirements
- Dispute resolution rules
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Any

from .jurisdiction import JurisdictionCode, JurisdictionRegion


class RegulatoryFramework(Enum):
    """Applicable regulatory frameworks by jurisdiction."""

    # US Regulations
    SEC_REG_D_506B = "sec_reg_d_506b"  # Regulation D 506(b)
    SEC_REG_D_506C = "sec_reg_d_506c"  # Regulation D 506(c)
    SEC_REG_S = "sec_reg_s"  # Regulation S (offshore)
    SEC_REG_A_PLUS = "sec_reg_a_plus"  # Regulation A+
    SEC_REG_CF = "sec_reg_cf"  # Regulation Crowdfunding
    FinCEN_MSB = "fincen_msb"  # Money Services Business

    # EU Regulations
    EU_MIFID_II = "eu_mifid_ii"  # Markets in Financial Instruments
    EU_MICA = "eu_mica"  # Markets in Crypto-Assets
    EU_PROSPECTUS = "eu_prospectus"  # Prospectus Regulation
    EU_GDPR = "eu_gdpr"  # General Data Protection
    EU_EMIR = "eu_emir"  # European Market Infrastructure

    # UK Regulations
    UK_FCA = "uk_fca"  # Financial Conduct Authority
    UK_RAO = "uk_rao"  # Regulated Activities Order

    # Asian Regulations
    SG_MAS = "sg_mas"  # Monetary Authority of Singapore
    SG_PSA = "sg_psa"  # Payment Services Act
    HK_SFC = "hk_sfc"  # Securities and Futures Commission
    JP_FSA = "jp_fsa"  # Financial Services Agency
    JP_JFSA = "jp_jfsa"  # Japan Virtual Currency Act

    # Swiss Regulations
    CH_FINMA = "ch_finma"  # FINMA regulatory framework

    # Offshore
    KY_CIMA = "ky_cima"  # Cayman Islands Monetary Authority
    VG_FSC = "vg_fsc"  # BVI Financial Services Commission

    # None/Unknown
    NONE = "none"


class ContractLaw(Enum):
    """Contract law systems by jurisdiction."""

    COMMON_LAW = "common_law"  # US, UK, CA, AU, etc.
    CIVIL_LAW = "civil_law"  # EU, Latin America, etc.
    MIXED = "mixed"  # Scotland, Quebec, etc.
    SHARIA = "sharia"  # Islamic law jurisdictions
    CUSTOMARY = "customary"  # Traditional/customary


class DisputeResolution(Enum):
    """Dispute resolution mechanisms."""

    LITIGATION = "litigation"  # Court proceedings
    ARBITRATION_ICC = "arbitration_icc"  # ICC Arbitration
    ARBITRATION_LCIA = "arbitration_lcia"  # London Court
    ARBITRATION_AAA = "arbitration_aaa"  # American Arbitration
    ARBITRATION_SIAC = "arbitration_siac"  # Singapore International
    ARBITRATION_HKIAC = "arbitration_hkiac"  # Hong Kong
    ARBITRATION_JCAA = "arbitration_jcaa"  # Japan Commercial
    MEDIATION = "mediation"  # Mediation first
    SMART_CONTRACT = "smart_contract"  # On-chain resolution


class IPLawTreaty(Enum):
    """Relevant IP law treaties."""

    PARIS_CONVENTION = "paris_convention"
    BERNE_CONVENTION = "berne_convention"
    TRIPS = "trips"
    PCT = "pct"  # Patent Cooperation Treaty
    MADRID_PROTOCOL = "madrid_protocol"  # Trademark
    WIPO_COPYRIGHT = "wipo_copyright"
    WIPO_PERFORMERS = "wipo_performers"


@dataclass
class TaxRequirements:
    """Tax requirements for a jurisdiction."""

    withholding_rate: Decimal  # Default withholding tax rate
    has_treaty_network: bool  # Has tax treaties
    treaty_countries: List[JurisdictionCode] = field(default_factory=list)
    vat_applicable: bool = False
    vat_rate: Optional[Decimal] = None
    capital_gains_rate: Optional[Decimal] = None
    royalty_tax_rate: Optional[Decimal] = None
    requires_tax_id: bool = True
    tax_forms: List[str] = field(default_factory=list)


@dataclass
class DisclosureRequirements:
    """Disclosure requirements for a jurisdiction."""

    prospectus_required: bool = False
    prospectus_threshold: Optional[Decimal] = None  # Amount threshold
    risk_disclosure_required: bool = True
    fee_disclosure_required: bool = True
    investor_suitability: bool = False
    annual_reporting: bool = False
    beneficial_ownership: bool = True
    aml_disclosure: bool = True
    required_documents: List[str] = field(default_factory=list)


@dataclass
class InvestorRequirements:
    """Investor eligibility requirements."""

    accreditation_required: bool = False
    accreditation_type: Optional[str] = None  # "net_worth", "income", "professional"
    minimum_investment: Optional[Decimal] = None
    maximum_investors: Optional[int] = None
    cooling_off_period_days: int = 0
    holding_period_days: int = 0
    resale_restrictions: List[str] = field(default_factory=list)


@dataclass
class ContractRequirements:
    """Contract-specific requirements."""

    language: str = "en"
    governing_law: str = ""
    choice_of_forum: str = ""
    dispute_resolution: DisputeResolution = DisputeResolution.ARBITRATION_ICC
    arbitration_seat: Optional[str] = None
    force_majeure_required: bool = True
    limitation_of_liability: bool = True
    indemnification: bool = True
    confidentiality: bool = True
    assignment_restrictions: bool = False
    electronic_signatures_valid: bool = True
    notarization_required: bool = False
    witness_required: bool = False
    specific_clauses: List[str] = field(default_factory=list)


@dataclass
class IPLawRequirements:
    """IP law-specific requirements."""

    registration_required: bool = True
    recordation_assignment: bool = True
    moral_rights_recognized: bool = True
    work_for_hire_doctrine: bool = False
    first_to_file: bool = True  # vs first-to-invent
    grace_period_months: int = 0
    patent_term_years: int = 20
    trademark_renewal_years: int = 10
    copyright_term: str = "life+70"
    compulsory_licensing: bool = False
    parallel_imports_allowed: bool = False
    treaties: List[IPLawTreaty] = field(default_factory=list)


@dataclass
class JurisdictionRules:
    """Complete compliance rules for a jurisdiction."""

    jurisdiction: JurisdictionCode
    region: JurisdictionRegion
    name: str

    # Regulatory
    regulatory_frameworks: List[RegulatoryFramework] = field(default_factory=list)
    license_required: bool = False
    license_type: Optional[str] = None
    registration_required: bool = False

    # Legal system
    contract_law: ContractLaw = ContractLaw.COMMON_LAW

    # Requirements
    tax: TaxRequirements = field(
        default_factory=lambda: TaxRequirements(
            withholding_rate=Decimal("0"), has_treaty_network=False
        )
    )
    disclosure: DisclosureRequirements = field(default_factory=DisclosureRequirements)
    investor: InvestorRequirements = field(default_factory=InvestorRequirements)
    contract: ContractRequirements = field(default_factory=ContractRequirements)
    ip_law: IPLawRequirements = field(default_factory=IPLawRequirements)

    # Restrictions
    is_restricted: bool = False
    restriction_reason: Optional[str] = None
    blocked_activities: List[str] = field(default_factory=list)

    # Metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"


class JurisdictionRulesRegistry:
    """
    Registry of compliance rules by jurisdiction.

    Provides jurisdiction-specific rules for:
    - Regulatory compliance
    - Contract requirements
    - Tax obligations
    - IP law considerations
    """

    def __init__(self):
        self._rules: Dict[JurisdictionCode, JurisdictionRules] = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default rules for major jurisdictions."""

        # United States
        self._rules[JurisdictionCode.US] = JurisdictionRules(
            jurisdiction=JurisdictionCode.US,
            region=JurisdictionRegion.NORTH_AMERICA,
            name="United States",
            regulatory_frameworks=[
                RegulatoryFramework.SEC_REG_D_506C,
                RegulatoryFramework.SEC_REG_S,
                RegulatoryFramework.FinCEN_MSB,
            ],
            license_required=True,
            license_type="State money transmitter licenses or federal exemption",
            contract_law=ContractLaw.COMMON_LAW,
            tax=TaxRequirements(
                withholding_rate=Decimal("0.30"),
                has_treaty_network=True,
                treaty_countries=[
                    JurisdictionCode.GB,
                    JurisdictionCode.DE,
                    JurisdictionCode.FR,
                    JurisdictionCode.JP,
                    JurisdictionCode.CA,
                    JurisdictionCode.AU,
                ],
                vat_applicable=False,
                capital_gains_rate=Decimal("0.20"),
                royalty_tax_rate=Decimal("0.30"),
                tax_forms=["W-8BEN", "W-9", "Form 1099"],
            ),
            disclosure=DisclosureRequirements(
                prospectus_required=False,  # Exempt under Reg D
                risk_disclosure_required=True,
                fee_disclosure_required=True,
                investor_suitability=True,
                annual_reporting=True,
                required_documents=["PPM", "Subscription Agreement", "Operating Agreement"],
            ),
            investor=InvestorRequirements(
                accreditation_required=True,
                accreditation_type="net_worth_or_income",
                holding_period_days=365,
                resale_restrictions=["Rule 144 holding period", "Accredited investors only"],
            ),
            contract=ContractRequirements(
                language="en",
                governing_law="State of Delaware",
                choice_of_forum="Delaware Chancery Court",
                dispute_resolution=DisputeResolution.ARBITRATION_AAA,
                arbitration_seat="New York, NY",
                electronic_signatures_valid=True,
                specific_clauses=[
                    "ERISA compliance (if applicable)",
                    "Blue sky notice",
                    "Anti-money laundering provisions",
                ],
            ),
            ip_law=IPLawRequirements(
                registration_required=True,
                recordation_assignment=True,
                moral_rights_recognized=False,  # Limited in US
                work_for_hire_doctrine=True,
                first_to_file=True,
                grace_period_months=12,  # For patents
                patent_term_years=20,
                trademark_renewal_years=10,
                copyright_term="life+70 or 95/120 years for work-for-hire",
                treaties=[
                    IPLawTreaty.PARIS_CONVENTION,
                    IPLawTreaty.BERNE_CONVENTION,
                    IPLawTreaty.TRIPS,
                    IPLawTreaty.PCT,
                    IPLawTreaty.MADRID_PROTOCOL,
                ],
            ),
        )

        # United Kingdom
        self._rules[JurisdictionCode.GB] = JurisdictionRules(
            jurisdiction=JurisdictionCode.GB,
            region=JurisdictionRegion.EUROPE_NON_EU,
            name="United Kingdom",
            regulatory_frameworks=[
                RegulatoryFramework.UK_FCA,
                RegulatoryFramework.UK_RAO,
            ],
            license_required=True,
            license_type="FCA authorization for regulated activities",
            contract_law=ContractLaw.COMMON_LAW,
            tax=TaxRequirements(
                withholding_rate=Decimal("0.20"),
                has_treaty_network=True,
                treaty_countries=[
                    JurisdictionCode.US,
                    JurisdictionCode.DE,
                    JurisdictionCode.FR,
                ],
                vat_applicable=True,
                vat_rate=Decimal("0.20"),
                capital_gains_rate=Decimal("0.20"),
                royalty_tax_rate=Decimal("0.20"),
                tax_forms=["Self-assessment", "CT600"],
            ),
            disclosure=DisclosureRequirements(
                prospectus_required=True,
                prospectus_threshold=Decimal("8000000"),  # EUR 8M equivalent
                risk_disclosure_required=True,
                investor_suitability=True,
                required_documents=["Key Information Document", "Terms and Conditions"],
            ),
            investor=InvestorRequirements(
                accreditation_required=False,
                cooling_off_period_days=14,
            ),
            contract=ContractRequirements(
                language="en",
                governing_law="Laws of England and Wales",
                choice_of_forum="Courts of England and Wales",
                dispute_resolution=DisputeResolution.ARBITRATION_LCIA,
                arbitration_seat="London",
                electronic_signatures_valid=True,
            ),
            ip_law=IPLawRequirements(
                registration_required=True,
                moral_rights_recognized=True,
                work_for_hire_doctrine=False,
                first_to_file=True,
                patent_term_years=20,
                copyright_term="life+70",
                treaties=[
                    IPLawTreaty.PARIS_CONVENTION,
                    IPLawTreaty.BERNE_CONVENTION,
                    IPLawTreaty.TRIPS,
                ],
            ),
        )

        # Germany (representative for EU)
        self._rules[JurisdictionCode.DE] = JurisdictionRules(
            jurisdiction=JurisdictionCode.DE,
            region=JurisdictionRegion.EUROPEAN_UNION,
            name="Germany",
            regulatory_frameworks=[
                RegulatoryFramework.EU_MIFID_II,
                RegulatoryFramework.EU_MICA,
                RegulatoryFramework.EU_PROSPECTUS,
                RegulatoryFramework.EU_GDPR,
            ],
            license_required=True,
            license_type="BaFin authorization",
            contract_law=ContractLaw.CIVIL_LAW,
            tax=TaxRequirements(
                withholding_rate=Decimal("0.2638"),  # 26.375% with solidarity surcharge
                has_treaty_network=True,
                treaty_countries=[JurisdictionCode.US, JurisdictionCode.GB],
                vat_applicable=True,
                vat_rate=Decimal("0.19"),
                capital_gains_rate=Decimal("0.2638"),
                tax_forms=["Steuerbescheinigung"],
            ),
            disclosure=DisclosureRequirements(
                prospectus_required=True,
                prospectus_threshold=Decimal("8000000"),
                risk_disclosure_required=True,
                investor_suitability=True,
                required_documents=["Prospectus", "Key Investor Document", "GDPR Notice"],
            ),
            investor=InvestorRequirements(
                accreditation_required=False,
                cooling_off_period_days=14,
            ),
            contract=ContractRequirements(
                language="de",
                governing_law="Laws of Germany",
                choice_of_forum="Courts of Frankfurt am Main",
                dispute_resolution=DisputeResolution.ARBITRATION_ICC,
                arbitration_seat="Frankfurt",
                force_majeure_required=True,
                specific_clauses=[
                    "GDPR data processing agreement",
                    "Consumer protection provisions",
                ],
            ),
            ip_law=IPLawRequirements(
                registration_required=True,
                moral_rights_recognized=True,
                work_for_hire_doctrine=False,
                first_to_file=True,
                patent_term_years=20,
                copyright_term="life+70",
                compulsory_licensing=True,
                treaties=[
                    IPLawTreaty.PARIS_CONVENTION,
                    IPLawTreaty.BERNE_CONVENTION,
                    IPLawTreaty.TRIPS,
                    IPLawTreaty.PCT,
                ],
            ),
        )

        # Singapore
        self._rules[JurisdictionCode.SG] = JurisdictionRules(
            jurisdiction=JurisdictionCode.SG,
            region=JurisdictionRegion.ASIA_PACIFIC,
            name="Singapore",
            regulatory_frameworks=[
                RegulatoryFramework.SG_MAS,
                RegulatoryFramework.SG_PSA,
            ],
            license_required=True,
            license_type="MAS license for digital payment tokens",
            contract_law=ContractLaw.COMMON_LAW,
            tax=TaxRequirements(
                withholding_rate=Decimal("0.17"),
                has_treaty_network=True,
                treaty_countries=[JurisdictionCode.US, JurisdictionCode.GB, JurisdictionCode.JP],
                vat_applicable=True,
                vat_rate=Decimal("0.08"),  # GST
                capital_gains_rate=Decimal("0"),  # No capital gains tax
                tax_forms=["Form IR8A"],
            ),
            disclosure=DisclosureRequirements(
                prospectus_required=True,
                prospectus_threshold=Decimal("5000000"),
                risk_disclosure_required=True,
                investor_suitability=True,
            ),
            investor=InvestorRequirements(
                accreditation_required=True,
                accreditation_type="accredited_investor",
                minimum_investment=Decimal("200000"),
            ),
            contract=ContractRequirements(
                language="en",
                governing_law="Laws of Singapore",
                choice_of_forum="Courts of Singapore",
                dispute_resolution=DisputeResolution.ARBITRATION_SIAC,
                arbitration_seat="Singapore",
                electronic_signatures_valid=True,
            ),
            ip_law=IPLawRequirements(
                registration_required=True,
                moral_rights_recognized=True,
                first_to_file=True,
                patent_term_years=20,
                copyright_term="life+70",
                treaties=[
                    IPLawTreaty.PARIS_CONVENTION,
                    IPLawTreaty.BERNE_CONVENTION,
                    IPLawTreaty.TRIPS,
                    IPLawTreaty.PCT,
                ],
            ),
        )

        # Switzerland
        self._rules[JurisdictionCode.CH] = JurisdictionRules(
            jurisdiction=JurisdictionCode.CH,
            region=JurisdictionRegion.EUROPE_NON_EU,
            name="Switzerland",
            regulatory_frameworks=[
                RegulatoryFramework.CH_FINMA,
            ],
            license_required=True,
            license_type="FINMA license for financial services",
            contract_law=ContractLaw.CIVIL_LAW,
            tax=TaxRequirements(
                withholding_rate=Decimal("0.35"),
                has_treaty_network=True,
                treaty_countries=[JurisdictionCode.US, JurisdictionCode.DE, JurisdictionCode.GB],
                vat_applicable=True,
                vat_rate=Decimal("0.077"),
                capital_gains_rate=Decimal("0"),  # Generally no capital gains tax
                tax_forms=["Verrechnungssteuer"],
            ),
            disclosure=DisclosureRequirements(
                prospectus_required=True,
                risk_disclosure_required=True,
            ),
            contract=ContractRequirements(
                language="de",  # Also fr, it
                governing_law="Swiss Law",
                choice_of_forum="Courts of Zurich",
                dispute_resolution=DisputeResolution.ARBITRATION_ICC,
                arbitration_seat="Zurich",
            ),
            ip_law=IPLawRequirements(
                registration_required=True,
                moral_rights_recognized=True,
                first_to_file=True,
                patent_term_years=20,
                copyright_term="life+70",
                treaties=[
                    IPLawTreaty.PARIS_CONVENTION,
                    IPLawTreaty.BERNE_CONVENTION,
                    IPLawTreaty.PCT,
                ],
            ),
        )

        # Cayman Islands
        self._rules[JurisdictionCode.KY] = JurisdictionRules(
            jurisdiction=JurisdictionCode.KY,
            region=JurisdictionRegion.OFFSHORE,
            name="Cayman Islands",
            regulatory_frameworks=[
                RegulatoryFramework.KY_CIMA,
            ],
            license_required=True,
            license_type="CIMA registration",
            contract_law=ContractLaw.COMMON_LAW,
            tax=TaxRequirements(
                withholding_rate=Decimal("0"),
                has_treaty_network=False,
                vat_applicable=False,
                capital_gains_rate=Decimal("0"),
            ),
            disclosure=DisclosureRequirements(
                prospectus_required=False,
                beneficial_ownership=True,
            ),
            investor=InvestorRequirements(
                accreditation_required=False,
            ),
            contract=ContractRequirements(
                language="en",
                governing_law="Laws of the Cayman Islands",
                choice_of_forum="Courts of the Cayman Islands",
                dispute_resolution=DisputeResolution.ARBITRATION_LCIA,
            ),
            ip_law=IPLawRequirements(
                registration_required=False,  # Limited IP registration
                moral_rights_recognized=True,
                treaties=[
                    IPLawTreaty.BERNE_CONVENTION,
                ],
            ),
        )

        # Japan
        self._rules[JurisdictionCode.JP] = JurisdictionRules(
            jurisdiction=JurisdictionCode.JP,
            region=JurisdictionRegion.ASIA_PACIFIC,
            name="Japan",
            regulatory_frameworks=[
                RegulatoryFramework.JP_FSA,
                RegulatoryFramework.JP_JFSA,
            ],
            license_required=True,
            license_type="FSA registration as crypto-asset exchange service provider",
            contract_law=ContractLaw.CIVIL_LAW,
            tax=TaxRequirements(
                withholding_rate=Decimal("0.2042"),
                has_treaty_network=True,
                treaty_countries=[JurisdictionCode.US, JurisdictionCode.GB],
                vat_applicable=True,
                vat_rate=Decimal("0.10"),
                capital_gains_rate=Decimal("0.20"),
            ),
            disclosure=DisclosureRequirements(
                prospectus_required=True,
                risk_disclosure_required=True,
                investor_suitability=True,
            ),
            contract=ContractRequirements(
                language="ja",
                governing_law="Laws of Japan",
                choice_of_forum="Tokyo District Court",
                dispute_resolution=DisputeResolution.ARBITRATION_JCAA,
                arbitration_seat="Tokyo",
            ),
            ip_law=IPLawRequirements(
                registration_required=True,
                moral_rights_recognized=True,
                first_to_file=True,
                grace_period_months=6,
                patent_term_years=20,
                copyright_term="life+70",
                treaties=[
                    IPLawTreaty.PARIS_CONVENTION,
                    IPLawTreaty.BERNE_CONVENTION,
                    IPLawTreaty.TRIPS,
                    IPLawTreaty.PCT,
                ],
            ),
        )

        # Restricted: North Korea
        self._rules[JurisdictionCode.KP] = JurisdictionRules(
            jurisdiction=JurisdictionCode.KP,
            region=JurisdictionRegion.RESTRICTED,
            name="North Korea",
            is_restricted=True,
            restriction_reason="OFAC comprehensive sanctions",
            blocked_activities=["All transactions"],
        )

        # Restricted: Iran
        self._rules[JurisdictionCode.IR] = JurisdictionRules(
            jurisdiction=JurisdictionCode.IR,
            region=JurisdictionRegion.RESTRICTED,
            name="Iran",
            is_restricted=True,
            restriction_reason="OFAC comprehensive sanctions",
            blocked_activities=["All transactions"],
        )

        # International default
        self._rules[JurisdictionCode.INT] = JurisdictionRules(
            jurisdiction=JurisdictionCode.INT,
            region=JurisdictionRegion.INTERNATIONAL,
            name="International",
            contract_law=ContractLaw.COMMON_LAW,
            contract=ContractRequirements(
                language="en",
                governing_law="UNIDROIT Principles",
                dispute_resolution=DisputeResolution.ARBITRATION_ICC,
                arbitration_seat="Paris",
            ),
            ip_law=IPLawRequirements(
                treaties=[
                    IPLawTreaty.PARIS_CONVENTION,
                    IPLawTreaty.BERNE_CONVENTION,
                    IPLawTreaty.TRIPS,
                    IPLawTreaty.PCT,
                ],
            ),
        )

    def get_rules(self, jurisdiction: JurisdictionCode) -> Optional[JurisdictionRules]:
        """Get compliance rules for a jurisdiction."""
        return self._rules.get(jurisdiction)

    def get_all_rules(self) -> Dict[JurisdictionCode, JurisdictionRules]:
        """Get all registered jurisdiction rules."""
        return self._rules.copy()

    def register_rules(self, rules: JurisdictionRules):
        """Register or update rules for a jurisdiction."""
        self._rules[rules.jurisdiction] = rules

    def get_rules_for_region(self, region: JurisdictionRegion) -> List[JurisdictionRules]:
        """Get all rules for a specific region."""
        return [r for r in self._rules.values() if r.region == region]

    def get_compatible_rules(
        self, jurisdiction1: JurisdictionCode, jurisdiction2: JurisdictionCode
    ) -> Dict[str, Any]:
        """
        Get compatible/merged rules for cross-border transactions.

        Returns the more restrictive requirements from each jurisdiction.
        """
        rules1 = self.get_rules(jurisdiction1)
        rules2 = self.get_rules(jurisdiction2)

        if not rules1 or not rules2:
            return {"error": "One or both jurisdictions not found"}

        if rules1.is_restricted or rules2.is_restricted:
            return {
                "compatible": False,
                "reason": f"Restricted jurisdiction: {rules1.restriction_reason or rules2.restriction_reason}",
            }

        # Merge requirements (take more restrictive)
        merged = {
            "compatible": True,
            "jurisdictions": [jurisdiction1.value, jurisdiction2.value],
            # Take more restrictive disclosure
            "prospectus_required": rules1.disclosure.prospectus_required
            or rules2.disclosure.prospectus_required,
            "risk_disclosure_required": rules1.disclosure.risk_disclosure_required
            or rules2.disclosure.risk_disclosure_required,
            # Take more restrictive investor requirements
            "accreditation_required": rules1.investor.accreditation_required
            or rules2.investor.accreditation_required,
            "holding_period_days": max(
                rules1.investor.holding_period_days, rules2.investor.holding_period_days
            ),
            "cooling_off_period_days": max(
                rules1.investor.cooling_off_period_days, rules2.investor.cooling_off_period_days
            ),
            # Take higher withholding
            "withholding_rate": max(rules1.tax.withholding_rate, rules2.tax.withholding_rate),
            # Dispute resolution - prefer neutral venue
            "dispute_resolution": DisputeResolution.ARBITRATION_ICC.value,
            "arbitration_seat": (
                "London"
                if (jurisdiction1 != JurisdictionCode.GB and jurisdiction2 != JurisdictionCode.GB)
                else "Singapore"
            ),
            # Languages
            "languages": list(set([rules1.contract.language, rules2.contract.language])),
        }

        return merged

    def check_transaction_compliance(
        self,
        from_jurisdiction: JurisdictionCode,
        to_jurisdiction: JurisdictionCode,
        transaction_type: str,
        amount: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Check if a transaction is compliant across jurisdictions.

        Returns compliance status and any required actions.
        """
        from_rules = self.get_rules(from_jurisdiction)
        to_rules = self.get_rules(to_jurisdiction)

        issues = []
        required_actions = []

        # Check restrictions
        if from_rules and from_rules.is_restricted:
            issues.append(f"Source jurisdiction restricted: {from_rules.restriction_reason}")
        if to_rules and to_rules.is_restricted:
            issues.append(f"Destination jurisdiction restricted: {to_rules.restriction_reason}")

        if issues:
            return {
                "compliant": False,
                "issues": issues,
                "required_actions": [],
            }

        # Check prospectus requirements
        if to_rules and to_rules.disclosure.prospectus_required:
            if amount and to_rules.disclosure.prospectus_threshold:
                if amount >= to_rules.disclosure.prospectus_threshold:
                    required_actions.append(f"Prospectus required in {to_jurisdiction.value}")

        # Check investor requirements
        if to_rules and to_rules.investor.accreditation_required:
            required_actions.append(f"Verify accreditation for {to_jurisdiction.value}")

        # Check holding periods
        if to_rules and to_rules.investor.holding_period_days > 0:
            required_actions.append(
                f"Enforce {to_rules.investor.holding_period_days} day holding period"
            )

        # Check withholding tax
        if from_rules and to_rules:
            if from_rules.tax.withholding_rate > Decimal("0"):
                required_actions.append(
                    f"Withhold {from_rules.tax.withholding_rate * 100}% tax (check treaty rates)"
                )

        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "required_actions": required_actions,
            "from_rules_summary": (
                {
                    "jurisdiction": from_jurisdiction.value,
                    "license_required": from_rules.license_required if from_rules else None,
                    "withholding_rate": (
                        str(from_rules.tax.withholding_rate) if from_rules else None
                    ),
                }
                if from_rules
                else None
            ),
            "to_rules_summary": (
                {
                    "jurisdiction": to_jurisdiction.value,
                    "accreditation_required": (
                        to_rules.investor.accreditation_required if to_rules else None
                    ),
                    "prospectus_required": (
                        to_rules.disclosure.prospectus_required if to_rules else None
                    ),
                }
                if to_rules
                else None
            ),
        }


def create_rules_registry() -> JurisdictionRulesRegistry:
    """Factory function to create a JurisdictionRulesRegistry."""
    return JurisdictionRulesRegistry()
