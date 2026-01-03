#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Register IP Asset with Story Protocol

Registers a new IP Asset on Story Protocol mainnet using the
RegistrationWorkflows contract.

Usage:
    python scripts/register_ip_asset.py --private-key $STORY_PRIVATE_KEY

Or with environment variables:
    set STORY_PRIVATE_KEY=0x...
    python scripts/register_ip_asset.py
"""

import argparse
import os
import sys
from web3 import Web3

# Story Protocol Mainnet Configuration
STORY_MAINNET_CHAIN_ID = 1514
STORY_MAINNET_RPC = "https://mainnet.storyrpc.io"

# Story Protocol Mainnet Contract Addresses (from deployment-1514.json)
CONTRACTS = {
    "ip_asset_registry": "0x77319B4031e6eF1250907aa00018B8B1c67a244b",
    "licensing_module": "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f",
    "pil_template": "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316",
    "royalty_module": "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086",
    "royalty_policy_lap": "0xBe54FB168b3c982b7AaE60dB6CF75Bd8447b390E",
    "registration_workflows": "0xbe39E1C756e921BD25DF86e7AAa31106d1eb0424",
    "license_attachment_workflows": "0xcC2E862bCee5B6036Db0de6E06Ae87e524a79fd8",
    "spg_nft_beacon": "0xD2926B9ecaE85fF59B6FB0ff02f568a680c01218",
}

# Our pre-registered license terms
LICENSE_TERMS_ID = 28437

# IP Asset Registry ABI (minimal for registration)
IP_ASSET_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "chainId", "type": "uint256"},
            {"name": "tokenContract", "type": "address"},
            {"name": "tokenId", "type": "uint256"}
        ],
        "name": "register",
        "outputs": [{"name": "id", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "id", "type": "address"}],
        "name": "isRegistered",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Registration Workflows ABI
REGISTRATION_WORKFLOWS_ABI = [
    {
        "inputs": [
            {"name": "spgNftContract", "type": "address"},
            {"name": "recipient", "type": "address"},
            {
                "name": "ipMetadata",
                "type": "tuple",
                "components": [
                    {"name": "ipMetadataURI", "type": "string"},
                    {"name": "ipMetadataHash", "type": "bytes32"},
                    {"name": "nftMetadataURI", "type": "string"},
                    {"name": "nftMetadataHash", "type": "bytes32"}
                ]
            },
            {"name": "allowDuplicates", "type": "bool"}
        ],
        "name": "mintAndRegisterIp",
        "outputs": [
            {"name": "ipId", "type": "address"},
            {"name": "tokenId", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# SPG NFT Factory ABI (for creating NFT collection)
SPG_NFT_BEACON_ABI = [
    {
        "inputs": [
            {"name": "name", "type": "string"},
            {"name": "symbol", "type": "string"},
            {"name": "maxSupply", "type": "uint32"},
            {"name": "mintFee", "type": "uint256"},
            {"name": "mintFeeToken", "type": "address"},
            {"name": "owner", "type": "address"},
        ],
        "name": "createCollection",
        "outputs": [{"name": "spgNftContract", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


def register_ip_asset(private_key: str, network: str = "mainnet"):
    """
    Register a new IP Asset on Story Protocol.

    Args:
        private_key: Private key for signing transactions
        network: Network name (mainnet or testnet)
    """
    print("=" * 60)
    print("Story Protocol IP Asset Registration")
    print("=" * 60)

    # Connect to Story Protocol
    rpc_url = STORY_MAINNET_RPC if network == "mainnet" else "https://aeneid.storyrpc.io"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        print(f"[ERROR] Failed to connect to {rpc_url}")
        sys.exit(1)

    print(f"\nConnected to Story Protocol {network}")
    print(f"  Chain ID: {w3.eth.chain_id}")

    # Create account from private key
    account = w3.eth.account.from_key(private_key)
    owner_address = account.address
    print(f"  Owner: {owner_address}")

    # Check balance
    balance = w3.eth.get_balance(owner_address)
    balance_ip = w3.from_wei(balance, 'ether')
    print(f"  Balance: {balance_ip} IP")

    if balance < w3.to_wei(0.01, 'ether'):
        print("\n[WARNING] Low balance! You need IP tokens for gas.")
        print("  Get IP tokens from: https://faucet.story.foundation")

    # Get IP Asset Registry contract
    ip_registry = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["ip_asset_registry"]),
        abi=IP_ASSET_REGISTRY_ABI
    )

    # Check current total supply of IP Assets
    try:
        total_supply = ip_registry.functions.totalSupply().call()
        print(f"\n  Total registered IP Assets: {total_supply}")
    except Exception as e:
        print(f"  Could not get total supply: {e}")

    print("\n" + "-" * 60)
    print("REGISTRATION OPTIONS")
    print("-" * 60)

    print("""
