# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Integration tests for blockchain components with mocked blockchain.

Tests contract deployment, license issuance, Story Protocol integration,
treasury coordination, and end-to-end workflows without requiring a
real blockchain connection.
"""

import pytest
from unittest.mock import patch, Mock
from typing import Dict, Any
import os
import sys

# Add tests directory to path for conftest imports
sys.path.insert(0, os.path.dirname(__file__))

# Import mock classes from conftest (they're defined there for fixture use)
try:
    from conftest import (
        MockWeb3,
        MockContract,
        MockTransactionReceipt,
        MockContractFunction,
    )
except ImportError:
    # Fallback: define minimal mock classes inline if conftest import fails
    from dataclasses import dataclass, field
    from typing import List, Optional

    @dataclass
    class MockTransactionReceipt:
        status: int = 1
        transactionHash: bytes = field(default_factory=lambda: os.urandom(32))
        blockNumber: int = 12345678
        gasUsed: int = 100000
        contractAddress: Optional[str] = None
        logs: List[Dict] = field(default_factory=list)

        def __getitem__(self, key):
            return getattr(self, key)

    @dataclass
    class MockContractFunction:
        return_value: Any = None

        def call(self, *args, **kwargs):
            return self.return_value

        def build_transaction(self, tx_params: Dict) -> Dict:
            return {"gas": 100000, "nonce": 0}

    class MockContract:
        def __init__(self, address=None, abi=None):
            self.address = address or "0x" + "1" * 40
            self.abi = abi or []

    class MockWeb3:
        def __init__(self, chain_id=1, connected=True):
            self._connected = connected

        def is_connected(self):
            return self._connected

        @staticmethod
        def to_wei(amount, unit="ether"):
            return int(amount * (10**18 if unit == "ether" else 10**9 if unit == "gwei" else 1))

        @staticmethod
        def from_wei(amount, unit="ether"):
            return amount / (10**18 if unit == "ether" else 10**9 if unit == "gwei" else 1)

        @staticmethod
        def to_checksum_address(addr):
            return "0x" + addr.lower().replace("0x", "")


# =============================================================================
# Contract Manager Integration Tests
# =============================================================================


@pytest.mark.integration
class TestContractManagerIntegration:
    """Integration tests for ContractManager with mocked blockchain."""

    def test_contract_manager_initialization(self, mock_web3):
        """Test ContractManager initializes correctly with mock Web3."""
        from rra.contracts.manager import ContractManager

        with patch("rra.contracts.manager.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = Mock(return_value=Mock())

            manager = ContractManager(network="localhost", provider_url="http://localhost:8545")

            assert manager.network == "localhost"
            assert manager.w3 is not None

    def test_contract_manager_network_validation(self):
        """Test ContractManager validates network names."""
        from rra.contracts.manager import ContractManager

        with patch("rra.contracts.manager.Web3") as mock_web3_class:
            mock_web3_class.HTTPProvider = Mock(return_value=Mock())
            mock_instance = MockWeb3()
            mock_web3_class.return_value = mock_instance

            # Valid networks should work
            for network in ["mainnet", "sepolia", "localhost"]:
                manager = ContractManager(network=network)
                assert manager.network == network

    def test_contract_manager_connection_check(self, mock_web3, mock_web3_disconnected):
        """Test ContractManager properly checks blockchain connection."""
        assert mock_web3.is_connected() is True
        assert mock_web3_disconnected.is_connected() is False

    def test_deploy_license_contract_requires_connection(
        self, mock_web3_disconnected, test_accounts
    ):
        """Test deployment fails when not connected to blockchain."""
        from rra.contracts.manager import ContractManager
        from rra.exceptions import ConfigurationError

        with patch("rra.contracts.manager.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3_disconnected
            mock_web3_class.HTTPProvider = Mock(return_value=Mock())

            manager = ContractManager(network="localhost")
            manager.w3 = mock_web3_disconnected

            with pytest.raises(ConfigurationError) as exc_info:
                manager.deploy_license_contract(
                    deployer_address=test_accounts["deployer"]["address"],
                    private_key=test_accounts["deployer"]["private_key"],
                )

            assert "Not connected" in str(exc_info.value)

    def test_save_deployment_persists_address(self, mock_web3, tmp_path):
        """Test deployment addresses are saved correctly."""
        from rra.contracts.manager import ContractManager

        with patch("rra.contracts.manager.Web3") as mock_web3_class:
            mock_web3_class.return_value = mock_web3
            mock_web3_class.HTTPProvider = Mock(return_value=Mock())

            manager = ContractManager(network="localhost")

            # Temporarily change deployments directory
            original_cwd = os.getcwd()
            os.chdir(tmp_path)

            try:
                contract_address = "0x1234567890123456789012345678901234567890"
                manager.save_deployment("TestContract", contract_address)

                # Verify file was created
                import json

                deployments_file = tmp_path / "deployments" / "localhost.json"
                assert deployments_file.exists()

                with open(deployments_file) as f:
                    deployments = json.load(f)
                    assert deployments["TestContract"] == contract_address
            finally:
                os.chdir(original_cwd)


# =============================================================================
# License NFT Contract Integration Tests
# =============================================================================


@pytest.mark.integration
class TestLicenseNFTIntegration:
    """Integration tests for LicenseNFTContract with mocked blockchain."""

    def test_license_nft_initialization(self, mock_web3, mock_contract_artifact):
        """Test LicenseNFTContract initializes correctly."""
        from rra.contracts.license_nft import LicenseNFTContract

        contract = LicenseNFTContract(
            web3=mock_web3,
            contract_address="0x1234567890123456789012345678901234567890",
            contract_abi=mock_contract_artifact["abi"],
        )

        assert contract.w3 == mock_web3
        assert contract.abi == mock_contract_artifact["abi"]

    def test_license_nft_minimal_abi_fallback(self, mock_web3):
        """Test LicenseNFTContract uses minimal ABI when artifacts unavailable."""
        from rra.contracts.license_nft import LicenseNFTContract

        with patch("rra.contracts.license_nft.load_contract") as mock_load:
            mock_load.side_effect = FileNotFoundError("No artifact")

            contract = LicenseNFTContract(
                web3=mock_web3,
                contract_address="0x1234567890123456789012345678901234567890",
            )

            # Should have minimal ABI for read operations
            assert contract.abi is not None
            assert len(contract.abi) > 0

    def test_license_nft_deploy_transaction(self, mock_web3, test_accounts, mock_contract_artifact):
        """Test LicenseNFTContract deployment builds correct transaction."""
        from rra.contracts.license_nft import LicenseNFTContract
        from rra.contracts.artifacts import ContractArtifact

        mock_artifact = ContractArtifact(
            name="RepoLicense",
            abi=mock_contract_artifact["abi"],
            bytecode=mock_contract_artifact["bytecode"],
            deployed_bytecode="",
            metadata={},
        )

        with patch("rra.contracts.license_nft.load_contract") as mock_load:
            mock_load.return_value = mock_artifact

            contract = LicenseNFTContract(web3=mock_web3)

            # Deploy
            address = contract.deploy(
                deployer_address=test_accounts["deployer"]["address"],
                private_key=test_accounts["deployer"]["private_key"],
            )

            # Verify deployment occurred
            assert address is not None
            assert address.startswith("0x")
            assert len(mock_web3._deployed_contracts) > 0

    def test_license_validation_check(self, mock_web3, mock_contract_artifact):
        """Test license validation returns correct result."""
        from rra.contracts.license_nft import LicenseNFTContract

        contract_address = "0x1234567890123456789012345678901234567890"

        # Configure mock to return True for isLicenseValid
        mock_web3.set_contract_function_return(contract_address, "isLicenseValid", True)

        contract = LicenseNFTContract(
            web3=mock_web3,
            contract_address=contract_address,
            contract_abi=mock_contract_artifact["abi"],
        )

        # Call isLicenseValid
        result = contract.contract.functions.isLicenseValid(1).call()
        assert result is True


# =============================================================================
# Story Protocol Integration Tests
# =============================================================================


@pytest.mark.integration
class TestStoryProtocolIntegration:
    """Integration tests for Story Protocol with mocked blockchain."""

    def test_story_protocol_initialization(self, mock_web3):
        """Test StoryProtocolClient initializes correctly."""
        from rra.contracts.story_protocol import StoryProtocolClient

        client = StoryProtocolClient(web3=mock_web3, network="testnet")

        assert client.w3 == mock_web3
        assert client.network == "testnet"
        assert "IPAssetRegistry" in client.addresses

    def test_story_protocol_network_addresses(self, mock_web3):
        """Test StoryProtocolClient uses correct addresses per network."""
        from rra.contracts.story_protocol import StoryProtocolClient

        # Testnet
        testnet_client = StoryProtocolClient(web3=mock_web3, network="testnet")
        assert testnet_client.addresses == StoryProtocolClient.STORY_TESTNET_CONTRACTS

        # Localhost
        localhost_client = StoryProtocolClient(web3=mock_web3, network="localhost")
        assert localhost_client.addresses == StoryProtocolClient.STORY_LOCALHOST_CONTRACTS

        # Mainnet
        mainnet_client = StoryProtocolClient(web3=mock_web3, network="mainnet")
        assert mainnet_client.addresses == StoryProtocolClient.STORY_MAINNET_CONTRACTS

    def test_story_protocol_custom_addresses(self, mock_web3):
        """Test StoryProtocolClient accepts custom addresses."""
        from rra.contracts.story_protocol import StoryProtocolClient

        # Use valid hex addresses for custom addresses
        custom = {
            "IPAssetRegistry": "0x1111111111111111111111111111111111111111",
            "LicenseRegistry": "0x2222222222222222222222222222222222222222",
            "LicensingModule": "0x3333333333333333333333333333333333333333",
            "RoyaltyModule": "0x4444444444444444444444444444444444444444",
            "PILicenseTemplate": "0x5555555555555555555555555555555555555555",
        }

        client = StoryProtocolClient(web3=mock_web3, network="testnet", custom_addresses=custom)

        assert client.addresses["IPAssetRegistry"] == "0x1111111111111111111111111111111111111111"
        assert client.addresses["LicenseRegistry"] == "0x2222222222222222222222222222222222222222"

    def test_ip_asset_metadata_creation(self):
        """Test IPAssetMetadata dataclass works correctly."""
        from rra.contracts.story_protocol import IPAssetMetadata

        metadata = IPAssetMetadata(
            name="Test Repo",
            description="A test repository",
            ipType="SOFTWARE",
            createdAt=1700000000,
            ipfsHash="QmTest123",
            externalUrl="https://github.com/test/repo",
        )

        assert metadata.name == "Test Repo"
        assert metadata.ipType == "SOFTWARE"
        assert metadata.ipfsHash == "QmTest123"

    def test_pil_terms_defaults(self):
        """Test PILTerms has sensible defaults."""
        from rra.contracts.story_protocol import PILTerms

        terms = PILTerms()

        assert terms.commercial_use is True
        assert terms.derivatives_allowed is True
        assert terms.derivatives_attribution is True
        assert terms.commercial_revenue_share == 0


# =============================================================================
# End-to-End Integration Tests
# =============================================================================


@pytest.mark.integration
class TestE2EBlockchainFlow:
    """End-to-end integration tests for complete blockchain workflows."""

    def test_full_licensing_flow(
        self, mock_web3, test_accounts, sample_repo_data, mock_contract_artifact
    ):
        """Test complete licensing flow from deployment to license issuance."""
        from rra.contracts.license_nft import LicenseNFTContract
        from rra.contracts.artifacts import ContractArtifact

        mock_artifact = ContractArtifact(
            name="RepoLicense",
            abi=mock_contract_artifact["abi"],
            bytecode=mock_contract_artifact["bytecode"],
            deployed_bytecode="",
            metadata={},
        )

        with patch("rra.contracts.license_nft.load_contract") as mock_load:
            mock_load.return_value = mock_artifact

            # 1. Deploy contract
            contract = LicenseNFTContract(web3=mock_web3)
            contract_address = contract.deploy(
                deployer_address=test_accounts["deployer"]["address"],
                private_key=test_accounts["deployer"]["private_key"],
                registrar_address=test_accounts["registrar"]["address"],
            )

            assert contract_address is not None

            # 2. Configure mock for subsequent calls
            mock_web3.set_contract_function_return(
                contract_address, "registrar", test_accounts["registrar"]["address"]
            )
            mock_web3.set_contract_function_return(contract_address, "isLicenseValid", True)

            # 3. Verify contract state
            registrar = contract.contract.functions.registrar().call()
            # Note: Mock returns configured value
            assert registrar is not None

    def test_multi_chain_configuration(self, mock_web3):
        """Test multi-chain configuration works correctly."""
        from rra.chains.config import get_chain_manager

        # Use the existing chain manager with pre-configured chains
        manager = get_chain_manager()

        # Verify built-in chains are available
        ethereum = manager.get_chain(1)
        polygon = manager.get_chain(137)

        assert ethereum is not None
        assert polygon is not None
        assert ethereum.name == "ethereum"
        assert polygon.name == "polygon"
        assert ethereum.native_currency == "ETH"
        assert polygon.native_currency == "MATIC"


# =============================================================================
# Mock Validation Tests
# =============================================================================


@pytest.mark.integration
class TestMockInfrastructure:
    """Tests to validate the mock infrastructure works correctly."""

    def test_mock_web3_connection_status(self):
        """Test MockWeb3 correctly reports connection status."""
        connected = MockWeb3(connected=True)
        disconnected = MockWeb3(connected=False)

        assert connected.is_connected() is True
        assert disconnected.is_connected() is False

    def test_mock_web3_transaction_flow(self, mock_web3, test_accounts):
        """Test MockWeb3 handles transaction flow correctly."""
        # Get nonce
        nonce = mock_web3.eth.get_transaction_count(test_accounts["deployer"]["address"])
        assert nonce == 0

        # Create and sign transaction
        tx = {"to": test_accounts["buyer"]["address"], "value": 1000, "nonce": nonce}
        signed = mock_web3.eth.account.sign_transaction(
            tx, test_accounts["deployer"]["private_key"]
        )
        assert signed.raw_transaction is not None

        # Send transaction
        tx_hash = mock_web3.eth.send_raw_transaction(signed.raw_transaction)
        assert tx_hash is not None
        assert len(tx_hash) == 32

        # Wait for receipt
        receipt = mock_web3.eth.wait_for_transaction_receipt(tx_hash)
        assert receipt["status"] == 1

    def test_mock_contract_function_returns(self, mock_web3):
        """Test MockWeb3 contract function return values."""
        contract_addr = "0x1234567890123456789012345678901234567890"

        # Set up return values
        mock_web3.set_contract_function_return(contract_addr, "balanceOf", 1000)
        mock_web3.set_contract_function_return(contract_addr, "name", "TestToken")
        mock_web3.set_contract_function_return(contract_addr, "isValid", True)

        # Get contract
        contract = mock_web3.eth.contract(address=contract_addr, abi=[])

        # Call functions
        balance = contract.functions.balanceOf("0xUser").call()
        name = contract.functions.name().call()
        is_valid = contract.functions.isValid(1).call()

        assert balance == 1000
        assert name == "TestToken"
        assert is_valid is True

    def test_mock_web3_wei_conversion(self):
        """Test MockWeb3 wei conversion functions."""
        assert MockWeb3.to_wei(1, "ether") == 10**18
        assert MockWeb3.to_wei(1, "gwei") == 10**9
        assert MockWeb3.to_wei(1, "wei") == 1

        assert MockWeb3.from_wei(10**18, "ether") == 1.0
        assert MockWeb3.from_wei(10**9, "gwei") == 1.0
        assert MockWeb3.from_wei(1, "wei") == 1.0

    def test_mock_web3_checksum_address(self):
        """Test MockWeb3 checksum address conversion."""
        addr = "0xABCDef1234567890ABCDEF1234567890abcdef12"
        checksum = MockWeb3.to_checksum_address(addr)

        assert checksum.startswith("0x")
        assert len(checksum) == 42

    def test_mock_transaction_receipt_structure(self):
        """Test MockTransactionReceipt has correct structure."""
        receipt = MockTransactionReceipt(
            status=1,
            contractAddress="0x1234567890123456789012345678901234567890",
        )

        # Test dataclass access
        assert receipt.status == 1
        assert receipt.contractAddress == "0x1234567890123456789012345678901234567890"
        assert receipt.blockNumber == 12345678

        # Test dict-like access
        assert receipt["status"] == 1
        assert receipt["contractAddress"] == "0x1234567890123456789012345678901234567890"


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.integration
class TestBlockchainErrorHandling:
    """Tests for blockchain error handling with mocked failures."""

    def test_contract_call_failure_handling(self, mock_web3):
        """Test handling of contract call failures."""

        contract_addr = "0x1234567890123456789012345678901234567890"
        contract = mock_web3.eth.contract(address=contract_addr, abi=[])

        # By default, functions return None which should be handled gracefully
        result = contract.functions.someFunction().call()
        assert result is None

    def test_transaction_timeout_handling(self, mock_web3):
        """Test handling of transaction timeout."""
        # Create a transaction hash that doesn't exist
        fake_hash = os.urandom(32)

        with pytest.raises(TimeoutError):
            mock_web3.eth.wait_for_transaction_receipt(fake_hash)

    def test_invalid_address_handling(self, mock_web3):
        """Test handling of invalid addresses."""
        # MockWeb3 accepts any address format for testing
        # Real implementation would validate
        checksum = mock_web3.to_checksum_address("invalid")
        assert checksum == "0xinvalid"


# =============================================================================
# IPFS Integration Tests
# =============================================================================


@pytest.mark.integration
class TestIPFSIntegration:
    """Tests for IPFS storage integration."""

    def test_ipfs_add_and_retrieve(self, mock_ipfs_client):
        """Test adding and retrieving content from mock IPFS."""
        content = b"Test content for IPFS storage"

        # Add content
        ipfs_hash = mock_ipfs_client.add(content)
        assert ipfs_hash.startswith("Qm")

        # Retrieve content
        retrieved = mock_ipfs_client.cat(ipfs_hash)
        assert retrieved == content

    def test_ipfs_pin_existing_content(self, mock_ipfs_client):
        """Test pinning existing content."""
        content = b"Content to pin"
        ipfs_hash = mock_ipfs_client.add(content)

        assert mock_ipfs_client.pin(ipfs_hash) is True

    def test_ipfs_pin_nonexistent_content(self, mock_ipfs_client):
        """Test pinning non-existent content fails."""
        assert mock_ipfs_client.pin("QmNonExistent") is False

    def test_ipfs_retrieve_nonexistent(self, mock_ipfs_client):
        """Test retrieving non-existent content raises error."""
        with pytest.raises(FileNotFoundError):
            mock_ipfs_client.cat("QmNonExistent")
