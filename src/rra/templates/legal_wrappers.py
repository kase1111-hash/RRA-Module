# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Legal Wrapper Templates module for RRA.

Provides jurisdiction-specific legal wrapper templates for:
- License agreements
- Assignment agreements
- Dispute resolution clauses
- Regulatory compliance sections
- Tax withholding provisions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import re


class TemplateType(Enum):
    """Types of legal wrapper templates."""

    LICENSE_GRANT = "license_grant"
    ASSIGNMENT = "assignment"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    REPRESENTATIONS = "representations"
    WARRANTIES = "warranties"
    INDEMNIFICATION = "indemnification"
    LIMITATION_LIABILITY = "limitation_liability"
    CONFIDENTIALITY = "confidentiality"
    TERMINATION = "termination"
    FORCE_MAJEURE = "force_majeure"
    NOTICES = "notices"
    ENTIRE_AGREEMENT = "entire_agreement"
    TAX_PROVISIONS = "tax_provisions"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    DATA_PROTECTION = "data_protection"
    ANTI_MONEY_LAUNDERING = "anti_money_laundering"
    SMART_CONTRACT = "smart_contract"


class LanguageCode(Enum):
    """Language codes for templates."""

    EN = "en"  # English
    DE = "de"  # German
    FR = "fr"  # French
    ES = "es"  # Spanish
    IT = "it"  # Italian
    JA = "ja"  # Japanese
    ZH = "zh"  # Chinese
    PT = "pt"  # Portuguese


@dataclass
class TemplateVariable:
    """A variable placeholder in a template."""

    name: str
    description: str
    required: bool = True
    default_value: Optional[str] = None
    validation_pattern: Optional[str] = None
    example: Optional[str] = None


@dataclass
class LegalTemplate:
    """A legal wrapper template."""

    template_id: str
    template_type: TemplateType
    jurisdiction: str  # ISO 3166-1 alpha-2 or "INT"
    language: LanguageCode

    title: str
    content: str

    variables: List[TemplateVariable] = field(default_factory=list)
    required_for: List[str] = field(default_factory=list)  # Transaction types

    # Metadata
    version: str = "1.0"
    effective_date: datetime = field(default_factory=datetime.utcnow)
    last_reviewed: datetime = field(default_factory=datetime.utcnow)
    reviewer: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class RenderedClause:
    """A rendered legal clause with variables filled in."""

    template_id: str
    template_type: TemplateType
    jurisdiction: str
    language: LanguageCode
    title: str
    content: str
    rendered_at: datetime = field(default_factory=datetime.utcnow)


class LegalTemplateLibrary:
    """
    Library of legal wrapper templates.

    Provides jurisdiction-specific templates that can be combined
    to create complete legal wrappers for IP licensing transactions.
    """

    def __init__(self):
        self._templates: Dict[str, LegalTemplate] = {}
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Initialize default legal templates."""

        # ============ Governing Law Templates ============

        # US Delaware
        self._templates["gov_law_us_de"] = LegalTemplate(
            template_id="gov_law_us_de",
            template_type=TemplateType.GOVERNING_LAW,
            jurisdiction="US",
            language=LanguageCode.EN,
            title="Governing Law (Delaware)",
            content="""
GOVERNING LAW

This Agreement and any dispute or claim arising out of or in connection with it 
or its subject matter or formation (including non-contractual disputes or claims) 
shall be governed by and construed in accordance with the laws of the State of 
Delaware, United States of America, without giving effect to any choice or 
conflict of law provision or rule that would cause the application of the laws 
of any other jurisdiction.

The parties irrevocably submit to the exclusive jurisdiction of the courts of 
the State of Delaware and the United States District Court for the District of 
Delaware for the purpose of any suit, action, or other proceeding arising out 
of this Agreement.
""".strip(),
            variables=[],
            required_for=["us_transactions", "delaware_entities"],
        )

        # UK
        self._templates["gov_law_gb"] = LegalTemplate(
            template_id="gov_law_gb",
            template_type=TemplateType.GOVERNING_LAW,
            jurisdiction="GB",
            language=LanguageCode.EN,
            title="Governing Law (England & Wales)",
            content="""
GOVERNING LAW AND JURISDICTION

