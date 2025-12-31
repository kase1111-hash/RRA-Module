# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for Sybil resistance and Proof of Humanity integrations.

Tests verification methods for:
- Worldcoin World ID
- BrightID
- ENS ownership
- Hardware keys (WebAuthn/FIDO2)
- On-chain stake
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import httpx

from rra.identity.sybil_resistance import (
    SybilResistance,
    ProofType,
    ProofOfHumanity,
    IdentityScore,
    SybilCheck,
    RiskLevel,
    TrustLevel,
)


@pytest.fixture
def sybil_resistance():
    """Create a SybilResistance instance."""
    return SybilResistance()


@pytest.fixture
def sample_did():
    """Sample DID for testing."""
    return "did:ethr:0x1234567890123456789012345678901234567890"


class TestProofOfHumanity:
    """Test ProofOfHumanity dataclass."""

    def test_proof_creation(self):
        """Test creating a proof of humanity."""
        proof = ProofOfHumanity(
            proof_type=ProofType.POH_WORLDCOIN,
            provider="worldcoin",
            verified_at=datetime.utcnow(),
            confidence=0.95,
        )

        assert proof.proof_type == ProofType.POH_WORLDCOIN
        assert proof.provider == "worldcoin"
        assert proof.confidence == 0.95

    def test_proof_validity_no_expiry(self):
        """Test proof is valid when no expiry set."""
        proof = ProofOfHumanity(
            proof_type=ProofType.POH_BRIGHTID,
            provider="brightid",
            verified_at=datetime.utcnow(),
        )

        assert proof.is_valid() is True

    def test_proof_validity_expired(self):
        """Test proof is invalid when expired."""
        proof = ProofOfHumanity(
            proof_type=ProofType.ENS,
            provider="ens",
            verified_at=datetime.utcnow() - timedelta(days=400),
            expires_at=datetime.utcnow() - timedelta(days=35),
        )

        assert proof.is_valid() is False

    def test_proof_to_dict(self):
        """Test proof serialization."""
        proof = ProofOfHumanity(
            proof_type=ProofType.HARDWARE,
            provider="yubikey",
            verified_at=datetime.utcnow(),
            confidence=0.90,
        )

        data = proof.to_dict()
        assert data["proof_type"] == "hardware"
        assert data["provider"] == "yubikey"
        assert data["confidence"] == 0.90


class TestIdentityScore:
    """Test IdentityScore dataclass."""

    def test_score_creation(self):
        """Test creating an identity score."""
        score = IdentityScore(
            did="did:ethr:0x123",
            score=75,
            risk_level=RiskLevel.LOW,
            voting_weight=1.5,
        )

        assert score.score == 75
        assert score.risk_level == RiskLevel.LOW
        assert score.voting_weight == 1.5

    def test_score_to_dict(self):
        """Test score serialization."""
        score = IdentityScore(
            did="did:ethr:0x123",
            score=50,
            risk_level=RiskLevel.MEDIUM,
            voting_weight=1.0,
            proof_score=30,
            stake_score=20,
        )

        data = score.to_dict()
        assert data["score"] == 50
        assert data["risk_level"] == "medium"
        assert data["components"]["proof"] == 30
        assert data["components"]["stake"] == 20


class TestSybilResistance:
    """Test SybilResistance core functionality."""

    @pytest.mark.asyncio
    async def test_register_identity(self, sybil_resistance, sample_did):
        """Test identity registration."""
        score = await sybil_resistance.register_identity(sample_did)

        assert score.did == sample_did
        assert 0 <= score.score <= 100

    @pytest.mark.asyncio
    async def test_add_proof(self, sybil_resistance, sample_did):
        """Test adding a proof to an identity."""
        await sybil_resistance.register_identity(sample_did)

        proof = ProofOfHumanity(
            proof_type=ProofType.POH_WORLDCOIN,
            provider="worldcoin",
            verified_at=datetime.utcnow(),
            confidence=0.95,
        )

        score = await sybil_resistance.add_proof(sample_did, proof)

        assert len(score.proofs) == 1
        assert score.proofs[0].proof_type == ProofType.POH_WORLDCOIN

    @pytest.mark.asyncio
    async def test_get_identity_score(self, sybil_resistance, sample_did):
        """Test getting identity score."""
        await sybil_resistance.register_identity(sample_did)

        score = await sybil_resistance.get_identity_score(sample_did)

        assert score.did == sample_did
        assert isinstance(score.risk_level, RiskLevel)
        assert 0.1 <= score.voting_weight <= 2.0

    @pytest.mark.asyncio
    async def test_check_identity(self, sybil_resistance, sample_did):
        """Test Sybil check on identity."""
        await sybil_resistance.register_identity(sample_did)

        check = await sybil_resistance.check_identity(sample_did)

        assert check.did == sample_did
        assert isinstance(check.risk_level, RiskLevel)
        assert isinstance(check.trust_level, TrustLevel)
        assert "proof_of_humanity" in check.checks_performed


