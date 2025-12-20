# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Pre-Hardened License Clause Templates.

Provides battle-tested clause templates with:
- Specific, measurable terms (no "reasonable" or "best efforts")
- Clear thresholds and boundaries
- Defined procedures for common scenarios
- Low dispute-rate language based on historical data

Templates are organized by category and license type,
with customizable parameters for specific use cases.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import re


class TemplateCategory(Enum):
    """Categories of clause templates."""

    GRANT = "grant"
    RESTRICTIONS = "restrictions"
    ATTRIBUTION = "attribution"
    WARRANTY = "warranty"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    TERMINATION = "termination"
    PAYMENT = "payment"
    SUPPORT = "support"
    CONFIDENTIALITY = "confidentiality"
    IP_OWNERSHIP = "ip_ownership"
    DISPUTE_RESOLUTION = "dispute_resolution"
    GOVERNING_LAW = "governing_law"
    DATA_PROTECTION = "data_protection"
    AUDIT = "audit"


class LicenseType(Enum):
    """Types of licenses these templates support."""

    OPEN_SOURCE = "open_source"
    COMMERCIAL = "commercial"
    SAAS = "saas"
    API = "api"
    DATA = "data"
    CONTENT = "content"
    HYBRID = "hybrid"


@dataclass
class TemplateParameter:
    """A customizable parameter in a template."""

    name: str
    description: str
    default_value: str
    examples: List[str] = field(default_factory=list)
    required: bool = False
    validation_pattern: Optional[str] = None

    def validate(self, value: str) -> bool:
        """Validate a parameter value."""
        if self.validation_pattern:
            return bool(re.match(self.validation_pattern, value))
        return True


@dataclass
class ClauseTemplate:
    """A pre-hardened clause template."""

    id: str
    name: str
    category: TemplateCategory
    license_types: List[LicenseType]
    template_text: str
    parameters: List[TemplateParameter] = field(default_factory=list)
    description: str = ""
    risk_score: float = 0.0  # Lower is better (0-1)
    source: str = ""  # Where this template originated
    tags: List[str] = field(default_factory=list)
    related_templates: List[str] = field(default_factory=list)

    def render(self, values: Optional[Dict[str, str]] = None) -> str:
        """
        Render the template with provided values.

        Args:
            values: Parameter values to substitute

        Returns:
            Rendered clause text
        """
        values = values or {}
        text = self.template_text

        for param in self.parameters:
            placeholder = f"{{{param.name}}}"
            value = values.get(param.name, param.default_value)
            text = text.replace(placeholder, value)

        return text

    def get_required_parameters(self) -> List[str]:
        """Get list of required parameter names."""
        return [p.name for p in self.parameters if p.required]

    def validate_values(self, values: Dict[str, str]) -> List[str]:
        """
        Validate provided parameter values.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        for param in self.parameters:
            if param.required and param.name not in values:
                errors.append(f"Required parameter '{param.name}' is missing")
            elif param.name in values and not param.validate(values[param.name]):
                errors.append(
                    f"Parameter '{param.name}' has invalid value: {values[param.name]}"
                )

        return errors


class TemplateLibrary:
    """
    Library of pre-hardened clause templates.

    Provides categorized access to battle-tested clause templates
    with low dispute rates and clear, specific language.
    """

    def __init__(self):
        """Initialize the template library."""
        self._templates: Dict[str, ClauseTemplate] = {}
        self._by_category: Dict[TemplateCategory, List[str]] = {}
        self._by_license_type: Dict[LicenseType, List[str]] = {}
        self._by_tag: Dict[str, List[str]] = {}

    def add_template(self, template: ClauseTemplate) -> None:
        """Add a template to the library."""
        self._templates[template.id] = template

        # Index by category
        if template.category not in self._by_category:
            self._by_category[template.category] = []
        self._by_category[template.category].append(template.id)

        # Index by license type
        for lt in template.license_types:
            if lt not in self._by_license_type:
                self._by_license_type[lt] = []
            self._by_license_type[lt].append(template.id)

        # Index by tag
        for tag in template.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = []
            self._by_tag[tag].append(template.id)

    def get_template(self, template_id: str) -> Optional[ClauseTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def get_by_category(self, category: TemplateCategory) -> List[ClauseTemplate]:
        """Get all templates in a category."""
        ids = self._by_category.get(category, [])
        return [self._templates[tid] for tid in ids]

    def get_by_license_type(self, license_type: LicenseType) -> List[ClauseTemplate]:
        """Get all templates for a license type."""
        ids = self._by_license_type.get(license_type, [])
        return [self._templates[tid] for tid in ids]

    def get_by_tag(self, tag: str) -> List[ClauseTemplate]:
        """Get all templates with a specific tag."""
        ids = self._by_tag.get(tag, [])
        return [self._templates[tid] for tid in ids]

    def search(
        self,
        category: Optional[TemplateCategory] = None,
        license_type: Optional[LicenseType] = None,
        tags: Optional[List[str]] = None,
        max_risk_score: Optional[float] = None,
    ) -> List[ClauseTemplate]:
        """
        Search for templates matching criteria.

        Args:
            category: Filter by category
            license_type: Filter by license type
            tags: Filter by tags (any match)
            max_risk_score: Maximum acceptable risk score

        Returns:
            List of matching templates
        """
        candidates = set(self._templates.keys())

        if category:
            category_ids = set(self._by_category.get(category, []))
            candidates &= category_ids

        if license_type:
            type_ids = set(self._by_license_type.get(license_type, []))
            candidates &= type_ids

        if tags:
            tag_ids = set()
            for tag in tags:
                tag_ids.update(self._by_tag.get(tag, []))
            candidates &= tag_ids

        results = [self._templates[tid] for tid in candidates]

        if max_risk_score is not None:
            results = [t for t in results if t.risk_score <= max_risk_score]

        return sorted(results, key=lambda t: t.risk_score)

    def get_complete_contract(
        self,
        license_type: LicenseType,
        values: Optional[Dict[str, str]] = None,
    ) -> Dict[TemplateCategory, str]:
        """
        Generate a complete contract using templates.

        Args:
            license_type: Type of license
            values: Parameter values to apply

        Returns:
            Dict mapping categories to rendered clauses
        """
        values = values or {}
        contract = {}

        for category in TemplateCategory:
            templates = self.search(
                category=category,
                license_type=license_type,
                max_risk_score=0.3,
            )
            if templates:
                # Use the lowest-risk template
                template = templates[0]
                contract[category] = template.render(values)

        return contract

    def list_all(self) -> List[ClauseTemplate]:
        """Get all templates."""
        return list(self._templates.values())


# =============================================================================
# Default Templates
# =============================================================================

DEFAULT_TEMPLATES = [
    # === GRANT TEMPLATES ===
    ClauseTemplate(
        id="grant_software_perpetual",
        name="Perpetual Software License Grant",
        category=TemplateCategory.GRANT,
        license_types=[LicenseType.COMMERCIAL, LicenseType.OPEN_SOURCE],
        template_text="""
