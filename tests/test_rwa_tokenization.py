# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for Phase 6.11: Tokenized Real-World Assets.

Tests cover:
- Asset tokenization workflow
- RWA compliance checks
- Valuation oracles
- Legal wrapper generation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from rra.rwa import (
    AssetType,
    TokenizationStatus,
    RegistrationAuthority,
    AssetDocumentation,
    OwnershipRecord,
    RWAMetadata,
    TokenizationRequest,
    TokenizedAsset,
    AssetTokenizer,
    create_tokenizer,
    ComplianceStatus,
    KYCStatus,
    AccreditationType,
    RegulationType,
    JurisdictionRules,
    ParticipantProfile,
    ComplianceCheck,
    ComplianceReport,
    RWAComplianceChecker,
    create_compliance_checker,
)
from rra.oracles import (
    ValuationMethod,
    AssetCategory,
    ValuationInput,
    ValuationResult,
    ConsensusValuation,
    OracleReputation,
    ValuationOracle,
    ValuationOracleAggregator,
    create_valuation_oracle,
    create_valuation_aggregator,
)
from rra.legal import (
    WrapperType,
    JurisdictionType,
    AssetClassification,
    LegalParty,
    WrapperClause,
    WrapperTemplate,
    GeneratedWrapper,
    LegalWrapperGenerator,
    create_wrapper_generator,
)


# ============ Asset Tokenizer Tests ============

