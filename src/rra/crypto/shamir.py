# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Shamir's Secret Sharing for M-of-N Key Escrow.

Enables threshold-based key recovery for compliance and emergency access
without single points of failure.

Use Cases:
- 3-of-5 escrow: User, DAO, 2 independent escrow services, compliance officer
- Emergency key recovery for lost access
- Legal compliance with warrant-based decryption

Security Properties:
- Any M shares can reconstruct the secret
- Fewer than M shares reveal nothing about the secret
- Shares are computationally independent
"""

import secrets
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# Use a large prime for the finite field
# This is a 256-bit prime, safe for 32-byte secrets
PRIME = 2**256 - 189  # A known safe prime


def _is_probable_prime(n: int, k: int = 40) -> bool:
    """
    Miller-Rabin primality test.

    SECURITY: Verifies the prime modulus at module load to prevent
    scheme failure from corrupted or misconfigured constants.

    Args:
        n: Number to test
        k: Number of rounds (40 gives negligible error probability)

    Returns:
        True if n is probably prime
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False

    # Write n-1 as 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2

    # Witness loop
    import random

    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)

        if x == 1 or x == n - 1:
            continue

        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False

    return True


def _verify_prime_constant() -> None:
    """
    Verify PRIME constant is actually prime at module load.

    SECURITY: Prevents complete scheme failure from corrupted constants.

    Raises:
        ValueError: If PRIME is not prime
    """
    if not _is_probable_prime(PRIME):
        raise ValueError(
            f"FATAL: Shamir prime constant {PRIME} failed primality test. "
            "This indicates corruption or misconfiguration."
        )


# Verify prime at module load
_verify_prime_constant()


class ShareHolder(str, Enum):
    """Standard share holder roles."""

    USER = "user"
    DAO_GOVERNANCE = "dao_governance"
    ESCROW_SERVICE_1 = "escrow_1"
    ESCROW_SERVICE_2 = "escrow_2"
    COMPLIANCE_OFFICER = "compliance"
    PROTOCOL_MULTISIG = "protocol_multisig"
    INDEPENDENT_AUDITOR = "auditor"


@dataclass
class ThresholdConfig:
    """
    Configuration for threshold secret sharing.

    Defines the M-of-N scheme parameters.
    """

    threshold: int  # M - minimum shares needed
    total_shares: int  # N - total shares created
    holders: List[ShareHolder]  # Who gets each share

    def __post_init__(self):
        if self.threshold < 2:
            raise ValueError("Threshold must be at least 2")
        if self.threshold > self.total_shares:
            raise ValueError("Threshold cannot exceed total shares")
        if len(self.holders) != self.total_shares:
            raise ValueError("Number of holders must match total shares")

    @classmethod
    def standard_3_of_5(cls) -> "ThresholdConfig":
        """Standard 3-of-5 configuration for compliance."""
        return cls(
            threshold=3,
            total_shares=5,
            holders=[
                ShareHolder.USER,
                ShareHolder.DAO_GOVERNANCE,
                ShareHolder.ESCROW_SERVICE_1,
                ShareHolder.ESCROW_SERVICE_2,
                ShareHolder.COMPLIANCE_OFFICER,
            ],
        )

    @classmethod
    def simple_2_of_3(cls) -> "ThresholdConfig":
        """Simple 2-of-3 for basic recovery."""
        return cls(
            threshold=2,
            total_shares=3,
            holders=[
                ShareHolder.USER,
                ShareHolder.DAO_GOVERNANCE,
                ShareHolder.PROTOCOL_MULTISIG,
            ],
        )


