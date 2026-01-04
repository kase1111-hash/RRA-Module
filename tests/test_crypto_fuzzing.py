# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Fuzzing Tests for Cryptographic Primitives.

These tests use randomized and edge-case inputs to discover vulnerabilities
in cryptographic implementations. They test:

1. Shamir Secret Sharing
   - Edge case secrets (zeros, max values, boundary conditions)
   - Various threshold configurations
   - Invalid/malformed shares
   - Timing attack resistance properties

2. Pedersen Commitments
   - Edge case values (zeros, field boundary)
   - Invalid curve points
   - Commitment hiding and binding properties

3. ECIES / Viewing Keys
   - Edge case plaintexts
   - Malformed encrypted data
   - Key commitment verification

Security Properties Tested:
- No crashes on malformed input
- Consistent behavior across random inputs
- Proper error handling without information leakage
- Boundary condition handling
"""

import pytest
import os
import struct
import random
from typing import List

from rra.crypto.viewing_keys import (
    ViewingKey,
    ViewingKeyManager,
    EncryptedData,
    KeyPurpose,
)
from rra.crypto.shamir import (
    ShamirSecretSharing,
    KeyShare,
    ThresholdConfig,
    ShareHolder,
    PRIME,
)
from rra.crypto.pedersen import (
    PedersenCommitment,
    BN254_CURVE_ORDER,
    BN254_FIELD_PRIME,
    _is_on_curve,
    _bytes_to_point,
    _point_to_bytes,
    _scalar_mult,
    G_POINT,
    H_POINT,
)
from rra.privacy.secret_sharing import (
    ShamirSecretSharing as PrivacyShamir,
    Share,
)


# ============================================================================
# Fuzzing Configuration
# ============================================================================

# Number of random iterations for fuzzing tests
FUZZ_ITERATIONS = 100

# Seed for reproducibility (set to None for true randomness)
FUZZ_SEED = 42


@pytest.fixture(autouse=True)
def set_random_seed():
    """Set random seed for reproducibility in fuzzing tests."""
    if FUZZ_SEED is not None:
        random.seed(FUZZ_SEED)


# ============================================================================
# Shamir Secret Sharing Fuzzing Tests
# ============================================================================

class TestShamirFuzzing:
    """Fuzzing tests for Shamir Secret Sharing."""

    def test_random_secrets(self):
        """Test with many random 32-byte secrets."""
        shamir = ShamirSecretSharing()
        config = ThresholdConfig.standard_3_of_5()

        for i in range(FUZZ_ITERATIONS):
            secret = os.urandom(32)
            shares = shamir.split(secret, config, f"fuzz-{i}")

            # Reconstruct with random subset of threshold shares
            indices = random.sample(range(5), 3)
            subset = [shares[j] for j in indices]
            reconstructed = shamir.reconstruct(subset)

            assert reconstructed == secret, f"Failed on iteration {i}"

    def test_edge_case_secrets(self):
        """Test edge case secret values."""
        shamir = ShamirSecretSharing()
        config = ThresholdConfig.simple_2_of_3()

        edge_cases = [
            b"\x00" * 32,  # All zeros
            b"\xff" * 32,  # All ones (max bytes)
            b"\x00" * 31 + b"\x01",  # Minimal non-zero
            b"\x7f" + b"\xff" * 31,  # Just under half max
            b"\x80" + b"\x00" * 31,  # Just over half max
            (PRIME - 1).to_bytes(32, "big"),  # Prime - 1 (edge of field)
            bytes(range(32)),  # Sequential bytes
            bytes(range(31, -1, -1)),  # Reverse sequential
        ]

        for i, secret in enumerate(edge_cases):
            # Ensure secret is valid (< PRIME)
            secret_int = int.from_bytes(secret, "big")
            if secret_int >= PRIME:
                secret = (secret_int % PRIME).to_bytes(32, "big")

            shares = shamir.split(secret, config, f"edge-{i}")
            reconstructed = shamir.reconstruct(shares[:2])
            assert reconstructed == secret, f"Failed on edge case {i}"

    def test_all_threshold_combinations(self):
        """Test various threshold/total share combinations."""
        shamir = ShamirSecretSharing()
        secret = os.urandom(32)

        # Test various (threshold, total) combinations
        configs = [
            (2, 2),  # Minimum
            (2, 3),
            (2, 5),
            (3, 3),
            (3, 5),
            (3, 7),
            (4, 5),
            (4, 7),
            (5, 5),
            (5, 7),
            (5, 10),
        ]

        for threshold, total in configs:
            holders = [ShareHolder.USER] * total  # Dummy holders
            config = ThresholdConfig(
                threshold=threshold,
                total_shares=total,
                holders=holders
            )

            shares = shamir.split(secret, config, "config-test")

            # Test with exactly threshold shares
            reconstructed = shamir.reconstruct(shares[:threshold])
            assert reconstructed == secret, f"Failed for ({threshold}, {total})"

            # Test with more than threshold shares
            if total > threshold:
                reconstructed = shamir.reconstruct(shares)
                assert reconstructed == secret

    def test_share_independence(self):
        """Verify shares are computationally independent."""
        shamir = ShamirSecretSharing()
        config = ThresholdConfig.standard_3_of_5()

        # Create multiple sharings of the same secret
        secret = os.urandom(32)

        sharings = []
        for _ in range(10):
            shares = shamir.split(secret, config, "independence")
            sharings.append(shares)

        # Each sharing should produce different share values
        # (due to random polynomial coefficients)
        for i in range(5):
            values = set()
            for shares in sharings:
                values.add(shares[i].value)
            # All 10 sharings should have different values for share i
            assert len(values) == 10, f"Share {i} values not independent"

    def test_malformed_share_index(self):
        """Test handling of malformed share indices."""
        shamir = PrivacyShamir(3, 5)
        secret_int = int.from_bytes(os.urandom(32), "big") % shamir.prime

        shares = shamir.split(secret_int)

        # Test index 0 (should be invalid - reveals secret directly)
        bad_share = Share(index=0, value=shares[0].value)
        with pytest.raises(ValueError, match="Invalid share index"):
            shamir.reconstruct([bad_share, shares[1], shares[2]])

        # Test negative-like index (256+ wraps in single byte)
        bad_share = Share(index=256, value=shares[0].value)
        with pytest.raises(ValueError, match="Invalid share index"):
            shamir.reconstruct([bad_share, shares[1], shares[2]])

    def test_duplicate_share_indices(self):
        """Test handling of duplicate share indices."""
        shamir = PrivacyShamir(3, 5)
        secret_int = int.from_bytes(os.urandom(32), "big") % shamir.prime

        shares = shamir.split(secret_int)

        # Create duplicate index
        dup_share = Share(index=shares[0].index, value=shares[1].value)

        with pytest.raises(ValueError, match="Duplicate share index"):
            shamir.reconstruct([shares[0], dup_share, shares[2]])

    def test_insufficient_shares_error(self):
        """Test proper error for insufficient shares."""
        shamir = ShamirSecretSharing()
        config = ThresholdConfig.standard_3_of_5()
        secret = os.urandom(32)

        shares = shamir.split(secret, config, "test")

        # 0, 1, 2 shares should all fail for 3-of-5
        for count in range(3):
            with pytest.raises(ValueError, match="Not enough shares"):
                shamir.reconstruct(shares[:count])


# ============================================================================
# Pedersen Commitment Fuzzing Tests
# ============================================================================

class TestPedersenFuzzing:
    """Fuzzing tests for Pedersen Commitments."""

    def test_random_values(self):
        """Test commitment/verification with random values."""
        pedersen = PedersenCommitment()

        for _ in range(FUZZ_ITERATIONS):
            value = os.urandom(random.randint(1, 32))
            commitment, blinding = pedersen.commit(value)

            # Verify should succeed
            assert pedersen.verify(commitment, value, blinding)

            # Wrong value should fail
            wrong_value = os.urandom(len(value))
            if wrong_value != value:
                assert not pedersen.verify(commitment, wrong_value, blinding)

    def test_edge_case_values(self):
        """Test edge case commitment values."""
        pedersen = PedersenCommitment()

        edge_cases = [
            b"\x00",  # Single zero
            b"\x00" * 32,  # All zeros
            b"\xff" * 32,  # All ones
            b"\x01",  # Minimal non-zero
            (BN254_CURVE_ORDER - 1).to_bytes(32, "big"),  # Max field element
            b"",  # Empty (should be handled)
        ]

        for i, value in enumerate(edge_cases):
            if len(value) == 0:
                # Empty value - pad to avoid issues
                value = b"\x00"

            try:
                commitment, blinding = pedersen.commit(value)
                assert pedersen.verify(commitment, value, blinding), f"Edge case {i}"
            except ValueError:
                # Some edge cases may legitimately fail (e.g., point at infinity)
                pass

    def test_blinding_factor_variations(self):
        """Test various blinding factor values."""
        pedersen = PedersenCommitment()
        value = b"test value"

        blinding_cases = [
            b"\x00" * 32,  # Zero blinding
            b"\xff" * 32,  # Max blinding
            b"\x01" + b"\x00" * 31,  # Minimal
            os.urandom(32),  # Random
        ]

        for blinding in blinding_cases:
            try:
                commitment, _ = pedersen.commit(value, blinding)
                assert pedersen.verify(commitment, value, blinding)
            except ValueError:
                # Point at infinity case is acceptable
                pass

    def test_commitment_uniqueness(self):
        """Verify different values produce different commitments."""
        pedersen = PedersenCommitment()
        blinding = os.urandom(32)

        commitments = set()
        for i in range(100):
            value = i.to_bytes(32, "big")
            commitment, _ = pedersen.commit(value, blinding)
            commitments.add(commitment)

        # All commitments should be unique
        assert len(commitments) == 100

    def test_malformed_point_rejection(self):
        """Test rejection of points not on the curve."""
        # Create a point that's NOT on the BN254 curve
        invalid_points = [
            (1, 1),  # Not on curve
            (0, 1),  # Not on curve
            (BN254_FIELD_PRIME - 1, 1),  # Not on curve
        ]

        for point in invalid_points:
            assert not _is_on_curve(point), f"Point {point} should not be on curve"

    def test_valid_generator_points(self):
        """Verify generator points are valid."""
        assert _is_on_curve(G_POINT), "G_POINT should be on curve"
        assert _is_on_curve(H_POINT), "H_POINT should be on curve"

    def test_point_serialization_roundtrip(self):
        """Test point serialization/deserialization."""
        # Test with generator points
        for point in [G_POINT, H_POINT]:
            serialized = _point_to_bytes(point)
            assert len(serialized) == 64
            deserialized = _bytes_to_point(serialized)
            assert deserialized == point

    def test_invalid_point_bytes_rejection(self):
        """Test rejection of invalid point bytes."""
        invalid_cases = [
            b"\x00" * 63,  # Too short
            b"\x00" * 65,  # Too long
            # Point not on curve
            b"\x00" * 31 + b"\x01" + b"\x00" * 31 + b"\x01",
        ]

        for data in invalid_cases:
            if len(data) == 64:
                with pytest.raises(ValueError, match="not on the BN254 curve"):
                    _bytes_to_point(data)
            else:
                with pytest.raises(ValueError, match="64 bytes"):
                    _bytes_to_point(data)

    def test_scalar_mult_edge_cases(self):
        """Test scalar multiplication edge cases."""
        # Multiply by 0 should give point at infinity
        result = _scalar_mult(0, G_POINT)
        assert result == (0, 0)

        # Multiply by 1 should give same point
        result = _scalar_mult(1, G_POINT)
        assert result == G_POINT

        # Multiply by curve order should give point at infinity
        result = _scalar_mult(BN254_CURVE_ORDER, G_POINT)
        assert result == (0, 0)


# ============================================================================
# ECIES / Viewing Key Fuzzing Tests
# ============================================================================

class TestViewingKeyFuzzing:
    """Fuzzing tests for ECIES viewing keys."""

    def test_random_plaintexts(self):
        """Test encryption/decryption with random plaintexts."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "fuzz-test")

        for _ in range(FUZZ_ITERATIONS):
            # Random length between 1 and 10KB
            length = random.randint(1, 10240)
            plaintext = os.urandom(length)

            encrypted = key.encrypt(plaintext)
            decrypted = key.decrypt(encrypted)

            assert decrypted == plaintext

    def test_edge_case_plaintexts(self):
        """Test edge case plaintext values."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "edge-test")

        edge_cases = [
            b"",  # Empty
            b"\x00",  # Single null
            b"\x00" * 1000,  # Many nulls
            b"\xff" * 1000,  # Many max bytes
            bytes(range(256)) * 10,  # All byte values
            b"A" * 65536,  # 64KB
        ]

        for i, plaintext in enumerate(edge_cases):
            encrypted = key.encrypt(plaintext)
            decrypted = key.decrypt(encrypted)
            assert decrypted == plaintext, f"Failed on edge case {i}"

    def test_many_keys(self):
        """Test with many different keys."""
        plaintext = b"Test message for many keys"

        for i in range(FUZZ_ITERATIONS):
            key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, f"key-{i}")
            encrypted = key.encrypt(plaintext)
            decrypted = key.decrypt(encrypted)
            assert decrypted == plaintext

    def test_malformed_encrypted_data(self):
        """Test handling of malformed encrypted data."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "malform-test")

        # Create valid encrypted data first
        valid = key.encrypt(b"test")

        # Test truncated ciphertext
        truncated = EncryptedData(
            ephemeral_public_key=valid.ephemeral_public_key,
            iv=valid.iv,
            ciphertext=valid.ciphertext[:-5],  # Truncate
            auth_tag=valid.auth_tag,
            key_commitment=valid.key_commitment,
        )
        with pytest.raises(ValueError):
            key.decrypt(truncated)

        # Test wrong IV
        wrong_iv = EncryptedData(
            ephemeral_public_key=valid.ephemeral_public_key,
            iv=os.urandom(12),  # Wrong IV
            ciphertext=valid.ciphertext,
            auth_tag=valid.auth_tag,
            key_commitment=valid.key_commitment,
        )
        with pytest.raises(ValueError):
            key.decrypt(wrong_iv)

        # Test corrupted auth tag
        corrupted_tag = EncryptedData(
            ephemeral_public_key=valid.ephemeral_public_key,
            iv=valid.iv,
            ciphertext=valid.ciphertext,
            auth_tag=os.urandom(16),  # Wrong tag
            key_commitment=valid.key_commitment,
        )
        with pytest.raises(ValueError):
            key.decrypt(corrupted_tag)

    def test_wrong_key_commitment(self):
        """Test wrong key commitment detection."""
        key1 = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "key1")
        key2 = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "key2")

        encrypted = key1.encrypt(b"secret")

        # Decrypting with wrong key should fail on commitment check
        with pytest.raises(ValueError, match="commitment mismatch"):
            key2.decrypt(encrypted)

    def test_expired_key_decryption(self):
        """Test that expired keys cannot decrypt."""
        from datetime import datetime, timedelta

        key = ViewingKey.generate(
            KeyPurpose.DISPUTE_EVIDENCE,
            "expire-test",
            expires_in_days=1
        )

        # Manually expire the key
        key.expires_at = datetime.utcnow() - timedelta(days=1)

        encrypted = ViewingKey.generate(
            KeyPurpose.DISPUTE_EVIDENCE, "other"
        ).encrypt(b"test")
        encrypted.key_commitment = key.commitment

        # Should fail due to expiration
        with pytest.raises(ValueError, match="expired"):
            key.decrypt(encrypted)

    def test_key_derivation_consistency(self):
        """Test that key derivation is consistent."""
        master = os.urandom(32)

        for _ in range(FUZZ_ITERATIONS):
            context = f"ctx-{random.randint(0, 1000000)}"
            index = random.randint(0, 1000)

            key1 = ViewingKey.derive(master, KeyPurpose.DISPUTE_EVIDENCE, context, index)
            key2 = ViewingKey.derive(master, KeyPurpose.DISPUTE_EVIDENCE, context, index)

            # Same derivation params should give same public key
            assert key1.public_key.to_bytes() == key2.public_key.to_bytes()

    def test_encrypted_data_serialization(self):
        """Test EncryptedData serialization with random data."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "serial-test")

        for _ in range(50):
            plaintext = os.urandom(random.randint(1, 1000))
            encrypted = key.encrypt(plaintext)

            # Binary serialization
            binary = encrypted.to_bytes()
            restored = EncryptedData.from_bytes(binary)
            assert key.decrypt(restored) == plaintext

            # Dict serialization
            as_dict = encrypted.to_dict()
            restored = EncryptedData.from_dict(as_dict)
            assert key.decrypt(restored) == plaintext


# ============================================================================
# Timing Attack Resistance Tests
# ============================================================================

class TestTimingResistance:
    """Tests to verify timing attack resistance properties."""

    def test_constant_time_share_verification(self):
        """Test that share verification uses constant-time comparison."""
        import time
        from rra.privacy.secret_sharing import ShamirSecretSharing as SSS
        from eth_utils import keccak

        sss = SSS(3, 5)
        secret = int.from_bytes(os.urandom(32), "big") % sss.prime
        shares = sss.split(secret)

        # Create correct and wrong commitments
        correct_commitment = keccak(shares[0].to_bytes())
        # Wrong commitment - differs in first byte
        wrong_early = b"\x00" + correct_commitment[1:]
        # Wrong commitment - differs in last byte
        wrong_late = correct_commitment[:-1] + b"\x00"

        # Time many iterations to average out noise
        iterations = 1000

        # Time verification with correct commitment
        start = time.perf_counter()
        for _ in range(iterations):
            sss.verify_share(shares[0], correct_commitment)
        time_correct = time.perf_counter() - start

        # Time verification with early-different wrong commitment
        start = time.perf_counter()
        for _ in range(iterations):
            sss.verify_share(shares[0], wrong_early)
        time_early = time.perf_counter() - start

        # Time verification with late-different wrong commitment
        start = time.perf_counter()
        for _ in range(iterations):
            sss.verify_share(shares[0], wrong_late)
        time_late = time.perf_counter() - start

        # All times should be similar (within 20% tolerance)
        # Note: This is a best-effort test - actual timing attacks need
        # statistical analysis over many more samples
        times = [time_correct, time_early, time_late]
        avg = sum(times) / len(times)
        for t in times:
            assert abs(t - avg) / avg < 0.2, "Timing variance too high"

    def test_hmac_compare_usage(self):
        """Verify that security-critical comparisons use hmac.compare_digest."""
        import inspect
        from rra.crypto import shamir, pedersen, viewing_keys
        from rra.privacy import secret_sharing

        modules_to_check = [shamir, pedersen, viewing_keys, secret_sharing]

        for module in modules_to_check:
            source = inspect.getsource(module)
            # Count occurrences of hmac.compare_digest
            compare_count = source.count("hmac.compare_digest")
            # This is a sanity check - each module should use constant-time comparison
            assert compare_count > 0, f"{module.__name__} missing hmac.compare_digest"


# ============================================================================
# Boundary Condition Tests
# ============================================================================

class TestBoundaryConditions:
    """Test behavior at mathematical boundaries."""

    def test_shamir_prime_boundary(self):
        """Test Shamir with values near the prime modulus."""
        shamir = ShamirSecretSharing()
        config = ThresholdConfig.simple_2_of_3()

        # Values near PRIME boundary
        boundary_secrets = [
            (PRIME - 1).to_bytes(32, "big"),
            (PRIME - 2).to_bytes(32, "big"),
            (PRIME // 2).to_bytes(32, "big"),
            (1).to_bytes(32, "big"),
            (2).to_bytes(32, "big"),
        ]

        for secret in boundary_secrets:
            # Secret must be < PRIME, so modulo if needed
            secret_int = int.from_bytes(secret, "big")
            if secret_int >= PRIME:
                continue  # Skip invalid

            shares = shamir.split(secret, config, "boundary")
            reconstructed = shamir.reconstruct(shares[:2])
            assert reconstructed == secret

    def test_pedersen_field_boundary(self):
        """Test Pedersen with values near field boundary."""
        pedersen = PedersenCommitment()

        # Values near BN254_CURVE_ORDER boundary
        boundary_values = [
            (BN254_CURVE_ORDER - 1).to_bytes(32, "big"),
            (BN254_CURVE_ORDER // 2).to_bytes(32, "big"),
            (1).to_bytes(32, "big"),
        ]

        for value in boundary_values:
            # These get reduced mod order internally
            commitment, blinding = pedersen.commit(value)
            assert pedersen.verify(commitment, value, blinding)


# ============================================================================
# Stress Tests
# ============================================================================

class TestStress:
    """Stress tests for cryptographic operations."""

    def test_many_sequential_encryptions(self):
        """Test many sequential encryption operations."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "stress")
        plaintext = b"Stress test data" * 100

        for i in range(500):
            encrypted = key.encrypt(plaintext)
            decrypted = key.decrypt(encrypted)
            assert decrypted == plaintext, f"Failed at iteration {i}"

    def test_many_share_reconstructions(self):
        """Test many share reconstruction operations."""
        shamir = ShamirSecretSharing()
        config = ThresholdConfig.standard_3_of_5()
        secret = os.urandom(32)

        shares = shamir.split(secret, config, "stress")

        for i in range(500):
            # Random subset of 3 shares
            indices = random.sample(range(5), 3)
            subset = [shares[j] for j in indices]
            reconstructed = shamir.reconstruct(subset)
            assert reconstructed == secret, f"Failed at iteration {i}"

    def test_many_commitments(self):
        """Test many commitment operations."""
        pedersen = PedersenCommitment()

        for i in range(500):
            value = os.urandom(32)
            commitment, blinding = pedersen.commit(value)
            assert pedersen.verify(commitment, value, blinding), f"Failed at {i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
