# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
High-Throughput Batch Dispute Processor.

Provides efficient batch processing of disputes for L3 rollup:
- Collects disputes into batches
- Computes Merkle roots for state commitments
- Manages batch lifecycle (pending -> processing -> committed)
- Handles batch submission to L2

Throughput targets:
- 1000+ disputes per second on L3
- Sub-second finality for L3 state
- Batched L2 commitments every 100 blocks
"""

import hashlib
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from eth_utils import keccak


class BatchStatus(Enum):
    """Status of a batch."""

    PENDING = "pending"          # Collecting disputes
    FULL = "full"                # Ready for processing
    PROCESSING = "processing"    # Being processed
    COMMITTED = "committed"      # State root submitted to L2
    CHALLENGED = "challenged"    # Under fraud proof challenge
    FINALIZED = "finalized"      # Finalized on L2
    REJECTED = "rejected"        # Fraud proof succeeded


@dataclass
class ProcessedDispute:
    """A dispute processed in a batch."""

    dispute_id: int
    initiator_hash: bytes
    counterparty_hash: bytes
    evidence_root: bytes
    stake_amount: int  # wei
    created_at: datetime
    resolution: Optional[bytes] = None
    resolved_at: Optional[datetime] = None
    data_hash: bytes = field(default_factory=bytes)

    def __post_init__(self):
        """Compute data hash if not provided."""
        if not self.data_hash:
            self.data_hash = keccak(
                self.dispute_id.to_bytes(32, "big")
                + self.initiator_hash
                + self.counterparty_hash
                + self.evidence_root
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dispute_id": self.dispute_id,
            "initiator_hash": self.initiator_hash.hex(),
            "counterparty_hash": self.counterparty_hash.hex(),
            "evidence_root": self.evidence_root.hex(),
            "stake_amount": self.stake_amount,
            "created_at": self.created_at.isoformat(),
            "resolution": self.resolution.hex() if self.resolution else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "data_hash": self.data_hash.hex(),
        }


@dataclass
class Batch:
    """A batch of disputes for L2 commitment."""

    batch_id: int
    disputes: List[ProcessedDispute] = field(default_factory=list)
    state_root: bytes = field(default_factory=bytes)
    dispute_root: bytes = field(default_factory=bytes)
    prev_state_root: bytes = field(default_factory=bytes)
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    finalized_at: Optional[datetime] = None
    submitter: Optional[str] = None  # Sequencer address
    l2_tx_hash: Optional[str] = None

    @property
    def dispute_count(self) -> int:
        """Number of disputes in batch."""
        return len(self.disputes)

    @property
    def first_dispute_id(self) -> Optional[int]:
        """First dispute ID in batch."""
        return self.disputes[0].dispute_id if self.disputes else None

    @property
    def last_dispute_id(self) -> Optional[int]:
        """Last dispute ID in batch."""
        return self.disputes[-1].dispute_id if self.disputes else None

    @property
    def total_stake(self) -> int:
        """Total stake in batch."""
        return sum(d.stake_amount for d in self.disputes)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "dispute_count": self.dispute_count,
            "first_dispute_id": self.first_dispute_id,
            "last_dispute_id": self.last_dispute_id,
            "total_stake": self.total_stake,
            "state_root": self.state_root.hex() if self.state_root else None,
            "dispute_root": self.dispute_root.hex() if self.dispute_root else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
        }


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    min_batch_size: int = 10          # Minimum disputes per batch
    max_batch_size: int = 1000        # Maximum disputes per batch
    batch_interval_seconds: float = 60.0  # Max time before forcing batch
    challenge_period_seconds: float = 604800.0  # 7 days
    max_pending_batches: int = 100    # Maximum batches awaiting finalization
    compression_enabled: bool = True   # Use calldata compression
    parallel_processing: bool = True   # Process disputes in parallel


@dataclass
class BatchResult:
    """Result of batch processing."""

    batch_id: int
    success: bool
    state_root: bytes
    dispute_root: bytes
    disputes_processed: int
    processing_time_ms: float
    gas_estimate: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "success": self.success,
            "state_root": self.state_root.hex(),
            "dispute_root": self.dispute_root.hex(),
            "disputes_processed": self.disputes_processed,
            "processing_time_ms": round(self.processing_time_ms, 2),
            "gas_estimate": self.gas_estimate,
            "error": self.error,
        }


class BatchProcessor:
    """
    High-throughput batch dispute processor.

    Manages the lifecycle of dispute batches from collection
    through L2 commitment and finalization.
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Initialize the batch processor.

        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()

        # State
        self._next_batch_id = 1
        self._next_dispute_id = 1
        self._current_state_root = bytes(32)  # Genesis state

        # Pending disputes queue
        self._pending_disputes: deque[ProcessedDispute] = deque()

        # Batches by status
        self._batches: Dict[int, Batch] = {}
        self._pending_batches: List[int] = []
        self._committed_batches: List[int] = []
        self._finalized_batches: List[int] = []

        # Processing metrics
        self._total_disputes_processed = 0
        self._total_batches_processed = 0
        self._last_batch_time = time.time()

        # Callbacks
        self._on_batch_ready: Optional[Callable[[Batch], None]] = None
        self._on_batch_committed: Optional[Callable[[Batch], None]] = None

    def add_dispute(
        self,
        initiator_hash: bytes,
        counterparty_hash: bytes,
        evidence_root: bytes,
        stake_amount: int,
    ) -> ProcessedDispute:
        """
        Add a dispute to the pending queue.

        Args:
            initiator_hash: Privacy-preserving initiator identifier
            counterparty_hash: Privacy-preserving counterparty identifier
            evidence_root: Merkle root of evidence
            stake_amount: Stake amount in wei

        Returns:
            ProcessedDispute object
        """
        dispute_id = self._next_dispute_id
        self._next_dispute_id += 1

        dispute = ProcessedDispute(
            dispute_id=dispute_id,
            initiator_hash=initiator_hash,
            counterparty_hash=counterparty_hash,
            evidence_root=evidence_root,
            stake_amount=stake_amount,
            created_at=datetime.now(timezone.utc),
        )

        self._pending_disputes.append(dispute)

        # Check if we should create a batch
        if len(self._pending_disputes) >= self.config.max_batch_size:
            self._create_batch()

        return dispute

    def add_disputes_batch(
        self,
        disputes: List[Tuple[bytes, bytes, bytes, int]],
    ) -> List[ProcessedDispute]:
        """
        Add multiple disputes efficiently.

        Args:
            disputes: List of (initiator_hash, counterparty_hash, evidence_root, stake)

        Returns:
            List of ProcessedDispute objects
        """
        result = []
        for initiator, counterparty, evidence, stake in disputes:
            dispute = self.add_dispute(initiator, counterparty, evidence, stake)
            result.append(dispute)
        return result

    def should_create_batch(self) -> bool:
        """Check if a new batch should be created."""
        if len(self._pending_disputes) == 0:
            return False

        # Size threshold
        if len(self._pending_disputes) >= self.config.min_batch_size:
            return True

        # Time threshold
        elapsed = time.time() - self._last_batch_time
        if elapsed >= self.config.batch_interval_seconds and len(self._pending_disputes) > 0:
            return True

        return False

    def _create_batch(self) -> Optional[Batch]:
        """Create a new batch from pending disputes."""
        if len(self._pending_disputes) == 0:
            return None

        batch_size = min(len(self._pending_disputes), self.config.max_batch_size)

        # Collect disputes for batch
        disputes = []
        for _ in range(batch_size):
            if self._pending_disputes:
                disputes.append(self._pending_disputes.popleft())

        batch_id = self._next_batch_id
        self._next_batch_id += 1

        batch = Batch(
            batch_id=batch_id,
            disputes=disputes,
            prev_state_root=self._current_state_root,
            status=BatchStatus.FULL,
        )

        self._batches[batch_id] = batch
        self._pending_batches.append(batch_id)
        self._last_batch_time = time.time()

        return batch

    def process_batch(self, batch_id: int) -> BatchResult:
        """
        Process a batch and compute state roots.

        Args:
            batch_id: ID of batch to process

        Returns:
            BatchResult with state roots and metrics
        """
        start_time = time.time()

        if batch_id not in self._batches:
            return BatchResult(
                batch_id=batch_id,
                success=False,
                state_root=bytes(32),
                dispute_root=bytes(32),
                disputes_processed=0,
                processing_time_ms=0,
                gas_estimate=0,
                error="Batch not found",
            )

        batch = self._batches[batch_id]

        if batch.status not in (BatchStatus.FULL, BatchStatus.PENDING):
            return BatchResult(
                batch_id=batch_id,
                success=False,
                state_root=bytes(32),
                dispute_root=bytes(32),
                disputes_processed=0,
                processing_time_ms=0,
                gas_estimate=0,
                error=f"Invalid batch status: {batch.status.value}",
            )

        batch.status = BatchStatus.PROCESSING

        try:
            # Compute dispute Merkle root
            dispute_leaves = [d.data_hash for d in batch.disputes]
            dispute_root = self._compute_merkle_root(dispute_leaves)
            batch.dispute_root = dispute_root

            # Compute new state root
            state_root = keccak(
                batch.prev_state_root
                + dispute_root
                + int(time.time()).to_bytes(8, "big")
            )
            batch.state_root = state_root

            # Update current state
            self._current_state_root = state_root

            # Mark as committed (ready for L2 submission)
            batch.status = BatchStatus.COMMITTED
            batch.submitted_at = datetime.now(timezone.utc)

            # Move to committed list
            if batch_id in self._pending_batches:
                self._pending_batches.remove(batch_id)
            self._committed_batches.append(batch_id)

            # Update metrics
            self._total_disputes_processed += len(batch.disputes)
            self._total_batches_processed += 1

            processing_time = (time.time() - start_time) * 1000

            # Estimate gas (simplified)
            gas_estimate = 21000 + (len(batch.disputes) * 5000)

            # Trigger callback
            if self._on_batch_committed:
                self._on_batch_committed(batch)

            return BatchResult(
                batch_id=batch_id,
                success=True,
                state_root=state_root,
                dispute_root=dispute_root,
                disputes_processed=len(batch.disputes),
                processing_time_ms=processing_time,
                gas_estimate=gas_estimate,
            )

        except Exception as e:
            batch.status = BatchStatus.PENDING
            return BatchResult(
                batch_id=batch_id,
                success=False,
                state_root=bytes(32),
                dispute_root=bytes(32),
                disputes_processed=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                gas_estimate=0,
                error=str(e),
            )

    def process_pending_batches(self) -> List[BatchResult]:
        """Process all pending batches."""
        results = []
        for batch_id in list(self._pending_batches):
            result = self.process_batch(batch_id)
            results.append(result)
        return results

    def create_and_process_batch(self) -> Optional[BatchResult]:
        """Create a batch from pending disputes and process it."""
        # First try to create a new batch if needed
        if self.should_create_batch():
            batch = self._create_batch()
            if batch:
                return self.process_batch(batch.batch_id)

        # If no new batch created, process any existing pending batch
        if self._pending_batches:
            return self.process_batch(self._pending_batches[0])

        return None

    def finalize_batch(self, batch_id: int) -> bool:
        """
        Finalize a batch after challenge period.

        Args:
            batch_id: ID of batch to finalize

        Returns:
            True if finalized successfully
        """
        if batch_id not in self._batches:
            return False

        batch = self._batches[batch_id]

        if batch.status not in (BatchStatus.COMMITTED,):
            return False

        # Check challenge period (simplified - in production, use block time)
        if batch.submitted_at:
            elapsed = (datetime.now(timezone.utc) - batch.submitted_at).total_seconds()
            if elapsed < self.config.challenge_period_seconds:
                return False

        batch.status = BatchStatus.FINALIZED
        batch.finalized_at = datetime.now(timezone.utc)

        if batch_id in self._committed_batches:
            self._committed_batches.remove(batch_id)
        self._finalized_batches.append(batch_id)

        return True

    def challenge_batch(self, batch_id: int) -> bool:
        """
        Mark a batch as challenged.

        Args:
            batch_id: ID of batch to challenge

        Returns:
            True if challenge accepted
        """
        if batch_id not in self._batches:
            return False

        batch = self._batches[batch_id]

        if batch.status not in (BatchStatus.COMMITTED,):
            return False

        batch.status = BatchStatus.CHALLENGED
        return True

    def reject_batch(self, batch_id: int) -> bool:
        """
        Reject a batch (fraud proof succeeded).

        Args:
            batch_id: ID of batch to reject

        Returns:
            True if rejected successfully
        """
        if batch_id not in self._batches:
            return False

        batch = self._batches[batch_id]

        if batch.status not in (BatchStatus.CHALLENGED,):
            return False

        batch.status = BatchStatus.REJECTED

        # Revert state to previous
        self._current_state_root = batch.prev_state_root

        # Return disputes to pending
        for dispute in batch.disputes:
            self._pending_disputes.appendleft(dispute)

        return True

    def get_batch(self, batch_id: int) -> Optional[Batch]:
        """Get a batch by ID."""
        return self._batches.get(batch_id)

    def get_pending_dispute_count(self) -> int:
        """Get count of pending disputes."""
        return len(self._pending_disputes)

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            "current_state_root": self._current_state_root.hex(),
            "pending_disputes": len(self._pending_disputes),
            "pending_batches": len(self._pending_batches),
            "committed_batches": len(self._committed_batches),
            "finalized_batches": len(self._finalized_batches),
            "total_disputes_processed": self._total_disputes_processed,
            "total_batches_processed": self._total_batches_processed,
            "next_batch_id": self._next_batch_id,
            "next_dispute_id": self._next_dispute_id,
        }

    def set_on_batch_ready(self, callback: Callable[[Batch], None]) -> None:
        """Set callback for when a batch is ready."""
        self._on_batch_ready = callback

    def set_on_batch_committed(self, callback: Callable[[Batch], None]) -> None:
        """Set callback for when a batch is committed."""
        self._on_batch_committed = callback

    def _compute_merkle_root(self, leaves: List[bytes]) -> bytes:
        """Compute Merkle root from leaves."""
        if not leaves:
            return bytes(32)

        if len(leaves) == 1:
            return leaves[0]

        # Build tree
        current_level = list(leaves)
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    combined = keccak(current_level[i] + current_level[i + 1])
                else:
                    combined = current_level[i]
                next_level.append(combined)
            current_level = next_level

        return current_level[0]

    def get_merkle_proof(
        self,
        batch_id: int,
        dispute_id: int,
    ) -> Optional[List[bytes]]:
        """
        Get Merkle proof for a dispute in a batch.

        Args:
            batch_id: Batch containing the dispute
            dispute_id: Dispute to prove

        Returns:
            List of proof nodes or None if not found
        """
        batch = self.get_batch(batch_id)
        if not batch:
            return None

        # Find dispute index
        index = None
        for i, d in enumerate(batch.disputes):
            if d.dispute_id == dispute_id:
                index = i
                break

        if index is None:
            return None

        # Build proof
        leaves = [d.data_hash for d in batch.disputes]
        return self._compute_merkle_proof(leaves, index)

    def _compute_merkle_proof(
        self,
        leaves: List[bytes],
        index: int,
    ) -> List[bytes]:
        """Compute Merkle proof for element at index."""
        proof = []
        current_level = list(leaves)

        while len(current_level) > 1:
            next_level = []
            sibling_index = index ^ 1  # XOR to get sibling

            if sibling_index < len(current_level):
                proof.append(current_level[sibling_index])

            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    combined = keccak(current_level[i] + current_level[i + 1])
                else:
                    combined = current_level[i]
                next_level.append(combined)

            current_level = next_level
            index = index // 2

        return proof


def create_batch_processor(
    min_batch_size: int = 10,
    max_batch_size: int = 1000,
    batch_interval_seconds: float = 60.0,
) -> BatchProcessor:
    """
    Create a configured batch processor.

    Args:
        min_batch_size: Minimum disputes per batch
        max_batch_size: Maximum disputes per batch
        batch_interval_seconds: Max time before forcing batch

    Returns:
        Configured BatchProcessor
    """
    config = BatchConfig(
        min_batch_size=min_batch_size,
        max_batch_size=max_batch_size,
        batch_interval_seconds=batch_interval_seconds,
    )
    return BatchProcessor(config)
