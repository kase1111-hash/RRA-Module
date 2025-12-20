# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Authentication Module for RRA.

Provides multiple authentication mechanisms:
- FIDO2/WebAuthn for hardware-backed security
- DID-based authentication for decentralized identity
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
from .did_auth import (
    DIDAuthenticator,
    DIDAuthMiddleware,
    AuthChallenge,
    AuthSession,
    AuthResult,
    AuthStatus,
    AuthError,
    ChallengeExpiredError,
    InvalidSignatureError,
    DIDResolutionError,
    InsufficientScoreError,
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
    # DID Authentication
    "DIDAuthenticator",
    "DIDAuthMiddleware",
    "AuthChallenge",
    "AuthSession",
    "AuthResult",
    "AuthStatus",
    "AuthError",
    "ChallengeExpiredError",
    "InvalidSignatureError",
    "DIDResolutionError",
    "InsufficientScoreError",
]
