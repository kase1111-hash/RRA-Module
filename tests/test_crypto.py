# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Cryptographic Primitives.

Tests:
- ECIES viewing keys
- Shamir Secret Sharing
- Pedersen commitments
"""

import pytest
import os

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
    EscrowManager,
)
from rra.crypto.pedersen import (
    PedersenCommitment,
    EvidenceCommitmentManager,
)


# ============================================================================
# Viewing Keys Tests
# ============================================================================

class TestViewingKey:
    """Tests for ViewingKey class."""

    def test_generate_key(self):
        """Test generating a viewing key."""
        key = ViewingKey.generate(
            purpose=KeyPurpose.DISPUTE_EVIDENCE,
            context_id="dispute-123"
        )

        assert key.private_key is not None
        assert key.public_key is not None
        assert key.purpose == KeyPurpose.DISPUTE_EVIDENCE
        assert key.context_id == "dispute-123"
        assert key.commitment is not None
        assert len(key.commitment) == 32

    def test_generate_with_expiration(self):
        """Test generating key with expiration."""
        key = ViewingKey.generate(
            purpose=KeyPurpose.DISPUTE_EVIDENCE,
            context_id="dispute-123",
            expires_in_days=30
        )

        assert key.expires_at is not None
        assert key.is_expired is False
        assert key.expires_at > key.created_at

    def test_derive_key(self):
        """Test deriving key from master key."""
        master_key = os.urandom(32)

        key1 = ViewingKey.derive(
            master_key,
            KeyPurpose.DISPUTE_EVIDENCE,
            "dispute-123",
            index=0
        )

        key2 = ViewingKey.derive(
            master_key,
            KeyPurpose.DISPUTE_EVIDENCE,
            "dispute-123",
            index=0
        )

        # Same derivation should produce same key
        assert key1.commitment == key2.commitment

    def test_derive_different_indices(self):
        """Test different indices produce different keys."""
        master_key = os.urandom(32)

        key1 = ViewingKey.derive(master_key, KeyPurpose.DISPUTE_EVIDENCE, "d-1", 0)
        key2 = ViewingKey.derive(master_key, KeyPurpose.DISPUTE_EVIDENCE, "d-1", 1)

        assert key1.commitment != key2.commitment

    def test_encrypt_decrypt(self):
        """Test encryption and decryption."""
        key = ViewingKey.generate(
            purpose=KeyPurpose.DISPUTE_EVIDENCE,
            context_id="dispute-123"
        )

        plaintext = b"This is secret evidence for the dispute."
        encrypted = key.encrypt(plaintext)

        assert encrypted.ciphertext != plaintext
        assert encrypted.key_commitment == key.commitment

        decrypted = key.decrypt(encrypted)
        assert decrypted == plaintext

    def test_wrong_key_decrypt_fails(self):
        """Test decryption with wrong key fails."""
        key1 = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "d-1")
        key2 = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "d-2")

        encrypted = key1.encrypt(b"secret data")

        with pytest.raises(ValueError, match="commitment mismatch"):
            key2.decrypt(encrypted)

    def test_export_import(self):
        """Test key export and import."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "d-1")
        private_bytes = key.export_private()

        restored = ViewingKey.from_private_bytes(
            private_bytes,
            KeyPurpose.DISPUTE_EVIDENCE,
            "d-1"
        )

        assert restored.commitment == key.commitment