This Agreement and any dispute or claim (including non-contractual disputes or 
claims) arising out of or in connection with it or its subject matter or 
formation shall be governed by and construed in accordance with the law of 
England and Wales.

Each party irrevocably agrees that the courts of England and Wales shall have 
exclusive jurisdiction to settle any dispute or claim (including non-contractual 
disputes or claims) arising out of or in connection with this Agreement or its 
subject matter or formation.
""".strip(),
            variables=[],
            required_for=["uk_transactions"],
        )

        # Singapore
        self._templates["gov_law_sg"] = LegalTemplate(
            template_id="gov_law_sg",
            template_type=TemplateType.GOVERNING_LAW,
            jurisdiction="SG",
            language=LanguageCode.EN,
            title="Governing Law (Singapore)",
            content="""
GOVERNING LAW AND JURISDICTION

This Agreement shall be governed by and construed in accordance with the laws 
of the Republic of Singapore.

Any dispute arising out of or in connection with this Agreement, including any 
question regarding its existence, validity, or termination, shall be referred 
to and finally resolved by the Courts of the Republic of Singapore.
""".strip(),
            variables=[],
            required_for=["singapore_transactions"],
        )

        # International
        self._templates["gov_law_int"] = LegalTemplate(
            template_id="gov_law_int",
            template_type=TemplateType.GOVERNING_LAW,
            jurisdiction="INT",
            language=LanguageCode.EN,
            title="Governing Law (International)",
            content="""
GOVERNING LAW

This Agreement shall be governed by and construed in accordance with the 
UNIDROIT Principles of International Commercial Contracts (2016), supplemented 
where necessary by the law of {governing_jurisdiction}.

The United Nations Convention on Contracts for the International Sale of Goods 
(CISG) shall not apply to this Agreement.
""".strip(),
            variables=[
                TemplateVariable(
                    name="governing_jurisdiction",
                    description="Supplementary governing jurisdiction",
                    required=True,
                    default_value="England and Wales",
                    example="Switzerland",
                ),
            ],
            required_for=["cross_border_transactions"],
        )

        # ============ Dispute Resolution Templates ============

        # ICC Arbitration
        self._templates["disp_arb_icc"] = LegalTemplate(
            template_id="disp_arb_icc",
            template_type=TemplateType.DISPUTE_RESOLUTION,
            jurisdiction="INT",
            language=LanguageCode.EN,
            title="Dispute Resolution (ICC Arbitration)",
            content="""
DISPUTE RESOLUTION

All disputes arising out of or in connection with this Agreement shall be 
finally settled under the Rules of Arbitration of the International Chamber 
of Commerce by {number_of_arbitrators} arbitrator(s) appointed in accordance 
with the said Rules.

The seat, or legal place, of arbitration shall be {arbitration_seat}.

The language of the arbitration shall be {arbitration_language}.

The arbitral award shall be final and binding upon the parties and may be 
entered and enforced in any court of competent jurisdiction.

Notwithstanding the foregoing, either party may seek injunctive or other 
equitable relief in any court of competent jurisdiction to protect its 
intellectual property rights or confidential information.
""".strip(),
            variables=[
                TemplateVariable(
                    name="number_of_arbitrators",
                    description="Number of arbitrators (one or three)",
                    required=True,
                    default_value="one",
                    validation_pattern="^(one|three|1|3)$",
                ),
                TemplateVariable(
                    name="arbitration_seat",
                    description="Seat of arbitration",
                    required=True,
                    default_value="Paris, France",
                    example="London, United Kingdom",
                ),
                TemplateVariable(
                    name="arbitration_language",
                    description="Language of arbitration",
                    required=True,
                    default_value="English",
                ),
            ],
            required_for=["international_transactions"],
        )

        # AAA Arbitration (US)
        self._templates["disp_arb_aaa"] = LegalTemplate(
            template_id="disp_arb_aaa",
            template_type=TemplateType.DISPUTE_RESOLUTION,
            jurisdiction="US",
            language=LanguageCode.EN,
            title="Dispute Resolution (AAA Arbitration)",
            content="""
DISPUTE RESOLUTION