class TestAssetTokenizer:
    """Tests for AssetTokenizer."""
    
    @pytest.fixture
    def tokenizer(self) -> AssetTokenizer:
        return create_tokenizer(
            contract_address="0x1234567890123456789012345678901234567890",
            compliance_verifier="0x0987654321098765432109876543210987654321"
        )
    
    def test_create_tokenization_request(self, tokenizer: AssetTokenizer):
        """Test creating a tokenization request."""
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.PATENT_UTILITY,
            title="Test Patent",
            description="A test patent for unit testing",
            registration_number="US12345678",
            registration_authority=RegistrationAuthority.USPTO,
            registration_date=datetime(2020, 1, 15),
            origin_jurisdiction="US",
            requester_address="0xRequester",
            minimum_price=Decimal("10000"),
            royalty_basis_points=500,
        )
        
        assert request.request_id is not None
        assert request.status == TokenizationStatus.DRAFT
        assert request.asset_metadata.asset_type == AssetType.PATENT_UTILITY
        assert request.asset_metadata.registration_number == "US12345678"
        assert request.minimum_price == Decimal("10000")
        assert request.royalty_basis_points == 500
    
    def test_create_request_with_expiration(self, tokenizer: AssetTokenizer):
        """Test expiration date calculation for patents."""
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.PATENT_UTILITY,
            title="Expiring Patent",
            description="Patent with calculated expiration",
            registration_number="US87654321",
            registration_authority=RegistrationAuthority.USPTO,
            registration_date=datetime(2010, 6, 1),
            origin_jurisdiction="US",
            requester_address="0xOwner",
            minimum_price=Decimal("5000"),
            royalty_basis_points=300,
        )
        
        # Utility patents expire 20 years from registration
        expected_expiration = datetime(2030, 6, 1)
        assert request.asset_metadata.expiration_date is not None
        assert request.asset_metadata.expiration_date.year == expected_expiration.year
    
    def test_add_document(self, tokenizer: AssetTokenizer):
        """Test adding documentation to a request."""
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.TRADEMARK_WORD,
            title="Test Trademark",
            description="Word mark for testing",
            registration_number="TM123456",
            registration_authority=RegistrationAuthority.USPTO,
            registration_date=datetime(2019, 3, 10),
            origin_jurisdiction="US",
            requester_address="0xOwner",
            minimum_price=Decimal("2000"),
            royalty_basis_points=200,
        )
        
        doc = tokenizer.add_document(
            request_id=request.request_id,
            document_type="registration_certificate",
            document_hash="QmTestHash123",
            description="USPTO registration certificate"
        )
        
        assert doc.document_type == "registration_certificate"
        assert len(request.asset_metadata.documents) == 1
    
    def test_submit_for_verification_missing_docs(self, tokenizer: AssetTokenizer):
        """Test that verification requires all documents."""
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.PATENT_UTILITY,
            title="Missing Docs Patent",
            description="Patent without required docs",
            registration_number="US11111111",
            registration_authority=RegistrationAuthority.USPTO,
            registration_date=datetime(2021, 1, 1),
            origin_jurisdiction="US",
            requester_address="0xOwner",
            minimum_price=Decimal("1000"),
            royalty_basis_points=100,
        )
        
        with pytest.raises(ValueError) as exc_info:
            tokenizer.submit_for_verification(request.request_id)
        
        assert "Missing required documents" in str(exc_info.value)
    
    def test_full_tokenization_workflow(self, tokenizer: AssetTokenizer):
        """Test the complete tokenization workflow."""
        # Create request
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.COPYRIGHT_SOFTWARE,
            title="Open Source Library",
            description="A useful software library",
            registration_number="TX12345",
            registration_authority=RegistrationAuthority.USCO,
            registration_date=datetime(2022, 6, 15),
            origin_jurisdiction="US",
            requester_address="0xDeveloper",
            minimum_price=Decimal("500"),
            royalty_basis_points=100,
        )
        
        # Add required documents
        tokenizer.add_document(
            request.request_id,
            "registration_certificate",
            "QmCertHash",
            "Copyright registration"
        )
        tokenizer.add_document(
            request.request_id,
            "proof_of_ownership",
            "QmOwnerHash",
            "Proof of authorship"
        )
        tokenizer.add_document(
            request.request_id,
            "source_description",
            "QmSourceHash",
            "Source code description"
        )
        
        # Submit for verification
        request = tokenizer.submit_for_verification(request.request_id)
        assert request.status == TokenizationStatus.PENDING_VERIFICATION
        
        # Verify
        request = tokenizer.verify_request(
            request.request_id,
            verifier_address="0xVerifier",
            approved=True,
            notes="All documents verified"
        )
        assert request.status == TokenizationStatus.VERIFIED
        
        # Tokenize
        asset = tokenizer.tokenize(
            request.request_id,
            token_uri="ipfs://QmTokenMetadata"
        )
        
        assert asset.token_id is not None
        assert request.status == TokenizationStatus.TOKENIZED
        assert asset.metadata.title == "Open Source Library"
    
    def test_get_assets_by_owner(self, tokenizer: AssetTokenizer):
        """Test retrieving assets by owner."""
        owner = "0xTestOwner"
        
        # Create and tokenize an asset
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.TRADE_SECRET,
            title="Secret Formula",
            description="Proprietary algorithm",
            registration_number="INT-001",
            registration_authority=RegistrationAuthority.OTHER,
            registration_date=datetime(2023, 1, 1),
            origin_jurisdiction="US",
            requester_address=owner,
            minimum_price=Decimal("100000"),
            royalty_basis_points=1000,
        )
        
        # Add required documents
        tokenizer.add_document(request.request_id, "registration_certificate", "h1", "cert")
        tokenizer.add_document(request.request_id, "proof_of_ownership", "h2", "proof")
        tokenizer.add_document(request.request_id, "confidentiality_agreement", "h3", "nda")
        
        tokenizer.submit_for_verification(request.request_id)
        tokenizer.verify_request(request.request_id, "0xV", True)
        tokenizer.tokenize(request.request_id, "ipfs://test")
        
        assets = tokenizer.get_assets_by_owner(owner)
        assert len(assets) == 1
        assert assets[0].metadata.title == "Secret Formula"
    
    def test_update_valuation(self, tokenizer: AssetTokenizer):
        """Test updating asset valuation."""
        # Create and tokenize
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.PHYSICAL_IP,
            title="Prototype Device",
            description="Physical prototype",
            registration_number="PHY-001",
            registration_authority=RegistrationAuthority.OTHER,
            registration_date=datetime(2023, 6, 1),
            origin_jurisdiction="US",
            requester_address="0xOwner",
            minimum_price=Decimal("50000"),
            royalty_basis_points=500,
            is_physical_asset=True,
            physical_location="New York, NY",
            custodian="Secure Vault Inc."
        )
        
        for doc_type in ["registration_certificate", "proof_of_ownership", "custody_agreement", "physical_description"]:
            tokenizer.add_document(request.request_id, doc_type, f"hash_{doc_type}", doc_type)
        
        tokenizer.submit_for_verification(request.request_id)
        tokenizer.verify_request(request.request_id, "0xV", True)
        asset = tokenizer.tokenize(request.request_id, "ipfs://test")
        
        # Update valuation
        asset = tokenizer.update_valuation(
            token_id=asset.token_id,
            valuation=Decimal("75000"),
            confidence=8500
        )
        
        assert asset.current_valuation == Decimal("75000")
        assert asset.valuation_confidence == 8500