LICENSE GRANT. Subject to the terms of this Agreement and payment of all applicable fees,
Licensor hereby grants to Licensee a non-exclusive, non-transferable, perpetual license to:

(a) Install and use the Software on up to {max_installations} device(s) owned or controlled by Licensee;
(b) Make up to {max_copies} backup copies of the Software for archival purposes;
(c) Modify the Software solely for Licensee's internal use, provided that any modifications
    remain subject to this Agreement.

This license does not include the right to: (i) sublicense, sell, or distribute the Software
or any modifications; (ii) use the Software to provide services to third parties; or
(iii) reverse engineer, decompile, or disassemble the Software except as permitted by
applicable law.
""".strip(),
        parameters=[
            TemplateParameter(
                name="max_installations",
                description="Maximum number of installations allowed",
                default_value="5",
                examples=["1", "5", "unlimited"],
                required=True,
            ),
            TemplateParameter(
                name="max_copies",
                description="Maximum backup copies allowed",
                default_value="2",
                examples=["1", "2", "3"],
            ),
        ],
        description="Clear grant with specific installation limits and explicit exclusions",
        risk_score=0.15,
        tags=["perpetual", "software", "clear-scope"],
    ),

    ClauseTemplate(
        id="grant_api_usage",
        name="API Usage License Grant",
        category=TemplateCategory.GRANT,
        license_types=[LicenseType.API, LicenseType.SAAS],
        template_text="""
API LICENSE. Licensor grants Licensee a non-exclusive, non-transferable license to access
and use the API solely for the purposes of {permitted_purpose}.

USAGE LIMITS. Licensee's use is limited to:
- {rate_limit} API calls per {rate_period}
- {data_limit} of data transfer per calendar month
- {concurrent_connections} concurrent connections

