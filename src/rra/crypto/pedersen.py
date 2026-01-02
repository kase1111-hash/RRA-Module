# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Pedersen Commitments for On-Chain Evidence Proofs.

SECURITY FIX: Now uses proper elliptic curve point multiplication
instead of modular exponentiation.

Properties:
- Hiding: Commitment reveals nothing about the value
- Binding: Cannot open commitment to different value
- Homomorphic: Commitments can be combined

Use Cases:
- Prove dispute evidence exists before revealing
- Commit to viewing key without exposing it
- Aggregate proofs for batch verification
"""

import os
import hashlib
import hmac
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from eth_utils import keccak
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


# BN254/BN128 curve parameters (used in Ethereum ZK applications)
# Field prime p (verified against EIP-196)
BN254_FIELD_PRIME = 21888242871839275222246405745257275088696311157297823662689037894645226208583
# Curve order n (number of points, verified against EIP-196)
BN254_CURVE_ORDER = 21888242871839275222246405745257275088548364400416034343698204186575808495617

# BN254 curve equation: y^2 = x^3 + 3 (mod p)
BN254_CURVE_B = 3


def _is_on_curve(point: tuple) -> bool:
    """
    Verify that a point is on the BN254 curve.

    BN254 curve equation: y^2 = x^3 + 3 (mod p)

    Args:
        point: (x, y) coordinates

    Returns:
        True if point is on the curve
    """
    if point == (0, 0):  # Point at infinity is valid
        return True

    x, y = point
    # Verify y^2 = x^3 + 3 (mod p)
    left = (y * y) % BN254_FIELD_PRIME
    right = (pow(x, 3, BN254_FIELD_PRIME) + BN254_CURVE_B) % BN254_FIELD_PRIME
    return left == right


def _verify_generator_points() -> None:
    """
    Verify that generator points G and H are valid curve points.

    Raises:
        ValueError: If any generator point is not on the curve
    """
    if not _is_on_curve(G_POINT):
        raise ValueError("G_POINT is not on the BN254 curve")
    if not _is_on_curve(H_POINT):
        raise ValueError("H_POINT is not on the BN254 curve")


def _hash_to_scalar(data: bytes, domain: bytes = b"") -> int:
    """
    Hash data to a scalar in the curve's field.

    Uses domain separation to prevent cross-protocol attacks.
    """
    # Domain-separated hash
    h = hashlib.sha256(domain + b":" + data).digest()
    # Reduce modulo curve order
    return int.from_bytes(h, "big") % BN254_CURVE_ORDER


def _derive_generator_point(seed: bytes) -> Tuple[int, int]:
    """
    Derive a generator point using hash-to-curve.

    This is a simplified version - production should use RFC 9380.
    Uses try-and-increment method with proper domain separation.
    """
    domain = b"pedersen-generator-rra-v1"

    for counter in range(256):
        # Hash seed with counter
        attempt = hashlib.sha256(domain + seed + counter.to_bytes(1, "big")).digest()
        x = int.from_bytes(attempt, "big") % BN254_FIELD_PRIME

        # Try to compute y^2 = x^3 + 3 (BN254 curve equation: y^2 = x^3 + 3)
        y_squared = (pow(x, 3, BN254_FIELD_PRIME) + 3) % BN254_FIELD_PRIME

        # Check if y_squared is a quadratic residue (has square root)
        # Using Euler's criterion: a^((p-1)/2) = 1 (mod p) if a is QR
        if pow(y_squared, (BN254_FIELD_PRIME - 1) // 2, BN254_FIELD_PRIME) == 1:
            # Compute square root using Tonelli-Shanks (simplified for this prime)
            y = pow(y_squared, (BN254_FIELD_PRIME + 1) // 4, BN254_FIELD_PRIME)
            # Verify
            if (y * y) % BN254_FIELD_PRIME == y_squared:
                return (x, y)

    raise ValueError("Failed to derive generator point")


# Generator points derived using nothing-up-my-sleeve construction
# G is the standard BN254 generator
G_POINT = (1, 2)  # Standard BN254 G1 generator

# H is derived from a fixed seed - cannot be computed as k*G for known k
H_POINT = _derive_generator_point(b"pedersen-h-seed-2025")


# Verify generator points at module load time
def _validate_curve_constants() -> None:
    """Validate all curve constants at module initialization."""
    # Verify field prime and curve order match EIP-196
    expected_p = 21888242871839275222246405745257275088696311157297823662689037894645226208583
    expected_n = 21888242871839275222246405745257275088548364400416034343698204186575808495617

    if BN254_FIELD_PRIME != expected_p:
        raise ValueError("BN254_FIELD_PRIME does not match EIP-196")
    if BN254_CURVE_ORDER != expected_n:
        raise ValueError("BN254_CURVE_ORDER does not match EIP-196")

    # Verify generator points are on the curve
    _verify_generator_points()


# Run validation at module load
_validate_curve_constants()


def _point_add(p1: Tuple[int, int], p2: Tuple[int, int]) -> Tuple[int, int]:
    """Add two points on BN254 curve."""
    if p1 == (0, 0):
        return p2
    if p2 == (0, 0):
        return p1

    x1, y1 = p1
    x2, y2 = p2

    if x1 == x2:
        if y1 == y2:
            # Point doubling
            if y1 == 0:
                return (0, 0)  # Point at infinity
            # lambda = (3*x1^2) / (2*y1)
            num = (3 * x1 * x1) % BN254_FIELD_PRIME
            denom = (2 * y1) % BN254_FIELD_PRIME
            lam = (num * pow(denom, BN254_FIELD_PRIME - 2, BN254_FIELD_PRIME)) % BN254_FIELD_PRIME
        else:
            # P + (-P) = O (point at infinity)
            return (0, 0)
    else:
        # Point addition
        # lambda = (y2 - y1) / (x2 - x1)
        num = (y2 - y1) % BN254_FIELD_PRIME
        denom = (x2 - x1) % BN254_FIELD_PRIME
        lam = (num * pow(denom, BN254_FIELD_PRIME - 2, BN254_FIELD_PRIME)) % BN254_FIELD_PRIME

    # x3 = lambda^2 - x1 - x2
    x3 = (lam * lam - x1 - x2) % BN254_FIELD_PRIME
    # y3 = lambda * (x1 - x3) - y1
    y3 = (lam * (x1 - x3) - y1) % BN254_FIELD_PRIME

    return (x3, y3)


def _scalar_mult(k: int, point: Tuple[int, int]) -> Tuple[int, int]:
    """Multiply point by scalar using double-and-add."""
    if k == 0:
        return (0, 0)
    if k < 0:
        k = -k
        point = (point[0], (-point[1]) % BN254_FIELD_PRIME)

    result = (0, 0)  # Point at infinity
    addend = point

    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1

    return result


def _point_to_bytes(point: Tuple[int, int]) -> bytes:
    """Serialize EC point to 64 bytes (x || y)."""
    if point == (0, 0):
        return b"\x00" * 64
    x, y = point
    return x.to_bytes(32, "big") + y.to_bytes(32, "big")


def _bytes_to_point(data: bytes) -> Tuple[int, int]:
    """
    Deserialize EC point from 64 bytes with curve validation.

    SECURITY: Validates that the deserialized point lies on the BN254 curve
    to prevent invalid curve attacks that could enable commitment forgery.

    Args:
        data: 64 bytes (x || y)

    Returns:
        (x, y) point on the curve

    Raises:
        ValueError: If data is not 64 bytes or point is not on curve
    """
    if len(data) != 64:
        raise ValueError("Point must be 64 bytes")
    if data == b"\x00" * 64:
        return (0, 0)
    x = int.from_bytes(data[:32], "big")
    y = int.from_bytes(data[32:], "big")
    point = (x, y)

    # SECURITY: Validate point is on the curve
    if not _is_on_curve(point):
        raise ValueError("Deserialized point is not on the BN254 curve")

    return point


@dataclass
class CommitmentProof:
    """
    Proof that a commitment was correctly formed.

    Used for on-chain verification without revealing the value.
    """

    commitment: bytes  # The commitment (64 bytes, EC point)
    blinding_factor_hash: bytes  # Hash of blinding factor for verification
    created_at: datetime
    context_id: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "commitment": self.commitment.hex(),
            "blinding_factor_hash": self.blinding_factor_hash.hex(),
            "created_at": self.created_at.isoformat(),
            "context_id": self.context_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommitmentProof":
        """Deserialize from dictionary."""
        return cls(
            commitment=bytes.fromhex(data["commitment"]),
            blinding_factor_hash=bytes.fromhex(data["blinding_factor_hash"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            context_id=data["context_id"],
            metadata=data.get("metadata", {}),
        )

    def to_bytes(self) -> bytes:
        """Compact binary serialization for on-chain storage."""
        return self.commitment + self.blinding_factor_hash


class PedersenCommitment:
    """
    Pedersen commitment scheme using proper elliptic curve math.

    SECURITY: Uses EC point multiplication (not modular exponentiation).

    Commitment: C = v*G + r*H
    where:
    - v is the value being committed (scalar)
    - r is a random blinding factor (scalar)
    - G, H are generator points on BN254
    - * denotes scalar multiplication
    - + denotes point addition
    """

    def __init__(
        self,
        g: Tuple[int, int] = G_POINT,
        h: Tuple[int, int] = H_POINT,
        order: int = BN254_CURVE_ORDER,
    ):
        """
        Initialize with generator points.

        Args:
            g: First generator point
            h: Second generator point (for blinding)
            order: Curve order
        """
        self.g = g
        self.h = h
        self.order = order

    def commit(self, value: bytes, blinding: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Create a Pedersen commitment to a value.

        C = v*G + r*H (EC point multiplication and addition)

        Args:
            value: Value to commit (max 32 bytes)
            blinding: Optional blinding factor (random if not provided)

        Returns:
            Tuple of (commitment_bytes, blinding_factor)
        """
        # Convert value to scalar
        if len(value) > 32:
            raise ValueError("Value must be at most 32 bytes")
        v = int.from_bytes(value.ljust(32, b"\x00"), "big") % self.order

        # Generate or use provided blinding factor
        if blinding is None:
            blinding = os.urandom(32)
        r = int.from_bytes(blinding, "big") % self.order

        # Compute commitment: C = v*G + r*H (proper EC math!)
        vG = _scalar_mult(v, self.g)
        rH = _scalar_mult(r, self.h)
        C = _point_add(vG, rH)

        # SECURITY: Reject point-at-infinity as commitment
        # Point at infinity reveals that v*G = -(r*H), leaking information
        if C == (0, 0):
            raise ValueError(
                "Commitment resulted in point-at-infinity; "
                "this leaks information about the value"
            )

        commitment = _point_to_bytes(C)
        return commitment, blinding

    def verify(self, commitment: bytes, value: bytes, blinding: bytes) -> bool:
        """
        Verify a commitment opening.

        Args:
            commitment: The commitment (64 bytes)
            value: Claimed value
            blinding: Blinding factor used

        Returns:
            True if commitment is valid for value and blinding
        """
        try:
            expected_commitment, _ = self.commit(value, blinding)
            # Use constant-time comparison
            return hmac.compare_digest(commitment, expected_commitment)
        except Exception:
            return False

    def commit_evidence(
        self, evidence_hash: bytes, context_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[CommitmentProof, bytes]:
        """
        Create a commitment proof for evidence.

        Args:
            evidence_hash: Hash of the evidence
            context_id: Context identifier (e.g., dispute ID)
            metadata: Optional metadata

        Returns:
            Tuple of (CommitmentProof, blinding_factor)
        """
        commitment, blinding = self.commit(evidence_hash)

        # Hash the blinding factor for later verification
        blinding_hash = keccak(blinding)

        proof = CommitmentProof(
            commitment=commitment,
            blinding_factor_hash=blinding_hash,
            created_at=datetime.utcnow(),
            context_id=context_id,
            metadata=metadata or {},
        )

        return proof, blinding

    def verify_evidence_commitment(
        self, proof: CommitmentProof, evidence_hash: bytes, blinding: bytes
    ) -> bool:
        """
        Verify an evidence commitment proof.

        Args:
            proof: The commitment proof
            evidence_hash: Hash of the evidence
            blinding: Blinding factor

        Returns:
            True if proof is valid
        """
        # Verify blinding factor matches (constant-time)
        expected_blinding_hash = keccak(blinding)
        if not hmac.compare_digest(expected_blinding_hash, proof.blinding_factor_hash):
            return False

        # Verify commitment
        return self.verify(proof.commitment, evidence_hash, blinding)

    @staticmethod
    def hash_evidence(evidence: bytes, context: str = "evidence") -> bytes:
        """
        Hash evidence for commitment with domain separation.

        Args:
            evidence: Raw evidence data
            context: Domain separator

        Returns:
            32-byte hash
        """
        # Domain-separated hash prevents cross-context collisions
        return keccak(context.encode() + b":" + evidence)

    def aggregate_commitments(self, commitments: List[bytes]) -> bytes:
        """
        Homomorphically aggregate multiple commitments.

        C_agg = C_1 + C_2 + ... + C_n (EC point addition)

        Args:
            commitments: List of commitments to aggregate (64 bytes each)

        Returns:
            Aggregated commitment (64 bytes)
        """
        result = (0, 0)  # Point at infinity
        for c in commitments:
            point = _bytes_to_point(c)
            result = _point_add(result, point)

        return _point_to_bytes(result)


class EvidenceCommitmentManager:
    """
    High-level manager for evidence commitments.

    Handles commitment creation, storage, and verification workflows.
    """

    def __init__(self):
        """Initialize the commitment manager."""
        self.pedersen = PedersenCommitment()
        self._commitments: Dict[str, CommitmentProof] = {}
        self._blindings: Dict[str, bytes] = {}

    def commit_dispute_evidence(self, dispute_id: str, evidence: bytes) -> CommitmentProof:
        """
        Create a commitment for dispute evidence.

        Args:
            dispute_id: Dispute identifier
            evidence: Raw evidence data

        Returns:
            CommitmentProof for on-chain storage
        """
        # Domain-separated hash
        evidence_hash = self.pedersen.hash_evidence(evidence, f"dispute:{dispute_id}")

        proof, blinding = self.pedersen.commit_evidence(
            evidence_hash, context_id=dispute_id, metadata={"evidence_size": len(evidence)}
        )

        # Store for later revelation
        self._commitments[dispute_id] = proof
        self._blindings[dispute_id] = blinding

        return proof

    def reveal_evidence(self, dispute_id: str, evidence: bytes) -> Tuple[bytes, bytes]:
        """
        Prepare evidence revelation with proof.

        Args:
            dispute_id: Dispute identifier
            evidence: Raw evidence to reveal

        Returns:
            Tuple of (evidence_hash, blinding_factor)

        Raises:
            ValueError: If no commitment exists
        """
        if dispute_id not in self._blindings:
            raise ValueError(f"No commitment found for dispute {dispute_id}")

        evidence_hash = self.pedersen.hash_evidence(evidence, f"dispute:{dispute_id}")
        blinding = self._blindings[dispute_id]

        return evidence_hash, blinding

    def verify_revelation(self, dispute_id: str, evidence: bytes, blinding: bytes) -> bool:
        """
        Verify that revealed evidence matches commitment.

        Args:
            dispute_id: Dispute identifier
            evidence: Revealed evidence
            blinding: Revealed blinding factor

        Returns:
            True if revelation is valid
        """
        if dispute_id not in self._commitments:
            return False

        proof = self._commitments[dispute_id]
        evidence_hash = self.pedersen.hash_evidence(evidence, f"dispute:{dispute_id}")

        return self.pedersen.verify_evidence_commitment(proof, evidence_hash, blinding)

    def get_commitment_for_chain(self, dispute_id: str) -> bytes:
        """
        Get the commitment bytes for on-chain storage.

        Args:
            dispute_id: Dispute identifier

        Returns:
            64-byte commitment (EC point)

        Raises:
            ValueError: If no commitment exists
        """
        if dispute_id not in self._commitments:
            raise ValueError(f"No commitment found for dispute {dispute_id}")

        return self._commitments[dispute_id].commitment

    def batch_commit(
        self, dispute_id: str, evidence_list: List[bytes]
    ) -> Tuple[bytes, List[bytes]]:
        """
        Create aggregated commitment for multiple evidence items.

        Args:
            dispute_id: Dispute identifier
            evidence_list: List of evidence items

        Returns:
            Tuple of (aggregated_commitment, list_of_blindings)
        """
        commitments = []
        blindings = []

        for i, evidence in enumerate(evidence_list):
            evidence_hash = self.pedersen.hash_evidence(evidence, f"dispute:{dispute_id}:item:{i}")
            commitment, blinding = self.pedersen.commit(evidence_hash)
            commitments.append(commitment)
            blindings.append(blinding)

        aggregated = self.pedersen.aggregate_commitments(commitments)

        return aggregated, blindings
