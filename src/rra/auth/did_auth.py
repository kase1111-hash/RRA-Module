# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
DID-Based Authentication Module.

Provides decentralized identity authentication for RRA:
- Challenge-response authentication with DID verification
- Multi-method DID support (did:web, did:ethr, did:key, did:nlc)
- Session management with DID-bound tokens
- Integration with Sybil resistance scoring
"""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..identity.did_resolver import DIDResolver
from ..identity.sybil_resistance import SybilResistance, IdentityScore


class AuthStatus(Enum):
    """Status of an authentication attempt."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuthError(Exception):
    """Base exception for authentication errors."""

    pass


class ChallengeExpiredError(AuthError):
    """Challenge has expired."""

    pass


class InvalidSignatureError(AuthError):
    """Signature verification failed."""

    pass


class DIDResolutionError(AuthError):
    """Failed to resolve DID document."""

    pass


class InsufficientScoreError(AuthError):
    """Identity score below required threshold."""

    pass


@dataclass
class AuthChallenge:
    """A challenge for DID authentication."""

    id: str
    did: str
    nonce: bytes
    message: str
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if challenge has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def to_sign_bytes(self) -> bytes:
        """Get bytes to be signed by the DID controller."""
        # Include challenge ID, nonce, and timestamp for replay protection
        sign_data = (
            f"{self.id}:{self.nonce.hex()}:{self.message}:{int(self.created_at.timestamp())}"
        )
        return sign_data.encode("utf-8")


@dataclass
class AuthSession:
    """An authenticated session bound to a DID."""

    id: str
    did: str
    challenge_id: str
    created_at: datetime
    expires_at: datetime
    identity_score: Optional[IdentityScore] = None
    scopes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: AuthStatus = AuthStatus.VERIFIED

    @property
    def is_valid(self) -> bool:
        """Check if session is valid."""
        return self.status == AuthStatus.VERIFIED and datetime.now(timezone.utc) <= self.expires_at

    def has_scope(self, scope: str) -> bool:
        """Check if session has a specific scope."""
        return scope in self.scopes or "*" in self.scopes


