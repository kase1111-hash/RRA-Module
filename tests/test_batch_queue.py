# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Batch Queue (Inference Attack Prevention).

Tests:
- Dispute queueing
- Proof queueing
- Batch release logic
- Privacy enhancer
"""

import pytest
import os
from datetime import datetime

from rra.privacy.batch_queue import (
    BatchQueueClient,
    PrivacyEnhancer,
    QueuedDispute,
    QueuedProof,
    BatchConfig,
    SubmissionStatus,
    create_batch_client,
    create_privacy_enhancer,
)


# ============================================================================
# BatchQueueClient Tests
# ============================================================================

class TestBatchQueueClient:
    """Tests for BatchQueueClient."""

    def test_create_client(self):
        """Test creating a batch queue client."""
        client = BatchQueueClient()
        assert client is not None
        assert client.contract_address is None

    def test_create_client_with_address(self):
        """Test creating client with contract address."""
        address = "0x" + "1234" * 10
        client = BatchQueueClient(contract_address=address)
        assert client.contract_address == address

    def test_queue_dispute(self):
        """Test queueing a dispute."""
        client = BatchQueueClient()

        queued = client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://QmTest123",
            stake_amount=1000000000000000000,  # 1 ETH in wei
        )

        assert queued.queue_index == 0
        assert queued.status == SubmissionStatus.PENDING
        assert queued.stake_amount == 1000000000000000000
        assert queued.dispute_id is None

    def test_queue_dispute_requires_positive_stake(self):
        """Test that stake amount must be positive."""
        client = BatchQueueClient()

        with pytest.raises(ValueError, match="positive"):
            client.queue_dispute(
                initiator_hash=os.urandom(32),
                counterparty_hash=os.urandom(32),
                evidence_hash=os.urandom(32),
                viewing_key_commitment=os.urandom(32),
                ipfs_uri="ipfs://QmTest",
                stake_amount=0,
            )

    def test_queue_multiple_disputes(self):
        """Test queueing multiple disputes."""
        client = BatchQueueClient()

        dispute1 = client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://1",
            stake_amount=100,
        )

        dispute2 = client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://2",
            stake_amount=200,
        )

        assert dispute1.queue_index == 0
        assert dispute2.queue_index == 1

    def test_queue_identity_proof(self):
        """Test queueing an identity proof."""
        client = BatchQueueClient()

        proof = client.queue_identity_proof(
            dispute_id=123,
            proof_a=(1, 2),
            proof_b=((1, 2), (3, 4)),
            proof_c=(5, 6),
            public_signals=(7,),
        )

        assert proof.queue_index == 0
        assert proof.dispute_id == 123
        assert proof.status == SubmissionStatus.PENDING


class TestBatchRelease:
    """Tests for batch release logic."""

    def test_cannot_release_empty_queue(self):
        """Test that empty queue cannot be released."""
        client = BatchQueueClient()
        assert client.can_release_batch() is False

    def test_can_release_when_min_size_reached(self):
        """Test batch can release when minimum size reached."""
        client = BatchQueueClient()
        client._config.min_batch_size = 2

        # Queue first dispute
        client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://1",
            stake_amount=100,
        )
        assert client.can_release_batch() is False

        # Queue second dispute
        client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://2",
            stake_amount=100,
        )
        assert client.can_release_batch() is True

    def test_simulate_batch_release(self):
        """Test simulating batch release."""
        client = BatchQueueClient()
        client._config.min_batch_size = 2

        # Queue disputes
        client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://1",
            stake_amount=100,
        )
        client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://2",
            stake_amount=100,
        )

        result = client.simulate_batch_release(current_block=1000)

        assert result["released"] is True
        assert result["disputes_processed"] == 2
        assert result["proofs_processed"] == 0

    def test_max_batch_size_enforced(self):
        """Test that max batch size is enforced."""
        client = BatchQueueClient()
        client._config.min_batch_size = 1
        client._config.max_batch_size = 3

        # Queue 5 disputes
        for i in range(5):
            client.queue_dispute(
                initiator_hash=os.urandom(32),
                counterparty_hash=os.urandom(32),
                evidence_hash=os.urandom(32),
                viewing_key_commitment=os.urandom(32),
                ipfs_uri=f"ipfs://{i}",
                stake_amount=100,
            )

        result = client.simulate_batch_release(current_block=1000)

        # Only 3 should be processed (max batch size)
        assert result["disputes_processed"] == 3

        # 2 should still be pending
        status = client.get_queue_status()
        assert status["dispute_queue"]["pending"] == 2

    def test_disputes_get_ids_after_release(self):
        """Test that disputes get IDs assigned after release."""
        client = BatchQueueClient()
        client._config.min_batch_size = 1

        dispute = client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://1",
            stake_amount=100,
        )

        assert dispute.dispute_id is None

        client.simulate_batch_release(current_block=1000)

        # After release, dispute_id should be assigned
        assert client._dispute_queue[0].dispute_id is not None
        assert client._dispute_queue[0].status == SubmissionStatus.COMPLETED


class TestQueueStatus:
    """Tests for queue status reporting."""

    def test_get_queue_status(self):
        """Test getting queue status."""
        client = BatchQueueClient()

        status = client.get_queue_status()

        assert "dispute_queue" in status
        assert "proof_queue" in status
        assert "can_release" in status
        assert "config" in status

    def test_queue_status_counts(self):
        """Test queue status counts correctly."""
        client = BatchQueueClient()

        # Queue some items
        client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://1",
            stake_amount=100,
        )
        client.queue_identity_proof(
            dispute_id=1,
            proof_a=(1, 2),
            proof_b=((1, 2), (3, 4)),
            proof_c=(5, 6),
            public_signals=(7,),
        )

        status = client.get_queue_status()

        assert status["dispute_queue"]["pending"] == 1
        assert status["dispute_queue"]["total"] == 1
        assert status["proof_queue"]["pending"] == 1
        assert status["proof_queue"]["total"] == 1


class TestBatchConfig:
    """Tests for batch configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        client = BatchQueueClient()

        assert client._config.batch_interval == 100
        assert client._config.min_batch_size == 3
        assert client._config.max_batch_size == 20
        assert client._config.dummy_probability == 20

    def test_update_config(self):
        """Test updating configuration."""
        client = BatchQueueClient()

        updated = client.update_config(
            batch_interval=50,
            min_batch_size=5,
            max_batch_size=10,
            dummy_probability=30,
        )

        assert updated.batch_interval == 50
        assert updated.min_batch_size == 5
        assert updated.max_batch_size == 10
        assert updated.dummy_probability == 30

    def test_invalid_max_batch_size(self):
        """Test that max_batch_size cannot be less than min."""
        client = BatchQueueClient()
        client._config.min_batch_size = 5

        with pytest.raises(ValueError, match="less than"):
            client.update_config(max_batch_size=3)

    def test_invalid_dummy_probability(self):
        """Test that dummy probability must be 0-100."""
        client = BatchQueueClient()

        with pytest.raises(ValueError, match="0-100"):
            client.update_config(dummy_probability=150)


