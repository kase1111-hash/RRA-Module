# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Pedersen Commitments for On-Chain Evidence Proofs.

Enables proving existence of evidence without revealing content.

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
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from eth_utils import keccak


# Generator points for Pedersen commitment
# In production, these would be derived from a trusted setup
# or use a hash-to-curve function
# For now, we use deterministic derivation from fixed seeds

def _derive_generator(seed: bytes) -> int:
    """Derive a generator point from seed (simplified)."""
    # This is a simplified version - in production use proper
    # hash-to-curve or trusted setup
    h = hashlib.sha256(seed).digest()
    return int.from_bytes(h, 'big')


# BN254 curve order (common for Ethereum ZK applications)
CURVE_ORDER = 21888242871839275222246405745257275088548364400416034343698204186575808495617

# Generator points
G = _derive_generator(b"pedersen-g-v1")
H = _derive_generator(b"pedersen-h-v1")


@dataclass
class CommitmentProof:
    """
    Proof that a commitment was correctly formed.

    Used for on-chain verification without revealing the value.
    """
    commitment: bytes  # The commitment itself
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
    def from_dict(cls, data: Dict[str, Any]) -> 'CommitmentProof':
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
    Pedersen commitment scheme implementation.

    Commitment: C = g^v * h^r (mod p)
    where:
    - v is the value being committed
    - r is a random blinding factor
    - g, h are generator points
    """

    def __init__(
        self,
        g: int = G,
        h: int = H,
        order: int = CURVE_ORDER
    ):
        """
        Initialize with generator points.

        Args:
            g: First generator
            h: Second generator (for blinding)
            order: Curve/group order
        """
        self.g = g
        self.h = h
        self.order = order

    def commit(
        self,
        value: bytes,
        blinding: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Create a Pedersen commitment to a value.

        Args:
            value: Value to commit (max 32 bytes)
            blinding: Optional blinding factor (random if not provided)

        Returns:
            Tuple of (commitment, blinding_factor)
        """
        # Convert value to integer
        if len(value) > 32:
            raise ValueError("Value must be at most 32 bytes")
        v = int.from_bytes(value.ljust(32, b'\x00'), 'big') % self.order

        # Generate or use provided blinding factor
        if blinding is None:
            blinding = os.urandom(32)
        r = int.from_bytes(blinding, 'big') % self.order

        # Compute commitment: C = g^v * h^r (mod order)
        # Simplified - in production use proper elliptic curve math
        c = (pow(self.g, v, self.order) * pow(self.h, r, self.order)) % self.order

        commitment = c.to_bytes(32, 'big')
        return commitment, blinding

    def verify(
        self,
        commitment: bytes,
        value: bytes,
        blinding: bytes
    ) -> bool:
        """
        Verify a commitment opening.

        Args:
            commitment: The commitment
            value: Claimed value
            blinding: Blinding factor used

        Returns:
            True if commitment is valid for value and blinding
        """
        try:
            expected_commitment, _ = self.commit(value, blinding)
            return commitment == expected_commitment
        except Exception:
            return False

    def commit_evidence(
        self,
        evidence_hash: bytes,
        context_id: str,
        metadata: Optional[Dict[str, Any]] = None
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
        self,
        proof: CommitmentProof,
        evidence_hash: bytes,
        blinding: bytes
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
        # Verify blinding factor matches
        if keccak(blinding) != proof.blinding_factor_hash:
            return False

        # Verify commitment
        return self.verify(proof.commitment, evidence_hash, blinding)

    @staticmethod
    def hash_evidence(evidence: bytes) -> bytes:
        """
        Hash evidence for commitment.

        Args:
            evidence: Raw evidence data

        Returns:
            32-byte hash
        """
        return keccak(evidence)

    def aggregate_commitments(
        self,
        commitments: List[bytes]
    ) -> bytes:
        """
        Homomorphically aggregate multiple commitments.

        C_agg = C_1 * C_2 * ... * C_n

        Args:
            commitments: List of commitments to aggregate

        Returns:
            Aggregated commitment
        """
        result = 1
        for c in commitments:
            c_int = int.from_bytes(c, 'big')
            result = (result * c_int) % self.order

        return result.to_bytes(32, 'big')


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

    def commit_dispute_evidence(
        self,
        dispute_id: str,
        evidence: bytes
    ) -> CommitmentProof:
        """
        Create a commitment for dispute evidence.

        Args:
            dispute_id: Dispute identifier
            evidence: Raw evidence data

        Returns:
            CommitmentProof for on-chain storage
        """
        evidence_hash = self.pedersen.hash_evidence(evidence)

        proof, blinding = self.pedersen.commit_evidence(
            evidence_hash,
            context_id=dispute_id,
            metadata={"evidence_size": len(evidence)}
        )

        # Store for later revelation
        self._commitments[dispute_id] = proof
        self._blindings[dispute_id] = blinding

        return proof

    def reveal_evidence(
        self,
        dispute_id: str,
        evidence: bytes
    ) -> Tuple[bytes, bytes]:
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

        evidence_hash = self.pedersen.hash_evidence(evidence)
        blinding = self._blindings[dispute_id]

        return evidence_hash, blinding

    def verify_revelation(
        self,
        dispute_id: str,
        evidence: bytes,
        blinding: bytes
    ) -> bool:
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
        evidence_hash = self.pedersen.hash_evidence(evidence)

        return self.pedersen.verify_evidence_commitment(
            proof, evidence_hash, blinding
        )

    def get_commitment_for_chain(self, dispute_id: str) -> bytes:
        """
        Get the commitment bytes for on-chain storage.

        Args:
            dispute_id: Dispute identifier

        Returns:
            32-byte commitment

        Raises:
            ValueError: If no commitment exists
        """
        if dispute_id not in self._commitments:
            raise ValueError(f"No commitment found for dispute {dispute_id}")

        return self._commitments[dispute_id].commitment

    def batch_commit(
        self,
        dispute_id: str,
        evidence_list: List[bytes]
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

        for evidence in evidence_list:
            evidence_hash = self.pedersen.hash_evidence(evidence)
            commitment, blinding = self.pedersen.commit(evidence_hash)
            commitments.append(commitment)
            blindings.append(blinding)

        aggregated = self.pedersen.aggregate_commitments(commitments)

        return aggregated, blindings
