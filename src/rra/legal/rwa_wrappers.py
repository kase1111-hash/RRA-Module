# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Legal Wrapper Generation module for RWA tokenization.

Provides legal documentation generation for:
- Assignment agreements
- License agreements
- Security interest documents
- Jurisdiction-specific wrappers
- Regulatory disclosures
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import hashlib
import json


class WrapperType(Enum):
    """Types of legal wrappers."""

    ASSIGNMENT_AGREEMENT = "assignment_agreement"
    LICENSE_AGREEMENT = "license_agreement"
    SECURITY_INTEREST = "security_interest"
    PLEDGE_AGREEMENT = "pledge_agreement"
    CUSTODY_AGREEMENT = "custody_agreement"
    REGULATORY_DISCLOSURE = "regulatory_disclosure"
    INVESTOR_SUBSCRIPTION = "investor_subscription"
    TRANSFER_RESTRICTION = "transfer_restriction"
    FRACTIONALIZATION_AGREEMENT = "fractionalization_agreement"
    GOVERNING_LAW = "governing_law"


class JurisdictionType(Enum):
    """Jurisdiction types for legal wrappers."""

    US_FEDERAL = "us_federal"
    US_DELAWARE = "us_delaware"
    US_NEW_YORK = "us_new_york"
    US_CALIFORNIA = "us_california"
    UK = "uk"
    EU = "eu"
    SWITZERLAND = "switzerland"
    SINGAPORE = "singapore"
    CAYMAN = "cayman"
    BVI = "bvi"
    INTERNATIONAL = "international"


class AssetClassification(Enum):
    """Asset classification for legal purposes."""

    UTILITY_TOKEN = "utility_token"
    SECURITY_TOKEN = "security_token"
    NFT = "nft"
    HYBRID = "hybrid"
    TANGIBLE_ASSET = "tangible_asset"
    INTANGIBLE_ASSET = "intangible_asset"


@dataclass
class LegalParty:
    """Party to a legal agreement."""

    name: str
    legal_type: str  # individual, corporation, llc, trust, etc.
    jurisdiction: str
    registration_number: Optional[str] = None  # EIN, company number, etc.
    address: Optional[str] = None
    wallet_address: Optional[str] = None
    authorized_signatory: Optional[str] = None
    email: Optional[str] = None


@dataclass
class WrapperClause:
    """A clause within a legal wrapper."""

    clause_id: str
    title: str
    content: str
    is_required: bool = True
    is_negotiable: bool = False
    jurisdiction_specific: Optional[str] = None
    regulatory_reference: Optional[str] = None


@dataclass
class WrapperTemplate:
    """Template for generating legal wrappers."""

    template_id: str
    wrapper_type: WrapperType
    jurisdiction: JurisdictionType
    asset_classification: AssetClassification
    version: str

    title: str
    preamble: str
    clauses: List[WrapperClause] = field(default_factory=list)
    definitions: Dict[str, str] = field(default_factory=dict)
    schedules: List[str] = field(default_factory=list)

    requires_notarization: bool = False
    requires_witness: bool = False
    regulatory_filings: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GeneratedWrapper:
    """A generated legal wrapper document."""

    wrapper_id: str
    template_id: str
    wrapper_type: WrapperType
    jurisdiction: JurisdictionType

    # Parties
    parties: List[LegalParty] = field(default_factory=list)

    # Asset details
    asset_id: str = ""
    token_id: Optional[int] = None
    contract_address: Optional[str] = None
    asset_description: str = ""
    asset_value: Optional[Decimal] = None

    # Document content
    title: str = ""
    content: str = ""
    content_hash: str = ""

    # Execution
    execution_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None

    # Signatures
    signatures: Dict[str, str] = field(default_factory=dict)
    witnesses: List[str] = field(default_factory=list)
    notarized: bool = False
    notary_info: Optional[str] = None

    # Storage
    ipfs_hash: Optional[str] = None
    on_chain_reference: Optional[str] = None

    # Status
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.utcnow)


