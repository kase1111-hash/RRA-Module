# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Decentralized Identity (DID) Module for NatLangChain.

Provides DID-based identity management for the RRA ecosystem:
- DID resolution and verification (did:web, did:ethr, did:key)
- Sybil-resistant participation in disputes
- Portable identity across NatLangChain ecosystem
- Privacy-preserving identity verification

Part of Phase 6.3: DID Integration
"""

from .did_resolver import (
    DIDDocument,
    DIDResolver,
    DIDMethod,
    VerificationMethod,
    resolve_did,
)
from .sybil_resistance import (
    SybilResistance,
    IdentityScore,
    ProofOfHumanity,
    SybilCheck,
)

__all__ = [
    # DID Resolution
    "DIDDocument",
    "DIDResolver",
    "DIDMethod",
    "VerificationMethod",
    "resolve_did",
    # Sybil Resistance
    "SybilResistance",
    "IdentityScore",
    "ProofOfHumanity",
    "SybilCheck",
]
