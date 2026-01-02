# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
L3 Dispute Sequencer.

Provides transaction ordering and state transition management for the L3 rollup:
- Orders incoming transactions
- Validates state transitions
- Manages sequencer rotation
- Handles L2 bridge communication

The sequencer is responsible for:
1. Receiving transactions from users
2. Ordering them deterministically
3. Executing state transitions
4. Committing batches to L2
"""

import asyncio
import hashlib
import heapq
import secrets
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from eth_utils import keccak

from .batch_processor import BatchProcessor, BatchConfig, BatchResult


class TransactionType(Enum):
    """Types of L3 transactions."""

    DISPUTE_SUBMIT = "dispute_submit"
    DISPUTE_RESOLVE = "dispute_resolve"
    EVIDENCE_SUBMIT = "evidence_submit"
    VOTE_CAST = "vote_cast"
    STAKE_DEPOSIT = "stake_deposit"
    STAKE_WITHDRAW = "stake_withdraw"
    BATCH_COMMIT = "batch_commit"


class SequencerStatus(Enum):
    """Sequencer operational status."""

    STARTING = "starting"
    RUNNING = "running"
    SYNCING = "syncing"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Transaction:
    """An L3 transaction."""

    tx_id: str
    tx_type: TransactionType
    sender: str  # Sender address (can be hashed)
    payload: bytes  # Transaction data
    timestamp: datetime
    priority: int = 0  # Higher = earlier processing
    gas_price: int = 0  # For fee market ordering
    nonce: int = 0  # Sender nonce
    signature: Optional[bytes] = None
    processed: bool = False
    result: Optional[bytes] = None
    error: Optional[str] = None

    def __lt__(self, other: "Transaction") -> bool:
        """Compare for priority queue (higher priority first, then by timestamp)."""
        if self.priority != other.priority:
            return self.priority > other.priority
        if self.gas_price != other.gas_price:
            return self.gas_price > other.gas_price
        return self.timestamp < other.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type.value,
            "sender": self.sender,
            "payload_hash": hashlib.sha256(self.payload).hexdigest()[:16],
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "gas_price": self.gas_price,
            "nonce": self.nonce,
            "processed": self.processed,
            "error": self.error,
        }


@dataclass
class StateTransition:
    """A state transition in the L3 chain."""

    transition_id: int
    prev_state_root: bytes
    new_state_root: bytes
    transactions: List[str]  # Transaction IDs
    timestamp: datetime
    sequencer: str
    signature: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transition_id": self.transition_id,
            "prev_state_root": self.prev_state_root.hex(),
            "new_state_root": self.new_state_root.hex(),
            "transaction_count": len(self.transactions),
            "timestamp": self.timestamp.isoformat(),
            "sequencer": self.sequencer,
        }


@dataclass
class SequencerConfig:
    """Configuration for the sequencer."""

    sequencer_id: str = ""
    max_transactions_per_block: int = 1000
    block_time_ms: int = 100  # Target 100ms blocks for sub-second finality
    max_pending_transactions: int = 10000
    batch_commit_interval: int = 100  # Blocks between L2 commits
    priority_fee_threshold: int = 0  # Min priority fee
    max_gas_per_block: int = 30_000_000
    enable_mempool: bool = True
    enable_priority_queue: bool = True


class DisputeSequencer:
    """
    L3 Dispute Sequencer.

    Orders transactions and manages state transitions for the L3 rollup.
    Provides sub-second finality on L3 with periodic L2 commitments.
    """

    def __init__(
        self,
        config: Optional[SequencerConfig] = None,
        batch_processor: Optional[BatchProcessor] = None,
    ):
        """
        Initialize the sequencer.

        Args:
            config: Sequencer configuration
            batch_processor: Batch processor for L2 commits
        """
        self.config = config or SequencerConfig()
        if not self.config.sequencer_id:
            self.config.sequencer_id = secrets.token_hex(16)

        self.batch_processor = batch_processor or BatchProcessor()

        # State
        self._status = SequencerStatus.STARTING
        self._current_state_root = bytes(32)
        self._current_block = 0
        self._next_transition_id = 1

        # Transaction management
        self._pending_transactions: List[Transaction] = []  # Priority queue
        self._processed_transactions: Dict[str, Transaction] = {}
        self._sender_nonces: Dict[str, int] = {}

        # State history
        self._transitions: Dict[int, StateTransition] = {}
        self._state_roots: List[bytes] = [bytes(32)]  # Genesis

        # Blocks
        self._blocks_since_commit = 0

        # Metrics
        self._total_transactions = 0
        self._total_blocks = 0
        self._start_time: Optional[float] = None

        # Callbacks
        self._on_block_produced: Optional[Callable[[StateTransition], None]] = None
        self._on_batch_committed: Optional[Callable[[BatchResult], None]] = None

    def start(self) -> None:
        """Start the sequencer."""
        self._status = SequencerStatus.RUNNING
        self._start_time = time.time()

    def stop(self) -> None:
        """Stop the sequencer."""
        self._status = SequencerStatus.STOPPED

    def pause(self) -> None:
        """Pause the sequencer."""
        self._status = SequencerStatus.PAUSED

    def resume(self) -> None:
        """Resume the sequencer."""
        if self._status == SequencerStatus.PAUSED:
            self._status = SequencerStatus.RUNNING

    @property
    def status(self) -> SequencerStatus:
        """Get current sequencer status."""
        return self._status

    def submit_transaction(self, tx: Transaction) -> bool:
        """
        Submit a transaction for sequencing.

        Args:
            tx: Transaction to submit

        Returns:
            True if accepted into mempool
        """
        if self._status != SequencerStatus.RUNNING:
            return False

        if len(self._pending_transactions) >= self.config.max_pending_transactions:
            return False

        # Validate nonce
        sender_nonce = self._sender_nonces.get(tx.sender, 0)
        if tx.nonce < sender_nonce:
            tx.error = "Nonce too low"
            return False

        # Add to priority queue
        heapq.heappush(self._pending_transactions, tx)
        return True

    def submit_dispute(
        self,
        sender: str,
        initiator_hash: bytes,
        counterparty_hash: bytes,
        evidence_root: bytes,
        stake_amount: int,
    ) -> Optional[str]:
        """
        Submit a dispute transaction.

        Args:
            sender: Sender identifier
            initiator_hash: Privacy-preserving initiator
            counterparty_hash: Privacy-preserving counterparty
            evidence_root: Merkle root of evidence
            stake_amount: Stake amount in wei

        Returns:
            Transaction ID or None if rejected
        """
        payload = (
            initiator_hash + counterparty_hash + evidence_root + stake_amount.to_bytes(32, "big")
        )

        tx = Transaction(
            tx_id=secrets.token_hex(16),
            tx_type=TransactionType.DISPUTE_SUBMIT,
            sender=sender,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            nonce=self._sender_nonces.get(sender, 0),
        )

        if self.submit_transaction(tx):
            return tx.tx_id
        return None

    def submit_resolution(
        self,
        sender: str,
        dispute_id: int,
        resolution: bytes,
    ) -> Optional[str]:
        """
        Submit a dispute resolution transaction.

        Args:
            sender: Sequencer/resolver identifier
            dispute_id: ID of dispute to resolve
            resolution: Resolution data

        Returns:
            Transaction ID or None if rejected
        """
        payload = dispute_id.to_bytes(32, "big") + resolution

        tx = Transaction(
            tx_id=secrets.token_hex(16),
            tx_type=TransactionType.DISPUTE_RESOLVE,
            sender=sender,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            priority=10,  # Higher priority for resolutions
            nonce=self._sender_nonces.get(sender, 0),
        )

        if self.submit_transaction(tx):
            return tx.tx_id
        return None

    def produce_block(self) -> Optional[StateTransition]:
        """
        Produce a new L3 block.

        Processes pending transactions and creates a state transition.

        Returns:
            StateTransition or None if no transactions
        """
        if self._status != SequencerStatus.RUNNING:
            return None

        if not self._pending_transactions:
            return None

        # Collect transactions for this block
        block_txs: List[Transaction] = []
        total_gas = 0

        while (
            self._pending_transactions
            and len(block_txs) < self.config.max_transactions_per_block
            and total_gas < self.config.max_gas_per_block
        ):
            tx = heapq.heappop(self._pending_transactions)

            # Estimate gas (simplified)
            tx_gas = self._estimate_gas(tx)
            if total_gas + tx_gas > self.config.max_gas_per_block:
                # Put back and stop
                heapq.heappush(self._pending_transactions, tx)
                break

            block_txs.append(tx)
            total_gas += tx_gas

        if not block_txs:
            return None

        # Process transactions
        processed_ids = []
        for tx in block_txs:
            self._process_transaction(tx)
            processed_ids.append(tx.tx_id)
            self._processed_transactions[tx.tx_id] = tx
            self._total_transactions += 1

            # Update nonce
            self._sender_nonces[tx.sender] = tx.nonce + 1

        # Create state transition
        prev_root = self._current_state_root
        new_root = self._compute_new_state_root(block_txs)

        transition = StateTransition(
            transition_id=self._next_transition_id,
            prev_state_root=prev_root,
            new_state_root=new_root,
            transactions=processed_ids,
            timestamp=datetime.now(timezone.utc),
            sequencer=self.config.sequencer_id,
        )

        self._next_transition_id += 1
        self._current_state_root = new_root
        self._state_roots.append(new_root)
        self._transitions[transition.transition_id] = transition
        self._current_block += 1
        self._total_blocks += 1
        self._blocks_since_commit += 1

        # Check if we should commit to L2
        if self._blocks_since_commit >= self.config.batch_commit_interval:
            self._commit_batch()

        # Trigger callback
        if self._on_block_produced:
            self._on_block_produced(transition)

        return transition

    def _process_transaction(self, tx: Transaction) -> None:
        """Process a single transaction."""
        try:
            if tx.tx_type == TransactionType.DISPUTE_SUBMIT:
                self._process_dispute_submit(tx)
            elif tx.tx_type == TransactionType.DISPUTE_RESOLVE:
                self._process_dispute_resolve(tx)
            elif tx.tx_type == TransactionType.EVIDENCE_SUBMIT:
                self._process_evidence_submit(tx)
            elif tx.tx_type == TransactionType.VOTE_CAST:
                self._process_vote_cast(tx)
            else:
                tx.error = f"Unknown transaction type: {tx.tx_type}"

            tx.processed = True

        except Exception as e:
            tx.error = str(e)
            tx.processed = True

    def _process_dispute_submit(self, tx: Transaction) -> None:
        """Process a dispute submission."""
        if len(tx.payload) < 128:
            tx.error = "Invalid payload length"
            return

        initiator_hash = tx.payload[0:32]
        counterparty_hash = tx.payload[32:64]
        evidence_root = tx.payload[64:96]
        stake_amount = int.from_bytes(tx.payload[96:128], "big")

        # Add to batch processor
        dispute = self.batch_processor.add_dispute(
            initiator_hash=initiator_hash,
            counterparty_hash=counterparty_hash,
            evidence_root=evidence_root,
            stake_amount=stake_amount,
        )

        tx.result = dispute.dispute_id.to_bytes(32, "big")

    def _process_dispute_resolve(self, tx: Transaction) -> None:
        """Process a dispute resolution."""
        if len(tx.payload) < 64:
            tx.error = "Invalid payload length"
            return

        dispute_id = int.from_bytes(tx.payload[0:32], "big")
        resolution = tx.payload[32:]

        tx.result = resolution

    def _process_evidence_submit(self, tx: Transaction) -> None:
        """Process evidence submission."""
        tx.result = keccak(tx.payload)

    def _process_vote_cast(self, tx: Transaction) -> None:
        """Process a vote."""
        tx.result = b"\x01"  # Success

    def _compute_new_state_root(self, transactions: List[Transaction]) -> bytes:
        """Compute new state root from transactions."""
        # Hash all transaction results
        tx_hashes = []
        for tx in transactions:
            tx_hash = keccak(
                tx.tx_id.encode() + (tx.result or b"") + tx.timestamp.isoformat().encode()
            )
            tx_hashes.append(tx_hash)

        # Combine with previous state
        combined = self._current_state_root
        for h in tx_hashes:
            combined = keccak(combined + h)

        return combined

    def _estimate_gas(self, tx: Transaction) -> int:
        """Estimate gas for a transaction."""
        base_gas = 21000

        if tx.tx_type == TransactionType.DISPUTE_SUBMIT:
            return base_gas + 50000
        elif tx.tx_type == TransactionType.DISPUTE_RESOLVE:
            return base_gas + 30000
        elif tx.tx_type == TransactionType.EVIDENCE_SUBMIT:
            return base_gas + 20000 + len(tx.payload) * 16
        else:
            return base_gas + 10000

    def _commit_batch(self) -> Optional[BatchResult]:
        """Commit pending disputes to L2 via batch processor."""
        result = self.batch_processor.create_and_process_batch()

        if result and result.success:
            self._blocks_since_commit = 0

            if self._on_batch_committed:
                self._on_batch_committed(result)

        return result

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        return self._processed_transactions.get(tx_id)

    def get_transition(self, transition_id: int) -> Optional[StateTransition]:
        """Get a state transition by ID."""
        return self._transitions.get(transition_id)

    def get_pending_count(self) -> int:
        """Get count of pending transactions."""
        return len(self._pending_transactions)

    def get_current_state_root(self) -> bytes:
        """Get current state root."""
        return self._current_state_root

    def get_stats(self) -> Dict[str, Any]:
        """Get sequencer statistics."""
        uptime = time.time() - self._start_time if self._start_time else 0
        tps = self._total_transactions / uptime if uptime > 0 else 0

        return {
            "sequencer_id": self.config.sequencer_id,
            "status": self._status.value,
            "current_block": self._current_block,
            "current_state_root": self._current_state_root.hex(),
            "pending_transactions": len(self._pending_transactions),
            "total_transactions": self._total_transactions,
            "total_blocks": self._total_blocks,
            "blocks_since_commit": self._blocks_since_commit,
            "uptime_seconds": round(uptime, 2),
            "transactions_per_second": round(tps, 2),
            "batch_processor_stats": self.batch_processor.get_stats(),
        }

    def set_on_block_produced(
        self,
        callback: Callable[[StateTransition], None],
    ) -> None:
        """Set callback for when a block is produced."""
        self._on_block_produced = callback

    def set_on_batch_committed(
        self,
        callback: Callable[[BatchResult], None],
    ) -> None:
        """Set callback for when a batch is committed to L2."""
        self._on_batch_committed = callback


def create_sequencer(
    sequencer_id: Optional[str] = None,
    block_time_ms: int = 100,
    max_transactions_per_block: int = 1000,
    batch_commit_interval: int = 100,
) -> DisputeSequencer:
    """
    Create a configured sequencer.

    Args:
        sequencer_id: Unique sequencer identifier
        block_time_ms: Target block time in milliseconds
        max_transactions_per_block: Max transactions per block
        batch_commit_interval: Blocks between L2 commits

    Returns:
        Configured DisputeSequencer
    """
    config = SequencerConfig(
        sequencer_id=sequencer_id or secrets.token_hex(16),
        block_time_ms=block_time_ms,
        max_transactions_per_block=max_transactions_per_block,
        batch_commit_interval=batch_commit_interval,
    )
    return DisputeSequencer(config)
