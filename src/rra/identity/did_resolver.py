# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
DID Resolver for NatLangChain Identity System.

Implements resolution for multiple DID methods:
- did:web - Web-based DIDs (domain-linked)
- did:ethr - Ethereum address-based DIDs
- did:key - Cryptographic key-based DIDs
- did:nlc - NatLangChain native DIDs (on-chain registry)

DID Document Structure (W3C DID Core 1.0):
{
    "@context": ["https://www.w3.org/ns/did/v1"],
    "id": "did:ethr:0x123...",
    "verificationMethod": [...],
    "authentication": [...],
    "assertionMethod": [...],
    "service": [...]
}

Usage:
    resolver = DIDResolver()

    # Resolve a DID
    doc = await resolver.resolve("did:ethr:0x123...")

    # Verify a signature
    is_valid = await resolver.verify_signature(
        did="did:ethr:0x123...",
        message=b"hello",
        signature=b"..."
    )
"""

import re
import os
import json
import hashlib
import asyncio
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod

import httpx
from web3 import Web3

from rra.integration.network_resilience import (
    RetryConfig, CircuitBreaker, CircuitBreakerConfig, calculate_delay
)
from eth_utils import keccak, to_checksum_address
from eth_keys import keys
from eth_account.messages import encode_defunct
from eth_account import Account
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


class DIDMethod(Enum):
    """Supported DID methods."""
    WEB = "web"       # did:web:example.com
    ETHR = "ethr"     # did:ethr:0x123...
    KEY = "key"       # did:key:z6Mk...
    NLC = "nlc"       # did:nlc:abc123 (NatLangChain native)


@dataclass
class VerificationMethod:
    """
    Verification method in a DID Document.

    Represents a public key or other verification material.
    """
    id: str                          # e.g., "did:ethr:0x123...#key-1"
    type: str                        # e.g., "EcdsaSecp256k1VerificationKey2019"
    controller: str                  # DID that controls this key
    public_key_hex: Optional[str] = None
    public_key_jwk: Optional[Dict] = None
    public_key_multibase: Optional[str] = None
    blockchain_account_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to DID Document format."""
        result = {
            "id": self.id,
            "type": self.type,
            "controller": self.controller,
        }
        if self.public_key_hex:
            result["publicKeyHex"] = self.public_key_hex
        if self.public_key_jwk:
            result["publicKeyJwk"] = self.public_key_jwk
        if self.public_key_multibase:
            result["publicKeyMultibase"] = self.public_key_multibase
        if self.blockchain_account_id:
            result["blockchainAccountId"] = self.blockchain_account_id
        return result


@dataclass
class ServiceEndpoint:
    """Service endpoint in a DID Document."""
    id: str                          # e.g., "did:ethr:0x123...#messaging"
    type: str                        # e.g., "MessagingService"
    service_endpoint: str            # URL or other endpoint

    def to_dict(self) -> Dict[str, Any]:
        """Convert to DID Document format."""
        return {
            "id": self.id,
            "type": self.type,
            "serviceEndpoint": self.service_endpoint,
        }


