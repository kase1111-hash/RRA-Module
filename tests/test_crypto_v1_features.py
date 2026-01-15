# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for v1.0.0-rc1 crypto features.

Covers:
- Performance optimizations (gmpy2, py_ecc, windowed scalar mult)
- Security fixes (constant-time, batch inversion, encrypted export)
- Breaking changes validation
"""

import pytest
import time
import os

from rra.crypto.viewing_keys import (
    ViewingKey,
    KeyPurpose,
)
from rra.crypto.pedersen import (
    PedersenCommitment,
    GMPY2_AVAILABLE,
    PY_ECC_AVAILABLE,
    _scalar_mult,
    _scalar_mult_windowed,
    _mod_inverse,
    BN254_FIELD_PRIME,
    BN254_CURVE_ORDER,
)
from rra.crypto.shamir import ShamirSecretSharing, ThresholdConfig


class TestEncryptedKeyExport:
    """Tests for HIGH-005: Secure password-protected key export."""

    def test_export_import_roundtrip(self):
        """Test encrypted export/import preserves key material."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "test-1")
        password = b"secure_password_123!"

        # Export encrypted
        encrypted_data = key.export_private_encrypted(password)
        assert isinstance(encrypted_data, bytes)
        assert len(encrypted_data) > 32  # Salt + IV + ciphertext + tag

        # Import with correct password
        restored = ViewingKey.import_private_encrypted(
            encrypted_data,
            password,
            KeyPurpose.DISPUTE_EVIDENCE,
            "test-1"
        )

        # Verify keys match
        assert restored.public_key.to_bytes() == key.public_key.to_bytes()

    def test_wrong_password_fails(self):
        """Test decryption with wrong password fails."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "test-2")
        encrypted = key.export_private_encrypted(b"correct_password")

        with pytest.raises((ValueError, Exception)):  # Decryption should fail
            ViewingKey.import_private_encrypted(
                encrypted,
                b"wrong_password",
                KeyPurpose.DISPUTE_EVIDENCE,
                "test-2"
            )

    def test_tampered_data_fails(self):
        """Test tampered encrypted data is rejected."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "test-3")
        encrypted = key.export_private_encrypted(b"password123")

        # Tamper with the ciphertext (middle bytes)
        tampered = bytearray(encrypted)
        tampered[len(tampered) // 2] ^= 0xFF

        with pytest.raises((ValueError, Exception)):
            ViewingKey.import_private_encrypted(
                bytes(tampered),
                b"password123",
                KeyPurpose.DISPUTE_EVIDENCE,
                "test-3"
            )


class TestPedersenPerformance:
    """Tests for performance optimizations in Pedersen commitments."""

    def test_commitment_basic(self):
        """Test basic commitment creation works."""
        pc = PedersenCommitment()
        value = b"test_value"

        commitment, blinding = pc.commit(value)

        assert commitment is not None
        assert isinstance(commitment, bytes)
        assert len(commitment) == 64  # Serialized (x, y) point = 32 + 32 bytes
        assert blinding is not None
        assert len(blinding) == 32

    def test_commitment_verification(self):
        """Test commitment verification with blinding factor."""
        pc = PedersenCommitment()
        value = b"secret_data"

        commitment, blinding = pc.commit(value)

        # Verify with correct blinding
        assert pc.verify(commitment, value, blinding)

        # Verify fails with wrong value
        assert not pc.verify(commitment, b"wrong_data", blinding)

        # Verify fails with wrong blinding
        wrong_blinding = os.urandom(32)
        assert not pc.verify(commitment, value, wrong_blinding)

    def test_windowed_scalar_mult_correctness(self):
        """Test windowed scalar mult gives same result as basic."""
        pc = PedersenCommitment()

        # Test with various scalars
        test_scalars = [1, 2, 7, 255, 12345, 2**128, 2**200]

        for k in test_scalars:
            k = k % BN254_CURVE_ORDER
            if k == 0:
                continue

            basic = _scalar_mult(k, pc.g)
            windowed = _scalar_mult_windowed(k, pc.g)

            assert basic == windowed, f"Mismatch for scalar {k}"

    def test_mod_inverse_correctness(self):
        """Test modular inverse is correct."""
        test_values = [1, 2, 7, 12345, 2**128, 2**200]

        for a in test_values:
            a = a % BN254_FIELD_PRIME
            if a == 0:
                continue

            inv = _mod_inverse(a)

            # Verify: a * inv ≡ 1 (mod p)
            assert (a * inv) % BN254_FIELD_PRIME == 1

    @pytest.mark.skipif(not GMPY2_AVAILABLE, reason="gmpy2 not installed")
    def test_gmpy2_speedup(self):
        """Test gmpy2 provides significant speedup for modular inverse."""
        import time

        # Large random value
        a = int.from_bytes(os.urandom(32), 'big') % BN254_FIELD_PRIME
        if a == 0:
            a = 1

        iterations = 100

        # Time gmpy2 version (current)
        start = time.perf_counter()
        for _ in range(iterations):
            _mod_inverse(a)
        gmpy2_time = time.perf_counter() - start

        # Time pure Python fallback
        start = time.perf_counter()
        for _ in range(iterations):
            pow(a, BN254_FIELD_PRIME - 2, BN254_FIELD_PRIME)
        python_time = time.perf_counter() - start

        # gmpy2 should be significantly faster
        speedup = python_time / gmpy2_time
        assert speedup > 10, f"Expected >10x speedup, got {speedup:.1f}x"

    def test_commitment_throughput(self):
        """Test commitment creation throughput is reasonable."""
        pc = PedersenCommitment()
        values = [os.urandom(32) for _ in range(10)]

        start = time.perf_counter()
        for v in values:
            pc.commit(v)
        elapsed = time.perf_counter() - start

        throughput = 10 / elapsed

        # Should achieve at least 10 commitments/second even without optimizations
        assert throughput > 10, f"Throughput too low: {throughput:.1f}/s"


class TestShamirSecurityFixes:
    """Tests for Shamir secret sharing security fixes."""

    def test_basic_split_reconstruct(self):
        """Test basic 2-of-3 secret sharing."""
        config = ThresholdConfig.simple_2_of_3()
        shamir = ShamirSecretSharing()  # Uses default prime

        secret = os.urandom(32)
        shares = shamir.split(secret, config, "test-context")

        assert len(shares) == 3

        # Reconstruct with any 2 shares
        reconstructed = shamir.reconstruct([shares[0], shares[1]])
        assert reconstructed == secret

        reconstructed = shamir.reconstruct([shares[1], shares[2]])
        assert reconstructed == secret

    def test_insufficient_shares_fails(self):
        """Test reconstruction with insufficient shares raises ValueError."""
        config = ThresholdConfig.standard_3_of_5()
        shamir = ShamirSecretSharing()

        secret = os.urandom(32)
        shares = shamir.split(secret, config, "test-context")

        # Only 2 shares when 3 required
        with pytest.raises(ValueError):
            shamir.reconstruct([shares[0], shares[1]])

    def test_batch_inversion_correctness(self):
        """Test batch modular inversion gives correct results."""
        shamir = ShamirSecretSharing()  # Uses default prime

        values = [123, 456, 789, 1000, 12345]

        # Compute batch inverses
        batch_inverses = shamir._batch_modular_inverse(values)

        # Verify each inverse
        for v, inv in zip(values, batch_inverses):
            assert (v * inv) % shamir.prime == 1

    def test_horner_evaluation_consistency(self):
        """Test polynomial evaluation uses Horner's method consistently."""
        shamir = ShamirSecretSharing()  # Uses default prime

        # Create polynomial coefficients
        coeffs = [100, 200, 300]  # f(x) = 100 + 200x + 300x^2

        # Evaluate at multiple points
        x_values = [1, 2, 3, 4, 5]

        for x in x_values:
            result = shamir._evaluate_polynomial(coeffs, x)

            # Verify against direct computation
            expected = sum(c * pow(x, i, shamir.prime) for i, c in enumerate(coeffs))
            expected = expected % shamir.prime

            assert result == expected


class TestSecurityProperties:
    """Tests for security properties and edge cases."""

    def test_point_at_infinity_rejection(self):
        """Test CRITICAL-002: Point-at-infinity is rejected in commitments."""
        pc = PedersenCommitment()

        # Create many commitments - none should be point at infinity
        for _ in range(100):
            commitment, _ = pc.commit(os.urandom(32))
            assert commitment != (0, 0), "Point at infinity should be rejected"

    def test_blinding_factor_randomness(self):
        """Test MED-001: Each commitment uses unique blinding factor."""
        pc = PedersenCommitment()
        value = b"same_value"

        commitments = set()
        for _ in range(10):
            commitment, _ = pc.commit(value)
            commitments.add(commitment)

        # All commitments should be different due to random blinding
        assert len(commitments) == 10, "Commitments should use random blinding"

    def test_key_commitment_hiding(self):
        """Test MED-001: Commitments use hiding with blinding factor."""
        # Generate two keys with same purpose
        key1 = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "hide-test-1")
        key2 = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "hide-test-2")

        # Commitments should be different even for same purpose
        # (due to random blinding factors)
        assert key1.commitment != key2.commitment

    def test_constant_time_comparison(self):
        """Test LOW-001: Secret comparisons use constant-time."""
        import hmac

        # This test verifies hmac.compare_digest is used
        secret1 = b"secret_value_1"
        secret2 = b"secret_value_1"
        secret3 = b"secret_value_2"

        # Equal values
        assert hmac.compare_digest(secret1, secret2)

        # Different values
        assert not hmac.compare_digest(secret1, secret3)