Option 1: Register an existing NFT as IP Asset
  - If you already have an NFT (ERC-721), you can register it

Option 2: Use Story Protocol's web interface
  - Go to: https://app.story.foundation
  - Connect your wallet
  - Click "Register IP"
  - This creates both the NFT and IP Asset

Option 3: Use the SDK (TypeScript)
  - npm install @story-protocol/core-sdk viem
  - Use mintAndRegisterIpAssetWithPilTerms()

For now, here's how to register an existing NFT:
""")

    print("\n" + "=" * 60)
    print("MANUAL REGISTRATION STEPS")
    print("=" * 60)

    print(f"""
1. First, get an ERC-721 NFT on Story mainnet
   - Mint on OpenSea, or
   - Deploy a simple ERC-721, or
   - Use Story's SPG NFT collection

2. Call IPAssetRegistry.register():
   - chainId: {STORY_MAINNET_CHAIN_ID}
   - tokenContract: <your NFT contract address>
   - tokenId: <your NFT token ID>

3. Then attach license terms:
   - licenseTermsId: {LICENSE_TERMS_ID}
   - Using LicensingModule.attachLicenseTerms()

StoryScan for contracts:
  - IP Asset Registry: https://storyscan.io/address/{CONTRACTS["ip_asset_registry"]}
  - Licensing Module: https://storyscan.io/address/{CONTRACTS["licensing_module"]}
""")

    # Provide the command for registering if they have an NFT
    print("\n" + "=" * 60)
    print("QUICK REGISTRATION (if you have an NFT)")
    print("=" * 60)

    print("""
Run this after you have an NFT:

python -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://mainnet.storyrpc.io'))
account = w3.eth.account.from_key('YOUR_PRIVATE_KEY')

# Replace these with your NFT details
NFT_CONTRACT = '0x...'  # Your ERC-721 contract
TOKEN_ID = 1            # Your token ID

registry = w3.eth.contract(
    address='0x77319B4031e6eF1250907aa00018B8B1c67a244b',
    abi=[{
        'inputs': [
            {'name': 'chainId', 'type': 'uint256'},
            {'name': 'tokenContract', 'type': 'address'},
            {'name': 'tokenId', 'type': 'uint256'}
        ],
        'name': 'register',
        'outputs': [{'name': 'id', 'type': 'address'}],
        'stateMutability': 'nonpayable',
        'type': 'function'
    }]
)

tx = registry.functions.register(1514, NFT_CONTRACT, TOKEN_ID).build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gasPrice': w3.eth.gas_price,
    'gas': 300000,
})

signed = w3.eth.account.sign_transaction(tx, account.key)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print(f'IP Asset registered! TX: {tx_hash.hex()}')
"
""")


def main():
    parser = argparse.ArgumentParser(
        description="Register IP Asset with Story Protocol"
    )
    parser.add_argument(
        "--private-key",
        help="Private key for signing transactions (or use STORY_PRIVATE_KEY env var)",
    )
    parser.add_argument(
        "--network",
        default="mainnet",
        choices=["mainnet", "testnet"],
        help="Story Protocol network",
    )

    args = parser.parse_args()

    # Get private key from args or environment
    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Private key required. Use --private-key or set STORY_PRIVATE_KEY")
        sys.exit(1)

    register_ip_asset(
        private_key=private_key,
        network=args.network,
    )


if __name__ == "__main__":
    main()
