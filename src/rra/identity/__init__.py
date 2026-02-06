# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Decentralized Identity (DID) Module for RRA.

Provides DID-based identity management:
- DID resolution and verification (did:web, did:ethr, did:key)
- Portable identity across NatLangChain ecosystem
"""

from .did_resolver import (
    DIDDocument,
    DIDResolver,
    DIDMethod,
    VerificationMethod,
    resolve_did,
)

__all__ = [
    # DID Resolution
    "DIDDocument",
    "DIDResolver",
    "DIDMethod",
    "VerificationMethod",
    "resolve_did",
]
