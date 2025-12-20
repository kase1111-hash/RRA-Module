# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Sybil Resistance Module for NatLangChain.

Provides mechanisms to prevent Sybil attacks where bad actors create
multiple identities to game the system. Uses multiple signals:

1. Proof of Humanity: Integration with PoH protocols
2. Stake-based resistance: Economic cost to create identities
3. Social graph analysis: Cross-referencing identity claims
4. Activity patterns: Detecting coordinated behavior
5. Hardware attestation: FIDO2/WebAuthn binding

Scoring Model:
- Each identity gets a Sybil resistance score (0-100)
- Higher scores indicate more trustworthy identities
- Scores affect voting weight in disputes
- New identities start with limited privileges

Usage:
    sybil = SybilResistance()

    # Check if identity is likely a Sybil
    check = await sybil.check_identity(did="did:ethr:0x123...")

    if check.is_suspicious:
        print(f"Warning: {check.risk_factors}")

    # Get identity score for dispute weighting
    score = await sybil.get_identity_score(did="did:ethr:0x123...")
    voting_weight = score.voting_weight
"""

import hashlib
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "low"           # Score > 70
    MEDIUM = "medium"     # Score 40-70
    HIGH = "high"         # Score 20-40
    CRITICAL = "critical" # Score < 20


class ProofType(Enum):
    """Types of humanity/identity proofs."""
    NONE = "none"
    STAKE = "stake"                    # Economic stake
    POH_WORLDCOIN = "poh_worldcoin"    # Worldcoin orb verification
    POH_BRIGHTID = "poh_brightid"      # BrightID social verification
    POH_GITCOIN = "poh_gitcoin"        # Gitcoin Passport
    HARDWARE = "hardware"              # FIDO2/WebAuthn
    ENS = "ens"                        # ENS domain ownership
    SOCIAL = "social"                  # Social account verification
    ONCHAIN_HISTORY = "onchain"        # On-chain activity history


@dataclass
class ProofOfHumanity:
    """
    Proof of humanity attestation.

    Represents verified proof that an identity is controlled
    by a unique human (not a bot or duplicate).
    """
    proof_type: ProofType
    provider: str                      # e.g., "worldcoin", "brightid"
    verified_at: datetime
    expires_at: Optional[datetime] = None
    confidence: float = 0.0            # 0-1 confidence score
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if proof is still valid."""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "proof_type": self.proof_type.value,
            "provider": self.provider,
            "verified_at": self.verified_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "confidence": self.confidence,
            "is_valid": self.is_valid(),
        }


@dataclass
class IdentityScore:
    """
    Sybil resistance score for an identity.

    Higher scores indicate more trustworthy identities.
    Used to weight votes in disputes and gate access to features.
    """
    did: str
    score: int                         # 0-100
    risk_level: RiskLevel
    voting_weight: float               # Multiplier for votes (0.1-2.0)

    # Score components
    proof_score: int = 0               # From PoH attestations
    stake_score: int = 0               # From staked assets
    age_score: int = 0                 # From account age
    activity_score: int = 0            # From activity patterns
    reputation_score: int = 0          # From historical behavior

    # Proofs held
    proofs: List[ProofOfHumanity] = field(default_factory=list)

    # Computed at
    computed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "did": self.did,
            "score": self.score,
            "risk_level": self.risk_level.value,
            "voting_weight": round(self.voting_weight, 2),
            "components": {
                "proof": self.proof_score,
                "stake": self.stake_score,
                "age": self.age_score,
                "activity": self.activity_score,
                "reputation": self.reputation_score,
            },
            "proofs": [p.to_dict() for p in self.proofs],
            "computed_at": self.computed_at.isoformat(),
        }