# ============ Compliance Tests ============

class TestRWACompliance:
    """Tests for RWA compliance checking."""
    
    @pytest.fixture
    def checker(self) -> RWAComplianceChecker:
        return create_compliance_checker()
    
    def test_register_participant(self, checker: RWAComplianceChecker):
        """Test participant registration."""
        profile = checker.register_participant(
            address="0xParticipant",
            jurisdictions=["US"]
        )
        
        assert profile.address == "0xParticipant"
        assert profile.kyc_status == KYCStatus.NOT_STARTED
        assert "US" in profile.jurisdictions
    
    def test_update_kyc_status(self, checker: RWAComplianceChecker):
        """Test KYC status updates."""
        checker.register_participant("0xUser", ["US"])
        
        profile = checker.update_kyc_status(
            address="0xUser",
            status=KYCStatus.VERIFIED,
            provider="Jumio",
            expires_in_days=365
        )
        
        assert profile.kyc_status == KYCStatus.VERIFIED
        assert profile.kyc_provider == "Jumio"
        assert profile.kyc_expires_at is not None
    
    def test_update_accreditation(self, checker: RWAComplianceChecker):
        """Test accreditation updates."""
        checker.register_participant("0xInvestor", ["US"])
        
        profile = checker.update_accreditation(
            address="0xInvestor",
            accreditation_type=AccreditationType.ACCREDITED_INDIVIDUAL
        )
        
        assert profile.accreditation_type == AccreditationType.ACCREDITED_INDIVIDUAL
    
    def test_check_tokenization_compliance_unregistered(self, checker: RWAComplianceChecker):
        """Test compliance check for unregistered owner."""
        report = checker.check_tokenization_compliance(
            owner_address="0xUnknown",
            asset_type="patent_utility",
            origin_jurisdiction="US",
            target_jurisdictions=["US", "EU"]
        )
        
        assert not report.overall_passed
        assert "Owner not registered" in report.blocking_issues[0]
    
    def test_check_tokenization_compliance_success(self, checker: RWAComplianceChecker):
        """Test successful tokenization compliance check."""
        # Register and verify participant
        checker.register_participant("0xOwner", ["US"])
        checker.update_kyc_status("0xOwner", KYCStatus.VERIFIED)
        checker.update_aml_status("0xOwner", True)
        checker.update_sanctions_status("0xOwner", True)
        
        report = checker.check_tokenization_compliance(
            owner_address="0xOwner",
            asset_type="patent_utility",
            origin_jurisdiction="US",
            target_jurisdictions=["US"]
        )
        
        assert report.overall_passed
        assert len(report.blocking_issues) == 0
    
    def test_check_restricted_jurisdiction(self, checker: RWAComplianceChecker):
        """Test compliance check for restricted jurisdiction."""
        checker.register_participant("0xOwner", ["US"])
        checker.update_kyc_status("0xOwner", KYCStatus.VERIFIED)
        checker.update_aml_status("0xOwner", True)
        checker.update_sanctions_status("0xOwner", True)
        
        report = checker.check_tokenization_compliance(
            owner_address="0xOwner",
            asset_type="patent_utility",
            origin_jurisdiction="US",
            target_jurisdictions=["US", "KP"]  # North Korea is restricted
        )
        
        # Should pass overall but have warning about KP
        assert report.overall_passed  # Origin is valid
        assert any("KP" in w for w in report.warnings)
    
    def test_check_transfer_compliance(self, checker: RWAComplianceChecker):
        """Test transfer compliance check."""
        # Register both parties
        checker.register_participant("0xSender", ["US"])
        checker.register_participant("0xRecipient", ["US"])
        
        # Verify recipient
        checker.update_kyc_status("0xRecipient", KYCStatus.VERIFIED)
        checker.update_aml_status("0xRecipient", True)
        checker.update_sanctions_status("0xRecipient", True)
        checker.update_accreditation("0xRecipient", AccreditationType.ACCREDITED_INDIVIDUAL)
        
        report = checker.check_transfer_compliance(
            token_id=1,
            from_address="0xSender",
            to_address="0xRecipient",
            asset_type="patent_utility",
            asset_jurisdiction="US",
            minimum_price=Decimal("1000"),
            transfer_value=Decimal("1500")
        )
        
        assert report.overall_passed
    
    def test_check_transfer_below_minimum(self, checker: RWAComplianceChecker):
        """Test transfer fails when below minimum price."""
        checker.register_participant("0xSender", ["US"])
        checker.register_participant("0xRecipient", ["US"])
        
        checker.update_kyc_status("0xRecipient", KYCStatus.VERIFIED)
        checker.update_aml_status("0xRecipient", True)
        checker.update_sanctions_status("0xRecipient", True)
        
        report = checker.check_transfer_compliance(
            token_id=1,
            from_address="0xSender",
            to_address="0xRecipient",
            asset_type="copyright_software",
            asset_jurisdiction="EU",  # EU doesn't require accreditation
            minimum_price=Decimal("1000"),
            transfer_value=Decimal("500")  # Below minimum
        )
        
        assert not report.overall_passed
        assert any("minimum" in issue.lower() for issue in report.blocking_issues)
    
    def test_pep_status(self, checker: RWAComplianceChecker):
        """Test PEP (Politically Exposed Person) handling."""
        checker.register_participant("0xPolitician", ["US"])
        checker.update_pep_status("0xPolitician", is_pep=True, pep_cleared=False)
        
        report = checker.check_participant_eligibility(
            address="0xPolitician",
            jurisdiction="US",
            asset_type="patent_utility"
        )
        
        # PEP not cleared should generate warning
        assert any("PEP" in w for w in report.warnings)


