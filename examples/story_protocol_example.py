#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Example: Story Protocol Integration

This example demonstrates how to:
1. Register a repository as an IP Asset on Story Protocol
2. Attach Programmable IP License (PIL) terms
3. Register derivatives (forks) with automatic royalty tracking
4. Query royalty statistics and derivative graphs
"""

import os
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv

from rra.integrations.story_integration import StoryIntegrationManager
from rra.config.market_config import MarketConfig


def main():
    """Run Story Protocol integration example."""

    # Load environment variables
    load_dotenv()

    # Configuration
    rpc_url = os.getenv("ETHEREUM_RPC_URL", "https://sepolia.infura.io/v3/YOUR_KEY")
    owner_address = os.getenv("ETHEREUM_ADDRESS")
    private_key = os.getenv("ETHEREUM_PRIVATE_KEY")

    if not owner_address or not private_key:
        print("Error: Please set ETHEREUM_ADDRESS and ETHEREUM_PRIVATE_KEY in .env")
        return

    print("=" * 60)
    print("Story Protocol Integration Example")
    print("=" * 60)
    print()

    # Initialize Web3
    print("1. Connecting to Ethereum...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print("Error: Failed to connect to Ethereum network")
        return

    print(f"   ✓ Connected to network (Chain ID: {w3.eth.chain_id})")
    print()

    # Initialize Story Integration Manager
    print("2. Initializing Story Protocol Integration...")
    manager = StoryIntegrationManager(w3, network="testnet")

    network_info = manager.get_network_info()
    print("   ✓ Story Protocol Client initialized")
    print(f"   Network: {network_info['network']}")
    print(f"   Contracts: {len(network_info['story_contracts'])} deployed")
    print()

    # Load market configuration
    print("3. Loading market configuration...")
    market_config_path = Path(".market.yaml")

    if not market_config_path.exists():
        print("   ! .market.yaml not found, creating example config...")
        config = MarketConfig(
            target_price="0.05 ETH",
            floor_price="0.02 ETH",
            story_protocol_enabled=True,
            pil_commercial_use=True,
            pil_derivatives_allowed=True,
            pil_derivatives_attribution=True,
            pil_derivatives_reciprocal=False,
            derivative_royalty_percentage=0.15,
            developer_wallet=owner_address,
            description="Example repository with Story Protocol integration"
        )
    else:
        config = MarketConfig.from_yaml(market_config_path)
        config.story_protocol_enabled = True
        config.derivative_royalty_percentage = 0.15

    print("   ✓ Configuration loaded")
    print(f"   Story Protocol: {'Enabled' if config.story_protocol_enabled else 'Disabled'}")
    print(f"   Derivative Royalty: {config.derivative_royalty_percentage * 100}%")
    print()

    # Register repository as IP Asset
    print("4. Registering repository as IP Asset...")
    print("   Repository: https://github.com/example/repo")
    print(f"   Owner: {owner_address}")
    print()

    try:
        # Note: This is a simulation - actual registration requires gas
        print("   [SIMULATION MODE - No actual transactions]")
        print()

        # Simulated registration result
        simulated_result = {
            "status": "success",
            "ip_asset_id": "ip_asset_0x1234567890abcdef",
            "tx_hash": "0xabc123def456789...",
            "block_number": 12345678,
            "pil_terms_tx": "0xdef456abc789...",
            "royalty_tx": "0x789abc123def..."
        }

        print("   Registration Result:")
        print(f"   ✓ IP Asset ID: {simulated_result['ip_asset_id']}")
        print(f"   ✓ Transaction: {simulated_result['tx_hash']}")
        print(f"   ✓ PIL Terms: {simulated_result['pil_terms_tx']}")
        print(f"   ✓ Royalty Policy: {simulated_result['royalty_tx']}")
        print()

        # Actual registration (commented out to prevent accidental execution)
        """
        result = manager.register_repository_as_ip_asset(
            repo_url="https://github.com/example/repo",
            market_config=config,
            owner_address=owner_address,
            private_key=private_key,
            repo_description="Example repository for Story Protocol demo"
        )

        print(f"   ✓ IP Asset registered: {result['ip_asset_id']}")
        print(f"   ✓ Transaction: {result['tx_hash']}")

        # Update config with IP Asset ID
        manager.update_market_config_with_ip_asset(
            market_config_path,
            result['ip_asset_id']
        )
        """

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    # Demonstrate derivative registration
    print("5. Registering a derivative (fork)...")
    print("   Fork: https://github.com/fork-owner/forked-repo")
    print()

    print("   [SIMULATION MODE]")
    print()

    simulated_fork_result = {
        "status": "success",
        "derivative_ip_asset_id": "ip_asset_0xfork987654321",
        "parent_ip_asset_id": "ip_asset_0x1234567890abcdef",
        "tx_hash": "0xfork_tx_hash..."
    }

    print("   Derivative Registration Result:")
    print(f"   ✓ Derivative ID: {simulated_fork_result['derivative_ip_asset_id']}")
    print(f"   ✓ Parent ID: {simulated_fork_result['parent_ip_asset_id']}")
    print(f"   ✓ Transaction: {simulated_fork_result['tx_hash']}")
    print()

    # Actual derivative registration (commented out)
    """
    fork_result = manager.register_derivative_repository(
        parent_repo_url="https://github.com/example/repo",
        parent_ip_asset_id=result['ip_asset_id'],
        fork_repo_url="https://github.com/fork-owner/forked-repo",
        fork_description="Enhanced fork with additional features",
        license_terms_id="terms_0xabc123",
        fork_owner_address="0xForkOwnerAddress",
        private_key="0xForkPrivateKey"
    )

    print(f"   ✓ Fork registered: {fork_result['derivative_ip_asset_id']}")
    """

    # Query derivatives
    print("6. Querying derivative graph...")
    print()

    print("   [SIMULATION MODE]")
    print()

    simulated_derivatives = {
        "parent_ip_asset_id": "ip_asset_0x1234567890abcdef",
        "derivative_count": 3,
        "derivatives": [
            {"id": "ip_asset_0xfork1", "owner": "0xFork1Owner"},
            {"id": "ip_asset_0xfork2", "owner": "0xFork2Owner"},
            {"id": "ip_asset_0xfork3", "owner": "0xFork3Owner"}
        ]
    }

    print("   Derivative Graph:")
    print(f"   Total Derivatives: {simulated_derivatives['derivative_count']}")
    for i, deriv in enumerate(simulated_derivatives['derivatives'], 1):
        print(f"   {i}. ID: {deriv['id']}")
        print(f"      Owner: {deriv['owner']}")
    print()

    # Actual query (commented out)
    """
    derivatives = manager.get_repository_derivatives(result['ip_asset_id'])

    print(f"   Total Derivatives: {derivatives['derivative_count']}")
    for deriv in derivatives['derivatives']:
        print(f"   - {deriv['id']} (Owner: {deriv['owner']})")
    """

    # Query royalty statistics
    print("7. Querying royalty statistics...")
    print()

    print("   [SIMULATION MODE]")
    print()

    simulated_royalty_stats = {
        "ip_asset_id": "ip_asset_0x1234567890abcdef",
        "royalty_percentage": 15.0,
        "payment_token": "0x0000000000000000000000000000000000000000",
        "total_collected_wei": 1500000000000000000,
        "total_collected_eth": 1.5,
        "last_payment_timestamp": 1703001234
    }

    print("   Royalty Statistics:")
    print(f"   Royalty Rate: {simulated_royalty_stats['royalty_percentage']}%")
    print(f"   Total Collected: {simulated_royalty_stats['total_collected_eth']} ETH")
    print("   Payment Token: ETH")
    print()

    # Actual query (commented out)
    """
    stats = manager.get_royalty_stats(result['ip_asset_id'])

    print(f"   Royalty Rate: {stats['royalty_percentage']}%")
    print(f"   Total Collected: {stats['total_collected_eth']} ETH")
    print(f"   Last Payment: {stats['last_payment_timestamp']}")
    """

    print("=" * 60)
    print("Example Complete!")
    print()
    print("To run with actual transactions:")
    print("1. Ensure you have testnet ETH")
    print("2. Uncomment the actual transaction code blocks")
    print("3. Set ETHEREUM_RPC_URL to a testnet RPC endpoint")
    print("4. Run the script")
    print("=" * 60)


if __name__ == "__main__":
    main()
