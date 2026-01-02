# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Multi-chain Configuration for RRA Module.

Supports deployment across multiple EVM-compatible chains:
- Ethereum Mainnet
- Polygon (low gas fees)
- Arbitrum (L2 scaling)
- Base (Coinbase L2)
- Optimism (L2 scaling)
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class ChainId(Enum):
    """Supported chain IDs."""

    # Mainnets
    ETHEREUM_MAINNET = 1
    POLYGON_MAINNET = 137
    ARBITRUM_ONE = 42161
    BASE_MAINNET = 8453
    OPTIMISM_MAINNET = 10

    # Testnets (Sepolia-based - preferred for development)
    ETHEREUM_SEPOLIA = 11155111
    ARBITRUM_SEPOLIA = 421614
    OPTIMISM_SEPOLIA = 11155420
    BASE_SEPOLIA = 84532

    # Legacy testnets (deprecated but kept for compatibility)
    ETHEREUM_GOERLI = 5  # Deprecated
    POLYGON_MUMBAI = 80001  # Deprecated
    ARBITRUM_GOERLI = 421613  # Deprecated
    BASE_GOERLI = 84531  # Deprecated
    OPTIMISM_GOERLI = 420  # Deprecated


@dataclass
class ChainConfig:
    """Configuration for a blockchain network."""

    chain_id: int
    name: str
    display_name: str
    rpc_url: str
    explorer_url: str
    native_currency: str
    native_decimals: int = 18
    is_testnet: bool = False
    is_l2: bool = False
    avg_block_time: float = 12.0  # seconds

    # Contract addresses (deployed per chain)
    license_nft_address: Optional[str] = None
    license_manager_address: Optional[str] = None
    story_protocol_addresses: Dict[str, str] = field(default_factory=dict)
    superfluid_addresses: Dict[str, str] = field(default_factory=dict)

    # Gas settings
    max_gas_price_gwei: Optional[float] = None
    priority_fee_gwei: float = 1.5

    def get_explorer_tx_url(self, tx_hash: str) -> str:
        """Get explorer URL for a transaction."""
        return f"{self.explorer_url}/tx/{tx_hash}"

    def get_explorer_address_url(self, address: str) -> str:
        """Get explorer URL for an address."""
        return f"{self.explorer_url}/address/{address}"


# =============================================================================
# Chain Configurations
# =============================================================================

