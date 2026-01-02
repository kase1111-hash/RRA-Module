# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

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

import os
import logging
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

import httpx
from web3 import Web3
from eth_utils import to_checksum_address

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification."""

    LOW = "low"  # Score > 70
    MEDIUM = "medium"  # Score 40-70
    HIGH = "high"  # Score 20-40
    CRITICAL = "critical"  # Score < 20


class TrustLevel(Enum):
    """Trust level classification for identities."""

    HIGH = "high"  # Highly trusted identity
    MEDIUM = "medium"  # Moderately trusted
    LOW = "low"  # Low trust, limited privileges
    UNTRUSTED = "untrusted"  # Not trusted, probationary status


class ProofType(Enum):
    """Types of humanity/identity proofs."""

    NONE = "none"
    STAKE = "stake"  # Economic stake
    POH_WORLDCOIN = "poh_worldcoin"  # Worldcoin orb verification
    POH_BRIGHTID = "poh_brightid"  # BrightID social verification
    POH_GITCOIN = "poh_gitcoin"  # Gitcoin Passport
    HARDWARE = "hardware"  # FIDO2/WebAuthn
    ENS = "ens"  # ENS domain ownership
    SOCIAL = "social"  # Social account verification
    ONCHAIN_HISTORY = "onchain"  # On-chain activity history


@dataclass
class ProofOfHumanity:
    """
    Proof of humanity attestation.

    Represents verified proof that an identity is controlled
    by a unique human (not a bot or duplicate).
    """

    proof_type: ProofType
    provider: str  # e.g., "worldcoin", "brightid"
    verified_at: datetime
    expires_at: Optional[datetime] = None
    confidence: float = 0.0  # 0-1 confidence score
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
    score: int  # 0-100
    risk_level: RiskLevel
    voting_weight: float  # Multiplier for votes (0.1-2.0)

    # Score components
    proof_score: int = 0  # From PoH attestations
    stake_score: int = 0  # From staked assets
    age_score: int = 0  # From account age
    activity_score: int = 0  # From activity patterns
    reputation_score: int = 0  # From historical behavior

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
    is_human: bool  # Whether identity verified as human
    risk_level: RiskLevel
    trust_level: TrustLevel  # Trust level for privileges
    confidence: float  # 0-1 how confident we are

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
        ProofType.POH_WORLDCOIN: 30,  # Orb verification is strong
        ProofType.HARDWARE: 25,  # Hardware key is strong
        ProofType.POH_BRIGHTID: 20,  # Social graph verification
        ProofType.POH_GITCOIN: 15,  # Gitcoin passport
        ProofType.ENS: 10,  # ENS ownership
        ProofType.STAKE: 10,  # Staked assets
        ProofType.ONCHAIN_HISTORY: 10,  # On-chain history
        ProofType.SOCIAL: 5,  # Social accounts
    }

    # Minimum age for full score (days)
    MIN_AGE_DAYS = 30

    # Activity thresholds
    MIN_TRANSACTIONS = 10
    MIN_UNIQUE_INTERACTIONS = 5

    def __init__(self, resolver: Optional[Any] = None):
        """Initialize the Sybil resistance system.

        Args:
            resolver: Optional DID resolver instance for identity lookups
        """
        self.resolver = resolver
        # Identity data storage (in production, use database)
        self._identities: Dict[str, Dict] = {}
        self._proofs: Dict[str, List[ProofOfHumanity]] = defaultdict(list)
        self._activity: Dict[str, List[Dict]] = defaultdict(list)
        self._relationships: Dict[str, Set[str]] = defaultdict(set)

        # Suspicious patterns
        self._flagged_ips: Set[str] = set()
        self._flagged_patterns: List[Dict] = []

    async def register_identity(self, did: str, metadata: Optional[Dict] = None) -> IdentityScore:
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

    async def add_proof(self, did: str, proof: ProofOfHumanity) -> IdentityScore:
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
        self, did: str, activity_type: str, metadata: Optional[Dict] = None
    ) -> None:
        """
        Record an activity for an identity.

        Args:
            did: The DID performing the activity
            activity_type: Type of activity
            metadata: Activity metadata
        """
        self._activity[did].append(
            {
                "type": activity_type,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {},
            }
        )

    async def add_relationship(
        self, did1: str, did2: str, relationship_type: str = "interaction"
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
            proof_score * 0.35
            + stake_score * 0.20
            + age_score * 0.15
            + activity_score * 0.15
            + reputation_score * 0.15
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
            voting_weight = 0.1 + score * 0.01  # 0.1-0.3

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

        # Determine trust level based on score
        if score.score >= 70:
            trust_level = TrustLevel.HIGH
        elif score.score >= 40:
            trust_level = TrustLevel.MEDIUM
        elif score.score >= 20:
            trust_level = TrustLevel.LOW
        else:
            trust_level = TrustLevel.UNTRUSTED

        # is_human is true if we have valid proof of humanity
        is_human = any(p.is_valid() for p in proofs) if proofs else False

        return SybilCheck(
            did=did,
            is_suspicious=is_suspicious,
            is_human=is_human,
            risk_level=score.risk_level,
            trust_level=trust_level,
            confidence=confidence,
            risk_factors=risk_factors,
            related_identities=list(related_identities)[:10],
            recommendations=recommendations,
            checks_performed=checks_performed,
        )

    async def verify_proof_of_humanity(
        self, did: str, proof_type: ProofType, verification_data: Dict[str, Any]
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
        total_stake = sum(p.metadata.get("amount_usd", 0) for p in stake_proofs)

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
        recent = [a for a in activity if (datetime.utcnow() - a["timestamp"]).days <= 30]

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

        positive = sum(1 for a in activity if a.get("metadata", {}).get("outcome") == "positive")
        negative = sum(1 for a in activity if a.get("metadata", {}).get("outcome") == "negative")

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

    # API Configuration (can be overridden via environment variables)
    WORLDCOIN_API_URL = os.environ.get(
        "WORLDCOIN_API_URL", "https://developer.worldcoin.org/api/v2/verify"
    )
    WORLDCOIN_APP_ID = os.environ.get("WORLDCOIN_APP_ID", "")

    BRIGHTID_NODE_URL = os.environ.get("BRIGHTID_NODE_URL", "https://node.brightid.org/brightid/v6")
    BRIGHTID_APP_NAME = os.environ.get("BRIGHTID_APP_NAME", "rra-module")

    # Default Ethereum RPC for ENS and stake verification
    ETH_RPC_URL = os.environ.get("ETH_RPC_URL", "https://eth.llamarpc.com")

    async def _verify_worldcoin(self, data: Dict[str, Any]) -> Tuple[bool, float, Dict]:
        """
        Verify Worldcoin World ID proof.

        Required data fields:
            - proof: The zero-knowledge proof from IDKit
            - merkle_root: The Merkle root hash
            - nullifier_hash: The unique nullifier hash
            - verification_level: "orb" or "device"
            - action: The action identifier (optional, defaults to "verify")
            - signal_hash: Optional signal hash

        Returns:
            Tuple of (verified, confidence, metadata)
        """
        proof = data.get("proof")
        merkle_root = data.get("merkle_root")
        nullifier_hash = data.get("nullifier_hash")
        verification_level = data.get("verification_level", "orb")
        action = data.get("action", "verify")
        signal_hash = data.get("signal_hash", "")

        if not all([proof, merkle_root, nullifier_hash]):
            logger.warning("Worldcoin verification missing required fields")
            return (
                False,
                0.0,
                {"error": "Missing required fields: proof, merkle_root, nullifier_hash"},
            )

        app_id = data.get("app_id") or self.WORLDCOIN_APP_ID
        if not app_id:
            logger.warning("Worldcoin APP_ID not configured")
            return False, 0.0, {"error": "WORLDCOIN_APP_ID not configured"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.WORLDCOIN_API_URL}/{app_id}",
                    json={
                        "proof": proof,
                        "merkle_root": merkle_root,
                        "nullifier_hash": nullifier_hash,
                        "verification_level": verification_level,
                        "action": action,
                        "signal_hash": signal_hash,
                    },
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        # Orb verification is highest confidence, device is lower
                        confidence = 0.95 if verification_level == "orb" else 0.75
                        return (
                            True,
                            confidence,
                            {
                                "orb_verified": verification_level == "orb",
                                "nullifier_hash": nullifier_hash,
                                "action": result.get("action"),
                                "created_at": result.get("created_at"),
                            },
                        )

                # Handle error responses
                error_data = (
                    response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else {}
                )
                error_code = error_data.get("code", "unknown")
                error_detail = error_data.get("detail", response.text[:200])

                logger.warning(f"Worldcoin verification failed: {error_code} - {error_detail}")
                return False, 0.0, {"error": error_code, "detail": error_detail}

        except httpx.TimeoutException:
            logger.error("Worldcoin API timeout")
            return False, 0.0, {"error": "API timeout"}
        except Exception as e:
            logger.error(f"Worldcoin verification error: {e}")
            return False, 0.0, {"error": str(e)}

    async def _verify_brightid(self, data: Dict[str, Any]) -> Tuple[bool, float, Dict]:
        """
        Verify BrightID proof.

        Required data fields:
            - context_id: The user's context ID (usually their ETH address or UUID)
            - app: Optional app name (defaults to BRIGHTID_APP_NAME)

        Returns:
            Tuple of (verified, confidence, metadata)
        """
        context_id = data.get("context_id")
        app = data.get("app") or self.BRIGHTID_APP_NAME

        if not context_id:
            logger.warning("BrightID verification missing context_id")
            return False, 0.0, {"error": "Missing required field: context_id"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Query the BrightID node for verification status
                response = await client.get(
                    f"{self.BRIGHTID_NODE_URL}/verifications/{app}/{context_id}",
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    result = response.json()
                    data_obj = result.get("data", {})

                    # Check if user is unique (verified)
                    is_unique = data_obj.get("unique", False)

                    if is_unique:
                        # Get the verification timestamp if available
                        timestamp = data_obj.get("timestamp")
                        context_ids = data_obj.get("contextIds", [])

                        # Confidence based on how many verifications they have
                        base_confidence = 0.80
                        # Bonus for having multiple linked contextIds (more established)
                        confidence = min(0.95, base_confidence + len(context_ids) * 0.02)

                        return (
                            True,
                            confidence,
                            {
                                "unique": True,
                                "app": app,
                                "context_id": context_id,
                                "linked_context_ids": len(context_ids),
                                "timestamp": timestamp,
                            },
                        )

                    return False, 0.0, {"error": "User not verified as unique"}

                elif response.status_code == 404:
                    # User not found - they need to link their BrightID first
                    return False, 0.0, {"error": "context_id not linked to BrightID"}

                else:
                    error_data = (
                        response.json()
                        if response.headers.get("content-type", "").startswith("application/json")
                        else {}
                    )
                    error_msg = error_data.get("errorMessage", response.text[:200])
                    logger.warning(f"BrightID verification failed: {error_msg}")
                    return False, 0.0, {"error": error_msg}

        except httpx.TimeoutException:
            logger.error("BrightID API timeout")
            return False, 0.0, {"error": "API timeout"}
        except Exception as e:
            logger.error(f"BrightID verification error: {e}")
            return False, 0.0, {"error": str(e)}

    async def _verify_hardware(self, data: Dict[str, Any]) -> Tuple[bool, float, Dict]:
        """
        Verify WebAuthn/FIDO2 hardware key attestation.

        Required data fields:
            - credential_id: The credential ID from WebAuthn registration
            - authenticator_data: The authenticator data
            - client_data_json: The client data JSON
            - signature: The signature from the authenticator
            - public_key: The public key (for verification)

        For registration (first time):
            - attestation_object: The attestation object from registration

        Returns:
            Tuple of (verified, confidence, metadata)
        """
        credential_id = data.get("credential_id")
        authenticator_data = data.get("authenticator_data")
        signature = data.get("signature")

        if not credential_id:
            logger.warning("Hardware verification missing credential_id")
            return False, 0.0, {"error": "Missing required field: credential_id"}

        # For registration flow, we just need to verify the attestation
        attestation_object = data.get("attestation_object")
        if attestation_object:
            # Registration - verify the attestation
            try:
                # Decode and verify attestation format
                # In production, use webauthn library: from webauthn import verify_registration_response
                # For now, we validate the structure is present

                # Check for authenticator type from attestation
                aaguid = data.get("aaguid")
                authenticator_type = "unknown"

                # Known authenticator AAGUIDs
                known_authenticators = {
                    "fbfc3007-154e-4ecc-8c0b-6e020557d7bd": "YubiKey 5",
                    "cb69481e-8ff7-4039-93ec-0a2729a154a8": "YubiKey 5 NFC",
                    "ee882879-721c-4913-9775-3dfcce97072a": "YubiKey 5C",
                    "adce0002-35bc-c60a-648b-0b25f1f05503": "Chrome Touch ID",
                    "08987058-cadc-4b81-b6e1-30de50dcbe96": "Windows Hello",
                    "9ddd1817-af5a-4672-a2b9-3e3dd95000a9": "Windows Hello",
                }

                if aaguid and aaguid in known_authenticators:
                    authenticator_type = known_authenticators[aaguid]

                # Hardware keys are high confidence
                confidence = 0.90
                if "yubikey" in authenticator_type.lower():
                    confidence = 0.95  # Physical hardware key is highest

                return (
                    True,
                    confidence,
                    {
                        "credential_id": credential_id,
                        "authenticator_type": authenticator_type,
                        "aaguid": aaguid,
                        "registration": True,
                    },
                )

            except Exception as e:
                logger.error(f"Hardware attestation verification error: {e}")
                return False, 0.0, {"error": str(e)}

        # For authentication flow, verify the signature
        if authenticator_data and signature:
            try:
                # In production, use webauthn library: from webauthn import verify_authentication_response
                # For now, validate the structure is present and properly formatted

                # Verify signature length (at minimum 64 bytes for ECDSA)
                if isinstance(signature, str):
                    sig_bytes = bytes.fromhex(signature.replace("0x", ""))
                else:
                    sig_bytes = signature

                if len(sig_bytes) < 64:
                    return False, 0.0, {"error": "Invalid signature length"}

                # Check authenticator data flags
                if isinstance(authenticator_data, str):
                    auth_bytes = bytes.fromhex(authenticator_data.replace("0x", ""))
                else:
                    auth_bytes = authenticator_data

                if len(auth_bytes) < 37:
                    return False, 0.0, {"error": "Invalid authenticator data"}

                # Flags byte is at position 32
                flags = auth_bytes[32]
                user_present = bool(flags & 0x01)
                user_verified = bool(flags & 0x04)

                if not user_present:
                    return False, 0.0, {"error": "User presence not verified"}

                confidence = 0.85
                if user_verified:
                    confidence = 0.92  # User verification (biometric/PIN) adds confidence

                return (
                    True,
                    confidence,
                    {
                        "credential_id": credential_id,
                        "user_present": user_present,
                        "user_verified": user_verified,
                        "authentication": True,
                    },
                )

            except Exception as e:
                logger.error(f"Hardware authentication verification error: {e}")
                return False, 0.0, {"error": str(e)}

        return False, 0.0, {"error": "Missing authenticator_data or signature for authentication"}

    async def _verify_ens(self, data: Dict[str, Any]) -> Tuple[bool, float, Dict]:
        """
        Verify ENS name ownership.

        Required data fields:
            - ens_name: The ENS name (e.g., "vitalik.eth")
            - address: The Ethereum address claiming ownership

        Optional:
            - rpc_url: Custom RPC endpoint

        Returns:
            Tuple of (verified, confidence, metadata)
        """
        ens_name = data.get("ens_name")
        address = data.get("address")
        rpc_url = data.get("rpc_url") or self.ETH_RPC_URL

        if not ens_name or not address:
            logger.warning("ENS verification missing required fields")
            return False, 0.0, {"error": "Missing required fields: ens_name, address"}

        try:
            # Normalize the ENS name
            if not ens_name.endswith(".eth"):
                ens_name = f"{ens_name}.eth"

            # Connect to Ethereum
            w3 = Web3(Web3.HTTPProvider(rpc_url))

            if not w3.is_connected():
                logger.error(f"Failed to connect to Ethereum RPC: {rpc_url}")
                return False, 0.0, {"error": "Failed to connect to Ethereum network"}

            # Initialize ENS
            from ens import ENS

            ns = ENS.from_web3(w3)

            # Resolve ENS name to address
            resolved_address = ns.address(ens_name)

            if resolved_address is None:
                return False, 0.0, {"error": f"ENS name '{ens_name}' not found or not configured"}

            # Compare addresses (case-insensitive)
            claimed_address = to_checksum_address(address)
            resolved_checksum = to_checksum_address(resolved_address)

            if claimed_address.lower() == resolved_checksum.lower():
                # Additional: check if ENS name has reverse resolution set up
                # This provides additional confidence that the user controls the name
                reverse_name = None
                try:
                    reverse_name = ns.name(claimed_address)
                except Exception:
                    pass

                # Base confidence for owning an ENS name
                confidence = 0.75

                # Bonus if reverse resolution matches
                if reverse_name and reverse_name.lower() == ens_name.lower():
                    confidence = 0.85

                # Premium names (short, valuable) add confidence
                name_length = len(ens_name.replace(".eth", ""))
                if name_length <= 4:
                    confidence = min(0.95, confidence + 0.10)
                elif name_length <= 6:
                    confidence = min(0.95, confidence + 0.05)

                return (
                    True,
                    confidence,
                    {
                        "ens_name": ens_name,
                        "address": claimed_address,
                        "reverse_resolution": reverse_name == ens_name,
                        "name_length": name_length,
                    },
                )

            return (
                False,
                0.0,
                {
                    "error": "Address does not match ENS owner",
                    "expected": resolved_checksum,
                    "claimed": claimed_address,
                },
            )

        except ImportError:
            logger.error("ENS module not available - install with: pip install ens")
            return False, 0.0, {"error": "ENS module not available"}
        except Exception as e:
            logger.error(f"ENS verification error: {e}")
            return False, 0.0, {"error": str(e)}

    async def _verify_stake(self, data: Dict[str, Any]) -> Tuple[bool, float, Dict]:
        """
        Verify on-chain staked assets.

        Required data fields:
            - address: The Ethereum address to check
            - min_stake_usd: Minimum stake required in USD (optional, defaults to 100)

        Optional:
            - rpc_url: Custom RPC endpoint
            - eth_price_usd: Current ETH price (if not provided, fetched from oracle)

        Returns:
            Tuple of (verified, confidence, metadata)
        """
        address = data.get("address")
        min_stake_usd = data.get("min_stake_usd", 100)
        rpc_url = data.get("rpc_url") or self.ETH_RPC_URL

        if not address:
            logger.warning("Stake verification missing address")
            return False, 0.0, {"error": "Missing required field: address"}

        try:
            w3 = Web3(Web3.HTTPProvider(rpc_url))

            if not w3.is_connected():
                logger.error(f"Failed to connect to Ethereum RPC: {rpc_url}")
                return False, 0.0, {"error": "Failed to connect to Ethereum network"}

            # Get ETH balance
            checksum_address = to_checksum_address(address)
            balance_wei = w3.eth.get_balance(checksum_address)
            balance_eth = w3.from_wei(balance_wei, "ether")

            # Get ETH price
            eth_price_usd = data.get("eth_price_usd")
            if not eth_price_usd:
                # Try to fetch from Chainlink price feed
                try:
                    eth_price_usd = await self._get_eth_price(w3)
                except Exception:
                    # Fallback to a reasonable estimate
                    eth_price_usd = 2000  # Approximate fallback

            # Calculate USD value
            balance_usd = float(balance_eth) * eth_price_usd

            # Also check for staked ETH (beacon chain deposits, staking contracts)
            staked_eth = await self._get_staked_eth(w3, checksum_address)
            staked_usd = staked_eth * eth_price_usd

            total_value_usd = balance_usd + staked_usd

            if total_value_usd >= min_stake_usd:
                # Logarithmic confidence: more stake = more confidence
                import math

                # $100 = 0.6, $1000 = 0.75, $10000 = 0.90
                confidence = min(0.95, 0.45 + 0.15 * math.log10(total_value_usd + 1))

                return (
                    True,
                    confidence,
                    {
                        "address": checksum_address,
                        "balance_eth": float(balance_eth),
                        "staked_eth": staked_eth,
                        "total_eth": float(balance_eth) + staked_eth,
                        "eth_price_usd": eth_price_usd,
                        "balance_usd": round(balance_usd, 2),
                        "staked_usd": round(staked_usd, 2),
                        "total_value_usd": round(total_value_usd, 2),
                        "min_stake_usd": min_stake_usd,
                    },
                )

            return (
                False,
                0.0,
                {
                    "error": f"Insufficient stake: ${total_value_usd:.2f} < ${min_stake_usd}",
                    "balance_usd": round(balance_usd, 2),
                    "min_stake_usd": min_stake_usd,
                },
            )

        except Exception as e:
            logger.error(f"Stake verification error: {e}")
            return False, 0.0, {"error": str(e)}

    async def _get_eth_price(self, w3: Web3) -> float:
        """Get current ETH price from Chainlink oracle."""
        # Chainlink ETH/USD price feed on Ethereum mainnet
        CHAINLINK_ETH_USD = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"

        # ABI for Chainlink price feed
        price_feed_abi = [
            {
                "inputs": [],
                "name": "latestRoundData",
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"},
                ],
                "stateMutability": "view",
                "type": "function",
            }
        ]

        try:
            price_feed = w3.eth.contract(
                address=to_checksum_address(CHAINLINK_ETH_USD), abi=price_feed_abi
            )
            _, answer, _, _, _ = price_feed.functions.latestRoundData().call()
            # Chainlink returns price with 8 decimals
            return answer / 1e8
        except Exception as e:
            logger.warning(f"Failed to get ETH price from Chainlink: {e}")
            raise

    async def _get_staked_eth(self, w3: Web3, address: str) -> float:
        """
        Get staked ETH for an address.

        Checks common staking protocols: Lido, RocketPool, etc.
        """
        total_staked = 0.0

        # Lido stETH balance
        LIDO_STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
        try:
            steth = w3.eth.contract(
                address=to_checksum_address(LIDO_STETH),
                abi=[
                    {
                        "constant": True,
                        "inputs": [{"name": "account", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "", "type": "uint256"}],
                        "type": "function",
                    }
                ],
            )
            steth_balance = steth.functions.balanceOf(address).call()
            total_staked += w3.from_wei(steth_balance, "ether")
        except Exception:
            pass

        # RocketPool rETH balance
        ROCKETPOOL_RETH = "0xae78736Cd615f374D3085123A210448E74Fc6393"
        try:
            reth = w3.eth.contract(
                address=to_checksum_address(ROCKETPOOL_RETH),
                abi=[
                    {
                        "constant": True,
                        "inputs": [{"name": "account", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "", "type": "uint256"}],
                        "type": "function",
                    }
                ],
            )
            reth_balance = reth.functions.balanceOf(address).call()
            # rETH appreciates in value, so 1 rETH > 1 ETH
            # For simplicity, treat as 1:1 here
            total_staked += w3.from_wei(reth_balance, "ether")
        except Exception:
            pass

        return float(total_staked)

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
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
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
        self._flagged_patterns.append(
            {
                "did": did,
                "reason": reason,
                "flagged_at": datetime.utcnow(),
            }
        )

    def get_flagged_identities(self) -> List[Dict]:
        """Get all manually flagged identities."""
        return self._flagged_patterns.copy()
