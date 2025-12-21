# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
L3 High-Throughput Dispute Processing Module.

Provides app-specific rollup infrastructure for high-throughput dispute handling:

- Batch processor: Efficient batch dispute processing
- Sequencer: Transaction ordering and state transitions
- State management: Merkle tree state commitments
- L2 bridge: Cross-layer communication

Architecture:
- L3 processes disputes with sub-second finality
- Batches state roots to L2 periodically
- Fraud proofs for security guarantees
- Compressed calldata for gas efficiency
"""

from .batch_processor import (
    BatchProcessor,
    Batch,
    BatchConfig,
    BatchStatus,
    ProcessedDispute,
    BatchResult,
    create_batch_processor,
)
from .sequencer import (
    DisputeSequencer,
    SequencerConfig,
    SequencerStatus,
    Transaction,
    TransactionType,
    StateTransition,
    create_sequencer,
)

__all__ = [
    # Batch processing
    "BatchProcessor",
    "Batch",
    "BatchConfig",
    "BatchStatus",
    "ProcessedDispute",
    "BatchResult",
    "create_batch_processor",
    # Sequencing
    "DisputeSequencer",
    "SequencerConfig",
    "SequencerStatus",
    "Transaction",
    "TransactionType",
    "StateTransition",
    "create_sequencer",
]
