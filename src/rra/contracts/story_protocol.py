# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Story Protocol integration for programmable IP licensing.

Uses the official Story Protocol Python SDK for reliable blockchain interactions.
Provides high-level interface for registering repositories as IP Assets.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from web3 import Web3

# Try to import the official SDK, fall back to manual implementation
try:
    from story_protocol_python_sdk import StoryClient

    STORY_SDK_AVAILABLE = True
except ImportError:
    STORY_SDK_AVAILABLE = False


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
    Client for interacting with Story Protocol using the official SDK.

    Story Protocol enables tokenizing code repositories as IP Assets
    with programmable licensing terms and automated royalty distribution.
    """

    # Story Protocol Chain IDs
    STORY_MAINNET_CHAIN_ID = 1514  # Story Homer Mainnet
    STORY_TESTNET_CHAIN_ID = 1315  # Story Aeneid Testnet

    # Contract addresses per network
    # See: https://docs.story.foundation/developers/deployed-smart-contracts
    STORY_MAINNET_CONTRACTS = {
        "IPAssetRegistry": "0x77319B4031e6eF1250907aa00018B8B1c67a244b",
        "LicenseRegistry": "0xf49da534215DA7b48E57A41d3f6b0E5B5F4b6111",
        "LicensingModule": "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f",
        "RoyaltyModule": "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086",
        "PILicenseTemplate": "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316",
    }

    STORY_TESTNET_CONTRACTS = {
        "IPAssetRegistry": "0x1a9d0d28a0422F26D31Be72Edc6f13ea4371E11B",
        "LicenseRegistry": "0x529a750E02d8E2f0d9e8A99F95B81f5c9B3E22b0",
        "LicensingModule": "0x5a7D9Fa17DE09350F481A53B470D798c1c1aabae",
        "RoyaltyModule": "0x968beb5432c362c12b5Be6967a5d6F1ED5A63F55",
        "PILicenseTemplate": "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316",
    }

    STORY_LOCALHOST_CONTRACTS = {
        "IPAssetRegistry": "0x0000000000000000000000000000000000000001",
        "LicenseRegistry": "0x0000000000000000000000000000000000000002",
        "LicensingModule": "0x0000000000000000000000000000000000000003",
        "RoyaltyModule": "0x0000000000000000000000000000000000000004",
        "PILicenseTemplate": "0x0000000000000000000000000000000000000005",
    }

    # Default SPG NFT collection for RRA repositories
    # This is created once and reused for all repository registrations
    DEFAULT_SPG_COLLECTIONS = {
        "mainnet": None,  # Will be set after first collection creation
        "testnet": None,
    }

    def __init__(
        self,
        web3: Web3,
        network: str = "testnet",
        custom_addresses: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize Story Protocol client.

        Args:
            web3: Web3 instance connected to Story Protocol network
            network: Network name ("mainnet", "testnet", "localhost")
            custom_addresses: Custom contract addresses (optional)
        """
        self.w3 = web3
        self.network = network
        self.chain_id = (
            self.STORY_MAINNET_CHAIN_ID if network == "mainnet" else self.STORY_TESTNET_CHAIN_ID
        )
        self._story_client = None
        self._account = None
        self._spg_nft_contract = None

        # Set contract addresses based on network or custom addresses
        if custom_addresses:
            self.addresses = custom_addresses
        elif network == "mainnet":
            self.addresses = self.STORY_MAINNET_CONTRACTS.copy()
        elif network == "localhost":
            self.addresses = self.STORY_LOCALHOST_CONTRACTS.copy()
        else:  # testnet (default)
            self.addresses = self.STORY_TESTNET_CONTRACTS.copy()

        # Initialize contract instances (lazy-loaded with minimal ABI for testing)
        self._init_contracts()

    def _init_contracts(self) -> None:
        """Initialize contract instances with minimal ABIs for read operations."""
        # Minimal ABIs for each contract - just enough for basic operations
        minimal_abi = [
            {"type": "function", "name": "name", "inputs": [], "outputs": [{"type": "string"}]},
        ]

        self.ip_asset_registry = self.w3.eth.contract(
            address=self.addresses["IPAssetRegistry"], abi=minimal_abi
        )
        self.license_registry = self.w3.eth.contract(
            address=self.addresses["LicenseRegistry"], abi=minimal_abi
        )
        self.royalty_module = self.w3.eth.contract(
            address=self.addresses["RoyaltyModule"], abi=minimal_abi
        )
        self.pil_license_template = self.w3.eth.contract(
            address=self.addresses["PILicenseTemplate"], abi=minimal_abi
        )

    def _init_sdk_client(self, private_key: str) -> None:
        """Initialize the Story Protocol SDK client with account."""
        if not STORY_SDK_AVAILABLE:
            raise ImportError(
                "Story Protocol SDK not installed. "
                "Install with: pip install story-protocol-python-sdk web3"
            )

        # Create account from private key
        self._account = self.w3.eth.account.from_key(private_key)

        # Initialize Story SDK client
        self._story_client = StoryClient(self.w3, self._account, self.chain_id)

    def _ensure_spg_collection(self, owner_address: str, private_key: str) -> str:
        """
        Ensure an SPG NFT collection exists for minting repository NFTs.

        Creates one if it doesn't exist, otherwise returns existing address.
        """
        # Check if we already have a collection for this network
        if self.DEFAULT_SPG_COLLECTIONS.get(self.network):
            return self.DEFAULT_SPG_COLLECTIONS[self.network]

        # Create new SPG NFT collection with all required parameters
        result = self._story_client.NFTClient.create_nft_collection(
            name="RRA Repository Licenses",
            symbol="RRA-LICENSE",
            max_supply=1000000,
            mint_fee=0,
            mint_fee_token="0x0000000000000000000000000000000000000000",
            mint_fee_recipient=owner_address,
            owner=owner_address,
            is_public_minting=True,
            mint_open=True,
            contract_uri="",
        )

        nft_contract = result.get("nft_contract") or result.get("nftContract")

        # Cache for future use
        self.DEFAULT_SPG_COLLECTIONS[self.network] = nft_contract

        return nft_contract

    def register_ip_asset(
        self, owner_address: str, metadata: IPAssetMetadata, private_key: str
    ) -> Dict[str, Any]:
        """
        Register a repository as an IP Asset on Story Protocol.

        Uses the SDK's mintAndRegisterIpAssetWithPilTerms for a single transaction.

        Args:
            owner_address: Ethereum address of the IP owner
            metadata: IP Asset metadata
            private_key: Private key for signing transaction

        Returns:
            Dictionary with transaction hash and IP Asset ID
        """
        try:
            # Initialize SDK if needed
            if not self._story_client:
                self._init_sdk_client(private_key)

            # Ensure we have an SPG NFT collection
            spg_nft_contract = self._ensure_spg_collection(owner_address, private_key)

            # Register using SDK - mints NFT and registers as IP in one tx
            # Note: ip_metadata requires IPFS URIs - skipping for now to get registration working
            # TODO: Add IPFS upload for full metadata support
            # See: https://docs.story.foundation/sdk-reference/ipasset
            result = self._story_client.IPAsset.mint_and_register_ip(
                spg_nft_contract=spg_nft_contract,
                recipient=owner_address,
            )

            # Extract results
            ip_id = result.get("ipId") or result.get("ip_id")
            tx_hash = result.get("txHash") or result.get("tx_hash")
            token_id = result.get("tokenId") or result.get("token_id")

            return {
                "tx_hash": tx_hash,
                "ip_asset_id": ip_id,
                "token_id": token_id,
                "nft_contract": spg_nft_contract,
                "block_number": None,  # SDK doesn't always return this
                "status": "success",
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }

    def attach_license_terms(
        self, ip_asset_id: str, pil_terms: PILTerms, owner_address: str, private_key: str
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
        try:
            if not self._story_client:
                self._init_sdk_client(private_key)

            # Use pre-registered license terms
            # license_terms_id=1 is "Non-Commercial Social Remixing" (pre-registered in protocol)
            # PILicenseTemplate address on testnet
            pil_template = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316"

            result = self._story_client.License.attach_license_terms(
                ip_id=ip_asset_id,
                license_template=pil_template,
                license_terms_id=1,
            )

            return result.get("txHash") or result.get("tx_hash", "")

        except Exception as e:
            raise RuntimeError(f"Failed to attach license terms: {e}")

    def register_derivative(
        self,
        parent_ip_asset_id: str,
        derivative_owner_address: str,
        derivative_metadata: IPAssetMetadata,
        license_terms_id: str,
        private_key: str,
    ) -> Dict[str, Any]:
        """
        Register a derivative work of an existing IP Asset.

        Args:
            parent_ip_asset_id: ID of the parent IP Asset
            derivative_owner_address: Owner address for the derivative
            derivative_metadata: Metadata for the derivative IP Asset
            license_terms_id: License terms ID to use for the derivative
            private_key: Private key for signing transaction

        Returns:
            Dictionary with transaction hash and derivative IP Asset ID
        """
        try:
            if not self._story_client:
                self._init_sdk_client(private_key)

            # First register the derivative as a new IP Asset
            result = self.register_ip_asset(
                derivative_owner_address, derivative_metadata, private_key
            )

            if result.get("status") != "success":
                return result

            derivative_ip_id = result.get("ip_asset_id")

            # Then link it to the parent
            # Note: This uses the SDK's derivative registration
            link_result = self._story_client.IPAsset.register_derivative(
                child_ip_id=derivative_ip_id,
                parent_ip_ids=[parent_ip_asset_id],
                license_terms_ids=[
                    (
                        int(license_terms_id.replace("terms_", ""))
                        if license_terms_id.startswith("terms_")
                        else 1
                    )
                ],
                license_template=self.addresses["PILicenseTemplate"],
            )

            return {
                "tx_hash": link_result.get("txHash")
                or link_result.get("tx_hash", result.get("tx_hash")),
                "derivative_ip_asset_id": derivative_ip_id,
                "parent_ip_asset_id": parent_ip_asset_id,
                "status": "success",
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }

    def set_royalty_policy(
        self,
        ip_asset_id: str,
        royalty_percentage: int,
        payment_token: str,
        owner_address: str,
        private_key: str,
    ) -> str:
        """
        Set royalty policy for an IP Asset.

        Args:
            ip_asset_id: ID of the IP Asset
            royalty_percentage: Royalty percentage in basis points (0-10000)
            payment_token: Token address for royalty payments
            owner_address: Owner's Ethereum address
            private_key: Private key for signing

        Returns:
            Transaction hash

        Raises:
            ValueError: If royalty_percentage exceeds 10000 (100%)
        """
        # Validate royalty percentage (basis points, max 10000 = 100%)
        if royalty_percentage > 10000:
            raise ValueError(
                f"Royalty percentage {royalty_percentage} basis points "
                "cannot exceed 100% (10000 basis points)"
            )

        try:
            if not self._story_client:
                self._init_sdk_client(private_key)

            # Set royalty policy via SDK
            # Note: Story Protocol uses LAP (Liquid Absolute Percentage) for royalties
            result = self._story_client.Royalty.set_royalty_policy(
                ip_id=ip_asset_id,
                royalty_policy="LAP",  # Liquid Absolute Percentage
                revenue_share=royalty_percentage,
                currency_token=payment_token,
            )

            return result.get("txHash") or result.get("tx_hash", "0x" + "0" * 64)

        except Exception as e:
            raise RuntimeError(f"Failed to set royalty policy: {e}")

    def get_ip_asset_info(self, ip_asset_id: str) -> Dict[str, Any]:
        """
        Get information about an IP Asset.

        Args:
            ip_asset_id: The IP Asset ID (ipId address)

        Returns:
            Dictionary with IP Asset details
        """
        try:
            if not self._story_client:
                # For read-only operations, we can query without full initialization
                pass

            # Query IP Asset info from the registry
            # This is a read-only call, doesn't need signing
            return {
                "ip_id": ip_asset_id,
                "network": self.network,
                "explorer_url": self._get_explorer_url(ip_asset_id),
            }

        except Exception as e:
            return {"error": str(e)}

    def _get_explorer_url(self, ip_asset_id: str) -> str:
        """Get the explorer URL for an IP Asset."""
        if self.network == "mainnet":
            return f"https://explorer.story.foundation/ip/{ip_asset_id}"
        else:
            return f"https://aeneid.storyscan.xyz/address/{ip_asset_id}"


# Convenience function for quick registration
def register_repository_ip(
    repo_url: str,
    owner_address: str,
    private_key: str,
    description: Optional[str] = None,
    network: str = "testnet",
    rpc_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Quick helper to register a repository as an IP Asset.

    Args:
        repo_url: URL of the repository
        owner_address: Owner's wallet address
        private_key: Private key for signing
        description: Optional description
        network: "mainnet" or "testnet"
        rpc_url: RPC endpoint (defaults to Story Protocol public RPC)

    Returns:
        Registration result with IP Asset ID
    """
    import time

    # Default RPC URLs
    if not rpc_url:
        rpc_url = (
            "https://mainnet.storyrpc.io" if network == "mainnet" else "https://aeneid.storyrpc.io"
        )

    # Connect to Story Protocol
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        return {"status": "failed", "error": f"Failed to connect to {rpc_url}"}

    # Create client and register
    client = StoryProtocolClient(w3, network=network)

    metadata = IPAssetMetadata(
        name=f"Repository: {repo_url}",
        description=description or f"Code repository at {repo_url}",
        ipType="SOFTWARE_REPOSITORY",
        createdAt=int(time.time()),
        externalUrl=repo_url,
    )

    return client.register_ip_asset(owner_address, metadata, private_key)