# ============ Valuation Oracle Tests ============

class TestValuationOracle:
    """Tests for valuation oracles."""
    
    @pytest.fixture
    def oracle(self) -> ValuationOracle:
        return create_valuation_oracle(
            oracle_address="0xOracle1",
            specializations=[AssetCategory.PATENT, AssetCategory.COPYRIGHT]
        )
    
    def test_income_valuation(self, oracle: ValuationOracle):
        """Test income approach valuation."""
        inputs = ValuationInput(
            asset_category=AssetCategory.PATENT,
            asset_type="patent_utility",
            annual_revenue=Decimal("500000"),
            royalty_rate=Decimal("0.05"),  # 5% royalty
            remaining_life_years=10,
        )
        
        result = oracle.calculate_valuation(
            asset_id="test_asset",
            inputs=inputs,
            method=ValuationMethod.INCOME_APPROACH
        )
        
        assert result.estimated_value > 0
        assert result.confidence_score > 0
        assert result.method == ValuationMethod.INCOME_APPROACH
    
    def test_market_comparable_valuation(self, oracle: ValuationOracle):
        """Test market comparable valuation."""
        inputs = ValuationInput(
            asset_category=AssetCategory.PATENT,
            asset_type="patent_utility",
            comparable_sales=[
                Decimal("100000"),
                Decimal("120000"),
                Decimal("95000"),
                Decimal("115000"),
            ]
        )
        
        result = oracle.calculate_valuation(
            asset_id="test_asset",
            inputs=inputs,
            method=ValuationMethod.MARKET_COMPARABLE
        )
        
        assert result.estimated_value > 0
        # Median should be around 107500
        assert Decimal("90000") < result.estimated_value < Decimal("130000")
    
    def test_cost_valuation(self, oracle: ValuationOracle):
        """Test cost approach valuation."""
        inputs = ValuationInput(
            asset_category=AssetCategory.COPYRIGHT,
            asset_type="copyright_software",
            development_cost=Decimal("250000"),
            remaining_life_years=15,
        )
        
        result = oracle.calculate_valuation(
            asset_id="software_asset",
            inputs=inputs,
            method=ValuationMethod.COST_APPROACH
        )
        
        assert result.estimated_value > 0
        assert result.estimated_value <= inputs.development_cost  # Should depreciate
    
    def test_royalty_relief_valuation(self, oracle: ValuationOracle):
        """Test relief from royalty valuation."""
        inputs = ValuationInput(
            asset_category=AssetCategory.PATENT,
            asset_type="patent_utility",
            annual_revenue=Decimal("1000000"),
            royalty_rate=Decimal("0.08"),  # 8% royalty
            remaining_life_years=8,
        )
        
        result = oracle.calculate_valuation(
            asset_id="patent_asset",
            inputs=inputs,
            method=ValuationMethod.ROYALTY_RELIEF
        )
        
        assert result.estimated_value > 0
        assert result.confidence_score >= 7500  # High confidence for royalty relief
    
    def test_hybrid_valuation(self, oracle: ValuationOracle):
        """Test hybrid valuation combining methods."""
        inputs = ValuationInput(
            asset_category=AssetCategory.PATENT,
            asset_type="patent_utility",
            annual_revenue=Decimal("500000"),
            royalty_rate=Decimal("0.05"),
            remaining_life_years=12,
            development_cost=Decimal("200000"),
            comparable_sales=[
                Decimal("300000"),
                Decimal("350000"),
                Decimal("280000"),
            ]
        )
        
        result = oracle.calculate_valuation(
            asset_id="multi_data_asset",
            inputs=inputs,
            method=ValuationMethod.ALGORITHMIC  # Will use hybrid
        )
        
        assert result.estimated_value > 0
        assert "hybrid" in result.calculation_details.get("method", "")


