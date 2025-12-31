#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
L3 Dispute Rollup Deployment Script.

Deploys the L3DisputeRollup contract and configures the sequencer:

Usage:
    python scripts/deploy_l3.py --network <network> [options]

Networks:
    - localhost: Local development (Anvil/Hardhat)
    - sepolia: Ethereum Sepolia testnet
    - base-sepolia: Base Sepolia testnet
    - mainnet: Ethereum mainnet (requires confirmation)

Options:
    --l2-bridge: Address of L2 bridge contract
    --l2-contract: Address of L2 ILRM contract
    --sequencer-bond: Bond amount for sequencers (in ETH)
    --verify: Verify contract on Etherscan/Basescan
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Web3 imports (optional, graceful fallback)
try:
    from web3 import Web3
    from eth_account import Account
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False


@dataclass
class NetworkConfig:
    """Configuration for a network."""

    name: str
    rpc_url: str
    chain_id: int
    explorer_url: Optional[str] = None
    explorer_api_key_env: Optional[str] = None
    is_testnet: bool = True


# Network configurations
NETWORKS: Dict[str, NetworkConfig] = {
    "localhost": NetworkConfig(
        name="localhost",
        rpc_url="http://127.0.0.1:8545",
        chain_id=31337,
        is_testnet=True,
    ),
    "sepolia": NetworkConfig(
        name="sepolia",
        rpc_url=os.environ.get("SEPOLIA_RPC_URL", "https://rpc.sepolia.org"),
        chain_id=11155111,
        explorer_url="https://sepolia.etherscan.io",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        is_testnet=True,
    ),
    "base-sepolia": NetworkConfig(
        name="base-sepolia",
        rpc_url=os.environ.get("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org"),
        chain_id=84532,
        explorer_url="https://sepolia.basescan.org",
        explorer_api_key_env="BASESCAN_API_KEY",
        is_testnet=True,
    ),
    "base": NetworkConfig(
        name="base",
        rpc_url=os.environ.get("BASE_RPC_URL", "https://mainnet.base.org"),
        chain_id=8453,
        explorer_url="https://basescan.org",
        explorer_api_key_env="BASESCAN_API_KEY",
        is_testnet=False,
    ),
    "mainnet": NetworkConfig(
        name="mainnet",
        rpc_url=os.environ.get("MAINNET_RPC_URL", "https://eth.llamarpc.com"),
        chain_id=1,
        explorer_url="https://etherscan.io",
        explorer_api_key_env="ETHERSCAN_API_KEY",
        is_testnet=False,
    ),
}


@dataclass
class DeploymentResult:
    """Result of a deployment."""

    contract_address: str
    transaction_hash: str
    deployer: str
    network: str
    constructor_args: Dict[str, Any]
    verified: bool = False


def load_contract_artifact(contract_name: str) -> Dict[str, Any]:
    """
    Load compiled contract artifact.

    Args:
        contract_name: Name of the contract

    Returns:
        Contract ABI and bytecode
    """
    # Try common artifact locations
    artifact_paths = [
        Path(f"out/{contract_name}.sol/{contract_name}.json"),  # Foundry
        Path(f"artifacts/contracts/{contract_name}.sol/{contract_name}.json"),  # Hardhat
        Path(f"build/contracts/{contract_name}.json"),  # Truffle
    ]

    for path in artifact_paths:
        if path.exists():
            with open(path) as f:
                artifact = json.load(f)
                return {
                    "abi": artifact.get("abi"),
                    "bytecode": artifact.get("bytecode", {}).get("object")
                    or artifact.get("bytecode"),
                }

    raise FileNotFoundError(
        f"Contract artifact not found for {contract_name}. "
        "Please compile contracts first with 'forge build' or 'npx hardhat compile'"
    )


def get_deployer_account() -> Any:
    """
    Get deployer account from environment.

    Returns:
        Account object
    """
    private_key = os.environ.get("DEPLOYER_PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            "DEPLOYER_PRIVATE_KEY environment variable not set. "
            "Set it to deploy contracts."
        )

    if not private_key.startswith("0x"):
        private_key = f"0x{private_key}"

    return Account.from_key(private_key)


