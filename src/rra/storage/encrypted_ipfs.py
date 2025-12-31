# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Encrypted IPFS/Arweave Storage for ILRM Dispute Evidence.

Provides privacy-preserving storage for dispute evidence:
1. Encrypt evidence with viewing key (ECIES)
2. Store encrypted data on IPFS or Arweave
3. Store only content hash on-chain
4. Retrieve and decrypt with viewing key

Supports:
- IPFS via HTTP API (Infura, Pinata, local node)
- Arweave via HTTP API
- Lit Protocol for access control (optional)
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import urllib.request
import urllib.error

from eth_utils import keccak

from rra.privacy.viewing_keys import (
    ViewingKeyManager,
    ViewingKey,
    EncryptedEvidence,
)


class StorageProvider(str, Enum):
    """Supported storage providers."""
    IPFS_LOCAL = "ipfs_local"
    IPFS_INFURA = "ipfs_infura"
    IPFS_PINATA = "ipfs_pinata"
    ARWEAVE = "arweave"
    MOCK = "mock"  # For testing


@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    uri: str  # ipfs://... or ar://...
    content_hash: bytes  # Hash of encrypted content
    size_bytes: int
    provider: StorageProvider
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "uri": self.uri,
            "content_hash": self.content_hash.hex(),
            "size_bytes": self.size_bytes,
            "provider": self.provider.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass
class StorageConfig:
    """Configuration for storage provider."""
    provider: StorageProvider
    api_url: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    timeout: int = 30  # seconds
    max_retries: int = 3
    pin: bool = True  # Pin content for persistence


