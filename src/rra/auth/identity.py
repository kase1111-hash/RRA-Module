# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Hardware-Backed Identity for ZK Proofs.

Combines FIDO2 credentials with ZK identity commitments:
- Credential-bound identity secrets
- Poseidon-compatible commitment generation
- Nullifier derivation for anonymity with accountability
- Merkle proof generation for group membership

This enables "Hardware-Verified Anonymity":
- Registration links credential to identity (one-time, verifiable)
- Actions prove membership without revealing which credential
- Nullifiers prevent double-spending while maintaining privacy
"""

import os
import hashlib
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from eth_utils import keccak


@dataclass
class HardwareIdentity:
    """
    Identity backed by a FIDO2 hardware credential.

    Combines hardware security with ZK privacy:
    - identity_secret: Random secret known only to user
    - credential_hash: Hash binding to specific hardware credential
    - identity_commitment: Public commitment for group registration
    """
    identity_secret: int
    credential_hash: bytes
    identity_commitment: bytes
    nullifier_seed: bytes

    @classmethod
    def generate(
        cls,
        credential_public_key: bytes,
        user_entropy: Optional[bytes] = None
    ) -> 'HardwareIdentity':
        """
        Generate a new hardware-backed identity.

        Args:
            credential_public_key: FIDO2 credential's public key
            user_entropy: Optional additional entropy from user

        Returns:
            New HardwareIdentity
        """
        # Generate identity secret
        secret_entropy = os.urandom(32)
        if user_entropy:
            secret_entropy = hashlib.sha256(secret_entropy + user_entropy).digest()

        identity_secret = int.from_bytes(secret_entropy, 'big')

        # Compute credential hash
        credential_hash = keccak(credential_public_key)

        # Compute identity commitment
        # commitment = Poseidon(identity_secret, credential_hash)
        # Using keccak as Poseidon mock for compatibility
        commitment = poseidon_mock([identity_secret, int.from_bytes(credential_hash, 'big')])
        identity_commitment = commitment.to_bytes(32, 'big')

        # Nullifier seed for deriving action-specific nullifiers
        nullifier_seed = keccak(secret_entropy + credential_hash)

        return cls(
            identity_secret=identity_secret,
            credential_hash=credential_hash,
            identity_commitment=identity_commitment,
            nullifier_seed=nullifier_seed
        )

    def derive_nullifier(self, external_nullifier: int) -> bytes:
        """
        Derive a nullifier for a specific action/scope.

        Args:
            external_nullifier: Scope identifier (e.g., action hash, group ID)

        Returns:
            32-byte nullifier hash
        """
        # nullifier = Poseidon(identity_secret, external_nullifier)
        nullifier_int = poseidon_mock([self.identity_secret, external_nullifier])
        return nullifier_int.to_bytes(32, 'big')

    def prepare_zk_inputs(
        self,
        action_hash: bytes,
        external_nullifier: int,
        action_nonce: Optional[bytes] = None
    ) -> Dict[str, str]:
        """
        Prepare inputs for hardware_identity.circom circuit.

        Args:
            action_hash: Hash of the action being authorized
            external_nullifier: Scope identifier
            action_nonce: Optional nonce (random if not provided)

        Returns:
            Dictionary of inputs for ZK proof generation
        """
        nonce = action_nonce or os.urandom(16)
        nonce_int = int.from_bytes(nonce[:16].ljust(16, b'\x00'), 'big')

        nullifier = self.derive_nullifier(external_nullifier)

        return {
            "identitySecret": str(self.identity_secret),
            "credentialHash": str(int.from_bytes(self.credential_hash, 'big')),
            "actionNonce": str(nonce_int),
            "identityCommitment": str(int.from_bytes(self.identity_commitment, 'big')),
            "actionHash": str(int.from_bytes(action_hash[:32].ljust(32, b'\x00'), 'big')),
            "nullifierHash": str(int.from_bytes(nullifier, 'big'))
        }

    def prepare_membership_proof_inputs(
        self,
        merkle_siblings: List[bytes],
        merkle_path_indices: List[int],
        signal_hash: bytes,
        external_nullifier: int
    ) -> Dict[str, Any]:
        """
        Prepare inputs for semaphore_membership.circom circuit.

        Args:
            merkle_siblings: Merkle proof sibling hashes
            merkle_path_indices: Path indices (0 = left, 1 = right)
            signal_hash: Hash of the action/signal
            external_nullifier: Scope identifier

        Returns:
            Dictionary of inputs for ZK proof generation
        """
        nullifier = self.derive_nullifier(external_nullifier)

        return {
            "identitySecret": str(self.identity_secret),
            "credentialCommitment": str(int.from_bytes(self.credential_hash, 'big')),
            "merkleProofSiblings": [str(int.from_bytes(s, 'big')) for s in merkle_siblings],
            "merkleProofPathIndices": [str(i) for i in merkle_path_indices],
            "merkleRoot": "",  # To be filled from contract
            "nullifierHash": str(int.from_bytes(nullifier, 'big')),
            "signalHash": str(int.from_bytes(signal_hash[:32].ljust(32, b'\x00'), 'big')),
            "externalNullifier": str(external_nullifier)
        }

    def to_dict(self) -> Dict[str, str]:
        """Serialize identity (CAUTION: includes secret!)."""
        return {
            "identity_secret": hex(self.identity_secret),
            "credential_hash": self.credential_hash.hex(),
            "identity_commitment": self.identity_commitment.hex(),
            "nullifier_seed": self.nullifier_seed.hex()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'HardwareIdentity':
        """Deserialize identity."""
        return cls(
            identity_secret=int(data["identity_secret"], 16),
            credential_hash=bytes.fromhex(data["credential_hash"]),
            identity_commitment=bytes.fromhex(data["identity_commitment"]),
            nullifier_seed=bytes.fromhex(data["nullifier_seed"])
        )


class IdentityGroupManager:
    """
    Manages Semaphore-style identity groups for anonymous hardware verification.

    Provides:
    - Group creation and member management
    - Merkle tree operations for membership proofs
    - Nullifier tracking for replay prevention
    """

    def __init__(self, depth: int = 20):
        """
        Initialize group manager.

        Args:
            depth: Merkle tree depth (max members = 2^depth)
        """
        self.depth = depth
        self.groups: Dict[int, Dict[str, Any]] = {}
        self.group_count = 0

        # Zero value for empty leaves (same as Semaphore)
        self.zero_value = int.from_bytes(
            keccak(b"Semaphore"),
            'big'
        ) % (2**256 - 1)

    def create_group(self, name: str) -> int:
        """Create a new identity group."""
        group_id = self.group_count
        self.group_count += 1

        self.groups[group_id] = {
            "name": name,
            "members": [],  # List of identity commitments
            "merkle_root": self._compute_zero_root(),
            "nullifiers": set()
        }

        return group_id

    def add_member(
        self,
        group_id: int,
        identity: HardwareIdentity
    ) -> Tuple[int, bytes]:
        """
        Add a member to a group.

        Args:
            group_id: Group to add to
            identity: Hardware identity to add

        Returns:
            Tuple of (member_index, new_merkle_root)
        """
        group = self.groups.get(group_id)
        if not group:
            raise ValueError("Group not found")

        commitment = identity.identity_commitment
        if commitment in group["members"]:
            raise ValueError("Already a member")

        index = len(group["members"])
        if index >= (1 << self.depth):
            raise ValueError("Group is full")

        group["members"].append(commitment)
        group["merkle_root"] = self._compute_root(group["members"])

        return index, group["merkle_root"]

    def get_merkle_proof(
        self,
        group_id: int,
        identity: HardwareIdentity
    ) -> Tuple[List[bytes], List[int]]:
        """
        Get Merkle proof for a member.

        Args:
            group_id: Group ID
            identity: Identity to prove membership for

        Returns:
            Tuple of (siblings, path_indices)
        """
        group = self.groups.get(group_id)
        if not group:
            raise ValueError("Group not found")

        commitment = identity.identity_commitment
        if commitment not in group["members"]:
            raise ValueError("Not a member")

        index = group["members"].index(commitment)

        # Compute Merkle proof
        siblings = []
        path_indices = []

        current_index = index
        leaves = [int.from_bytes(m, 'big') for m in group["members"]]

        # Pad to power of 2
        tree_size = 1 << self.depth
        leaves.extend([self.zero_value] * (tree_size - len(leaves)))

        current_level = leaves

        for level in range(self.depth):
            sibling_index = current_index ^ 1  # XOR to get sibling
            if sibling_index < len(current_level):
                siblings.append(current_level[sibling_index].to_bytes(32, 'big'))
            else:
                siblings.append(self._get_zero_hash(level).to_bytes(32, 'big'))

            path_indices.append(current_index & 1)  # 0 = left, 1 = right

            # Compute next level
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else self._get_zero_hash(level)
                parent = poseidon_mock([left, right])
                next_level.append(parent)

            current_level = next_level
            current_index //= 2

        return siblings, path_indices

    def verify_nullifier(
        self,
        group_id: int,
        nullifier_hash: bytes
    ) -> bool:
        """Check if nullifier has been used."""
        group = self.groups.get(group_id)
        if not group:
            return False
        return nullifier_hash in group["nullifiers"]

    def use_nullifier(
        self,
        group_id: int,
        nullifier_hash: bytes
    ) -> bool:
        """Mark nullifier as used. Returns False if already used."""
        group = self.groups.get(group_id)
        if not group:
            return False

        if nullifier_hash in group["nullifiers"]:
            return False

        group["nullifiers"].add(nullifier_hash)
        return True

    def _compute_root(self, members: List[bytes]) -> bytes:
        """Compute Merkle root from members."""
        if not members:
            return self._compute_zero_root()

        leaves = [int.from_bytes(m, 'big') for m in members]

        # Pad to power of 2
        tree_size = 1 << self.depth
        leaves.extend([self.zero_value] * (tree_size - len(leaves)))

        current_level = leaves

        for level in range(self.depth):
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1]
                parent = poseidon_mock([left, right])
                next_level.append(parent)
            current_level = next_level

        return current_level[0].to_bytes(32, 'big')

    def _compute_zero_root(self) -> bytes:
        """Compute root of empty tree."""
        current = self.zero_value
        for _ in range(self.depth):
            current = poseidon_mock([current, current])
        return current.to_bytes(32, 'big')

    def _get_zero_hash(self, level: int) -> int:
        """Get zero hash for a given level."""
        current = self.zero_value
        for _ in range(level):
            current = poseidon_mock([current, current])
        return current


# =========================================================================
# Helper Functions
# =========================================================================

def poseidon_mock(inputs: List[int]) -> int:
    """
    Mock Poseidon hash using keccak256.

    In production, use actual Poseidon implementation for ZK compatibility.
    """
    data = b''
    for inp in inputs:
        data += inp.to_bytes(32, 'big')

    return int.from_bytes(keccak(data), 'big')


def generate_identity_commitment(
    identity_secret: int,
    credential_hash: bytes
) -> bytes:
    """
    Generate identity commitment from secret and credential.

    commitment = Poseidon(identity_secret, credential_hash)
    """
    credential_int = int.from_bytes(credential_hash, 'big')
    commitment_int = poseidon_mock([identity_secret, credential_int])
    return commitment_int.to_bytes(32, 'big')


def compute_credential_hash(public_key: bytes) -> bytes:
    """Compute hash of FIDO2 credential public key."""
    return keccak(public_key)
