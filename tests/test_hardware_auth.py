# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Tests for Hardware Authentication Infrastructure.

Tests FIDO2/WebAuthn integration, hardware identities,
and scoped delegation for RRA agents.
"""

import pytest
import os
from datetime import datetime, timedelta


class TestWebAuthnClient:
    """Tests for WebAuthn client."""

    def test_create_challenge(self):
        """Test challenge creation."""
        from rra.auth.webauthn import WebAuthnClient

        client = WebAuthnClient("rra.example.com", "RRA Module")
        action_hash = os.urandom(32)

        challenge = client.create_challenge(action_hash)

        assert challenge.value is not None
        assert len(challenge.value) == 32
        assert challenge.action_hash == action_hash
        assert challenge.is_valid

    def test_challenge_expiration(self):
        """Test challenge expiration."""
        from rra.auth.webauthn import WebAuthnClient

        client = WebAuthnClient("rra.example.com", "RRA Module", challenge_timeout=1)
        action_hash = os.urandom(32)

        challenge = client.create_challenge(action_hash)

        # Initially valid
        assert challenge.is_valid

        # Fast-forward time (mock expiration)
        challenge.expires_at = datetime.utcnow() - timedelta(seconds=1)
        assert not challenge.is_valid

    def test_credential_registration(self):
        """Test credential registration."""
        from rra.auth.webauthn import WebAuthnClient

        client = WebAuthnClient("rra.example.com", "RRA Module")

        # Generate mock public key (uncompressed P-256 format)
        mock_public_key = b'\x04' + os.urandom(64)
        credential_id = os.urandom(32)
        user_id = os.urandom(16)

        credential = client.register_credential(
            credential_id=credential_id,
            public_key_cose=mock_public_key,
            user_id=user_id
        )

        assert credential.credential_id == credential_id
        assert credential.user_id == user_id
        assert credential.public_key_x is not None
        assert credential.public_key_y is not None
        assert credential.sign_count == 0

    def test_credential_retrieval(self):
        """Test credential retrieval methods."""
        from rra.auth.webauthn import WebAuthnClient

        client = WebAuthnClient("rra.example.com", "RRA Module")

        mock_public_key = b'\x04' + os.urandom(64)
        credential_id = os.urandom(32)
        user_id = os.urandom(16)

        registered = client.register_credential(
            credential_id=credential_id,
            public_key_cose=mock_public_key,
            user_id=user_id
        )

        # Retrieve by ID
        retrieved = client.get_credential(credential_id)
        assert retrieved is not None
        assert retrieved.credential_id == credential_id

        # Retrieve by hash
        retrieved_by_hash = client.get_credential_by_hash(registered.credential_id_hash)
        assert retrieved_by_hash is not None
        assert retrieved_by_hash.credential_id == credential_id

        # List credentials
        all_creds = client.list_credentials()
        assert len(all_creds) == 1

        user_creds = client.list_credentials(user_id=user_id)
        assert len(user_creds) == 1

    def test_prepare_for_contract(self):
        """Test contract data preparation."""
        from rra.auth.webauthn import WebAuthnClient, AuthenticatorAssertion

        client = WebAuthnClient("rra.example.com", "RRA Module")

        # Register credential
        mock_public_key = b'\x04' + os.urandom(64)
        credential_id = os.urandom(32)
        user_id = os.urandom(16)

        client.register_credential(
            credential_id=credential_id,
            public_key_cose=mock_public_key,
            user_id=user_id
        )

        # Create mock assertion
        rp_id_hash = b'\x00' * 32
        flags = 0x01  # User present
        sign_count = 1
        auth_data = rp_id_hash + bytes([flags]) + sign_count.to_bytes(4, 'big')

        assertion = AuthenticatorAssertion(
            credential_id=credential_id,
            authenticator_data=auth_data,
            client_data_json=b'{"type":"webauthn.get","challenge":"test"}',
            signature=b'\x30\x44\x02\x20' + os.urandom(32) + b'\x02\x20' + os.urandom(32)
        )

        contract_data = client.prepare_for_contract(assertion)

        assert "credentialIdHash" in contract_data
        assert "authenticatorData" in contract_data
        assert "clientDataJSON" in contract_data
        assert "signatureR" in contract_data
        assert "signatureS" in contract_data


class TestHardwareIdentity:
    """Tests for hardware-backed identity."""

    def test_generate_identity(self):
        """Test identity generation."""
        from rra.auth.identity import HardwareIdentity

        credential_public_key = b'\x04' + os.urandom(64)

        identity = HardwareIdentity.generate(credential_public_key)

        assert identity.identity_secret != 0
        assert identity.credential_hash is not None
        assert len(identity.credential_hash) == 32
        assert identity.identity_commitment is not None
        assert len(identity.identity_commitment) == 32

    def test_deterministic_with_entropy(self):
        """Test identity is deterministic with same entropy."""
        from rra.auth.identity import HardwareIdentity

        credential_public_key = b'\x04' + os.urandom(64)
        user_entropy = b'deterministic_test'

        identity1 = HardwareIdentity.generate(credential_public_key, user_entropy)
        identity2 = HardwareIdentity.generate(credential_public_key, user_entropy)

        # Different random components but same structure
        assert identity1.credential_hash == identity2.credential_hash

    def test_nullifier_derivation(self):
        """Test nullifier derivation for different scopes."""
        from rra.auth.identity import HardwareIdentity

        credential_public_key = b'\x04' + os.urandom(64)
        identity = HardwareIdentity.generate(credential_public_key)

        nullifier1 = identity.derive_nullifier(1)
        nullifier2 = identity.derive_nullifier(2)
        nullifier1_again = identity.derive_nullifier(1)

        assert nullifier1 != nullifier2  # Different scopes
        assert nullifier1 == nullifier1_again  # Same scope, deterministic

    def test_prepare_zk_inputs(self):
        """Test ZK input preparation."""
        from rra.auth.identity import HardwareIdentity

        credential_public_key = b'\x04' + os.urandom(64)
        identity = HardwareIdentity.generate(credential_public_key)

        action_hash = os.urandom(32)
        external_nullifier = 12345

        inputs = identity.prepare_zk_inputs(action_hash, external_nullifier)

        assert "identitySecret" in inputs
        assert "credentialHash" in inputs
        assert "actionNonce" in inputs
        assert "identityCommitment" in inputs
        assert "actionHash" in inputs
        assert "nullifierHash" in inputs

    def test_serialization(self):
        """Test identity serialization/deserialization."""
        from rra.auth.identity import HardwareIdentity

        credential_public_key = b'\x04' + os.urandom(64)
        identity = HardwareIdentity.generate(credential_public_key)

        data = identity.to_dict()
        restored = HardwareIdentity.from_dict(data)

        assert restored.identity_secret == identity.identity_secret
        assert restored.credential_hash == identity.credential_hash
        assert restored.identity_commitment == identity.identity_commitment


class TestIdentityGroupManager:
    """Tests for identity group management."""

    def test_create_group(self):
        """Test group creation."""
        from rra.auth.identity import IdentityGroupManager

        manager = IdentityGroupManager(depth=10)

        group_id = manager.create_group("test_group")

        assert group_id == 0
        assert "test_group" == manager.groups[group_id]["name"]
        assert len(manager.groups[group_id]["members"]) == 0

    def test_add_member(self):
        """Test adding members to group."""
        from rra.auth.identity import IdentityGroupManager, HardwareIdentity

        manager = IdentityGroupManager(depth=10)
        group_id = manager.create_group("test_group")

        credential_public_key = b'\x04' + os.urandom(64)
        identity = HardwareIdentity.generate(credential_public_key)

        index, root = manager.add_member(group_id, identity)

        assert index == 0
        assert root is not None
        assert len(manager.groups[group_id]["members"]) == 1

    def test_duplicate_member_rejected(self):
        """Test duplicate member is rejected."""
        from rra.auth.identity import IdentityGroupManager, HardwareIdentity

        manager = IdentityGroupManager(depth=10)
        group_id = manager.create_group("test_group")

        credential_public_key = b'\x04' + os.urandom(64)
        identity = HardwareIdentity.generate(credential_public_key)

        manager.add_member(group_id, identity)

        with pytest.raises(ValueError, match="Already a member"):
            manager.add_member(group_id, identity)

    def test_merkle_proof(self):
        """Test Merkle proof generation."""
        from rra.auth.identity import IdentityGroupManager, HardwareIdentity

        manager = IdentityGroupManager(depth=5)
        group_id = manager.create_group("test_group")

        # Add multiple members
        identities = []
        for i in range(3):
            credential = b'\x04' + os.urandom(64)
            identity = HardwareIdentity.generate(credential)
            manager.add_member(group_id, identity)
            identities.append(identity)

        # Get proof for first member
        siblings, path_indices = manager.get_merkle_proof(group_id, identities[0])

        assert len(siblings) == 5  # depth
        assert len(path_indices) == 5

    def test_nullifier_tracking(self):
        """Test nullifier usage tracking."""
        from rra.auth.identity import IdentityGroupManager

        manager = IdentityGroupManager(depth=10)
        group_id = manager.create_group("test_group")

        nullifier = os.urandom(32)

        # Initially unused
        assert not manager.verify_nullifier(group_id, nullifier)

        # Use it
        assert manager.use_nullifier(group_id, nullifier)

        # Now used
        assert manager.verify_nullifier(group_id, nullifier)

        # Can't use again
        assert not manager.use_nullifier(group_id, nullifier)


class TestScopedDelegation:
    """Tests for scoped delegation."""

    def test_create_delegation(self):
        """Test delegation creation."""
        from rra.auth.delegation import ScopedDelegation, ActionType

        delegation = ScopedDelegation()

        scope = delegation.create_delegation(
            delegator="0x1234567890123456789012345678901234567890",
            agent="0x0987654321098765432109876543210987654321",
            credential_id_hash=os.urandom(32),
            allowed_actions=[ActionType.MARKET_MATCH, ActionType.DISPUTE_STAKE],
            token_limits={
                "0xtoken1": 1000,
                "0xtoken2": 500
            },
            eth_limit=10**18,  # 1 ETH
            duration_seconds=86400,  # 1 day
            description="Test delegation"
        )

        assert scope.is_valid
        assert scope.can_perform_action(ActionType.MARKET_MATCH)
        assert scope.can_perform_action(ActionType.DISPUTE_STAKE)
        assert not scope.can_perform_action(ActionType.WITHDRAW)

    def test_spending_limits(self):
        """Test spending limit enforcement."""
        from rra.auth.delegation import ScopedDelegation, ActionType

        delegation = ScopedDelegation()

        scope = delegation.create_delegation(
            delegator="0x1234567890123456789012345678901234567890",
            agent="0x0987654321098765432109876543210987654321",
            credential_id_hash=os.urandom(32),
            allowed_actions=[ActionType.MARKET_MATCH],
            token_limits={"0xtoken": 100},
            eth_limit=1000,
            duration_seconds=86400,
            description="Limited delegation"
        )

        # Check limits
        assert scope.can_spend_eth(500)
        assert scope.can_spend_eth(1000)
        assert not scope.can_spend_eth(1001)

        assert scope.can_spend_token("0xtoken", 50)
        assert not scope.can_spend_token("0xtoken", 101)
        assert not scope.can_spend_token("0xother", 1)

    def test_use_delegation(self):
        """Test delegation usage."""
        from rra.auth.delegation import ScopedDelegation, ActionType

        manager = ScopedDelegation()

        scope = manager.create_delegation(
            delegator="0x1234567890123456789012345678901234567890",
            agent="0x0987654321098765432109876543210987654321",
            credential_id_hash=os.urandom(32),
            allowed_actions=[ActionType.MARKET_MATCH],
            token_limits={"0xtoken": 100},
            eth_limit=1000,
            duration_seconds=86400,
            description="Test"
        )

        # Use some ETH
        result = manager.use_delegation(
            scope.delegation_id,
            ActionType.MARKET_MATCH,
            None,  # ETH
            500
        )
        assert result

        # Check remaining
        assert scope.eth_remaining == 500

        # Try to overspend
        result = manager.use_delegation(
            scope.delegation_id,
            ActionType.MARKET_MATCH,
            None,
            600
        )
        assert not result

    def test_revoke_delegation(self):
        """Test delegation revocation."""
        from rra.auth.delegation import ScopedDelegation, ActionType

        manager = ScopedDelegation()
        delegator = "0x1234567890123456789012345678901234567890"

        scope = manager.create_delegation(
            delegator=delegator,
            agent="0x0987654321098765432109876543210987654321",
            credential_id_hash=os.urandom(32),
            allowed_actions=[ActionType.MARKET_MATCH],
            token_limits={},
            eth_limit=1000,
            duration_seconds=86400,
            description="Test"
        )

        assert scope.is_valid

        # Revoke
        result = manager.revoke_delegation(scope.delegation_id, delegator, "Testing")
        assert result

        assert not scope.is_valid

        # Can't use after revocation
        result = manager.use_delegation(
            scope.delegation_id,
            ActionType.MARKET_MATCH,
            None,
            100
        )
        assert not result

    def test_check_delegation(self):
        """Test delegation checking without consuming."""
        from rra.auth.delegation import ScopedDelegation, ActionType

        manager = ScopedDelegation()

        scope = manager.create_delegation(
            delegator="0x1234567890123456789012345678901234567890",
            agent="0x0987654321098765432109876543210987654321",
            credential_id_hash=os.urandom(32),
            allowed_actions=[ActionType.MARKET_MATCH],
            token_limits={},
            eth_limit=1000,
            duration_seconds=86400,
            description="Test"
        )

        # Check allowed action
        result = manager.check_delegation(
            scope.delegation_id,
            ActionType.MARKET_MATCH,
            None,
            500
        )
        assert result["allowed"]

        # Check disallowed action
        result = manager.check_delegation(
            scope.delegation_id,
            ActionType.WITHDRAW,
            None,
            500
        )
        assert not result["allowed"]
        assert "not allowed" in result["reason"]


class TestIntegration:
    """Integration tests for hardware auth workflow."""

    def test_full_hardware_identity_workflow(self):
        """Test complete hardware identity workflow."""
        from rra.auth.webauthn import WebAuthnClient
        from rra.auth.identity import HardwareIdentity, IdentityGroupManager
        from rra.auth.delegation import ScopedDelegation, ActionType

        # 1. Setup WebAuthn client
        webauthn_client = WebAuthnClient("rra.example.com", "RRA Module")

        # 2. Register hardware credential
        mock_public_key = b'\x04' + os.urandom(64)
        credential_id = os.urandom(32)
        user_id = os.urandom(16)

        credential = webauthn_client.register_credential(
            credential_id=credential_id,
            public_key_cose=mock_public_key,
            user_id=user_id
        )

        # 3. Generate hardware-backed identity
        identity = HardwareIdentity.generate(credential.public_key_bytes)

        # 4. Add to identity group
        group_manager = IdentityGroupManager(depth=10)
        group_id = group_manager.create_group("dispute_participants")
        member_index, merkle_root = group_manager.add_member(group_id, identity)

        # 5. Create challenge for action
        action_hash = os.urandom(32)
        challenge = webauthn_client.create_challenge(action_hash)

        # 6. Prepare ZK inputs
        zk_inputs = identity.prepare_zk_inputs(
            action_hash=action_hash,
            external_nullifier=group_id
        )

        # 7. Get Merkle proof for membership
        siblings, path_indices = group_manager.get_merkle_proof(group_id, identity)
        membership_inputs = identity.prepare_membership_proof_inputs(
            merkle_siblings=siblings,
            merkle_path_indices=path_indices,
            signal_hash=action_hash,
            external_nullifier=group_id
        )

        # 8. Create delegation for agent
        delegation_manager = ScopedDelegation()
        scope = delegation_manager.create_delegation(
            delegator="0x" + user_id.hex()[:40],
            agent="0x" + os.urandom(20).hex(),
            credential_id_hash=credential.credential_id_hash,
            allowed_actions=[ActionType.DISPUTE_STAKE],
            token_limits={},
            eth_limit=10**18,
            duration_seconds=3600,
            description="1-hour dispute authorization"
        )

        # Verify everything is set up
        assert credential is not None
        assert identity is not None
        assert member_index == 0
        assert zk_inputs is not None
        assert membership_inputs is not None
        assert scope.is_valid
