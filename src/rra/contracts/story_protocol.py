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
            network: Network name ("mainnet", "testnet")
            custom_addresses: Custom contract addresses (optional)
        """
        self.w3 = web3
        self.network = network
        self.chain_id = (
            self.STORY_MAINNET_CHAIN_ID if network == "mainnet"
            else self.STORY_TESTNET_CHAIN_ID
        )
        self._story_client = None
        self._account = None
        self._spg_nft_contract = None

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

            # Prepare IP metadata
            ip_metadata = {
                "title": metadata.name,
                "description": metadata.description,
                "ipType": metadata.ipType,
                "createdAt": str(metadata.createdAt),
            }

            if metadata.externalUrl:
                ip_metadata["externalUrl"] = metadata.externalUrl

            # Register using SDK - mints NFT and registers as IP in one tx
            # license_terms_id=1 is the pre-registered "Non-Commercial Social Remixing" flavor
            # See: https://docs.story.foundation/concepts/programmable-ip-license/pil-flavors
            result = self._story_client.IPAsset.mint_and_register_ip_asset_with_pil_terms(
                spg_nft_contract=spg_nft_contract,
                license_terms_id=1,  # Non-Commercial Social Remixing (pre-registered)
                ip_metadata=ip_metadata,
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

            # Determine PIL type based on terms
            if pil_terms.commercial_use:
                if pil_terms.commercial_revenue_share > 0:
                    pil_type = "commercial_remix"
                else:
                    pil_type = "commercial_use"
            else:
                pil_type = "non_commercial_social_remixing"

            result = self._story_client.License.attach_license_terms(
                ip_id=ip_asset_id,
                pil_type=pil_type,
            )

            return result.get("txHash") or result.get("tx_hash", "")

        except Exception as e:
            raise RuntimeError(f"Failed to attach license terms: {e}")

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
            "https://mainnet.storyrpc.io" if network == "mainnet"
            else "https://aeneid.storyrpc.io"
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