class TestEncryptedData:
    """Tests for EncryptedData serialization."""

    def test_to_bytes_from_bytes(self):
        """Test binary serialization."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "d-1")
        encrypted = key.encrypt(b"test data")

        serialized = encrypted.to_bytes()
        restored = EncryptedData.from_bytes(serialized)

        assert restored.ciphertext == encrypted.ciphertext
        assert restored.iv == encrypted.iv
        assert restored.auth_tag == encrypted.auth_tag

    def test_to_dict_from_dict(self):
        """Test dictionary serialization."""
        key = ViewingKey.generate(KeyPurpose.DISPUTE_EVIDENCE, "d-1")
        encrypted = key.encrypt(b"test data")

        as_dict = encrypted.to_dict()
        restored = EncryptedData.from_dict(as_dict)

        assert restored.ciphertext == encrypted.ciphertext


class TestViewingKeyManager:
    """Tests for ViewingKeyManager."""

    def test_generate_for_dispute(self):
        """Test generating key for dispute."""
        manager = ViewingKeyManager()
        key = manager.generate_for_dispute("dispute-456")

        assert key.context_id == "dispute-456"
        assert key.purpose == KeyPurpose.DISPUTE_EVIDENCE

    def test_encrypt_decrypt_dispute_evidence(self):
        """Test encrypting and decrypting dispute evidence."""
        manager = ViewingKeyManager()
        evidence = b"Confidential dispute evidence document"

        encrypted, commitment = manager.encrypt_for_dispute("d-1", evidence)

        decrypted = manager.decrypt_dispute_evidence("d-1", encrypted)
        assert decrypted == evidence

    def test_get_commitment_for_chain(self):
        """Test getting on-chain commitment."""
        manager = ViewingKeyManager()
        manager.generate_for_dispute("d-1")

        commitment = manager.get_commitment_for_chain("d-1")
        assert len(commitment) == 32


# ============================================================================
# Shamir Secret Sharing Tests
# ============================================================================

class TestShamirSecretSharing:
    """Tests for Shamir's Secret Sharing."""

    def test_split_and_reconstruct(self):
        """Test basic split and reconstruct."""
        shamir = ShamirSecretSharing()
        secret = os.urandom(32)

        config = ThresholdConfig(
            threshold=3,
            total_shares=5,
            holders=[
                ShareHolder.USER,
                ShareHolder.DAO_GOVERNANCE,
                ShareHolder.ESCROW_SERVICE_1,
                ShareHolder.ESCROW_SERVICE_2,
                ShareHolder.COMPLIANCE_OFFICER,
            ]
        )

        shares = shamir.split(secret, config, "context-1")
        assert len(shares) == 5

        # Reconstruct with exactly threshold shares
        reconstructed = shamir.reconstruct(shares[:3])
        assert reconstructed == secret

    def test_reconstruct_with_any_threshold_shares(self):
        """Test reconstruction with any M shares works."""
        shamir = ShamirSecretSharing()
        secret = os.urandom(32)
        config = ThresholdConfig.standard_3_of_5()

        shares = shamir.split(secret, config, "ctx")

        # Try different combinations
        assert shamir.reconstruct([shares[0], shares[1], shares[2]]) == secret
        assert shamir.reconstruct([shares[0], shares[2], shares[4]]) == secret
        assert shamir.reconstruct([shares[1], shares[3], shares[4]]) == secret

    def test_insufficient_shares_fails(self):
        """Test that fewer than threshold shares fails."""
        shamir = ShamirSecretSharing()
        secret = os.urandom(32)
        config = ThresholdConfig.standard_3_of_5()

        shares = shamir.split(secret, config, "ctx")

        with pytest.raises(ValueError, match="Not enough shares"):
            shamir.reconstruct(shares[:2])

    def test_share_metadata(self):
        """Test share metadata is correct."""
        shamir = ShamirSecretSharing()
        secret = os.urandom(32)
        config = ThresholdConfig.standard_3_of_5()

        shares = shamir.split(secret, config, "dispute-123")

        for i, share in enumerate(shares):
            assert share.index == i + 1
            assert share.holder == config.holders[i]
            assert share.context_id == "dispute-123"
            assert share.threshold == 3
            assert share.total_shares == 5

    def test_share_serialization(self):
        """Test share serialization."""
        shamir = ShamirSecretSharing()
        secret = os.urandom(32)
        config = ThresholdConfig.simple_2_of_3()

        shares = shamir.split(secret, config, "ctx")

        for share in shares:
            as_dict = share.to_dict()
            restored = KeyShare.from_dict(as_dict)
            assert restored.value == share.value
            assert restored.holder == share.holder


