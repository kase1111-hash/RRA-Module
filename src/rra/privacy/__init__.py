# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Privacy and Zero-Knowledge Infrastructure for RRA Module.

This module provides privacy-preserving primitives for ILRM dispute resolution:
- Viewing key generation and ECIES encryption
- Shamir's Secret Sharing for threshold key escrow
- ZK proof generation helpers
- Identity hash generation for anonymous participation
- Batch queue for inference attack prevention
"""

from .viewing_keys import (
    ViewingKeyManager,
    ECIESCipher,
    generate_viewing_key,
    encrypt_evidence,
    decrypt_evidence,
)
from .secret_sharing import (
    ShamirSecretSharing,
    split_secret,
    reconstruct_secret,
)
from .identity import (
    IdentityManager,
    generate_identity_secret,
    compute_identity_hash,
)
from .batch_queue import (
    BatchQueueClient,
    PrivacyEnhancer,
    QueuedDispute,
    QueuedProof,
    BatchConfig,
    SubmissionStatus,
    create_batch_client,
    create_privacy_enhancer,
)

__all__ = [
    # Viewing Keys
    "ViewingKeyManager",
    "ECIESCipher",
    "generate_viewing_key",
    "encrypt_evidence",
    "decrypt_evidence",
    # Secret Sharing
    "ShamirSecretSharing",
    "split_secret",
    "reconstruct_secret",
    # Identity
    "IdentityManager",
    "generate_identity_secret",
    "compute_identity_hash",
    # Batch Queue (Inference Attack Prevention)
    "BatchQueueClient",
    "PrivacyEnhancer",
    "QueuedDispute",
    "QueuedProof",
    "BatchConfig",
    "SubmissionStatus",
    "create_batch_client",
    "create_privacy_enhancer",
]