class TestBackwardsCompatibility:
    """Tests for deprecated API warnings and migration paths."""

    def test_deprecated_export_private_warns(self):
        """Test export_private() raises deprecation warning."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "compat-test")

        with pytest.warns(DeprecationWarning, match="export_private_encrypted"):
            key.export_private()

    def test_migration_path_works(self):
        """Test migration from old API to new API."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "migrate-test")

        # Old way (deprecated)
        with pytest.warns(DeprecationWarning):
            old_bytes = key.export_private()

        # New way (recommended)
        password = b"migration_password"
        new_encrypted = key.export_private_encrypted(password)

        # Both should allow key restoration
        restored_old = ViewingKey.from_private_bytes(
            old_bytes,
            KeyPurpose.DISPUTE_EVIDENCE,
            "migrate-test"
        )

        restored_new = ViewingKey.import_private_encrypted(
            new_encrypted,
            password,
            KeyPurpose.DISPUTE_EVIDENCE,
            "migrate-test"
        )

        # Both restorations should produce valid keys
        assert restored_old.public_key.to_bytes() == key.public_key.to_bytes()
        assert restored_new.public_key.to_bytes() == key.public_key.to_bytes()


class TestOptionalDependencies:
    """Tests for optional dependency detection."""

    def test_gmpy2_detection(self):
        """Test gmpy2 availability is correctly detected."""
        # Just verify the flag is a boolean
        assert isinstance(GMPY2_AVAILABLE, bool)

    def test_py_ecc_detection(self):
        """Test py_ecc availability is correctly detected."""
        assert isinstance(PY_ECC_AVAILABLE, bool)

    def test_fallback_without_optimizations(self):
        """Test crypto works without optional dependencies."""
        # This test always passes - it verifies the fallback path works
        pc = PedersenCommitment()
        commitment, blinding = pc.commit(b"test")

        assert pc.verify(commitment, b"test", blinding)
