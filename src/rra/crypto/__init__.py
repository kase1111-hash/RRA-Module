# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Cryptographic primitives for RRA Module.

Provides:
- ECIES encryption for viewing keys
- Shamir's Secret Sharing for key escrow
- Pedersen commitments for on-chain proofs
"""

from .viewing_keys import (
    ViewingKey,
    ViewingKeyManager,
    EncryptedData,
)
from .shamir import (
    ShamirSecretSharing,
    KeyShare,
    ThresholdConfig,
)
from .pedersen import (
    PedersenCommitment,
    CommitmentProof,
)

__all__ = [
    # Viewing Keys
    "ViewingKey",
    "ViewingKeyManager",
    "EncryptedData",
    # Shamir
    "ShamirSecretSharing",
    "KeyShare",
    "ThresholdConfig",
    # Pedersen
    "PedersenCommitment",
    "CommitmentProof",
]
