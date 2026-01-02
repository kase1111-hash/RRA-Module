# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Contract Manager for handling smart contract operations.

Manages contract deployment, configuration, and lifecycle.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
import json
from web3 import Web3
from web3.exceptions import ContractLogicError

from rra.contracts.license_nft import LicenseNFTContract
from rra.contracts.artifacts import is_compiled, available_contracts
from rra.exceptions import (
    ConfigurationError,
    ContractNotFoundError,
    ContractDeploymentError,
    ContractCallError,
    ValidationError,
    wrap_exception,
)

logger = logging.getLogger(__name__)


class ContractManager:
    """
    Manages smart contract deployment and configuration.

    Provides high-level interface for contract operations across
    different networks.
    """

    def __init__(self, network: str = "mainnet", provider_url: Optional[str] = None):
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
            available = ", ".join(providers.keys())
            raise ConfigurationError(
                message=f"Unknown network '{network}'. Available networks: {available}",
                config_key="network",
                expected=f"one of: {available}",
                actual=network,
            )

        logger.debug(f"Initializing Web3 provider for network '{network}'")
        return Web3(Web3.HTTPProvider(providers[network]))

    def _load_deployments(self) -> None:
        """Load deployed contract addresses from file."""
        deployments_file = Path(f"deployments/{self.network}.json")

        if not deployments_file.exists():
            logger.debug(f"No deployments file found at {deployments_file}")
            return

        try:
            with open(deployments_file) as f:
                deployments = json.load(f)
                logger.info(
                    f"Loaded deployments for network '{self.network}': "
                    f"{list(deployments.keys())}"
                )

                if "RepoLicense" in deployments:
                    address = deployments["RepoLicense"]
                    logger.debug(f"Initializing RepoLicense contract at {address}")
                    self.license_contract = LicenseNFTContract(self.w3, contract_address=address)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse deployments file {deployments_file}: {e}")
            raise ConfigurationError(
                message=f"Invalid JSON in deployments file: {deployments_file}",
                config_key="deployments_file",
                cause=e,
            )
        except Exception as e:
            logger.error(f"Failed to load deployments: {e}")
            raise wrap_exception(
                e,
                ConfigurationError,
                message=f"Failed to load contract deployments for network '{self.network}'",
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

        with open(deployments_file, "w") as f:
            json.dump(deployments, f, indent=2)

    def deploy_license_contract(
        self, deployer_address: str, private_key: str, registrar_address: Optional[str] = None
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
            ConfigurationError: If not connected to blockchain
            ContractNotFoundError: If contracts not compiled
            ContractDeploymentError: If deployment fails
        """
        # Validate inputs
        if not deployer_address:
            raise ValidationError(
                message="Deployer address is required",
                field="deployer_address",
                constraint="non-empty Ethereum address",
            )

        if not private_key:
            raise ValidationError(
                message="Private key is required for signing deployment transaction",
                field="private_key",
                constraint="non-empty hex string",
            )

        # Check connection
        if not self.w3.is_connected():
            raise ConfigurationError(
                message=f"Not connected to blockchain network '{self.network}'. "
                f"Check your provider URL and network connectivity.",
                config_key="provider_url",
            )

        # Check contracts are compiled
        if not is_compiled():
            available_contracts()
            raise ContractNotFoundError(
                contract_name="RepoLicense",
                search_paths=[
                    "contracts/out/RepoLicense.sol/",
                    "src/rra/contracts/artifacts/",
                ],
            )

        logger.info(
            f"Deploying RepoLicense contract on network '{self.network}' "
            f"from deployer {deployer_address[:10]}..."
        )

        try:
            # Create contract instance
            self.license_contract = LicenseNFTContract(self.w3)

            # Deploy
            contract_address = self.license_contract.deploy(
                deployer_address=deployer_address,
                private_key=private_key,
                registrar_address=registrar_address,
            )

            logger.info(f"RepoLicense deployed successfully at {contract_address}")

            # Save deployment
            self.save_deployment("RepoLicense", contract_address)

            return contract_address

        except Exception as e:
            logger.error(f"Contract deployment failed: {e}")
            raise ContractDeploymentError(
                contract_name="RepoLicense",
                reason=str(e),
                cause=e,
            )

    def register_repo(
        self,
        repo_url: str,
        target_price: str,
        floor_price: str,
        developer_address: str,
        private_key: str,
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

        Raises:
            ConfigurationError: If license contract not initialized
            ValidationError: If inputs are invalid
            ContractCallError: If registration fails
        """
        if not self.license_contract:
            raise ConfigurationError(
                message="License contract not initialized. Deploy or load contract first.",
                config_key="license_contract",
                expected="initialized LicenseNFTContract",
                actual="None",
            )

        # Validate inputs
        if not repo_url:
            raise ValidationError(
                message="Repository URL is required",
                field="repo_url",
                constraint="non-empty URL string",
            )

        if not developer_address:
            raise ValidationError(
                message="Developer address is required",
                field="developer_address",
                constraint="valid Ethereum address",
            )

        # Parse prices to wei with validation
        try:
            target_wei = self._parse_price_to_wei(target_price)
            floor_wei = self._parse_price_to_wei(floor_price)
        except (ValueError, IndexError) as e:
            raise ValidationError(
                message=f"Invalid price format: {e}",
                field="target_price/floor_price",
                value=f"{target_price}, {floor_price}",
                constraint="format: '<amount> <unit>' (e.g., '0.05 ETH')",
                cause=e,
            )

        if floor_wei > target_wei:
            raise ValidationError(
                message="Floor price cannot exceed target price",
                field="floor_price",
                value=floor_price,
                constraint=f"must be <= target_price ({target_price})",
            )

        logger.info(
            f"Registering repository: {repo_url} " f"(target: {target_price}, floor: {floor_price})"
        )

        try:
            tx_hash = self.license_contract.register_repository(
                repo_url, target_wei, floor_wei, developer_address, private_key
            )
            logger.info(f"Repository registered successfully. TX: {tx_hash}")
            return tx_hash

        except ContractLogicError as e:
            raise ContractCallError(
                contract_name="RepoLicense",
                function_name="registerRepository",
                reason=f"Contract reverted: {e}",
                args=(repo_url, target_wei, floor_wei),
                cause=e,
            )
        except Exception as e:
            logger.error(f"Failed to register repository: {e}")
            raise ContractCallError(
                contract_name="RepoLicense",
                function_name="registerRepository",
                reason=str(e),
                args=(repo_url, target_wei, floor_wei),
                cause=e,
            )

    def issue_license(
        self,
        buyer_address: str,
        repo_url: str,
        license_params: Dict[str, Any],
        payment: str,
        buyer_private_key: str,
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

        Raises:
            ConfigurationError: If license contract not initialized
            ValidationError: If inputs are invalid
            ContractCallError: If issuance fails
        """
        if not self.license_contract:
            raise ConfigurationError(
                message="License contract not initialized. Deploy or load contract first.",
                config_key="license_contract",
                expected="initialized LicenseNFTContract",
                actual="None",
            )

        # Validate inputs
        if not buyer_address:
            raise ValidationError(
                message="Buyer address is required",
                field="buyer_address",
                constraint="valid Ethereum address",
            )

        if not repo_url:
            raise ValidationError(
                message="Repository URL is required",
                field="repo_url",
                constraint="non-empty URL string",
            )

        try:
            payment_wei = self._parse_price_to_wei(payment)
        except (ValueError, IndexError) as e:
            raise ValidationError(
                message=f"Invalid payment format: {e}",
                field="payment",
                value=payment,
                constraint="format: '<amount> <unit>' (e.g., '0.05 ETH')",
                cause=e,
            )

        logger.info(
            f"Issuing license for repo '{repo_url}' to buyer {buyer_address[:10]}... "
            f"(payment: {payment})"
        )

        try:
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
                buyer_private_key,
            )
            logger.info(f"License issued successfully. TX: {tx_hash}")
            return tx_hash

        except ContractLogicError as e:
            raise ContractCallError(
                contract_name="RepoLicense",
                function_name="issueLicense",
                reason=f"Contract reverted: {e}",
                kwargs={"buyer": buyer_address, "repo_url": repo_url, "payment_wei": payment_wei},
                cause=e,
            )
        except Exception as e:
            logger.error(f"Failed to issue license: {e}")
            raise ContractCallError(
                contract_name="RepoLicense",
                function_name="issueLicense",
                reason=str(e),
                cause=e,
            )

    def verify_license(self, token_id: int) -> bool:
        """
        Verify if a license is valid.

        Args:
            token_id: License token ID

        Returns:
            True if valid

        Raises:
            ConfigurationError: If license contract not initialized
            ValidationError: If token_id is invalid
            ContractCallError: If verification fails
        """
        if not self.license_contract:
            raise ConfigurationError(
                message="License contract not initialized. Deploy or load contract first.",
                config_key="license_contract",
                expected="initialized LicenseNFTContract",
                actual="None",
            )

        if token_id < 0:
            raise ValidationError(
                message="Token ID must be a non-negative integer",
                field="token_id",
                value=token_id,
                constraint="token_id >= 0",
            )

        try:
            is_valid = self.license_contract.is_license_valid(token_id)
            logger.debug(f"License verification for token {token_id}: {is_valid}")
            return is_valid

        except ContractLogicError as e:
            # Token doesn't exist or other contract error
            logger.warning(f"License verification failed for token {token_id}: {e}")
            raise ContractCallError(
                contract_name="RepoLicense",
                function_name="isLicenseValid",
                reason=f"Contract error: {e}",
                args=(token_id,),
                cause=e,
            )
        except Exception as e:
            logger.error(f"Unexpected error verifying license: {e}")
            raise ContractCallError(
                contract_name="RepoLicense",
                function_name="isLicenseValid",
                reason=str(e),
                args=(token_id,),
                cause=e,
            )

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
            return Web3.to_wei(amount, "ether")

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
                "RepoLicense": (
                    self.license_contract.contract.address
                    if self.license_contract and self.license_contract.contract
                    else None
                )
            },
        }