@dataclass
class AuthResult:
    """Result of an authentication attempt."""

    success: bool
    did: Optional[str] = None
    session: Optional[AuthSession] = None
    identity_score: Optional[IdentityScore] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class DIDAuthenticator:
    """
    DID-based authentication handler.

    Provides challenge-response authentication flow:
    1. Client requests a challenge for their DID
    2. Client signs the challenge with their DID's private key
    3. Server verifies signature using DID document
    4. On success, server creates authenticated session
    """

    DEFAULT_CHALLENGE_TTL = 300  # 5 minutes
    DEFAULT_SESSION_TTL = 3600  # 1 hour
    MIN_IDENTITY_SCORE = 0  # Minimum score to authenticate (0 = no minimum)

    def __init__(
        self,
        did_resolver: Optional[DIDResolver] = None,
        sybil_resistance: Optional[SybilResistance] = None,
        challenge_ttl: int = DEFAULT_CHALLENGE_TTL,
        session_ttl: int = DEFAULT_SESSION_TTL,
        min_identity_score: float = MIN_IDENTITY_SCORE,
        require_sybil_check: bool = False,
    ):
        """
        Initialize the authenticator.

        Args:
            did_resolver: DID resolver instance
            sybil_resistance: Sybil resistance checker
            challenge_ttl: Challenge expiration in seconds
            session_ttl: Session expiration in seconds
            min_identity_score: Minimum identity score required
            require_sybil_check: Whether to require Sybil check for auth
        """
        self.did_resolver = did_resolver or DIDResolver()
        self.sybil_resistance = sybil_resistance or SybilResistance(self.did_resolver)
        self.challenge_ttl = challenge_ttl
        self.session_ttl = session_ttl
        self.min_identity_score = min_identity_score
        self.require_sybil_check = require_sybil_check

        # In-memory storage (production would use persistent storage)
        self._challenges: Dict[str, AuthChallenge] = {}
        self._sessions: Dict[str, AuthSession] = {}
        self._did_sessions: Dict[str, List[str]] = {}  # DID -> session IDs

        # Secret for HMAC operations
        self._hmac_secret = secrets.token_bytes(32)

    async def create_challenge(
        self,
        did: str,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuthChallenge:
        """
        Create an authentication challenge for a DID.

        Args:
            did: The DID requesting authentication
            message: Optional custom message to include
            metadata: Optional metadata to attach

        Returns:
            AuthChallenge to be signed by the DID controller
        """
        # Verify DID can be resolved
        doc = await self.did_resolver.resolve(did)
        if not doc:
            raise DIDResolutionError(f"Could not resolve DID: {did}")

        # Generate challenge
        challenge_id = secrets.token_urlsafe(32)
        nonce = secrets.token_bytes(32)
        now = datetime.now(timezone.utc)

        default_message = f"Authenticate to RRA as {did}"
        challenge = AuthChallenge(
            id=challenge_id,
            did=did,
            nonce=nonce,
            message=message or default_message,
            created_at=now,
            expires_at=now + timedelta(seconds=self.challenge_ttl),
            metadata=metadata or {},
        )

        # Store challenge
        self._challenges[challenge_id] = challenge

        return challenge

    async def verify_challenge(
        self,
        challenge_id: str,
        signature: bytes,
        scopes: Optional[List[str]] = None,
    ) -> AuthResult:
        """
        Verify a signed challenge and create an authenticated session.

        Args:
            challenge_id: The challenge ID
            signature: Signature over the challenge bytes
            scopes: Requested scopes for the session

        Returns:
            AuthResult with session if successful
        """
        # Get challenge
        challenge = self._challenges.get(challenge_id)
        if not challenge:
            return AuthResult(
                success=False,
                error="Challenge not found",
                error_code="CHALLENGE_NOT_FOUND",
            )

        # Check expiration
        if challenge.is_expired:
            del self._challenges[challenge_id]
            return AuthResult(
                success=False,
                error="Challenge has expired",
                error_code="CHALLENGE_EXPIRED",
            )

        # Verify signature
        message = challenge.to_sign_bytes()
        try:
            is_valid = await self.did_resolver.verify_signature(
                challenge.did,
                message,
                signature,
            )
        except Exception as e:
            return AuthResult(
                success=False,
                error=f"Signature verification error: {str(e)}",
                error_code="VERIFICATION_ERROR",
            )

        if not is_valid:
            return AuthResult(
                success=False,
                did=challenge.did,
                error="Invalid signature",
                error_code="INVALID_SIGNATURE",
            )

        # Check Sybil resistance if required
        identity_score = None
        if self.require_sybil_check or self.min_identity_score > 0:
            identity_score = await self.sybil_resistance.get_identity_score(challenge.did)

            if identity_score.score < self.min_identity_score:
                return AuthResult(
                    success=False,
                    did=challenge.did,
                    identity_score=identity_score,
                    error=f"Identity score {identity_score.score:.2f} below minimum {self.min_identity_score}",
                    error_code="INSUFFICIENT_SCORE",
                )

        # Create session
        session = await self._create_session(
            challenge=challenge,
            identity_score=identity_score,
            scopes=scopes or [],
        )

        # Clean up challenge
        del self._challenges[challenge_id]

        return AuthResult(
            success=True,
            did=challenge.did,
            session=session,
            identity_score=identity_score,
        )

    async def _create_session(
        self,
        challenge: AuthChallenge,
        identity_score: Optional[IdentityScore],
        scopes: List[str],
    ) -> AuthSession:
        """Create an authenticated session."""
        session_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        session = AuthSession(
            id=session_id,
            did=challenge.did,
            challenge_id=challenge.id,
            created_at=now,
            expires_at=now + timedelta(seconds=self.session_ttl),
            identity_score=identity_score,
            scopes=scopes,
            metadata=challenge.metadata,
        )

        # Store session
        self._sessions[session_id] = session

        # Track DID -> sessions mapping
        if challenge.did not in self._did_sessions:
            self._did_sessions[challenge.did] = []
        self._did_sessions[challenge.did].append(session_id)

        return session

    async def validate_session(
        self,
        session_id: str,
        required_scope: Optional[str] = None,
    ) -> AuthResult:
        """
        Validate an existing session.

        Args:
            session_id: The session ID to validate
            required_scope: Optional scope that must be present

        Returns:
            AuthResult indicating validity
        """
        session = self._sessions.get(session_id)
        if not session:
            return AuthResult(
                success=False,
                error="Session not found",
                error_code="SESSION_NOT_FOUND",
            )

        if not session.is_valid:
            return AuthResult(
                success=False,
                did=session.did,
                error="Session is invalid or expired",
                error_code="SESSION_INVALID",
            )

        if required_scope and not session.has_scope(required_scope):
            return AuthResult(
                success=False,
                did=session.did,
                session=session,
                error=f"Session lacks required scope: {required_scope}",
                error_code="INSUFFICIENT_SCOPE",
            )

        return AuthResult(
            success=True,
            did=session.did,
            session=session,
            identity_score=session.identity_score,
        )

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke an active session.

        Args:
            session_id: The session ID to revoke

        Returns:
            True if revoked, False if not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = AuthStatus.REVOKED

        # Remove from DID tracking
        if session.did in self._did_sessions:
            self._did_sessions[session.did] = [
                sid for sid in self._did_sessions[session.did] if sid != session_id
            ]

        return True

    async def revoke_all_sessions(self, did: str) -> int:
        """
        Revoke all sessions for a DID.

        Args:
            did: The DID whose sessions to revoke

        Returns:
            Number of sessions revoked
        """
        session_ids = self._did_sessions.get(did, [])
        count = 0

        for session_id in session_ids:
            if await self.revoke_session(session_id):
                count += 1

        return count

    async def get_active_sessions(self, did: str) -> List[AuthSession]:
        """
        Get all active sessions for a DID.

        Args:
            did: The DID to query

        Returns:
            List of active sessions
        """
        session_ids = self._did_sessions.get(did, [])
        sessions = []

        for session_id in session_ids:
            session = self._sessions.get(session_id)
            if session and session.is_valid:
                sessions.append(session)

        return sessions

    def generate_session_token(self, session: AuthSession) -> str:
        """
        Generate a bearer token for a session.

        Args:
            session: The session to generate token for

        Returns:
            Bearer token string
        """
        import base64

        # Create token payload with pipe separator (not in DID format)
        payload = f"{session.id}|{session.did}|{int(session.expires_at.timestamp())}"

        # Generate HMAC
        mac = hmac.new(
            self._hmac_secret,
            payload.encode("utf-8"),
            hashlib.sha256,
        )

        # Base64 encode payload to avoid separator issues
        encoded_payload = base64.urlsafe_b64encode(payload.encode()).decode()
        token = f"{encoded_payload}.{mac.hexdigest()}"
        return secrets.token_urlsafe(8) + "." + token

    async def validate_token(self, token: str) -> AuthResult:
        """
        Validate a bearer token and return the associated session.

        Args:
            token: The bearer token

        Returns:
            AuthResult with session if valid
        """
        import base64

        try:
            # Parse token: {random_prefix}.{base64_payload}.{mac}
            parts = token.split(".")
            if len(parts) != 3:
                return AuthResult(
                    success=False,
                    error="Invalid token format",
                    error_code="INVALID_TOKEN",
                )

            # Extract and decode payload (skip random prefix)
            encoded_payload = parts[1]
            provided_mac = parts[2]

            try:
                payload = base64.urlsafe_b64decode(encoded_payload).decode()
                payload_parts = payload.split("|")
                if len(payload_parts) != 3:
                    raise ValueError("Invalid payload structure")
                session_id, _, expires_ts = (
                    payload_parts[0],
                    payload_parts[1],
                    int(payload_parts[2]),
                )
            except (ValueError, UnicodeDecodeError):
                return AuthResult(
                    success=False,
                    error="Invalid token payload",
                    error_code="INVALID_TOKEN",
                )

            # Verify HMAC
            expected_mac = hmac.new(
                self._hmac_secret,
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(provided_mac, expected_mac):
                return AuthResult(
                    success=False,
                    error="Invalid token signature",
                    error_code="INVALID_TOKEN",
                )

            # Check expiration
            if time.time() > expires_ts:
                return AuthResult(
                    success=False,
                    error="Token has expired",
                    error_code="TOKEN_EXPIRED",
                )

            # Validate session
            return await self.validate_session(session_id)

        except (ValueError, IndexError) as e:
            return AuthResult(
                success=False,
                error=f"Token parsing error: {str(e)}",
                error_code="INVALID_TOKEN",
            )

    async def cleanup_expired(self) -> Tuple[int, int]:
        """
        Clean up expired challenges and sessions.

        Returns:
            Tuple of (challenges_removed, sessions_removed)
        """
        now = datetime.now(timezone.utc)

        # Clean challenges
        expired_challenges = [cid for cid, c in self._challenges.items() if c.is_expired]
        for cid in expired_challenges:
            del self._challenges[cid]

        # Clean sessions
        expired_sessions = [sid for sid, s in self._sessions.items() if now > s.expires_at]
        for sid in expired_sessions:
            session = self._sessions[sid]
            if session.did in self._did_sessions:
                self._did_sessions[session.did] = [
                    s for s in self._did_sessions[session.did] if s != sid
                ]
            del self._sessions[sid]

        return len(expired_challenges), len(expired_sessions)


class DIDAuthMiddleware:
    """
    Middleware for DID-based authentication.

    Can be used with web frameworks to protect endpoints.
    """

    def __init__(
        self,
        authenticator: DIDAuthenticator,
        required_scopes: Optional[List[str]] = None,
        min_identity_score: float = 0,
    ):
        """
        Initialize middleware.

        Args:
            authenticator: The DID authenticator
            required_scopes: Scopes required for all requests
            min_identity_score: Minimum identity score required
        """
        self.authenticator = authenticator
        self.required_scopes = required_scopes or []
        self.min_identity_score = min_identity_score

    async def authenticate_request(
        self,
        authorization_header: Optional[str],
    ) -> AuthResult:
        """
        Authenticate a request from its authorization header.

        Args:
            authorization_header: The Authorization header value

        Returns:
            AuthResult indicating authentication status
        """
        if not authorization_header:
            return AuthResult(
                success=False,
                error="Missing authorization header",
                error_code="NO_AUTH",
            )

        # Parse bearer token
        parts = authorization_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return AuthResult(
                success=False,
                error="Invalid authorization format",
                error_code="INVALID_AUTH_FORMAT",
            )

        token = parts[1]

        # Validate token
        result = await self.authenticator.validate_token(token)
        if not result.success:
            return result

        # Check required scopes
        if self.required_scopes and result.session:
            for scope in self.required_scopes:
                if not result.session.has_scope(scope):
                    return AuthResult(
                        success=False,
                        did=result.did,
                        session=result.session,
                        error=f"Missing required scope: {scope}",
                        error_code="INSUFFICIENT_SCOPE",
                    )

        # Check identity score
        if self.min_identity_score > 0 and result.identity_score:
            if result.identity_score.score < self.min_identity_score:
                return AuthResult(
                    success=False,
                    did=result.did,
                    session=result.session,
                    identity_score=result.identity_score,
                    error=f"Identity score below minimum: {self.min_identity_score}",
                    error_code="INSUFFICIENT_SCORE",
                )

        return result
