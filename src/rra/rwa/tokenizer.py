# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Asset Tokenization module for Real-World Assets.

Provides tokenization capabilities for:
- Patents (utility, design, plant)
- Trademarks (word marks, logos, trade dress)
- Copyrights (literary, artistic, software)
- Trade secrets
- Physical IP (prototypes, samples, designs)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
import hashlib
import json
import uuid


class AssetType(Enum):
    """Types of real-world assets that can be tokenized."""

    PATENT_UTILITY = "patent_utility"
    PATENT_DESIGN = "patent_design"
    PATENT_PLANT = "patent_plant"
    TRADEMARK_WORD = "trademark_word"
    TRADEMARK_LOGO = "trademark_logo"
    TRADEMARK_TRADE_DRESS = "trademark_trade_dress"
    COPYRIGHT_LITERARY = "copyright_literary"
    COPYRIGHT_ARTISTIC = "copyright_artistic"
    COPYRIGHT_SOFTWARE = "copyright_software"
    TRADE_SECRET = "trade_secret"
    PHYSICAL_IP = "physical_ip"
    HYBRID = "hybrid"


class TokenizationStatus(Enum):
    """Status of tokenization process."""

    DRAFT = "draft"
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    TOKENIZED = "tokenized"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class RegistrationAuthority(Enum):
    """Known IP registration authorities."""

    USPTO = "USPTO"  # US Patent and Trademark Office
    EPO = "EPO"  # European Patent Office
    WIPO = "WIPO"  # World Intellectual Property Organization
    JPO = "JPO"  # Japan Patent Office
    CNIPA = "CNIPA"  # China National Intellectual Property Administration
    UKIPO = "UKIPO"  # UK Intellectual Property Office
    INPI_FR = "INPI_FR"  # French National Industrial Property Institute
    DPMA = "DPMA"  # German Patent and Trade Mark Office
    KIPO = "KIPO"  # Korean Intellectual Property Office
    CIPO = "CIPO"  # Canadian Intellectual Property Office
    IP_AUSTRALIA = "IP_AUSTRALIA"  # IP Australia
    USCO = "USCO"  # US Copyright Office
    OTHER = "OTHER"


@dataclass
class AssetDocumentation:
    """Documentation for a real-world asset."""

    document_type: str  # registration_certificate, assignment, etc.
    document_hash: str  # IPFS or content hash
    description: str
    upload_date: datetime
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None


@dataclass
class OwnershipRecord:
    """Record of ownership for an asset."""

    owner_address: str
    ownership_percentage: Decimal  # 0-100
    acquired_date: datetime
    acquisition_type: str  # original, purchase, assignment, inheritance
    previous_owner: Optional[str] = None
    transaction_hash: Optional[str] = None


@dataclass
class RWAMetadata:
    """Metadata for a real-world asset."""

    asset_id: str
    asset_type: AssetType
    title: str
    description: str

    # Registration details
    registration_number: str
    registration_authority: RegistrationAuthority
    registration_date: datetime
    expiration_date: Optional[datetime]  # None for perpetual

    # Jurisdiction
    origin_jurisdiction: str  # ISO 3166-1 alpha-2
    allowed_jurisdictions: List[str] = field(default_factory=list)

    # Physical asset tracking
    is_physical_asset: bool = False
    physical_location: Optional[str] = None
    custodian: Optional[str] = None

    # Documentation
    documents: List[AssetDocumentation] = field(default_factory=list)
    legal_description_hash: Optional[str] = None

    # Ownership
    ownership_records: List[OwnershipRecord] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TokenizationRequest:
    """Request to tokenize a real-world asset."""

    request_id: str
    asset_metadata: RWAMetadata
    requester_address: str
    minimum_price: Decimal
    royalty_basis_points: int  # 0-10000

    # Token details
    token_uri: Optional[str] = None

    # Status tracking
    status: TokenizationStatus = TokenizationStatus.DRAFT
    verification_notes: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    tokenized_at: Optional[datetime] = None

    # On-chain details (populated after tokenization)
    token_id: Optional[int] = None
    transaction_hash: Optional[str] = None


