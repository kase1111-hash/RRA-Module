#!/usr/bin/env python3
"""
Step 2: Mint and Register IP Asset

Uses the already-created SPG NFT collection to mint and register an IP Asset.

Usage:
    python scripts/step2_register_ip.py --private-key 0x...
"""

import argparse
import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Your SPG NFT Collection (created in Step 1)
SPG_NFT_COLLECTION = "0x6f1E5AfAC39cBDAa47d22df56A960F2172FbD7a5"

# Contract addresses
CONTRACTS = {
    "ip_asset_registry": "0x77319B4031e6eF1250907aa00018B8B1c67a244b",
    "licensing_module": "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f",
    "pil_template": "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316",
    "registration_workflows": "0xbe39E1C756e921BD25DF86e7AAa31106d1eb0424",
}

LICENSE_TERMS_ID = 28437

# ABIs
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

LICENSING_MODULE_ABI = [
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "licenseTemplate", "type": "address"},
            {"name": "licenseTermsId", "type": "uint256"}
        ],
        "name": "attachLicenseTerms",
        "outputs": [],
        "stateMutability": "nonpayable",
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


def main():
    parser = argparse.ArgumentParser(description="Step 2: Mint and Register IP Asset")
    parser.add_argument("--private-key", help="Private key (or set STORY_PRIVATE_KEY)")
    args = parser.parse_args()

    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Private key required")
        sys.exit(1)

    # Connect
    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    print("=" * 60)
    print("Step 2: Mint and Register IP Asset")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} IP")
    print(f"SPG NFT Collection: {SPG_NFT_COLLECTION}")

    # Get contracts
    workflows = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["registration_workflows"]),
        abi=REGISTRATION_WORKFLOWS_ABI
    )
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["ip_asset_registry"]),
        abi=IP_ASSET_REGISTRY_ABI
    )
    licensing = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["licensing_module"]),
        abi=LICENSING_MODULE_ABI
    )

    # IP Metadata
    ip_metadata = (
        "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/.market.yaml",
        b'\x00' * 32,  # ipMetadataHash
        "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/README.md",
        b'\x00' * 32,  # nftMetadataHash
    )

    print("\n" + "-" * 60)
    print("Minting NFT and Registering as IP Asset...")
    print("-" * 60)

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = workflows.functions.mintAndRegisterIp(
            Web3.to_checksum_address(SPG_NFT_COLLECTION),
            account.address,
            ip_metadata,
            True,  # allowDuplicates
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 1000000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] != 1:
            print("  [ERROR] Registration failed!")
            print(f"  Check: https://explorer.story.foundation/tx/{tx_hash.hex()}")
            sys.exit(1)

        # Extract IP Asset ID from logs
        ip_asset_id = None
        token_id = None

        for log in receipt['logs']:
            # Look for IPRegistered event or the return values
            if len(log['topics']) > 1:
                potential = '0x' + log['topics'][1].hex()[-40:]
                try:
                    addr = Web3.to_checksum_address(potential)
                    if registry.functions.isRegistered(addr).call():
                        ip_asset_id = addr
                        break
                except Exception:
                    pass

            # Also check data field for addresses
            if len(log['data']) >= 66 and not ip_asset_id:
                potential = '0x' + log['data'].hex()[26:66]
                try:
                    addr = Web3.to_checksum_address(potential)
                    if registry.functions.isRegistered(addr).call():
                        ip_asset_id = addr
                except Exception:
                    pass

        if ip_asset_id:
            print(f"\n  IP Asset ID: {ip_asset_id}")
        else:
            print("\n  [WARN] Could not extract IP Asset ID from logs")
            print(f"  Check TX: https://explorer.story.foundation/tx/{tx_hash.hex()}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    # Step 3: Attach License Terms
    if ip_asset_id:
        print("\n" + "-" * 60)
        print("Attaching License Terms...")
        print("-" * 60)

        try:
            nonce = w3.eth.get_transaction_count(account.address)

            tx = licensing.functions.attachLicenseTerms(
                ip_asset_id,
                Web3.to_checksum_address(CONTRACTS["pil_template"]),
                LICENSE_TERMS_ID
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
                print("  License terms attached!")
            else:
                print("  [WARN] Attachment may have failed")

        except Exception as e:
            print(f"  [WARN] {e}")

        # Summary
        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"\n  IP Asset ID: {ip_asset_id}")
        print(f"  License Terms: {LICENSE_TERMS_ID}")
        print(f"  SPG NFT: {SPG_NFT_COLLECTION}")
        print(f"\n  Story Explorer: https://explorer.story.foundation/ipa/{ip_asset_id}")
        print("\nUPDATE YOUR CONFIGS:")
        print(f'  .market.yaml: ip_asset_id: "{ip_asset_id}"')
        print(f'  buy-license.html: IP_ASSET_ID = "{ip_asset_id}"')


if __name__ == "__main__":
    main()
