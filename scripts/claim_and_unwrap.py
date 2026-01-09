#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Claim Royalties and Unwrap WIP to Native IP

Claims pending revenue from your IP Asset's Royalty Vault,
then unwraps any WIP tokens to native IP for easier transfer/exchange.

Usage:
    set STORY_PRIVATE_KEY=0x...
    python scripts/claim_and_unwrap.py

Or with arguments:
    python scripts/claim_and_unwrap.py --ip-asset 0x... --private-key 0x...
"""

import argparse
import os
import sys
from web3 import Web3

# Story Protocol Constants
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses
ROYALTY_MODULE = "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086"
WIP_TOKEN = "0x1514000000000000000000000000000000000000"

# Default IP Asset
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"

# Royalty Module ABI
ROYALTY_MODULE_ABI = [
    {
        "inputs": [{"name": "ipId", "type": "address"}],
        "name": "ipRoyaltyVaults",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
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
    }
]

# Royalty Vault ABI
ROYALTY_VAULT_ABI = [
    {
        "inputs": [{"name": "token", "type": "address"}],
        "name": "claimableRevenue",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "pendingVaultAmount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "snapshot",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# WIP Token ABI (WETH-style wrapped token)
WIP_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "amount", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]


def main():
    parser = argparse.ArgumentParser(description="Claim royalties and unwrap WIP to native IP")
    parser.add_argument("--ip-asset", default=IP_ASSET_ID, help="IP Asset ID")
    parser.add_argument("--private-key", help="Private key (or set STORY_PRIVATE_KEY)")
    parser.add_argument("--unwrap-only", action="store_true", help="Only unwrap existing WIP, skip claim")
    args = parser.parse_args()

    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Set STORY_PRIVATE_KEY environment variable")
        print("Usage: set STORY_PRIVATE_KEY=0x... && python scripts/claim_and_unwrap.py")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect to Story Protocol")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)

    print("=" * 60)
    print("Claim Royalties & Unwrap WIP")
    print("=" * 60)
    print(f"\nWallet: {account.address}")

    # Check balances
    native_balance = w3.eth.get_balance(account.address)
    print(f"Native IP: {w3.from_wei(native_balance, 'ether')} IP")

    wip = w3.eth.contract(
        address=Web3.to_checksum_address(WIP_TOKEN),
        abi=WIP_ABI
    )
    wip_balance = wip.functions.balanceOf(account.address).call()
    print(f"WIP Token: {w3.from_wei(wip_balance, 'ether')} WIP")

    ip_asset = Web3.to_checksum_address(args.ip_asset)

    # Step 1: Claim royalties (unless --unwrap-only)
    if not args.unwrap_only:
        print("\n" + "-" * 60)
        print("Step 1: Claiming Royalties")
        print("-" * 60)
        print(f"IP Asset: {ip_asset}")

        royalty_module = w3.eth.contract(
            address=Web3.to_checksum_address(ROYALTY_MODULE),
            abi=ROYALTY_MODULE_ABI
        )

        # Get vault address
        try:
            vault_address = royalty_module.functions.ipRoyaltyVaults(ip_asset).call()
            print(f"Royalty Vault: {vault_address}")

            if vault_address == "0x0000000000000000000000000000000000000000":
                print("  No Royalty Vault found (no revenue yet)")
            else:
                vault = w3.eth.contract(
                    address=Web3.to_checksum_address(vault_address),
                    abi=ROYALTY_VAULT_ABI
                )

                # Check claimable WIP
                try:
                    claimable = vault.functions.claimableRevenue(
                        Web3.to_checksum_address(WIP_TOKEN)
                    ).call()
                    print(f"Claimable WIP: {w3.from_wei(claimable, 'ether')} WIP")
                except Exception as e:
                    print(f"  Could not check claimable: {e}")

                # Try snapshot first
                print("\nSnapshotting pending revenue...")
                try:
                    nonce = w3.eth.get_transaction_count(account.address)
                    tx = vault.functions.snapshot().build_transaction({
                        "from": account.address,
                        "nonce": nonce,
                        "gas": 200000,
                        "gasPrice": w3.eth.gas_price,
                        "chainId": CHAIN_ID,
                    })
                    signed = w3.eth.account.sign_transaction(tx, private_key)
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    print(f"  Snapshot TX: {tx_hash.hex()}")
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    if receipt["status"] == 1:
                        print("  Snapshot successful!")
                    else:
                        print("  Snapshot may have failed")
                except Exception as e:
                    print(f"  Snapshot skipped: {str(e)[:50]}")

                # Claim revenue
                print("\nClaiming revenue...")
                try:
                    nonce = w3.eth.get_transaction_count(account.address)
                    tx = royalty_module.functions.claimRevenue(
                        ip_asset,
                        account.address,
                        [Web3.to_checksum_address(WIP_TOKEN)]
                    ).build_transaction({
                        "from": account.address,
                        "nonce": nonce,
                        "gas": 300000,
                        "gasPrice": w3.eth.gas_price,
                        "chainId": CHAIN_ID,
                    })
                    signed = w3.eth.account.sign_transaction(tx, private_key)
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    print(f"  Claim TX: {tx_hash.hex()}")
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                    if receipt["status"] == 1:
                        print("  Claim successful!")
                    else:
                        print("  Claim may have failed")
                except Exception as e:
                    print(f"  Claim failed: {str(e)[:80]}")

        except Exception as e:
            print(f"  Error: {e}")

        # Refresh WIP balance after claim
        wip_balance = wip.functions.balanceOf(account.address).call()
        print(f"\nWIP Balance after claim: {w3.from_wei(wip_balance, 'ether')} WIP")

    # Step 2: Unwrap WIP to native IP
    print("\n" + "-" * 60)
    print("Step 2: Unwrapping WIP to Native IP")
    print("-" * 60)

    # Refresh balance
    wip_balance = wip.functions.balanceOf(account.address).call()

    if wip_balance == 0:
        print("  No WIP tokens to unwrap")
    else:
        print(f"  Unwrapping {w3.from_wei(wip_balance, 'ether')} WIP...")

        try:
            nonce = w3.eth.get_transaction_count(account.address)
            tx = wip.functions.withdraw(wip_balance).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
                "chainId": CHAIN_ID,
            })

            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  Unwrap TX: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                print("  Unwrap successful!")
            else:
                print("  Unwrap may have failed")

        except Exception as e:
            print(f"  Unwrap failed: {e}")

    # Final summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    final_native = w3.eth.get_balance(account.address)
    final_wip = wip.functions.balanceOf(account.address).call()

    print(f"\nNative IP: {w3.from_wei(final_native, 'ether')} IP")
    print(f"WIP Token: {w3.from_wei(final_wip, 'ether')} WIP")
    print(f"\nStoryScan: https://storyscan.io/address/{account.address}")

    if final_native > native_balance:
        gained = final_native - native_balance
        print(f"\n  Gained: +{w3.from_wei(gained, 'ether')} IP")


if __name__ == "__main__":
    main()
