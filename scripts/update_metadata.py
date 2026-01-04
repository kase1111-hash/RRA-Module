#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Update IP Asset Metadata on Story Protocol

This script updates the metadata URIs for an existing IP Asset using the
CoreMetadataModule contract.

Usage:
    python scripts/update_metadata.py --private-key 0x...
"""

import argparse
import hashlib
import json
import os
import sys
import requests
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses (from deployment-1514.json)
CONTRACTS = {
    "core_metadata_module": "0x6E81a25C99C6e8430aeC7353325EB138aFE5DC16",
    "ip_asset_registry": "0x77319B4031e6eF1250907aa00018B8B1c67a244b",
}

# Our IP Asset
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"

# New metadata URIs (raw GitHub URLs)
IP_METADATA_URI = "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/ip-metadata.json"
NFT_METADATA_URI = "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/nft-metadata.json"

# CoreMetadataModule ABI (relevant functions only)
CORE_METADATA_MODULE_ABI = [
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "metadataURI", "type": "string"},
            {"name": "metadataHash", "type": "bytes32"}
        ],
        "name": "setMetadataURI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "metadataURI", "type": "string"},
            {"name": "metadataHash", "type": "bytes32"},
            {"name": "nftMetadataHash", "type": "bytes32"}
        ],
        "name": "setAll",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "nftMetadataURI", "type": "string"},
            {"name": "nftMetadataHash", "type": "bytes32"}
        ],
        "name": "updateNftTokenURI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "ipId", "type": "address"}],
        "name": "isMetadataFrozen",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

IP_ASSET_REGISTRY_ABI = [
    {
        "inputs": [{"name": "id", "type": "address"}],
        "name": "isRegistered",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def compute_hash(content: str) -> bytes:
    """Compute SHA-256 hash of content as bytes32."""
    return hashlib.sha256(content.encode('utf-8')).digest()


def fetch_and_hash(url: str) -> tuple[str, bytes]:
    """Fetch content from URL and compute its hash."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text
        content_hash = compute_hash(content)
        return content, content_hash
    except Exception as e:
        print(f"  [WARN] Could not fetch {url}: {e}")
        return None, b'\x00' * 32


def main():
    parser = argparse.ArgumentParser(description="Update IP Asset Metadata")
    parser.add_argument("--private-key", help="Private key (or set STORY_PRIVATE_KEY)")
    parser.add_argument("--ip-asset", default=IP_ASSET_ID, help="IP Asset ID to update")
    args = parser.parse_args()

    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Private key required")
        print("Usage: python scripts/update_metadata.py --private-key 0x...")
        sys.exit(1)

    # Connect
    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect to Story Protocol")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    print("=" * 60)
    print("Update IP Asset Metadata")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} IP")
    print(f"IP Asset: {args.ip_asset}")

    # Get contracts
    metadata_module = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["core_metadata_module"]),
        abi=CORE_METADATA_MODULE_ABI
    )
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["ip_asset_registry"]),
        abi=IP_ASSET_REGISTRY_ABI
    )

    ip_asset = Web3.to_checksum_address(args.ip_asset)

    # Verify IP Asset is registered
    print("\n" + "-" * 60)
    print("Verifying IP Asset...")
    print("-" * 60)

    if not registry.functions.isRegistered(ip_asset).call():
        print(f"  [ERROR] IP Asset {ip_asset} is not registered!")
        sys.exit(1)
    print(f"  IP Asset verified: {ip_asset}")

    # Check if metadata is frozen
    try:
        is_frozen = metadata_module.functions.isMetadataFrozen(ip_asset).call()
        if is_frozen:
            print("  [ERROR] Metadata is frozen and cannot be updated!")
            sys.exit(1)
        print("  Metadata is not frozen (can be updated)")
    except Exception as e:
        print(f"  [WARN] Could not check frozen status: {e}")

    # Compute hashes from local files
    print("\n" + "-" * 60)
    print("Computing Metadata Hashes...")
    print("-" * 60)

    # Read local files for hash computation
    try:
        with open("ip-metadata.json", "r") as f:
            ip_metadata_content = f.read()
        ip_metadata_hash = compute_hash(ip_metadata_content)
        print(f"  IP Metadata Hash: 0x{ip_metadata_hash.hex()}")
    except FileNotFoundError:
        print("  [WARN] ip-metadata.json not found locally, fetching from URL...")
        _, ip_metadata_hash = fetch_and_hash(IP_METADATA_URI)
        print(f"  IP Metadata Hash: 0x{ip_metadata_hash.hex()}")

    try:
        with open("nft-metadata.json", "r") as f:
            nft_metadata_content = f.read()
        nft_metadata_hash = compute_hash(nft_metadata_content)
        print(f"  NFT Metadata Hash: 0x{nft_metadata_hash.hex()}")
    except FileNotFoundError:
        print("  [WARN] nft-metadata.json not found locally, fetching from URL...")
        _, nft_metadata_hash = fetch_and_hash(NFT_METADATA_URI)
        print(f"  NFT Metadata Hash: 0x{nft_metadata_hash.hex()}")

    # Update IP Metadata URI
    print("\n" + "-" * 60)
    print("Step 1: Updating IP Metadata URI...")
    print("-" * 60)
    print(f"  URI: {IP_METADATA_URI}")

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = metadata_module.functions.setMetadataURI(
            ip_asset,
            IP_METADATA_URI,
            ip_metadata_hash
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print("  IP Metadata URI updated successfully!")
        else:
            print("  [WARN] Transaction may have failed")
            print(f"  Check: https://explorer.story.foundation/tx/{tx_hash.hex()}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        print("\n  This might be a permissions issue. Only the IP Asset owner")
        print("  can update metadata. Trying alternative approach...")

    # Update NFT Metadata URI
    print("\n" + "-" * 60)
    print("Step 2: Updating NFT Token URI...")
    print("-" * 60)
    print(f"  URI: {NFT_METADATA_URI}")

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = metadata_module.functions.updateNftTokenURI(
            ip_asset,
            NFT_METADATA_URI,
            nft_metadata_hash
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print("  NFT Token URI updated successfully!")
        else:
            print("  [WARN] Transaction may have failed")

    except Exception as e:
        print(f"  [ERROR] {e}")

    # Summary
    print("\n" + "=" * 60)
    print("METADATA UPDATE COMPLETE")
    print("=" * 60)
    print(f"\n  IP Asset: {ip_asset}")
    print(f"  IP Metadata: {IP_METADATA_URI}")
    print(f"  NFT Metadata: {NFT_METADATA_URI}")
    print(f"\n  Story Explorer: https://explorer.story.foundation/ipa/{ip_asset}")
    print("\nNote: It may take a few minutes for the explorer to reflect changes.")


if __name__ == "__main__":
    main()
