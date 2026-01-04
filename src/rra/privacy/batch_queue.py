# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Batch Queue Client for Inference Attack Prevention.

This module provides a Python client for the BatchQueue smart contract,
enabling privacy-preserving dispute submissions through batched transactions.

Key Features:
- Queue disputes for batched release (prevents timing analysis)
- Queue identity proofs for batched submission
- Monitor batch status and queue sizes
- Automatic dummy transaction padding for additional privacy

Privacy Benefits:
- Decouples submission timing from user's transaction
- Multiple disputes released in same block
- Dummy entries obscure real activity patterns
"""

import os
import time
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from eth_utils import keccak


class SubmissionStatus(str, Enum):
    """Status of a queued submission."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueuedDispute:
    """A dispute queued for batched submission."""

    queue_index: int
    initiator_hash: bytes
    counterparty_hash: bytes
    evidence_hash: bytes
    viewing_key_commitment: bytes
    ipfs_uri: str
    stake_amount: int  # in wei
    queued_at: datetime
    status: SubmissionStatus = SubmissionStatus.PENDING
    dispute_id: Optional[int] = None  # Set after processing

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "queue_index": self.queue_index,
            "initiator_hash": self.initiator_hash.hex(),
            "counterparty_hash": self.counterparty_hash.hex(),
            "evidence_hash": self.evidence_hash.hex(),
            "viewing_key_commitment": self.viewing_key_commitment.hex(),
            "ipfs_uri": self.ipfs_uri,
            "stake_amount": self.stake_amount,
            "queued_at": self.queued_at.isoformat(),
            "status": self.status.value,
            "dispute_id": self.dispute_id,
        }


@dataclass
class QueuedProof:
    """An identity proof queued for batched submission."""

    queue_index: int
    dispute_id: int
    proof_a: Tuple[int, int]
    proof_b: Tuple[Tuple[int, int], Tuple[int, int]]
    proof_c: Tuple[int, int]
    public_signals: Tuple[int]
    queued_at: datetime
    status: SubmissionStatus = SubmissionStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        # proof_b is Tuple[Tuple[int, int], Tuple[int, int]]
        proof_b_serialized = [list(self.proof_b[0]), list(self.proof_b[1])]
        return {
            "queue_index": self.queue_index,
            "dispute_id": self.dispute_id,
            "proof_a": list(self.proof_a),
            "proof_b": proof_b_serialized,
            "proof_c": list(self.proof_c),
            "public_signals": list(self.public_signals),
            "queued_at": self.queued_at.isoformat(),
            "status": self.status.value,
        }


@dataclass
class BatchConfig:
    """Configuration for batch queue behavior."""

    batch_interval: int = 100  # blocks between releases
    min_batch_size: int = 3  # minimum items before release
    max_batch_size: int = 20  # maximum items per batch
    dummy_probability: int = 20  # 0-100, percentage