# ============================================================================
# PrivacyEnhancer Tests
# ============================================================================

class TestPrivacyEnhancer:
    """Tests for PrivacyEnhancer."""

    def test_create_privacy_enhancer(self):
        """Test creating a privacy enhancer."""
        enhancer = PrivacyEnhancer()
        assert enhancer is not None
        assert enhancer.batch_client is not None

    def test_submit_private_dispute(self):
        """Test submitting a private dispute."""
        enhancer = PrivacyEnhancer()

        queued = enhancer.submit_private_dispute(
            initiator_secret=os.urandom(32),
            counterparty_identity=os.urandom(32),
            evidence=b"test evidence",
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://QmTest",
            stake_amount=100,
            add_random_delay=False,  # Disable delay for test speed
        )

        assert queued.status == SubmissionStatus.PENDING

    def test_submit_private_proof(self):
        """Test submitting a private proof."""
        enhancer = PrivacyEnhancer()

        proof_data = {
            "a": [1, 2],
            "b": [[1, 2], [3, 4]],
            "c": [5, 6],
            "signals": [7],
        }

        queued = enhancer.submit_private_proof(
            dispute_id=123,
            proof=proof_data,
            add_random_delay=False,
        )

        assert queued.dispute_id == 123
        assert queued.status == SubmissionStatus.PENDING

    def test_get_privacy_metrics(self):
        """Test getting privacy metrics."""
        enhancer = PrivacyEnhancer()

        # Submit some items
        enhancer.submit_private_dispute(
            initiator_secret=os.urandom(32),
            counterparty_identity=os.urandom(32),
            evidence=b"evidence",
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://1",
            stake_amount=100,
            add_random_delay=False,
        )

        metrics = enhancer.get_privacy_metrics()

        assert "queue_status" in metrics
        assert "random_delays" in metrics
        assert "privacy_level" in metrics

    def test_privacy_level_calculation(self):
        """Test privacy level calculation."""
        enhancer = PrivacyEnhancer()

        # With no items and low dummy probability, privacy should be low
        enhancer.batch_client._config.dummy_probability = 10
        metrics = enhancer.get_privacy_metrics()
        assert metrics["privacy_level"] == "low"

        # Queue many items with high dummy probability for high privacy
        enhancer.batch_client._config.dummy_probability = 35
        for i in range(12):
            enhancer.submit_private_dispute(
                initiator_secret=os.urandom(32),
                counterparty_identity=os.urandom(32),
                evidence=b"evidence",
                evidence_hash=os.urandom(32),
                viewing_key_commitment=os.urandom(32),
                ipfs_uri=f"ipfs://{i}",
                stake_amount=100,
                add_random_delay=False,
            )

        metrics = enhancer.get_privacy_metrics()
        assert metrics["privacy_level"] == "high"