@dataclass
class DIDDocument:
    """
    W3C DID Document representation.

    Contains identity information, verification methods,
    authentication methods, and service endpoints.
    """
    id: str                                              # The DID
    context: List[str] = field(default_factory=lambda: ["https://www.w3.org/ns/did/v1"])
    controller: Optional[str] = None
    verification_method: List[VerificationMethod] = field(default_factory=list)
    authentication: List[str] = field(default_factory=list)
    assertion_method: List[str] = field(default_factory=list)
    key_agreement: List[str] = field(default_factory=list)
    capability_invocation: List[str] = field(default_factory=list)
    capability_delegation: List[str] = field(default_factory=list)
    service: List[ServiceEndpoint] = field(default_factory=list)

    # Metadata
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    deactivated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard DID Document JSON format."""
        doc = {
            "@context": self.context,
            "id": self.id,
        }

        if self.controller:
            doc["controller"] = self.controller

        if self.verification_method:
            doc["verificationMethod"] = [vm.to_dict() for vm in self.verification_method]

        if self.authentication:
            doc["authentication"] = self.authentication

        if self.assertion_method:
            doc["assertionMethod"] = self.assertion_method

        if self.key_agreement:
            doc["keyAgreement"] = self.key_agreement

        if self.capability_invocation:
            doc["capabilityInvocation"] = self.capability_invocation

        if self.capability_delegation:
            doc["capabilityDelegation"] = self.capability_delegation

        if self.service:
            doc["service"] = [s.to_dict() for s in self.service]

        return doc

    def get_verification_method(self, method_id: str) -> Optional[VerificationMethod]:
        """Get a verification method by ID."""
        for vm in self.verification_method:
            if vm.id == method_id or vm.id.endswith(f"#{method_id}"):
                return vm
        return None

    def get_primary_verification_method(self) -> Optional[VerificationMethod]:
        """Get the primary verification method (first authentication key)."""
        if self.authentication and self.verification_method:
            primary_id = self.authentication[0]
            return self.get_verification_method(primary_id)
        if self.verification_method:
            return self.verification_method[0]
        return None


class DIDMethodResolver(ABC):
    """Abstract base class for DID method resolvers."""

    @abstractmethod
    async def resolve(self, did: str) -> Optional[DIDDocument]:
        """Resolve a DID to a DID Document."""
        pass

    @abstractmethod
    def supports(self, did: str) -> bool:
        """Check if this resolver supports the given DID."""
        pass


class EthrDIDResolver(DIDMethodResolver):
    """
    Resolver for did:ethr (Ethereum address-based DIDs).

    Format: did:ethr:<network>:<address> or did:ethr:<address>
    Examples:
        - did:ethr:0x123...
        - did:ethr:mainnet:0x123...
        - did:ethr:sepolia:0x123...
    """

    # Network chain IDs
    NETWORKS = {
        "mainnet": 1,
        "sepolia": 11155111,
        "goerli": 5,
        "polygon": 137,
        "arbitrum": 42161,
        "optimism": 10,
        "base": 8453,
    }

    def __init__(self, rpc_url: Optional[str] = None):
        """
        Initialize the resolver.

        Args:
            rpc_url: Optional RPC URL for on-chain resolution
        """
        self.rpc_url = rpc_url

    def supports(self, did: str) -> bool:
        """Check if this is an ethr DID."""
        return did.startswith("did:ethr:")

    def _parse_did(self, did: str) -> Tuple[Optional[str], str]:
        """Parse network and address from DID."""
        parts = did.replace("did:ethr:", "").split(":")
        if len(parts) == 1:
            return None, parts[0]  # No network specified
        return parts[0], parts[1]

    async def resolve(self, did: str) -> Optional[DIDDocument]:
        """Resolve an Ethereum DID to a document."""
        if not self.supports(did):
            return None

        network, address = self._parse_did(did)

        # Validate address
        try:
            address = to_checksum_address(address)
        except Exception:
            return None

        # Build verification method
        vm = VerificationMethod(
            id=f"{did}#controller",
            type="EcdsaSecp256k1RecoveryMethod2020",
            controller=did,
            blockchain_account_id=f"eip155:{self.NETWORKS.get(network, 1)}:{address}",
        )

        # Build DID Document
        doc = DIDDocument(
            id=did,
            context=[
                "https://www.w3.org/ns/did/v1",
                "https://w3id.org/security/suites/secp256k1recovery-2020/v2",
            ],
            verification_method=[vm],
            authentication=[f"{did}#controller"],
            assertion_method=[f"{did}#controller"],
        )

        return doc


class WebDIDResolver(DIDMethodResolver):
    """
    Resolver for did:web (Web-based DIDs).

    Format: did:web:<domain>[:path]
    Examples:
        - did:web:example.com
        - did:web:example.com:user:alice
    """

    def __init__(self, timeout: float = 10.0):
        """
        Initialize the resolver.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout

    def supports(self, did: str) -> bool:
        """Check if this is a web DID."""
        return did.startswith("did:web:")

    def _did_to_url(self, did: str) -> str:
        """Convert DID to well-known URL."""
        # Remove did:web: prefix
        domain_path = did.replace("did:web:", "")

        # Replace : with /
        parts = domain_path.split(":")

        # First part is domain (URL decode %3A back to :)
        domain = parts[0].replace("%3A", ":")

        if len(parts) == 1:
            # Root DID: /.well-known/did.json
            return f"https://{domain}/.well-known/did.json"
        else:
            # Path-based DID
            path = "/".join(parts[1:])
            return f"https://{domain}/{path}/did.json"

    async def resolve(self, did: str) -> Optional[DIDDocument]:
        """Resolve a Web DID by fetching the document with retry logic."""
        if not self.supports(did):
            return None

        url = self._did_to_url(did)
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=1.0,
            retryable_exceptions=(httpx.TimeoutException, httpx.NetworkError)
        )

        last_exception = None
        for attempt in range(retry_config.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=self.timeout)
                    response.raise_for_status()
                    data = response.json()

                    # Validate that the document ID matches
                    if data.get("id") != did:
                        logger.warning(f"DID document ID mismatch: expected {did}")
                        return None

                    return self._parse_document(data)

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < retry_config.max_retries:
                    delay = calculate_delay(attempt, retry_config)
                    logger.warning(f"DID resolution retry {attempt + 1}/{retry_config.max_retries} for {did}: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"DID resolution failed after {retry_config.max_retries} retries for {did}: {e}")
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error resolving DID {did}: {e.response.status_code}")
                return None
            except Exception as e:
                logger.debug(f"DID resolution error for {did}: {e}")
                return None

        return None

    def _parse_document(self, data: Dict) -> DIDDocument:
        """Parse JSON to DIDDocument."""
        doc = DIDDocument(
            id=data["id"],
            context=data.get("@context", ["https://www.w3.org/ns/did/v1"]),
            controller=data.get("controller"),
        )

        # Parse verification methods
        for vm_data in data.get("verificationMethod", []):
            vm = VerificationMethod(
                id=vm_data["id"],
                type=vm_data["type"],
                controller=vm_data.get("controller", doc.id),
                public_key_hex=vm_data.get("publicKeyHex"),
                public_key_jwk=vm_data.get("publicKeyJwk"),
                public_key_multibase=vm_data.get("publicKeyMultibase"),
            )
            doc.verification_method.append(vm)

        # Parse relationships
        doc.authentication = data.get("authentication", [])
        doc.assertion_method = data.get("assertionMethod", [])
        doc.key_agreement = data.get("keyAgreement", [])

        # Parse services
        for svc_data in data.get("service", []):
            svc = ServiceEndpoint(
                id=svc_data["id"],
                type=svc_data["type"],
                service_endpoint=svc_data["serviceEndpoint"],
            )
            doc.service.append(svc)

        return doc


class KeyDIDResolver(DIDMethodResolver):
    """
    Resolver for did:key (Cryptographic key-based DIDs).

    Format: did:key:<multibase-encoded-public-key>
    The DID itself encodes the public key, so no external resolution needed.

    Supports:
        - Ed25519 keys (z6Mk prefix)
        - Secp256k1 keys (zQ3s prefix)
    """

    # Multicodec prefixes
    ED25519_PREFIX = bytes([0xed, 0x01])
    SECP256K1_PREFIX = bytes([0xe7, 0x01])

    def supports(self, did: str) -> bool:
        """Check if this is a key DID."""
        return did.startswith("did:key:")

    def _decode_multibase(self, encoded: str) -> bytes:
        """Decode multibase-encoded data."""
        if encoded.startswith("z"):
            # Base58btc encoding
            import base58
            return base58.b58decode(encoded[1:])
        raise ValueError(f"Unsupported multibase encoding: {encoded[0]}")

    async def resolve(self, did: str) -> Optional[DIDDocument]:
        """Resolve a key DID (self-describing)."""
        if not self.supports(did):
            return None

        try:
            # Extract multibase key
            multibase_key = did.replace("did:key:", "")
            key_bytes = self._decode_multibase(multibase_key)

            # Determine key type from multicodec prefix
            if key_bytes[:2] == self.ED25519_PREFIX:
                key_type = "Ed25519VerificationKey2020"
                public_key = key_bytes[2:]
            elif key_bytes[:2] == self.SECP256K1_PREFIX:
                key_type = "EcdsaSecp256k1VerificationKey2019"
                public_key = key_bytes[2:]
            else:
                return None

            # Build verification method
            vm = VerificationMethod(
                id=f"{did}#{multibase_key}",
                type=key_type,
                controller=did,
                public_key_multibase=multibase_key,
            )

            doc = DIDDocument(
                id=did,
                context=[
                    "https://www.w3.org/ns/did/v1",
                    "https://w3id.org/security/suites/ed25519-2020/v1",
                ],
                verification_method=[vm],
                authentication=[f"{did}#{multibase_key}"],
                assertion_method=[f"{did}#{multibase_key}"],
                key_agreement=[f"{did}#{multibase_key}"],
            )

            return doc

        except Exception:
            return None


class NLCDIDResolver(DIDMethodResolver):
    """
    Resolver for did:nlc (NatLangChain native DIDs).

    Format: did:nlc:<identifier>
    These DIDs are resolved against the on-chain DIDRegistry contract.

    The identifier is a 64-character hex string representing a bytes32 value.
    """

    # Default RPC URL for Ethereum mainnet
    DEFAULT_RPC_URL = os.environ.get("ETH_RPC_URL", "https://eth.llamarpc.com")

    # Default DID Registry contract address (to be set after deployment)
    DEFAULT_REGISTRY_ADDRESS = os.environ.get("NLC_DID_REGISTRY_ADDRESS", "")

    # DIDRegistry contract ABI (minimal for resolution)
    REGISTRY_ABI = [
        {
            "inputs": [{"name": "_identifier", "type": "bytes32"}],
            "name": "getDocument",
            "outputs": [
                {
                    "components": [
                        {"name": "identifier", "type": "bytes32"},
                        {"name": "owner", "type": "address"},
                        {"name": "controllers", "type": "address[]"},
                        {"name": "createdAt", "type": "uint256"},
                        {"name": "updatedAt", "type": "uint256"},
                        {"name": "deactivated", "type": "bool"},
                        {"name": "stake", "type": "uint256"},
                        {"name": "verificationMethodCount", "type": "uint8"},
                        {"name": "serviceCount", "type": "uint8"},
                        {"name": "pohCount", "type": "uint8"},
                    ],
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "_identifier", "type": "bytes32"}],
            "name": "getVerificationMethods",
            "outputs": [
                {
                    "components": [
                        {"name": "id", "type": "bytes32"},
                        {"name": "keyType", "type": "uint8"},
                        {"name": "controller", "type": "address"},
                        {"name": "publicKey", "type": "bytes"},
                        {"name": "active", "type": "bool"},
                        {"name": "addedAt", "type": "uint256"},
                    ],
                    "name": "",
                    "type": "tuple[]",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "_identifier", "type": "bytes32"}],
            "name": "getServices",
            "outputs": [
                {
                    "components": [
                        {"name": "id", "type": "bytes32"},
                        {"name": "serviceType", "type": "string"},
                        {"name": "endpoint", "type": "string"},
                        {"name": "active", "type": "bool"},
                    ],
                    "name": "",
                    "type": "tuple[]",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "_identifier", "type": "bytes32"}],
            "name": "buildDID",
            "outputs": [{"name": "", "type": "string"}],
            "stateMutability": "pure",
            "type": "function",
        },
    ]

    # Key type mapping from contract enum to string type
    KEY_TYPE_MAP = {
        0: "EcdsaSecp256k1VerificationKey2019",  # EcdsaSecp256k1
        1: "Ed25519VerificationKey2020",          # Ed25519
        2: "X25519KeyAgreementKey2020",           # X25519
    }

    def __init__(self, registry_address: Optional[str] = None, rpc_url: Optional[str] = None):
        """
        Initialize the resolver.

        Args:
            registry_address: Address of DIDRegistry contract
            rpc_url: RPC URL for the blockchain
        """
        self.registry_address = registry_address or self.DEFAULT_REGISTRY_ADDRESS
        self.rpc_url = rpc_url or self.DEFAULT_RPC_URL
        self._cache: Dict[str, Tuple[DIDDocument, datetime]] = {}
        self._cache_ttl = 300  # 5 minutes
        self._w3: Optional[Web3] = None
        self._contract = None

    def supports(self, did: str) -> bool:
        """Check if this is an NLC DID."""
        return did.startswith("did:nlc:")

    def _get_web3(self) -> Web3:
        """Get or create Web3 instance."""
        if self._w3 is None:
            self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        return self._w3

    def _get_contract(self):
        """Get or create contract instance."""
        if self._contract is None and self.registry_address:
            w3 = self._get_web3()
            self._contract = w3.eth.contract(
                address=to_checksum_address(self.registry_address),
                abi=self.REGISTRY_ABI
            )
        return self._contract

    def _identifier_to_bytes32(self, identifier: str) -> bytes:
        """Convert hex string identifier to bytes32."""
        # Remove 0x prefix if present
        if identifier.startswith("0x"):
            identifier = identifier[2:]

        # Pad to 64 characters (32 bytes) if needed
        identifier = identifier.zfill(64)

        return bytes.fromhex(identifier)

    def _bytes32_to_hex(self, data: bytes) -> str:
        """Convert bytes32 to hex string."""
        return "0x" + data.hex()

    async def resolve(self, did: str) -> Optional[DIDDocument]:
        """
        Resolve an NLC DID from the on-chain registry.

        Args:
            did: The DID to resolve (format: did:nlc:<identifier>)

        Returns:
            DIDDocument if found, None otherwise
        """
        if not self.supports(did):
            return None

        # Check cache
        if did in self._cache:
            doc, cached_at = self._cache[did]
            if (datetime.utcnow() - cached_at).total_seconds() < self._cache_ttl:
                return doc

        # Extract identifier
        identifier = did.replace("did:nlc:", "")

        # Check if we have a registry address configured
        if not self.registry_address:
            logger.warning("NLC DID Registry address not configured. Set NLC_DID_REGISTRY_ADDRESS env var.")
            # Return a placeholder document for development
            return self._create_placeholder_document(did, identifier)

        try:
            contract = self._get_contract()
            if contract is None:
                logger.error("Failed to get DID Registry contract")
                return None

            # Convert identifier to bytes32
            identifier_bytes = self._identifier_to_bytes32(identifier)

            # Fetch document from chain
            doc_data = contract.functions.getDocument(identifier_bytes).call()

            # Check if document exists (createdAt > 0)
            if doc_data[3] == 0:  # createdAt index
                logger.debug(f"DID not found on-chain: {did}")
                return None

            # Check if deactivated
            if doc_data[5]:  # deactivated index
                logger.debug(f"DID is deactivated: {did}")
                return None

            # Parse document data
            owner = doc_data[1]
            controllers = doc_data[2]
            created_at = datetime.fromtimestamp(doc_data[3])
            updated_at = datetime.fromtimestamp(doc_data[4])

            # Fetch verification methods
            vm_data = contract.functions.getVerificationMethods(identifier_bytes).call()
            verification_methods = []
            authentication = []
            assertion_method = []
            key_agreement = []

            for vm in vm_data:
                if not vm[4]:  # Skip inactive keys
                    continue

                key_id_hex = self._bytes32_to_hex(vm[0])
                key_type_enum = vm[1]
                controller_addr = vm[2]
                public_key = vm[3]

                # Map key type enum to string
                key_type_str = self.KEY_TYPE_MAP.get(key_type_enum, "EcdsaSecp256k1VerificationKey2019")

                vm_obj = VerificationMethod(
                    id=f"{did}#{key_id_hex[-8:]}",  # Use last 8 chars as key fragment
                    type=key_type_str,
                    controller=did,
                    public_key_hex=public_key.hex() if public_key else None,
                    blockchain_account_id=f"eip155:1:{controller_addr}",
                )
                verification_methods.append(vm_obj)

                # Add to appropriate relationships based on key type
                if key_type_enum in (0, 1):  # Secp256k1 or Ed25519
                    authentication.append(vm_obj.id)
                    assertion_method.append(vm_obj.id)
                if key_type_enum == 2:  # X25519 (key agreement)
                    key_agreement.append(vm_obj.id)

            # Fetch services
            svc_data = contract.functions.getServices(identifier_bytes).call()
            services = []

            for svc in svc_data:
                if not svc[3]:  # Skip inactive services
                    continue

                svc_id_hex = self._bytes32_to_hex(svc[0])
                svc_type = svc[1]
                endpoint = svc[2]

                svc_obj = ServiceEndpoint(
                    id=f"{did}#{svc_id_hex[-8:]}",
                    type=svc_type,
                    service_endpoint=endpoint,
                )
                services.append(svc_obj)

            # Build DID Document
            doc = DIDDocument(
                id=did,
                context=[
                    "https://www.w3.org/ns/did/v1",
                    "https://w3id.org/security/suites/secp256k1-2019/v1",
                    "https://natlangchain.io/did/v1",
                ],
                controller=f"did:ethr:{owner}" if owner else None,
                verification_method=verification_methods,
                authentication=authentication,
                assertion_method=assertion_method,
                key_agreement=key_agreement,
                service=services,
                created=created_at,
                updated=updated_at,
                deactivated=False,
            )

            # Cache the result
            self._cache[did] = (doc, datetime.utcnow())

            logger.debug(f"Resolved DID from chain: {did}")
            return doc

        except Exception as e:
            logger.error(f"Error resolving NLC DID {did}: {e}")
            return None

    def _create_placeholder_document(self, did: str, identifier: str) -> DIDDocument:
        """
        Create a placeholder document when registry is not configured.

        This is used for development/testing when no registry is deployed.
        """
        logger.warning(f"Creating placeholder document for {did} - registry not configured")

        doc = DIDDocument(
            id=did,
            context=[
                "https://www.w3.org/ns/did/v1",
                "https://natlangchain.io/did/v1",
            ],
            verification_method=[
                VerificationMethod(
                    id=f"{did}#key-1",
                    type="EcdsaSecp256k1VerificationKey2019",
                    controller=did,
                )
            ],
            authentication=[f"{did}#key-1"],
            assertion_method=[f"{did}#key-1"],
        )

        # Cache placeholder
        self._cache[did] = (doc, datetime.utcnow())

        return doc

    async def register_did(
        self,
        public_key: bytes,
        key_type: int = 0,
        private_key: Optional[str] = None,
        stake_wei: int = 10000000000000000,  # 0.01 ETH default
    ) -> Optional[str]:
        """
        Register a new DID on-chain.

        Args:
            public_key: The initial public key bytes
            key_type: Key type (0=Secp256k1, 1=Ed25519, 2=X25519)
            private_key: Private key for signing the transaction
            stake_wei: Stake amount in wei (minimum 0.01 ETH)

        Returns:
            The new DID string if successful, None otherwise
        """
        if not self.registry_address:
            logger.error("Registry address not configured")
            return None

        if not private_key:
            logger.error("Private key required for registration")
            return None

        try:
            w3 = self._get_web3()
            contract = self._get_contract()

            # Get account from private key
            account = Account.from_key(private_key)

            # Build transaction
            tx = contract.functions.registerDID(
                public_key,
                key_type
            ).build_transaction({
                'from': account.address,
                'value': stake_wei,
                'gas': 500000,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(account.address),
            })

            # Sign and send
            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] == 1:
                # Parse the DIDRegistered event to get the identifier
                # For now, construct from logs
                for log in receipt['logs']:
                    if len(log['topics']) >= 2:
                        # First topic is event signature, second is indexed identifier
                        identifier = log['topics'][1].hex()
                        did = f"did:nlc:{identifier}"
                        logger.info(f"Registered new DID: {did}")
                        return did

            logger.error("DID registration transaction failed")
            return None

        except Exception as e:
            logger.error(f"Error registering DID: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()


class DIDResolver:
    """
    Universal DID Resolver supporting multiple methods.

    Aggregates method-specific resolvers and provides a unified interface.
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        registry_address: Optional[str] = None
    ):
        """
        Initialize the resolver with method-specific resolvers.

        Args:
            rpc_url: RPC URL for blockchain-based resolution
            registry_address: Address of NLC DID Registry
        """
        self.resolvers: List[DIDMethodResolver] = [
            EthrDIDResolver(rpc_url),
            WebDIDResolver(),
            KeyDIDResolver(),
            NLCDIDResolver(registry_address, rpc_url),
        ]
        self._cache: Dict[str, Tuple[DIDDocument, datetime]] = {}
        self._cache_ttl = 300  # 5 minutes

    def add_resolver(self, resolver: DIDMethodResolver) -> None:
        """Add a custom DID method resolver."""
        self.resolvers.insert(0, resolver)

    async def resolve(self, did: str) -> Optional[DIDDocument]:
        """
        Resolve a DID to a DID Document.

        Args:
            did: The DID to resolve

        Returns:
            DIDDocument if found, None otherwise
        """
        # Validate DID format
        if not self._validate_did_format(did):
            return None

        # Check cache
        if did in self._cache:
            doc, cached_at = self._cache[did]
            if (datetime.utcnow() - cached_at).total_seconds() < self._cache_ttl:
                return doc

        # Try each resolver
        for resolver in self.resolvers:
            if resolver.supports(did):
                doc = await resolver.resolve(did)
                if doc:
                    self._cache[did] = (doc, datetime.utcnow())
                    return doc

        return None

    def _validate_did_format(self, did: str) -> bool:
        """Validate DID format according to W3C spec."""
        # Basic pattern: did:<method>:<method-specific-id>
        pattern = r'^did:[a-z0-9]+:[a-zA-Z0-9._:%-]+$'
        return bool(re.match(pattern, did))

    def get_method(self, did: str) -> Optional[DIDMethod]:
        """Extract the DID method from a DID."""
        if not did.startswith("did:"):
            return None

        parts = did.split(":")
        if len(parts) < 3:
            return None

        method = parts[1]
        try:
            return DIDMethod(method)
        except ValueError:
            return None

    def parse_did(self, did: str) -> Tuple[DIDMethod, str]:
        """
        Parse a DID into its method and method-specific identifier.

        Args:
            did: The DID to parse (e.g., "did:ethr:0x123...")

        Returns:
            Tuple of (DIDMethod, identifier)

        Raises:
            ValueError: If the DID format is invalid or method is unsupported
        """
        if not did.startswith("did:"):
            raise ValueError(f"Invalid DID format: {did}")

        parts = did.split(":")
        if len(parts) < 3:
            raise ValueError(f"Invalid DID format: {did}")

        method_str = parts[1]
        # Join remaining parts as identifier (handles did:ethr:mainnet:0x123)
        identifier = ":".join(parts[2:])

        try:
            method = DIDMethod(method_str)
        except ValueError:
            raise ValueError(f"Unsupported DID method: {method_str}")

        return method, identifier

    async def verify_signature(
        self,
        did: str,
        message: bytes,
        signature: bytes,
        verification_method_id: Optional[str] = None
    ) -> bool:
        """
        Verify a signature against a DID's verification method.

        Args:
            did: The DID of the signer
            message: The signed message
            signature: The signature bytes
            verification_method_id: Optional specific verification method to use

        Returns:
            True if signature is valid
        """
        doc = await self.resolve(did)
        if not doc:
            return False

        # Get verification method
        if verification_method_id:
            vm = doc.get_verification_method(verification_method_id)
        else:
            vm = doc.get_primary_verification_method()

        if not vm:
            return False

        # Verify based on key type
        try:
            if "Secp256k1" in vm.type:
                return self._verify_secp256k1(vm, message, signature)
            elif "Ed25519" in vm.type:
                return self._verify_ed25519(vm, message, signature)
            else:
                return False
        except Exception:
            return False

    def _verify_secp256k1(
        self,
        vm: VerificationMethod,
        message: bytes,
        signature: bytes
    ) -> bool:
        """Verify secp256k1 signature."""
        # For blockchain account ID (Ethereum)
        if vm.blockchain_account_id:
            # Extract address
            parts = vm.blockchain_account_id.split(":")
            address = parts[-1]

            # Recover address from signature
            message_hash = encode_defunct(message)
            recovered = Account.recover_message(message_hash, signature=signature)

            return recovered.lower() == address.lower()

        return False

    def _verify_ed25519(
        self,
        vm: VerificationMethod,
        message: bytes,
        signature: bytes
    ) -> bool:
        """Verify Ed25519 signature."""
        try:
            public_key_bytes: Optional[bytes] = None

            # Try to get the public key from available sources
            if vm.public_key_hex:
                public_key_bytes = bytes.fromhex(vm.public_key_hex)
            elif vm.public_key_multibase:
                # Decode multibase-encoded key
                if vm.public_key_multibase.startswith("z"):
                    # Base58btc encoding
                    import base58
                    key_bytes = base58.b58decode(vm.public_key_multibase[1:])
                    # Check for multicodec prefix (0xed01 for Ed25519)
                    if len(key_bytes) > 2 and key_bytes[:2] == bytes([0xed, 0x01]):
                        public_key_bytes = key_bytes[2:]
                    else:
                        public_key_bytes = key_bytes
                else:
                    return False

            if not public_key_bytes or len(public_key_bytes) != 32:
                return False

            # Load the Ed25519 public key and verify
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, message)
            return True

        except (InvalidSignature, ValueError, Exception):
            return False

    async def authenticate(
        self,
        did: str,
        challenge: bytes,
        response: bytes
    ) -> bool:
        """
        Authenticate a DID by verifying a challenge-response.

        Args:
            did: The DID claiming authentication
            challenge: Random challenge bytes
            response: Signed response

        Returns:
            True if authentication successful
        """
        return await self.verify_signature(did, challenge, response)

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()


# Convenience function
async def resolve_did(did: str) -> Optional[DIDDocument]:
    """
    Resolve a DID using the default resolver.

    Args:
        did: The DID to resolve

    Returns:
        DIDDocument if found
    """
    resolver = DIDResolver()
    return await resolver.resolve(did)