Any controversy or claim arising out of or relating to this Agreement, or the 
breach thereof, shall be settled by arbitration administered by the American 
Arbitration Association in accordance with its Commercial Arbitration Rules, 
and judgment on the award rendered by the arbitrator(s) may be entered in any 
court having jurisdiction thereof.

The place of arbitration shall be {arbitration_city}, {arbitration_state}.

The arbitration shall be conducted in English.

Each party shall bear its own costs and expenses, including attorney fees, 
incurred in connection with the arbitration, and the parties shall share 
equally the fees and expenses of the arbitrator(s) and the AAA.

WAIVER OF JURY TRIAL: EACH PARTY HEREBY WAIVES ITS RIGHT TO A TRIAL BY JURY 
IN ANY ACTION OR PROCEEDING ARISING OUT OF OR RELATING TO THIS AGREEMENT.
""".strip(),
            variables=[
                TemplateVariable(
                    name="arbitration_city",
                    description="City for arbitration",
                    required=True,
                    default_value="New York",
                ),
                TemplateVariable(
                    name="arbitration_state",
                    description="State for arbitration",
                    required=True,
                    default_value="New York",
                ),
            ],
            required_for=["us_transactions"],
        )

        # SIAC Arbitration (Singapore)
        self._templates["disp_arb_siac"] = LegalTemplate(
            template_id="disp_arb_siac",
            template_type=TemplateType.DISPUTE_RESOLUTION,
            jurisdiction="SG",
            language=LanguageCode.EN,
            title="Dispute Resolution (SIAC Arbitration)",
            content="""
DISPUTE RESOLUTION

Any dispute arising out of or in connection with this contract, including any 
question regarding its existence, validity or termination, shall be referred 
to and finally resolved by arbitration administered by the Singapore 
International Arbitration Centre ("SIAC") in accordance with the Arbitration 
Rules of the Singapore International Arbitration Centre ("SIAC Rules") for the 
time being in force, which rules are deemed to be incorporated by reference in 
this clause.

The seat of the arbitration shall be Singapore.

The Tribunal shall consist of {number_of_arbitrators} arbitrator(s).

The language of the arbitration shall be English.
""".strip(),
            variables=[
                TemplateVariable(
                    name="number_of_arbitrators",
                    description="Number of arbitrators",
                    required=True,
                    default_value="one",
                ),
            ],
            required_for=["singapore_transactions", "asia_pacific_transactions"],
        )

        # ============ License Grant Templates ============

        self._templates["license_grant_exclusive"] = LegalTemplate(
            template_id="license_grant_exclusive",
            template_type=TemplateType.LICENSE_GRANT,
            jurisdiction="INT",
            language=LanguageCode.EN,
            title="Exclusive License Grant",
            content="""
GRANT OF LICENSE

Subject to the terms and conditions of this Agreement, Licensor hereby grants 
to Licensee an exclusive, {transferability} license to:

(a) use, reproduce, modify, and create derivative works of the Licensed IP;
(b) publicly display and publicly perform the Licensed IP;
(c) distribute, sell, lease, or otherwise transfer copies of the Licensed IP; and
(d) sublicense any or all of the foregoing rights to third parties,

in each case, solely within the Territory and during the Term.

"Licensed IP" means {licensed_ip_description}.

"Territory" means {territory}.

"Term" means the period commencing on the Effective Date and ending on 
{term_end_date}, unless earlier terminated in accordance with this Agreement.

This license is granted on a royalty-bearing basis, with Licensee paying 
Licensor a royalty of {royalty_rate} percent ({royalty_rate}%) of Net Revenue, 
as defined herein.
""".strip(),
            variables=[
                TemplateVariable(
                    name="transferability",
                    description="Whether license is transferable",
                    required=True,
                    default_value="non-transferable",
                    validation_pattern="^(transferable|non-transferable)$",
                ),
                TemplateVariable(
                    name="licensed_ip_description",
                    description="Description of the licensed IP",
                    required=True,
                    example="US Patent No. 12,345,678 and all related applications",
                ),
                TemplateVariable(
                    name="territory",
                    description="Geographic territory for the license",
                    required=True,
                    default_value="worldwide",
                ),
                TemplateVariable(
                    name="term_end_date",
                    description="End date of the license term",
                    required=True,
                    example="December 31, 2030",
                ),
                TemplateVariable(
                    name="royalty_rate",
                    description="Royalty rate as percentage",
                    required=True,
                    default_value="5",
                    validation_pattern="^\\d+(\\.\\d+)?$",
                ),
            ],
            required_for=["exclusive_license"],
        )

        self._templates["license_grant_nonexclusive"] = LegalTemplate(
            template_id="license_grant_nonexclusive",
            template_type=TemplateType.LICENSE_GRANT,
            jurisdiction="INT",
            language=LanguageCode.EN,
            title="Non-Exclusive License Grant",
            content="""