class TestValuationAggregator:
    """Tests for valuation oracle aggregator."""
    
    @pytest.fixture
    def aggregator(self) -> ValuationOracleAggregator:
        agg = create_valuation_aggregator(min_oracles=2)
        
        # Register multiple oracles
        oracle1 = create_valuation_oracle("0xOracle1", [AssetCategory.PATENT])
        oracle2 = create_valuation_oracle("0xOracle2", [AssetCategory.PATENT])
        oracle3 = create_valuation_oracle("0xOracle3", [AssetCategory.PATENT])
        
        agg.register_oracle(oracle1)
        agg.register_oracle(oracle2)
        agg.register_oracle(oracle3)
        
        return agg
    
    def test_consensus_valuation(self, aggregator: ValuationOracleAggregator):
        """Test consensus valuation from multiple oracles."""
        inputs = ValuationInput(
            asset_category=AssetCategory.PATENT,
            asset_type="patent_utility",
            annual_revenue=Decimal("500000"),
            royalty_rate=Decimal("0.05"),
            remaining_life_years=10,
        )
        
        consensus = aggregator.request_valuation(
            asset_id="consensus_test",
            inputs=inputs,
            methods=[ValuationMethod.INCOME_APPROACH]
        )
        
        assert consensus.consensus_value > 0
        assert consensus.oracle_count >= 2
        assert consensus.agreement_score > 0
    
    def test_oracle_reputation(self, aggregator: ValuationOracleAggregator):
        """Test oracle reputation tracking."""
        reputation = aggregator.get_oracle_reputation("0xOracle1")
        
        assert reputation is not None
        assert reputation.accuracy_score == 5000  # Initial 50%
        assert reputation.is_active
    
    def test_update_oracle_accuracy(self, aggregator: ValuationOracleAggregator):
        """Test accuracy updates based on actual values."""
        # Good prediction (within 10%)
        aggregator.update_oracle_accuracy(
            oracle_address="0xOracle1",
            actual_value=Decimal("100000"),
            predicted_value=Decimal("105000")  # 5% deviation
        )
        
        reputation = aggregator.get_oracle_reputation("0xOracle1")
        assert reputation.accuracy_score > 5000  # Should increase


# ============ Legal Wrapper Tests ============