class EncryptedIPFSStorage:
    """
    Encrypted storage for ILRM dispute evidence.

    Handles encryption, upload, retrieval, and decryption
    of dispute evidence on decentralized storage.
    """

    # Default API endpoints
    DEFAULT_ENDPOINTS = {
        StorageProvider.IPFS_LOCAL: "http://localhost:5001/api/v0",
        StorageProvider.IPFS_INFURA: "https://ipfs.infura.io:5001/api/v0",
        StorageProvider.IPFS_PINATA: "https://api.pinata.cloud",
        StorageProvider.ARWEAVE: "https://arweave.net",
    }

    def __init__(
        self,
        config: Optional[StorageConfig] = None,
        viewing_key_manager: Optional[ViewingKeyManager] = None,
    ):
        """
        Initialize encrypted storage.

        Args:
            config: Storage provider configuration
            viewing_key_manager: Manager for viewing key operations
        """
        self.config = config or StorageConfig(
            provider=StorageProvider.MOCK,
            api_url="",
        )
        self.vk_manager = viewing_key_manager or ViewingKeyManager()

        # Mock storage for testing
        self._mock_storage: Dict[str, bytes] = {}

    def store_evidence(
        self,
        evidence: Dict[str, Any],
        viewing_key: ViewingKey,
        dispute_id: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StorageResult:
        """
        Encrypt and store evidence.

        Args:
            evidence: Evidence data to store
            viewing_key: Viewing key for encryption
            dispute_id: Associated dispute ID
            metadata: Optional metadata to store alongside

        Returns:
            StorageResult with URI and content hash
        """
        # 1. Encrypt evidence
        encrypted, evidence_hash = self.vk_manager.encrypt_evidence(
            evidence, viewing_key, dispute_id
        )

        # 2. Serialize encrypted evidence
        serialized = self.vk_manager.serialize_encrypted(encrypted)

        # 3. Create storage package with metadata
        package = {
            "version": "1.0",
            "dispute_id": dispute_id,
            "evidence_hash": evidence_hash.hex(),
            "viewing_key_commitment": viewing_key.commitment.hex(),
            "encrypted_evidence": serialized.decode(),
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        package_bytes = json.dumps(package, sort_keys=True).encode()

        # 4. Upload to storage provider
        return self._upload(package_bytes, dispute_id)

    def retrieve_evidence(
        self,
        uri: str,
        viewing_key: ViewingKey,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Retrieve and decrypt evidence.

        Args:
            uri: Storage URI (ipfs://... or ar://...)
            viewing_key: Viewing key for decryption

        Returns:
            Tuple of (evidence_data, metadata)

        Raises:
            ValueError: If decryption fails
        """
        # 1. Download from storage
        package_bytes = self._download(uri)

        # 2. Parse package
        package = json.loads(package_bytes.decode())

        # 3. Deserialize encrypted evidence
        encrypted = self.vk_manager.deserialize_encrypted(
            package["encrypted_evidence"].encode()
        )

        # 4. Decrypt
        decrypted = self.vk_manager.decrypt_evidence(encrypted, viewing_key)

        # 5. Build metadata including package-level fields
        metadata = package.get("metadata", {}).copy()
        if "dispute_id" in package:
            metadata["dispute_id"] = package["dispute_id"]

        return decrypted["evidence"], metadata

    def verify_evidence_hash(
        self,
        uri: str,
        expected_hash: bytes,
    ) -> bool:
        """
        Verify evidence hash without decryption.

        Args:
            uri: Storage URI
            expected_hash: Expected evidence hash from on-chain

        Returns:
            True if hash matches
        """
        try:
            package_bytes = self._download(uri)
            package = json.loads(package_bytes.decode())
            stored_hash = bytes.fromhex(package["evidence_hash"])
            return stored_hash == expected_hash
        except Exception:
            return False

    def _upload(self, data: bytes, dispute_id: int) -> StorageResult:
        """Upload data to storage provider."""
        content_hash = keccak(data)

        if self.config.provider == StorageProvider.MOCK:
            return self._mock_upload(data, content_hash, dispute_id)
        elif self.config.provider in (
            StorageProvider.IPFS_LOCAL,
            StorageProvider.IPFS_INFURA,
        ):
            return self._ipfs_upload(data, content_hash, dispute_id)
        elif self.config.provider == StorageProvider.IPFS_PINATA:
            return self._pinata_upload(data, content_hash, dispute_id)
        elif self.config.provider == StorageProvider.ARWEAVE:
            return self._arweave_upload(data, content_hash, dispute_id)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def _download(self, uri: str) -> bytes:
        """Download data from storage provider."""
        if uri.startswith("mock://"):
            cid = uri.replace("mock://", "")
            if cid not in self._mock_storage:
                raise ValueError(f"Not found: {uri}")
            return self._mock_storage[cid]

        elif uri.startswith("ipfs://"):
            cid = uri.replace("ipfs://", "")
            return self._ipfs_download(cid)

        elif uri.startswith("ar://"):
            tx_id = uri.replace("ar://", "")
            return self._arweave_download(tx_id)

        else:
            raise ValueError(f"Unsupported URI scheme: {uri}")

    def _mock_upload(
        self,
        data: bytes,
        content_hash: bytes,
        dispute_id: int,
    ) -> StorageResult:
        """Mock upload for testing."""
        cid = hashlib.sha256(data).hexdigest()[:46]
        self._mock_storage[cid] = data

        return StorageResult(
            success=True,
            uri=f"mock://{cid}",
            content_hash=content_hash,
            size_bytes=len(data),
            provider=StorageProvider.MOCK,
            timestamp=datetime.utcnow(),
            metadata={"dispute_id": dispute_id},
        )

    def _ipfs_upload(
        self,
        data: bytes,
        content_hash: bytes,
        dispute_id: int,
    ) -> StorageResult:
        """Upload to IPFS via HTTP API."""
        url = f"{self.config.api_url}/add"

        # Create multipart form data
        boundary = "----IPFSBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="evidence.json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }

        # Add auth if configured
        if self.config.api_key and self.config.api_secret:
            import base64
            credentials = base64.b64encode(
                f"{self.config.api_key}:{self.config.api_secret}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        try:
            request = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode())
                cid = result.get("Hash")

                # Pin if configured
                if self.config.pin:
                    self._ipfs_pin(cid)

                return StorageResult(
                    success=True,
                    uri=f"ipfs://{cid}",
                    content_hash=content_hash,
                    size_bytes=len(data),
                    provider=self.config.provider,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "dispute_id": dispute_id,
                        "cid": cid,
                    },
                )
        except urllib.error.URLError as e:
            return StorageResult(
                success=False,
                uri="",
                content_hash=content_hash,
                size_bytes=len(data),
                provider=self.config.provider,
                timestamp=datetime.utcnow(),
                error=str(e),
            )

    def _ipfs_download(self, cid: str) -> bytes:
        """Download from IPFS."""
        # Try configured API first
        if self.config.api_url:
            url = f"{self.config.api_url}/cat?arg={cid}"
            try:
                request = urllib.request.Request(url)
                with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                    return response.read()
            except urllib.error.URLError:
                pass

        # Fallback to public gateway
        gateway_url = f"https://ipfs.io/ipfs/{cid}"
        request = urllib.request.Request(gateway_url)
        with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
            return response.read()

    def _ipfs_pin(self, cid: str) -> bool:
        """Pin content on IPFS."""
        url = f"{self.config.api_url}/pin/add?arg={cid}"
        try:
            request = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                return response.status == 200
        except urllib.error.URLError:
            return False

    def _pinata_upload(
        self,
        data: bytes,
        content_hash: bytes,
        dispute_id: int,
    ) -> StorageResult:
        """Upload to Pinata IPFS pinning service."""
        url = f"{self.config.api_url}/pinning/pinFileToIPFS"

        # Create multipart form data
        boundary = "----PinataBoundary"

        # Metadata for Pinata
        pinata_metadata = json.dumps({
            "name": f"dispute_{dispute_id}_evidence",
            "keyvalues": {
                "dispute_id": str(dispute_id),
                "type": "ilrm_evidence",
            }
        })

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="evidence.json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode() + data + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="pinataMetadata"\r\n'
            f"Content-Type: application/json\r\n\r\n"
            f"{pinata_metadata}\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {self.config.api_key}",
        }

        try:
            request = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode())
                cid = result.get("IpfsHash")

                return StorageResult(
                    success=True,
                    uri=f"ipfs://{cid}",
                    content_hash=content_hash,
                    size_bytes=len(data),
                    provider=self.config.provider,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "dispute_id": dispute_id,
                        "cid": cid,
                        "pin_size": result.get("PinSize"),
                    },
                )
        except urllib.error.URLError as e:
            return StorageResult(
                success=False,
                uri="",
                content_hash=content_hash,
                size_bytes=len(data),
                provider=self.config.provider,
                timestamp=datetime.utcnow(),
                error=str(e),
            )

    def _arweave_upload(
        self,
        data: bytes,
        content_hash: bytes,
        dispute_id: int,
    ) -> StorageResult:
        """Upload to Arweave."""
        # Note: Real Arweave upload requires JWK signing
        # This is a simplified implementation for demo purposes
        url = f"{self.config.api_url}/tx"

        # Create Arweave transaction structure
        tx = {
            "data": data.hex(),
            "tags": [
                {"name": "Content-Type", "value": "application/json"},
                {"name": "App-Name", "value": "ILRM"},
                {"name": "Dispute-ID", "value": str(dispute_id)},
            ],
        }

        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(tx).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                result = json.loads(response.read().decode())
                tx_id = result.get("id", hashlib.sha256(data).hexdigest()[:43])

                return StorageResult(
                    success=True,
                    uri=f"ar://{tx_id}",
                    content_hash=content_hash,
                    size_bytes=len(data),
                    provider=self.config.provider,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "dispute_id": dispute_id,
                        "tx_id": tx_id,
                    },
                )
        except urllib.error.URLError as e:
            return StorageResult(
                success=False,
                uri="",
                content_hash=content_hash,
                size_bytes=len(data),
                provider=self.config.provider,
                timestamp=datetime.utcnow(),
                error=str(e),
            )

    def _arweave_download(self, tx_id: str) -> bytes:
        """Download from Arweave."""
        url = f"{self.config.api_url or 'https://arweave.net'}/{tx_id}"
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
            return response.read()


def create_storage(
    provider: StorageProvider = StorageProvider.MOCK,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> EncryptedIPFSStorage:
    """
    Create an encrypted storage instance.

    Args:
        provider: Storage provider to use
        api_url: API endpoint URL
        api_key: API key for authentication
        api_secret: API secret for authentication

    Returns:
        Configured EncryptedIPFSStorage instance
    """
    config = StorageConfig(
        provider=provider,
        api_url=api_url or EncryptedIPFSStorage.DEFAULT_ENDPOINTS.get(provider, ""),
        api_key=api_key,
        api_secret=api_secret,
    )

    return EncryptedIPFSStorage(config)