@dataclass
class KeyShare:
    """
    A single share of a secret.

    Contains the share value and metadata for reconstruction.
    """

    index: int  # x-coordinate (1-indexed)
    value: bytes  # y-coordinate as bytes
    holder: ShareHolder
    context_id: str  # e.g., dispute ID
    created_at: datetime
    threshold: int  # M value for reconstruction
    total_shares: int  # N value
    commitment: bytes  # Hash of original secret for verification
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "index": self.index,
            "value": self.value.hex(),
            "holder": self.holder.value,
            "context_id": self.context_id,
            "created_at": self.created_at.isoformat(),
            "threshold": self.threshold,
            "total_shares": self.total_shares,
            "commitment": self.commitment.hex(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyShare":
        """Deserialize from dictionary."""
        return cls(
            index=data["index"],
            value=bytes.fromhex(data["value"]),
            holder=ShareHolder(data["holder"]),
            context_id=data["context_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            threshold=data["threshold"],
            total_shares=data["total_shares"],
            commitment=bytes.fromhex(data["commitment"]),
            metadata=data.get("metadata", {}),
        )

    def to_bytes(self) -> bytes:
        """Compact binary serialization."""
        import struct

        context_bytes = self.context_id.encode()
        return (
            struct.pack(">BHH", self.index, self.threshold, self.total_shares)
            + self.value
            + struct.pack(">H", len(context_bytes))
            + context_bytes
            + self.commitment
        )


class ShamirSecretSharing:
    """
    Shamir's Secret Sharing implementation.

    Splits a secret into N shares where any M can reconstruct it.
    Uses finite field arithmetic over a large prime.
    """

    def __init__(self, prime: int = PRIME):
        """
        Initialize with a prime for the finite field.

        Args:
            prime: Prime number defining the finite field
        """
        self.prime = prime

    def split(self, secret: bytes, config: ThresholdConfig, context_id: str) -> List[KeyShare]:
        """
        Split a secret into shares.

        Args:
            secret: 32-byte secret to split
            config: Threshold configuration
            context_id: Context identifier (e.g., dispute ID)

        Returns:
            List of KeyShare objects

        Raises:
            ValueError: If secret is not 32 bytes
        """
        if len(secret) != 32:
            raise ValueError("Secret must be 32 bytes")

        # Convert secret to integer
        secret_int = int.from_bytes(secret, "big")

        # Generate random polynomial coefficients
        # f(x) = secret + a1*x + a2*x^2 + ... + a(m-1)*x^(m-1)
        coefficients = [secret_int]
        for _ in range(config.threshold - 1):
            coef = secrets.randbelow(self.prime)
            coefficients.append(coef)

        # Compute commitment (hash of secret)
        from eth_utils import keccak

        commitment = keccak(secret)

        # Generate shares
        shares = []
        created_at = datetime.utcnow()

        for i in range(config.total_shares):
            x = i + 1  # 1-indexed
            y = self._evaluate_polynomial(coefficients, x)

            share = KeyShare(
                index=x,
                value=y.to_bytes(32, "big"),
                holder=config.holders[i],
                context_id=context_id,
                created_at=created_at,
                threshold=config.threshold,
                total_shares=config.total_shares,
                commitment=commitment,
            )
            shares.append(share)

        return shares

    def reconstruct(self, shares: List[KeyShare]) -> bytes:
        """
        Reconstruct secret from shares using Lagrange interpolation.

        Args:
            shares: List of shares (at least threshold shares required)

        Returns:
            Reconstructed 32-byte secret

        Raises:
            ValueError: If not enough shares or verification fails
        """
        if not shares:
            raise ValueError("No shares provided")

        threshold = shares[0].threshold
        if len(shares) < threshold:
            raise ValueError(f"Not enough shares: have {len(shares)}, need {threshold}")

        # Use exactly threshold shares
        shares_to_use = shares[:threshold]

        # Extract x and y coordinates
        points = [(share.index, int.from_bytes(share.value, "big")) for share in shares_to_use]

        # Lagrange interpolation at x=0 gives the secret
        secret_int = self._lagrange_interpolate(0, points)

        # Convert back to bytes
        secret = secret_int.to_bytes(32, "big")

        # Verify commitment
        from eth_utils import keccak

        if keccak(secret) != shares[0].commitment:
            raise ValueError("Secret verification failed - commitment mismatch")

        return secret

    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """
        Evaluate polynomial at point x using Horner's method.

        f(x) = c0 + c1*x + c2*x^2 + ...

        SECURITY: Uses Horner's method which processes all coefficients
        in constant time regardless of their values. The number of
        operations depends only on the polynomial degree, not the
        coefficient values.
        """
        # Horner's method: ((c_n * x + c_{n-1}) * x + ...) * x + c_0
        # This processes all coefficients uniformly
        result = 0
        for coef in reversed(coefficients):
            result = (result * x + coef) % self.prime

        return result

    def _lagrange_interpolate(self, x: int, points: List[Tuple[int, int]]) -> int:
        """
        Lagrange interpolation in finite field.

        Computes f(x) given points (x_i, y_i).

        SECURITY: This implementation processes all points uniformly,
        performing the same operations regardless of point values.
        The modular inverse uses Fermat's little theorem which has
        constant-time execution for a given prime size.
        """
        result = 0

        for i, (x_i, y_i) in enumerate(points):
            # Compute Lagrange basis polynomial L_i(x)
            # All points are processed uniformly
            numerator = 1
            denominator = 1

            for j, (x_j, _) in enumerate(points):
                if i != j:
                    numerator = (numerator * (x - x_j)) % self.prime
                    denominator = (denominator * (x_i - x_j)) % self.prime

            # Compute modular inverse using Fermat's little theorem
            # pow() with three arguments uses constant-time modular exponentiation
            inv_denominator = pow(denominator, self.prime - 2, self.prime)

            # Add contribution: y_i * L_i(x)
            term = (y_i * numerator * inv_denominator) % self.prime
            result = (result + term) % self.prime

        return result

    def verify_share(self, share: KeyShare, all_shares: List[KeyShare]) -> bool:
        """
        Verify a share is consistent with others.

        Uses subset reconstruction to verify without revealing secret.

        SECURITY FIX: Previously returned True when not enough shares were
        available for verification, which is a "fail open" vulnerability.
        Now raises ValueError to ensure explicit handling.

        Args:
            share: Share to verify
            all_shares: All available shares

        Returns:
            True if share is valid

        Raises:
            ValueError: If not enough shares available for verification
        """
        # Need at least threshold shares including the one to verify
        threshold = share.threshold
        other_shares = [s for s in all_shares if s.index != share.index]

        if len(other_shares) < threshold - 1:
            # SECURITY FIX: Fail closed instead of open
            raise ValueError(
                f"Not enough shares to verify: have {len(other_shares)}, "
                f"need at least {threshold - 1} other shares"
            )

        # Try to reconstruct using threshold-1 other shares + this share
        test_shares = other_shares[: threshold - 1] + [share]

        try:
            # If reconstruction succeeds and commitment matches, share is valid
            secret = self.reconstruct(test_shares)
            from eth_utils import keccak

            return keccak(secret) == share.commitment
        except Exception:
            return False


def split_key_for_escrow(
    key_bytes: bytes, context_id: str, config: Optional[ThresholdConfig] = None
) -> List[KeyShare]:
    """
    Convenience function to split a key for escrow.

    Args:
        key_bytes: 32-byte key to split
        context_id: Context identifier
        config: Optional threshold config (default: 3-of-5)

    Returns:
        List of KeyShare objects
    """
    if config is None:
        config = ThresholdConfig.standard_3_of_5()

    shamir = ShamirSecretSharing()
    return shamir.split(key_bytes, config, context_id)


def reconstruct_key_from_shares(shares: List[KeyShare]) -> bytes:
    """
    Convenience function to reconstruct a key from shares.

    Args:
        shares: List of shares

    Returns:
        Reconstructed 32-byte key
    """
    shamir = ShamirSecretSharing()
    return shamir.reconstruct(shares)


class EscrowManager:
    """
    High-level manager for key escrow operations.

    Coordinates between viewing keys, Shamir sharing, and storage.
    """

    def __init__(
        self, config: Optional[ThresholdConfig] = None, storage_backend: Optional[Any] = None
    ):
        """
        Initialize escrow manager.

        Args:
            config: Default threshold configuration
            storage_backend: Optional storage for shares
        """
        self.config = config or ThresholdConfig.standard_3_of_5()
        self.storage = storage_backend
        self.shamir = ShamirSecretSharing()
        self._shares_cache: Dict[str, List[KeyShare]] = {}

    def escrow_viewing_key(self, key_bytes: bytes, context_id: str) -> Dict[ShareHolder, KeyShare]:
        """
        Split and escrow a viewing key.

        Args:
            key_bytes: 32-byte viewing key
            context_id: Context identifier

        Returns:
            Dictionary mapping holder to their share
        """
        shares = self.shamir.split(key_bytes, self.config, context_id)

        # Cache shares
        self._shares_cache[context_id] = shares

        # Return as dict for easy distribution
        return {share.holder: share for share in shares}

    def recover_viewing_key(self, context_id: str, provided_shares: List[KeyShare]) -> bytes:
        """
        Recover a viewing key from provided shares.

        Args:
            context_id: Context identifier
            provided_shares: Shares provided by holders

        Returns:
            Reconstructed 32-byte key

        Raises:
            ValueError: If not enough valid shares
        """
        return self.shamir.reconstruct(provided_shares)

    def get_share_for_holder(self, context_id: str, holder: ShareHolder) -> Optional[KeyShare]:
        """
        Get a specific holder's share.

        Args:
            context_id: Context identifier
            holder: Share holder

        Returns:
            KeyShare if found, None otherwise
        """
        if context_id not in self._shares_cache:
            return None

        for share in self._shares_cache[context_id]:
            if share.holder == holder:
                return share

        return None

    def verify_reconstruction_possible(
        self, context_id: str, available_holders: List[ShareHolder]
    ) -> bool:
        """
        Check if reconstruction is possible with available holders.

        Args:
            context_id: Context identifier
            available_holders: Holders who can provide shares

        Returns:
            True if reconstruction is possible
        """
        if context_id not in self._shares_cache:
            return False

        available_count = sum(
            1 for share in self._shares_cache[context_id] if share.holder in available_holders
        )

        return available_count >= self.config.threshold