class TestLegalWrapperGenerator:
    """Tests for legal wrapper generation."""
    
    @pytest.fixture
    def generator(self) -> LegalWrapperGenerator:
        return create_wrapper_generator()
    
    def test_list_templates(self, generator: LegalWrapperGenerator):
        """Test listing available templates."""
        templates = generator.list_templates()
        assert len(templates) > 0
        
        # Filter by type
        assignment_templates = generator.list_templates(wrapper_type=WrapperType.ASSIGNMENT_AGREEMENT)
        assert all(t.wrapper_type == WrapperType.ASSIGNMENT_AGREEMENT for t in assignment_templates)
    
    def test_generate_assignment_wrapper(self, generator: LegalWrapperGenerator):
        """Test generating an assignment agreement."""
        assignor = LegalParty(
            name="Patent Holder LLC",
            legal_type="llc",
            jurisdiction="US",
            registration_number="12345678",
            wallet_address="0xAssignor"
        )
        assignee = LegalParty(
            name="Token Buyer Inc",
            legal_type="corporation",
            jurisdiction="US",
            registration_number="87654321",
            wallet_address="0xAssignee"
        )
        
        wrapper = generator.generate_wrapper(
            template_id="assignment_delaware",
            parties=[assignor, assignee],
            asset_id="asset_123",
            parameters={
                "effective_date": "December 15, 2024",
                "consideration_amount": "$100,000 USD",
                "asset_description": "US Patent No. 12,345,678",
            },
            token_id=1,
            contract_address="0xRWAContract"
        )
        
        assert wrapper.wrapper_id is not None
        assert wrapper.wrapper_type == WrapperType.ASSIGNMENT_AGREEMENT
        assert "Assignment" in wrapper.title
        assert wrapper.status == "draft"
    
    def test_sign_wrapper(self, generator: LegalWrapperGenerator):
        """Test signing a wrapper."""
        party1 = LegalParty(
            name="Party One",
            legal_type="individual",
            jurisdiction="US",
            wallet_address="0xParty1"
        )
        party2 = LegalParty(
            name="Party Two",
            legal_type="individual",
            jurisdiction="US",
            wallet_address="0xParty2"
        )
        
        wrapper = generator.generate_wrapper(
            template_id="license_standard",
            parties=[party1, party2],
            asset_id="asset_456",
            parameters={
                "license_type": "non-exclusive",
                "exclusivity": "non-exclusive",
                "territory": "United States",
                "royalty_rate": "5%",
                "start_date": "January 1, 2025",
                "end_date": "December 31, 2029",
                "contract_address": "0xContract",
            }
        )
        
        # First signature
        wrapper = generator.sign_wrapper(
            wrapper_id=wrapper.wrapper_id,
            party_wallet="0xParty1",
            signature="0xSignature1"
        )
        assert wrapper.status == "partially_signed"
        
        # Second signature
        wrapper = generator.sign_wrapper(
            wrapper_id=wrapper.wrapper_id,
            party_wallet="0xParty2",
            signature="0xSignature2"
        )
        assert wrapper.status == "fully_signed"
    
    def test_notarize_wrapper(self, generator: LegalWrapperGenerator):
        """Test wrapper notarization."""
        party1 = LegalParty(name="P1", legal_type="corp", jurisdiction="US", wallet_address="0xP1")
        party2 = LegalParty(name="P2", legal_type="corp", jurisdiction="US", wallet_address="0xP2")
        
        wrapper = generator.generate_wrapper(
            template_id="security_ucc",
            parties=[party1, party2],
            asset_id="asset_789",
            parameters={
                "token_id": "1",
                "contract_address": "0xContract",
            },
            token_id=1
        )
        
        generator.sign_wrapper(wrapper.wrapper_id, "0xP1", "sig1")
        generator.sign_wrapper(wrapper.wrapper_id, "0xP2", "sig2")
        
        wrapper = generator.notarize_wrapper(
            wrapper_id=wrapper.wrapper_id,
            notary_info="John Smith, Notary Public, State of Delaware, Commission #12345"
        )
        
        assert wrapper.notarized
        assert wrapper.status == "executed"
    
    def test_store_on_ipfs(self, generator: LegalWrapperGenerator):
        """Test IPFS storage recording."""
        party1 = LegalParty(name="P1", legal_type="llc", jurisdiction="US", wallet_address="0xP1")
        party2 = LegalParty(name="P2", legal_type="llc", jurisdiction="US", wallet_address="0xP2")
        
        wrapper = generator.generate_wrapper(
            template_id="fractionalization",
            parties=[party1, party2],
            asset_id="frac_asset",
            parameters={
                "total_fractions": "1000",
                "manager": "Asset Management LLC",
                "buyout_threshold": "67",
            }
        )
        
        wrapper = generator.store_on_ipfs(
            wrapper_id=wrapper.wrapper_id,
            ipfs_hash="QmTestIPFSHash123456789"
        )
        
        assert wrapper.ipfs_hash == "QmTestIPFSHash123456789"
    
    def test_export_to_json(self, generator: LegalWrapperGenerator):
        """Test JSON export of wrapper metadata."""
        party1 = LegalParty(name="Exporter", legal_type="corp", jurisdiction="US", wallet_address="0xExp")
        party2 = LegalParty(name="Importer", legal_type="corp", jurisdiction="EU", wallet_address="0xImp")
        
        wrapper = generator.generate_wrapper(
            template_id="custody_physical",
            parties=[party1, party2],
            asset_id="physical_asset",
            parameters={
                "custody_location": "Secure Facility, Delaware",
                "insurance_amount": "$1,000,000",
                "token_id": "5",
            },
            token_id=5
        )
        
        json_str = generator.export_to_json(wrapper.wrapper_id)
        
        assert "wrapper_id" in json_str
        assert "physical_asset" in json_str
        assert "content_hash" in json_str
    
    def test_get_wrappers_for_asset(self, generator: LegalWrapperGenerator):
        """Test retrieving all wrappers for an asset."""
        party1 = LegalParty(name="Owner", legal_type="individual", jurisdiction="US", wallet_address="0xOwn")
        party2 = LegalParty(name="Buyer", legal_type="individual", jurisdiction="US", wallet_address="0xBuy")
        
        # Create multiple wrappers for same asset
        generator.generate_wrapper(
            template_id="assignment_delaware",
            parties=[party1, party2],
            asset_id="multi_wrapper_asset",
            parameters={"effective_date": "2024-01-01", "consideration_amount": "$50,000"},
        )
        
        generator.generate_wrapper(
            template_id="license_standard",
            parties=[party1, party2],
            asset_id="multi_wrapper_asset",
            parameters={
                "license_type": "exclusive",
                "exclusivity": "exclusive",
                "territory": "Worldwide",
                "royalty_rate": "3%",
                "start_date": "2024-01-01",
                "end_date": "2029-01-01",
                "contract_address": "0xC",
            },
        )
        
        wrappers = generator.get_wrappers_for_asset("multi_wrapper_asset")
        assert len(wrappers) == 2


