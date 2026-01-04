#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Claim Royalties from Story Protocol

Claims pending revenue from your IP Asset's Royalty Vault.

Usage:
    python scripts/claim_royalties.py --ip-asset 0xYourIPAssetID --private-key $PRIVATE_KEY

Or with environment variables:
    set STORY_PRIVATE_KEY=0x...
    python scripts/claim_royalties.py --ip-asset 0xYourIPAssetID
"""

import argparse
import os
import sys
from web3 import Web3

# Story Protocol Constants
STORY_MAINNET_CHAIN_ID = 1514
STORY_MAINNET_RPC = "https://mainnet.storyrpc.io"

# Story Protocol Contract Addresses (Mainnet) - Updated Jan 2026
ROYALTY_MODULE = "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086"
IP_ASSET_REGISTRY = "0x77319B4031e6eF1250907aa00018B8B1c67a244b"

# Royalty Module ABI (minimal for claiming)
ROYALTY_MODULE_ABI = [
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "claimer", "type": "address"},
            {"name": "tokens", "type": "address[]"}
        ],
        "name": "claimRevenue",
        "outputs": [{"name": "", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "ipId", "type": "address"}],
        "name": "ipRoyaltyVaults",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "receiverIpId", "type": "address"},
            {"name": "payerIpId", "type": "address"},
            {"name": "token", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "payRoyaltyOnBehalf",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# IP Royalty Vault ABI (for checking balance and claiming)
ROYALTY_VAULT_ABI = [
    {
        "inputs": [],
        "name": "claimableRevenue",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "token", "type": "address"}],
        "name": "claimableRevenue",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "claimer", "type": "address"},
            {"name": "token", "type": "address"}
        ],
        "name": "claimRevenueByTokenBatch",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "snapshot",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "pendingVaultAmount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Common token addresses
TOKENS = {
    "ETH": "0x0000000000000000000000000000000000000000",
    "WIP": "0x1514000000000000000000000000000000000000",  # Wrapped IP
    "WETH": "0x0000000000000000000000000000000000000000",
}


def claim_royalties(ip_asset_id: str, private_key: str, network: str = "mainnet"):
    """
    Claim pending royalties from an IP Asset's Royalty Vault.

    Args:
        ip_asset_id: The IP Asset address
        private_key: Private key for signing transactions
        network: Network name (mainnet or testnet)
    """
    print("=" * 60)
    print("Story Protocol Royalty Claim")
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

    # Normalize IP Asset address
    ip_asset_id = Web3.to_checksum_address(ip_asset_id.lower())
    print(f"\nIP Asset: {ip_asset_id}")

    # Get Royalty Module contract
    royalty_module = w3.eth.contract(
        address=Web3.to_checksum_address(ROYALTY_MODULE.lower()),
        abi=ROYALTY_MODULE_ABI
    )

    # Get the Royalty Vault address for this IP Asset
    print("\nLooking up Royalty Vault...")
    try:
        vault_address = royalty_module.functions.ipRoyaltyVaults(ip_asset_id).call()
        print(f"  Royalty Vault: {vault_address}")

        if vault_address == "0x0000000000000000000000000000000000000000":
            print("\n[WARNING] No Royalty Vault found for this IP Asset.")
            print("This could mean:")
            print("  - The IP Asset was registered without a royalty policy")
            print("  - No revenue has been received yet")
            print("  - The vault hasn't been created yet")
            return

    except Exception as e:
        print(f"[ERROR] Failed to get Royalty Vault: {e}")
        return

    # Get the Royalty Vault contract
    vault = w3.eth.contract(
        address=Web3.to_checksum_address(vault_address),
        abi=ROYALTY_VAULT_ABI
    )

    # Check pending/claimable amounts
    print("\nChecking balances...")

    try:
        # Try to get pending vault amount
        pending = vault.functions.pendingVaultAmount().call()
        print(f"  Pending in vault: {w3.from_wei(pending, 'ether')} ETH/IP")
    except Exception:
        print("  Could not read pending amount")

    # Check claimable for common tokens
    tokens_to_claim = []
    for token_name, token_address in TOKENS.items():
        try:
            claimable = vault.functions.claimableRevenue(
                Web3.to_checksum_address(token_address)
            ).call()
            if claimable > 0:
                print(f"  Claimable {token_name}: {w3.from_wei(claimable, 'ether')}")
                tokens_to_claim.append((token_name, token_address, claimable))
        except Exception:
            # Try without token parameter
            try:
                claimable = vault.functions.claimableRevenue().call()
                if claimable > 0:
                    print(f"  Claimable (native): {w3.from_wei(claimable, 'ether')}")
                    tokens_to_claim.append(("NATIVE", TOKENS["ETH"], claimable))
            except Exception:
                pass

    if not tokens_to_claim:
        print("\n[INFO] No claimable revenue found.")
        print("\nPossible reasons:")
        print("  1. Revenue hasn't been snapshotted yet")
        print("  2. Revenue was already claimed")
        print("  3. The minting fee went elsewhere (protocol fee)")
        print("\nTrying to snapshot and claim anyway...")

    # Try to snapshot first (makes pending funds claimable)
    print("\nStep 1: Snapshotting pending revenue...")
    try:
        nonce = w3.eth.get_transaction_count(owner_address)
        gas_price = w3.eth.gas_price

        snapshot_tx = vault.functions.snapshot().build_transaction({
            "from": owner_address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": 200000,
        })

        signed_tx = w3.eth.account.sign_transaction(snapshot_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  Snapshot tx: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt["status"] == 1:
            print(f"  Snapshot confirmed in block {receipt['blockNumber']}")
        else:
            print("  Snapshot failed (might be no pending funds)")
    except Exception as e:
        print(f"  Snapshot skipped: {str(e)[:50]}...")

    # Now try to claim
    print("\nStep 2: Claiming revenue...")

    # Claim for each token
    token_addresses = [TOKENS["ETH"], TOKENS["WIP"]]

    try:
        nonce = w3.eth.get_transaction_count(owner_address)

        claim_tx = royalty_module.functions.claimRevenue(
            ip_asset_id,
            owner_address,
            [Web3.to_checksum_address(t.lower()) for t in token_addresses]
        ).build_transaction({
            "from": owner_address,
            "nonce": nonce,
            "gasPrice": w3.eth.gas_price,
            "gas": 300000,
        })

        signed_tx = w3.eth.account.sign_transaction(claim_tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  Claim tx: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt["status"] == 1:
            print(f"\n  Claim confirmed in block {receipt['blockNumber']}")
            print(f"  Gas used: {receipt['gasUsed']}")

            # Check new balance
            new_balance = w3.eth.get_balance(owner_address)
            print(f"\n  Your balance: {w3.from_wei(new_balance, 'ether')} IP")
            print("\n" + "=" * 60)
            print("CLAIM COMPLETE!")
            print("=" * 60)
        else:
            print("\n[ERROR] Claim transaction failed")
            print("Check StoryScan for details")

    except Exception as e:
        error_msg = str(e)
        print(f"\n[ERROR] Claim failed: {error_msg[:100]}")

        if "revert" in error_msg.lower():
            print("\nThis usually means:")
            print("  - No revenue to claim")
            print("  - You don't own the Royalty Tokens")
            print("  - Revenue already claimed")

    # Final balance check
    print(f"\nYour wallet balance: {w3.from_wei(w3.eth.get_balance(owner_address), 'ether')} IP")
    print(f"StoryScan: https://storyscan.io/address/{owner_address}")


def main():
    parser = argparse.ArgumentParser(
        description="Claim royalties from Story Protocol Royalty Vault"
    )
    parser.add_argument(
        "--ip-asset",
        default="0xf08574c30337dde7C38869b8d399BA07ab23a07F",
        help="Story Protocol IP Asset ID (address)",
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

    claim_royalties(
        ip_asset_id=args.ip_asset,
        private_key=private_key,
        network=args.network,
    )


if __name__ == "__main__":
    main()
