# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Tests for Encrypted IPFS/Arweave Storage.
"""

import pytest
import os
from datetime import datetime


class TestEncryptedStorage:
    """Tests for EncryptedIPFSStorage."""

    def test_store_and_retrieve_mock(self):
        """Test store and retrieve with mock provider."""
        from rra.storage import EncryptedIPFSStorage, StorageProvider, create_storage
        from rra.privacy import generate_viewing_key

        storage = create_storage(provider=StorageProvider.MOCK)
        viewing_key = generate_viewing_key()

        evidence = {
            "description": "Test dispute evidence",
            "documents": ["doc1.pdf", "contract.txt"],
            "claim_amount": 1000,
        }
        dispute_id = 42

        # Store
        result = storage.store_evidence(evidence, viewing_key, dispute_id)

        assert result.success is True
        assert result.uri.startswith("mock://")
        assert result.content_hash is not None
        assert result.size_bytes > 0
        assert result.provider == StorageProvider.MOCK

        # Retrieve
        retrieved_evidence, metadata = storage.retrieve_evidence(
            result.uri, viewing_key
        )

        assert retrieved_evidence == evidence
        assert metadata.get("dispute_id") == dispute_id

    def test_store_with_metadata(self):
        """Test storing evidence with additional metadata."""
        from rra.storage import create_storage, StorageProvider
        from rra.privacy import generate_viewing_key

        storage = create_storage(provider=StorageProvider.MOCK)
        viewing_key = generate_viewing_key()

        evidence = {"claim": "License violation"}
        metadata = {
            "repo_url": "https://github.com/example/repo",
            "detected_at": "2025-01-15T10:00:00Z",
            "severity": "high",
        }

        result = storage.store_evidence(
            evidence, viewing_key, dispute_id=1, metadata=metadata
        )

        assert result.success is True

        # Retrieve and check metadata
        _, retrieved_metadata = storage.retrieve_evidence(result.uri, viewing_key)
        # Retrieved metadata includes both user metadata and package-level fields
        for key, value in metadata.items():
            assert retrieved_metadata.get(key) == value
        assert retrieved_metadata.get("dispute_id") == 1

    def test_verify_evidence_hash(self):
        """Test evidence hash verification."""
        from rra.storage import create_storage, StorageProvider
        from rra.privacy import generate_viewing_key, encrypt_evidence

        storage = create_storage(provider=StorageProvider.MOCK)
        viewing_key = generate_viewing_key()

        evidence = {"test": "data"}
        dispute_id = 123

        # Get expected hash
        _, expected_hash = encrypt_evidence(evidence, viewing_key, dispute_id)

        # Store
        result = storage.store_evidence(evidence, viewing_key, dispute_id)

        # Verify
        is_valid = storage.verify_evidence_hash(result.uri, expected_hash)
        assert is_valid is True

        # Wrong hash should fail
        wrong_hash = bytes(32)
        is_invalid = storage.verify_evidence_hash(result.uri, wrong_hash)
        assert is_invalid is False

    def test_retrieve_not_found(self):
        """Test retrieval of non-existent content."""
        from rra.storage import create_storage, StorageProvider
        from rra.privacy import generate_viewing_key

        storage = create_storage(provider=StorageProvider.MOCK)
        viewing_key = generate_viewing_key()

        with pytest.raises(ValueError, match="Not found"):
            storage.retrieve_evidence("mock://nonexistent", viewing_key)

    def test_wrong_viewing_key_fails(self):
        """Test that wrong viewing key fails decryption."""
        from rra.storage import create_storage, StorageProvider
        from rra.privacy import generate_viewing_key

        storage = create_storage(provider=StorageProvider.MOCK)
        correct_key = generate_viewing_key()
        wrong_key = generate_viewing_key()

        evidence = {"secret": "data"}
        result = storage.store_evidence(evidence, correct_key, dispute_id=1)

        # Should fail with wrong key
        with pytest.raises(Exception):  # Decryption error
            storage.retrieve_evidence(result.uri, wrong_key)

    def test_storage_result_serialization(self):
        """Test StorageResult serialization."""
        from rra.storage import StorageResult, StorageProvider

        result = StorageResult(
            success=True,
            uri="ipfs://QmTest123",
            content_hash=bytes(32),
            size_bytes=1024,
            provider=StorageProvider.IPFS_INFURA,
            timestamp=datetime.utcnow(),
            metadata={"key": "value"},
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["uri"] == "ipfs://QmTest123"
        assert len(data["content_hash"]) == 64  # hex
        assert data["size_bytes"] == 1024
        assert data["provider"] == "ipfs_infura"
        assert data["metadata"] == {"key": "value"}


class TestStorageProviders:
    """Tests for different storage provider configurations."""

    def test_create_mock_storage(self):
        """Test creating mock storage."""
        from rra.storage import create_storage, StorageProvider

        storage = create_storage(provider=StorageProvider.MOCK)
        assert storage.config.provider == StorageProvider.MOCK

    def test_create_ipfs_storage(self):
        """Test creating IPFS storage configuration."""
        from rra.storage import create_storage, StorageProvider

        storage = create_storage(
            provider=StorageProvider.IPFS_INFURA,
            api_key="test_key",
            api_secret="test_secret",
        )

        assert storage.config.provider == StorageProvider.IPFS_INFURA
        assert storage.config.api_key == "test_key"
        assert storage.config.api_secret == "test_secret"
        assert "infura" in storage.config.api_url.lower()

    def test_create_pinata_storage(self):
        """Test creating Pinata storage configuration."""
        from rra.storage import create_storage, StorageProvider

        storage = create_storage(
            provider=StorageProvider.IPFS_PINATA,
            api_key="pinata_jwt_token",
        )

        assert storage.config.provider == StorageProvider.IPFS_PINATA
        assert "pinata" in storage.config.api_url.lower()

    def test_create_arweave_storage(self):
        """Test creating Arweave storage configuration."""
        from rra.storage import create_storage, StorageProvider

        storage = create_storage(provider=StorageProvider.ARWEAVE)

        assert storage.config.provider == StorageProvider.ARWEAVE
        assert "arweave" in storage.config.api_url.lower()


class TestStorageIntegration:
    """Integration tests for storage with privacy modules."""

    def test_full_privacy_workflow_with_storage(self):
        """Test complete workflow: encrypt, store, retrieve, decrypt."""
        from rra.storage import create_storage, StorageProvider
        from rra.privacy import (
            generate_viewing_key,
            split_secret,
            reconstruct_secret,
        )
        from rra.privacy.viewing_keys import ViewingKey

        # 1. Create storage and viewing key
        storage = create_storage(provider=StorageProvider.MOCK)
        viewing_key = generate_viewing_key()

        # 2. Prepare evidence
        evidence = {
            "claim": "Unauthorized use of licensed code",
            "infringing_repo": "https://github.com/infringer/repo",
            "original_repo": "https://github.com/owner/original",
            "detected_lines": [10, 20, 30, 40, 50],
            "similarity_score": 0.95,
        }
        dispute_id = 999

        # 3. Store evidence
        result = storage.store_evidence(
            evidence,
            viewing_key,
            dispute_id,
            metadata={"severity": "critical"},
        )
        assert result.success is True

        # 4. Split viewing key for escrow
        shares = split_secret(viewing_key.private_key, threshold=3, total_shares=5)
        assert len(shares) == 5

        # 5. Simulate key recovery (threshold reached)
        recovered_private = reconstruct_secret(shares[:3], threshold=3)
        recovered_key = ViewingKey(
            private_key=recovered_private,
            public_key=viewing_key.public_key,
            commitment=viewing_key.commitment,
            blinding_factor=viewing_key.blinding_factor,
        )

        # 6. Retrieve and decrypt with recovered key
        retrieved_evidence, metadata = storage.retrieve_evidence(
            result.uri, recovered_key
        )

        assert retrieved_evidence == evidence
        assert metadata["severity"] == "critical"

    def test_multiple_disputes_storage(self):
        """Test storing evidence for multiple disputes."""
        from rra.storage import create_storage, StorageProvider
        from rra.privacy import generate_viewing_key

        storage = create_storage(provider=StorageProvider.MOCK)

        disputes = []
        for i in range(5):
            key = generate_viewing_key()
            evidence = {"dispute_number": i, "data": f"Evidence for dispute {i}"}

            result = storage.store_evidence(evidence, key, dispute_id=i)
            disputes.append((result.uri, key, evidence))

        # Verify each can be retrieved independently
        for uri, key, original_evidence in disputes:
            retrieved, _ = storage.retrieve_evidence(uri, key)
            assert retrieved == original_evidence
