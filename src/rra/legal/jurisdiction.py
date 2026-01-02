# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Jurisdiction Detection module for RRA.

Provides automatic jurisdiction detection based on:
- IP address geolocation
- Participant registration data
- Asset registration authority
- Explicit declarations
- Smart contract interaction location
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import re


class JurisdictionCode(Enum):
    """ISO 3166-1 alpha-2 jurisdiction codes with regional groupings."""

    # North America
    US = "US"  # United States
    CA = "CA"  # Canada
    MX = "MX"  # Mexico

    # European Union
    DE = "DE"  # Germany
    FR = "FR"  # France
    IT = "IT"  # Italy
    ES = "ES"  # Spain
    NL = "NL"  # Netherlands
    BE = "BE"  # Belgium
    AT = "AT"  # Austria
    IE = "IE"  # Ireland
    PT = "PT"  # Portugal
    PL = "PL"  # Poland
    SE = "SE"  # Sweden
    DK = "DK"  # Denmark
    FI = "FI"  # Finland

    # Europe (non-EU)
    GB = "GB"  # United Kingdom
    CH = "CH"  # Switzerland
    NO = "NO"  # Norway

    # Asia-Pacific
    JP = "JP"  # Japan
    KR = "KR"  # South Korea
    CN = "CN"  # China
    HK = "HK"  # Hong Kong
    SG = "SG"  # Singapore
    AU = "AU"  # Australia
    NZ = "NZ"  # New Zealand
    IN = "IN"  # India

    # Offshore/Special
    KY = "KY"  # Cayman Islands
    VG = "VG"  # British Virgin Islands
    BM = "BM"  # Bermuda
    GI = "GI"  # Gibraltar

    # Other
    BR = "BR"  # Brazil
    AE = "AE"  # UAE
    IL = "IL"  # Israel

    # Restricted
    KP = "KP"  # North Korea (restricted)
    IR = "IR"  # Iran (restricted)
    CU = "CU"  # Cuba (restricted)
    SY = "SY"  # Syria (restricted)
    RU = "RU"  # Russia (restricted for some purposes)
    BY = "BY"  # Belarus (restricted)

    # Unknown/International
    XX = "XX"  # Unknown
    INT = "INT"  # International/Multi-jurisdiction


class JurisdictionRegion(Enum):
    """Regional groupings for jurisdiction."""

    NORTH_AMERICA = "north_america"
    EUROPEAN_UNION = "european_union"
    EUROPE_NON_EU = "europe_non_eu"
    ASIA_PACIFIC = "asia_pacific"
    OFFSHORE = "offshore"
    RESTRICTED = "restricted"
    OTHER = "other"
    INTERNATIONAL = "international"


class DetectionMethod(Enum):
    """Methods used to detect jurisdiction."""

    IP_GEOLOCATION = "ip_geolocation"
    REGISTRATION_DATA = "registration_data"
    ASSET_AUTHORITY = "asset_authority"
    EXPLICIT_DECLARATION = "explicit_declaration"
    SMART_CONTRACT_EVENT = "smart_contract_event"
    KYC_VERIFICATION = "kyc_verification"
    PHONE_NUMBER = "phone_number"
    ADDRESS_PARSING = "address_parsing"
    DOCUMENT_ANALYSIS = "document_analysis"


class ConfidenceLevel(Enum):
    """Confidence level of jurisdiction detection."""

    LOW = "low"  # < 50% confidence
    MEDIUM = "medium"  # 50-80% confidence
    HIGH = "high"  # 80-95% confidence
    VERIFIED = "verified"  # > 95% confidence (KYC verified)


@dataclass
class JurisdictionSignal:
    """A signal indicating a potential jurisdiction."""

    jurisdiction: JurisdictionCode
    method: DetectionMethod
    confidence: float  # 0.0 - 1.0
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JurisdictionResult:
    """Result of jurisdiction detection."""

    primary_jurisdiction: JurisdictionCode
    secondary_jurisdictions: List[JurisdictionCode]
    confidence_level: ConfidenceLevel
    confidence_score: float  # 0.0 - 1.0
    signals: List[JurisdictionSignal]
    region: JurisdictionRegion
    is_restricted: bool
    restriction_reason: Optional[str]
    detected_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))


