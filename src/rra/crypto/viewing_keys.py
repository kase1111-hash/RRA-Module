# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Viewing Key Infrastructure using ECIES Encryption.

Provides selective de-anonymization for dispute resolution while
maintaining privacy for normal operations.

Features:
- ECIES encryption on secp256k1 (Ethereum-compatible)
- Per-dispute viewing key generation
- Key derivation for hierarchical access
- Integration with on-chain commitments

Security Model:
- Viewing keys are generated per-dispute
- Only key holders can decrypt dispute evidence
- Keys can be escrowed using Shamir's Secret Sharing
- On-chain commitment proves key existence without revealing it
"""

import os
import hashlib
import hmac
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from eth_keys import keys
from eth_keys.datatypes import PrivateKey, PublicKey
from eth_utils import keccak
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


class KeyPurpose(str, Enum):
    """Purpose of viewing key determines its derivation path."""
    DISPUTE_EVIDENCE = "dispute_evidence"
    LICENSE_METADATA = "license_metadata"
    AUDIT_TRAIL = "audit_trail"
    COMPLIANCE_REPORT = "compliance_report"


@dataclass
class EncryptedData:
    """
    ECIES-encrypted data with all components needed for decryption.
    """
    ephemeral_public_key: bytes  # 65 bytes uncompressed
    iv: bytes                     # 12 bytes for AES-GCM
    ciphertext: bytes             # Encrypted data
    auth_tag: bytes               # 16 bytes authentication tag
    key_commitment: bytes         # 32 bytes - hash of viewing key for verification

    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage."""
        return (
            len(self.ephemeral_public_key).to_bytes(1, 'big') +
            self.ephemeral_public_key +
            self.iv +
            len(self.ciphertext).to_bytes(4, 'big') +
            self.ciphertext +
            self.auth_tag +
            self.key_commitment
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'EncryptedData':
        """Deserialize from bytes."""
        offset = 0

        pk_len = data[offset]
        offset += 1

        ephemeral_pk = data[offset:offset + pk_len]
        offset += pk_len

        iv = data[offset:offset + 12]
        offset += 12

        ct_len = int.from_bytes(data[offset:offset + 4], 'big')
        offset += 4

        ciphertext = data[offset:offset + ct_len]
        offset += ct_len

        auth_tag = data[offset:offset + 16]
        offset += 16

        key_commitment = data[offset:offset + 32]

        return cls(
            ephemeral_public_key=ephemeral_pk,
            iv=iv,
            ciphertext=ciphertext,
            auth_tag=auth_tag,
            key_commitment=key_commitment
        )

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary with hex-encoded values."""
        return {
            "ephemeral_public_key": self.ephemeral_public_key.hex(),
            "iv": self.iv.hex(),
            "ciphertext": self.ciphertext.hex(),
            "auth_tag": self.auth_tag.hex(),
            "key_commitment": self.key_commitment.hex(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'EncryptedData':
        """Create from dictionary with hex-encoded values."""
        return cls(
            ephemeral_public_key=bytes.fromhex(data["ephemeral_public_key"]),
            iv=bytes.fromhex(data["iv"]),
            ciphertext=bytes.fromhex(data["ciphertext"]),
            auth_tag=bytes.fromhex(data["auth_tag"]),
            key_commitment=bytes.fromhex(data["key_commitment"]),
        )


@dataclass
class ViewingKey:
    """
    ECIES viewing key for selective disclosure.

    Generated per-dispute or per-context, allowing selective
    decryption of private data.
    """
    private_key: PrivateKey
    public_key: PublicKey
    purpose: KeyPurpose
    context_id: str  # e.g., dispute ID
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def generate(
        cls,
        purpose: KeyPurpose,
        context_id: str,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'ViewingKey':
        """
        Generate a new viewing key for a specific context.

        Args:
            purpose: The purpose of this key
            context_id: Unique identifier (e.g., dispute ID)
            expires_in_days: Optional expiration
            metadata: Additional metadata

        Returns:
            New ViewingKey instance
        """
        # Generate random private key
        private_key_bytes = os.urandom(32)
        private_key = keys.PrivateKey(private_key_bytes)
        public_key = private_key.public_key

        created_at = datetime.utcnow()
        expires_at = None
        if expires_in_days:
            from datetime import timedelta
            expires_at = created_at + timedelta(days=expires_in_days)

        return cls(
            private_key=private_key,
            public_key=public_key,
            purpose=purpose,
            context_id=context_id,
            created_at=created_at,
            expires_at=expires_at,
            metadata=metadata or {}
        )

    @classmethod
    def derive(
        cls,
        master_key: bytes,
        purpose: KeyPurpose,
        context_id: str,
        index: int = 0
    ) -> 'ViewingKey':
        """
        Derive a viewing key from a master key using HKDF.

        Allows hierarchical key derivation for organized access control.

        Args:
            master_key: 32-byte master secret
            purpose: Key purpose
            context_id: Context identifier
            index: Derivation index for multiple keys per context

        Returns:
            Derived ViewingKey
        """
        # Derive key material using HKDF
        info = f"{purpose.value}:{context_id}:{index}".encode()

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"rra-viewing-key-v1",
            info=info,
            backend=default_backend()
        )

        derived_bytes = hkdf.derive(master_key)
        private_key = keys.PrivateKey(derived_bytes)

        return cls(
            private_key=private_key,
            public_key=private_key.public_key,
            purpose=purpose,
            context_id=context_id,
            created_at=datetime.utcnow(),
            metadata={"derived": True, "index": index}
        )

    @property
    def commitment(self) -> bytes:
        """
        Get on-chain commitment for this key.

        The commitment can be stored on-chain to prove key existence
        without revealing the key itself.
        """
        return keccak(self.public_key.to_bytes())

    @property
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def encrypt(self, plaintext: bytes) -> EncryptedData:
        """
        Encrypt data using ECIES.

        Uses ephemeral key pair for forward secrecy.

        Args:
            plaintext: Data to encrypt

        Returns:
            EncryptedData with all components for decryption
        """
        return ViewingKeyManager.encrypt_to_key(plaintext, self.public_key)

    def decrypt(self, encrypted: EncryptedData) -> bytes:
        """
        Decrypt ECIES-encrypted data.

        Args:
            encrypted: EncryptedData to decrypt

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails or key doesn't match
        """
        return ViewingKeyManager.decrypt_with_key(encrypted, self.private_key)

    def to_dict(self) -> Dict[str, Any]:
        """Export key data (excluding private key for safety)."""
        return {
            "public_key": self.public_key.to_hex(),
            "purpose": self.purpose.value,
            "context_id": self.context_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "commitment": self.commitment.hex(),
            "metadata": self.metadata,
        }

    def export_private(self) -> bytes:
        """Export private key bytes (use with caution)."""
        return self.private_key.to_bytes()

    @classmethod
    def from_private_bytes(
        cls,
        private_bytes: bytes,
        purpose: KeyPurpose,
        context_id: str
    ) -> 'ViewingKey':
        """Restore viewing key from private key bytes."""
        private_key = keys.PrivateKey(private_bytes)
        return cls(
            private_key=private_key,
            public_key=private_key.public_key,
            purpose=purpose,
            context_id=context_id,
            created_at=datetime.utcnow(),
        )


class ViewingKeyManager:
    """
    Manager for viewing key operations and storage.

    Handles:
    - Key generation and derivation
    - ECIES encryption/decryption
    - Key escrow integration
    - On-chain commitment generation
    """

    # AES-GCM parameters
    AES_KEY_SIZE = 32  # 256 bits
    AES_IV_SIZE = 12   # 96 bits for GCM
    AES_TAG_SIZE = 16  # 128 bits

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        storage_backend: Optional[Any] = None
    ):
        """
        Initialize ViewingKeyManager.

        Args:
            master_key: Optional 32-byte master key for derivation
            storage_backend: Optional storage backend for key persistence
        """
        self.master_key = master_key or os.urandom(32)
        self.storage = storage_backend
        self._key_cache: Dict[str, ViewingKey] = {}

    def generate_for_dispute(
        self,
        dispute_id: str,
        expires_in_days: int = 365
    ) -> ViewingKey:
        """
        Generate a viewing key for a specific dispute.

        Args:
            dispute_id: Unique dispute identifier
            expires_in_days: Key expiration in days

        Returns:
            New ViewingKey for the dispute
        """
        key = ViewingKey.generate(
            purpose=KeyPurpose.DISPUTE_EVIDENCE,
            context_id=dispute_id,
            expires_in_days=expires_in_days,
            metadata={"dispute_id": dispute_id}
        )

        self._key_cache[dispute_id] = key
        return key

    def derive_key(
        self,
        purpose: KeyPurpose,
        context_id: str,
        index: int = 0
    ) -> ViewingKey:
        """
        Derive a viewing key from the master key.

        Args:
            purpose: Key purpose
            context_id: Context identifier
            index: Derivation index

        Returns:
            Derived ViewingKey
        """
        cache_key = f"{purpose.value}:{context_id}:{index}"

        if cache_key in self._key_cache:
            return self._key_cache[cache_key]

        key = ViewingKey.derive(
            self.master_key,
            purpose,
            context_id,
            index
        )

        self._key_cache[cache_key] = key
        return key

    @staticmethod
    def _eth_pubkey_to_ec_public(eth_public: PublicKey) -> ec.EllipticCurvePublicKey:
        """Convert eth_keys PublicKey to cryptography EC public key."""
        # eth_keys public key is 64 bytes (uncompressed without prefix)
        # cryptography expects 65 bytes (04 prefix + x + y)
        pub_bytes = b'\x04' + eth_public.to_bytes()
        return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)

    @staticmethod
    def _eth_privkey_to_ec_private(eth_private: PrivateKey) -> ec.EllipticCurvePrivateKey:
        """Convert eth_keys PrivateKey to cryptography EC private key."""
        private_int = int.from_bytes(eth_private.to_bytes(), 'big')
        return ec.derive_private_key(private_int, ec.SECP256K1(), default_backend())

    @staticmethod
    def encrypt_to_key(
        plaintext: bytes,
        recipient_public_key: PublicKey
    ) -> EncryptedData:
        """
        Encrypt data to a recipient's public key using ECIES.

        ECIES flow:
        1. Generate ephemeral key pair
        2. Compute ECDH shared secret
        3. Derive AES key using HKDF
        4. Encrypt with AES-GCM

        Args:
            plaintext: Data to encrypt
            recipient_public_key: Recipient's public key

        Returns:
            EncryptedData with all decryption components
        """
        # Generate ephemeral key pair using cryptography for proper ECDH
        ephemeral_private_ec = ec.generate_private_key(ec.SECP256K1(), default_backend())
        ephemeral_public_ec = ephemeral_private_ec.public_key()

        # Get ephemeral public key bytes (uncompressed)
        ephemeral_public_bytes = ephemeral_public_ec.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        # Remove the 04 prefix to match eth_keys format (64 bytes)
        ephemeral_public_bytes_64 = ephemeral_public_bytes[1:]

        # Convert recipient public key to cryptography format for ECDH
        recipient_public_ec = ViewingKeyManager._eth_pubkey_to_ec_public(recipient_public_key)

        # Compute ECDH shared secret (proper elliptic curve Diffie-Hellman)
        shared_secret = ephemeral_private_ec.exchange(ec.ECDH(), recipient_public_ec)

        # Derive AES key using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=ephemeral_public_bytes_64[:16],
            info=b"rra-ecies-v1",
            backend=default_backend()
        )
        aes_key = hkdf.derive(shared_secret)

        # Generate IV
        iv = os.urandom(12)

        # Encrypt with AES-GCM
        aesgcm = AESGCM(aes_key)
        ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)

        # Split ciphertext and tag
        ciphertext = ciphertext_with_tag[:-16]
        auth_tag = ciphertext_with_tag[-16:]

        # Compute key commitment
        key_commitment = keccak(recipient_public_key.to_bytes())

        return EncryptedData(
            ephemeral_public_key=ephemeral_public_bytes_64,
            iv=iv,
            ciphertext=ciphertext,
            auth_tag=auth_tag,
            key_commitment=key_commitment
        )

    @staticmethod
    def decrypt_with_key(
        encrypted: EncryptedData,
        private_key: PrivateKey
    ) -> bytes:
        """
        Decrypt ECIES-encrypted data using private key.

        Args:
            encrypted: EncryptedData to decrypt
            private_key: Recipient's private key

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails
        """
        # Verify key commitment
        expected_commitment = keccak(private_key.public_key.to_bytes())
        if encrypted.key_commitment != expected_commitment:
            raise ValueError("Key commitment mismatch - wrong key")

        # Convert ephemeral public key bytes to cryptography EC public key
        # The stored bytes are 64 bytes (no 04 prefix), need to add it
        ephemeral_public_bytes = b'\x04' + encrypted.ephemeral_public_key
        ephemeral_public_ec = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(), ephemeral_public_bytes
        )

        # Convert private key to cryptography format
        private_key_ec = ViewingKeyManager._eth_privkey_to_ec_private(private_key)

        # Compute ECDH shared secret (proper elliptic curve Diffie-Hellman)
        shared_secret = private_key_ec.exchange(ec.ECDH(), ephemeral_public_ec)

        # Derive AES key using HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=encrypted.ephemeral_public_key[:16],
            info=b"rra-ecies-v1",
            backend=default_backend()
        )
        aes_key = hkdf.derive(shared_secret)

        # Decrypt with AES-GCM
        aesgcm = AESGCM(aes_key)
        ciphertext_with_tag = encrypted.ciphertext + encrypted.auth_tag

        try:
            plaintext = aesgcm.decrypt(encrypted.iv, ciphertext_with_tag, None)
            return plaintext
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def encrypt_for_dispute(
        self,
        dispute_id: str,
        evidence: bytes
    ) -> Tuple[EncryptedData, bytes]:
        """
        Encrypt evidence for a dispute.

        Creates or retrieves the dispute's viewing key and encrypts
        the evidence.

        Args:
            dispute_id: Dispute identifier
            evidence: Evidence data to encrypt

        Returns:
            Tuple of (EncryptedData, key_commitment)
        """
        if dispute_id in self._key_cache:
            key = self._key_cache[dispute_id]
        else:
            key = self.generate_for_dispute(dispute_id)

        encrypted = key.encrypt(evidence)
        return encrypted, key.commitment

    def decrypt_dispute_evidence(
        self,
        dispute_id: str,
        encrypted: EncryptedData
    ) -> bytes:
        """
        Decrypt dispute evidence.

        Args:
            dispute_id: Dispute identifier
            encrypted: Encrypted evidence

        Returns:
            Decrypted evidence

        Raises:
            ValueError: If key not found or decryption fails
        """
        if dispute_id not in self._key_cache:
            raise ValueError(f"No viewing key for dispute {dispute_id}")

        key = self._key_cache[dispute_id]
        return key.decrypt(encrypted)

    def get_commitment_for_chain(self, dispute_id: str) -> bytes:
        """
        Get the on-chain commitment for a dispute's viewing key.

        This can be stored in the smart contract to prove key existence.

        Args:
            dispute_id: Dispute identifier

        Returns:
            32-byte commitment hash
        """
        if dispute_id not in self._key_cache:
            raise ValueError(f"No viewing key for dispute {dispute_id}")

        return self._key_cache[dispute_id].commitment

    def export_key_for_escrow(self, dispute_id: str) -> bytes:
        """
        Export a key's private bytes for escrow.

        The exported bytes should be split using Shamir's Secret Sharing
        before storage.

        Args:
            dispute_id: Dispute identifier

        Returns:
            32-byte private key

        Raises:
            ValueError: If key not found
        """
        if dispute_id not in self._key_cache:
            raise ValueError(f"No viewing key for dispute {dispute_id}")

        return self._key_cache[dispute_id].export_private()

    def import_key_from_escrow(
        self,
        dispute_id: str,
        private_bytes: bytes
    ) -> ViewingKey:
        """
        Import a key from escrow storage.

        Args:
            dispute_id: Dispute identifier
            private_bytes: 32-byte private key

        Returns:
            Restored ViewingKey
        """
        key = ViewingKey.from_private_bytes(
            private_bytes,
            KeyPurpose.DISPUTE_EVIDENCE,
            dispute_id
        )

        self._key_cache[dispute_id] = key
        return key


def generate_viewing_key_for_dispute(dispute_id: str) -> Tuple[ViewingKey, bytes]:
    """
    Convenience function to generate a viewing key for a dispute.

    Args:
        dispute_id: Unique dispute identifier

    Returns:
        Tuple of (ViewingKey, commitment_bytes)
    """
    key = ViewingKey.generate(
        purpose=KeyPurpose.DISPUTE_EVIDENCE,
        context_id=dispute_id,
        expires_in_days=365
    )
    return key, key.commitment