GRANT OF LICENSE

Subject to the terms and conditions of this Agreement, Licensor hereby grants 
to Licensee a non-exclusive, non-transferable license to:

(a) use and reproduce the Licensed IP;
(b) incorporate the Licensed IP into Licensee's products and services; and
(c) distribute products and services incorporating the Licensed IP,

in each case, solely within the Territory and during the Term.

Licensor reserves all rights not expressly granted herein, including the right 
to grant licenses to third parties.

"Licensed IP" means {licensed_ip_description}.

"Territory" means {territory}.

"Term" means the period commencing on the Effective Date and continuing for 
{term_years} year(s), automatically renewing for successive {renewal_years}-year 
periods unless either party provides written notice of non-renewal at least 
{notice_days} days prior to the end of the then-current term.
""".strip(),
            variables=[
                TemplateVariable(
                    name="licensed_ip_description",
                    description="Description of the licensed IP",
                    required=True,
                ),
                TemplateVariable(
                    name="territory",
                    description="Geographic territory",
                    required=True,
                    default_value="worldwide",
                ),
                TemplateVariable(
                    name="term_years",
                    description="Initial term in years",
                    required=True,
                    default_value="3",
                ),
                TemplateVariable(
                    name="renewal_years",
                    description="Renewal period in years",
                    required=True,
                    default_value="1",
                ),
                TemplateVariable(
                    name="notice_days",
                    description="Notice days for non-renewal",
                    required=True,
                    default_value="90",
                ),
            ],
            required_for=["non_exclusive_license"],
        )

        # ============ Smart Contract Integration ============

        self._templates["smart_contract_integration"] = LegalTemplate(
            template_id="smart_contract_integration",
            template_type=TemplateType.SMART_CONTRACT,
            jurisdiction="INT",
            language=LanguageCode.EN,
            title="Smart Contract Integration Clause",
            content="""
SMART CONTRACT INTEGRATION

1. On-Chain Enforcement. The parties acknowledge and agree that certain terms 
   of this Agreement are encoded in and enforced by a smart contract deployed 
   at address {contract_address} on the {blockchain_network} blockchain network 
   (the "Smart Contract").

2. Primacy. In the event of any conflict between the terms of this Agreement 
   and the operation of the Smart Contract, the terms of this Agreement shall 
   control, except with respect to the following automated functions which 
   shall be governed by the Smart Contract:
   (a) royalty payment calculations and distributions;
   (b) license activation and deactivation;
   (c) usage tracking and reporting; and
   (d) transfer of license tokens.

3. Token Representation. The license rights granted herein are represented by 
   a non-fungible token (Token ID: {token_id}) on the Smart Contract. Transfer 
   of this token constitutes transfer of the license rights, subject to any 
   restrictions set forth in this Agreement.

4. Immutability. The parties acknowledge that blockchain transactions are 
   irreversible and that the Smart Contract code, once deployed, operates 
   autonomously according to its programmed logic.

5. Private Keys. Each party is solely responsible for maintaining the security 
   of its private keys and wallet credentials. Neither party shall be liable 
   for losses arising from the other party's failure to secure its credentials.

6. Gas Fees. Unless otherwise specified, each party shall bear its own 
   transaction costs (gas fees) for blockchain interactions.
