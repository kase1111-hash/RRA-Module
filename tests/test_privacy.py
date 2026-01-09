# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Privacy and Zero-Knowledge Infrastructure.
"""

import pytest
import os
from pathlib import Path
from tempfile import TemporaryDirectory


class TestViewingKeys:
    """Tests for viewing key infrastructure."""

    def test_generate_viewing_key(self):
        """Test viewing key generation."""
        from rra.privacy import generate_viewing_key

        key = generate_viewing_key()

        assert key.private_key is not None
        assert len(key.private_key) == 32
        assert key.public_key is not None
        assert len(key.public_key) == 65  # Uncompressed secp256k1
        assert key.commitment is not None
        assert len(key.commitment) == 32
        assert key.blinding_factor is not None
        assert len(key.blinding_factor) == 32

    def test_ecies_encryption_decryption(self):
        """Test ECIES encrypt/decrypt round trip."""
        from rra.privacy.viewing_keys import ECIESCipher

        cipher = ECIESCipher()

        # Generate key pair
        private_key, public_key = cipher.generate_key_pair()

        # Encrypt
        plaintext = b"Hello, ILRM dispute evidence!"
        encrypted = cipher.encrypt(plaintext, public_key)

        assert encrypted.ciphertext != plaintext
        assert encrypted.ephemeral_public_key is not None
        assert encrypted.nonce is not None
        assert encrypted.tag is not None

        # Decrypt
        decrypted = cipher.decrypt(encrypted, private_key)
        assert decrypted == plaintext

    def test_encrypt_evidence(self):
        """Test evidence encryption with viewing key."""
        from rra.privacy import generate_viewing_key, encrypt_evidence, decrypt_evidence

        key = generate_viewing_key()
        evidence = {
            "description": "Test dispute evidence",
            "documents": ["doc1.pdf", "doc2.txt"],
            "timestamp": 1234567890,
        }
        dispute_id = 42

        # Encrypt
        encrypted, evidence_hash = encrypt_evidence(evidence, key, dispute_id)

        assert encrypted.ciphertext is not None
        assert evidence_hash is not None
        assert len(evidence_hash) == 32

        # Decrypt
        decrypted = decrypt_evidence(encrypted, key)

        assert decrypted["evidence"] == evidence
        assert decrypted["dispute_id"] == dispute_id

    def test_viewing_key_serialization(self):
        """Test viewing key export/import."""
        from rra.privacy.viewing_keys import ViewingKeyManager

        manager = ViewingKeyManager()
        key = manager.generate_viewing_key()

        # Export without private key
        exported = manager.export_viewing_key(key, include_private=False)
        assert "private_key" not in exported
        assert "public_key" in exported

        # Export with private key
        exported_full = manager.export_viewing_key(key, include_private=True)
        assert "private_key" in exported_full

        # Import
        imported = manager.import_viewing_key(exported_full)
        assert imported.public_key == key.public_key
        assert imported.commitment == key.commitment


class TestSecretSharing:
    """Tests for Shamir's Secret Sharing."""

    def test_split_and_reconstruct(self):
        """Test basic split and reconstruct."""
        from rra.privacy import split_secret, reconstruct_secret

        secret = os.urandom(32)
        threshold = 3
        total_shares = 5

        # Split
        shares = split_secret(secret, threshold, total_shares)
        assert len(shares) == total_shares

        # Reconstruct with exact threshold
        reconstructed = reconstruct_secret(shares[:threshold], threshold)
        assert reconstructed == secret

        # Reconstruct with more than threshold
        reconstructed2 = reconstruct_secret(shares, threshold)
        assert reconstructed2 == secret

    def test_threshold_requirement(self):
        """Test that fewer than threshold shares fail."""
        from rra.privacy import split_secret
        from rra.privacy.secret_sharing import ShamirSecretSharing

        secret = os.urandom(32)
        threshold = 3
        total_shares = 5

        shares = split_secret(secret, threshold, total_shares)
        sss = ShamirSecretSharing(threshold, total_shares)

        # Should raise with too few shares
        with pytest.raises(ValueError):
            sss.reconstruct(shares[: threshold - 1])

    def test_any_threshold_shares_work(self):
        """Test that any combination of threshold shares works."""
        from rra.privacy import split_secret, reconstruct_secret

        secret = os.urandom(32)
        threshold = 3
        total_shares = 5

        shares = split_secret(secret, threshold, total_shares)

        # Try different combinations
        combinations = [
            [shares[0], shares[1], shares[2]],
            [shares[0], shares[2], shares[4]],
            [shares[1], shares[3], shares[4]],
            [shares[2], shares[3], shares[4]],
        ]

        for combo in combinations:
            reconstructed = reconstruct_secret(combo, threshold)
            assert reconstructed == secret

    def test_threshold_key_escrow(self):
        """Test high-level key escrow interface."""
        from rra.privacy.secret_sharing import ThresholdKeyEscrow

        escrow = ThresholdKeyEscrow(threshold=3, total_shares=5)
        viewing_key = os.urandom(32)

        # Escrow key
        shares, commitments = escrow.escrow_key(viewing_key)

        assert len(shares) == 5
        assert len(commitments) == 5

        # Verify shares
        verifications = escrow.verify_shares(shares, commitments)
        assert all(verifications)

        # Recover key
        recovered = escrow.recover_key(shares[:3])
        assert recovered == viewing_key


