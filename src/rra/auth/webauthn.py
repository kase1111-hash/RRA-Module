# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
WebAuthn/FIDO2 Client for Hardware-Backed Authentication.

Provides Python interface for WebAuthn operations:
- Credential registration with hardware authenticators
- Assertion generation and verification
- Challenge management
- P-256 signature handling for Ethereum integration

Security Properties:
- Private keys never leave the hardware device
- User presence/verification required
- Replay protection via challenge-response
- Origin binding prevents phishing

Compatible with:
- YubiKey (FIDO2/U2F)
- Touch ID / Face ID
- Windows Hello
- Android Biometric
"""

import binascii
import logging
import os
import json
import hashlib
import base64
import struct
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from eth_utils import keccak

logger = logging.getLogger(__name__)


@dataclass
class WebAuthnCredential:
    """A registered WebAuthn credential."""
    credential_id: bytes
    public_key_x: int
    public_key_y: int
    sign_count: int
    rp_id: str
    user_id: bytes
    created_at: datetime
    last_used: Optional[datetime] = None

    @property
    def credential_id_hash(self) -> bytes:
        """Get keccak256 hash of credential ID."""
        return keccak(self.credential_id)

    @property
    def public_key_bytes(self) -> bytes:
        """Get uncompressed public key bytes."""
        return b'\x04' + self.public_key_x.to_bytes(32, 'big') + self.public_key_y.to_bytes(32, 'big')

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "credential_id": base64.urlsafe_b64encode(self.credential_id).decode(),
            "public_key_x": hex(self.public_key_x),
            "public_key_y": hex(self.public_key_y),
            "sign_count": self.sign_count,
            "rp_id": self.rp_id,
            "user_id": base64.urlsafe_b64encode(self.user_id).decode(),
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebAuthnCredential':
        """Deserialize from dictionary."""
        return cls(
            credential_id=base64.urlsafe_b64decode(data["credential_id"]),
            public_key_x=int(data["public_key_x"], 16),
            public_key_y=int(data["public_key_y"], 16),
            sign_count=data["sign_count"],
            rp_id=data["rp_id"],
            user_id=base64.urlsafe_b64decode(data["user_id"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None
        )


@dataclass
class AuthenticatorData:
    """Parsed authenticator data structure."""
    rp_id_hash: bytes
    flags: int
    sign_count: int
    attested_credential_data: Optional[bytes] = None
    extensions: Optional[bytes] = None

    @property
    def user_present(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def user_verified(self) -> bool:
        return bool(self.flags & 0x04)

    @property
    def has_attested_credential(self) -> bool:
        return bool(self.flags & 0x40)

    @property
    def has_extensions(self) -> bool:
        return bool(self.flags & 0x80)

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        data = self.rp_id_hash + bytes([self.flags]) + struct.pack('>I', self.sign_count)
        if self.attested_credential_data:
            data += self.attested_credential_data
        if self.extensions:
            data += self.extensions
        return data


@dataclass
class AuthenticatorAssertion:
    """An authenticator assertion (authentication response)."""
    credential_id: bytes
    authenticator_data: bytes
    client_data_json: bytes
    signature: bytes
    user_handle: Optional[bytes] = None

    @property
    def parsed_auth_data(self) -> AuthenticatorData:
        """Parse authenticator data structure."""
        return parse_authenticator_data(self.authenticator_data)

    @property
    def signature_r(self) -> int:
        """Extract R component from DER-encoded signature."""
        r, _ = parse_der_signature(self.signature)
        return r

    @property
    def signature_s(self) -> int:
        """Extract S component from DER-encoded signature."""
        _, s = parse_der_signature(self.signature)
        return s

    @property
    def client_data_hash(self) -> bytes:
        """SHA-256 hash of client data JSON."""
        return hashlib.sha256(self.client_data_json).digest()

    @property
    def message_hash(self) -> bytes:
        """Compute message hash for signature verification."""
        return hashlib.sha256(self.authenticator_data + self.client_data_hash).digest()


@dataclass
class Challenge:
    """A WebAuthn challenge."""
    value: bytes
    action_hash: bytes
    created_at: datetime
    expires_at: datetime
    user_address: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at

    @property
    def challenge_hash(self) -> bytes:
        """Get keccak256 hash for on-chain verification."""
        return keccak(self.value)


class WebAuthnClient:
    """
    WebAuthn client for hardware-backed authentication.

    Manages credential registration, challenge creation, and assertion verification.
    Designed for integration with ILRM and RRA agent delegation.
    """

    def __init__(
        self,
        rp_id: str,
        rp_name: str,
        challenge_timeout: int = 300  # 5 minutes
    ):
        """
        Initialize WebAuthn client.

        Args:
            rp_id: Relying Party ID (domain, e.g., "rra.example.com")
            rp_name: Human-readable RP name
            challenge_timeout: Challenge validity in seconds
        """
        self.rp_id = rp_id
        self.rp_name = rp_name
        self.challenge_timeout = challenge_timeout
        self.rp_id_hash = hashlib.sha256(rp_id.encode()).digest()

        # In-memory stores (use persistent storage in production)
        self._credentials: Dict[bytes, WebAuthnCredential] = {}
        self._challenges: Dict[bytes, Challenge] = {}

    # =========================================================================
    # Challenge Management
    # =========================================================================

    def create_challenge(
        self,
        action_hash: bytes,
        user_address: Optional[str] = None
    ) -> Challenge:
        """
        Create a new authentication challenge.

        Args:
            action_hash: Hash of the action to be authorized
            user_address: Optional Ethereum address binding

        Returns:
            Challenge object
        """
        challenge_bytes = os.urandom(32)

        # Incorporate action and timestamp for uniqueness
        combined = challenge_bytes + action_hash + struct.pack('>Q', int(datetime.utcnow().timestamp()))
        challenge_value = hashlib.sha256(combined).digest()

        challenge = Challenge(
            value=challenge_value,
            action_hash=action_hash,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.challenge_timeout),
            user_address=user_address
        )

        self._challenges[challenge_value] = challenge

        return challenge

    def validate_challenge(self, challenge_value: bytes) -> Optional[Challenge]:
        """
        Validate and consume a challenge.

        Args:
            challenge_value: The challenge to validate

        Returns:
            Challenge if valid, None otherwise
        """
        challenge = self._challenges.get(challenge_value)

        if not challenge:
            return None

        if not challenge.is_valid:
            del self._challenges[challenge_value]
            return None

        # Consume challenge (one-time use)
        del self._challenges[challenge_value]

        return challenge

    # =========================================================================
    # Credential Management
    # =========================================================================

    def register_credential(
        self,
        credential_id: bytes,
        public_key_cose: bytes,
        user_id: bytes,
        attestation_object: Optional[bytes] = None
    ) -> WebAuthnCredential:
        """
        Register a new WebAuthn credential.

        Args:
            credential_id: Unique credential identifier from authenticator
            public_key_cose: COSE-encoded public key
            user_id: User identifier
            attestation_object: Optional attestation for verification

        Returns:
            Registered WebAuthnCredential
        """
        # Parse COSE public key to extract x, y coordinates
        public_key_x, public_key_y = parse_cose_public_key(public_key_cose)

        credential = WebAuthnCredential(
            credential_id=credential_id,
            public_key_x=public_key_x,
            public_key_y=public_key_y,
            sign_count=0,
            rp_id=self.rp_id,
            user_id=user_id,
            created_at=datetime.utcnow()
        )

        self._credentials[credential_id] = credential

        return credential

    def get_credential(self, credential_id: bytes) -> Optional[WebAuthnCredential]:
        """Get a registered credential."""
        return self._credentials.get(credential_id)

    def get_credential_by_hash(self, credential_id_hash: bytes) -> Optional[WebAuthnCredential]:
        """Get credential by its keccak256 hash."""
        for cred in self._credentials.values():
            if cred.credential_id_hash == credential_id_hash:
                return cred
        return None

    def list_credentials(self, user_id: Optional[bytes] = None) -> List[WebAuthnCredential]:
        """List all credentials, optionally filtered by user."""
        if user_id:
            return [c for c in self._credentials.values() if c.user_id == user_id]
        return list(self._credentials.values())

    # =========================================================================
    # Assertion Verification
    # =========================================================================

    def verify_assertion(
        self,
        assertion: AuthenticatorAssertion,
        expected_challenge: Optional[bytes] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify an authenticator assertion.

        Args:
            assertion: The assertion to verify
            expected_challenge: Optional expected challenge value

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get credential
        credential = self.get_credential(assertion.credential_id)
        if not credential:
            return False, "Credential not found"

        # Parse authenticator data
        auth_data = assertion.parsed_auth_data

        # Verify RP ID hash
        if auth_data.rp_id_hash != self.rp_id_hash:
            return False, "Invalid RP ID"

        # Verify user presence
        if not auth_data.user_present:
            return False, "User presence required"

        # Verify sign count (replay protection)
        if auth_data.sign_count <= credential.sign_count:
            return False, "Invalid sign count (possible replay)"

        # Verify challenge if provided
        if expected_challenge:
            client_data = json.loads(assertion.client_data_json.decode())
            challenge_b64 = client_data.get("challenge", "")
            try:
                received_challenge = base64.urlsafe_b64decode(challenge_b64 + "==")
                if received_challenge != expected_challenge:
                    return False, "Challenge mismatch"
            except (binascii.Error, ValueError) as e:
                logger.warning(f"Invalid challenge encoding: {e}")
                return False, "Invalid challenge encoding"

        # Verify P-256 signature
        valid = verify_p256_signature(
            assertion.message_hash,
            assertion.signature_r,
            assertion.signature_s,
            credential.public_key_x,
            credential.public_key_y
        )

        if not valid:
            return False, "Invalid signature"

        # Update sign count
        credential.sign_count = auth_data.sign_count
        credential.last_used = datetime.utcnow()

        return True, None

    # =========================================================================
    # Contract Integration Helpers
    # =========================================================================

    def prepare_for_contract(
        self,
        assertion: AuthenticatorAssertion
    ) -> Dict[str, Any]:
        """
        Prepare assertion data for smart contract verification.

        Returns data formatted for WebAuthnVerifier.sol
        """
        credential = self.get_credential(assertion.credential_id)

        return {
            "credentialIdHash": "0x" + assertion.credential_id_hash.hex() if hasattr(assertion, 'credential_id_hash') else "0x" + keccak(assertion.credential_id).hex(),
            "authenticatorData": "0x" + assertion.authenticator_data.hex(),
            "clientDataJSON": "0x" + assertion.client_data_json.hex(),
            "signatureR": assertion.signature_r,
            "signatureS": assertion.signature_s,
            "publicKeyX": credential.public_key_x if credential else 0,
            "publicKeyY": credential.public_key_y if credential else 0
        }


# =========================================================================
# Helper Functions
# =========================================================================

def parse_authenticator_data(data: bytes) -> AuthenticatorData:
    """Parse authenticator data structure."""
    if len(data) < 37:
        raise ValueError("Authenticator data too short")

    rp_id_hash = data[0:32]
    flags = data[32]
    sign_count = struct.unpack('>I', data[33:37])[0]

    attested_data = None
    extensions = None

    # Parse attested credential data if present
    if flags & 0x40 and len(data) > 37:
        # AAGUID (16) + credential ID length (2) + credential ID + public key
        attested_data = data[37:]  # Simplified

    return AuthenticatorData(
        rp_id_hash=rp_id_hash,
        flags=flags,
        sign_count=sign_count,
        attested_credential_data=attested_data,
        extensions=extensions
    )


def parse_cose_public_key(cose_key: bytes) -> Tuple[int, int]:
    """
    Parse COSE-encoded P-256 public key.

    Returns (x, y) coordinates as integers.
    """
    # Simplified COSE parsing for P-256
    # In production, use a proper CBOR library

    # Look for x (-2) and y (-3) keys in COSE map
    # For now, assume raw format: 04 || x (32 bytes) || y (32 bytes)
    if len(cose_key) >= 65 and cose_key[0] == 0x04:
        x = int.from_bytes(cose_key[1:33], 'big')
        y = int.from_bytes(cose_key[33:65], 'big')
        return x, y

    # Try to find coordinates in CBOR structure
    # This is a simplified parser
    try:
        import cbor2
        decoded = cbor2.loads(cose_key)
        x = int.from_bytes(decoded[-2], 'big')
        y = int.from_bytes(decoded[-3], 'big')
        return x, y
    except ImportError:
        # cbor2 not installed, cannot parse CBOR-encoded key
        pass
    except (KeyError, TypeError, ValueError) as e:
        # Invalid CBOR structure or missing keys
        raise ValueError(f"Invalid COSE public key structure: {e}") from e

    raise ValueError("Unable to parse COSE public key: unsupported format")


def parse_der_signature(der_sig: bytes) -> Tuple[int, int]:
    """
    Parse DER-encoded ECDSA signature.

    Returns (r, s) as integers.
    """
    if len(der_sig) < 8 or der_sig[0] != 0x30:
        raise ValueError("Invalid DER signature")

    # Skip sequence header
    idx = 2

    # Parse R
    if der_sig[idx] != 0x02:
        raise ValueError("Invalid R integer marker")
    idx += 1
    r_len = der_sig[idx]
    idx += 1
    r = int.from_bytes(der_sig[idx:idx + r_len], 'big')
    idx += r_len

    # Parse S
    if der_sig[idx] != 0x02:
        raise ValueError("Invalid S integer marker")
    idx += 1
    s_len = der_sig[idx]
    idx += 1
    s = int.from_bytes(der_sig[idx:idx + s_len], 'big')

    return r, s


def verify_p256_signature(
    message_hash: bytes,
    r: int,
    s: int,
    public_key_x: int,
    public_key_y: int
) -> bool:
    """
    Verify a P-256 signature using cryptography library.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import ec, utils
        from cryptography.hazmat.primitives import hashes
        from cryptography.exceptions import InvalidSignature

        # Construct public key
        public_numbers = ec.EllipticCurvePublicNumbers(
            x=public_key_x,
            y=public_key_y,
            curve=ec.SECP256R1()
        )
        public_key = public_numbers.public_key(default_backend())

        # Encode signature in DER format
        signature = utils.encode_dss_signature(r, s)

        # Verify (using prehashed since we have the hash)
        from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
        public_key.verify(
            signature,
            message_hash,
            ec.ECDSA(Prehashed(hashes.SHA256()))
        )

        return True
    except InvalidSignature:
        return False
    except (TypeError, ValueError) as e:
        logger.error(f"P-256 signature verification error: {e}")
        return False


# Convenience functions
def create_challenge(action_hash: bytes, rp_id: str = "rra.local") -> Challenge:
    """Create a WebAuthn challenge."""
    client = WebAuthnClient(rp_id, "RRA Module")
    return client.create_challenge(action_hash)


def verify_assertion(
    assertion: AuthenticatorAssertion,
    credential: WebAuthnCredential,
    expected_challenge: Optional[bytes] = None
) -> Tuple[bool, Optional[str]]:
    """Verify a WebAuthn assertion."""
    client = WebAuthnClient(credential.rp_id, "RRA Module")
    client._credentials[credential.credential_id] = credential
    return client.verify_assertion(assertion, expected_challenge)