PROHIBITED USES. Licensee shall not: (i) exceed the usage limits without prior written
authorization and payment of overage fees as specified in Schedule B; (ii) share API
credentials with third parties; (iii) use the API to build a competing service; or
(iv) attempt to circumvent rate limiting or access controls.
""".strip(),
        parameters=[
            TemplateParameter(
                name="permitted_purpose",
                description="Permitted use of the API",
                default_value="integrating with Licensee's internal applications",
                required=True,
            ),
            TemplateParameter(
                name="rate_limit",
                description="Maximum API calls per period",
                default_value="10,000",
                examples=["1,000", "10,000", "100,000"],
                required=True,
            ),
            TemplateParameter(
                name="rate_period",
                description="Rate limit time period",
                default_value="day",
                examples=["minute", "hour", "day"],
            ),
            TemplateParameter(
                name="data_limit",
                description="Monthly data transfer limit",
                default_value="10 GB",
                examples=["1 GB", "10 GB", "100 GB"],
            ),
            TemplateParameter(
                name="concurrent_connections",
                description="Maximum concurrent connections",
                default_value="10",
                examples=["5", "10", "50"],
            ),
        ],
        description="API license with specific, measurable usage limits",
        risk_score=0.12,
        tags=["api", "rate-limits", "clear-scope"],
    ),

    # === TERMINATION TEMPLATES ===
    ClauseTemplate(
        id="termination_for_cause",
        name="Termination for Cause",
        category=TemplateCategory.TERMINATION,
        license_types=[LicenseType.COMMERCIAL, LicenseType.SAAS, LicenseType.API],
        template_text="""
TERMINATION FOR CAUSE. Either party may terminate this Agreement immediately upon written
notice if the other party:

(a) Commits a material breach (as defined below) and fails to cure such breach within
    {cure_period} calendar days after receiving written notice specifying the breach;
(b) Files for bankruptcy, makes an assignment for the benefit of creditors, or becomes
    subject to dissolution, liquidation, or receivership proceedings;
(c) Fails to make any payment due under this Agreement within {payment_grace_period} days
    after written notice of non-payment.

DEFINITION OF MATERIAL BREACH. A "material breach" means any of the following:
- Failure to pay fees exceeding ${material_amount} in the aggregate;
- Unauthorized disclosure of Confidential Information;
- Use of the Software or Services in violation of Section {restrictions_section};
- Any breach that prevents the non-breaching party from receiving the substantial benefit
  of this Agreement.
""".strip(),
        parameters=[
            TemplateParameter(
                name="cure_period",
                description="Days to cure a breach",
                default_value="30",
                examples=["14", "30", "60"],
                required=True,
            ),
            TemplateParameter(
                name="payment_grace_period",
                description="Days grace period for payment",
                default_value="15",
                examples=["10", "15", "30"],
            ),
            TemplateParameter(
                name="material_amount",
                description="Dollar threshold for material breach",
                default_value="1,000",
                examples=["500", "1,000", "5,000"],
            ),
            TemplateParameter(
                name="restrictions_section",
                description="Section number for restrictions",
                default_value="3",
            ),
        ],
        description="Clear termination with defined material breach threshold",
        risk_score=0.18,
        tags=["termination", "defined-thresholds", "cure-period"],
    ),

    ClauseTemplate(
        id="termination_convenience",
        name="Termination for Convenience",
        category=TemplateCategory.TERMINATION,
        license_types=[LicenseType.SAAS, LicenseType.COMMERCIAL],
        template_text="""
TERMINATION FOR CONVENIENCE. Either party may terminate this Agreement for any reason
by providing written notice to the other party at least {notice_period} calendar days
prior to the intended termination date.

NOTICE REQUIREMENTS. Written notice must be sent via {notice_method} to the address
specified in Section {notice_section}. Notice is deemed received:
- If sent by registered mail: {mail_receipt_days} business days after posting
- If sent by courier: upon delivery confirmation
- If sent by email: upon receipt of read confirmation or after {email_receipt_hours} hours