""".strip(),
            variables=[
                TemplateVariable(
                    name="contract_address",
                    description="Smart contract address",
                    required=True,
                    validation_pattern="^0x[a-fA-F0-9]{40}$",
                    example="0x1234567890123456789012345678901234567890",
                ),
                TemplateVariable(
                    name="blockchain_network",
                    description="Blockchain network name",
                    required=True,
                    default_value="Ethereum",
                ),
                TemplateVariable(
                    name="token_id",
                    description="NFT token ID",
                    required=True,
                    validation_pattern="^\\d+$",
                ),
            ],
            required_for=["tokenized_license", "smart_contract"],
        )

        # ============ Data Protection (GDPR) ============

        self._templates["data_protection_gdpr"] = LegalTemplate(
            template_id="data_protection_gdpr",
            template_type=TemplateType.DATA_PROTECTION,
            jurisdiction="EU",
            language=LanguageCode.EN,
            title="Data Protection (GDPR Compliance)",
            content="""
DATA PROTECTION

1. Definitions. For the purposes of this clause:
   - "Data Protection Laws" means the General Data Protection Regulation 
     (EU) 2016/679 ("GDPR") and any applicable national implementing 
     legislation, as amended from time to time.
   - "Personal Data", "Controller", "Processor", and "Processing" have the 
     meanings given to them in the GDPR.

2. Compliance. Each party shall comply with its obligations under applicable 
   Data Protection Laws in relation to any Personal Data processed in 
   connection with this Agreement.

3. Processing Roles. The parties acknowledge that:
   - Licensor acts as Controller with respect to {licensor_data_types};
   - Licensee acts as Controller with respect to {licensee_data_types}.

4. Data Processing Agreement. Where either party processes Personal Data on 
   behalf of the other, the parties shall enter into a separate Data 
   Processing Agreement that meets the requirements of Article 28 of the GDPR.

5. International Transfers. Neither party shall transfer Personal Data to a 
   country outside the European Economic Area unless appropriate safeguards 
   are in place in accordance with Chapter V of the GDPR.

6. Data Subject Rights. Each party shall assist the other in responding to 
   requests from data subjects exercising their rights under the GDPR.
""".strip(),
            variables=[
                TemplateVariable(
                    name="licensor_data_types",
                    description="Types of data controlled by licensor",
                    required=True,
                    default_value="licensee contact information and payment data",
                ),
                TemplateVariable(
                    name="licensee_data_types",
                    description="Types of data controlled by licensee",
                    required=True,
                    default_value="end user data collected through the licensed products",
                ),
            ],
            required_for=["eu_transactions", "gdpr_required"],
        )

        # ============ Tax Withholding ============

        self._templates["tax_withholding_us"] = LegalTemplate(
            template_id="tax_withholding_us",
            template_type=TemplateType.TAX_PROVISIONS,
            jurisdiction="US",
            language=LanguageCode.EN,
            title="Tax Withholding (US)",
            content="""
TAX PROVISIONS

1. Withholding. All payments due under this Agreement are subject to 
   applicable withholding taxes. Licensee shall withhold and remit to the 
   appropriate taxing authorities all taxes required by law to be withheld 
   from payments to Licensor.

2. Tax Forms. Prior to receiving any payments, Licensor shall provide 
   Licensee with a properly completed:
   - IRS Form W-9 (if Licensor is a U.S. person); or
   - IRS Form W-8BEN, W-8BEN-E, or other applicable W-8 form (if Licensor 
     is not a U.S. person).

3. Treaty Benefits. If Licensor is entitled to reduced withholding under an 
   applicable tax treaty, Licensor shall provide documentation sufficient to 
   establish entitlement to such reduced rate. Licensee shall apply the 
   reduced rate upon receipt of such documentation.

4. Gross-Up. Unless otherwise required by law, all amounts payable by 
   Licensee under this Agreement are exclusive of withholding taxes, and 
   Licensee shall not be required to gross up payments to account for 
   withholding.

5. Tax Indemnity. Each party shall indemnify the other against any taxes, 
   penalties, or interest assessed against the indemnified party as a result 
   of the indemnifying party's failure to comply with its tax obligations 
   under this Agreement.
""".strip(),
            variables=[],
            required_for=["us_transactions", "cross_border_royalties"],
        )

        # ============ AML/KYC ============

        self._templates["aml_kyc"] = LegalTemplate(
            template_id="aml_kyc",
            template_type=TemplateType.ANTI_MONEY_LAUNDERING,
            jurisdiction="INT",
            language=LanguageCode.EN,
            title="Anti-Money Laundering and Know Your Customer",
            content="""
