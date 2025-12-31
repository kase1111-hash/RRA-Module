# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
License NFT contract interaction module.

Provides Python interface for interacting with the RepoLicense smart contract.
"""

from typing import Dict, Any, Optional
from web3 import Web3
from web3.exceptions import ContractLogicError

from rra.contracts.artifacts import load_contract, ContractArtifact


class LicenseNFTContract:
    """
    Interface for RepoLicense smart contract.

    Handles deployment and interaction with the licensing NFT contract.
    """

    CONTRACT_NAME = "RepoLicense"

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
            contract_abi: Contract ABI (if not using compiled artifact)
        """
        self.w3 = web3
        self._artifact: Optional[ContractArtifact] = None

        # Load ABI from compiled artifact if not provided
        if contract_abi is None:
            try:
                self._artifact = load_contract(self.CONTRACT_NAME)
                contract_abi = self._artifact.abi
            except FileNotFoundError:
                # Fall back to minimal ABI for read-only operations
                contract_abi = self._get_minimal_abi()

        self.abi = contract_abi

        if contract_address:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=self.abi
            )
        else:
            self.contract = None

    def deploy(
        self,
        deployer_address: str,
        private_key: str,
        registrar_address: Optional[str] = None,
        gas_limit: int = 5000000,
        wait_for_receipt: bool = True
    ) -> str:
        """
        Deploy the RepoLicense contract.

        Args:
            deployer_address: Address deploying the contract
            private_key: Private key for signing transaction
            registrar_address: Address of the registrar (defaults to deployer)
            gas_limit: Gas limit for deployment transaction
            wait_for_receipt: Whether to wait for transaction receipt

        Returns:
            Deployed contract address

        Raises:
            FileNotFoundError: If contract artifacts not compiled
            ValueError: If deployment fails
        """
        # Load artifact if not already loaded
        if self._artifact is None:
            self._artifact = load_contract(self.CONTRACT_NAME)

        if not self._artifact.has_bytecode:
            raise ValueError(
                f"No bytecode available for {self.CONTRACT_NAME}. "
                "Run 'forge build' in contracts/ directory."
            )

        # Use deployer as registrar if not specified
        if registrar_address is None:
            registrar_address = deployer_address

        deployer_address = Web3.to_checksum_address(deployer_address)
        registrar_address = Web3.to_checksum_address(registrar_address)

        # Create contract factory
        contract_factory = self.w3.eth.contract(
            abi=self._artifact.abi,
            bytecode=self._artifact.bytecode
        )

        # Build deployment transaction
        # Constructor: constructor(address _registrar)
        nonce = self.w3.eth.get_transaction_count(deployer_address)

        deploy_txn = contract_factory.constructor(registrar_address).build_transaction({
            'from': deployer_address,
            'nonce': nonce,
            'gas': gas_limit,
            'gasPrice': self.w3.eth.gas_price,
        })

        # Sign and send transaction
        signed_txn = self.w3.eth.account.sign_transaction(deploy_txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        if wait_for_receipt:
            # Wait for deployment
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            if tx_receipt['status'] != 1:
                raise ValueError(f"Contract deployment failed: {tx_hash.hex()}")

            contract_address = tx_receipt['contractAddress']

            # Initialize contract instance
            self.contract = self.w3.eth.contract(
                address=contract_address,
                abi=self._artifact.abi
            )

            return contract_address
        else:
            return tx_hash.hex()

    def register_repository(
        self,
        repo_url: str,
        target_price_wei: int,
        floor_price_wei: int,
        nonce: bytes,
        signature: bytes,
        developer_address: str,
        private_key: str,
        gas_limit: int = 300000
    ) -> str:
        """
        Register a repository for licensing.

        Args:
            repo_url: Repository URL
            target_price_wei: Target price in wei
            floor_price_wei: Floor price in wei
            nonce: Unique nonce for replay protection
            signature: Registrar signature authorizing registration
            developer_address: Developer's Ethereum address
            private_key: Private key for signing
            gas_limit: Gas limit for transaction

        Returns:
            Transaction hash
        """
        if not self.contract:
            raise ValueError("Contract not initialized. Deploy or set address first.")

        developer_address = Web3.to_checksum_address(developer_address)

        # Build transaction
        txn = self.contract.functions.registerRepository(
            repo_url,
            target_price_wei,
            floor_price_wei,
            nonce,
            signature
        ).build_transaction({
            'from': developer_address,
            'nonce': self.w3.eth.get_transaction_count(developer_address),
            'gas': gas_limit,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

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
        buyer_private_key: str,
        gas_limit: int = 500000
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
            gas_limit: Gas limit for transaction

        Returns:
            Transaction hash
        """
        if not self.contract:
            raise ValueError("Contract not initialized. Deploy or set address first.")

        licensee_address = Web3.to_checksum_address(licensee_address)

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
            'gas': gas_limit,
            'gasPrice': self.w3.eth.gas_price
        })

        # Sign and send
        signed_txn = self.w3.eth.account.sign_transaction(txn, buyer_private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

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

        try:
            return self.contract.functions.isLicenseValid(token_id).call()
        except ContractLogicError:
            return False

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

        # Get license struct from contract
        license_data = self.contract.functions.licenses(token_id).call()

        return {
            "license_type": license_data[0],
            "price": license_data[1],
            "expiration_date": license_data[2],
            "max_seats": license_data[3],
            "allow_forks": license_data[4],
            "royalty_basis_points": license_data[5],
            "repo_url": license_data[6],
            "licensee": license_data[7],
            "issued_at": license_data[8],
            "active": license_data[9],
        }

    def get_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Get repository registration details.

        Args:
            repo_url: Repository URL

        Returns:
            Dictionary with repository details
        """
        if not self.contract:
            raise ValueError("Contract not initialized")

        repo_data = self.contract.functions.repositories(repo_url).call()

        return {
            "url": repo_data[0],
            "developer": repo_data[1],
            "target_price": repo_data[2],
            "floor_price": repo_data[3],
            "active": repo_data[4],
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

        return self.contract.functions.userLicenses(
            Web3.to_checksum_address(user_address)
        ).call()

    def get_registrar(self) -> str:
        """Get the registrar address."""
        if not self.contract:
            raise ValueError("Contract not initialized")

        return self.contract.functions.registrar().call()

    @staticmethod
    def _get_minimal_abi() -> list:
        """
        Get minimal contract ABI for read-only operations.

        Used when compiled artifacts are not available.

        Returns:
            Minimal ABI list
        """
        return [
            {
                "inputs": [{"name": "_tokenId", "type": "uint256"}],
                "name": "isLicenseValid",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "", "type": "uint256"}],
                "name": "licenses",
                "outputs": [
                    {"name": "licenseType", "type": "uint8"},
                    {"name": "price", "type": "uint256"},
                    {"name": "expirationDate", "type": "uint256"},
                    {"name": "maxSeats", "type": "uint256"},
                    {"name": "allowForks", "type": "bool"},
                    {"name": "royaltyBasisPoints", "type": "uint16"},
                    {"name": "repoUrl", "type": "string"},
                    {"name": "licensee", "type": "address"},
                    {"name": "issuedAt", "type": "uint256"},
                    {"name": "active", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "", "type": "string"}],
                "name": "repositories",
                "outputs": [
                    {"name": "url", "type": "string"},
                    {"name": "developer", "type": "address"},
                    {"name": "targetPrice", "type": "uint256"},
                    {"name": "floorPrice", "type": "uint256"},
                    {"name": "active", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "registrar",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
        ]