EFFECT OF TERMINATION. Upon termination for convenience:
(a) Licensee shall pay all fees accrued through the termination date within {final_payment_days} days;
(b) Licensor shall provide {data_export_period} days for Licensee to export its data;
(c) No refunds shall be issued for prepaid fees, except as specified in Schedule A.
""".strip(),
        parameters=[
            TemplateParameter(
                name="notice_period",
                description="Days notice required",
                default_value="30",
                examples=["30", "60", "90"],
                required=True,
            ),
            TemplateParameter(
                name="notice_method",
                description="Acceptable notice delivery methods",
                default_value="registered mail, courier with tracking, or email with read receipt",
            ),
            TemplateParameter(
                name="notice_section",
                description="Section with notice addresses",
                default_value="12",
            ),
            TemplateParameter(
                name="mail_receipt_days",
                description="Days for mail receipt",
                default_value="5",
            ),
            TemplateParameter(
                name="email_receipt_hours",
                description="Hours for email receipt",
                default_value="48",
            ),
            TemplateParameter(
                name="final_payment_days",
                description="Days to pay final invoice",
                default_value="30",
            ),
            TemplateParameter(
                name="data_export_period",
                description="Days for data export",
                default_value="30",
            ),
        ],
        description="Clear termination for convenience with specific notice procedures",
        risk_score=0.10,
        tags=["termination", "convenience", "notice-procedures"],
    ),

    # === PAYMENT TEMPLATES ===
    ClauseTemplate(
        id="payment_subscription",
        name="Subscription Payment Terms",
        category=TemplateCategory.PAYMENT,
        license_types=[LicenseType.SAAS, LicenseType.API],
        template_text="""
FEES. Licensee shall pay the fees specified in Schedule A according to the following terms:

PAYMENT SCHEDULE. Fees are due {payment_frequency} in advance. Invoices will be issued
{invoice_timing} before the payment due date.

PAYMENT METHOD. Payment shall be made via {payment_methods}. Licensee is responsible for
all bank fees associated with the payment method chosen.

LATE PAYMENT. Payments not received within {grace_period} days of the due date shall
incur a late fee of {late_fee_percent}% per month (or the maximum permitted by law,
if lower) on the outstanding balance.

PRICE INCREASES. Licensor may increase fees upon {price_increase_notice} days' written
notice. Fee increases shall not exceed {max_increase_percent}% per year unless mutually
agreed in writing.

DISPUTED CHARGES. Licensee must notify Licensor of any disputed charges within {dispute_period}
days of the invoice date. Failure to dispute within this period constitutes acceptance of
the charges.
""".strip(),
        parameters=[
            TemplateParameter(
                name="payment_frequency",
                description="Payment frequency",
                default_value="monthly",
                examples=["monthly", "quarterly", "annually"],
                required=True,
            ),
            TemplateParameter(
                name="invoice_timing",
                description="When invoices are issued",
                default_value="7 days",
                examples=["7 days", "14 days", "30 days"],
            ),
            TemplateParameter(
                name="payment_methods",
                description="Accepted payment methods",
                default_value="credit card, ACH, or wire transfer",
            ),
            TemplateParameter(
                name="grace_period",
                description="Days grace period for payment",
                default_value="10",
                examples=["7", "10", "15"],
            ),
            TemplateParameter(
                name="late_fee_percent",
                description="Monthly late fee percentage",
                default_value="1.5",
                examples=["1", "1.5", "2"],
            ),
            TemplateParameter(
                name="price_increase_notice",
                description="Days notice for price increase",
                default_value="60",
                examples=["30", "60", "90"],
            ),
            TemplateParameter(
                name="max_increase_percent",
                description="Maximum annual price increase",
                default_value="10",
                examples=["5", "10", "15"],
            ),
            TemplateParameter(
                name="dispute_period",
                description="Days to dispute charges",
                default_value="30",
                examples=["15", "30", "45"],
            ),
        ],
        description="Comprehensive payment terms with specific procedures",
        risk_score=0.15,
        tags=["payment", "subscription", "late-fees"],
    ),

    # === LIABILITY TEMPLATES ===
    ClauseTemplate(
        id="liability_limitation_cap",
        name="Liability Limitation with Cap",
        category=TemplateCategory.LIABILITY,
        license_types=[LicenseType.COMMERCIAL, LicenseType.SAAS],
        template_text="""
LIMITATION OF LIABILITY.

EXCLUSION OF DAMAGES. IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS,
LOSS OF DATA, BUSINESS INTERRUPTION, OR LOSS OF GOODWILL, ARISING OUT OF OR RELATED TO
THIS AGREEMENT, REGARDLESS OF THE CAUSE OF ACTION OR THE THEORY OF LIABILITY, EVEN IF
SUCH PARTY HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