CHAIN_CONFIGS: Dict[int, ChainConfig] = {
    # Ethereum Mainnet
    ChainId.ETHEREUM_MAINNET.value: ChainConfig(
        chain_id=1,
        name="ethereum",
        display_name="Ethereum Mainnet",
        rpc_url=os.environ.get("ETH_RPC_URL", "https://eth.llamarpc.com"),
        explorer_url="https://etherscan.io",
        native_currency="ETH",
        avg_block_time=12.0,
        max_gas_price_gwei=100.0,
        story_protocol_addresses={
            "IPAssetRegistry": "0x1a9d0d28a0422F26D31Be72Edc6f13ea4371E11B",
            "LicenseRegistry": "0x4f4b1bf7135C7ff1462826CCA81B048e1E99a3d5",
            "RoyaltyModule": "0x3C27b2D7d30131D4b58C3584FD7c86e3358744de",
        },
    ),
    # Ethereum Sepolia (Testnet) - Primary development network
    ChainId.ETHEREUM_SEPOLIA.value: ChainConfig(
        chain_id=11155111,
        name="sepolia",
        display_name="Ethereum Sepolia",
        rpc_url=os.environ.get("SEPOLIA_RPC_URL", "https://rpc.sepolia.org"),
        explorer_url="https://sepolia.etherscan.io",
        native_currency="ETH",
        is_testnet=True,
        avg_block_time=12.0,
        # Mock addresses for development - deploy your own or use address(0xdead)
        license_nft_address="0x000000000000000000000000000000000000dEaD",
        license_manager_address="0x000000000000000000000000000000000000dEaD",
        story_protocol_addresses={
            # Deploy mocks using Foundry/Hardhat before testing
            "IPAssetRegistry": "0x000000000000000000000000000000000000dEaD",
            "LicenseRegistry": "0x000000000000000000000000000000000000dEaD",
            "RoyaltyModule": "0x000000000000000000000000000000000000dEaD",
            "PILFramework": "0x000000000000000000000000000000000000dEaD",
        },
    ),
    # Arbitrum Sepolia (Testnet) - L2 development
    ChainId.ARBITRUM_SEPOLIA.value: ChainConfig(
        chain_id=421614,
        name="arbitrum-sepolia",
        display_name="Arbitrum Sepolia",
        rpc_url=os.environ.get(
            "ARBITRUM_SEPOLIA_RPC_URL", "https://sepolia-rollup.arbitrum.io/rpc"
        ),
        explorer_url="https://sepolia.arbiscan.io",
        native_currency="ETH",
        is_testnet=True,
        is_l2=True,
        avg_block_time=0.25,
        license_nft_address="0x000000000000000000000000000000000000dEaD",
        license_manager_address="0x000000000000000000000000000000000000dEaD",
    ),
    # Optimism Sepolia (Testnet) - L2 development
    ChainId.OPTIMISM_SEPOLIA.value: ChainConfig(
        chain_id=11155420,
        name="optimism-sepolia",
        display_name="Optimism Sepolia",
        rpc_url=os.environ.get("OPTIMISM_SEPOLIA_RPC_URL", "https://sepolia.optimism.io"),
        explorer_url="https://sepolia-optimism.etherscan.io",
        native_currency="ETH",
        is_testnet=True,
        is_l2=True,
        avg_block_time=2.0,
        license_nft_address="0x000000000000000000000000000000000000dEaD",
        license_manager_address="0x000000000000000000000000000000000000dEaD",
    ),
    # Base Sepolia (Testnet) - L2 development
    ChainId.BASE_SEPOLIA.value: ChainConfig(
        chain_id=84532,
        name="base-sepolia",
        display_name="Base Sepolia",
        rpc_url=os.environ.get("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org"),
        explorer_url="https://sepolia.basescan.org",
        native_currency="ETH",
        is_testnet=True,
        is_l2=True,
        avg_block_time=2.0,
        license_nft_address="0x000000000000000000000000000000000000dEaD",
        license_manager_address="0x000000000000000000000000000000000000dEaD",
    ),
    # Polygon Mainnet
    ChainId.POLYGON_MAINNET.value: ChainConfig(
        chain_id=137,
        name="polygon",
        display_name="Polygon",
        rpc_url=os.environ.get("POLYGON_RPC_URL", "https://polygon-rpc.com"),
        explorer_url="https://polygonscan.com",
        native_currency="MATIC",
        is_l2=True,
        avg_block_time=2.0,
        max_gas_price_gwei=500.0,
        priority_fee_gwei=30.0,
        superfluid_addresses={
            "Host": "0x3E14dC1b13c488a8d5D310918780c983bD5982E7",
            "CFAv1": "0x6EeE6060f715257b970700bc2656De21dEdF074C",
            "SuperTokenFactory": "0x2C90719f25B10Fc5646c82DA3240C76Fa5BcCF34",
        },
    ),
    # Polygon Mumbai (Testnet)
    ChainId.POLYGON_MUMBAI.value: ChainConfig(
        chain_id=80001,
        name="mumbai",
        display_name="Polygon Mumbai",
        rpc_url=os.environ.get("MUMBAI_RPC_URL", "https://rpc-mumbai.maticvigil.com"),
        explorer_url="https://mumbai.polygonscan.com",
        native_currency="MATIC",
        is_testnet=True,
        is_l2=True,
        avg_block_time=2.0,
        superfluid_addresses={
            "Host": "0xEB796bdb90fFA0f28255275e16936D25d3418603",
            "CFAv1": "0x49e565Ed1bdc17F3d220f72DF0857C26FA83F873",
            "SuperTokenFactory": "0x200657E2f123761f499a725A5C1B7E6b3C8f8e49",
        },
    ),
    # Arbitrum One
    ChainId.ARBITRUM_ONE.value: ChainConfig(
        chain_id=42161,
        name="arbitrum",
        display_name="Arbitrum One",
        rpc_url=os.environ.get("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        explorer_url="https://arbiscan.io",
        native_currency="ETH",
        is_l2=True,
        avg_block_time=0.25,
        max_gas_price_gwei=1.0,
        priority_fee_gwei=0.01,
        superfluid_addresses={
            "Host": "0xCf8Acb4eF033efF16E8080aed4c7D5B9285D2192",
            "CFAv1": "0x731FdBB12944973B500518179f4E374d877F8C4d",
            "SuperTokenFactory": "0x1C21Ead77fd45C84a4c916Db7A6635D0C6FF09D6",
        },
    ),
    # Arbitrum Goerli (Testnet)
    ChainId.ARBITRUM_GOERLI.value: ChainConfig(
        chain_id=421613,
        name="arbitrum-goerli",
        display_name="Arbitrum Goerli",
        rpc_url=os.environ.get("ARBITRUM_GOERLI_RPC_URL", "https://goerli-rollup.arbitrum.io/rpc"),
        explorer_url="https://goerli.arbiscan.io",
        native_currency="ETH",
        is_testnet=True,
        is_l2=True,
        avg_block_time=0.25,
    ),
    # Base Mainnet
    ChainId.BASE_MAINNET.value: ChainConfig(
        chain_id=8453,
        name="base",
        display_name="Base",
        rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
        explorer_url="https://basescan.org",
        native_currency="ETH",
        is_l2=True,
        avg_block_time=2.0,
        max_gas_price_gwei=0.1,
        superfluid_addresses={
            "Host": "0x4C073B3baB6d8826b8C5b229f3cfdC1eC6E47E74",
            "CFAv1": "0x19ba78B9cDB05A877718841c574325fdB53601bb",
            "SuperTokenFactory": "0xe20B9a38E0c96F61d1bA6b42a61512c56Fea5b03",
        },
    ),
    # Optimism Mainnet
    ChainId.OPTIMISM_MAINNET.value: ChainConfig(
        chain_id=10,
        name="optimism",
        display_name="Optimism",
        rpc_url=os.environ.get("OPTIMISM_RPC_URL", "https://mainnet.optimism.io"),
        explorer_url="https://optimistic.etherscan.io",
        native_currency="ETH",
        is_l2=True,
        avg_block_time=2.0,
        max_gas_price_gwei=0.1,
        superfluid_addresses={
            "Host": "0x567c4B141ED61923967cA25Ef4906C8781069a10",
            "CFAv1": "0x204C6f131bb7F258b2Ea1593f5309911d8E458eD",
            "SuperTokenFactory": "0x8276469A443D5C6B7146BED45e2abCaD3B6adad9",
        },
    ),
}


# =============================================================================
# Chain Manager
# =============================================================================


class ChainManager:
    """
    Manages multi-chain operations for the RRA module.

    Provides chain selection, configuration, and cross-chain utilities.
    """

    def __init__(self, default_chain_id: int = ChainId.ETHEREUM_MAINNET.value):
        """
        Initialize the chain manager.

        Args:
            default_chain_id: Default chain ID to use
        """
        self._default_chain_id = default_chain_id
        self._active_chain_id = default_chain_id
        self._deployed_contracts: Dict[int, Dict[str, str]] = {}

    @property
    def active_chain(self) -> ChainConfig:
        """Get the currently active chain configuration."""
        return self.get_chain(self._active_chain_id)

    @property
    def active_chain_id(self) -> int:
        """Get the currently active chain ID."""
        return self._active_chain_id

    def set_active_chain(self, chain_id: int) -> ChainConfig:
        """
        Set the active chain.

        Args:
            chain_id: Chain ID to activate

        Returns:
            The activated chain configuration
        """
        if chain_id not in CHAIN_CONFIGS:
            raise ValueError(f"Unsupported chain ID: {chain_id}")
        self._active_chain_id = chain_id
        return self.active_chain

    def get_chain(self, chain_id: int) -> ChainConfig:
        """
        Get chain configuration by ID.

        Args:
            chain_id: Chain ID

        Returns:
            Chain configuration
        """
        if chain_id not in CHAIN_CONFIGS:
            raise ValueError(f"Unsupported chain ID: {chain_id}")
        return CHAIN_CONFIGS[chain_id]

    def get_chain_by_name(self, name: str) -> ChainConfig:
        """
        Get chain configuration by name.

        Args:
            name: Chain name (e.g., 'polygon', 'arbitrum')

        Returns:
            Chain configuration
        """
        for config in CHAIN_CONFIGS.values():
            if config.name == name:
                return config
        raise ValueError(f"Unknown chain name: {name}")

    def list_chains(self, include_testnets: bool = False) -> List[ChainConfig]:
        """
        List all available chains.

        Args:
            include_testnets: Whether to include testnets

        Returns:
            List of chain configurations
        """
        chains = list(CHAIN_CONFIGS.values())
        if not include_testnets:
            chains = [c for c in chains if not c.is_testnet]
        return chains

    def list_l2_chains(self) -> List[ChainConfig]:
        """List all L2 chains (lower gas fees)."""
        return [c for c in CHAIN_CONFIGS.values() if c.is_l2 and not c.is_testnet]

    def get_cheapest_chain(self) -> ChainConfig:
        """
        Get the chain with lowest expected gas costs.

        Returns:
            Chain configuration for cheapest network
        """
        l2_chains = self.list_l2_chains()
        if not l2_chains:
            return self.get_chain(ChainId.ETHEREUM_MAINNET.value)

        # Sort by max gas price (lower is better)
        return min(l2_chains, key=lambda c: c.max_gas_price_gwei or float("inf"))

    def register_contract(self, chain_id: int, contract_name: str, address: str) -> None:
        """
        Register a deployed contract address.

        Args:
            chain_id: Chain ID where contract is deployed
            contract_name: Name of the contract
            address: Contract address
        """
        if chain_id not in self._deployed_contracts:
            self._deployed_contracts[chain_id] = {}
        self._deployed_contracts[chain_id][contract_name] = address

    def get_contract_address(self, chain_id: int, contract_name: str) -> Optional[str]:
        """
        Get a deployed contract address.

        Args:
            chain_id: Chain ID
            contract_name: Name of the contract

        Returns:
            Contract address or None
        """
        chain_contracts = self._deployed_contracts.get(chain_id, {})
        return chain_contracts.get(contract_name)

    def get_recommended_chain(self, use_case: str = "general") -> ChainConfig:
        """
        Get recommended chain for a specific use case.

        Args:
            use_case: One of 'general', 'high_volume', 'streaming', 'nft'

        Returns:
            Recommended chain configuration
        """
        if use_case == "high_volume":
            # High transaction volume - use cheapest L2
            return self.get_cheapest_chain()

        elif use_case == "streaming":
            # Superfluid streaming - needs Superfluid deployment
            for chain in self.list_l2_chains():
                if chain.superfluid_addresses:
                    return chain
            return self.get_chain(ChainId.POLYGON_MAINNET.value)

        elif use_case == "nft":
            # NFT minting - Ethereum for prestige, Polygon for cost
            return self.get_chain(ChainId.POLYGON_MAINNET.value)

        else:
            # General use - default to Polygon for balance
            return self.get_chain(ChainId.POLYGON_MAINNET.value)

    def estimate_gas_cost_usd(
        self, chain_id: int, gas_units: int, native_price_usd: float
    ) -> float:
        """
        Estimate gas cost in USD.

        Args:
            chain_id: Chain ID
            gas_units: Estimated gas units
            native_price_usd: Price of native currency in USD

        Returns:
            Estimated cost in USD
        """
        chain = self.get_chain(chain_id)
        gas_price_gwei = chain.max_gas_price_gwei or 50.0
        gas_price_eth = gas_price_gwei / 1e9
        cost_native = gas_units * gas_price_eth
        return cost_native * native_price_usd


# =============================================================================
# Global Instance
# =============================================================================

# Default chain manager instance
chain_manager = ChainManager()


def get_chain_manager() -> ChainManager:
    """Get the global chain manager instance."""
    return chain_manager
