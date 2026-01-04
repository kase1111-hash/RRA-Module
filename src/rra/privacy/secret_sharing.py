# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Shamir's Secret Sharing for Threshold Key Escrow.

Implements (t, n) threshold secret sharing where:
- Secret is split into n shares
- Any t shares can reconstruct the secret
- t-1 or fewer shares reveal nothing about the secret

Used in ComplianceEscrow for decentralized key management:
- No single party can decrypt dispute evidence
- Legal compliance requires council approval (m-of-n)
- Prevents honeypot attacks
"""

import secrets
from typing import List, Tuple
from dataclasses import dataclass


# Prime for finite field operations (256-bit prime close to 2^256)
# Using secp256k1 order for Ethereum compatibility
PRIME = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


@dataclass
class Share:
    """A single share of a split secret."""

    index: int  # x-coordinate (1 to n)
    value: int  # y-coordinate (share value)

    def to_bytes(self) -> bytes:
        """Serialize share to bytes."""
        index_bytes = self.index.to_bytes(1, "big")
        value_bytes = self.value.to_bytes(32, "big")
        return index_bytes + value_bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> "Share":
        """Deserialize share from bytes."""
        index = data[0]
        value = int.from_bytes(data[1:33], "big")
        return cls(index=index, value=value)

    def to_hex(self) -> str:
        """Convert to hex string."""
        return self.to_bytes().hex()

    @classmethod
    def from_hex(cls, hex_str: str) -> "Share":
        """Parse from hex string."""
        return cls.from_bytes(bytes.fromhex(hex_str))


class ShamirSecretSharing:
    """
    Shamir's Secret Sharing over a finite field.

    Uses polynomial interpolation in GF(p) where p is the secp256k1 order.
    """

    def __init__(self, threshold: int, total_shares: int, prime: int = PRIME):
        """
        Initialize secret sharing scheme.

        Args:
            threshold: Minimum shares needed for reconstruction (t)
            total_shares: Total number of shares to generate (n)
            prime: Prime modulus for finite field
        """
        if threshold < 2:
            raise ValueError("Threshold must be at least 2")
        if threshold > total_shares:
            raise ValueError("Threshold cannot exceed total shares")
        if total_shares > 255:
            raise ValueError("Maximum 255 shares supported")

        self.threshold = threshold
        self.total_shares = total_shares
        self.prime = prime

    def split(self, secret: int) -> List[Share]:
        """
        Split a secret into shares.

        Args:
            secret: The secret value to split (must be < prime)

        Returns:
            List of Share objects
        """
        if secret >= self.prime:
            raise ValueError("Secret must be less than prime")

        # Generate random polynomial coefficients
        # f(x) = secret + a1*x + a2*x^2 + ... + a(t-1)*x^(t-1)
        coefficients = [secret]
        for _ in range(self.threshold - 1):
            coefficients.append(secrets.randbelow(self.prime))

        # Evaluate polynomial at points 1, 2, ..., n
        shares = []
        for x in range(1, self.total_shares + 1):
            y = self._evaluate_polynomial(coefficients, x)
            shares.append(Share(index=x, value=y))

        return shares

    def reconstruct(self, shares: List[Share]) -> int:
        """
        Reconstruct secret from shares using Lagrange interpolation.

        SECURITY FIX MED-008: Validates share indices before reconstruction.

        Args:
            shares: At least threshold shares

        Returns:
            The reconstructed secret

        Raises:
            ValueError: If shares are insufficient or have invalid indices
        """
        if len(shares) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} shares, got {len(shares)}")

        # SECURITY FIX MED-008: Validate share indices
        # Index 0 would leak the secret directly (f(0) = secret)
        # Negative or out-of-range indices could cause undefined behavior
        seen_indices = set()
        for share in shares:
            if not (1 <= share.index <= 255):
                raise ValueError(f"Invalid share index {share.index}: must be between 1 and 255")
            # Check for duplicate indices (would cause division by zero in Lagrange)
            if share.index in seen_indices:
                raise ValueError(
                    f"Duplicate share index {share.index}: each share must have unique index"
                )
            seen_indices.add(share.index)

        # Use only threshold shares
        shares = shares[: self.threshold]

        # Lagrange interpolation at x=0
        secret = 0
        for i, share_i in enumerate(shares):
            # Compute Lagrange basis polynomial L_i(0)
            numerator = 1
            denominator = 1

            for j, share_j in enumerate(shares):
                if i != j:
                    numerator = (numerator * (-share_j.index)) % self.prime
                    denominator = (denominator * (share_i.index - share_j.index)) % self.prime

            # Compute L_i(0) = numerator / denominator (mod prime)
            lagrange = (numerator * self._mod_inverse(denominator)) % self.prime

            # Add contribution
            secret = (secret + share_i.value * lagrange) % self.prime

        return secret

    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at point x using Horner's method."""
        result = 0
        for coeff in reversed(coefficients):
            result = (result * x + coeff) % self.prime
        return result

    def _mod_inverse(self, a: int) -> int:
        """Compute modular multiplicative inverse using extended Euclidean algorithm."""
        return pow(a, self.prime - 2, self.prime)

    def verify_share(self, share: Share, commitment: bytes) -> bool:
        """
        Verify a share against a commitment.

        Uses the share commitment scheme where commitments are hashes.

        SECURITY FIX LOW-001: Uses constant-time comparison to prevent
        timing side-channel attacks during share verification.
        """
        import hmac
        from eth_utils import keccak

        expected = keccak(share.to_bytes())
        # SECURITY FIX: Use constant-time comparison
        return hmac.compare_digest(expected, commitment)


