#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Update SPG NFT Token URI

This script updates the token URI for an NFT minted via SPG collection.
Only the token owner can call this function.

Usage:
    python scripts/update_nft_uri.py --private-key 0x...
"""

import argparse
import hashlib
import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# SPG NFT Collection (created in step 1)
SPG_NFT_COLLECTION = "0x6f1E5AfAC39cBDAa47d22df56A960F2172FbD7a5"

# Token ID (first minted token)
TOKEN_ID = 1

# NFT Metadata URI
NFT_METADATA_URI = "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/nft-metadata.json"

# SPGNFT ABI (setTokenURI function)
SPGNFT_ABI = [
    {
        "inputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "tokenUri", "type": "string"},
            {"name": "nftMetadataHash", "type": "bytes32"}
        ],
        "name": "setTokenURI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenId", "type": "uint256"},
            {"name": "tokenUri", "type": "string"}
        ],
        "name": "setTokenURI",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def compute_hash(content: str) -> bytes:
    """Compute SHA-256 hash of content as bytes32."""
    return hashlib.sha256(content.encode('utf-8')).digest()


def main():
    parser = argparse.ArgumentParser(description="Update SPG NFT Token URI")
    parser.add_argument("--private-key", help="Private key (or set STORY_PRIVATE_KEY)")
    parser.add_argument("--token-id", type=int, default=TOKEN_ID, help="Token ID to update")
    args = parser.parse_args()

    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Private key required")
        print("Usage: python scripts/update_nft_uri.py --private-key 0x...")
        sys.exit(1)

    # Connect
    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect to Story Protocol")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    print("=" * 60)
    print("Update SPG NFT Token URI")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} IP")
    print(f"SPG NFT Collection: {SPG_NFT_COLLECTION}")
    print(f"Token ID: {args.token_id}")

    # Get SPG NFT contract
    spg_nft = w3.eth.contract(
        address=Web3.to_checksum_address(SPG_NFT_COLLECTION),
        abi=SPGNFT_ABI
    )

    # Check token owner
    print("\n" + "-" * 60)
    print("Verifying Token Ownership...")
    print("-" * 60)

    try:
        owner = spg_nft.functions.ownerOf(args.token_id).call()
        print(f"  Token Owner: {owner}")

        if owner.lower() != account.address.lower():
            print(f"  [ERROR] You are not the owner of token {args.token_id}")
            print(f"  Your address: {account.address}")
            sys.exit(1)
        print("  Ownership verified!")
    except Exception as e:
        print(f"  [ERROR] Could not verify ownership: {e}")
        sys.exit(1)

    # Get current token URI
    print("\n" + "-" * 60)
    print("Current Token URI...")
    print("-" * 60)

    try:
        current_uri = spg_nft.functions.tokenURI(args.token_id).call()
        print(f"  Current: {current_uri if current_uri else '(empty)'}")
    except Exception as e:
        print(f"  Could not fetch current URI: {e}")

    # Compute metadata hash
    print("\n" + "-" * 60)
    print("Computing Metadata Hash...")
    print("-" * 60)

    try:
        with open("nft-metadata.json", "r") as f:
            nft_metadata_content = f.read()
        nft_metadata_hash = compute_hash(nft_metadata_content)
        print(f"  Hash: 0x{nft_metadata_hash.hex()}")
    except FileNotFoundError:
        print("  [WARN] nft-metadata.json not found, using zero hash")
        nft_metadata_hash = b'\x00' * 32

    # Update token URI
    print("\n" + "-" * 60)
    print("Updating Token URI...")
    print("-" * 60)
    print(f"  New URI: {NFT_METADATA_URI}")

    # Try the deprecated version first (without hash) as it might have fewer restrictions
    print("\n  Trying setTokenURI (without hash)...")
    try:
        nonce = w3.eth.get_transaction_count(account.address)

        # Build function call manually for the 2-param version
        func_selector = w3.keccak(text="setTokenURI(uint256,string)")[:4]

        tx = spg_nft.functions.setTokenURI(
            args.token_id,
            NFT_METADATA_URI
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,  # More gas
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print("  Token URI updated successfully!")
        else:
            print("  [WARN] 2-param version failed, trying 3-param version...")
            raise Exception("Try 3-param version")

    except Exception as e:
        print(f"  First attempt failed: {e}")
        print("\n  Trying setTokenURI (with hash)...")

        try:
            nonce = w3.eth.get_transaction_count(account.address)

            tx = spg_nft.functions.setTokenURI(
                args.token_id,
                NFT_METADATA_URI,
                nft_metadata_hash
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': w3.eth.gas_price,
                'chainId': CHAIN_ID,
            })

            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  TX: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt['status'] == 1:
                print("  Token URI updated successfully!")
            else:
                print("  [ERROR] Both attempts failed")
                print(f"  Check: https://explorer.story.foundation/tx/{tx_hash.hex()}")
                sys.exit(1)

        except Exception as e2:
            print(f"  [ERROR] {e2}")
            sys.exit(1)

    # Verify new URI
    print("\n" + "-" * 60)
    print("Verifying Update...")
    print("-" * 60)

    try:
        new_uri = spg_nft.functions.tokenURI(args.token_id).call()
        print(f"  New URI: {new_uri}")
    except Exception as e:
        print(f"  Could not verify: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("NFT METADATA UPDATE COMPLETE")
    print("=" * 60)
    print(f"\n  SPG Collection: {SPG_NFT_COLLECTION}")
    print(f"  Token ID: {args.token_id}")
    print(f"  Metadata URI: {NFT_METADATA_URI}")
    print(f"\n  Story Explorer: https://explorer.story.foundation/ipa/0xf08574c30337dde7C38869b8d399BA07ab23a07F")


if __name__ == "__main__":
    main()
