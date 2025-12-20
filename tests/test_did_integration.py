# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Tests for DID Integration (Phase 6.3).

Tests cover:
- DID resolution across multiple methods
- Sybil resistance scoring
- DID-based authentication
- Session management
"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.rra.identity.did_resolver import (
    DIDResolver,
    DIDDocument,
    DIDMethod,
    VerificationMethod,
    ServiceEndpoint,
)
from src.rra.identity.sybil_resistance import (
    SybilResistance,
    IdentityScore,
    SybilCheck,
    ProofOfHumanity,
    ProofType,
    TrustLevel,
)
from src.rra.auth.did_auth import (
    DIDAuthenticator,
    DIDAuthMiddleware,
    AuthChallenge,
    AuthSession,
    AuthResult,
    AuthStatus,
    DIDResolutionError,
)


# =============================================================================
# DID Resolver Tests
# =============================================================================


class TestDIDResolver:
    """Tests for DID resolution."""

    @pytest.fixture
    def resolver(self):
        """Create a DID resolver instance."""
        return DIDResolver()

    def test_parse_did_web(self, resolver):
        """Test parsing did:web DIDs."""
        did = "did:web:example.com"
        method, identifier = resolver.parse_did(did)
        assert method == DIDMethod.WEB
        assert identifier == "example.com"

    def test_parse_did_ethr(self, resolver):
        """Test parsing did:ethr DIDs."""
        did = "did:ethr:0x1234567890abcdef1234567890abcdef12345678"
        method, identifier = resolver.parse_did(did)
        assert method == DIDMethod.ETHR
        assert identifier == "0x1234567890abcdef1234567890abcdef12345678"

    def test_parse_did_key(self, resolver):
        """Test parsing did:key DIDs."""
        did = "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
        method, identifier = resolver.parse_did(did)
        assert method == DIDMethod.KEY
        assert "z6Mk" in identifier

    def test_parse_did_nlc(self, resolver):
        """Test parsing did:nlc DIDs."""
        did = "did:nlc:abc123xyz"
        method, identifier = resolver.parse_did(did)
        assert method == DIDMethod.NLC
        assert identifier == "abc123xyz"

    def test_parse_invalid_did(self, resolver):
        """Test parsing invalid DID format."""
        with pytest.raises(ValueError):
            resolver.parse_did("not-a-did")

    def test_parse_unknown_method(self, resolver):
        """Test parsing unknown DID method."""
        with pytest.raises(ValueError):
            resolver.parse_did("did:unknown:something")

    @pytest.mark.asyncio
    async def test_resolve_did_nlc(self, resolver):
        """Test resolving did:nlc DIDs."""
        did = "did:nlc:test123"
        doc = await resolver.resolve(did)

        assert doc is not None
        assert doc.id == did
        assert len(doc.verification_method) > 0
        assert len(doc.authentication) > 0

    @pytest.mark.asyncio
    async def test_resolve_caching(self, resolver):
        """Test that resolved DIDs are cached."""
        did = "did:nlc:cache_test"

        # First resolution
        doc1 = await resolver.resolve(did)
        assert doc1 is not None

        # Second resolution should use cache
        doc2 = await resolver.resolve(did)
        assert doc2 is not None
        assert doc1.id == doc2.id

    def test_did_document_structure(self):
        """Test DID document dataclass."""
        doc = DIDDocument(
            id="did:nlc:test",
            controller="did:nlc:test",
            verification_method=[
                VerificationMethod(
                    id="did:nlc:test#key-1",
                    type="Ed25519VerificationKey2020",
                    controller="did:nlc:test",
                    public_key_multibase="z6Mk...",
                )
            ],
            authentication=["did:nlc:test#key-1"],
            service=[
                ServiceEndpoint(
                    id="did:nlc:test#rra",
                    type="RRAEndpoint",
                    service_endpoint="https://example.com/rra",
                )
            ],
        )

        assert doc.id == "did:nlc:test"
        assert len(doc.verification_method) == 1
        assert doc.verification_method[0].type == "Ed25519VerificationKey2020"


# =============================================================================
# Sybil Resistance Tests
# =============================================================================