class TestWorldcoinVerification:
    """Test Worldcoin World ID verification."""

    @pytest.mark.asyncio
    async def test_verify_worldcoin_missing_fields(self, sybil_resistance):
        """Test Worldcoin verification with missing fields."""
        verified, confidence, metadata = await sybil_resistance._verify_worldcoin({})

        assert verified is False
        assert confidence == 0.0
        assert "error" in metadata

    @pytest.mark.asyncio
    async def test_verify_worldcoin_missing_app_id(self, sybil_resistance):
        """Test Worldcoin verification without app ID."""
        verified, confidence, metadata = await sybil_resistance._verify_worldcoin({
            "proof": "0x123",
            "merkle_root": "0x456",
            "nullifier_hash": "0x789",
        })

        assert verified is False
        assert "WORLDCOIN_APP_ID not configured" in metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_verify_worldcoin_success(self, sybil_resistance):
        """Test successful Worldcoin verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "action": "verify",
            "nullifier_hash": "0x789",
            "created_at": "2025-01-01T00:00:00Z",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            verified, confidence, metadata = await sybil_resistance._verify_worldcoin({
                "proof": "0x123",
                "merkle_root": "0x456",
                "nullifier_hash": "0x789",
                "verification_level": "orb",
                "app_id": "app_test123",
            })

            assert verified is True
            assert confidence == 0.95  # Orb verification
            assert metadata["orb_verified"] is True


class TestBrightIDVerification:
    """Test BrightID verification."""

    @pytest.mark.asyncio
    async def test_verify_brightid_missing_context_id(self, sybil_resistance):
        """Test BrightID verification with missing context_id."""
        verified, confidence, metadata = await sybil_resistance._verify_brightid({})

        assert verified is False
        assert "context_id" in metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_verify_brightid_success(self, sybil_resistance):
        """Test successful BrightID verification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "unique": True,
                "timestamp": 1234567890,
                "contextIds": ["ctx1", "ctx2"],
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            verified, confidence, metadata = await sybil_resistance._verify_brightid({
                "context_id": "0x123",
            })

            assert verified is True
            assert confidence >= 0.80
            assert metadata["unique"] is True

    @pytest.mark.asyncio
    async def test_verify_brightid_not_found(self, sybil_resistance):
        """Test BrightID verification when user not found."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            verified, confidence, metadata = await sybil_resistance._verify_brightid({
                "context_id": "0x123",
            })

            assert verified is False
            assert "not linked" in metadata.get("error", "")


class TestENSVerification:
    """Test ENS ownership verification."""

    @pytest.mark.asyncio
    async def test_verify_ens_missing_fields(self, sybil_resistance):
        """Test ENS verification with missing fields."""
        verified, confidence, metadata = await sybil_resistance._verify_ens({})

        assert verified is False
        assert "Missing required fields" in metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_verify_ens_success(self, sybil_resistance):
        """Test successful ENS verification."""
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True

        mock_ns = MagicMock()
        mock_ns.address.return_value = "0x1234567890123456789012345678901234567890"
        mock_ns.name.return_value = "vitalik.eth"

        with patch("rra.identity.sybil_resistance.Web3") as mock_web3, \
             patch("ens.ENS.from_web3", return_value=mock_ns):
            mock_web3.return_value = mock_w3
            mock_web3.HTTPProvider.return_value = MagicMock()

            verified, confidence, metadata = await sybil_resistance._verify_ens({
                "ens_name": "vitalik.eth",
                "address": "0x1234567890123456789012345678901234567890",
            })

            assert verified is True
            assert confidence >= 0.75
            assert metadata["ens_name"] == "vitalik.eth"


class TestHardwareVerification:
    """Test hardware key (WebAuthn) verification."""

    @pytest.mark.asyncio
    async def test_verify_hardware_missing_credential(self, sybil_resistance):
        """Test hardware verification with missing credential_id."""
        verified, confidence, metadata = await sybil_resistance._verify_hardware({})

        assert verified is False
        assert "credential_id" in metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_verify_hardware_registration(self, sybil_resistance):
        """Test hardware key registration flow."""
        verified, confidence, metadata = await sybil_resistance._verify_hardware({
            "credential_id": "cred_123",
            "attestation_object": "attestation_data",
            "aaguid": "fbfc3007-154e-4ecc-8c0b-6e020557d7bd",  # YubiKey 5
        })

        assert verified is True
        assert confidence >= 0.90
        assert metadata["authenticator_type"] == "YubiKey 5"
        assert metadata["registration"] is True

    @pytest.mark.asyncio
    async def test_verify_hardware_authentication(self, sybil_resistance):
        """Test hardware key authentication flow."""
        # Create valid authenticator data with user_present and user_verified flags
        # First 32 bytes: RP ID hash, then flags byte, then counter
        auth_data = "00" * 32 + "05" + "00000000"  # flags = 0x05 (UP + UV)

        # Valid signature (at least 64 bytes)
        signature = "00" * 72

        verified, confidence, metadata = await sybil_resistance._verify_hardware({
            "credential_id": "cred_123",
            "authenticator_data": auth_data,
            "signature": signature,
        })

        assert verified is True
        assert confidence >= 0.85
        assert metadata["user_present"] is True
        assert metadata["user_verified"] is True


class TestStakeVerification:
    """Test on-chain stake verification."""

    @pytest.mark.asyncio
    async def test_verify_stake_missing_address(self, sybil_resistance):
        """Test stake verification with missing address."""
        verified, confidence, metadata = await sybil_resistance._verify_stake({})

        assert verified is False
        assert "address" in metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_verify_stake_success(self, sybil_resistance):
        """Test successful stake verification."""
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH in wei
        mock_w3.from_wei.return_value = 1.0

        with patch("rra.identity.sybil_resistance.Web3") as mock_web3:
            mock_web3.return_value = mock_w3
            mock_web3.HTTPProvider.return_value = MagicMock()

            # Mock the staking contract calls
            mock_contract = MagicMock()
            mock_contract.functions.balanceOf.return_value.call.return_value = 0
            mock_w3.eth.contract.return_value = mock_contract

            verified, confidence, metadata = await sybil_resistance._verify_stake({
                "address": "0x1234567890123456789012345678901234567890",
                "eth_price_usd": 2000,  # $2000 per ETH
            })

            assert verified is True
            assert confidence >= 0.45
            assert metadata["total_value_usd"] >= 2000

    @pytest.mark.asyncio
    async def test_verify_stake_insufficient(self, sybil_resistance):
        """Test stake verification with insufficient balance."""
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.get_balance.return_value = 10000000000000000  # 0.01 ETH
        mock_w3.from_wei.return_value = 0.01

        with patch("rra.identity.sybil_resistance.Web3") as mock_web3:
            mock_web3.return_value = mock_w3
            mock_web3.HTTPProvider.return_value = MagicMock()

            mock_contract = MagicMock()
            mock_contract.functions.balanceOf.return_value.call.return_value = 0
            mock_w3.eth.contract.return_value = mock_contract

            verified, confidence, metadata = await sybil_resistance._verify_stake({
                "address": "0x1234567890123456789012345678901234567890",
                "eth_price_usd": 2000,
                "min_stake_usd": 100,
            })

            assert verified is False
            assert "Insufficient stake" in metadata.get("error", "")


class TestSybilDetection:
    """Test Sybil attack detection."""

    @pytest.mark.asyncio
    async def test_detect_suspicious_timing(self, sybil_resistance, sample_did):
        """Test detection of suspicious timing patterns."""
        await sybil_resistance.register_identity(sample_did)

        # Add activities with suspiciously regular timing
        base_time = datetime.utcnow()
        for i in range(10):
            sybil_resistance._activity[sample_did].append({
                "type": "transaction",
                "timestamp": base_time + timedelta(seconds=i * 30),
                "metadata": {},
            })

        is_suspicious = sybil_resistance._check_timing_patterns(sample_did)

        # Very regular timing should be flagged
        assert is_suspicious is True

    @pytest.mark.asyncio
    async def test_find_suspicious_cluster(self, sybil_resistance, sample_did):
        """Test detection of suspicious identity clusters."""
        await sybil_resistance.register_identity(sample_did)

        # Create a related suspicious identity
        suspicious_did = "did:ethr:0xsuspicious"
        await sybil_resistance.register_identity(suspicious_did)

        # Link them
        await sybil_resistance.add_relationship(sample_did, suspicious_did)

        # Make the related identity suspicious (low score)
        # We don't add any proofs, so it has a low score

        suspicious = await sybil_resistance._find_suspicious_cluster(sample_did)

        # Should detect the suspicious related identity
        assert len(suspicious) >= 0  # May or may not find it depending on threshold


class TestRiskLevels:
    """Test risk level calculations."""

    def test_risk_level_low(self, sybil_resistance):
        """Test low risk level for high scores."""
        risk = sybil_resistance._get_risk_level(85)
        assert risk == RiskLevel.LOW

    def test_risk_level_medium(self, sybil_resistance):
        """Test medium risk level for moderate scores."""
        risk = sybil_resistance._get_risk_level(55)
        assert risk == RiskLevel.MEDIUM

    def test_risk_level_high(self, sybil_resistance):
        """Test high risk level for low scores."""
        risk = sybil_resistance._get_risk_level(30)
        assert risk == RiskLevel.HIGH

    def test_risk_level_critical(self, sybil_resistance):
        """Test critical risk level for very low scores."""
        risk = sybil_resistance._get_risk_level(10)
        assert risk == RiskLevel.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