# ============================================================================
# Serialization Tests
# ============================================================================

class TestSerialization:
    """Tests for data serialization."""

    def test_queued_dispute_to_dict(self):
        """Test QueuedDispute serialization."""
        client = BatchQueueClient()

        dispute = client.queue_dispute(
            initiator_hash=os.urandom(32),
            counterparty_hash=os.urandom(32),
            evidence_hash=os.urandom(32),
            viewing_key_commitment=os.urandom(32),
            ipfs_uri="ipfs://test",
            stake_amount=1000,
        )

        as_dict = dispute.to_dict()

        assert "queue_index" in as_dict
        assert "initiator_hash" in as_dict
        assert "stake_amount" in as_dict
        assert as_dict["stake_amount"] == 1000

    def test_queued_proof_to_dict(self):
        """Test QueuedProof serialization."""
        client = BatchQueueClient()

        proof = client.queue_identity_proof(
            dispute_id=456,
            proof_a=(1, 2),
            proof_b=((1, 2), (3, 4)),
            proof_c=(5, 6),
            public_signals=(7,),
        )

        as_dict = proof.to_dict()

        assert "queue_index" in as_dict
        assert "dispute_id" in as_dict
        assert as_dict["dispute_id"] == 456


# ============================================================================
# Convenience Function Tests
# ============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_batch_client(self):
        """Test create_batch_client function."""
        client = create_batch_client()
        assert isinstance(client, BatchQueueClient)

    def test_create_batch_client_with_address(self):
        """Test create_batch_client with address."""
        address = "0x" + "abcd" * 10
        client = create_batch_client(contract_address=address)
        assert client.contract_address == address

    def test_create_privacy_enhancer_function(self):
        """Test create_privacy_enhancer function."""
        enhancer = create_privacy_enhancer()
        assert isinstance(enhancer, PrivacyEnhancer)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