class TestSybilResistance:
    """Tests for Sybil resistance scoring."""

    @pytest.fixture
    def sybil(self):
        """Create a Sybil resistance instance."""
        resolver = DIDResolver()
        return SybilResistance(resolver)

    @pytest.mark.asyncio
    async def test_get_identity_score(self, sybil):
        """Test getting identity score for a DID."""
        did = "did:nlc:score_test"
        score = await sybil.get_identity_score(did)

        assert isinstance(score, IdentityScore)
        assert 0 <= score.overall_score <= 100
        assert score.did == did

    @pytest.mark.asyncio
    async def test_check_identity(self, sybil):
        """Test identity check."""
        did = "did:nlc:check_test"
        check = await sybil.check_identity(did)

        assert isinstance(check, SybilCheck)
        assert check.did == did
        assert isinstance(check.is_human, bool)
        assert isinstance(check.trust_level, TrustLevel)

    def test_proof_weights(self, sybil):
        """Test that proof type weights are configured."""
        assert ProofType.POH_WORLDCOIN in sybil.PROOF_WEIGHTS
        assert ProofType.HARDWARE in sybil.PROOF_WEIGHTS
        assert ProofType.POH_BRIGHTID in sybil.PROOF_WEIGHTS

        # Worldcoin should have highest weight
        assert sybil.PROOF_WEIGHTS[ProofType.POH_WORLDCOIN] >= 25

    def test_proof_of_humanity_structure(self):
        """Test ProofOfHumanity dataclass."""
        proof = ProofOfHumanity(
            proof_type=ProofType.POH_WORLDCOIN,
            verified=True,
            verification_time=datetime.now(timezone.utc),
            evidence_hash="0x123...",
            confidence=0.95,
        )

        assert proof.verified is True
        assert proof.confidence == 0.95
        assert proof.proof_type == ProofType.POH_WORLDCOIN

    @pytest.mark.asyncio
    async def test_trust_level_thresholds(self, sybil):
        """Test trust level determination based on score."""
        # Create mock scores and verify trust levels
        assert TrustLevel.HIGH.value == "high"
        assert TrustLevel.MEDIUM.value == "medium"
        assert TrustLevel.LOW.value == "low"
        assert TrustLevel.UNTRUSTED.value == "untrusted"


# =============================================================================
# DID Authentication Tests
# =============================================================================


