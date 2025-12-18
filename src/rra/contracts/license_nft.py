"""
License NFT contract interaction module.

Provides Python interface for interacting with the RepoLicense smart contract.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from web3 import Web3
from web3.contract import Contract


class LicenseNFTContract:
    """
    Interface for RepoLicense smart contract.

    Handles deployment and interaction with the licensing NFT contract.
    """

    def __init__(
        self,
        web3: Web3,
        contract_address: Optional[str] = None,
        contract_abi: Optional[list] = None
    ):
        """
        Initialize contract interface.

        Args:
            web3: Web3 instance connected to blockchain
            contract_address: Deployed contract address (if already deployed)
            contract_abi: Contract ABI (if not using default)
        """
        self.w3 = web3

        if contract_abi is None:
            # Load default ABI (simplified for this implementation)
            contract_abi = self._get_default_abi()

        self.abi = contract_abi

        if contract_address:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=self.abi
            )
        else:
            self.contract = None

    def deploy(self, deployer_address: str, private_key: str) -> str:
        """
        Deploy the RepoLicense contract.

        Args:
            deployer_address: Address deploying the contract
            private_key: Private key for signing transaction

        Returns:
            Deployed contract address
        """
        # In production, would compile Solidity and deploy
        # For now, this is a placeholder
        raise NotImplementedError("Contract deployment requires compilation step")

    def register_repository(
        self,
        repo_url: str,
        target_price_wei: int,
        floor_price_wei: int,
        developer_address: str,
        private_key: str
    ) -> str:
        """
        Register a repository for licensing.

        Args:
            repo_url: Repository URL
            target_price_wei: Target price in wei
            floor_price_wei: Floor price in wei
            developer_address: Developer's Ethereum address
            private_key: Private key for signing

        Returns:
            Transaction hash
        """
        if not self.contract:
            raise ValueError("Contract not initialized")

        # Build transaction
        txn = self.contract.functions.registerRepository(
            repo_url,
            target_price_wei,
            floor_price_wei
        ).build_transaction({
            'from': developer_address,
            'nonce': self.w3.eth.get_transaction_count(developer_address),
            'gas': 2000000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return tx_hash.hex()

    def issue_license(
        self,
        licensee_address: str,
        repo_url: str,
        license_type: int,
        duration: int,
        max_seats: int,
        allow_forks: bool,
        royalty_basis_points: int,
        token_uri: str,
        payment_wei: int,
        buyer_private_key: str
    ) -> str:
        """
        Issue a new license NFT.

        Args:
            licensee_address: Address receiving the license
            repo_url: Repository URL
            license_type: Type of license (0=PER_SEAT, 1=SUBSCRIPTION, etc.)
            duration: Duration in seconds (0 for perpetual)
            max_seats: Maximum seats (0 for unlimited)
            allow_forks: Whether forking is allowed
            royalty_basis_points: Royalty percentage in basis points (0-10000)
            token_uri: Token metadata URI
            payment_wei: Payment amount in wei
            buyer_private_key: Private key for signing transaction

        Returns:
            Transaction hash
        """
        if not self.contract:
            raise ValueError("Contract not initialized")

        # Build transaction
        txn = self.contract.functions.issueLicense(
            licensee_address,
            repo_url,
            license_type,
            duration,
            max_seats,
            allow_forks,
            royalty_basis_points,
            token_uri
        ).build_transaction({
            'from': licensee_address,
            'value': payment_wei,
            'nonce': self.w3.eth.get_transaction_count(licensee_address),
            'gas': 3000000,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, buyer_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return tx_hash.hex()

    def is_license_valid(self, token_id: int) -> bool:
        """
        Check if a license is valid.

        Args:
            token_id: License token ID

        Returns:
            True if license is valid and active
        """
        if not self.contract:
            raise ValueError("Contract not initialized")

        return self.contract.functions.isLicenseValid(token_id).call()

    def get_license_details(self, token_id: int) -> Dict[str, Any]:
        """
        Get details for a license.

        Args:
            token_id: License token ID

        Returns:
            Dictionary with license details
        """
        if not self.contract:
            raise ValueError("Contract not initialized")

        details = self.contract.functions.getLicenseDetails(token_id).call()

        return {
            "license_type": details[0],
            "price": details[1],
            "expiration_date": details[2],
            "max_seats": details[3],
            "allow_forks": details[4],
            "repo_url": details[5],
            "active": details[6],
            "valid": details[7],
        }

    def get_user_licenses(self, user_address: str) -> list[int]:
        """
        Get all license token IDs owned by a user.

        Args:
            user_address: User's Ethereum address

        Returns:
            List of token IDs
        """
        if not self.contract:
            raise ValueError("Contract not initialized")

        return self.contract.functions.getLicensesByOwner(
            Web3.to_checksum_address(user_address)
        ).call()

    @staticmethod
    def _get_default_abi() -> list:
        """
        Get default contract ABI.

        Returns:
            Contract ABI list
        """
        # Simplified ABI for key functions
        # In production, would load from compiled contract
        return [
            {
                "inputs": [
                    {"name": "_repoUrl", "type": "string"},
                    {"name": "_targetPrice", "type": "uint256"},
                    {"name": "_floorPrice", "type": "uint256"}
                ],
                "name": "registerRepository",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_tokenId", "type": "uint256"}
                ],
                "name": "isLicenseValid",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            },
        ]
