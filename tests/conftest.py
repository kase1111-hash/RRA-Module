# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Pytest configuration and shared fixtures for RRA tests.
"""

import os
import hashlib
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock, Mock, patch
from dataclasses import dataclass, field

import pytest


# =============================================================================
# Blockchain Mock Infrastructure
# =============================================================================


@dataclass
class MockTransactionReceipt:
    """Mock Ethereum transaction receipt."""

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
    """Mock contract function that can be called or built into transaction."""

    return_value: Any = None
    _call_count: int = 0

    def call(self, *args, **kwargs):
        """Simulate a view/pure function call."""
        self._call_count += 1
        return self.return_value

    def build_transaction(self, tx_params: Dict) -> Dict:
        """Build a transaction dict for state-changing function."""
        self._call_count += 1
        return {
            "to": "0x" + "1" * 40,
            "data": "0x" + os.urandom(32).hex(),
            "gas": tx_params.get("gas", 100000),
            "gasPrice": tx_params.get("gasPrice", 20_000_000_000),
            "nonce": tx_params.get("nonce", 0),
            "value": tx_params.get("value", 0),
        }


class MockContract:
    """Mock Web3 contract object."""

    def __init__(self, address: str = None, abi: list = None):
        self.address = address or "0x" + "1" * 40
        self.abi = abi or []
        self._function_returns: Dict[str, Any] = {}

    def set_function_return(self, name: str, value: Any):
        """Set the return value for a specific function."""
        self._function_returns[name] = value

    @property
    def functions(self):
        """Return a mock functions object that creates MockContractFunction on access."""

        class FunctionsProxy:
            def __init__(proxy_self, contract):
                proxy_self._contract = contract

            def __getattr__(proxy_self, name):
                def function_factory(*args, **kwargs):
                    return_val = proxy_self._contract._function_returns.get(name)
                    return MockContractFunction(return_value=return_val)

                return function_factory

        return FunctionsProxy(self)

    @property
    def constructor(self):
        """Return mock constructor."""

        def constructor_factory(*args, **kwargs):
            return MockContractFunction()

        return constructor_factory


class MockWeb3:
    """
    Comprehensive mock for Web3 instance.

    Simulates blockchain interactions for testing without real network.
    """

    def __init__(
        self,
        chain_id: int = 1,
        block_number: int = 12345678,
        gas_price: int = 20_000_000_000,
        connected: bool = True,
    ):
        self._chain_id = chain_id
        self._block_number = block_number
        self._gas_price = gas_price
        self._connected = connected
        self._nonces: Dict[str, int] = {}
        self._contracts: Dict[str, MockContract] = {}
        self._transactions: Dict[bytes, MockTransactionReceipt] = {}
        self._deployed_contracts: List[str] = []
        self._next_contract_address = 1

        # Setup eth module
        self.eth = self._create_eth_module()

    def _create_eth_module(self):
        """Create mock eth module."""
        eth = MagicMock()
        eth.chain_id = self._chain_id
        eth.block_number = self._block_number
        eth.gas_price = self._gas_price

        # get_transaction_count
        def get_nonce(address, *args):
            addr = address.lower()
            return self._nonces.get(addr, 0)

        eth.get_transaction_count = get_nonce

        # contract factory
        def create_contract(address=None, abi=None, bytecode=None):
            if address:
                addr = address.lower()
                if addr not in self._contracts:
                    self._contracts[addr] = MockContract(address, abi)
                return self._contracts[addr]
            else:
                # Deployment - return a contract with constructor
                mock = MockContract(abi=abi)
                return mock

        eth.contract = create_contract

        # Transaction signing
        def sign_transaction(tx_dict, private_key):
            signed = MagicMock()
            signed.raw_transaction = os.urandom(100)
            signed.hash = os.urandom(32)
            return signed

        eth.account = MagicMock()
        eth.account.sign_transaction = sign_transaction

        # Send raw transaction
        def send_raw_transaction(raw_tx):
            tx_hash = os.urandom(32)
            # Create a pending receipt
            contract_addr = None
            # Check if this looks like a deployment (no 'to' in recent txs)
            contract_addr = f"0x{self._next_contract_address:040x}"
            self._next_contract_address += 1
            self._deployed_contracts.append(contract_addr)

            self._transactions[tx_hash] = MockTransactionReceipt(
                status=1,
                transactionHash=tx_hash,
                contractAddress=contract_addr,
            )
            return tx_hash

        eth.send_raw_transaction = send_raw_transaction

        # Wait for receipt
        def wait_for_receipt(tx_hash, timeout=None):
            if tx_hash in self._transactions:
                return self._transactions[tx_hash]
            raise TimeoutError(f"Transaction {tx_hash.hex()} not found")

        eth.wait_for_transaction_receipt = wait_for_receipt

        # Get transaction
        def get_transaction(tx_hash):
            if tx_hash in self._transactions:
                return {"hash": tx_hash, "blockNumber": self._block_number}
            return None

        eth.get_transaction = get_transaction

        return eth

    def is_connected(self) -> bool:
        """Check if connected to blockchain."""
        return self._connected

    @staticmethod
    def to_checksum_address(address: str) -> str:
        """Convert address to checksum format."""
        # Simple mock - just return the address with proper formatting
        addr = address.lower().replace("0x", "")
        return "0x" + addr

    @staticmethod
    def to_wei(amount: float, unit: str = "ether") -> int:
        """Convert to wei."""
        multipliers = {
            "ether": 10**18,
            "gwei": 10**9,
            "wei": 1,
        }
        return int(amount * multipliers.get(unit, 10**18))

    @staticmethod
    def from_wei(amount: int, unit: str = "ether") -> float:
        """Convert from wei."""
        divisors = {
            "ether": 10**18,
            "gwei": 10**9,
            "wei": 1,
        }
        return amount / divisors.get(unit, 10**18)

    def set_contract_function_return(
        self, contract_address: str, function_name: str, return_value: Any
    ):
        """Configure return value for a contract function."""
        addr = contract_address.lower()
        if addr not in self._contracts:
            self._contracts[addr] = MockContract(contract_address)
        self._contracts[addr].set_function_return(function_name, return_value)


class MockHTTPProvider:
    """Mock Web3 HTTP Provider."""

    def __init__(self, url: str):
        self.endpoint_uri = url


def pytest_configure(config):
    """
    Configure pytest environment before tests run.

    Sets up development mode for API authentication.
    """
    # Enable development mode for API tests
    # This allows any non-empty API key to pass authentication
    os.environ["RRA_DEV_MODE"] = "true"

    # Set a default API key for tests
    os.environ["RRA_API_KEY"] = "test-api-key-for-testing"


@pytest.fixture(scope="session")
def api_headers():
    """Provide standard API headers for authenticated requests."""
    return {"X-API-Key": os.environ.get("RRA_API_KEY", "test-api-key-for-testing")}


@pytest.fixture
def authenticated_client():
    """
    Create an authenticated test client wrapper.

    Returns a TestClient that automatically includes the X-API-Key header.
    """
    from fastapi.testclient import TestClient
    from rra.api.server import app

    class AuthenticatedTestClient(TestClient):
        """TestClient wrapper that adds authentication headers."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._auth_headers = {
                "X-API-Key": os.environ.get("RRA_API_KEY", "test-api-key-for-testing")
            }

        def request(self, method, url, **kwargs):
            headers = kwargs.pop("headers", {})
            headers.update(self._auth_headers)
            return super().request(method, url, headers=headers, **kwargs)

    return AuthenticatedTestClient(app)


