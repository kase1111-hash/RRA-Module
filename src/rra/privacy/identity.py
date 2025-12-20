# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
ZK Identity Management for ILRM Disputes.

Provides privacy-preserving identity handling:
- Generate identity secrets for dispute participation
- Compute identity hashes for on-chain registration
- Prepare inputs for ZK proof generation
- Manage identity secret storage

Security:
- Identity secrets never exposed on-chain
- Only Poseidon hashes stored in dispute structs
- ZK proofs verify identity without revelation
"""

import os
import json
import hashlib
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from eth_utils import keccak


@dataclass
class DisputeIdentity:
    """Identity for participating in a dispute."""
    identity_secret: int      # Private: 256-bit secret value
    identity_hash: bytes      # Public: Poseidon hash for on-chain
    salt: bytes               # Additional entropy
    address: Optional[str]    # Optional: Associated Ethereum address


class PoseidonMock:
    """
    Mock Poseidon hash for Python.

    In production, use a proper Poseidon implementation
    (e.g., py-poseidon2) for ZK circuit compatibility.

    This mock uses keccak for development/testing.
    """

    @staticmethod
    def hash(inputs: list) -> int:
        """
        Compute Poseidon hash of inputs.

        Args:
            inputs: List of field elements (integers)

        Returns:
            Hash as integer in field
        """
        # Mock: concatenate and keccak
        # Replace with actual Poseidon for production
        data = b''
        for inp in inputs:
            if isinstance(inp, int):
                data += inp.to_bytes(32, 'big')
            elif isinstance(inp, bytes):
                data += inp.ljust(32, b'\x00')
            else:
                data += str(inp).encode().ljust(32, b'\x00')

        hash_bytes = keccak(data)
        return int.from_bytes(hash_bytes, 'big')


class IdentityManager:
    """
    Manager for dispute identity creation and ZK proof preparation.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize identity manager.

        Args:
            storage_path: Optional path for encrypted identity storage
        """
        self.storage_path = storage_path
        self.poseidon = PoseidonMock()

    def generate_identity(
        self,
        address: Optional[str] = None,
        custom_salt: Optional[bytes] = None
    ) -> DisputeIdentity:
        """
        Generate a new dispute identity.

        Args:
            address: Optional Ethereum address to bind identity to
            custom_salt: Optional custom salt (uses random if not provided)

        Returns:
            DisputeIdentity with secret and public hash
        """
        # Generate random salt
        salt = custom_salt or os.urandom(32)

        # Generate identity secret
        if address:
            # Derive from address + salt for deterministic binding
            combined = bytes.fromhex(address[2:]).ljust(20, b'\x00') + salt
            identity_secret = int.from_bytes(keccak(combined), 'big')
        else:
            # Pure random identity
            identity_secret = int.from_bytes(os.urandom(32), 'big')

        # Compute Poseidon hash for on-chain
        identity_hash_int = self.poseidon.hash([identity_secret])
        identity_hash = identity_hash_int.to_bytes(32, 'big')

        return DisputeIdentity(
            identity_secret=identity_secret,
            identity_hash=identity_hash,
            salt=salt,
            address=address
        )

    def derive_identity_from_signature(
        self,
        signature: bytes,
        message: str = "ILRM Identity"
    ) -> DisputeIdentity:
        """
        Derive identity from an Ethereum signature.

        Allows deterministic identity recovery from wallet signature.

        Args:
            signature: Ethereum signature (65 bytes)
            message: Message that was signed

        Returns:
            Deterministically derived identity
        """
        # Hash signature components
        combined = signature + message.encode()
        secret_bytes = keccak(combined)
        identity_secret = int.from_bytes(secret_bytes, 'big')

        # Compute hash
        identity_hash_int = self.poseidon.hash([identity_secret])
        identity_hash = identity_hash_int.to_bytes(32, 'big')

        return DisputeIdentity(
            identity_secret=identity_secret,
            identity_hash=identity_hash,
            salt=signature[:32],
            address=None
        )

    def prepare_zk_inputs(
        self,
        identity: DisputeIdentity,
        identity_manager_hash: bytes
    ) -> Dict[str, str]:
        """
        Prepare inputs for ZK proof generation.

        Compatible with snarkjs input format.

        Args:
            identity: DisputeIdentity to prove
            identity_manager_hash: On-chain hash to verify against

        Returns:
            Dictionary of inputs for prove_identity.circom
        """
        return {
            "identitySecret": str(identity.identity_secret),
            "identityManager": str(int.from_bytes(identity_manager_hash, 'big'))
        }

    def prepare_membership_inputs(
        self,
        identity: DisputeIdentity,
        initiator_hash: bytes,
        counterparty_hash: bytes,
        is_initiator: bool
    ) -> Dict[str, str]:
        """
        Prepare inputs for dispute membership proof.

        Compatible with dispute_membership.circom.

        Args:
            identity: DisputeIdentity to prove
            initiator_hash: On-chain initiator hash
            counterparty_hash: On-chain counterparty hash
            is_initiator: True if proving as initiator

        Returns:
            Dictionary of inputs for dispute_membership.circom
        """
        return {
            "identitySecret": str(identity.identity_secret),
            "roleSelector": "0" if is_initiator else "1",
            "initiatorHash": str(int.from_bytes(initiator_hash, 'big')),
            "counterpartyHash": str(int.from_bytes(counterparty_hash, 'big'))
        }

    def save_identity(
        self,
        identity: DisputeIdentity,
        name: str,
        password: str
    ) -> bool:
        """
        Save identity to encrypted storage.

        Args:
            identity: Identity to save
            name: Identifier for this identity
            password: Encryption password

        Returns:
            True if saved successfully
        """
        if not self.storage_path:
            return False

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        import base64

        # Derive key from password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

        # Serialize identity
        data = {
            "identity_secret": str(identity.identity_secret),
            "identity_hash": identity.identity_hash.hex(),
            "salt": identity.salt.hex(),
            "address": identity.address
        }

        # Encrypt
        f = Fernet(key)
        encrypted = f.encrypt(json.dumps(data).encode())

        # Save
        self.storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self.storage_path / f"{name}.identity"
        with open(file_path, 'wb') as f:
            f.write(salt + encrypted)

        return True

    def load_identity(self, name: str, password: str) -> Optional[DisputeIdentity]:
        """
        Load identity from encrypted storage.

        Args:
            name: Identifier for the identity
            password: Decryption password

        Returns:
            DisputeIdentity or None if not found/invalid
        """
        if not self.storage_path:
            return None

        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        import base64

        file_path = self.storage_path / f"{name}.identity"
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'rb') as f:
                content = f.read()

            salt = content[:16]
            encrypted = content[16:]

            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))

            # Decrypt
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode())

            return DisputeIdentity(
                identity_secret=int(data["identity_secret"]),
                identity_hash=bytes.fromhex(data["identity_hash"]),
                salt=bytes.fromhex(data["salt"]),
                address=data.get("address")
            )
        except Exception:
            return None


# Convenience functions
def generate_identity_secret() -> Tuple[int, bytes]:
    """
    Generate a random identity secret.

    Returns:
        Tuple of (secret_int, hash_bytes)
    """
    manager = IdentityManager()
    identity = manager.generate_identity()
    return identity.identity_secret, identity.identity_hash


def compute_identity_hash(secret: int) -> bytes:
    """
    Compute identity hash from secret.

    Args:
        secret: Identity secret integer

    Returns:
        32-byte Poseidon hash
    """
    poseidon = PoseidonMock()
    hash_int = poseidon.hash([secret])
    return hash_int.to_bytes(32, 'big')