ANTI-MONEY LAUNDERING AND KNOW YOUR CUSTOMER

1. Representations. Each party represents and warrants that:
   (a) it is not, and is not owned or controlled by, a person or entity that 
       is listed on any sanctions list maintained by the U.S. Office of 
       Foreign Assets Control (OFAC), the United Nations, the European Union, 
       or any other applicable governmental authority;
   (b) it is not located in, organized under the laws of, or a resident of 
       any country or territory that is subject to comprehensive sanctions;
   (c) it has implemented and maintains an anti-money laundering program in 
       compliance with applicable laws; and
   (d) all funds used in connection with this Agreement are derived from 
       legitimate sources.

2. Cooperation. Each party agrees to:
   (a) provide such information and documentation as the other party may 
       reasonably request to verify compliance with applicable anti-money 
       laundering and sanctions laws;
   (b) promptly notify the other party if it becomes aware of any 
       circumstances that would make any of the foregoing representations 
       untrue; and
   (c) cooperate with any governmental investigation related to this 
       Agreement.

3. Suspension. Either party may immediately suspend performance under this 
   Agreement if it has reasonable grounds to believe the other party is in 
   violation of applicable anti-money laundering or sanctions laws.

4. Termination. Either party may terminate this Agreement immediately upon 
   written notice if the other party is determined to be in violation of 
   applicable anti-money laundering or sanctions laws.
""".strip(),
            variables=[],
            required_for=["all_transactions"],
        )

    def get_template(self, template_id: str) -> Optional[LegalTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def get_templates_by_type(self, template_type: TemplateType) -> List[LegalTemplate]:
        """Get all templates of a specific type."""
        return [t for t in self._templates.values() if t.template_type == template_type]

    def get_templates_by_jurisdiction(self, jurisdiction: str) -> List[LegalTemplate]:
        """Get all templates for a specific jurisdiction."""
        return [
            t
            for t in self._templates.values()
            if t.jurisdiction == jurisdiction or t.jurisdiction == "INT"
        ]

    def render_template(self, template_id: str, variables: Dict[str, str]) -> RenderedClause:
        """Render a template with the provided variables."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        content = template.content

        # Validate and substitute variables
        for var in template.variables:
            if var.name in variables:
                value = variables[var.name]

                # Validate if pattern provided
                if var.validation_pattern:
                    if not re.match(var.validation_pattern, value):
                        raise ValueError(
                            f"Variable '{var.name}' value '{value}' does not match "
                            f"pattern '{var.validation_pattern}'"
                        )

                content = content.replace(f"{{{var.name}}}", value)
            elif var.required and not var.default_value:
                raise ValueError(f"Required variable '{var.name}' not provided")
            elif var.default_value:
                content = content.replace(f"{{{var.name}}}", var.default_value)

        return RenderedClause(
            template_id=template_id,
            template_type=template.template_type,
            jurisdiction=template.jurisdiction,
            language=template.language,
            title=template.title,
            content=content,
        )

    def build_wrapper(
        self, jurisdiction: str, template_types: List[TemplateType], variables: Dict[str, str]
    ) -> List[RenderedClause]:
        """Build a complete legal wrapper from multiple templates."""
        clauses = []

        for template_type in template_types:
            # Find best template for jurisdiction and type
            templates = [
                t
                for t in self._templates.values()
                if t.template_type == template_type
                and (t.jurisdiction == jurisdiction or t.jurisdiction == "INT")
            ]

            # Prefer jurisdiction-specific over international
            templates.sort(key=lambda t: 0 if t.jurisdiction == jurisdiction else 1)

            if templates:
                template = templates[0]
                try:
                    clause = self.render_template(template.template_id, variables)
                    clauses.append(clause)
                except ValueError:
                    # Skip if required variables missing
                    pass

        return clauses

    def register_template(self, template: LegalTemplate):
        """Register a new template."""
        self._templates[template.template_id] = template

    def list_templates(self) -> List[LegalTemplate]:
        """List all registered templates."""
        return list(self._templates.values())


def create_template_library() -> LegalTemplateLibrary:
    """Factory function to create a LegalTemplateLibrary."""
    return LegalTemplateLibrary()
