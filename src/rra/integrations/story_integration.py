# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Story Protocol integration manager for RRA Module.

Provides high-level interface for registering repositories as IP Assets
and managing programmable licenses via Story Protocol.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import time
from web3 import Web3

from rra.contracts.story_protocol import (
    StoryProtocolClient,
    IPAssetMetadata,
    PILTerms
)
from rra.config.market_config import MarketConfig


class StoryIntegrationManager:
    """
    Manages Story Protocol integration for repository licensing.

    Handles IP Asset registration, PIL term attachment, derivative tracking,
    and royalty enforcement for code repositories.
    """

    def __init__(
        self,
        web3: Web3,
        network: str = "mainnet",
        custom_addresses: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Story Integration Manager.

        Args:
            web3: Web3 instance connected to blockchain
            network: Network name ("mainnet", "testnet", "localhost")
            custom_addresses: Custom Story Protocol contract addresses
        """
        self.w3 = web3
        self.network = network
        self.story_client = StoryProtocolClient(web3, network, custom_addresses)

    def register_repository_as_ip_asset(
        self,
        repo_url: str,
        market_config: MarketConfig,
        owner_address: str,
        private_key: str,
        repo_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a repository as an IP Asset on Story Protocol.

        Args:
            repo_url: Repository URL (e.g., github.com/user/repo)
            market_config: Repository market configuration
            owner_address: Owner's Ethereum address
            private_key: Private key for signing transactions
            repo_description: Optional description override

        Returns:
            Dictionary with IP Asset ID and registration details
        """
        if not market_config.story_protocol_enabled:
            raise ValueError(
                "Story Protocol not enabled in market config. "
                "Set story_protocol_enabled: true in .market.yaml"
            )

        # Create IP Asset metadata
        metadata = IPAssetMetadata(
            name=f"Repository: {repo_url}",
            description=repo_description or market_config.description or f"Code repository at {repo_url}",
            ipType="SOFTWARE_REPOSITORY",
            createdAt=int(time.time()),
            externalUrl=repo_url,
            ipfsHash=None  # Could be populated with IPFS hash of repo snapshot
        )

        # Register IP Asset
        result = self.story_client.register_ip_asset(
            owner_address=owner_address,
            metadata=metadata,
            private_key=private_key
        )

        # Attach PIL terms
        pil_terms = self._market_config_to_pil_terms(market_config)

        if result["status"] == "success":
            terms_tx = self.story_client.attach_license_terms(
                ip_asset_id=result["ip_asset_id"],
                pil_terms=pil_terms,
                owner_address=owner_address,
                private_key=private_key
            )
            result["pil_terms_tx"] = terms_tx

            # Set royalty policy if configured
            if market_config.derivative_royalty_percentage:
                royalty_tx = self._set_royalty_policy(
                    ip_asset_id=result["ip_asset_id"],
                    royalty_percentage=market_config.derivative_royalty_percentage,
                    owner_address=owner_address,
                    private_key=private_key
                )
                result["royalty_tx"] = royalty_tx

        return result

    def register_derivative_repository(
        self,
        parent_repo_url: str,
        parent_ip_asset_id: str,
        fork_repo_url: str,
        fork_description: str,
        license_terms_id: str,
        fork_owner_address: str,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Register a forked/derivative repository linked to parent IP Asset.

        This enables automatic royalty tracking from forks back to original.

        Args:
            parent_repo_url: URL of parent repository
            parent_ip_asset_id: Story Protocol IP Asset ID of parent
            fork_repo_url: URL of fork/derivative repository
            fork_description: Description of the fork
            license_terms_id: License terms being used from parent
            fork_owner_address: Owner of the fork
            private_key: Private key for signing

        Returns:
            Dictionary with derivative IP Asset details
        """
        # Create derivative metadata
        derivative_metadata = IPAssetMetadata(
            name=f"Fork: {fork_repo_url}",
            description=f"{fork_description} (Derivative of {parent_repo_url})",
            ipType="SOFTWARE_REPOSITORY_DERIVATIVE",
            createdAt=int(time.time()),
            externalUrl=fork_repo_url,
            ipfsHash=None
        )

        # Register derivative
        result = self.story_client.register_derivative(
            parent_ip_asset_id=parent_ip_asset_id,
            derivative_owner_address=fork_owner_address,
            derivative_metadata=derivative_metadata,
            license_terms_id=license_terms_id,
            private_key=private_key
        )

        return result

    def mint_license_for_buyer(
        self,
        ip_asset_id: str,
        buyer_address: str,
        license_terms_id: str,
        quantity: int,
        issuer_address: str,
        private_key: str
    ) -> str:
        """
        Mint a license NFT for a repository buyer.

        Args:
            ip_asset_id: IP Asset ID of the repository
            buyer_address: Buyer's Ethereum address
            license_terms_id: ID of license terms to use
            quantity: Number of licenses to mint
            issuer_address: Address issuing the license (repo owner)
            private_key: Private key for signing

        Returns:
            Transaction hash
        """
        return self.story_client.mint_license(
            ip_asset_id=ip_asset_id,
            licensee_address=buyer_address,
            license_terms_id=license_terms_id,
            amount=quantity,
            minter_address=issuer_address,
            private_key=private_key
        )

    def get_repository_derivatives(self, ip_asset_id: str) -> Dict[str, Any]:
        """
        Get all derivative repositories (forks) for a given IP Asset.

        Args:
            ip_asset_id: IP Asset ID of the parent repository

        Returns:
            Dictionary with derivative information
        """
        derivative_ids = self.story_client.get_derivatives(ip_asset_id)

        derivatives = []
        for derivative_id in derivative_ids:
            info = self.story_client.get_ip_asset_info(derivative_id)
            derivatives.append(info)

        return {
            "parent_ip_asset_id": ip_asset_id,
            "derivative_count": len(derivatives),
            "derivatives": derivatives
        }

    def get_royalty_stats(self, ip_asset_id: str) -> Dict[str, Any]:
        """
        Get royalty statistics for a repository IP Asset.

        Args:
            ip_asset_id: IP Asset ID

        Returns:
            Dictionary with royalty information
        """
        royalty_info = self.story_client.get_royalty_info(ip_asset_id)

        return {
            "ip_asset_id": ip_asset_id,
            "royalty_percentage": royalty_info["royalty_percentage"] / 100,  # Convert from basis points
            "payment_token": royalty_info["payment_token"],
            "total_collected_wei": royalty_info["total_collected"],
            "total_collected_eth": self.w3.from_wei(royalty_info["total_collected"], 'ether'),
            "last_payment_timestamp": royalty_info["last_payment_timestamp"]
        }

    def update_market_config_with_ip_asset(
        self,
        market_config_path: Path,
        ip_asset_id: str
    ) -> None:
        """
        Update .market.yaml with Story Protocol IP Asset ID.

        Args:
            market_config_path: Path to .market.yaml file
            ip_asset_id: IP Asset ID to save
        """
        config = MarketConfig.from_yaml(market_config_path)
        config.ip_asset_id = ip_asset_id
        config.to_yaml(market_config_path)

    # Helper methods

    def _market_config_to_pil_terms(self, config: MarketConfig) -> PILTerms:
        """Convert MarketConfig to Story Protocol PIL terms."""
        pil_dict = config.to_pil_terms()

        return PILTerms(
            commercial_use=pil_dict["commercial_use"],
            derivatives_allowed=pil_dict["derivatives_allowed"],
            derivatives_approve=pil_dict["derivatives_approve"],
            derivatives_attribution=pil_dict["derivatives_attribution"],
            derivatives_reciprocal=pil_dict["derivatives_reciprocal"],
            royalty_policy=pil_dict["royalty_policy"],
            commercial_revenue_share=pil_dict["commercial_revenue_share"],
            territory_restriction=pil_dict["territory_restriction"],
            distribution_channels=pil_dict["distribution_channels"]
        )

    def _set_royalty_policy(
        self,
        ip_asset_id: str,
        royalty_percentage: float,
        owner_address: str,
        private_key: str,
        payment_token: str = "0x0000000000000000000000000000000000000000"  # ETH
    ) -> str:
        """
        Set royalty policy for an IP Asset.

        Args:
            ip_asset_id: IP Asset ID
            royalty_percentage: Royalty percentage (0.0-1.0)
            owner_address: Owner's address
            private_key: Private key for signing
            payment_token: Payment token address (default: ETH)

        Returns:
            Transaction hash
        """
        royalty_bps = int(royalty_percentage * 10000)

        return self.story_client.set_royalty_policy(
            ip_asset_id=ip_asset_id,
            royalty_percentage=royalty_bps,
            payment_token=payment_token,
            owner_address=owner_address,
            private_key=private_key
        )

    def get_network_info(self) -> Dict[str, Any]:
        """
        Get Story Protocol network information.

        Returns:
            Dictionary with network and contract information
        """
        return {
            "network": self.network,
            "connected": self.w3.is_connected(),
            "chain_id": self.w3.eth.chain_id if self.w3.is_connected() else None,
            "story_contracts": self.story_client.addresses
        }
