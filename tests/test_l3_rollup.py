# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for L3 High-Throughput Dispute Processing (Phase 6.7).

Tests cover:
- Batch processor functionality
- Sequencer transaction ordering
- State transition computation
- Merkle proof generation
- Batch lifecycle management
"""

import secrets
import time
from datetime import datetime, timezone

import pytest

from src.rra.l3.batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchStatus,
    create_batch_processor,
)
from src.rra.l3.sequencer import (
    DisputeSequencer,
    SequencerConfig,
    SequencerStatus,
    Transaction,
    TransactionType,
    create_sequencer,
)


# =============================================================================
# Fixtures
# =============================================================================


def random_hash() -> bytes:
    """Generate a random 32-byte hash."""
    return secrets.token_bytes(32)


# =============================================================================
# BatchProcessor Tests
# =============================================================================


class TestBatchProcessor:
    """Tests for the batch processor."""

    @pytest.fixture
    def processor(self):
        """Create a batch processor with small batch sizes for testing."""
        config = BatchConfig(
            min_batch_size=3,
            max_batch_size=10,
            batch_interval_seconds=1.0,
        )
        return BatchProcessor(config)

    def test_add_dispute(self, processor):
        """Test adding a single dispute."""
        dispute = processor.add_dispute(
            initiator_hash=random_hash(),
            counterparty_hash=random_hash(),
            evidence_root=random_hash(),
            stake_amount=1000000000000000000,  # 1 ETH
        )

        assert dispute.dispute_id == 1
        assert dispute.stake_amount == 1000000000000000000
        assert dispute.data_hash is not None
        assert len(dispute.data_hash) == 32

    def test_add_multiple_disputes(self, processor):
        """Test adding multiple disputes."""
        disputes = []
        for i in range(5):
            dispute = processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000000000000000 * (i + 1),
            )
            disputes.append(dispute)

        assert len(disputes) == 5
        assert disputes[0].dispute_id == 1
        assert disputes[4].dispute_id == 5

    def test_batch_disputes(self, processor):
        """Test batch dispute submission."""
        batch_data = [(random_hash(), random_hash(), random_hash(), 1000000) for _ in range(5)]

        disputes = processor.add_disputes_batch(batch_data)

        assert len(disputes) == 5
        assert processor.get_pending_dispute_count() == 5

    def test_should_create_batch_size_threshold(self, processor):
        """Test batch creation based on size threshold."""
        # Add disputes below threshold
        for _ in range(2):
            processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        assert not processor.should_create_batch()

        # Add one more to meet threshold
        processor.add_dispute(
            initiator_hash=random_hash(),
            counterparty_hash=random_hash(),
            evidence_root=random_hash(),
            stake_amount=1000000,
        )

        assert processor.should_create_batch()

    def test_process_batch(self, processor):
        """Test batch processing."""
        # Add enough disputes
        for _ in range(5):
            processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        # Create and process batch
        result = processor.create_and_process_batch()

        assert result is not None
        assert result.success
        assert result.disputes_processed == 5
        assert len(result.state_root) == 32
        assert len(result.dispute_root) == 32
        assert result.processing_time_ms > 0

    def test_batch_lifecycle(self, processor):
        """Test complete batch lifecycle."""
        # Add disputes
        for _ in range(5):
            processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        # Process
        result = processor.create_and_process_batch()
        assert result.success

        # Get batch
        batch = processor.get_batch(result.batch_id)
        assert batch is not None
        assert batch.status == BatchStatus.COMMITTED

        # Finalize (would normally wait for challenge period)
        processor.config.challenge_period_seconds = 0  # Skip for test
        time.sleep(0.1)
        success = processor.finalize_batch(result.batch_id)
        assert success

        batch = processor.get_batch(result.batch_id)
        assert batch.status == BatchStatus.FINALIZED

    def test_batch_challenge(self, processor):
        """Test batch challenge mechanism."""
        # Add and process disputes
        for _ in range(5):
            processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        result = processor.create_and_process_batch()
        assert result.success

        # Challenge the batch
        success = processor.challenge_batch(result.batch_id)
        assert success

        batch = processor.get_batch(result.batch_id)
        assert batch.status == BatchStatus.CHALLENGED

    def test_batch_rejection(self, processor):
        """Test batch rejection (fraud proof success)."""
        # Add and process disputes
        for _ in range(5):
            processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        processor.get_pending_dispute_count()
        result = processor.create_and_process_batch()

        # Challenge and reject
        processor.challenge_batch(result.batch_id)
        success = processor.reject_batch(result.batch_id)
        assert success

        batch = processor.get_batch(result.batch_id)
        assert batch.status == BatchStatus.REJECTED

        # Disputes should be returned to pending
        assert processor.get_pending_dispute_count() == 5

    def test_merkle_proof_generation(self, processor):
        """Test Merkle proof generation."""
        # Add disputes
        dispute_ids = []
        for _ in range(5):
            dispute = processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )
            dispute_ids.append(dispute.dispute_id)

        result = processor.create_and_process_batch()

        # Get proof for first dispute
        proof = processor.get_merkle_proof(result.batch_id, dispute_ids[0])
        assert proof is not None
        assert len(proof) > 0

    def test_stats(self, processor):
        """Test processor statistics."""
        # Add and process some disputes
        for _ in range(10):
            processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        processor.create_and_process_batch()

        stats = processor.get_stats()

        assert "current_state_root" in stats
        assert "total_disputes_processed" in stats
        assert "total_batches_processed" in stats
        assert stats["total_batches_processed"] == 1

    def test_callback_on_batch_committed(self, processor):
        """Test callback when batch is committed."""
        callback_called = [False]
        committed_batch = [None]

        def on_commit(batch):
            callback_called[0] = True
            committed_batch[0] = batch

        processor.set_on_batch_committed(on_commit)

        for _ in range(5):
            processor.add_dispute(
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        processor.create_and_process_batch()

        assert callback_called[0]
        assert committed_batch[0] is not None

    def test_create_batch_processor_factory(self):
        """Test batch processor factory function."""
        processor = create_batch_processor(
            min_batch_size=5,
            max_batch_size=50,
            batch_interval_seconds=30.0,
        )

        assert processor.config.min_batch_size == 5
        assert processor.config.max_batch_size == 50
        assert processor.config.batch_interval_seconds == 30.0


# =============================================================================
# DisputeSequencer Tests
# =============================================================================


class TestDisputeSequencer:
    """Tests for the dispute sequencer."""

    @pytest.fixture
    def sequencer(self):
        """Create a sequencer with test configuration."""
        config = SequencerConfig(
            max_transactions_per_block=100,
            block_time_ms=10,
            batch_commit_interval=5,
        )
        return DisputeSequencer(config)

    def test_sequencer_lifecycle(self, sequencer):
        """Test sequencer start/stop lifecycle."""
        assert sequencer.status == SequencerStatus.STARTING

        sequencer.start()
        assert sequencer.status == SequencerStatus.RUNNING

        sequencer.pause()
        assert sequencer.status == SequencerStatus.PAUSED

        sequencer.resume()
        assert sequencer.status == SequencerStatus.RUNNING

        sequencer.stop()
        assert sequencer.status == SequencerStatus.STOPPED

    def test_submit_transaction(self, sequencer):
        """Test transaction submission."""
        sequencer.start()

        tx = Transaction(
            tx_id=secrets.token_hex(16),
            tx_type=TransactionType.DISPUTE_SUBMIT,
            sender="0x" + secrets.token_hex(20),
            payload=random_hash() * 4,
            timestamp=datetime.now(timezone.utc),
        )

        accepted = sequencer.submit_transaction(tx)
        assert accepted
        assert sequencer.get_pending_count() == 1

    def test_submit_dispute(self, sequencer):
        """Test dispute submission helper."""
        sequencer.start()

        tx_id = sequencer.submit_dispute(
            sender="0x" + secrets.token_hex(20),
            initiator_hash=random_hash(),
            counterparty_hash=random_hash(),
            evidence_root=random_hash(),
            stake_amount=1000000000000000000,
        )

        assert tx_id is not None
        assert sequencer.get_pending_count() == 1

    def test_submit_resolution(self, sequencer):
        """Test resolution submission."""
        sequencer.start()

        tx_id = sequencer.submit_resolution(
            sender="0x" + secrets.token_hex(20),
            dispute_id=1,
            resolution=random_hash(),
        )

        assert tx_id is not None
        assert sequencer.get_pending_count() == 1

    def test_produce_block(self, sequencer):
        """Test block production."""
        sequencer.start()

        # Submit some transactions
        for _ in range(5):
            sequencer.submit_dispute(
                sender="0x" + secrets.token_hex(20),
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        # Produce block
        transition = sequencer.produce_block()

        assert transition is not None
        assert transition.transition_id == 1
        assert len(transition.transactions) == 5
        assert len(transition.new_state_root) == 32

    def test_transaction_ordering(self, sequencer):
        """Test that transactions are ordered by priority."""
        sequencer.start()

        # Submit low priority
        low_tx = Transaction(
            tx_id="low",
            tx_type=TransactionType.DISPUTE_SUBMIT,
            sender="sender1",
            payload=random_hash(),
            timestamp=datetime.now(timezone.utc),
            priority=1,
        )
        sequencer.submit_transaction(low_tx)

        # Submit high priority
        high_tx = Transaction(
            tx_id="high",
            tx_type=TransactionType.DISPUTE_RESOLVE,
            sender="sender2",
            payload=random_hash(),
            timestamp=datetime.now(timezone.utc),
            priority=10,
        )
        sequencer.submit_transaction(high_tx)

        # Produce block
        transition = sequencer.produce_block()

        # High priority should be processed first
        assert transition.transactions[0] == "high"
        assert transition.transactions[1] == "low"

    def test_multiple_blocks(self, sequencer):
        """Test producing multiple blocks."""
        sequencer.start()

        for block_num in range(3):
            for _ in range(5):
                sequencer.submit_dispute(
                    sender="0x" + secrets.token_hex(20),
                    initiator_hash=random_hash(),
                    counterparty_hash=random_hash(),
                    evidence_root=random_hash(),
                    stake_amount=1000000,
                )

            transition = sequencer.produce_block()
            assert transition.transition_id == block_num + 1

        stats = sequencer.get_stats()
        assert stats["total_blocks"] == 3
        assert stats["total_transactions"] == 15

    def test_state_root_changes(self, sequencer):
        """Test that state root changes with each block."""
        sequencer.start()

        initial_root = sequencer.get_current_state_root()
        previous_root = initial_root

        for _ in range(3):
            sequencer.submit_dispute(
                sender="0x" + secrets.token_hex(20),
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

            sequencer.produce_block()
            current_root = sequencer.get_current_state_root()

            # Root should change
            assert current_root != previous_root
            previous_root = current_root

    def test_callback_on_block_produced(self, sequencer):
        """Test callback when block is produced."""
        callback_called = [False]
        produced_transition = [None]

        def on_block(transition):
            callback_called[0] = True
            produced_transition[0] = transition

        sequencer.set_on_block_produced(on_block)
        sequencer.start()

        sequencer.submit_dispute(
            sender="0x" + secrets.token_hex(20),
            initiator_hash=random_hash(),
            counterparty_hash=random_hash(),
            evidence_root=random_hash(),
            stake_amount=1000000,
        )

        sequencer.produce_block()

        assert callback_called[0]
        assert produced_transition[0] is not None

    def test_batch_commit_integration(self, sequencer):
        """Test integration with batch processor."""
        sequencer.config.batch_commit_interval = 2  # Every 2 blocks
        sequencer.config.max_transactions_per_block = 5  # Force multiple blocks
        sequencer.start()

        batch_results = []

        def on_batch(result):
            batch_results.append(result)

        sequencer.set_on_batch_committed(on_batch)

        # Submit and produce in rounds to create multiple blocks
        for _ in range(3):
            for _ in range(5):
                sequencer.submit_dispute(
                    sender="0x" + secrets.token_hex(20),
                    initiator_hash=random_hash(),
                    counterparty_hash=random_hash(),
                    evidence_root=random_hash(),
                    stake_amount=1000000,
                )
            sequencer.produce_block()

        # Should have at least 1 batch commit (after 2 or more blocks)
        assert len(batch_results) >= 1

    def test_rejected_when_stopped(self, sequencer):
        """Test that transactions are rejected when sequencer is stopped."""
        # Don't start sequencer
        assert sequencer.status == SequencerStatus.STARTING

        tx_id = sequencer.submit_dispute(
            sender="0x" + secrets.token_hex(20),
            initiator_hash=random_hash(),
            counterparty_hash=random_hash(),
            evidence_root=random_hash(),
            stake_amount=1000000,
        )

        assert tx_id is None

    def test_stats(self, sequencer):
        """Test sequencer statistics."""
        sequencer.start()

        for _ in range(5):
            sequencer.submit_dispute(
                sender="0x" + secrets.token_hex(20),
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        sequencer.produce_block()

        stats = sequencer.get_stats()

        assert stats["status"] == "running"
        assert stats["total_transactions"] == 5
        assert stats["total_blocks"] == 1
        assert "batch_processor_stats" in stats

    def test_create_sequencer_factory(self):
        """Test sequencer factory function."""
        sequencer = create_sequencer(
            sequencer_id="test-sequencer",
            block_time_ms=50,
            max_transactions_per_block=500,
            batch_commit_interval=50,
        )

        assert sequencer.config.sequencer_id == "test-sequencer"
        assert sequencer.config.block_time_ms == 50
        assert sequencer.config.max_transactions_per_block == 500
        assert sequencer.config.batch_commit_interval == 50


# =============================================================================
# Integration Tests
# =============================================================================


class TestL3Integration:
    """Integration tests for L3 components."""

    def test_full_dispute_flow(self):
        """Test complete dispute flow through L3."""
        # Create sequencer with batch processor
        batch_config = BatchConfig(min_batch_size=3, max_batch_size=10)
        batch_processor = BatchProcessor(batch_config)

        seq_config = SequencerConfig(
            max_transactions_per_block=4,  # Small blocks to spread transactions
            batch_commit_interval=2,
        )
        sequencer = DisputeSequencer(seq_config, batch_processor)
        sequencer.start()

        # Submit disputes and produce blocks in rounds
        dispute_tx_ids = []
        blocks_produced = 0
        for i in range(12):  # 12 disputes across 3 blocks
            tx_id = sequencer.submit_dispute(
                sender=f"sender_{i}",
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000 * (i + 1),
            )
            dispute_tx_ids.append(tx_id)

            # Produce a block every 4 transactions
            if (i + 1) % 4 == 0:
                transition = sequencer.produce_block()
                if transition is not None:
                    blocks_produced += 1

        # Verify we produced at least 1 block
        assert blocks_produced >= 1

        # Check stats
        seq_stats = sequencer.get_stats()
        batch_stats = batch_processor.get_stats()

        assert seq_stats["total_transactions"] == 12
        assert seq_stats["total_blocks"] >= 1
        assert batch_stats["total_disputes_processed"] > 0

    def test_high_throughput(self):
        """Test high-throughput processing."""
        processor = create_batch_processor(
            min_batch_size=100,
            max_batch_size=1000,
        )

        sequencer = create_sequencer(
            max_transactions_per_block=1000,
            batch_commit_interval=10,
        )
        sequencer.batch_processor = processor
        sequencer.start()

        # Submit 1000 transactions
        start_time = time.time()

        for i in range(1000):
            sequencer.submit_dispute(
                sender=f"sender_{i % 100}",
                initiator_hash=random_hash(),
                counterparty_hash=random_hash(),
                evidence_root=random_hash(),
                stake_amount=1000000,
            )

        time.time() - start_time

        # Process all
        while sequencer.get_pending_count() > 0:
            sequencer.produce_block()

        process_time = time.time() - start_time

        stats = sequencer.get_stats()
        assert stats["total_transactions"] == 1000

        # Should be reasonably fast (< 5 seconds for 1000 txs in-memory)
        assert process_time < 5.0


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_batch_processing(self):
        """Test processing with no disputes."""
        processor = create_batch_processor()
        result = processor.create_and_process_batch()
        assert result is None

    def test_single_dispute_batch(self):
        """Test batch with single dispute."""
        processor = create_batch_processor(min_batch_size=1)

        processor.add_dispute(
            initiator_hash=random_hash(),
            counterparty_hash=random_hash(),
            evidence_root=random_hash(),
            stake_amount=1000000,
        )

        result = processor.create_and_process_batch()
        assert result is not None
        assert result.success
        assert result.disputes_processed == 1

    def test_invalid_batch_id(self):
        """Test operations on invalid batch ID."""
        processor = create_batch_processor()

        batch = processor.get_batch(999)
        assert batch is None

        result = processor.process_batch(999)
        assert not result.success
        assert result.error == "Batch not found"

    def test_empty_block_production(self):
        """Test block production with no pending transactions."""
        sequencer = create_sequencer()
        sequencer.start()

        transition = sequencer.produce_block()
        assert transition is None

    def test_duplicate_nonce_rejection(self):
        """Test that duplicate nonces are handled."""
        sequencer = create_sequencer()
        sequencer.start()

        sender = "0x" + secrets.token_hex(20)

        # First transaction
        tx1 = Transaction(
            tx_id="tx1",
            tx_type=TransactionType.DISPUTE_SUBMIT,
            sender=sender,
            payload=random_hash(),
            timestamp=datetime.now(timezone.utc),
            nonce=0,
        )
        assert sequencer.submit_transaction(tx1)

        # Process to update nonce
        sequencer.produce_block()

        # Try with old nonce
        tx2 = Transaction(
            tx_id="tx2",
            tx_type=TransactionType.DISPUTE_SUBMIT,
            sender=sender,
            payload=random_hash(),
            timestamp=datetime.now(timezone.utc),
            nonce=0,  # Should be rejected
        )
        assert not sequencer.submit_transaction(tx2)