class LegalWrapperGenerator:
    """
    Generator for legal wrapper documents.

    Creates legally-compliant documentation for RWA tokenization.
    """

    def __init__(self):
        self._templates: Dict[str, WrapperTemplate] = {}
        self._wrappers: Dict[str, GeneratedWrapper] = {}
        self._wrapper_counter = 0

        # Initialize default templates
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Initialize default legal wrapper templates."""
        # Assignment Agreement - US Delaware
        self._templates["assignment_delaware"] = WrapperTemplate(
            template_id="assignment_delaware",
            wrapper_type=WrapperType.ASSIGNMENT_AGREEMENT,
            jurisdiction=JurisdictionType.US_DELAWARE,
            asset_classification=AssetClassification.INTANGIBLE_ASSET,
            version="1.0",
            title="Assignment of Intellectual Property Rights",
            preamble="This Assignment Agreement (the 'Agreement') is entered into as of {effective_date}.",
            clauses=[
                WrapperClause(
                    clause_id="assignment_1",
                    title="Assignment",
                    content="Assignor hereby assigns, transfers, and conveys to Assignee all right, title, and interest in and to the Intellectual Property described in Schedule A.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="assignment_2",
                    title="Consideration",
                    content="In consideration for the assignment, Assignee shall pay to Assignor the sum of {consideration_amount}.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="assignment_3",
                    title="Representations and Warranties",
                    content="Assignor represents and warrants that: (a) Assignor is the sole owner of the Intellectual Property; (b) the Intellectual Property is free and clear of all liens and encumbrances.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="assignment_4",
                    title="Tokenization Authorization",
                    content="Assignor authorizes the tokenization of the assigned Intellectual Property on the blockchain network specified in Schedule B.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="assignment_5",
                    title="Governing Law",
                    content="This Agreement shall be governed by the laws of the State of Delaware.",
                    is_required=True,
                ),
            ],
            definitions={
                "Intellectual Property": "The patents, trademarks, copyrights, and other IP rights described in Schedule A.",
                "Assignor": "The party transferring the Intellectual Property.",
                "Assignee": "The party receiving the Intellectual Property.",
            },
            schedules=[
                "Schedule A: Description of Intellectual Property",
                "Schedule B: Blockchain Details",
            ],
            requires_notarization=False,
        )

        # Security Interest - US UCC
        self._templates["security_ucc"] = WrapperTemplate(
            template_id="security_ucc",
            wrapper_type=WrapperType.SECURITY_INTEREST,
            jurisdiction=JurisdictionType.US_FEDERAL,
            asset_classification=AssetClassification.INTANGIBLE_ASSET,
            version="1.0",
            title="Security Agreement (UCC Article 9)",
            preamble="This Security Agreement (the 'Agreement') is entered into to grant a security interest in the Collateral.",
            clauses=[
                WrapperClause(
                    clause_id="security_1",
                    title="Grant of Security Interest",
                    content="Debtor hereby grants to Secured Party a continuing security interest in the Collateral to secure the Obligations.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="security_2",
                    title="Collateral Description",
                    content="The Collateral consists of the tokenized intellectual property with Token ID {token_id} on contract {contract_address}.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="security_3",
                    title="Perfection",
                    content="Secured Party may file UCC-1 financing statements to perfect its security interest.",
                    is_required=True,
                ),
            ],
            definitions={
                "Collateral": "The tokenized intellectual property and all proceeds thereof.",
                "Obligations": "All debts, liabilities, and obligations of Debtor to Secured Party.",
            },
            regulatory_filings=["UCC-1 Financing Statement"],
        )

        # License Agreement
        self._templates["license_standard"] = WrapperTemplate(
            template_id="license_standard",
            wrapper_type=WrapperType.LICENSE_AGREEMENT,
            jurisdiction=JurisdictionType.INTERNATIONAL,
            asset_classification=AssetClassification.INTANGIBLE_ASSET,
            version="1.0",
            title="Intellectual Property License Agreement",
            preamble="This License Agreement grants specific rights to use the licensed Intellectual Property.",
            clauses=[
                WrapperClause(
                    clause_id="license_1",
                    title="License Grant",
                    content="Licensor grants to Licensee a {license_type} license to use the Licensed IP for the purposes described herein.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="license_2",
                    title="Scope and Territory",
                    content="This license is {exclusivity} and covers the territory of {territory}.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="license_3",
                    title="Royalties",
                    content="Licensee shall pay royalties of {royalty_rate} on all revenue derived from the Licensed IP.",
                    is_required=True,
                    is_negotiable=True,
                ),
                WrapperClause(
                    clause_id="license_4",
                    title="Term",
                    content="This license shall commence on {start_date} and continue until {end_date}.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="license_5",
                    title="Blockchain Enforcement",
                    content="License terms are enforced through smart contract at address {contract_address}.",
                    is_required=True,
                ),
            ],
            definitions={
                "Licensed IP": "The intellectual property subject to this license.",
                "Revenue": "All income derived from use of the Licensed IP.",
            },
        )

        # Investor Subscription - Reg D
        self._templates["subscription_reg_d"] = WrapperTemplate(
            template_id="subscription_reg_d",
            wrapper_type=WrapperType.INVESTOR_SUBSCRIPTION,
            jurisdiction=JurisdictionType.US_FEDERAL,
            asset_classification=AssetClassification.SECURITY_TOKEN,
            version="1.0",
            title="Subscription Agreement (Regulation D)",
            preamble="This Subscription Agreement is for the purchase of security tokens representing fractional ownership in real-world assets.",
            clauses=[
                WrapperClause(
                    clause_id="sub_1",
                    title="Subscription",
                    content="Subscriber hereby subscribes to purchase {token_amount} tokens at a price of {price_per_token} per token.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="sub_2",
                    title="Accredited Investor Representations",
                    content="Subscriber represents that it is an 'accredited investor' as defined in Rule 501(a) of Regulation D.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="sub_3",
                    title="Transfer Restrictions",
                    content="The tokens are subject to a one-year holding period and may only be transferred in compliance with Rule 144.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="sub_4",
                    title="Risk Factors",
                    content="Subscriber acknowledges receipt of and has reviewed the risk factors set forth in the Private Placement Memorandum.",
                    is_required=True,
                ),
            ],
            requires_notarization=False,
            regulatory_filings=["Form D", "Blue Sky Filings"],
        )

        # Fractionalization Agreement
        self._templates["fractionalization"] = WrapperTemplate(
            template_id="fractionalization",
            wrapper_type=WrapperType.FRACTIONALIZATION_AGREEMENT,
            jurisdiction=JurisdictionType.US_DELAWARE,
            asset_classification=AssetClassification.HYBRID,
            version="1.0",
            title="Asset Fractionalization Agreement",
            preamble="This Agreement governs the fractionalization of a tokenized real-world asset into multiple ownership interests.",
            clauses=[
                WrapperClause(
                    clause_id="frac_1",
                    title="Fractionalization",
                    content="The Asset shall be divided into {total_fractions} fractional interests, each represented by an ERC-20 token.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="frac_2",
                    title="Rights of Fraction Holders",
                    content="Each fraction holder has a pro-rata right to: (a) income distributions; (b) voting on major decisions; (c) proceeds upon sale.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="frac_3",
                    title="Management",
                    content="The Asset shall be managed by {manager} pursuant to the terms of the Management Agreement.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="frac_4",
                    title="Buyout Rights",
                    content="A holder of {buyout_threshold}% or more of fractions may trigger a buyout of remaining holders.",
                    is_required=True,
                    is_negotiable=True,
                ),
            ],
            definitions={
                "Asset": "The underlying tokenized real-world asset.",
                "Fractions": "The ERC-20 tokens representing ownership interests.",
            },
        )

        # Custody Agreement
        self._templates["custody_physical"] = WrapperTemplate(
            template_id="custody_physical",
            wrapper_type=WrapperType.CUSTODY_AGREEMENT,
            jurisdiction=JurisdictionType.INTERNATIONAL,
            asset_classification=AssetClassification.TANGIBLE_ASSET,
            version="1.0",
            title="Physical Asset Custody Agreement",
            preamble="This Agreement governs the custody of physical assets underlying tokenized securities.",
            clauses=[
                WrapperClause(
                    clause_id="custody_1",
                    title="Appointment of Custodian",
                    content="Owner appoints Custodian to hold, safeguard, and maintain the Physical Assets.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="custody_2",
                    title="Custody Location",
                    content="The Physical Assets shall be held at {custody_location}.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="custody_3",
                    title="Insurance",
                    content="Custodian shall maintain insurance coverage of at least {insurance_amount} for the Physical Assets.",
                    is_required=True,
                ),
                WrapperClause(
                    clause_id="custody_4",
                    title="Token-Linked Custody",
                    content="Custody rights are linked to ownership of Token ID {token_id}. Upon transfer, custody rights transfer automatically.",
                    is_required=True,
                ),
            ],
            definitions={
                "Physical Assets": "The tangible items subject to this custody arrangement.",
                "Custodian": "The party responsible for holding the Physical Assets.",
            },
        )

    def get_template(self, template_id: str) -> Optional[WrapperTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(
        self,
        wrapper_type: Optional[WrapperType] = None,
        jurisdiction: Optional[JurisdictionType] = None,
    ) -> List[WrapperTemplate]:
        """List available templates with optional filters."""
        templates = list(self._templates.values())

        if wrapper_type:
            templates = [t for t in templates if t.wrapper_type == wrapper_type]

        if jurisdiction:
            templates = [t for t in templates if t.jurisdiction == jurisdiction]

        return templates

    def generate_wrapper(
        self,
        template_id: str,
        parties: List[LegalParty],
        asset_id: str,
        parameters: Dict[str, Any],
        token_id: Optional[int] = None,
        contract_address: Optional[str] = None,
        effective_date: Optional[datetime] = None,
        expiration_date: Optional[datetime] = None,
    ) -> GeneratedWrapper:
        """Generate a legal wrapper from a template."""
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        if len(parties) < 2:
            raise ValueError("At least two parties required")

        self._wrapper_counter += 1
        wrapper_id = f"wrapper_{self._wrapper_counter}"

        # Build document content
        content = self._build_document_content(template, parties, parameters)
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        wrapper = GeneratedWrapper(
            wrapper_id=wrapper_id,
            template_id=template_id,
            wrapper_type=template.wrapper_type,
            jurisdiction=template.jurisdiction,
            parties=parties,
            asset_id=asset_id,
            token_id=token_id,
            contract_address=contract_address,
            asset_description=parameters.get("asset_description", ""),
            asset_value=parameters.get("asset_value"),
            title=template.title,
            content=content,
            content_hash=content_hash,
            effective_date=effective_date or datetime.utcnow(),
            expiration_date=expiration_date,
            status="draft",
        )

        self._wrappers[wrapper_id] = wrapper
        return wrapper

    def sign_wrapper(self, wrapper_id: str, party_wallet: str, signature: str) -> GeneratedWrapper:
        """Add a signature to a wrapper."""
        wrapper = self._wrappers.get(wrapper_id)
        if not wrapper:
            raise ValueError(f"Wrapper {wrapper_id} not found")

        # Verify party is in the agreement
        party_found = False
        for party in wrapper.parties:
            if party.wallet_address and party.wallet_address.lower() == party_wallet.lower():
                party_found = True
                break

        if not party_found:
            raise ValueError("Signing party not found in agreement")

        wrapper.signatures[party_wallet] = signature

        # Check if all parties have signed
        required_signatures = len([p for p in wrapper.parties if p.wallet_address])
        if len(wrapper.signatures) >= required_signatures:
            wrapper.status = "fully_signed"
            wrapper.execution_date = datetime.utcnow()
        else:
            wrapper.status = "partially_signed"

        return wrapper

    def add_witness(self, wrapper_id: str, witness_info: str) -> GeneratedWrapper:
        """Add a witness to a wrapper."""
        wrapper = self._wrappers.get(wrapper_id)
        if not wrapper:
            raise ValueError(f"Wrapper {wrapper_id} not found")

        wrapper.witnesses.append(witness_info)
        return wrapper

    def notarize_wrapper(self, wrapper_id: str, notary_info: str) -> GeneratedWrapper:
        """Record notarization of a wrapper."""
        wrapper = self._wrappers.get(wrapper_id)
        if not wrapper:
            raise ValueError(f"Wrapper {wrapper_id} not found")

        if wrapper.status != "fully_signed":
            raise ValueError("Wrapper must be fully signed before notarization")

        wrapper.notarized = True
        wrapper.notary_info = notary_info
        wrapper.status = "executed"

        return wrapper

    def store_on_ipfs(self, wrapper_id: str, ipfs_hash: str) -> GeneratedWrapper:
        """Record IPFS storage of wrapper."""
        wrapper = self._wrappers.get(wrapper_id)
        if not wrapper:
            raise ValueError(f"Wrapper {wrapper_id} not found")

        wrapper.ipfs_hash = ipfs_hash
        return wrapper

    def link_to_chain(self, wrapper_id: str, on_chain_reference: str) -> GeneratedWrapper:
        """Link wrapper to on-chain record."""
        wrapper = self._wrappers.get(wrapper_id)
        if not wrapper:
            raise ValueError(f"Wrapper {wrapper_id} not found")

        wrapper.on_chain_reference = on_chain_reference
        return wrapper

    def get_wrapper(self, wrapper_id: str) -> Optional[GeneratedWrapper]:
        """Get a wrapper by ID."""
        return self._wrappers.get(wrapper_id)

    def get_wrappers_for_asset(self, asset_id: str) -> List[GeneratedWrapper]:
        """Get all wrappers for an asset."""
        return [w for w in self._wrappers.values() if w.asset_id == asset_id]

    def _build_document_content(
        self, template: WrapperTemplate, parties: List[LegalParty], parameters: Dict[str, Any]
    ) -> str:
        """Build document content from template."""
        lines = []

        # Title
        lines.append(f"# {template.title}")
        lines.append("")

        # Preamble
        preamble = template.preamble
        for key, value in parameters.items():
            preamble = preamble.replace(f"{{{key}}}", str(value))
        lines.append(preamble)
        lines.append("")

        # Parties
        lines.append("## PARTIES")
        lines.append("")
        for i, party in enumerate(parties, 1):
            role = ["Assignor/Licensor", "Assignee/Licensee", "Third Party"][min(i - 1, 2)]
            lines.append(f"**{role}:** {party.name}")
            lines.append(f"- Type: {party.legal_type}")
            lines.append(f"- Jurisdiction: {party.jurisdiction}")
            if party.registration_number:
                lines.append(f"- Registration: {party.registration_number}")
            if party.wallet_address:
                lines.append(f"- Wallet: {party.wallet_address}")
            lines.append("")

        # Definitions
        if template.definitions:
            lines.append("## DEFINITIONS")
            lines.append("")
            for term, definition in template.definitions.items():
                lines.append(f'**"{term}"** means {definition}')
                lines.append("")

        # Clauses
        lines.append("## TERMS AND CONDITIONS")
        lines.append("")
        for i, clause in enumerate(template.clauses, 1):
            content = clause.content
            for key, value in parameters.items():
                content = content.replace(f"{{{key}}}", str(value))

            lines.append(f"### {i}. {clause.title}")
            lines.append("")
            lines.append(content)
            lines.append("")

        # Schedules
        if template.schedules:
            lines.append("## SCHEDULES")
            lines.append("")
            for schedule in template.schedules:
                lines.append(f"- {schedule}")
            lines.append("")

        # Execution block
        lines.append("## EXECUTION")
        lines.append("")
        lines.append("IN WITNESS WHEREOF, the parties have executed this Agreement.")
        lines.append("")
        for party in parties:
            lines.append(f"**{party.name}**")
            lines.append("")
            lines.append("Signature: _______________________")
            lines.append(f"Name: {party.authorized_signatory or party.name}")
            lines.append("Date: _______________________")
            lines.append("")

        return "\n".join(lines)

    def export_to_json(self, wrapper_id: str) -> str:
        """Export wrapper metadata to JSON."""
        wrapper = self._wrappers.get(wrapper_id)
        if not wrapper:
            raise ValueError(f"Wrapper {wrapper_id} not found")

        data = {
            "wrapper_id": wrapper.wrapper_id,
            "template_id": wrapper.template_id,
            "wrapper_type": wrapper.wrapper_type.value,
            "jurisdiction": wrapper.jurisdiction.value,
            "asset_id": wrapper.asset_id,
            "token_id": wrapper.token_id,
            "contract_address": wrapper.contract_address,
            "content_hash": wrapper.content_hash,
            "status": wrapper.status,
            "signatures": wrapper.signatures,
            "ipfs_hash": wrapper.ipfs_hash,
            "on_chain_reference": wrapper.on_chain_reference,
            "created_at": wrapper.created_at.isoformat(),
            "effective_date": (
                wrapper.effective_date.isoformat() if wrapper.effective_date else None
            ),
            "execution_date": (
                wrapper.execution_date.isoformat() if wrapper.execution_date else None
            ),
        }

        return json.dumps(data, indent=2)


def create_wrapper_generator() -> LegalWrapperGenerator:
    """Factory function to create a LegalWrapperGenerator."""
    return LegalWrapperGenerator()