class TestThresholdConfig:
    """Tests for ThresholdConfig."""

    def test_standard_3_of_5(self):
        """Test standard 3-of-5 config."""
        config = ThresholdConfig.standard_3_of_5()
        assert config.threshold == 3
        assert config.total_shares == 5
        assert len(config.holders) == 5

    def test_simple_2_of_3(self):
        """Test simple 2-of-3 config."""
        config = ThresholdConfig.simple_2_of_3()
        assert config.threshold == 2
        assert config.total_shares == 3

    def test_invalid_threshold(self):
        """Test invalid threshold raises error."""
        with pytest.raises(ValueError, match="at least 2"):
            ThresholdConfig(
                threshold=1,
                total_shares=3,
                holders=[ShareHolder.USER, ShareHolder.DAO_GOVERNANCE, ShareHolder.COMPLIANCE_OFFICER]
            )

    def test_threshold_exceeds_total(self):
        """Test threshold > total raises error."""
        with pytest.raises(ValueError, match="cannot exceed"):
            ThresholdConfig(
                threshold=4,
                total_shares=3,
                holders=[ShareHolder.USER, ShareHolder.DAO_GOVERNANCE, ShareHolder.COMPLIANCE_OFFICER]
            )


class TestEscrowManager:
    """Tests for EscrowManager."""

    def test_escrow_and_recover(self):
        """Test escrowing and recovering a key."""
        manager = EscrowManager()
        key = os.urandom(32)

        shares_by_holder = manager.escrow_viewing_key(key, "dispute-1")
        assert len(shares_by_holder) == 5

        # Recover with user + DAO + escrow1 (3 of 5)
        provided_shares = [
            shares_by_holder[ShareHolder.USER],
            shares_by_holder[ShareHolder.DAO_GOVERNANCE],
            shares_by_holder[ShareHolder.ESCROW_SERVICE_1],
        ]

        recovered = manager.recover_viewing_key("dispute-1", provided_shares)
        assert recovered == key

    def test_verify_reconstruction_possible(self):
        """Test checking if reconstruction is possible."""
        manager = EscrowManager()
        key = os.urandom(32)
        manager.escrow_viewing_key(key, "d-1")

        # With 3 holders - should be possible
        assert manager.verify_reconstruction_possible(
            "d-1",
            [ShareHolder.USER, ShareHolder.DAO_GOVERNANCE, ShareHolder.ESCROW_SERVICE_1]
        )

        # With only 2 - should not be possible
        assert not manager.verify_reconstruction_possible(
            "d-1",
            [ShareHolder.USER, ShareHolder.DAO_GOVERNANCE]
        )


# ============================================================================
# Pedersen Commitment Tests
# ============================================================================

class TestPedersenCommitment:
    """Tests for Pedersen commitments."""

    def test_commit_and_verify(self):
        """Test basic commitment and verification."""
        pedersen = PedersenCommitment()
        value = b"secret evidence hash"

        commitment, blinding = pedersen.commit(value)

        assert len(commitment) == 64  # EC point (x || y)
        assert len(blinding) == 32
        assert pedersen.verify(commitment, value, blinding)

    def test_different_blinding_different_commitment(self):
        """Test different blinding factors produce different commitments."""
        pedersen = PedersenCommitment()
        value = b"same value"

        c1, _ = pedersen.commit(value)
        c2, _ = pedersen.commit(value)

        assert c1 != c2  # Different random blinding

    def test_explicit_blinding(self):
        """Test using explicit blinding factor."""
        pedersen = PedersenCommitment()
        value = b"test"
        blinding = os.urandom(32)

        c1, _ = pedersen.commit(value, blinding)
        c2, _ = pedersen.commit(value, blinding)

        assert c1 == c2  # Same blinding = same commitment

    def test_wrong_value_fails_verification(self):
        """Test verification fails with wrong value."""
        pedersen = PedersenCommitment()

        commitment, blinding = pedersen.commit(b"real value")

        assert not pedersen.verify(commitment, b"fake value", blinding)

    def test_wrong_blinding_fails_verification(self):
        """Test verification fails with wrong blinding."""
        pedersen = PedersenCommitment()
        value = b"test"

        commitment, _ = pedersen.commit(value)
        wrong_blinding = os.urandom(32)

        assert not pedersen.verify(commitment, value, wrong_blinding)

    def test_commit_evidence(self):
        """Test evidence commitment with proof."""
        pedersen = PedersenCommitment()
        evidence_hash = pedersen.hash_evidence(b"raw evidence data")

        proof, blinding = pedersen.commit_evidence(evidence_hash, "dispute-1")

        assert proof.commitment is not None
        assert proof.context_id == "dispute-1"
        assert pedersen.verify_evidence_commitment(proof, evidence_hash, blinding)

    def test_aggregate_commitments(self):
        """Test homomorphic aggregation."""
        pedersen = PedersenCommitment()

        c1, _ = pedersen.commit(b"value1")
        c2, _ = pedersen.commit(b"value2")
        c3, _ = pedersen.commit(b"value3")

        aggregated = pedersen.aggregate_commitments([c1, c2, c3])
        assert len(aggregated) == 64  # EC point (x || y)