@dataclass
class ParticipantJurisdiction:
    """Jurisdiction profile for a participant."""

    participant_id: str
    wallet_address: Optional[str]

    # Primary jurisdiction (residence/incorporation)
    primary_jurisdiction: JurisdictionCode

    # Additional jurisdictions (citizenship, business presence)
    additional_jurisdictions: List[JurisdictionCode] = field(default_factory=list)

    # Detection results
    detection_history: List[JurisdictionResult] = field(default_factory=list)

    # Explicit declarations
    declared_residence: Optional[JurisdictionCode] = None
    declared_citizenship: Optional[JurisdictionCode] = None
    declared_incorporation: Optional[JurisdictionCode] = None

    # Verification status
    kyc_verified: bool = False
    kyc_jurisdiction: Optional[JurisdictionCode] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class JurisdictionDetector:
    """
    Detector for participant and asset jurisdictions.

    Uses multiple signals to determine applicable jurisdictions
    for licensing, compliance, and legal wrapper selection.
    """

    def __init__(self):
        self._participants: Dict[str, ParticipantJurisdiction] = {}

        # Region mappings
        self._region_map: Dict[JurisdictionCode, JurisdictionRegion] = {
            JurisdictionCode.US: JurisdictionRegion.NORTH_AMERICA,
            JurisdictionCode.CA: JurisdictionRegion.NORTH_AMERICA,
            JurisdictionCode.MX: JurisdictionRegion.NORTH_AMERICA,
            JurisdictionCode.DE: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.FR: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.IT: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.ES: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.NL: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.BE: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.AT: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.IE: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.PT: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.PL: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.SE: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.DK: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.FI: JurisdictionRegion.EUROPEAN_UNION,
            JurisdictionCode.GB: JurisdictionRegion.EUROPE_NON_EU,
            JurisdictionCode.CH: JurisdictionRegion.EUROPE_NON_EU,
            JurisdictionCode.NO: JurisdictionRegion.EUROPE_NON_EU,
            JurisdictionCode.JP: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.KR: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.CN: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.HK: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.SG: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.AU: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.NZ: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.IN: JurisdictionRegion.ASIA_PACIFIC,
            JurisdictionCode.KY: JurisdictionRegion.OFFSHORE,
            JurisdictionCode.VG: JurisdictionRegion.OFFSHORE,
            JurisdictionCode.BM: JurisdictionRegion.OFFSHORE,
            JurisdictionCode.GI: JurisdictionRegion.OFFSHORE,
            JurisdictionCode.KP: JurisdictionRegion.RESTRICTED,
            JurisdictionCode.IR: JurisdictionRegion.RESTRICTED,
            JurisdictionCode.CU: JurisdictionRegion.RESTRICTED,
            JurisdictionCode.SY: JurisdictionRegion.RESTRICTED,
            JurisdictionCode.RU: JurisdictionRegion.RESTRICTED,
            JurisdictionCode.BY: JurisdictionRegion.RESTRICTED,
            JurisdictionCode.BR: JurisdictionRegion.OTHER,
            JurisdictionCode.AE: JurisdictionRegion.OTHER,
            JurisdictionCode.IL: JurisdictionRegion.OTHER,
            JurisdictionCode.XX: JurisdictionRegion.INTERNATIONAL,
            JurisdictionCode.INT: JurisdictionRegion.INTERNATIONAL,
        }

        # Restricted jurisdictions
        self._restricted: Set[JurisdictionCode] = {
            JurisdictionCode.KP,
            JurisdictionCode.IR,
            JurisdictionCode.CU,
            JurisdictionCode.SY,
        }

        # Partially restricted (sanctions)
        self._partially_restricted: Dict[JurisdictionCode, str] = {
            JurisdictionCode.RU: "Subject to various sectoral sanctions",
            JurisdictionCode.BY: "Subject to various sectoral sanctions",
        }

        # IP registration authority to jurisdiction mapping
        self._authority_jurisdiction: Dict[str, JurisdictionCode] = {
            "USPTO": JurisdictionCode.US,
            "USCO": JurisdictionCode.US,
            "EPO": JurisdictionCode.DE,  # Uses DE as representative
            "WIPO": JurisdictionCode.INT,
            "JPO": JurisdictionCode.JP,
            "CNIPA": JurisdictionCode.CN,
            "KIPO": JurisdictionCode.KR,
            "UKIPO": JurisdictionCode.GB,
            "CIPO": JurisdictionCode.CA,
            "IP_AUSTRALIA": JurisdictionCode.AU,
            "INPI_FR": JurisdictionCode.FR,
            "DPMA": JurisdictionCode.DE,
        }

        # Phone prefix to jurisdiction
        self._phone_prefixes: Dict[str, JurisdictionCode] = {
            "+1": JurisdictionCode.US,  # Also CA
            "+44": JurisdictionCode.GB,
            "+49": JurisdictionCode.DE,
            "+33": JurisdictionCode.FR,
            "+81": JurisdictionCode.JP,
            "+86": JurisdictionCode.CN,
            "+82": JurisdictionCode.KR,
            "+65": JurisdictionCode.SG,
            "+61": JurisdictionCode.AU,
            "+41": JurisdictionCode.CH,
            "+31": JurisdictionCode.NL,
            "+39": JurisdictionCode.IT,
            "+34": JurisdictionCode.ES,
            "+91": JurisdictionCode.IN,
            "+971": JurisdictionCode.AE,
            "+972": JurisdictionCode.IL,
            "+55": JurisdictionCode.BR,
            "+852": JurisdictionCode.HK,
        }

    def detect_from_ip(
        self, ip_address: str, geolocation_data: Optional[Dict[str, Any]] = None
    ) -> JurisdictionSignal:
        """
        Detect jurisdiction from IP address.

        Note: In production, this would use a real geolocation service.
        """
        # Mock implementation - would use MaxMind, IP2Location, etc.
        country_code = "US"  # Default
        confidence = 0.7

        if geolocation_data:
            country_code = geolocation_data.get("country_code", "US")
            confidence = geolocation_data.get("accuracy", 0.7)

        try:
            jurisdiction = JurisdictionCode(country_code)
        except ValueError:
            jurisdiction = JurisdictionCode.XX
            confidence = 0.3

        return JurisdictionSignal(
            jurisdiction=jurisdiction,
            method=DetectionMethod.IP_GEOLOCATION,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            source=ip_address,
            metadata=geolocation_data or {},
        )

    def detect_from_phone(self, phone_number: str) -> Optional[JurisdictionSignal]:
        """Detect jurisdiction from phone number prefix."""
        # Normalize phone number
        phone = re.sub(r"[^\d+]", "", phone_number)

        for prefix, jurisdiction in self._phone_prefixes.items():
            if phone.startswith(prefix):
                return JurisdictionSignal(
                    jurisdiction=jurisdiction,
                    method=DetectionMethod.PHONE_NUMBER,
                    confidence=0.8,
                    timestamp=datetime.utcnow(),
                    source=phone_number,
                    metadata={"prefix": prefix},
                )

        return None

    def detect_from_address(self, address: str) -> Optional[JurisdictionSignal]:
        """
        Detect jurisdiction from postal address.

        Uses simple pattern matching for country names/codes.
        """
        address_upper = address.upper()

        # Country name patterns
        country_patterns: Dict[str, JurisdictionCode] = {
            "UNITED STATES": JurisdictionCode.US,
            "USA": JurisdictionCode.US,
            "U.S.A": JurisdictionCode.US,
            "UNITED KINGDOM": JurisdictionCode.GB,
            "UK": JurisdictionCode.GB,
            "GREAT BRITAIN": JurisdictionCode.GB,
            "GERMANY": JurisdictionCode.DE,
            "DEUTSCHLAND": JurisdictionCode.DE,
            "FRANCE": JurisdictionCode.FR,
            "JAPAN": JurisdictionCode.JP,
            "CHINA": JurisdictionCode.CN,
            "SINGAPORE": JurisdictionCode.SG,
            "AUSTRALIA": JurisdictionCode.AU,
            "CANADA": JurisdictionCode.CA,
            "SWITZERLAND": JurisdictionCode.CH,
            "NETHERLANDS": JurisdictionCode.NL,
            "HONG KONG": JurisdictionCode.HK,
            "SOUTH KOREA": JurisdictionCode.KR,
            "KOREA": JurisdictionCode.KR,
        }

        for pattern, jurisdiction in country_patterns.items():
            if pattern in address_upper:
                return JurisdictionSignal(
                    jurisdiction=jurisdiction,
                    method=DetectionMethod.ADDRESS_PARSING,
                    confidence=0.85,
                    timestamp=datetime.utcnow(),
                    source=address,
                    metadata={"matched_pattern": pattern},
                )

        # Check for US state abbreviations with ZIP codes
        us_pattern = re.search(r"\b[A-Z]{2}\s+\d{5}(-\d{4})?\b", address_upper)
        if us_pattern:
            return JurisdictionSignal(
                jurisdiction=JurisdictionCode.US,
                method=DetectionMethod.ADDRESS_PARSING,
                confidence=0.9,
                timestamp=datetime.utcnow(),
                source=address,
                metadata={"matched_pattern": "US_ZIP"},
            )

        return None

    def detect_from_authority(self, authority: str) -> Optional[JurisdictionSignal]:
        """Detect jurisdiction from IP registration authority."""
        authority_upper = authority.upper().replace(" ", "_")

        if authority_upper in self._authority_jurisdiction:
            return JurisdictionSignal(
                jurisdiction=self._authority_jurisdiction[authority_upper],
                method=DetectionMethod.ASSET_AUTHORITY,
                confidence=0.95,
                timestamp=datetime.utcnow(),
                source=authority,
                metadata={"authority": authority_upper},
            )

        return None

    def declare_jurisdiction(
        self,
        participant_id: str,
        jurisdiction: JurisdictionCode,
        declaration_type: str = "residence",
    ) -> JurisdictionSignal:
        """Record an explicit jurisdiction declaration."""
        return JurisdictionSignal(
            jurisdiction=jurisdiction,
            method=DetectionMethod.EXPLICIT_DECLARATION,
            confidence=0.9,
            timestamp=datetime.utcnow(),
            source=f"declaration:{participant_id}",
            metadata={"declaration_type": declaration_type},
        )

    def verify_from_kyc(
        self, participant_id: str, kyc_jurisdiction: JurisdictionCode, kyc_provider: str
    ) -> JurisdictionSignal:
        """Record KYC-verified jurisdiction."""
        return JurisdictionSignal(
            jurisdiction=kyc_jurisdiction,
            method=DetectionMethod.KYC_VERIFICATION,
            confidence=0.99,
            timestamp=datetime.utcnow(),
            source=f"kyc:{kyc_provider}",
            metadata={"provider": kyc_provider, "participant": participant_id},
        )

    def aggregate_signals(self, signals: List[JurisdictionSignal]) -> JurisdictionResult:
        """Aggregate multiple jurisdiction signals into a result."""
        if not signals:
            return JurisdictionResult(
                primary_jurisdiction=JurisdictionCode.XX,
                secondary_jurisdictions=[],
                confidence_level=ConfidenceLevel.LOW,
                confidence_score=0.0,
                signals=[],
                region=JurisdictionRegion.INTERNATIONAL,
                is_restricted=False,
                restriction_reason=None,
            )

        # Weight signals by confidence and method
        method_weights = {
            DetectionMethod.KYC_VERIFICATION: 1.0,
            DetectionMethod.EXPLICIT_DECLARATION: 0.9,
            DetectionMethod.REGISTRATION_DATA: 0.85,
            DetectionMethod.ASSET_AUTHORITY: 0.85,
            DetectionMethod.ADDRESS_PARSING: 0.8,
            DetectionMethod.PHONE_NUMBER: 0.7,
            DetectionMethod.IP_GEOLOCATION: 0.6,
            DetectionMethod.SMART_CONTRACT_EVENT: 0.5,
            DetectionMethod.DOCUMENT_ANALYSIS: 0.75,
        }

        # Calculate weighted scores per jurisdiction
        jurisdiction_scores: Dict[JurisdictionCode, float] = {}
        for signal in signals:
            weight = method_weights.get(signal.method, 0.5)
            score = signal.confidence * weight

            if signal.jurisdiction not in jurisdiction_scores:
                jurisdiction_scores[signal.jurisdiction] = 0
            jurisdiction_scores[signal.jurisdiction] += score

        # Sort by score
        sorted_jurisdictions = sorted(jurisdiction_scores.items(), key=lambda x: x[1], reverse=True)

        primary = sorted_jurisdictions[0][0]
        primary_score = sorted_jurisdictions[0][1]

        # Normalize score
        total_score = sum(jurisdiction_scores.values())
        confidence_score = primary_score / total_score if total_score > 0 else 0

        # Determine confidence level
        if any(s.method == DetectionMethod.KYC_VERIFICATION for s in signals):
            confidence_level = ConfidenceLevel.VERIFIED
        elif confidence_score > 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence_score > 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        # Get secondary jurisdictions
        secondary = [j for j, _ in sorted_jurisdictions[1:4]]

        # Check restrictions
        is_restricted = primary in self._restricted
        restriction_reason = None
        if is_restricted:
            restriction_reason = "OFAC sanctioned jurisdiction"
        elif primary in self._partially_restricted:
            restriction_reason = self._partially_restricted[primary]

        return JurisdictionResult(
            primary_jurisdiction=primary,
            secondary_jurisdictions=secondary,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            signals=signals,
            region=self._region_map.get(primary, JurisdictionRegion.OTHER),
            is_restricted=is_restricted,
            restriction_reason=restriction_reason,
        )

    def register_participant(
        self,
        participant_id: str,
        wallet_address: Optional[str] = None,
        initial_signals: Optional[List[JurisdictionSignal]] = None,
    ) -> ParticipantJurisdiction:
        """Register a participant for jurisdiction tracking."""
        signals = initial_signals or []

        if signals:
            result = self.aggregate_signals(signals)
            primary = result.primary_jurisdiction
        else:
            primary = JurisdictionCode.XX

        profile = ParticipantJurisdiction(
            participant_id=participant_id,
            wallet_address=wallet_address,
            primary_jurisdiction=primary,
            detection_history=[self.aggregate_signals(signals)] if signals else [],
        )

        self._participants[participant_id] = profile
        return profile

    def get_participant(self, participant_id: str) -> Optional[ParticipantJurisdiction]:
        """Get participant jurisdiction profile."""
        return self._participants.get(participant_id)

    def update_participant_jurisdiction(
        self, participant_id: str, signals: List[JurisdictionSignal]
    ) -> ParticipantJurisdiction:
        """Update participant jurisdiction with new signals."""
        profile = self._participants.get(participant_id)
        if not profile:
            raise ValueError(f"Participant {participant_id} not found")

        result = self.aggregate_signals(signals)
        profile.primary_jurisdiction = result.primary_jurisdiction
        profile.additional_jurisdictions = result.secondary_jurisdictions
        profile.detection_history.append(result)
        profile.updated_at = datetime.utcnow()

        return profile

    def set_kyc_verification(
        self, participant_id: str, jurisdiction: JurisdictionCode, provider: str
    ) -> ParticipantJurisdiction:
        """Set KYC-verified jurisdiction for participant."""
        profile = self._participants.get(participant_id)
        if not profile:
            raise ValueError(f"Participant {participant_id} not found")

        profile.kyc_verified = True
        profile.kyc_jurisdiction = jurisdiction
        profile.primary_jurisdiction = jurisdiction  # KYC overrides other signals
        profile.updated_at = datetime.utcnow()

        # Add KYC signal to history
        signal = self.verify_from_kyc(participant_id, jurisdiction, provider)
        result = self.aggregate_signals([signal])
        profile.detection_history.append(result)

        return profile

    def get_region(self, jurisdiction: JurisdictionCode) -> JurisdictionRegion:
        """Get the region for a jurisdiction."""
        return self._region_map.get(jurisdiction, JurisdictionRegion.OTHER)

    def is_restricted(self, jurisdiction: JurisdictionCode) -> Tuple[bool, Optional[str]]:
        """Check if a jurisdiction is restricted."""
        if jurisdiction in self._restricted:
            return True, "OFAC sanctioned jurisdiction"
        if jurisdiction in self._partially_restricted:
            return False, self._partially_restricted[jurisdiction]
        return False, None

    def get_eu_jurisdictions(self) -> List[JurisdictionCode]:
        """Get list of EU member state jurisdictions."""
        return [j for j, r in self._region_map.items() if r == JurisdictionRegion.EUROPEAN_UNION]

    def are_compatible(
        self, jurisdiction1: JurisdictionCode, jurisdiction2: JurisdictionCode
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if two jurisdictions are compatible for transactions.

        Returns (compatible, reason_if_not).
        """
        # Check if either is restricted
        is_restricted1, reason1 = self.is_restricted(jurisdiction1)
        is_restricted2, reason2 = self.is_restricted(jurisdiction2)

        if is_restricted1:
            return False, f"{jurisdiction1.value} is restricted: {reason1}"
        if is_restricted2:
            return False, f"{jurisdiction2.value} is restricted: {reason2}"

        # Both in EU - highly compatible
        eu_jurisdictions = set(self.get_eu_jurisdictions())
        if jurisdiction1 in eu_jurisdictions and jurisdiction2 in eu_jurisdictions:
            return True, None

        # Generally compatible unless there are specific restrictions
        return True, None


def create_jurisdiction_detector() -> JurisdictionDetector:
    """Factory function to create a JurisdictionDetector."""
    return JurisdictionDetector()
