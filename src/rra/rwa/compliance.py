# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
RWA Compliance module for Real-World Asset tokenization.

Provides compliance checking for:
- Jurisdiction restrictions
- Regulatory requirements
- Transfer eligibility
- KYC/AML verification status
- Accreditation requirements
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import re


class ComplianceStatus(Enum):
    """Compliance verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    REQUIRES_UPDATE = "requires_update"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class KYCStatus(Enum):
    """KYC verification status."""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    VERIFIED = "verified"
    EXPIRED = "expired"
    FAILED = "failed"
    SUSPENDED = "suspended"


class AccreditationType(Enum):
    """Investor accreditation types."""
    NONE = "none"
    ACCREDITED_INDIVIDUAL = "accredited_individual"  # US Rule 501
    QUALIFIED_PURCHASER = "qualified_purchaser"      # US Investment Company Act
    PROFESSIONAL_INVESTOR = "professional_investor"  # EU MiFID II
    SOPHISTICATED_INVESTOR = "sophisticated_investor"
    INSTITUTIONAL = "institutional"


class RegulationType(Enum):
    """Applicable regulatory frameworks."""
    SEC_REG_D = "sec_reg_d"           # US Regulation D
    SEC_REG_S = "sec_reg_s"           # US Regulation S (offshore)
    SEC_REG_A = "sec_reg_a"           # US Regulation A+
    SEC_REG_CF = "sec_reg_cf"         # US Crowdfunding
    EU_MICA = "eu_mica"               # EU Markets in Crypto-Assets
    EU_MIFID = "eu_mifid"             # EU Markets in Financial Instruments
    UK_FCA = "uk_fca"                 # UK Financial Conduct Authority
    SWISS_FINMA = "swiss_finma"       # Swiss Financial Market Supervisory
    SG_MAS = "sg_mas"                 # Singapore Monetary Authority
    HK_SFC = "hk_sfc"                 # Hong Kong Securities and Futures
    JP_FSA = "jp_fsa"                 # Japan Financial Services Agency
    NONE = "none"                     # No specific regulation


@dataclass
class JurisdictionRules:
    """Compliance rules for a jurisdiction."""
    country_code: str                           # ISO 3166-1 alpha-2
    allowed_asset_types: List[str] = field(default_factory=list)
    blocked_asset_types: List[str] = field(default_factory=list)
    requires_kyc: bool = True
    requires_accreditation: bool = False
    minimum_accreditation: AccreditationType = AccreditationType.NONE
    applicable_regulations: List[RegulationType] = field(default_factory=list)
    transfer_restrictions: List[str] = field(default_factory=list)
    holding_period_days: int = 0                # Lock-up period
    max_investors: Optional[int] = None         # Investor limits
    reporting_requirements: List[str] = field(default_factory=list)
    is_restricted: bool = False                 # Blanket restriction
    restriction_reason: Optional[str] = None


@dataclass
class ParticipantProfile:
    """Compliance profile for a participant."""
    address: str
    kyc_status: KYCStatus = KYCStatus.NOT_STARTED
    kyc_verified_at: Optional[datetime] = None
    kyc_expires_at: Optional[datetime] = None
    kyc_provider: Optional[str] = None
    
    accreditation_type: AccreditationType = AccreditationType.NONE
    accreditation_verified_at: Optional[datetime] = None
    accreditation_expires_at: Optional[datetime] = None
    
    jurisdictions: List[str] = field(default_factory=list)  # Residence/citizenship
    blocked_jurisdictions: List[str] = field(default_factory=list)
    
    aml_cleared: bool = False
    aml_cleared_at: Optional[datetime] = None
    
    sanctions_cleared: bool = False
    sanctions_checked_at: Optional[datetime] = None
    
    is_pep: bool = False  # Politically Exposed Person
    pep_cleared: bool = False
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceCheck:
    """Result of a compliance check."""
    check_id: str
    check_type: str
    passed: bool
    message: str
    details: Dict = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComplianceReport:
    """Full compliance report for an action."""
    report_id: str
    action_type: str  # tokenization, transfer, fractionalization
    subject_type: str  # asset, participant
    subject_id: str
    
    overall_passed: bool
    checks: List[ComplianceCheck] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    generated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class RWAComplianceChecker:
    """
    Compliance checker for RWA tokenization and transfers.
    
    Handles:
    - Jurisdiction-based restrictions
    - KYC/AML verification
    - Accreditation requirements
    - Transfer eligibility
    - Regulatory compliance
    """
    
    def __init__(self):
        self._participants: Dict[str, ParticipantProfile] = {}
        self._jurisdiction_rules: Dict[str, JurisdictionRules] = {}
        self._check_counter = 0
        self._report_counter = 0
        
        # Initialize default jurisdiction rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default compliance rules for common jurisdictions."""
        # United States
        self._jurisdiction_rules["US"] = JurisdictionRules(
            country_code="US",
            requires_kyc=True,
            requires_accreditation=True,
            minimum_accreditation=AccreditationType.ACCREDITED_INDIVIDUAL,
            applicable_regulations=[RegulationType.SEC_REG_D, RegulationType.SEC_REG_S],
            holding_period_days=365,  # 1 year holding period for Reg D
            max_investors=2000,  # Reg D 506(c) allows unlimited accredited
            reporting_requirements=["form_d", "blue_sky"],
        )
        
        # European Union
        self._jurisdiction_rules["EU"] = JurisdictionRules(
            country_code="EU",
            requires_kyc=True,
            requires_accreditation=False,
            applicable_regulations=[RegulationType.EU_MICA, RegulationType.EU_MIFID],
            holding_period_days=0,
            reporting_requirements=["mifid_reporting"],
        )
        
        # United Kingdom
        self._jurisdiction_rules["GB"] = JurisdictionRules(
            country_code="GB",
            requires_kyc=True,
            requires_accreditation=False,
            applicable_regulations=[RegulationType.UK_FCA],
            holding_period_days=0,
            reporting_requirements=["fca_reporting"],
        )
        
        # Switzerland
        self._jurisdiction_rules["CH"] = JurisdictionRules(
            country_code="CH",
            requires_kyc=True,
            requires_accreditation=False,
            applicable_regulations=[RegulationType.SWISS_FINMA],
            holding_period_days=0,
        )
        
        # Singapore
        self._jurisdiction_rules["SG"] = JurisdictionRules(
            country_code="SG",
            requires_kyc=True,
            requires_accreditation=True,
            minimum_accreditation=AccreditationType.ACCREDITED_INDIVIDUAL,
            applicable_regulations=[RegulationType.SG_MAS],
            holding_period_days=0,
        )
        
        # Restricted jurisdictions
        for code in ["KP", "IR", "CU", "SY"]:  # North Korea, Iran, Cuba, Syria
            self._jurisdiction_rules[code] = JurisdictionRules(
                country_code=code,
                is_restricted=True,
                restriction_reason="OFAC sanctioned jurisdiction",
            )
    
    def register_participant(
        self,
        address: str,
        jurisdictions: Optional[List[str]] = None
    ) -> ParticipantProfile:
        """Register a new participant for compliance tracking."""
        if address in self._participants:
            return self._participants[address]
        
        profile = ParticipantProfile(
            address=address,
            jurisdictions=jurisdictions or [],
        )
        self._participants[address] = profile
        return profile
    
    def get_participant(self, address: str) -> Optional[ParticipantProfile]:
        """Get participant compliance profile."""
        return self._participants.get(address)
    
    def update_kyc_status(
        self,
        address: str,
        status: KYCStatus,
        provider: Optional[str] = None,
        expires_in_days: int = 365
    ) -> ParticipantProfile:
        """Update KYC status for a participant."""
        profile = self._participants.get(address)
        if not profile:
            raise ValueError(f"Participant {address} not found")
        
        profile.kyc_status = status
        profile.kyc_provider = provider
        profile.updated_at = datetime.utcnow()
        
        if status == KYCStatus.VERIFIED:
            profile.kyc_verified_at = datetime.utcnow()
            profile.kyc_expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        return profile
    
    def update_accreditation(
        self,
        address: str,
        accreditation_type: AccreditationType,
        expires_in_days: int = 365
    ) -> ParticipantProfile:
        """Update accreditation status for a participant."""
        profile = self._participants.get(address)
        if not profile:
            raise ValueError(f"Participant {address} not found")
        
        profile.accreditation_type = accreditation_type
        profile.accreditation_verified_at = datetime.utcnow()
        profile.accreditation_expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        profile.updated_at = datetime.utcnow()
        
        return profile
    
    def update_aml_status(
        self,
        address: str,
        cleared: bool
    ) -> ParticipantProfile:
        """Update AML clearance status for a participant."""
        profile = self._participants.get(address)
        if not profile:
            raise ValueError(f"Participant {address} not found")
        
        profile.aml_cleared = cleared
        profile.aml_cleared_at = datetime.utcnow() if cleared else None
        profile.updated_at = datetime.utcnow()
        
        return profile
    
    def update_sanctions_status(
        self,
        address: str,
        cleared: bool
    ) -> ParticipantProfile:
        """Update sanctions check status for a participant."""
        profile = self._participants.get(address)
        if not profile:
            raise ValueError(f"Participant {address} not found")
        
        profile.sanctions_cleared = cleared
        profile.sanctions_checked_at = datetime.utcnow()
        profile.updated_at = datetime.utcnow()
        
        return profile
    
    def update_pep_status(
        self,
        address: str,
        is_pep: bool,
        pep_cleared: bool = False
    ) -> ParticipantProfile:
        """Update PEP (Politically Exposed Person) status."""
        profile = self._participants.get(address)
        if not profile:
            raise ValueError(f"Participant {address} not found")
        
        profile.is_pep = is_pep
        profile.pep_cleared = pep_cleared
        profile.updated_at = datetime.utcnow()
        
        return profile
    
    def set_jurisdiction_rules(
        self,
        country_code: str,
        rules: JurisdictionRules
    ):
        """Set compliance rules for a jurisdiction."""
        self._jurisdiction_rules[country_code] = rules
    
    def get_jurisdiction_rules(self, country_code: str) -> Optional[JurisdictionRules]:
        """Get compliance rules for a jurisdiction."""
        return self._jurisdiction_rules.get(country_code)
    
    def check_tokenization_compliance(
        self,
        owner_address: str,
        asset_type: str,
        origin_jurisdiction: str,
        target_jurisdictions: List[str]
    ) -> ComplianceReport:
        """Check compliance for tokenizing an asset."""
        checks = []
        blocking_issues = []
        warnings = []
        
        # Check owner registration
        owner = self._participants.get(owner_address)
        if not owner:
            blocking_issues.append("Owner not registered for compliance")
            checks.append(self._create_check(
                "owner_registration",
                False,
                "Owner must be registered for compliance tracking"
            ))
        else:
            checks.append(self._create_check(
                "owner_registration",
                True,
                "Owner is registered"
            ))
            
            # Check KYC
            kyc_check = self._check_kyc(owner)
            checks.append(kyc_check)
            if not kyc_check.passed:
                blocking_issues.append(kyc_check.message)
            
            # Check AML
            aml_check = self._check_aml(owner)
            checks.append(aml_check)
            if not aml_check.passed:
                blocking_issues.append(aml_check.message)
            
            # Check sanctions
            sanctions_check = self._check_sanctions(owner)
            checks.append(sanctions_check)
            if not sanctions_check.passed:
                blocking_issues.append(sanctions_check.message)
        
        # Check origin jurisdiction
        origin_check = self._check_jurisdiction(origin_jurisdiction, asset_type)
        checks.append(origin_check)
        if not origin_check.passed:
            blocking_issues.append(origin_check.message)
        
        # Check target jurisdictions
        for jurisdiction in target_jurisdictions:
            jurisdiction_check = self._check_jurisdiction(jurisdiction, asset_type)
            checks.append(jurisdiction_check)
            if not jurisdiction_check.passed:
                if jurisdiction == origin_jurisdiction:
                    blocking_issues.append(jurisdiction_check.message)
                else:
                    warnings.append(f"Target jurisdiction {jurisdiction}: {jurisdiction_check.message}")
        
        overall_passed = len(blocking_issues) == 0
        
        return self._create_report(
            "tokenization",
            "asset",
            f"{owner_address}:{asset_type}",
            overall_passed,
            checks,
            blocking_issues,
            warnings
        )
    
    def check_transfer_compliance(
        self,
        token_id: int,
        from_address: str,
        to_address: str,
        asset_type: str,
        asset_jurisdiction: str,
        minimum_price: Decimal,
        transfer_value: Decimal
    ) -> ComplianceReport:
        """Check compliance for transferring an asset."""
        checks = []
        blocking_issues = []
        warnings = []
        
        # Check sender
        sender = self._participants.get(from_address)
        if not sender:
            blocking_issues.append("Sender not registered for compliance")
            checks.append(self._create_check(
                "sender_registration",
                False,
                "Sender must be registered"
            ))
        else:
            checks.append(self._create_check(
                "sender_registration",
                True,
                "Sender is registered"
            ))
        
        # Check recipient
        recipient = self._participants.get(to_address)
        if not recipient:
            blocking_issues.append("Recipient not registered for compliance")
            checks.append(self._create_check(
                "recipient_registration",
                False,
                "Recipient must be registered"
            ))
        else:
            checks.append(self._create_check(
                "recipient_registration",
                True,
                "Recipient is registered"
            ))
            
            # Check recipient KYC
            kyc_check = self._check_kyc(recipient)
            checks.append(kyc_check)
            if not kyc_check.passed:
                blocking_issues.append(f"Recipient: {kyc_check.message}")
            
            # Check recipient AML
            aml_check = self._check_aml(recipient)
            checks.append(aml_check)
            if not aml_check.passed:
                blocking_issues.append(f"Recipient: {aml_check.message}")
            
            # Check recipient sanctions
            sanctions_check = self._check_sanctions(recipient)
            checks.append(sanctions_check)
            if not sanctions_check.passed:
                blocking_issues.append(f"Recipient: {sanctions_check.message}")
            
            # Check recipient accreditation if required
            rules = self._jurisdiction_rules.get(asset_jurisdiction)
            if rules and rules.requires_accreditation:
                accred_check = self._check_accreditation(recipient, rules.minimum_accreditation)
                checks.append(accred_check)
                if not accred_check.passed:
                    blocking_issues.append(f"Recipient: {accred_check.message}")
            
            # Check recipient jurisdiction
            if recipient.jurisdictions:
                for jurisdiction in recipient.jurisdictions:
                    jurisdiction_check = self._check_jurisdiction(jurisdiction, asset_type)
                    checks.append(jurisdiction_check)
                    if not jurisdiction_check.passed:
                        blocking_issues.append(f"Recipient jurisdiction {jurisdiction}: {jurisdiction_check.message}")
        
        # Check minimum price
        if transfer_value < minimum_price:
            blocking_issues.append(f"Transfer value {transfer_value} below minimum {minimum_price}")
            checks.append(self._create_check(
                "minimum_price",
                False,
                f"Transfer value must be at least {minimum_price}"
            ))
        else:
            checks.append(self._create_check(
                "minimum_price",
                True,
                "Transfer value meets minimum"
            ))
        
        overall_passed = len(blocking_issues) == 0
        
        return self._create_report(
            "transfer",
            "asset",
            str(token_id),
            overall_passed,
            checks,
            blocking_issues,
            warnings
        )
    
    def check_participant_eligibility(
        self,
        address: str,
        jurisdiction: str,
        asset_type: str
    ) -> ComplianceReport:
        """Check if a participant is eligible to hold an asset type in a jurisdiction."""
        checks = []
        blocking_issues = []
        warnings = []
        
        participant = self._participants.get(address)
        if not participant:
            blocking_issues.append("Participant not registered")
            checks.append(self._create_check(
                "registration",
                False,
                "Participant must be registered"
            ))
        else:
            # KYC check
            kyc_check = self._check_kyc(participant)
            checks.append(kyc_check)
            if not kyc_check.passed:
                blocking_issues.append(kyc_check.message)
            
            # AML check
            aml_check = self._check_aml(participant)
            checks.append(aml_check)
            if not aml_check.passed:
                blocking_issues.append(aml_check.message)
            
            # Sanctions check
            sanctions_check = self._check_sanctions(participant)
            checks.append(sanctions_check)
            if not sanctions_check.passed:
                blocking_issues.append(sanctions_check.message)
            
            # PEP check
            pep_check = self._check_pep(participant)
            checks.append(pep_check)
            if not pep_check.passed:
                warnings.append(pep_check.message)
            
            # Jurisdiction rules
            rules = self._jurisdiction_rules.get(jurisdiction)
            if rules:
                if rules.is_restricted:
                    blocking_issues.append(f"Jurisdiction {jurisdiction} is restricted: {rules.restriction_reason}")
                    checks.append(self._create_check(
                        "jurisdiction",
                        False,
                        f"Restricted jurisdiction: {rules.restriction_reason}"
                    ))
                else:
                    checks.append(self._create_check(
                        "jurisdiction",
                        True,
                        f"Jurisdiction {jurisdiction} is allowed"
                    ))
                    
                    # Accreditation check
                    if rules.requires_accreditation:
                        accred_check = self._check_accreditation(participant, rules.minimum_accreditation)
                        checks.append(accred_check)
                        if not accred_check.passed:
                            blocking_issues.append(accred_check.message)
            
            # Check blocked jurisdictions
            for blocked in participant.blocked_jurisdictions:
                if blocked == jurisdiction:
                    blocking_issues.append(f"Participant blocked from jurisdiction {jurisdiction}")
                    checks.append(self._create_check(
                        "blocked_jurisdiction",
                        False,
                        f"Participant is blocked from {jurisdiction}"
                    ))
        
        overall_passed = len(blocking_issues) == 0
        
        return self._create_report(
            "eligibility",
            "participant",
            address,
            overall_passed,
            checks,
            blocking_issues,
            warnings
        )
    
    def _check_kyc(self, participant: ParticipantProfile) -> ComplianceCheck:
        """Check KYC status."""
        if participant.kyc_status != KYCStatus.VERIFIED:
            return self._create_check(
                "kyc",
                False,
                f"KYC not verified (status: {participant.kyc_status.value})"
            )
        
        if participant.kyc_expires_at and participant.kyc_expires_at < datetime.utcnow():
            return self._create_check(
                "kyc",
                False,
                "KYC has expired"
            )
        
        return self._create_check(
            "kyc",
            True,
            "KYC verified and current"
        )
    
    def _check_aml(self, participant: ParticipantProfile) -> ComplianceCheck:
        """Check AML clearance."""
        if not participant.aml_cleared:
            return self._create_check(
                "aml",
                False,
                "AML check not passed"
            )
        
        return self._create_check(
            "aml",
            True,
            "AML cleared"
        )
    
    def _check_sanctions(self, participant: ParticipantProfile) -> ComplianceCheck:
        """Check sanctions status."""
        if not participant.sanctions_cleared:
            return self._create_check(
                "sanctions",
                False,
                "Sanctions check not passed"
            )
        
        # Check if sanctions check is stale (> 30 days)
        if participant.sanctions_checked_at:
            if datetime.utcnow() - participant.sanctions_checked_at > timedelta(days=30):
                return self._create_check(
                    "sanctions",
                    False,
                    "Sanctions check is stale (> 30 days old)"
                )
        
        return self._create_check(
            "sanctions",
            True,
            "Sanctions cleared"
        )
    
    def _check_pep(self, participant: ParticipantProfile) -> ComplianceCheck:
        """Check PEP status."""
        if participant.is_pep and not participant.pep_cleared:
            return self._create_check(
                "pep",
                False,
                "PEP status requires additional clearance"
            )
        
        return self._create_check(
            "pep",
            True,
            "PEP check passed"
        )
    
    def _check_accreditation(
        self,
        participant: ParticipantProfile,
        minimum: AccreditationType
    ) -> ComplianceCheck:
        """Check accreditation level."""
        accreditation_levels = {
            AccreditationType.NONE: 0,
            AccreditationType.SOPHISTICATED_INVESTOR: 1,
            AccreditationType.ACCREDITED_INDIVIDUAL: 2,
            AccreditationType.PROFESSIONAL_INVESTOR: 3,
            AccreditationType.QUALIFIED_PURCHASER: 4,
            AccreditationType.INSTITUTIONAL: 5,
        }
        
        participant_level = accreditation_levels.get(participant.accreditation_type, 0)
        required_level = accreditation_levels.get(minimum, 0)
        
        if participant_level < required_level:
            return self._create_check(
                "accreditation",
                False,
                f"Insufficient accreditation: {participant.accreditation_type.value} < {minimum.value}"
            )
        
        # Check expiration
        if participant.accreditation_expires_at and participant.accreditation_expires_at < datetime.utcnow():
            return self._create_check(
                "accreditation",
                False,
                "Accreditation has expired"
            )
        
        return self._create_check(
            "accreditation",
            True,
            f"Accreditation verified: {participant.accreditation_type.value}"
        )
    
    def _check_jurisdiction(self, jurisdiction: str, asset_type: str) -> ComplianceCheck:
        """Check jurisdiction rules for an asset type."""
        rules = self._jurisdiction_rules.get(jurisdiction)
        
        if not rules:
            return self._create_check(
                f"jurisdiction_{jurisdiction}",
                True,
                f"No specific rules for jurisdiction {jurisdiction}",
                {"warning": "Unknown jurisdiction - default allow"}
            )
        
        if rules.is_restricted:
            return self._create_check(
                f"jurisdiction_{jurisdiction}",
                False,
                f"Jurisdiction {jurisdiction} is restricted: {rules.restriction_reason}"
            )
        
        if rules.blocked_asset_types and asset_type in rules.blocked_asset_types:
            return self._create_check(
                f"jurisdiction_{jurisdiction}",
                False,
                f"Asset type {asset_type} is blocked in {jurisdiction}"
            )
        
        if rules.allowed_asset_types and asset_type not in rules.allowed_asset_types:
            return self._create_check(
                f"jurisdiction_{jurisdiction}",
                False,
                f"Asset type {asset_type} not in allowed list for {jurisdiction}"
            )
        
        return self._create_check(
            f"jurisdiction_{jurisdiction}",
            True,
            f"Asset type {asset_type} is allowed in {jurisdiction}"
        )
    
    def _create_check(
        self,
        check_type: str,
        passed: bool,
        message: str,
        details: Optional[Dict] = None
    ) -> ComplianceCheck:
        """Create a compliance check result."""
        self._check_counter += 1
        return ComplianceCheck(
            check_id=f"check_{self._check_counter}",
            check_type=check_type,
            passed=passed,
            message=message,
            details=details or {},
        )
    
    def _create_report(
        self,
        action_type: str,
        subject_type: str,
        subject_id: str,
        overall_passed: bool,
        checks: List[ComplianceCheck],
        blocking_issues: List[str],
        warnings: List[str]
    ) -> ComplianceReport:
        """Create a compliance report."""
        self._report_counter += 1
        return ComplianceReport(
            report_id=f"report_{self._report_counter}",
            action_type=action_type,
            subject_type=subject_type,
            subject_id=subject_id,
            overall_passed=overall_passed,
            checks=checks,
            blocking_issues=blocking_issues,
            warnings=warnings,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )


def create_compliance_checker() -> RWAComplianceChecker:
    """Factory function to create an RWAComplianceChecker instance."""
    return RWAComplianceChecker()