LIABILITY CAP. EXCEPT FOR (A) BREACHES OF CONFIDENTIALITY OBLIGATIONS, (B) INDEMNIFICATION
OBLIGATIONS, (C) LICENSEE'S PAYMENT OBLIGATIONS, AND (D) EITHER PARTY'S GROSS NEGLIGENCE
OR WILLFUL MISCONDUCT, EACH PARTY'S TOTAL CUMULATIVE LIABILITY UNDER THIS AGREEMENT SHALL
NOT EXCEED {liability_cap}.

CALCULATION. The liability cap shall be calculated as {cap_calculation}.

ACKNOWLEDGMENT. THE PARTIES ACKNOWLEDGE THAT THE LIMITATIONS SET FORTH IN THIS SECTION
REFLECT THE ALLOCATION OF RISK BETWEEN THE PARTIES AND ARE AN ESSENTIAL ELEMENT OF THE
BASIS OF THE BARGAIN BETWEEN THEM.
""".strip(),
        parameters=[
            TemplateParameter(
                name="liability_cap",
                description="Maximum liability amount or formula",
                default_value="the total fees paid by Licensee in the 12 months preceding the claim",
                examples=[
                    "$100,000",
                    "the total fees paid in the preceding 12 months",
                    "2x the annual contract value",
                ],
                required=True,
            ),
            TemplateParameter(
                name="cap_calculation",
                description="How the cap is calculated",
                default_value="the aggregate of fees actually paid by Licensee under this Agreement during the twelve (12) month period immediately preceding the event giving rise to the claim",
            ),
        ],
        description="Standard liability cap with clear exclusions and carve-outs",
        risk_score=0.20,
        tags=["liability", "cap", "exclusions"],
    ),

    # === DISPUTE RESOLUTION TEMPLATES ===
    ClauseTemplate(
        id="dispute_escalation",
        name="Dispute Resolution with Escalation",
        category=TemplateCategory.DISPUTE_RESOLUTION,
        license_types=[LicenseType.COMMERCIAL, LicenseType.SAAS, LicenseType.API],
        template_text="""
DISPUTE RESOLUTION.

INFORMAL RESOLUTION. The parties shall first attempt to resolve any dispute arising under
this Agreement through good faith negotiations. Within {negotiation_start} business days
of written notice of a dispute, each party shall designate a representative with authority
to resolve the matter. The representatives shall meet (in person or via video conference)
within {negotiation_meeting} business days and shall have {negotiation_period} calendar
days to reach a resolution.

MEDIATION. If the dispute is not resolved through negotiation, either party may initiate
non-binding mediation by providing written notice to the other party. Mediation shall be
conducted by a mediator mutually agreed upon by the parties within {mediator_selection}
days, or if no agreement, appointed by {mediation_organization}. The mediation shall take
place in {mediation_location} and shall be completed within {mediation_period} calendar
days of the mediator's appointment. Mediation costs shall be {mediation_costs}.

BINDING ARBITRATION. If the dispute is not resolved through mediation, it shall be resolved
by binding arbitration conducted by {arbitration_organization} in accordance with its
{arbitration_rules}. The arbitration shall be conducted in {arbitration_location} by
{arbitrator_count} arbitrator(s). The arbitrator's decision shall be final and binding,
and judgment on the award may be entered in any court of competent jurisdiction.

EXCEPTIONS. Notwithstanding the foregoing, either party may seek injunctive relief in any
court of competent jurisdiction to protect its intellectual property rights or Confidential
Information.