def split_secret(secret: bytes, threshold: int, total_shares: int) -> List[Share]:
    """
    Split a secret (bytes) into shares.

    Args:
        secret: Secret bytes (max 32 bytes)
        threshold: Minimum shares for reconstruction
        total_shares: Total shares to generate

    Returns:
        List of Share objects
    """
    if len(secret) > 32:
        raise ValueError("Secret must be at most 32 bytes")

    secret_int = int.from_bytes(secret.ljust(32, b"\x00"), "big")
    sss = ShamirSecretSharing(threshold, total_shares)
    return sss.split(secret_int)


def reconstruct_secret(shares: List[Share], threshold: int) -> bytes:
    """
    Reconstruct a secret from shares.

    Args:
        shares: List of Share objects
        threshold: Original threshold value

    Returns:
        Reconstructed secret bytes
    """
    sss = ShamirSecretSharing(threshold, len(shares))
    secret_int = sss.reconstruct(shares)
    return secret_int.to_bytes(32, "big")


class ThresholdKeyEscrow:
    """
    High-level interface for threshold key escrow.

    Combines Shamir's Secret Sharing with viewing key management.
    """

    def __init__(self, threshold: int = 3, total_shares: int = 5):
        """
        Initialize escrow with threshold parameters.

        Default: 3-of-5 threshold (council majority required)
        """
        self.threshold = threshold
        self.total_shares = total_shares
        self.sss = ShamirSecretSharing(threshold, total_shares)

    def escrow_key(self, viewing_key_private: bytes) -> Tuple[List[Share], List[bytes]]:
        """
        Split viewing key for threshold escrow.

        Args:
            viewing_key_private: 32-byte private viewing key

        Returns:
            Tuple of (shares, commitments)
            - shares: List of Share objects (distribute to shareholders)
            - commitments: List of commitment hashes (store on-chain)
        """
        from eth_utils import keccak

        shares = split_secret(viewing_key_private, self.threshold, self.total_shares)
        commitments = [keccak(share.to_bytes()) for share in shares]

        return shares, commitments

    def recover_key(self, shares: List[Share]) -> bytes:
        """
        Recover viewing key from threshold shares.

        Args:
            shares: At least threshold shares

        Returns:
            Recovered 32-byte private viewing key
        """
        return reconstruct_secret(shares, self.threshold)

    def verify_shares(self, shares: List[Share], commitments: List[bytes]) -> List[bool]:
        """
        Verify shares against their commitments.

        SECURITY FIX LOW-001: Uses constant-time comparison to prevent
        timing side-channel attacks during share verification.

        Args:
            shares: Shares to verify
            commitments: Expected commitment hashes

        Returns:
            List of verification results
        """
        import hmac
        from eth_utils import keccak

        results = []
        for share in shares:
            if share.index - 1 < len(commitments):
                expected = commitments[share.index - 1]
                actual = keccak(share.to_bytes())
                # SECURITY FIX: Use constant-time comparison
                results.append(hmac.compare_digest(actual, expected))
            else:
                results.append(False)

        return results
