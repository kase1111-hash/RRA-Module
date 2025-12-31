# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Contract Manager for handling smart contract operations.

Manages contract deployment, configuration, and lifecycle.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import json
import os
from web3 import Web3

from rra.contracts.license_nft import LicenseNFTContract
from rra.contracts.artifacts import is_compiled, available_contracts


class ContractManager:
    """
    Manages smart contract deployment and configuration.

    Provides high-level interface for contract operations across
    different networks.
    """

    def __init__(
        self,
        network: str = "mainnet",
        provider_url: Optional[str] = None
    ):
        """
        Initialize ContractManager.

        Args:
            network: Network name ("mainnet", "sepolia", "localhost", etc.)
            provider_url: Optional custom provider URL
        """
        self.network = network

        # Setup Web3 provider
        if provider_url:
            self.w3 = Web3(Web3.HTTPProvider(provider_url))
        else:
            self.w3 = self._get_default_provider(network)

        # Contract instances
        self.license_contract: Optional[LicenseNFTContract] = None

        # Load deployed contracts if available
        self._load_deployments()

    def _get_default_provider(self, network: str) -> Web3:
        """Get default provider for a network."""
        providers = {
            "mainnet": "https://mainnet.infura.io/v3/YOUR_INFURA_KEY",
            "sepolia": "https://sepolia.infura.io/v3/YOUR_INFURA_KEY",
            "localhost": "http://127.0.0.1:8545",
        }

        if network not in providers:
            raise ValueError(f"Unknown network: {network}")

        return Web3(Web3.HTTPProvider(providers[network]))

    def _load_deployments(self) -> None:
        """Load deployed contract addresses from file."""
        deployments_file = Path(f"deployments/{self.network}.json")

        if deployments_file.exists():
            with open(deployments_file) as f:
                deployments = json.load(f)

                if "RepoLicense" in deployments:
                    self.license_contract = LicenseNFTContract(
                        self.w3,
                        contract_address=deployments["RepoLicense"]
                    )

    def save_deployment(self, contract_name: str, address: str) -> None:
        """Save deployed contract address."""
        deployments_dir = Path("deployments")
        deployments_dir.mkdir(exist_ok=True)

        deployments_file = deployments_dir / f"{self.network}.json"

        deployments = {}
        if deployments_file.exists():
            with open(deployments_file) as f:
                deployments = json.load(f)

        deployments[contract_name] = address

        with open(deployments_file, 'w') as f:
            json.dump(deployments, f, indent=2)

    def deploy_license_contract(
        self,
        deployer_address: str,
        private_key: str,
        registrar_address: Optional[str] = None
    ) -> str:
        """
        Deploy the RepoLicense contract.

        Requires contracts to be compiled first with `forge build` in contracts/.

        Args:
            deployer_address: Address deploying the contract
            private_key: Private key for signing
            registrar_address: Address of registrar (defaults to deployer)

        Returns:
            Deployed contract address

        Raises:
            ConnectionError: If not connected to blockchain
            FileNotFoundError: If contracts not compiled
        """
        if not self.w3.is_connected():
            raise ConnectionError("Not connected to blockchain")

        if not is_compiled():
            raise FileNotFoundError(
                "Contracts not compiled. Run 'forge build' in contracts/ directory first.\n"
                "Install Foundry: curl -L https://foundry.paradigm.xyz | bash && foundryup"
            )

        # Create contract instance
        self.license_contract = LicenseNFTContract(self.w3)

        # Deploy
        contract_address = self.license_contract.deploy(
            deployer_address=deployer_address,
            private_key=private_key,
            registrar_address=registrar_address
        )

        # Save deployment
        self.save_deployment("RepoLicense", contract_address)

        return contract_address

    def register_repo(
        self,
        repo_url: str,
        target_price: str,
        floor_price: str,
        developer_address: str,
        private_key: str
    ) -> str:
        """
        Register a repository on-chain.

        Args:
            repo_url: Repository URL
            target_price: Target price (e.g., "0.05 ETH")
            floor_price: Floor price (e.g., "0.02 ETH")
            developer_address: Developer's Ethereum address
            private_key: Private key for signing

        Returns:
            Transaction hash
        """
        if not self.license_contract:
            raise ValueError("License contract not initialized")

        # Parse prices to wei
        target_wei = self._parse_price_to_wei(target_price)
        floor_wei = self._parse_price_to_wei(floor_price)

        # Register on-chain
        tx_hash = self.license_contract.register_repository(
            repo_url,
            target_wei,
            floor_wei,
            developer_address,
            private_key
        )

        return tx_hash

    def issue_license(
        self,
        buyer_address: str,
        repo_url: str,
        license_params: Dict[str, Any],
        payment: str,
        buyer_private_key: str
    ) -> str:
        """
        Issue a license NFT.

        Args:
            buyer_address: Buyer's Ethereum address
            repo_url: Repository URL
            license_params: License parameters dict
            payment: Payment amount (e.g., "0.05 ETH")
            buyer_private_key: Buyer's private key

        Returns:
            Transaction hash
        """
        if not self.license_contract:
            raise ValueError("License contract not initialized")

        payment_wei = self._parse_price_to_wei(payment)

        tx_hash = self.license_contract.issue_license(
            buyer_address,
            repo_url,
            license_params.get("type", 0),
            license_params.get("duration", 0),
            license_params.get("max_seats", 0),
            license_params.get("allow_forks", False),
            license_params.get("royalty_basis_points", 0),
            license_params.get("token_uri", ""),
            payment_wei,
            buyer_private_key
        )

        return tx_hash

    def verify_license(self, token_id: int) -> bool:
        """
        Verify if a license is valid.

        Args:
            token_id: License token ID

        Returns:
            True if valid
        """
        if not self.license_contract:
            raise ValueError("License contract not initialized")

        return self.license_contract.is_license_valid(token_id)

    @staticmethod
    def _parse_price_to_wei(price_str: str) -> int:
        """
        Parse price string to wei.

        Args:
            price_str: Price string like "0.05 ETH"

        Returns:
            Price in wei
        """
        parts = price_str.strip().split()
        amount = float(parts[0])
        currency = parts[1].upper() if len(parts) > 1 else "ETH"

        if currency in ["ETH", "ETHER"]:
            return Web3.to_wei(amount, 'ether')

        # Default to wei
        return int(amount)

    def get_network_info(self) -> Dict[str, Any]:
        """
        Get information about the connected network.

        Returns:
            Dictionary with network information
        """
        return {
            "network": self.network,
            "connected": self.w3.is_connected(),
            "chain_id": self.w3.eth.chain_id if self.w3.is_connected() else None,
            "block_number": self.w3.eth.block_number if self.w3.is_connected() else None,
            "contracts": {
                "RepoLicense": self.license_contract.contract.address if self.license_contract and self.license_contract.contract else None
            }
        }