COSTS. Unless the arbitrator determines otherwise, each party shall bear its own attorneys'
fees and costs, and the parties shall share equally the arbitrator's fees and administrative
costs.
""".strip(),
        parameters=[
            TemplateParameter(
                name="negotiation_start",
                description="Days to designate representatives",
                default_value="5",
            ),
            TemplateParameter(
                name="negotiation_meeting",
                description="Days to initial meeting",
                default_value="10",
            ),
            TemplateParameter(
                name="negotiation_period",
                description="Days for negotiation",
                default_value="30",
            ),
            TemplateParameter(
                name="mediator_selection",
                description="Days to select mediator",
                default_value="10",
            ),
            TemplateParameter(
                name="mediation_organization",
                description="Mediator appointment organization",
                default_value="JAMS",
                examples=["JAMS", "AAA", "ICC"],
            ),
            TemplateParameter(
                name="mediation_location",
                description="Mediation location",
                default_value="San Francisco, California",
                required=True,
            ),
            TemplateParameter(
                name="mediation_period",
                description="Days for mediation",
                default_value="45",
            ),
            TemplateParameter(
                name="mediation_costs",
                description="How mediation costs are split",
                default_value="shared equally by the parties",
            ),
            TemplateParameter(
                name="arbitration_organization",
                description="Arbitration organization",
                default_value="JAMS",
                examples=["JAMS", "AAA", "ICC"],
            ),
            TemplateParameter(
                name="arbitration_rules",
                description="Arbitration rules",
                default_value="Streamlined Arbitration Rules and Procedures",
            ),
            TemplateParameter(
                name="arbitration_location",
                description="Arbitration location",
                default_value="San Francisco, California",
                required=True,
            ),
            TemplateParameter(
                name="arbitrator_count",
                description="Number of arbitrators",
                default_value="1",
                examples=["1", "3"],
            ),
        ],
        description="Comprehensive dispute resolution with clear escalation path",
        risk_score=0.12,
        tags=["dispute", "arbitration", "mediation", "escalation"],
    ),

    # === WARRANTY TEMPLATES ===
    ClauseTemplate(
        id="warranty_limited",
        name="Limited Warranty",
        category=TemplateCategory.WARRANTY,
        license_types=[LicenseType.COMMERCIAL, LicenseType.SAAS],
        template_text="""
LIMITED WARRANTY.

PERFORMANCE WARRANTY. Licensor warrants that for a period of {warranty_period} from the
Effective Date (the "Warranty Period"), the Software will perform substantially in
accordance with the documentation provided to Licensee.

SERVICE LEVEL. For SaaS offerings, Licensor warrants an uptime of {uptime_percentage}%
measured on a {uptime_period} basis, excluding scheduled maintenance windows announced
at least {maintenance_notice} hours in advance.

EXCLUSIVE REMEDY. Licensee's exclusive remedy for breach of this warranty shall be, at
Licensor's option: (a) repair or replacement of the non-conforming Software; or (b) if
Licensor is unable to repair or replace within {remedy_period} days, termination of this
Agreement and refund of fees paid for the non-conforming Software in the {refund_period}
months preceding the warranty claim.

WARRANTY EXCLUSIONS. This warranty does not apply to: (a) issues caused by Licensee's
modification of the Software; (b) use of the Software in combination with third-party
products not approved by Licensor; (c) use of the Software other than as specified in
the documentation; or (d) issues reported more than {report_deadline} days after discovery.

DISCLAIMER. EXCEPT AS EXPRESSLY PROVIDED IN THIS SECTION, THE SOFTWARE IS PROVIDED "AS IS"
AND LICENSOR DISCLAIMS ALL OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING THE IMPLIED
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
""".strip(),
        parameters=[
            TemplateParameter(
                name="warranty_period",
                description="Duration of warranty",
                default_value="90 days",
                examples=["30 days", "90 days", "1 year"],
                required=True,
            ),
            TemplateParameter(
                name="uptime_percentage",
                description="Guaranteed uptime percentage",
                default_value="99.9",
                examples=["99", "99.5", "99.9", "99.99"],
            ),
            TemplateParameter(
                name="uptime_period",
                description="Uptime measurement period",
                default_value="monthly",
                examples=["monthly", "quarterly"],
            ),
            TemplateParameter(
                name="maintenance_notice",
                description="Hours notice for maintenance",
                default_value="48",
                examples=["24", "48", "72"],
            ),
            TemplateParameter(
                name="remedy_period",
                description="Days to repair or replace",
                default_value="30",
            ),
            TemplateParameter(
                name="refund_period",
                description="Months for refund calculation",
                default_value="3",
            ),
            TemplateParameter(
                name="report_deadline",
                description="Days to report issues",
                default_value="30",
            ),
        ],
        description="Limited warranty with clear scope and exclusive remedy",
        risk_score=0.18,
        tags=["warranty", "sla", "uptime", "exclusive-remedy"],
    ),
]


def get_default_library() -> TemplateLibrary:
    """
    Get the default template library with all pre-hardened templates.

    Returns:
        Populated TemplateLibrary
    """
    library = TemplateLibrary()

    for template in DEFAULT_TEMPLATES:
        library.add_template(template)

    return library