class TestEvidenceCommitmentManager:
    """Tests for EvidenceCommitmentManager."""

    def test_commit_and_verify_evidence(self):
        """Test full evidence commitment flow."""
        manager = EvidenceCommitmentManager()
        evidence = b"This is dispute evidence that should be committed"

        proof = manager.commit_dispute_evidence("dispute-1", evidence)

        assert proof.commitment is not None

        # Reveal and verify
        evidence_hash, blinding = manager.reveal_evidence("dispute-1", evidence)

        assert manager.verify_revelation("dispute-1", evidence, blinding)

    def test_batch_commit(self):
        """Test batch commitment of multiple evidence items."""
        manager = EvidenceCommitmentManager()
        evidence_list = [
            b"Evidence item 1",
            b"Evidence item 2",
            b"Evidence item 3",
        ]

        aggregated, blindings = manager.batch_commit("dispute-1", evidence_list)

        assert len(aggregated) == 64  # EC point (x || y)
        assert len(blindings) == 3


# ============================================================================
# Integration Tests
# ============================================================================

class TestCryptoIntegration:
    """Integration tests for crypto modules."""

    def test_full_escrow_flow(self):
        """Test complete viewing key escrow flow."""
        # 1. Generate viewing key
        vk_manager = ViewingKeyManager()
        vk_manager.generate_for_dispute("dispute-123")

        # 2. Encrypt evidence
        evidence = b"Confidential dispute evidence"
        encrypted, _ = vk_manager.encrypt_for_dispute("dispute-123", evidence)

        # 3. Escrow the viewing key
        escrow = EscrowManager()
        key_bytes = vk_manager.export_key_for_escrow("dispute-123")
        shares = escrow.escrow_viewing_key(key_bytes, "dispute-123")

        # 4. Simulate threshold recovery
        recovery_shares = [
            shares[ShareHolder.USER],
            shares[ShareHolder.DAO_GOVERNANCE],
            shares[ShareHolder.COMPLIANCE_OFFICER],
        ]
        recovered_key = escrow.recover_viewing_key("dispute-123", recovery_shares)

        # 5. Restore viewing key and decrypt
        restored_vk = ViewingKey.from_private_bytes(
            recovered_key,
            KeyPurpose.DISPUTE_EVIDENCE,
            "dispute-123"
        )
        decrypted = restored_vk.decrypt(encrypted)

        assert decrypted == evidence

    def test_evidence_commitment_with_escrow(self):
        """Test evidence commitment integrated with key escrow."""
        # Commit evidence
        commit_manager = EvidenceCommitmentManager()
        evidence = b"Evidence requiring commitment"
        commit_manager.commit_dispute_evidence("d-1", evidence)

        # The commitment can be stored on-chain
        on_chain_commitment = commit_manager.get_commitment_for_chain("d-1")
        assert len(on_chain_commitment) == 64  # EC point (x || y)

        # Later, reveal and verify
        _, blinding = commit_manager.reveal_evidence("d-1", evidence)
        assert commit_manager.verify_revelation("d-1", evidence, blinding)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