@dataclass
class SybilCheck:
    """
    Result of a Sybil attack check.

    Contains analysis of whether an identity appears to be
    part of a Sybil attack.
    """
    did: str
    is_suspicious: bool
    risk_level: RiskLevel
    confidence: float                  # 0-1 how confident we are

    # Risk factors detected
    risk_factors: List[str] = field(default_factory=list)

    # Related suspicious identities
    related_identities: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Analysis metadata
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    checks_performed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "did": self.did,
            "is_suspicious": self.is_suspicious,
            "risk_level": self.risk_level.value,
            "confidence": round(self.confidence, 2),
            "risk_factors": self.risk_factors,
            "related_identities": self.related_identities,
            "recommendations": self.recommendations,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class SybilResistance:
    """
    Sybil attack detection and prevention system.

    Combines multiple signals to assess identity trustworthiness
    and detect coordinated Sybil attacks.
    """

    # Score weights for different proof types
    PROOF_WEIGHTS = {
        ProofType.POH_WORLDCOIN: 30,     # Orb verification is strong
        ProofType.HARDWARE: 25,           # Hardware key is strong
        ProofType.POH_BRIGHTID: 20,       # Social graph verification
        ProofType.POH_GITCOIN: 15,        # Gitcoin passport
        ProofType.ENS: 10,                # ENS ownership
        ProofType.STAKE: 10,              # Staked assets
        ProofType.ONCHAIN_HISTORY: 10,    # On-chain history
        ProofType.SOCIAL: 5,              # Social accounts
    }

    # Minimum age for full score (days)
    MIN_AGE_DAYS = 30

    # Activity thresholds
    MIN_TRANSACTIONS = 10
    MIN_UNIQUE_INTERACTIONS = 5

    def __init__(self):
        """Initialize the Sybil resistance system."""
        # Identity data storage (in production, use database)
        self._identities: Dict[str, Dict] = {}
        self._proofs: Dict[str, List[ProofOfHumanity]] = defaultdict(list)
        self._activity: Dict[str, List[Dict]] = defaultdict(list)
        self._relationships: Dict[str, Set[str]] = defaultdict(set)

        # Suspicious patterns
        self._flagged_ips: Set[str] = set()
        self._flagged_patterns: List[Dict] = []

    async def register_identity(
        self,
        did: str,
        metadata: Optional[Dict] = None
    ) -> IdentityScore:
        """
        Register a new identity in the system.

        Args:
            did: The DID to register
            metadata: Optional identity metadata

        Returns:
            Initial IdentityScore
        """
        self._identities[did] = {
            "did": did,
            "registered_at": datetime.utcnow(),
            "metadata": metadata or {},
        }

        return await self.get_identity_score(did)

    async def add_proof(
        self,
        did: str,
        proof: ProofOfHumanity
    ) -> IdentityScore:
        """
        Add a proof of humanity to an identity.

        Args:
            did: The DID to add proof to
            proof: The proof to add

        Returns:
            Updated IdentityScore
        """
        self._proofs[did].append(proof)
        return await self.get_identity_score(did)

    async def record_activity(
        self,
        did: str,
        activity_type: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Record an activity for an identity.

        Args:
            did: The DID performing the activity
            activity_type: Type of activity
            metadata: Activity metadata
        """
        self._activity[did].append({
            "type": activity_type,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {},
        })

    async def add_relationship(
        self,
        did1: str,
        did2: str,
        relationship_type: str = "interaction"
    ) -> None:
        """
        Record a relationship between two identities.

        Args:
            did1: First DID
            did2: Second DID
            relationship_type: Type of relationship
        """
        self._relationships[did1].add(did2)
        self._relationships[did2].add(did1)

    async def get_identity_score(self, did: str) -> IdentityScore:
        """
        Calculate the Sybil resistance score for an identity.

        Args:
            did: The DID to score

        Returns:
            IdentityScore with detailed breakdown
        """
        # Get proofs
        proofs = self._proofs.get(did, [])
        valid_proofs = [p for p in proofs if p.is_valid()]

        # Calculate component scores
        proof_score = self._calculate_proof_score(valid_proofs)
        stake_score = self._calculate_stake_score(did)
        age_score = self._calculate_age_score(did)
        activity_score = self._calculate_activity_score(did)
        reputation_score = self._calculate_reputation_score(did)

        # Combine scores (weighted average)
        total_score = (
            proof_score * 0.35 +
            stake_score * 0.20 +
            age_score * 0.15 +
            activity_score * 0.15 +
            reputation_score * 0.15
        )

        # Normalize to 0-100
        score = min(100, max(0, int(total_score)))

        # Determine risk level
        risk_level = self._get_risk_level(score)

        # Calculate voting weight (0.1 to 2.0 based on score)
        # Low scores get heavily penalized, high scores get bonus
        if score >= 80:
            voting_weight = 1.5 + (score - 80) * 0.025  # 1.5-2.0
        elif score >= 50:
            voting_weight = 0.8 + (score - 50) * 0.023  # 0.8-1.5
        elif score >= 20:
            voting_weight = 0.3 + (score - 20) * 0.017  # 0.3-0.8
        else:
            voting_weight = 0.1 + score * 0.01         # 0.1-0.3

        return IdentityScore(
            did=did,
            score=score,
            risk_level=risk_level,
            voting_weight=round(voting_weight, 2),
            proof_score=proof_score,
            stake_score=stake_score,
            age_score=age_score,
            activity_score=activity_score,
            reputation_score=reputation_score,
            proofs=valid_proofs,
        )

    async def check_identity(self, did: str) -> SybilCheck:
        """
        Check if an identity is likely part of a Sybil attack.

        Args:
            did: The DID to check

        Returns:
            SybilCheck with analysis results
        """
        risk_factors = []
        related_identities = []
        recommendations = []
        checks_performed = []

        # Check 1: Proof of humanity
        checks_performed.append("proof_of_humanity")
        proofs = self._proofs.get(did, [])
        if not proofs:
            risk_factors.append("No proof of humanity attestations")
            recommendations.append("Add proof of humanity (Worldcoin, BrightID, etc.)")

        # Check 2: Account age
        checks_performed.append("account_age")
        identity = self._identities.get(did)
        if identity:
            age = (datetime.utcnow() - identity["registered_at"]).days
            if age < 7:
                risk_factors.append(f"Very new account ({age} days old)")
            elif age < 30:
                risk_factors.append(f"Relatively new account ({age} days old)")

        # Check 3: Activity patterns
        checks_performed.append("activity_patterns")
        activity = self._activity.get(did, [])
        if len(activity) < self.MIN_TRANSACTIONS:
            risk_factors.append(f"Low activity ({len(activity)} actions)")
            recommendations.append("Build activity history through legitimate participation")

        # Check 4: Relationship graph
        checks_performed.append("relationship_graph")
        relationships = self._relationships.get(did, set())
        suspicious_related = await self._find_suspicious_cluster(did)
        if suspicious_related:
            risk_factors.append("Connected to suspicious identities")
            related_identities.extend(suspicious_related)

        # Check 5: Timing patterns
        checks_performed.append("timing_patterns")
        timing_suspicious = self._check_timing_patterns(did)
        if timing_suspicious:
            risk_factors.append("Suspicious timing patterns (possible automation)")

        # Calculate overall risk
        score = await self.get_identity_score(did)
        is_suspicious = len(risk_factors) >= 2 or score.score < 30

        # Confidence based on how much data we have
        data_points = len(proofs) + len(activity) + len(relationships)
        confidence = min(0.9, 0.3 + (data_points / 50))

        return SybilCheck(
            did=did,
            is_suspicious=is_suspicious,
            risk_level=score.risk_level,
            confidence=confidence,
            risk_factors=risk_factors,
            related_identities=list(related_identities)[:10],
            recommendations=recommendations,
            checks_performed=checks_performed,
        )

    async def verify_proof_of_humanity(
        self,
        did: str,
        proof_type: ProofType,
        verification_data: Dict[str, Any]
    ) -> Optional[ProofOfHumanity]:
        """
        Verify and add a proof of humanity.

        Args:
            did: The DID claiming the proof
            proof_type: Type of proof
            verification_data: Proof-specific verification data

        Returns:
            ProofOfHumanity if verified, None otherwise
        """
        # Verify based on proof type
        verified = False
        confidence = 0.0
        metadata = {}

        if proof_type == ProofType.POH_WORLDCOIN:
            verified, confidence, metadata = await self._verify_worldcoin(verification_data)
        elif proof_type == ProofType.POH_BRIGHTID:
            verified, confidence, metadata = await self._verify_brightid(verification_data)
        elif proof_type == ProofType.HARDWARE:
            verified, confidence, metadata = await self._verify_hardware(verification_data)
        elif proof_type == ProofType.ENS:
            verified, confidence, metadata = await self._verify_ens(verification_data)
        elif proof_type == ProofType.STAKE:
            verified, confidence, metadata = await self._verify_stake(verification_data)

        if verified:
            proof = ProofOfHumanity(
                proof_type=proof_type,
                provider=verification_data.get("provider", proof_type.value),
                verified_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=365),  # 1 year validity
                confidence=confidence,
                metadata=metadata,
            )
            await self.add_proof(did, proof)
            return proof

        return None

    # =========================================================================
    # Score Calculation Methods
    # =========================================================================

    def _calculate_proof_score(self, proofs: List[ProofOfHumanity]) -> int:
        """Calculate score from proofs (0-100)."""
        if not proofs:
            return 0

        total = 0
        for proof in proofs:
            weight = self.PROOF_WEIGHTS.get(proof.proof_type, 5)
            total += weight * proof.confidence

        return min(100, int(total))

    def _calculate_stake_score(self, did: str) -> int:
        """Calculate score from staked assets (0-100)."""
        # Check for stake proofs
        proofs = self._proofs.get(did, [])
        stake_proofs = [p for p in proofs if p.proof_type == ProofType.STAKE]

        if not stake_proofs:
            return 0

        # Get stake amount from metadata
        total_stake = sum(
            p.metadata.get("amount_usd", 0)
            for p in stake_proofs
        )

        # Logarithmic scoring: $100 = 50, $1000 = 75, $10000 = 100
        if total_stake <= 0:
            return 0

        import math
        score = min(100, int(25 * math.log10(total_stake + 1)))
        return score

    def _calculate_age_score(self, did: str) -> int:
        """Calculate score from account age (0-100)."""
        identity = self._identities.get(did)
        if not identity:
            return 0

        age_days = (datetime.utcnow() - identity["registered_at"]).days

        # Linear scoring up to MIN_AGE_DAYS, then full score
        if age_days >= self.MIN_AGE_DAYS:
            return 100
        return int((age_days / self.MIN_AGE_DAYS) * 100)

    def _calculate_activity_score(self, did: str) -> int:
        """Calculate score from activity patterns (0-100)."""
        activity = self._activity.get(did, [])

        if not activity:
            return 0

        # Count recent activity (last 30 days)
        recent = [
            a for a in activity
            if (datetime.utcnow() - a["timestamp"]).days <= 30
        ]

        # Score based on activity count and diversity
        count_score = min(50, len(recent) * 5)

        # Activity type diversity
        types = set(a["type"] for a in recent)
        diversity_score = min(50, len(types) * 10)

        return count_score + diversity_score

    def _calculate_reputation_score(self, did: str) -> int:
        """Calculate score from reputation (0-100)."""
        # Check for positive/negative activity outcomes
        activity = self._activity.get(did, [])

        positive = sum(
            1 for a in activity
            if a.get("metadata", {}).get("outcome") == "positive"
        )
        negative = sum(
            1 for a in activity
            if a.get("metadata", {}).get("outcome") == "negative"
        )

        if positive + negative == 0:
            return 50  # Neutral default

        ratio = positive / (positive + negative)
        return int(ratio * 100)

    def _get_risk_level(self, score: int) -> RiskLevel:
        """Convert score to risk level."""
        if score >= 70:
            return RiskLevel.LOW
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 20:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    # =========================================================================
    # Verification Methods
    # =========================================================================

    async def _verify_worldcoin(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, Dict]:
        """Verify Worldcoin proof."""
        # TODO: Implement actual Worldcoin verification
        # For now, return mock verification
        if data.get("proof"):
            return True, 0.95, {"orb_verified": True}
        return False, 0.0, {}

    async def _verify_brightid(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, Dict]:
        """Verify BrightID proof."""
        # TODO: Implement actual BrightID verification
        if data.get("signature"):
            return True, 0.85, {"level": "meets"}
        return False, 0.0, {}

    async def _verify_hardware(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, Dict]:
        """Verify hardware attestation."""
        # TODO: Implement actual WebAuthn verification
        if data.get("credential_id"):
            return True, 0.90, {"authenticator_type": data.get("type", "unknown")}
        return False, 0.0, {}

    async def _verify_ens(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, Dict]:
        """Verify ENS ownership."""
        # TODO: Implement actual ENS verification
        if data.get("ens_name"):
            return True, 0.75, {"name": data["ens_name"]}
        return False, 0.0, {}

    async def _verify_stake(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, float, Dict]:
        """Verify staked assets."""
        # TODO: Implement actual on-chain stake verification
        amount = data.get("amount_usd", 0)
        if amount > 0:
            confidence = min(0.9, 0.5 + (amount / 10000) * 0.4)
            return True, confidence, {"amount_usd": amount}
        return False, 0.0, {}

    # =========================================================================
    # Sybil Detection Methods
    # =========================================================================

    async def _find_suspicious_cluster(self, did: str) -> List[str]:
        """Find identities that might be part of a Sybil cluster."""
        suspicious = []
        relationships = self._relationships.get(did, set())

        for related_did in relationships:
            score = await self.get_identity_score(related_did)
            if score.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                suspicious.append(related_did)

        return suspicious

    def _check_timing_patterns(self, did: str) -> bool:
        """Check for suspicious timing patterns in activity."""
        activity = self._activity.get(did, [])

        if len(activity) < 5:
            return False

        # Check for unnaturally regular timing
        timestamps = [a["timestamp"] for a in sorted(activity, key=lambda x: x["timestamp"])]

        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)

        if not intervals:
            return False

        # Check if intervals are suspiciously uniform (bot behavior)
        avg_interval = sum(intervals) / len(intervals)
        variance = sum((i - avg_interval) ** 2 for i in intervals) / len(intervals)

        # Very low variance suggests automation
        if variance < 10 and avg_interval < 60:  # Less than 10s variance, <1min average
            return True

        return False

    def flag_identity(self, did: str, reason: str) -> None:
        """Manually flag an identity as suspicious."""
        self._flagged_patterns.append({
            "did": did,
            "reason": reason,
            "flagged_at": datetime.utcnow(),
        })

    def get_flagged_identities(self) -> List[Dict]:
        """Get all manually flagged identities."""
        return self._flagged_patterns.copy()