def deploy_l3_rollup(
    network: str,
    l2_bridge: str,
    l2_contract: str,
    verify: bool = False,
) -> DeploymentResult:
    """
    Deploy the L3DisputeRollup contract.

    Args:
        network: Network to deploy to
        l2_bridge: Address of L2 bridge contract
        l2_contract: Address of L2 ILRM contract
        verify: Whether to verify on block explorer

    Returns:
        DeploymentResult with contract address
    """
    if not HAS_WEB3:
        raise ImportError(
            "web3 and eth_account packages required for deployment. "
            "Install with: pip install web3 eth-account"
        )

    if network not in NETWORKS:
        raise ValueError(f"Unknown network: {network}. Available: {list(NETWORKS.keys())}")

    config = NETWORKS[network]

    # Safety check for mainnet
    if not config.is_testnet:
        confirm = input(
            f"WARNING: Deploying to {network} (mainnet). "
            "This will cost real ETH. Continue? [y/N] "
        )
        if confirm.lower() != "y":
            print("Deployment cancelled.")
            sys.exit(0)

    print(f"\n{'='*60}")
    print(f"Deploying L3DisputeRollup to {network}")
    print(f"{'='*60}")

    # Connect to network
    w3 = Web3(Web3.HTTPProvider(config.rpc_url))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to {config.rpc_url}")

    print(f"Connected to {network} (chain ID: {w3.eth.chain_id})")

    # Get deployer
    account = get_deployer_account()
    deployer_address = account.address
    balance = w3.eth.get_balance(deployer_address)
    print(f"Deployer: {deployer_address}")
    print(f"Balance: {w3.from_wei(balance, 'ether')} ETH")

    if balance == 0:
        raise ValueError("Deployer account has no ETH for gas")

    # Load contract artifact
    print("\nLoading contract artifact...")
    artifact = load_contract_artifact("L3DisputeRollup")

    # Create contract instance
    contract = w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])

    # Build constructor transaction
    print("\nBuilding deployment transaction...")
    construct_txn = contract.constructor(
        l2_bridge,
        l2_contract,
    ).build_transaction({
        "from": deployer_address,
        "nonce": w3.eth.get_transaction_count(deployer_address),
        "gas": 5_000_000,  # Estimate
        "gasPrice": w3.eth.gas_price,
        "chainId": config.chain_id,
    })

    # Sign and send
    print("Signing transaction...")
    signed_txn = w3.eth.account.sign_transaction(construct_txn, account.key)

    print("Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"Transaction hash: {tx_hash.hex()}")

    # Wait for receipt
    print("Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

    if receipt["status"] != 1:
        raise RuntimeError("Deployment transaction failed")

    contract_address = receipt["contractAddress"]
    print(f"\n{'='*60}")
    print(f"L3DisputeRollup deployed successfully!")
    print(f"Contract address: {contract_address}")
    print(f"Transaction hash: {tx_hash.hex()}")
    print(f"Gas used: {receipt['gasUsed']}")
    print(f"{'='*60}")

    # Save deployment info
    deployment_info = {
        "network": network,
        "contract": "L3DisputeRollup",
        "address": contract_address,
        "tx_hash": tx_hash.hex(),
        "deployer": deployer_address,
        "block": receipt["blockNumber"],
        "constructor_args": {
            "l2Bridge": l2_bridge,
            "l2Contract": l2_contract,
        },
    }

    deployments_dir = Path("deployments")
    deployments_dir.mkdir(exist_ok=True)

    deployment_file = deployments_dir / f"{network}_l3_rollup.json"
    with open(deployment_file, "w") as f:
        json.dump(deployment_info, f, indent=2)
    print(f"\nDeployment info saved to: {deployment_file}")

    # Verify if requested
    verified = False
    if verify and config.explorer_url:
        print("\nVerifying contract on block explorer...")
        verified = verify_contract(
            network=network,
            contract_address=contract_address,
            constructor_args=[l2_bridge, l2_contract],
        )

    return DeploymentResult(
        contract_address=contract_address,
        transaction_hash=tx_hash.hex(),
        deployer=deployer_address,
        network=network,
        constructor_args={"l2Bridge": l2_bridge, "l2Contract": l2_contract},
        verified=verified,
    )


def verify_contract(
    network: str,
    contract_address: str,
    constructor_args: list,
) -> bool:
    """
    Verify contract on block explorer.

    Args:
        network: Network name
        contract_address: Deployed contract address
        constructor_args: Constructor arguments

    Returns:
        True if verification successful
    """
    config = NETWORKS[network]

    if not config.explorer_api_key_env:
        print("No explorer API key configured for this network")
        return False

    api_key = os.environ.get(config.explorer_api_key_env)
    if not api_key:
        print(f"Set {config.explorer_api_key_env} environment variable to verify")
        return False

    # In a real implementation, this would call the explorer API
    # For now, print instructions
    print(f"\nTo verify manually, run:")
    print(f"  forge verify-contract \\")
    print(f"    --chain-id {config.chain_id} \\")
    print(f"    --constructor-args $(cast abi-encode 'constructor(address,address)' {constructor_args[0]} {constructor_args[1]}) \\")
    print(f"    {contract_address} \\")
    print(f"    contracts/src/L3DisputeRollup.sol:L3DisputeRollup")

    return False


def setup_sequencer(
    network: str,
    contract_address: str,
    sequencer_address: str,
    bond_amount_eth: float = 10.0,
) -> str:
    """
    Register a sequencer with the L3 rollup.

    Args:
        network: Network name
        contract_address: L3DisputeRollup address
        sequencer_address: Sequencer address to register
        bond_amount_eth: Bond amount in ETH

    Returns:
        Transaction hash
    """
    if not HAS_WEB3:
        raise ImportError("web3 package required")

    config = NETWORKS[network]
    w3 = Web3(Web3.HTTPProvider(config.rpc_url))

    artifact = load_contract_artifact("L3DisputeRollup")
    contract = w3.eth.contract(address=contract_address, abi=artifact["abi"])

    account = get_deployer_account()
    bond_wei = w3.to_wei(bond_amount_eth, "ether")

    txn = contract.functions.registerSequencer().build_transaction({
        "from": account.address,
        "value": bond_wei,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": config.chain_id,
    })

    signed_txn = w3.eth.account.sign_transaction(txn, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt["status"] != 1:
        raise RuntimeError("Sequencer registration failed")

    print(f"Sequencer registered: {sequencer_address}")
    print(f"Bond: {bond_amount_eth} ETH")
    print(f"Transaction: {tx_hash.hex()}")

    return tx_hash.hex()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy L3 Dispute Rollup contracts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--network",
        required=True,
        choices=list(NETWORKS.keys()),
        help="Network to deploy to",
    )
    parser.add_argument(
        "--l2-bridge",
        required=True,
        help="Address of L2 bridge contract",
    )
    parser.add_argument(
        "--l2-contract",
        required=True,
        help="Address of L2 ILRM contract",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify contract on block explorer",
    )
    parser.add_argument(
        "--register-sequencer",
        metavar="ADDRESS",
        help="Register sequencer after deployment",
    )
    parser.add_argument(
        "--sequencer-bond",
        type=float,
        default=10.0,
        help="Sequencer bond amount in ETH (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print deployment info without actually deploying",
    )

    args = parser.parse_args()

    if args.dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - No transactions will be sent")
        print(f"{'='*60}")
        print(f"\nNetwork: {args.network}")
        print(f"L2 Bridge: {args.l2_bridge}")
        print(f"L2 Contract: {args.l2_contract}")
        print(f"Verify: {args.verify}")
        if args.register_sequencer:
            print(f"Register Sequencer: {args.register_sequencer}")
            print(f"Sequencer Bond: {args.sequencer_bond} ETH")
        return

    try:
        result = deploy_l3_rollup(
            network=args.network,
            l2_bridge=args.l2_bridge,
            l2_contract=args.l2_contract,
            verify=args.verify,
        )

        if args.register_sequencer:
            setup_sequencer(
                network=args.network,
                contract_address=result.contract_address,
                sequencer_address=args.register_sequencer,
                bond_amount_eth=args.sequencer_bond,
            )

        print("\nDeployment complete!")

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