# =============================================================================
# Blockchain Test Fixtures
# =============================================================================


@pytest.fixture
def mock_web3():
    """Provide a mock Web3 instance for blockchain tests."""
    return MockWeb3(chain_id=1, connected=True)


@pytest.fixture
def mock_web3_sepolia():
    """Provide a mock Web3 instance for Sepolia testnet."""
    return MockWeb3(chain_id=11155111, connected=True)


@pytest.fixture
def mock_web3_disconnected():
    """Provide a disconnected mock Web3 instance."""
    return MockWeb3(chain_id=1, connected=False)


@pytest.fixture
def test_accounts():
    """Provide test Ethereum accounts with private keys."""
    # Deterministic test accounts (DO NOT use these in production)
    return {
        "deployer": {
            "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            "private_key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
        },
        "developer": {
            "address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
            "private_key": "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
        },
        "buyer": {
            "address": "0x90F79bf6EB2c4f870365E785982E1f101E93b906",
            "private_key": "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
        },
        "registrar": {
            "address": "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
            "private_key": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
        },
    }


@pytest.fixture
def mock_contract_artifact():
    """Provide a mock contract artifact."""
    return {
        "abi": [
            {
                "inputs": [{"name": "_registrar", "type": "address"}],
                "stateMutability": "nonpayable",
                "type": "constructor",
            },
            {
                "inputs": [],
                "name": "registrar",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "isLicenseValid",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"name": "repoUrl", "type": "string"},
                    {"name": "targetPrice", "type": "uint256"},
                    {"name": "floorPrice", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                    {"name": "signature", "type": "bytes"},
                ],
                "name": "registerRepository",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ],
        "bytecode": "0x608060405234801561001057600080fd5b50",
    }


@pytest.fixture
def sample_repo_data():
    """Provide sample repository data for testing."""
    return {
        "url": "https://github.com/test-org/test-repo",
        "target_price": "0.05 ETH",
        "floor_price": "0.02 ETH",
        "target_price_wei": 50000000000000000,  # 0.05 ETH in wei
        "floor_price_wei": 20000000000000000,  # 0.02 ETH in wei
        "description": "A test repository for integration testing",
        "license_model": "per_seat",
    }


@pytest.fixture
def mock_ipfs_client():
    """Provide a mock IPFS client."""

    class MockIPFS:
        def __init__(self):
            self._storage: Dict[str, bytes] = {}

        def add(self, content: bytes) -> str:
            """Add content to mock IPFS."""
            content_hash = hashlib.sha256(content).hexdigest()[:46]
            ipfs_hash = f"Qm{content_hash}"
            self._storage[ipfs_hash] = content
            return ipfs_hash

        def cat(self, ipfs_hash: str) -> bytes:
            """Retrieve content from mock IPFS."""
            if ipfs_hash not in self._storage:
                raise FileNotFoundError(f"IPFS hash not found: {ipfs_hash}")
            return self._storage[ipfs_hash]

        def pin(self, ipfs_hash: str) -> bool:
            """Pin content in mock IPFS."""
            return ipfs_hash in self._storage

    return MockIPFS()