@dataclass
class TokenizedAsset:
    """A tokenized real-world asset."""

    token_id: int
    contract_address: str
    metadata: RWAMetadata

    # Pricing
    minimum_price: Decimal
    royalty_basis_points: int

    # Valuation
    current_valuation: Optional[Decimal] = None
    last_valuation_date: Optional[datetime] = None
    valuation_confidence: Optional[int] = None  # 0-10000

    # Compliance
    compliance_status: str = "pending"
    transfer_restricted: bool = True

    # Fractionalization
    is_fractionalized: bool = False
    fractional_contract: Optional[str] = None

    # Legal wrapper
    legal_wrapper_hash: Optional[str] = None

    # Status
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class AssetTokenizer:
    """
    Tokenizer for real-world assets.

    Handles the process of converting real-world IP into on-chain tokens:
    1. Asset metadata collection and validation
    2. Documentation verification
    3. Compliance checks
    4. Token minting
    5. Post-tokenization management
    """

    def __init__(
        self, contract_address: Optional[str] = None, compliance_verifier: Optional[str] = None
    ):
        self.contract_address = contract_address
        self.compliance_verifier = compliance_verifier

        # In-memory storage (replace with database in production)
        self._requests: Dict[str, TokenizationRequest] = {}
        self._assets: Dict[int, TokenizedAsset] = {}
        self._next_token_id = 1

        # Supported asset types by authority
        self._authority_asset_types: Dict[RegistrationAuthority, List[AssetType]] = {
            RegistrationAuthority.USPTO: [
                AssetType.PATENT_UTILITY,
                AssetType.PATENT_DESIGN,
                AssetType.PATENT_PLANT,
                AssetType.TRADEMARK_WORD,
                AssetType.TRADEMARK_LOGO,
                AssetType.TRADEMARK_TRADE_DRESS,
            ],
            RegistrationAuthority.USCO: [
                AssetType.COPYRIGHT_LITERARY,
                AssetType.COPYRIGHT_ARTISTIC,
                AssetType.COPYRIGHT_SOFTWARE,
            ],
            RegistrationAuthority.EPO: [
                AssetType.PATENT_UTILITY,
                AssetType.PATENT_DESIGN,
            ],
            RegistrationAuthority.WIPO: [
                AssetType.PATENT_UTILITY,
                AssetType.PATENT_DESIGN,
                AssetType.TRADEMARK_WORD,
                AssetType.TRADEMARK_LOGO,
            ],
        }

        # Default expiration periods by asset type (in years)
        self._default_expirations: Dict[AssetType, Optional[int]] = {
            AssetType.PATENT_UTILITY: 20,
            AssetType.PATENT_DESIGN: 15,
            AssetType.PATENT_PLANT: 20,
            AssetType.TRADEMARK_WORD: 10,  # Renewable
            AssetType.TRADEMARK_LOGO: 10,  # Renewable
            AssetType.TRADEMARK_TRADE_DRESS: 10,  # Renewable
            AssetType.COPYRIGHT_LITERARY: 70,  # Life + 70 years
            AssetType.COPYRIGHT_ARTISTIC: 70,
            AssetType.COPYRIGHT_SOFTWARE: 70,
            AssetType.TRADE_SECRET: None,  # Perpetual while secret
            AssetType.PHYSICAL_IP: None,
            AssetType.HYBRID: None,
        }

    def create_tokenization_request(
        self,
        asset_type: AssetType,
        title: str,
        description: str,
        registration_number: str,
        registration_authority: RegistrationAuthority,
        registration_date: datetime,
        origin_jurisdiction: str,
        requester_address: str,
        minimum_price: Decimal,
        royalty_basis_points: int,
        expiration_date: Optional[datetime] = None,
        is_physical_asset: bool = False,
        physical_location: Optional[str] = None,
        custodian: Optional[str] = None,
        allowed_jurisdictions: Optional[List[str]] = None,
    ) -> TokenizationRequest:
        """Create a new tokenization request for a real-world asset."""
        # Validate inputs
        if royalty_basis_points < 0 or royalty_basis_points > 10000:
            raise ValueError("Royalty basis points must be between 0 and 10000")

        if minimum_price < 0:
            raise ValueError("Minimum price cannot be negative")

        if len(origin_jurisdiction) != 2:
            raise ValueError("Origin jurisdiction must be ISO 3166-1 alpha-2 code")

        # Generate IDs
        request_id = str(uuid.uuid4())
        asset_id = str(uuid.uuid4())

        # Calculate expiration if not provided
        if expiration_date is None and self._default_expirations.get(asset_type):
            years = self._default_expirations[asset_type]
            expiration_date = registration_date + timedelta(days=years * 365)

        # Create metadata
        metadata = RWAMetadata(
            asset_id=asset_id,
            asset_type=asset_type,
            title=title,
            description=description,
            registration_number=registration_number,
            registration_authority=registration_authority,
            registration_date=registration_date,
            expiration_date=expiration_date,
            origin_jurisdiction=origin_jurisdiction,
            allowed_jurisdictions=allowed_jurisdictions or [origin_jurisdiction],
            is_physical_asset=is_physical_asset,
            physical_location=physical_location,
            custodian=custodian,
        )

        # Add initial ownership record
        metadata.ownership_records.append(
            OwnershipRecord(
                owner_address=requester_address,
                ownership_percentage=Decimal("100"),
                acquired_date=datetime.utcnow(),
                acquisition_type="original",
            )
        )

        # Create request
        request = TokenizationRequest(
            request_id=request_id,
            asset_metadata=metadata,
            requester_address=requester_address,
            minimum_price=minimum_price,
            royalty_basis_points=royalty_basis_points,
            status=TokenizationStatus.DRAFT,
        )

        self._requests[request_id] = request
        return request

    def add_document(
        self, request_id: str, document_type: str, document_hash: str, description: str
    ) -> AssetDocumentation:
        """Add documentation to a tokenization request."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status not in [
            TokenizationStatus.DRAFT,
            TokenizationStatus.PENDING_VERIFICATION,
        ]:
            raise ValueError("Cannot add documents after verification")

        doc = AssetDocumentation(
            document_type=document_type,
            document_hash=document_hash,
            description=description,
            upload_date=datetime.utcnow(),
        )

        request.asset_metadata.documents.append(doc)
        request.asset_metadata.updated_at = datetime.utcnow()

        return doc

    def submit_for_verification(self, request_id: str) -> TokenizationRequest:
        """Submit a tokenization request for verification."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != TokenizationStatus.DRAFT:
            raise ValueError("Request is not in draft status")

        # Validate required documents
        required_doc_types = self._get_required_documents(request.asset_metadata.asset_type)
        existing_doc_types = {doc.document_type for doc in request.asset_metadata.documents}

        missing_docs = required_doc_types - existing_doc_types
        if missing_docs:
            raise ValueError(f"Missing required documents: {missing_docs}")

        request.status = TokenizationStatus.PENDING_VERIFICATION
        request.submitted_at = datetime.utcnow()

        return request

    def verify_request(
        self,
        request_id: str,
        verifier_address: str,
        approved: bool,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None,
    ) -> TokenizationRequest:
        """Verify a tokenization request."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != TokenizationStatus.PENDING_VERIFICATION:
            raise ValueError("Request is not pending verification")

        if approved:
            request.status = TokenizationStatus.VERIFIED
            request.verified_at = datetime.utcnow()

            # Mark all documents as verified
            for doc in request.asset_metadata.documents:
                doc.verified = True
                doc.verified_by = verifier_address
                doc.verified_at = datetime.utcnow()
        else:
            request.status = TokenizationStatus.DRAFT  # Return to draft for fixes
            request.rejection_reason = rejection_reason

        if notes:
            request.verification_notes.append(f"[{datetime.utcnow().isoformat()}] {notes}")

        return request

    def tokenize(self, request_id: str, token_uri: str) -> TokenizedAsset:
        """Tokenize a verified request, creating on-chain token."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != TokenizationStatus.VERIFIED:
            raise ValueError("Request must be verified before tokenization")

        # Assign token ID
        token_id = self._next_token_id
        self._next_token_id += 1

        # Create tokenized asset
        asset = TokenizedAsset(
            token_id=token_id,
            contract_address=self.contract_address or "0x0000000000000000000000000000000000000000",
            metadata=request.asset_metadata,
            minimum_price=request.minimum_price,
            royalty_basis_points=request.royalty_basis_points,
            compliance_status="pending",
            transfer_restricted=True,
        )

        # Update request
        request.status = TokenizationStatus.TOKENIZED
        request.tokenized_at = datetime.utcnow()
        request.token_id = token_id
        request.token_uri = token_uri

        # Generate mock transaction hash
        request.transaction_hash = self._generate_mock_tx_hash(request_id, token_id)

        self._assets[token_id] = asset
        return asset

    def get_request(self, request_id: str) -> Optional[TokenizationRequest]:
        """Get a tokenization request by ID."""
        return self._requests.get(request_id)

    def get_asset(self, token_id: int) -> Optional[TokenizedAsset]:
        """Get a tokenized asset by token ID."""
        return self._assets.get(token_id)

    def get_assets_by_owner(self, owner_address: str) -> List[TokenizedAsset]:
        """Get all tokenized assets owned by an address."""
        result = []
        for asset in self._assets.values():
            for record in asset.metadata.ownership_records:
                if record.owner_address.lower() == owner_address.lower():
                    if record.ownership_percentage > 0:
                        result.append(asset)
                        break
        return result

    def get_assets_by_type(self, asset_type: AssetType) -> List[TokenizedAsset]:
        """Get all tokenized assets of a specific type."""
        return [asset for asset in self._assets.values() if asset.metadata.asset_type == asset_type]

    def get_assets_by_jurisdiction(self, jurisdiction: str) -> List[TokenizedAsset]:
        """Get all tokenized assets allowed in a jurisdiction."""
        return [
            asset
            for asset in self._assets.values()
            if jurisdiction in asset.metadata.allowed_jurisdictions
        ]

    def update_valuation(
        self,
        token_id: int,
        valuation: Decimal,
        confidence: int,
        oracle_address: Optional[str] = None,
    ) -> TokenizedAsset:
        """Update the valuation for a tokenized asset."""
        asset = self._assets.get(token_id)
        if not asset:
            raise ValueError(f"Asset {token_id} not found")

        if confidence < 0 or confidence > 10000:
            raise ValueError("Confidence must be between 0 and 10000")

        asset.current_valuation = valuation
        asset.last_valuation_date = datetime.utcnow()
        asset.valuation_confidence = confidence

        return asset

    def update_compliance_status(
        self, token_id: int, status: str, transfer_restricted: Optional[bool] = None
    ) -> TokenizedAsset:
        """Update compliance status for a tokenized asset."""
        asset = self._assets.get(token_id)
        if not asset:
            raise ValueError(f"Asset {token_id} not found")

        valid_statuses = ["pending", "verified", "requires_update", "suspended", "revoked"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        asset.compliance_status = status
        if transfer_restricted is not None:
            asset.transfer_restricted = transfer_restricted

        return asset

    def set_fractionalized(self, token_id: int, fractional_contract: str) -> TokenizedAsset:
        """Mark an asset as fractionalized."""
        asset = self._assets.get(token_id)
        if not asset:
            raise ValueError(f"Asset {token_id} not found")

        if asset.is_fractionalized:
            raise ValueError("Asset is already fractionalized")

        asset.is_fractionalized = True
        asset.fractional_contract = fractional_contract

        return asset

    def update_legal_wrapper(self, token_id: int, wrapper_hash: str) -> TokenizedAsset:
        """Update the legal wrapper for a tokenized asset."""
        asset = self._assets.get(token_id)
        if not asset:
            raise ValueError(f"Asset {token_id} not found")

        asset.legal_wrapper_hash = wrapper_hash

        return asset

    def generate_token_metadata(self, token_id: int) -> Dict[str, Any]:
        """Generate ERC721 token metadata for an asset."""
        asset = self._assets.get(token_id)
        if not asset:
            raise ValueError(f"Asset {token_id} not found")

        metadata = asset.metadata

        return {
            "name": metadata.title,
            "description": metadata.description,
            "image": (
                f"ipfs://{metadata.legal_description_hash}"
                if metadata.legal_description_hash
                else None
            ),
            "external_url": f"https://rra.module/assets/{token_id}",
            "attributes": [
                {"trait_type": "Asset Type", "value": metadata.asset_type.value},
                {"trait_type": "Registration Number", "value": metadata.registration_number},
                {
                    "trait_type": "Registration Authority",
                    "value": metadata.registration_authority.value,
                },
                {"trait_type": "Origin Jurisdiction", "value": metadata.origin_jurisdiction},
                {
                    "trait_type": "Registration Date",
                    "value": metadata.registration_date.isoformat(),
                },
                {
                    "trait_type": "Expiration Date",
                    "value": (
                        metadata.expiration_date.isoformat()
                        if metadata.expiration_date
                        else "Perpetual"
                    ),
                },
                {
                    "trait_type": "Physical Asset",
                    "value": "Yes" if metadata.is_physical_asset else "No",
                },
                {"trait_type": "Compliance Status", "value": asset.compliance_status},
                {
                    "trait_type": "Transfer Restricted",
                    "value": "Yes" if asset.transfer_restricted else "No",
                },
                {
                    "trait_type": "Fractionalized",
                    "value": "Yes" if asset.is_fractionalized else "No",
                },
            ],
            "properties": {
                "royalty_basis_points": asset.royalty_basis_points,
                "minimum_price": str(asset.minimum_price),
                "current_valuation": (
                    str(asset.current_valuation) if asset.current_valuation else None
                ),
                "allowed_jurisdictions": metadata.allowed_jurisdictions,
            },
        }

    def _get_required_documents(self, asset_type: AssetType) -> set:
        """Get required document types for an asset type."""
        base_docs = {"registration_certificate", "proof_of_ownership"}

        type_specific = {
            AssetType.PATENT_UTILITY: {"claims_document", "drawings"},
            AssetType.PATENT_DESIGN: {"design_drawings"},
            AssetType.PATENT_PLANT: {"botanical_description"},
            AssetType.TRADEMARK_WORD: {"specimen"},
            AssetType.TRADEMARK_LOGO: {"logo_image", "specimen"},
            AssetType.TRADEMARK_TRADE_DRESS: {"trade_dress_photos"},
            AssetType.COPYRIGHT_LITERARY: {"work_copy"},
            AssetType.COPYRIGHT_ARTISTIC: {"work_images"},
            AssetType.COPYRIGHT_SOFTWARE: {"source_description"},
            AssetType.TRADE_SECRET: {"confidentiality_agreement"},
            AssetType.PHYSICAL_IP: {"custody_agreement", "physical_description"},
            AssetType.HYBRID: set(),
        }

        return base_docs | type_specific.get(asset_type, set())

    def _generate_mock_tx_hash(self, request_id: str, token_id: int) -> str:
        """Generate a mock transaction hash for testing."""
        data = f"{request_id}:{token_id}:{datetime.utcnow().isoformat()}"
        return "0x" + hashlib.sha256(data.encode()).hexdigest()


def create_tokenizer(
    contract_address: Optional[str] = None, compliance_verifier: Optional[str] = None
) -> AssetTokenizer:
    """Factory function to create an AssetTokenizer instance."""
    return AssetTokenizer(
        contract_address=contract_address, compliance_verifier=compliance_verifier
    )
