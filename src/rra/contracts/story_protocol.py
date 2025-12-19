# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Story Protocol integration for programmable IP licensing.

Provides Python interface for interacting with Story Protocol contracts
to register repositories as IP Assets and manage programmable licenses.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from web3 import Web3
from web3.contract import Contract
from eth_utils import to_checksum_address


@dataclass
class IPAssetMetadata:
    """Metadata for an IP Asset on Story Protocol."""
    name: str
    description: str
    ipType: str  # e.g., "SOFTWARE", "CODE", "REPOSITORY"
    createdAt: int
    ipfsHash: Optional[str] = None
    externalUrl: Optional[str] = None


@dataclass
class PILTerms:
    """Programmable IP License (PIL) terms."""
    commercial_use: bool = True
    derivatives_allowed: bool = True
    derivatives_approve: bool = False
    derivatives_attribution: bool = True
    derivatives_reciprocal: bool = False
    royalty_policy: Optional[str] = None
    commercial_revenue_share: int = 0  # Basis points (0-10000)
    territory_restriction: Optional[str] = None
    distribution_channels: Optional[List[str]] = None


class StoryProtocolClient:
    """
    Client for interacting with Story Protocol contracts.

    Story Protocol enables tokenizing code repositories as IP Assets
    with programmable licensing terms and automated royalty distribution.
    """

    # Story Protocol contract addresses (mainnet - launched Feb 2025)
    STORY_MAINNET_CONTRACTS = {
        "IPAssetRegistry": "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a",  # Placeholder
        "LicenseRegistry": "0x2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b",  # Placeholder
        "RoyaltyModule": "0x3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c",  # Placeholder
        "PILFramework": "0x4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d",  # Placeholder
    }

    # Story Protocol testnet addresses
    STORY_TESTNET_CONTRACTS = {
        "IPAssetRegistry": "0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
        "LicenseRegistry": "0xb2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2",
        "RoyaltyModule": "0xc3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3",
        "PILFramework": "0xd4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4",
    }

    def __init__(
        self,
        web3: Web3,
        network: str = "mainnet",
        custom_addresses: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Story Protocol client.

        Args:
            web3: Web3 instance connected to blockchain
            network: Network name ("mainnet", "testnet", "localhost")
            custom_addresses: Custom contract addresses (overrides defaults)
        """
        self.w3 = web3
        self.network = network

        # Select contract addresses
        if custom_addresses:
            self.addresses = custom_addresses
        elif network == "mainnet":
            self.addresses = self.STORY_MAINNET_CONTRACTS
        else:
            self.addresses = self.STORY_TESTNET_CONTRACTS

        # Initialize contract interfaces
        self.ip_asset_registry: Optional[Contract] = None
        self.license_registry: Optional[Contract] = None
        self.royalty_module: Optional[Contract] = None
        self.pil_framework: Optional[Contract] = None

        self._init_contracts()

    def _init_contracts(self) -> None:
        """Initialize contract instances with ABIs."""
        # IP Asset Registry Contract
        self.ip_asset_registry = self.w3.eth.contract(
            address=to_checksum_address(self.addresses["IPAssetRegistry"]),
            abi=self._get_ip_asset_registry_abi()
        )

        # License Registry Contract
        self.license_registry = self.w3.eth.contract(
            address=to_checksum_address(self.addresses["LicenseRegistry"]),
            abi=self._get_license_registry_abi()
        )

        # Royalty Module Contract
        self.royalty_module = self.w3.eth.contract(
            address=to_checksum_address(self.addresses["RoyaltyModule"]),
            abi=self._get_royalty_module_abi()
        )

        # PIL Framework Contract
        self.pil_framework = self.w3.eth.contract(
            address=to_checksum_address(self.addresses["PILFramework"]),
            abi=self._get_pil_framework_abi()
        )

    def register_ip_asset(
        self,
        owner_address: str,
        metadata: IPAssetMetadata,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Register a repository as an IP Asset on Story Protocol.

        Args:
            owner_address: Ethereum address of the IP owner
            metadata: IP Asset metadata
            private_key: Private key for signing transaction

        Returns:
            Dictionary with transaction hash and IP Asset ID
        """
        if not self.ip_asset_registry:
            raise ValueError("IP Asset Registry not initialized")

        # Encode metadata
        metadata_bytes = self._encode_metadata(metadata)

        # Build transaction
        txn = self.ip_asset_registry.functions.register(
            to_checksum_address(owner_address),
            metadata_bytes
        ).build_transaction({
            'from': to_checksum_address(owner_address),
            'nonce': self.w3.eth.get_transaction_count(owner_address),
            'gas': 500000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # Extract IP Asset ID from logs
        ip_asset_id = self._extract_ip_asset_id(receipt)

        return {
            "tx_hash": tx_hash.hex(),
            "ip_asset_id": ip_asset_id,
            "block_number": receipt['blockNumber'],
            "status": "success" if receipt['status'] == 1 else "failed"
        }

    def attach_license_terms(
        self,
        ip_asset_id: str,
        pil_terms: PILTerms,
        owner_address: str,
        private_key: str
    ) -> str:
        """
        Attach Programmable IP License (PIL) terms to an IP Asset.

        Args:
            ip_asset_id: ID of the registered IP Asset
            pil_terms: License terms to attach
            owner_address: Owner's Ethereum address
            private_key: Private key for signing

        Returns:
            Transaction hash
        """
        if not self.pil_framework:
            raise ValueError("PIL Framework not initialized")

        # Encode license terms
        terms_bytes = self._encode_pil_terms(pil_terms)

        # Build transaction
        txn = self.pil_framework.functions.attachLicenseTerms(
            ip_asset_id,
            terms_bytes
        ).build_transaction({
            'from': to_checksum_address(owner_address),
            'nonce': self.w3.eth.get_transaction_count(owner_address),
            'gas': 300000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return tx_hash.hex()

    def mint_license(
        self,
        ip_asset_id: str,
        licensee_address: str,
        license_terms_id: str,
        amount: int,
        minter_address: str,
        private_key: str
    ) -> str:
        """
        Mint a license NFT for an IP Asset.

        Args:
            ip_asset_id: ID of the IP Asset
            licensee_address: Address receiving the license
            license_terms_id: ID of the license terms to use
            amount: Number of licenses to mint
            minter_address: Address minting the license (usually owner)
            private_key: Private key for signing

        Returns:
            Transaction hash
        """
        if not self.license_registry:
            raise ValueError("License Registry not initialized")

        # Build transaction
        txn = self.license_registry.functions.mintLicense(
            ip_asset_id,
            to_checksum_address(licensee_address),
            license_terms_id,
            amount
        ).build_transaction({
            'from': to_checksum_address(minter_address),
            'nonce': self.w3.eth.get_transaction_count(minter_address),
            'gas': 250000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return tx_hash.hex()

    def register_derivative(
        self,
        parent_ip_asset_id: str,
        derivative_owner_address: str,
        derivative_metadata: IPAssetMetadata,
        license_terms_id: str,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Register a derivative work (fork) linked to parent IP Asset.

        This enables automatic royalty tracking and enforcement.

        Args:
            parent_ip_asset_id: ID of the parent IP Asset
            derivative_owner_address: Owner of the derivative
            derivative_metadata: Metadata for the derivative
            license_terms_id: License terms being used
            private_key: Private key for signing

        Returns:
            Dictionary with derivative IP Asset ID and transaction hash
        """
        if not self.ip_asset_registry:
            raise ValueError("IP Asset Registry not initialized")

        # Encode metadata
        metadata_bytes = self._encode_metadata(derivative_metadata)

        # Build transaction
        txn = self.ip_asset_registry.functions.registerDerivative(
            to_checksum_address(derivative_owner_address),
            parent_ip_asset_id,
            license_terms_id,
            metadata_bytes
        ).build_transaction({
            'from': to_checksum_address(derivative_owner_address),
            'nonce': self.w3.eth.get_transaction_count(derivative_owner_address),
            'gas': 600000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        derivative_id = self._extract_ip_asset_id(receipt)

        return {
            "tx_hash": tx_hash.hex(),
            "derivative_ip_asset_id": derivative_id,
            "parent_ip_asset_id": parent_ip_asset_id,
            "status": "success" if receipt['status'] == 1 else "failed"
        }

    def set_royalty_policy(
        self,
        ip_asset_id: str,
        royalty_percentage: int,  # Basis points (0-10000)
        payment_token: str,  # ERC20 token address
        owner_address: str,
        private_key: str
    ) -> str:
        """
        Set royalty policy for an IP Asset.

        Args:
            ip_asset_id: ID of the IP Asset
            royalty_percentage: Royalty in basis points (e.g., 1500 = 15%)
            payment_token: Address of ERC20 token for royalty payments
            owner_address: Owner's Ethereum address
            private_key: Private key for signing

        Returns:
            Transaction hash
        """
        if not self.royalty_module:
            raise ValueError("Royalty Module not initialized")

        if royalty_percentage > 10000:
            raise ValueError("Royalty percentage cannot exceed 100% (10000 basis points)")

        # Build transaction
        txn = self.royalty_module.functions.setRoyaltyPolicy(
            ip_asset_id,
            royalty_percentage,
            to_checksum_address(payment_token)
        ).build_transaction({
            'from': to_checksum_address(owner_address),
            'nonce': self.w3.eth.get_transaction_count(owner_address),
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return tx_hash.hex()

    def get_ip_asset_info(self, ip_asset_id: str) -> Dict[str, Any]:
        """
        Get information about an IP Asset.

        Args:
            ip_asset_id: ID of the IP Asset

        Returns:
            Dictionary with IP Asset information
        """
        if not self.ip_asset_registry:
            raise ValueError("IP Asset Registry not initialized")

        info = self.ip_asset_registry.functions.getIPAsset(ip_asset_id).call()

        return {
            "id": ip_asset_id,
            "owner": info[0],
            "metadata": self._decode_metadata(info[1]),
            "created_at": info[2],
            "is_active": info[3]
        }

    def get_derivatives(self, parent_ip_asset_id: str) -> List[str]:
        """
        Get all derivative IP Assets for a parent.

        Args:
            parent_ip_asset_id: ID of the parent IP Asset

        Returns:
            List of derivative IP Asset IDs
        """
        if not self.ip_asset_registry:
            raise ValueError("IP Asset Registry not initialized")

        return self.ip_asset_registry.functions.getDerivatives(
            parent_ip_asset_id
        ).call()

    def get_royalty_info(self, ip_asset_id: str) -> Dict[str, Any]:
        """
        Get royalty information for an IP Asset.

        Args:
            ip_asset_id: ID of the IP Asset

        Returns:
            Dictionary with royalty information
        """
        if not self.royalty_module:
            raise ValueError("Royalty Module not initialized")

        info = self.royalty_module.functions.getRoyaltyPolicy(ip_asset_id).call()

        return {
            "royalty_percentage": info[0],  # Basis points
            "payment_token": info[1],
            "total_collected": info[2],
            "last_payment_timestamp": info[3]
        }

    # Helper methods for encoding/decoding

    def _encode_metadata(self, metadata: IPAssetMetadata) -> bytes:
        """Encode IP Asset metadata for on-chain storage."""
        # Simplified encoding - in production would use proper ABI encoding
        import json
        metadata_dict = {
            "name": metadata.name,
            "description": metadata.description,
            "ipType": metadata.ipType,
            "createdAt": metadata.createdAt,
            "ipfsHash": metadata.ipfsHash,
            "externalUrl": metadata.externalUrl
        }
        return json.dumps(metadata_dict).encode('utf-8')

    def _decode_metadata(self, metadata_bytes: bytes) -> Dict[str, Any]:
        """Decode IP Asset metadata from on-chain storage."""
        import json
        return json.loads(metadata_bytes.decode('utf-8'))

    def _encode_pil_terms(self, terms: PILTerms) -> bytes:
        """Encode PIL terms for on-chain storage."""
        import json
        terms_dict = {
            "commercial_use": terms.commercial_use,
            "derivatives_allowed": terms.derivatives_allowed,
            "derivatives_approve": terms.derivatives_approve,
            "derivatives_attribution": terms.derivatives_attribution,
            "derivatives_reciprocal": terms.derivatives_reciprocal,
            "royalty_policy": terms.royalty_policy,
            "commercial_revenue_share": terms.commercial_revenue_share,
            "territory_restriction": terms.territory_restriction,
            "distribution_channels": terms.distribution_channels
        }
        return json.dumps(terms_dict).encode('utf-8')

    def _extract_ip_asset_id(self, receipt: Dict[str, Any]) -> str:
        """Extract IP Asset ID from transaction receipt logs."""
        # In production, would parse event logs properly
        # For now, return placeholder
        if receipt['logs']:
            # Simplified: use transaction hash as asset ID
            return f"ip_asset_{receipt['transactionHash'].hex()[:16]}"
        return "ip_asset_unknown"

    # Contract ABIs (simplified - in production would use full ABIs)

    @staticmethod
    def _get_ip_asset_registry_abi() -> List[Dict[str, Any]]:
        """Get IP Asset Registry contract ABI."""
        return [
            {
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "metadata", "type": "bytes"}
                ],
                "name": "register",
                "outputs": [{"name": "ipAssetId", "type": "bytes32"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "parentIpAssetId", "type": "bytes32"},
                    {"name": "licenseTermsId", "type": "bytes32"},
                    {"name": "metadata", "type": "bytes"}
                ],
                "name": "registerDerivative",
                "outputs": [{"name": "derivativeId", "type": "bytes32"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "ipAssetId", "type": "bytes32"}],
                "name": "getIPAsset",
                "outputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "metadata", "type": "bytes"},
                    {"name": "createdAt", "type": "uint256"},
                    {"name": "isActive", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "parentId", "type": "bytes32"}],
                "name": "getDerivatives",
                "outputs": [{"name": "", "type": "bytes32[]"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    @staticmethod
    def _get_license_registry_abi() -> List[Dict[str, Any]]:
        """Get License Registry contract ABI."""
        return [
            {
                "inputs": [
                    {"name": "ipAssetId", "type": "bytes32"},
                    {"name": "licensee", "type": "address"},
                    {"name": "licenseTermsId", "type": "bytes32"},
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "mintLicense",
                "outputs": [{"name": "licenseId", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]

    @staticmethod
    def _get_royalty_module_abi() -> List[Dict[str, Any]]:
        """Get Royalty Module contract ABI."""
        return [
            {
                "inputs": [
                    {"name": "ipAssetId", "type": "bytes32"},
                    {"name": "royaltyPercentage", "type": "uint256"},
                    {"name": "paymentToken", "type": "address"}
                ],
                "name": "setRoyaltyPolicy",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "ipAssetId", "type": "bytes32"}],
                "name": "getRoyaltyPolicy",
                "outputs": [
                    {"name": "percentage", "type": "uint256"},
                    {"name": "paymentToken", "type": "address"},
                    {"name": "totalCollected", "type": "uint256"},
                    {"name": "lastPaymentTimestamp", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    @staticmethod
    def _get_pil_framework_abi() -> List[Dict[str, Any]]:
        """Get PIL Framework contract ABI."""
        return [
            {
                "inputs": [
                    {"name": "ipAssetId", "type": "bytes32"},
                    {"name": "termsData", "type": "bytes"}
                ],
                "name": "attachLicenseTerms",
                "outputs": [{"name": "termsId", "type": "bytes32"}],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
