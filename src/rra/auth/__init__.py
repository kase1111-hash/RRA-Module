# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Hardware Authentication Module for RRA.

Provides FIDO2/WebAuthn integration for hardware-backed security:
- YubiKey and platform authenticator support
- Challenge-response authentication
- ZK-compatible identity commitment generation
- Scoped delegation management
"""

from .webauthn import (
    WebAuthnClient,
    WebAuthnCredential,
    AuthenticatorAssertion,
    create_challenge,
    verify_assertion,
)
from .identity import (
    HardwareIdentity,
    generate_identity_commitment,
    compute_credential_hash,
)
from .delegation import (
    ScopedDelegation,
    DelegationScope,
    ActionType,
)

__all__ = [
    # WebAuthn
    "WebAuthnClient",
    "WebAuthnCredential",
    "AuthenticatorAssertion",
    "create_challenge",
    "verify_assertion",
    # Identity
    "HardwareIdentity",
    "generate_identity_commitment",
    "compute_credential_hash",
    # Delegation
    "ScopedDelegation",
    "DelegationScope",
    "ActionType",
]