class TestIdentity:
    """Tests for ZK identity management."""

    def test_generate_identity(self):
        """Test identity generation."""
        from rra.privacy.identity import IdentityManager

        manager = IdentityManager()
        identity = manager.generate_identity()

        assert identity.identity_secret != 0
        assert identity.identity_hash is not None
        assert len(identity.identity_hash) == 32
        assert identity.salt is not None

    def test_identity_with_address(self):
        """Test identity bound to Ethereum address."""
        from rra.privacy.identity import IdentityManager
        from eth_utils import to_checksum_address

        manager = IdentityManager()
        # Use properly checksummed address (EIP-55 format)
        address = "0x742D35cC6634C0532925a3B844Bc9e7595F0bEb3"

        identity = manager.generate_identity(address=address)

        # Address is normalized to checksum format per LOW-003 security fix
        assert identity.address == to_checksum_address(address)
        assert identity.identity_secret != 0

    def test_deterministic_identity_from_signature(self):
        """Test signature-derived identity is deterministic."""
        from rra.privacy.identity import IdentityManager

        manager = IdentityManager()
        signature = os.urandom(65)  # Mock signature

        identity1 = manager.derive_identity_from_signature(signature)
        identity2 = manager.derive_identity_from_signature(signature)

        assert identity1.identity_secret == identity2.identity_secret
        assert identity1.identity_hash == identity2.identity_hash

    def test_prepare_zk_inputs(self):
        """Test ZK input preparation for prove_identity circuit."""
        from rra.privacy.identity import IdentityManager

        manager = IdentityManager()
        identity = manager.generate_identity()

        inputs = manager.prepare_zk_inputs(identity, identity.identity_hash)

        assert "identitySecret" in inputs
        assert "identityManager" in inputs
        assert inputs["identitySecret"] == str(identity.identity_secret)

    def test_prepare_membership_inputs(self):
        """Test ZK input preparation for dispute_membership circuit."""
        from rra.privacy.identity import IdentityManager

        manager = IdentityManager()
        initiator = manager.generate_identity()
        counterparty = manager.generate_identity()

        # Prepare as initiator
        inputs = manager.prepare_membership_inputs(
            initiator, initiator.identity_hash, counterparty.identity_hash, is_initiator=True
        )

        assert inputs["roleSelector"] == "0"
        assert "initiatorHash" in inputs
        assert "counterpartyHash" in inputs

        # Prepare as counterparty
        inputs = manager.prepare_membership_inputs(
            counterparty, initiator.identity_hash, counterparty.identity_hash, is_initiator=False
        )

        assert inputs["roleSelector"] == "1"

    def test_identity_storage(self):
        """Test encrypted identity storage."""
        from rra.privacy.identity import IdentityManager

        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir)
            manager = IdentityManager(storage_path=storage_path)

            identity = manager.generate_identity()
            password = "test_password_123"

            # Save
            result = manager.save_identity(identity, "test_identity", password)
            assert result is True

            # Load
            loaded = manager.load_identity("test_identity", password)
            assert loaded is not None
            assert loaded.identity_secret == identity.identity_secret
            assert loaded.identity_hash == identity.identity_hash

            # Wrong password fails
            wrong_loaded = manager.load_identity("test_identity", "wrong_password")
            assert wrong_loaded is None


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_identity_secret(self):
        """Test generate_identity_secret function."""
        from rra.privacy import generate_identity_secret

        secret, hash_bytes = generate_identity_secret()

        assert secret != 0
        assert len(hash_bytes) == 32

    def test_compute_identity_hash(self):
        """Test compute_identity_hash function."""
        from rra.privacy import compute_identity_hash

        secret = 12345678901234567890
        hash1 = compute_identity_hash(secret)
        hash2 = compute_identity_hash(secret)

        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 32


class TestIntegration:
    """Integration tests for full privacy workflow."""

    def test_full_dispute_privacy_workflow(self):
        """Test complete privacy workflow for dispute."""
        from rra.privacy import (
            generate_viewing_key,
            encrypt_evidence,
            decrypt_evidence,
            split_secret,
            reconstruct_secret,
        )
        from rra.privacy.identity import IdentityManager

        # 1. Generate identities for both parties
        manager = IdentityManager()
        initiator = manager.generate_identity()
        counterparty = manager.generate_identity()

        # 2. Generate viewing key for evidence
        viewing_key = generate_viewing_key()

        # 3. Encrypt evidence
        evidence = {
            "claim": "License violation detected",
            "repo_url": "https://github.com/example/repo",
            "evidence_links": ["https://example.com/proof1"],
        }
        dispute_id = 1

        encrypted, evidence_hash = encrypt_evidence(evidence, viewing_key, dispute_id)

        # 4. Split viewing key for escrow
        shares = split_secret(viewing_key.private_key, threshold=3, total_shares=5)

        # 5. Prepare ZK inputs for both parties
        initiator_inputs = manager.prepare_membership_inputs(
            initiator, initiator.identity_hash, counterparty.identity_hash, is_initiator=True
        )
        counterparty_inputs = manager.prepare_membership_inputs(
            counterparty, initiator.identity_hash, counterparty.identity_hash, is_initiator=False
        )

        # 6. Simulate compliance recovery
        recovered_key = reconstruct_secret(shares[:3], threshold=3)
        assert recovered_key == viewing_key.private_key

        # 7. Decrypt evidence with recovered key
        from rra.privacy.viewing_keys import ViewingKey

        recovered_viewing_key = ViewingKey(
            private_key=recovered_key,
            public_key=viewing_key.public_key,
            commitment=viewing_key.commitment,
            blinding_factor=viewing_key.blinding_factor,
        )

        decrypted = decrypt_evidence(encrypted, recovered_viewing_key)
        assert decrypted["evidence"] == evidence

        # Verify all pieces present
        assert initiator_inputs is not None
        assert counterparty_inputs is not None
        assert len(shares) == 5
        assert evidence_hash is not None