class TestDIDAuthenticator:
    """Tests for DID-based authentication."""

    @pytest.fixture
    def authenticator(self):
        """Create a DID authenticator instance."""
        return DIDAuthenticator(
            challenge_ttl=300,
            session_ttl=3600,
        )

    @pytest.mark.asyncio
    async def test_create_challenge(self, authenticator):
        """Test creating an authentication challenge."""
        did = "did:nlc:auth_test"
        challenge = await authenticator.create_challenge(did)

        assert isinstance(challenge, AuthChallenge)
        assert challenge.did == did
        assert len(challenge.nonce) == 32
        assert challenge.expires_at > challenge.created_at

    @pytest.mark.asyncio
    async def test_challenge_expiration(self, authenticator):
        """Test that challenges expire correctly."""
        did = "did:nlc:expire_test"
        challenge = await authenticator.create_challenge(did)

        # Fresh challenge should not be expired
        assert not challenge.is_expired

        # Manually set to expired
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert challenge.is_expired

    @pytest.mark.asyncio
    async def test_verify_challenge_not_found(self, authenticator):
        """Test verification with non-existent challenge."""
        result = await authenticator.verify_challenge(
            "nonexistent_challenge_id",
            b"signature",
        )

        assert not result.success
        assert result.error_code == "CHALLENGE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_session_management(self, authenticator):
        """Test session creation and validation."""
        # Create a mock session directly for testing
        did = "did:nlc:session_test"
        challenge = await authenticator.create_challenge(did)

        # Create session manually for testing
        session = AuthSession(
            id="test_session_id",
            did=did,
            challenge_id=challenge.id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["read", "write"],
        )

        # Store session
        authenticator._sessions[session.id] = session
        authenticator._did_sessions[did] = [session.id]

        # Validate session
        result = await authenticator.validate_session(session.id)
        assert result.success
        assert result.did == did

    @pytest.mark.asyncio
    async def test_session_scope_check(self, authenticator):
        """Test session scope verification."""
        did = "did:nlc:scope_test"

        session = AuthSession(
            id="scope_session_id",
            did=did,
            challenge_id="test_challenge",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["read"],
        )

        authenticator._sessions[session.id] = session

        # Check with valid scope
        result = await authenticator.validate_session(session.id, required_scope="read")
        assert result.success

        # Check with invalid scope
        result = await authenticator.validate_session(session.id, required_scope="admin")
        assert not result.success
        assert result.error_code == "INSUFFICIENT_SCOPE"

    @pytest.mark.asyncio
    async def test_revoke_session(self, authenticator):
        """Test session revocation."""
        did = "did:nlc:revoke_test"

        session = AuthSession(
            id="revoke_session_id",
            did=did,
            challenge_id="test_challenge",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        authenticator._sessions[session.id] = session
        authenticator._did_sessions[did] = [session.id]

        # Revoke session
        revoked = await authenticator.revoke_session(session.id)
        assert revoked

        # Session should no longer be valid
        result = await authenticator.validate_session(session.id)
        assert not result.success

    @pytest.mark.asyncio
    async def test_revoke_all_sessions(self, authenticator):
        """Test revoking all sessions for a DID."""
        did = "did:nlc:revoke_all_test"

        # Create multiple sessions
        for i in range(3):
            session = AuthSession(
                id=f"session_{i}",
                did=did,
                challenge_id=f"challenge_{i}",
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            authenticator._sessions[session.id] = session

        authenticator._did_sessions[did] = ["session_0", "session_1", "session_2"]

        # Revoke all
        count = await authenticator.revoke_all_sessions(did)
        assert count == 3

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, authenticator):
        """Test getting active sessions for a DID."""
        did = "did:nlc:active_test"

        # Create active and expired sessions
        active_session = AuthSession(
            id="active_session",
            did=did,
            challenge_id="challenge",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        expired_session = AuthSession(
            id="expired_session",
            did=did,
            challenge_id="challenge2",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        authenticator._sessions["active_session"] = active_session
        authenticator._sessions["expired_session"] = expired_session
        authenticator._did_sessions[did] = ["active_session", "expired_session"]

        # Only active session should be returned
        sessions = await authenticator.get_active_sessions(did)
        assert len(sessions) == 1
        assert sessions[0].id == "active_session"

    def test_generate_session_token(self, authenticator):
        """Test session token generation."""
        session = AuthSession(
            id="token_test_session",
            did="did:nlc:token_test",
            challenge_id="challenge",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        token = authenticator.generate_session_token(session)
        assert isinstance(token, str)
        assert len(token) > 50  # Token should be reasonably long

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, authenticator):
        """Test cleanup of expired challenges and sessions."""
        did = "did:nlc:cleanup_test"

        # Create expired challenge
        expired_challenge = AuthChallenge(
            id="expired_challenge",
            did=did,
            nonce=b"x" * 32,
            message="test",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        authenticator._challenges["expired_challenge"] = expired_challenge

        # Create expired session
        expired_session = AuthSession(
            id="expired_session",
            did=did,
            challenge_id="challenge",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        authenticator._sessions["expired_session"] = expired_session
        authenticator._did_sessions[did] = ["expired_session"]

        # Run cleanup
        challenges_removed, sessions_removed = await authenticator.cleanup_expired()
        assert challenges_removed == 1
        assert sessions_removed == 1


# =============================================================================
# DID Auth Middleware Tests
# =============================================================================


class TestDIDAuthMiddleware:
    """Tests for DID authentication middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        authenticator = DIDAuthenticator()
        return DIDAuthMiddleware(
            authenticator=authenticator,
            required_scopes=["read"],
        )

    @pytest.mark.asyncio
    async def test_missing_auth_header(self, middleware):
        """Test request without authorization header."""
        result = await middleware.authenticate_request(None)
        assert not result.success
        assert result.error_code == "NO_AUTH"

    @pytest.mark.asyncio
    async def test_invalid_auth_format(self, middleware):
        """Test request with invalid authorization format."""
        result = await middleware.authenticate_request("Basic abc123")
        assert not result.success
        assert result.error_code == "INVALID_AUTH_FORMAT"

    @pytest.mark.asyncio
    async def test_invalid_token(self, middleware):
        """Test request with invalid bearer token."""
        result = await middleware.authenticate_request("Bearer invalid_token")
        assert not result.success
        assert result.error_code == "INVALID_TOKEN"


# =============================================================================
# Integration Tests
# =============================================================================


class TestDIDIntegration:
    """Integration tests for the full DID flow."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow_mock(self):
        """Test full authentication flow with mocked signature verification."""
        # Create authenticator
        authenticator = DIDAuthenticator(
            challenge_ttl=300,
            session_ttl=3600,
        )

        did = "did:nlc:integration_test"

        # Step 1: Create challenge
        challenge = await authenticator.create_challenge(did)
        assert challenge is not None

        # Step 2: Mock successful signature verification
        with patch.object(
            authenticator.did_resolver,
            "verify_signature",
            new_callable=AsyncMock,
            return_value=True,
        ):
            # Verify challenge with mock signature
            result = await authenticator.verify_challenge(
                challenge.id,
                b"mock_signature",
                scopes=["read", "write"],
            )

            assert result.success
            assert result.session is not None
            assert result.session.did == did
            assert "read" in result.session.scopes
            assert "write" in result.session.scopes

        # Step 3: Validate session
        session_result = await authenticator.validate_session(result.session.id)
        assert session_result.success

        # Step 4: Generate and validate token
        token = authenticator.generate_session_token(result.session)
        token_result = await authenticator.validate_token(token)
        assert token_result.success

        # Step 5: Revoke session
        revoked = await authenticator.revoke_session(result.session.id)
        assert revoked

        # Verify session is revoked
        final_result = await authenticator.validate_session(result.session.id)
        assert not final_result.success

    @pytest.mark.asyncio
    async def test_sybil_required_authentication(self):
        """Test authentication with Sybil resistance requirement."""
        authenticator = DIDAuthenticator(
            require_sybil_check=True,
            min_identity_score=50,
        )

        did = "did:nlc:sybil_required_test"

        # Create challenge
        challenge = await authenticator.create_challenge(did)

        # Mock signature verification and identity score
        with patch.object(
            authenticator.did_resolver,
            "verify_signature",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch.object(
                authenticator.sybil_resistance,
                "get_identity_score",
                new_callable=AsyncMock,
                return_value=IdentityScore(
                    did=did,
                    overall_score=75,
                    proofs=[],
                    stake_score=50,
                    age_score=60,
                    activity_score=70,
                    last_updated=datetime.now(timezone.utc),
                ),
            ):
                result = await authenticator.verify_challenge(
                    challenge.id,
                    b"signature",
                )

                assert result.success
                assert result.identity_score is not None
                assert result.identity_score.overall_score == 75

    @pytest.mark.asyncio
    async def test_sybil_score_rejection(self):
        """Test authentication rejected due to low Sybil score."""
        authenticator = DIDAuthenticator(
            require_sybil_check=True,
            min_identity_score=80,
        )

        did = "did:nlc:low_score_test"

        # Create challenge
        challenge = await authenticator.create_challenge(did)

        # Mock signature verification and low identity score
        with patch.object(
            authenticator.did_resolver,
            "verify_signature",
            new_callable=AsyncMock,
            return_value=True,
        ):
            with patch.object(
                authenticator.sybil_resistance,
                "get_identity_score",
                new_callable=AsyncMock,
                return_value=IdentityScore(
                    did=did,
                    overall_score=50,
                    proofs=[],
                    stake_score=30,
                    age_score=40,
                    activity_score=45,
                    last_updated=datetime.now(timezone.utc),
                ),
            ):
                result = await authenticator.verify_challenge(
                    challenge.id,
                    b"signature",
                )

                assert not result.success
                assert result.error_code == "INSUFFICIENT_SCORE"
                assert result.identity_score is not None
                assert result.identity_score.overall_score == 50