# ============ Integration Tests ============

class TestRWAIntegration:
    """Integration tests for complete RWA workflow."""
    
    def test_full_rwa_workflow(self):
        """Test complete RWA tokenization and compliance workflow."""
        # Setup
        tokenizer = create_tokenizer()
        checker = create_compliance_checker()
        generator = create_wrapper_generator()
        aggregator = create_valuation_aggregator(min_oracles=2)
        
        # Register oracles
        for i in range(3):
            oracle = create_valuation_oracle(f"0xOracle{i}", [AssetCategory.PATENT])
            aggregator.register_oracle(oracle)
        
        owner_address = "0xPatentOwner"
        buyer_address = "0xPatentBuyer"
        
        # Step 1: Register participants for compliance
        checker.register_participant(owner_address, ["US"])
        checker.update_kyc_status(owner_address, KYCStatus.VERIFIED)
        checker.update_aml_status(owner_address, True)
        checker.update_sanctions_status(owner_address, True)
        
        checker.register_participant(buyer_address, ["US"])
        checker.update_kyc_status(buyer_address, KYCStatus.VERIFIED)
        checker.update_aml_status(buyer_address, True)
        checker.update_sanctions_status(buyer_address, True)
        checker.update_accreditation(buyer_address, AccreditationType.ACCREDITED_INDIVIDUAL)
        
        # Step 2: Check tokenization compliance
        compliance_report = checker.check_tokenization_compliance(
            owner_address=owner_address,
            asset_type="patent_utility",
            origin_jurisdiction="US",
            target_jurisdictions=["US", "EU", "GB"]
        )
        assert compliance_report.overall_passed
        
        # Step 3: Create tokenization request
        request = tokenizer.create_tokenization_request(
            asset_type=AssetType.PATENT_UTILITY,
            title="Revolutionary Algorithm Patent",
            description="A groundbreaking algorithm for data processing",
            registration_number="US11,234,567",
            registration_authority=RegistrationAuthority.USPTO,
            registration_date=datetime(2022, 3, 15),
            origin_jurisdiction="US",
            requester_address=owner_address,
            minimum_price=Decimal("500000"),
            royalty_basis_points=750,  # 7.5%
        )
        
        # Step 4: Add required documents
        tokenizer.add_document(request.request_id, "registration_certificate", "QmCert", "USPTO Certificate")
        tokenizer.add_document(request.request_id, "proof_of_ownership", "QmOwner", "Assignment chain")
        tokenizer.add_document(request.request_id, "claims_document", "QmClaims", "Patent claims")
        tokenizer.add_document(request.request_id, "drawings", "QmDrawings", "Patent drawings")
        
        # Step 5: Submit and verify
        tokenizer.submit_for_verification(request.request_id)
        tokenizer.verify_request(request.request_id, "0xVerifier", True, "All docs verified")
        
        # Step 6: Tokenize
        asset = tokenizer.tokenize(request.request_id, "ipfs://QmTokenMetadata")
        
        # Step 7: Get valuation
        valuation_inputs = ValuationInput(
            asset_category=AssetCategory.PATENT,
            asset_type="patent_utility",
            annual_revenue=Decimal("2000000"),
            royalty_rate=Decimal("0.075"),
            remaining_life_years=17,
            comparable_sales=[
                Decimal("400000"),
                Decimal("550000"),
                Decimal("480000"),
            ]
        )
        
        consensus = aggregator.request_valuation(
            asset_id=request.asset_metadata.asset_id,
            inputs=valuation_inputs,
            methods=[ValuationMethod.INCOME_APPROACH, ValuationMethod.ROYALTY_RELIEF]
        )
        
        # Update asset with valuation
        tokenizer.update_valuation(
            token_id=asset.token_id,
            valuation=consensus.consensus_value,
            confidence=consensus.confidence_score
        )
        
        # Step 8: Generate legal wrapper for sale
        owner_party = LegalParty(
            name="Patent Owner Corp",
            legal_type="corporation",
            jurisdiction="US",
            wallet_address=owner_address
        )
        buyer_party = LegalParty(
            name="Patent Buyer LLC",
            legal_type="llc",
            jurisdiction="US",
            wallet_address=buyer_address
        )
        
        wrapper = generator.generate_wrapper(
            template_id="assignment_delaware",
            parties=[owner_party, buyer_party],
            asset_id=request.asset_metadata.asset_id,
            parameters={
                "effective_date": datetime.utcnow().strftime("%B %d, %Y"),
                "consideration_amount": f"${consensus.consensus_value:,.2f} USD",
                "asset_description": f"US Patent No. {request.asset_metadata.registration_number}",
            },
            token_id=asset.token_id,
            contract_address=tokenizer.contract_address
        )
        
        # Step 9: Check transfer compliance
        transfer_report = checker.check_transfer_compliance(
            token_id=asset.token_id,
            from_address=owner_address,
            to_address=buyer_address,
            asset_type="patent_utility",
            asset_jurisdiction="US",
            minimum_price=asset.minimum_price,
            transfer_value=consensus.consensus_value
        )
        assert transfer_report.overall_passed
        
        # Verify final state
        assert asset.token_id is not None
        assert asset.current_valuation == consensus.consensus_value
        assert wrapper.wrapper_type == WrapperType.ASSIGNMENT_AGREEMENT
        assert wrapper.token_id == asset.token_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