class BatchQueueClient:
    """
    Client for interacting with the BatchQueue smart contract.

    Provides privacy-preserving dispute submissions through batching.
    """

    def __init__(
        self,
        contract_address: Optional[str] = None,
        web3_provider: Optional[Any] = None,
    ):
        """
        Initialize the BatchQueue client.

        Args:
            contract_address: Address of deployed BatchQueue contract
            web3_provider: Web3 provider instance (optional for testing)
        """
        self.contract_address = contract_address
        self.web3 = web3_provider

        # Local queue tracking (for simulation/testing)
        self._dispute_queue: List[QueuedDispute] = []
        self._proof_queue: List[QueuedProof] = []
        self._next_dispute_index = 0
        self._next_proof_index = 0
        self._config = BatchConfig()
        self._last_batch_block = 0

    def queue_dispute(
        self,
        initiator_hash: bytes,
        counterparty_hash: bytes,
        evidence_hash: bytes,
        viewing_key_commitment: bytes,
        ipfs_uri: str,
        stake_amount: int,
    ) -> QueuedDispute:
        """
        Queue a dispute for batched submission.

        Instead of submitting directly to ILRM, this queues the dispute
        for later batch release, preventing timing analysis attacks.

        Args:
            initiator_hash: Hash of initiator's identity commitment
            counterparty_hash: Hash of counterparty's identity commitment
            evidence_hash: Hash of encrypted evidence
            viewing_key_commitment: Commitment to viewing key
            ipfs_uri: URI for evidence metadata
            stake_amount: Stake amount in wei

        Returns:
            QueuedDispute with queue index and status
        """
        if stake_amount <= 0:
            raise ValueError("Stake amount must be positive")

        queued = QueuedDispute(
            queue_index=self._next_dispute_index,
            initiator_hash=initiator_hash,
            counterparty_hash=counterparty_hash,
            evidence_hash=evidence_hash,
            viewing_key_commitment=viewing_key_commitment,
            ipfs_uri=ipfs_uri,
            stake_amount=stake_amount,
            queued_at=datetime.utcnow(),
        )

        self._dispute_queue.append(queued)
        self._next_dispute_index += 1

        return queued

    def queue_identity_proof(
        self,
        dispute_id: int,
        proof_a: Tuple[int, int],
        proof_b: Tuple[Tuple[int, int], Tuple[int, int]],
        proof_c: Tuple[int, int],
        public_signals: Tuple[int],
    ) -> QueuedProof:
        """
        Queue an identity proof for batched submission.

        Args:
            dispute_id: ID of the dispute
            proof_a: First component of ZK proof
            proof_b: Second component of ZK proof
            proof_c: Third component of ZK proof
            public_signals: Public signals for verification

        Returns:
            QueuedProof with queue index and status
        """
        queued = QueuedProof(
            queue_index=self._next_proof_index,
            dispute_id=dispute_id,
            proof_a=proof_a,
            proof_b=proof_b,
            proof_c=proof_c,
            public_signals=public_signals,
            queued_at=datetime.utcnow(),
        )

        self._proof_queue.append(queued)
        self._next_proof_index += 1

        return queued

    def can_release_batch(self, current_block: Optional[int] = None) -> bool:
        """
        Check if a batch can be released.

        Args:
            current_block: Current block number (for testing). If None,
                           interval check is skipped and only size is checked.

        Returns:
            True if batch can be released
        """
        pending_disputes = sum(
            1 for d in self._dispute_queue if d.status == SubmissionStatus.PENDING
        )
        pending_proofs = sum(1 for p in self._proof_queue if p.status == SubmissionStatus.PENDING)
        total_pending = pending_disputes + pending_proofs

        # Check size threshold
        size_reached = total_pending >= self._config.min_batch_size

        # Check interval threshold (only if current_block provided)
        if current_block is not None:
            interval_passed = current_block >= self._last_batch_block + self._config.batch_interval
            return size_reached or (interval_passed and total_pending > 0)

        # If no block number provided, only check size threshold
        return size_reached

    def simulate_batch_release(self, current_block: Optional[int] = None) -> Dict[str, Any]:
        """
        Simulate releasing a batch of queued items.

        This is for testing/simulation. In production, the on-chain
        contract handles actual batch release via Chainlink Automation.

        Args:
            current_block: Current block number (for testing)

        Returns:
            Dictionary with batch release statistics
        """
        if not self.can_release_batch(current_block):
            return {
                "released": False,
                "reason": "Cannot release batch yet",
            }

        disputes_processed = 0
        proofs_processed = 0
        dummies_created = 0

        # Process disputes
        for dispute in self._dispute_queue:
            if dispute.status == SubmissionStatus.PENDING:
                if disputes_processed >= self._config.max_batch_size:
                    break
                dispute.status = SubmissionStatus.COMPLETED
                dispute.dispute_id = self._simulate_dispute_id()
                disputes_processed += 1

        # Process proofs
        for proof in self._proof_queue:
            if proof.status == SubmissionStatus.PENDING:
                if disputes_processed + proofs_processed >= self._config.max_batch_size:
                    break
                proof.status = SubmissionStatus.COMPLETED
                proofs_processed += 1

        # Simulate dummy transaction
        if self._should_add_dummy():
            dummies_created = 1

        if current_block:
            self._last_batch_block = current_block

        return {
            "released": True,
            "disputes_processed": disputes_processed,
            "proofs_processed": proofs_processed,
            "dummies_created": dummies_created,
            "block_number": current_block or self._last_batch_block,
        }

    def _simulate_dispute_id(self) -> int:
        """Generate a simulated dispute ID."""
        return int.from_bytes(os.urandom(4), "big") % 1000000

    def _should_add_dummy(self) -> bool:
        """Check if a dummy transaction should be added."""
        random_val = int.from_bytes(os.urandom(1), "big") % 100
        return random_val < self._config.dummy_probability

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Dictionary with queue sizes and statistics
        """
        pending_disputes = sum(
            1 for d in self._dispute_queue if d.status == SubmissionStatus.PENDING
        )
        completed_disputes = sum(
            1 for d in self._dispute_queue if d.status == SubmissionStatus.COMPLETED
        )
        pending_proofs = sum(1 for p in self._proof_queue if p.status == SubmissionStatus.PENDING)
        completed_proofs = sum(
            1 for p in self._proof_queue if p.status == SubmissionStatus.COMPLETED
        )

        return {
            "dispute_queue": {
                "pending": pending_disputes,
                "completed": completed_disputes,
                "total": len(self._dispute_queue),
            },
            "proof_queue": {
                "pending": pending_proofs,
                "completed": completed_proofs,
                "total": len(self._proof_queue),
            },
            "can_release": self.can_release_batch(),
            "config": {
                "batch_interval": self._config.batch_interval,
                "min_batch_size": self._config.min_batch_size,
                "max_batch_size": self._config.max_batch_size,
                "dummy_probability": self._config.dummy_probability,
            },
        }

    def update_config(
        self,
        batch_interval: Optional[int] = None,
        min_batch_size: Optional[int] = None,
        max_batch_size: Optional[int] = None,
        dummy_probability: Optional[int] = None,
    ) -> BatchConfig:
        """
        Update batch configuration.

        Args:
            batch_interval: Blocks between batch releases
            min_batch_size: Minimum items before release
            max_batch_size: Maximum items per batch
            dummy_probability: Percentage chance of dummy (0-100)

        Returns:
            Updated BatchConfig
        """
        if batch_interval is not None:
            self._config.batch_interval = batch_interval
        if min_batch_size is not None:
            self._config.min_batch_size = min_batch_size
        if max_batch_size is not None:
            if max_batch_size < self._config.min_batch_size:
                raise ValueError("max_batch_size cannot be less than min_batch_size")
            self._config.max_batch_size = max_batch_size
        if dummy_probability is not None:
            if not 0 <= dummy_probability <= 100:
                raise ValueError("dummy_probability must be 0-100")
            self._config.dummy_probability = dummy_probability

        return self._config


class PrivacyEnhancer:
    """
    High-level interface for privacy-enhanced dispute submission.

    Combines batch queue, timing randomization, and dummy transactions
    for comprehensive inference attack prevention.
    """

    def __init__(
        self,
        batch_client: Optional[BatchQueueClient] = None,
    ):
        """
        Initialize the PrivacyEnhancer.

        Args:
            batch_client: BatchQueue client instance
        """
        self.batch_client = batch_client or BatchQueueClient()
        self._random_delays: List[float] = []

    def submit_private_dispute(
        self,
        initiator_secret: bytes,
        counterparty_identity: bytes,
        evidence: bytes,
        evidence_hash: bytes,
        viewing_key_commitment: bytes,
        ipfs_uri: str,
        stake_amount: int,
        add_random_delay: bool = True,
    ) -> QueuedDispute:
        """
        Submit a dispute with privacy enhancements.

        This method:
        1. Computes identity hashes
        2. Adds optional random delay to submission
        3. Queues for batched release

        Args:
            initiator_secret: Initiator's identity secret
            counterparty_identity: Counterparty's identity commitment
            evidence: Raw evidence data
            evidence_hash: Hash of encrypted evidence
            viewing_key_commitment: Commitment to viewing key
            ipfs_uri: IPFS URI for evidence
            stake_amount: Stake in wei
            add_random_delay: Whether to add random delay

        Returns:
            QueuedDispute for tracking
        """
        # Compute identity hashes
        initiator_hash = keccak(initiator_secret)
        counterparty_hash = keccak(counterparty_identity)

        # SECURITY FIX LOW-004: Always add delay with random variation
        # Using a constant base delay prevents timing oracle attacks where
        # an attacker can distinguish delayed vs non-delayed operations.
        # Base delay: 5 seconds, random variation: 0-25 seconds (total: 5-30s)
        base_delay = 5.0
        random_variation = (int.from_bytes(os.urandom(2), "big") % 25000) / 1000
        delay = base_delay + random_variation if add_random_delay else base_delay
        self._random_delays.append(delay)
        time.sleep(delay)

        # Queue for batch release
        return self.batch_client.queue_dispute(
            initiator_hash=initiator_hash,
            counterparty_hash=counterparty_hash,
            evidence_hash=evidence_hash,
            viewing_key_commitment=viewing_key_commitment,
            ipfs_uri=ipfs_uri,
            stake_amount=stake_amount,
        )

    def submit_private_proof(
        self,
        dispute_id: int,
        proof: Dict[str, Any],
        add_random_delay: bool = True,
    ) -> QueuedProof:
        """
        Submit an identity proof with privacy enhancements.

        Args:
            dispute_id: ID of the dispute
            proof: ZK proof dictionary with a, b, c, signals
            add_random_delay: Whether to add random delay

        Returns:
            QueuedProof for tracking
        """
        # SECURITY FIX LOW-004: Always add delay with random variation
        # Using a constant base delay prevents timing oracle attacks where
        # an attacker can distinguish delayed vs non-delayed operations.
        base_delay = 5.0
        random_variation = (int.from_bytes(os.urandom(2), "big") % 25000) / 1000
        delay = base_delay + random_variation if add_random_delay else base_delay
        self._random_delays.append(delay)
        time.sleep(delay)

        # Extract proof components
        proof_a = tuple(proof["a"])
        proof_b = tuple(tuple(x) for x in proof["b"])
        proof_c = tuple(proof["c"])
        public_signals = tuple(proof["signals"])

        return self.batch_client.queue_identity_proof(
            dispute_id=dispute_id,
            proof_a=proof_a,
            proof_b=proof_b,
            proof_c=proof_c,
            public_signals=public_signals,
        )

    def get_privacy_metrics(self) -> Dict[str, Any]:
        """
        Get privacy-related metrics.

        Returns:
            Dictionary with privacy statistics
        """
        queue_status = self.batch_client.get_queue_status()

        return {
            "queue_status": queue_status,
            "random_delays": {
                "count": len(self._random_delays),
                "average": (
                    sum(self._random_delays) / len(self._random_delays)
                    if self._random_delays
                    else 0
                ),
                "total": sum(self._random_delays),
            },
            "privacy_level": self._calculate_privacy_level(queue_status),
        }

    def _calculate_privacy_level(self, queue_status: Dict[str, Any]) -> str:
        """
        Calculate the current privacy level.

        Args:
            queue_status: Current queue status

        Returns:
            Privacy level: "low", "medium", "high"
        """
        pending = queue_status["dispute_queue"]["pending"] + queue_status["proof_queue"]["pending"]
        dummy_prob = queue_status["config"]["dummy_probability"]

        if pending >= 10 and dummy_prob >= 30:
            return "high"
        elif pending >= 5 or dummy_prob >= 15:
            return "medium"
        else:
            return "low"


# Convenience functions


def create_batch_client(
    contract_address: Optional[str] = None,
    web3_provider: Optional[Any] = None,
) -> BatchQueueClient:
    """
    Create a BatchQueue client instance.

    Args:
        contract_address: Address of BatchQueue contract
        web3_provider: Web3 provider instance

    Returns:
        Configured BatchQueueClient
    """
    return BatchQueueClient(
        contract_address=contract_address,
        web3_provider=web3_provider,
    )


def create_privacy_enhancer(
    batch_client: Optional[BatchQueueClient] = None,
) -> PrivacyEnhancer:
    """
    Create a PrivacyEnhancer instance.

    Args:
        batch_client: Optional BatchQueue client

    Returns:
        Configured PrivacyEnhancer
    """
    return PrivacyEnhancer(batch_client=batch_client)
