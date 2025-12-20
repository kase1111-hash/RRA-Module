# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Viewing Key Infrastructure for ILRM Dispute Privacy.

Implements ECIES (Elliptic Curve Integrated Encryption Scheme) for
encrypting dispute evidence that can be selectively revealed.

Architecture:
1. Generate viewing key pair (secp256k1 for Ethereum compatibility)
2. Encrypt evidence with recipient's public key
3. Store encrypted evidence on IPFS/Arweave
4. Commit to viewing key on-chain (Pedersen-like commitment)
5. Use Shamir's Secret Sharing for threshold escrow

Security:
- Private keys never stored on-chain
- Commitments allow verification without revelation
- Threshold escrow prevents single point of failure
"""

import os
import json
import hashlib
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from eth_utils import keccak


@dataclass
class ViewingKey:
    """A viewing key pair for evidence encryption."""
    private_key: bytes
    public_key: bytes
    commitment: bytes  # On-chain commitment (hash)
    blinding_factor: bytes  # For ZK proofs


@dataclass
class EncryptedEvidence:
    """Encrypted evidence package."""
    ciphertext: bytes
    ephemeral_public_key: bytes
    nonce: bytes
    tag: bytes  # Authentication tag


class ECIESCipher:
    """
    ECIES encryption using secp256k1 curve.

    Compatible with Ethereum key pairs for seamless integration.
    """

    CURVE = ec.SECP256K1()

    @classmethod
    def generate_key_pair(cls) -> Tuple[bytes, bytes]:
        """
        Generate a new ECIES key pair.

        Returns:
            Tuple of (private_key_bytes, public_key_bytes)
        """
        private_key = ec.generate_private_key(cls.CURVE, default_backend())

        private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

        return private_bytes, public_bytes

    @classmethod
    def encrypt(cls, plaintext: bytes, recipient_public_key: bytes) -> EncryptedEvidence:
        """
        Encrypt data using ECIES.

        Args:
            plaintext: Data to encrypt
            recipient_public_key: Recipient's public key (uncompressed)

        Returns:
            EncryptedEvidence with ciphertext and metadata
        """
        # Generate ephemeral key pair
        ephemeral_private = ec.generate_private_key(cls.CURVE, default_backend())
        ephemeral_public = ephemeral_private.public_key()

        # Load recipient public key
        recipient_key = ec.EllipticCurvePublicKey.from_encoded_point(
            cls.CURVE, recipient_public_key
        )

        # Perform ECDH to derive shared secret
        shared_key = ephemeral_private.exchange(ec.ECDH(), recipient_key)

        # Derive encryption key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"viewing_key_encryption",
            backend=default_backend()
        ).derive(shared_key)

        # Encrypt with AES-GCM
        nonce = os.urandom(12)
        aesgcm = AESGCM(derived_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)

        # Split ciphertext and tag
        ciphertext = ciphertext_with_tag[:-16]
        tag = ciphertext_with_tag[-16:]

        ephemeral_public_bytes = ephemeral_public.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

        return EncryptedEvidence(
            ciphertext=ciphertext,
            ephemeral_public_key=ephemeral_public_bytes,
            nonce=nonce,
            tag=tag
        )

    @classmethod
    def decrypt(cls, encrypted: EncryptedEvidence, private_key: bytes) -> bytes:
        """
        Decrypt ECIES-encrypted data.

        Args:
            encrypted: EncryptedEvidence to decrypt
            private_key: Recipient's private key

        Returns:
            Decrypted plaintext
        """
        # Load private key
        private_value = int.from_bytes(private_key, 'big')
        private_key_obj = ec.derive_private_key(private_value, cls.CURVE, default_backend())

        # Load ephemeral public key
        ephemeral_public = ec.EllipticCurvePublicKey.from_encoded_point(
            cls.CURVE, encrypted.ephemeral_public_key
        )

        # Perform ECDH to derive shared secret
        shared_key = private_key_obj.exchange(ec.ECDH(), ephemeral_public)

        # Derive decryption key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"viewing_key_encryption",
            backend=default_backend()
        ).derive(shared_key)

        # Decrypt with AES-GCM
        aesgcm = AESGCM(derived_key)
        ciphertext_with_tag = encrypted.ciphertext + encrypted.tag
        plaintext = aesgcm.decrypt(encrypted.nonce, ciphertext_with_tag, None)

        return plaintext


class ViewingKeyManager:
    """
    Manager for viewing key lifecycle in ILRM disputes.

    Handles key generation, commitment creation, and evidence encryption.
    """

    def __init__(self):
        self.cipher = ECIESCipher()

    def generate_viewing_key(self) -> ViewingKey:
        """
        Generate a new viewing key with commitment.

        Returns:
            ViewingKey with private/public keys and on-chain commitment
        """
        private_key, public_key = self.cipher.generate_key_pair()
        blinding_factor = os.urandom(32)

        # Create Pedersen-like commitment: H(key || blinding)
        commitment = self._compute_commitment(private_key, blinding_factor)

        return ViewingKey(
            private_key=private_key,
            public_key=public_key,
            commitment=commitment,
            blinding_factor=blinding_factor
        )

    def _compute_commitment(self, key: bytes, blinding: bytes) -> bytes:
        """
        Compute on-chain commitment for viewing key.

        Uses Poseidon-compatible structure for ZK proof compatibility.
        In practice, this would use actual Poseidon hash.
        """
        # For Ethereum compatibility, use keccak256
        # Note: For ZK proofs, replace with Poseidon hash
        combined = key + blinding
        return keccak(combined)

    def encrypt_evidence(
        self,
        evidence: Dict[str, Any],
        viewing_key: ViewingKey,
        dispute_id: int
    ) -> Tuple[EncryptedEvidence, bytes]:
        """
        Encrypt evidence with viewing key.

        Args:
            evidence: Evidence data to encrypt
            viewing_key: ViewingKey to encrypt with
            dispute_id: Dispute ID for binding

        Returns:
            Tuple of (EncryptedEvidence, evidence_hash)
        """
        # Serialize and bind to dispute
        evidence_data = {
            "dispute_id": dispute_id,
            "evidence": evidence,
            "timestamp": int(os.urandom(4).hex(), 16)  # Random timestamp for uniqueness
        }
        plaintext = json.dumps(evidence_data, sort_keys=True).encode()

        # Compute evidence hash for on-chain
        evidence_hash = keccak(plaintext)

        # Encrypt
        encrypted = self.cipher.encrypt(plaintext, viewing_key.public_key)

        return encrypted, evidence_hash

    def decrypt_evidence(
        self,
        encrypted: EncryptedEvidence,
        viewing_key: ViewingKey
    ) -> Dict[str, Any]:
        """
        Decrypt evidence using viewing key.

        Args:
            encrypted: Encrypted evidence
            viewing_key: ViewingKey for decryption

        Returns:
            Decrypted evidence dictionary
        """
        plaintext = self.cipher.decrypt(encrypted, viewing_key.private_key)
        return json.loads(plaintext.decode())

    def serialize_encrypted(self, encrypted: EncryptedEvidence) -> bytes:
        """Serialize encrypted evidence for storage (IPFS/Arweave)."""
        return json.dumps({
            "ciphertext": encrypted.ciphertext.hex(),
            "ephemeral_public_key": encrypted.ephemeral_public_key.hex(),
            "nonce": encrypted.nonce.hex(),
            "tag": encrypted.tag.hex()
        }).encode()

    def deserialize_encrypted(self, data: bytes) -> EncryptedEvidence:
        """Deserialize encrypted evidence from storage."""
        obj = json.loads(data.decode())
        return EncryptedEvidence(
            ciphertext=bytes.fromhex(obj["ciphertext"]),
            ephemeral_public_key=bytes.fromhex(obj["ephemeral_public_key"]),
            nonce=bytes.fromhex(obj["nonce"]),
            tag=bytes.fromhex(obj["tag"])
        )

    def export_viewing_key(self, key: ViewingKey, include_private: bool = False) -> Dict[str, str]:
        """
        Export viewing key for storage or sharing.

        Args:
            key: ViewingKey to export
            include_private: Include private key (for secure storage only!)

        Returns:
            Dictionary with hex-encoded key components
        """
        result = {
            "public_key": key.public_key.hex(),
            "commitment": key.commitment.hex(),
            "blinding_factor": key.blinding_factor.hex()
        }

        if include_private:
            result["private_key"] = key.private_key.hex()

        return result

    def import_viewing_key(self, data: Dict[str, str]) -> ViewingKey:
        """Import viewing key from exported format."""
        return ViewingKey(
            private_key=bytes.fromhex(data.get("private_key", "00" * 32)),
            public_key=bytes.fromhex(data["public_key"]),
            commitment=bytes.fromhex(data["commitment"]),
            blinding_factor=bytes.fromhex(data["blinding_factor"])
        )


# Convenience functions
def generate_viewing_key() -> ViewingKey:
    """Generate a new viewing key."""
    manager = ViewingKeyManager()
    return manager.generate_viewing_key()


def encrypt_evidence(
    evidence: Dict[str, Any],
    viewing_key: ViewingKey,
    dispute_id: int
) -> Tuple[EncryptedEvidence, bytes]:
    """Encrypt evidence with viewing key."""
    manager = ViewingKeyManager()
    return manager.encrypt_evidence(evidence, viewing_key, dispute_id)


def decrypt_evidence(
    encrypted: EncryptedEvidence,
    viewing_key: ViewingKey
) -> Dict[str, Any]:
    """Decrypt evidence using viewing key."""
    manager = ViewingKeyManager()
    return manager.decrypt_evidence(encrypted, viewing_key)
