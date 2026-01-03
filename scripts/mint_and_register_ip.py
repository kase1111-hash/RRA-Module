#!/usr/bin/env python3
"""
Mint NFT and Register as IP Asset on Story Protocol

This script:
1. Mints an NFT using Story's SPG NFT collection
2. Registers it as an IP Asset
3. Attaches license terms (ID 28437)

Usage:
    python scripts/mint_and_register_ip.py --private-key 0x...
"""

import argparse
import os
import sys
import time
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses (from deployment-1514.json)
CONTRACTS = {
    "ip_asset_registry": "0x77319B4031e6eF1250907aa00018B8B1c67a244b",
    "licensing_module": "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f",
    "pil_template": "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316",
    "registration_workflows": "0xbe39E1C756e921BD25DF86e7AAa31106d1eb0424",
    "spg_nft_beacon": "0xD2926B9ecaE85fF59B6FB0ff02f568a680c01218",
}

# Our license terms
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
        "outputs": [{"name": "", "type": "address"}],
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
    },
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
        "inputs": [
            {"name": "chainId", "type": "uint256"},
            {"name": "tokenContract", "type": "address"},
            {"name": "tokenId", "type": "uint256"}
        ],
        "name": "ipId",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def main():
    parser = argparse.ArgumentParser(description="Mint and Register IP Asset")
    parser.add_argument("--private-key", help="Private key (or set STORY_PRIVATE_KEY)")
    args = parser.parse_args()

    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Private key required")
        print("Usage: python scripts/mint_and_register_ip.py --private-key 0x...")
        sys.exit(1)

    # Connect
    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect to Story Protocol")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    print("=" * 60)
    print("Story Protocol IP Asset Registration")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} IP")
    print(f"Chain ID: {w3.eth.chain_id}")

    # Get contracts
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["ip_asset_registry"]),
        abi=IP_ASSET_REGISTRY_ABI
    )
    licensing = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["licensing_module"]),
        abi=LICENSING_MODULE_ABI
    )

    # OPTION A: Use an existing public SPG NFT collection
    # Story Protocol has a default SPG NFT that anyone can mint from
    # Let's try to find one or use the beacon to create one

    print("\n" + "-" * 60)
    print("STEP 1: Creating SPG NFT Collection")
    print("-" * 60)

    spg_beacon = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["spg_nft_beacon"]),
        abi=SPG_NFT_BEACON_ABI
    )

    try:
        # Create a new SPG NFT collection for RRA-Module
        nonce = w3.eth.get_transaction_count(account.address)

        tx = spg_beacon.functions.createCollection(
            "RRA-Module License",  # name
            "RRML",                # symbol
            1000,                  # maxSupply
            w3.to_wei(0.005, 'ether'),  # mintFee (0.005 IP)
            "0x0000000000000000000000000000000000000000",  # mintFeeToken (native)
            account.address,       # owner
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  Creating collection... TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] != 1:
            print("  [ERROR] Collection creation failed!")
            print("  Trying alternative approach...")
            raise Exception("Collection creation failed")

        # Get the created collection address from logs
        # The createCollection emits an event with the new address
        spg_nft_address = None
        for log in receipt['logs']:
            if len(log['topics']) > 0:
                # Look for the collection address in the logs
                # Usually it's in the data or as a topic
                if len(log['data']) >= 66:
                    # Address is often in the data
                    potential_addr = '0x' + log['data'].hex()[-40:]
                    if w3.eth.get_code(Web3.to_checksum_address(potential_addr)):
                        spg_nft_address = Web3.to_checksum_address(potential_addr)
                        break

        if not spg_nft_address:
            # Try getting from contract call result
            print("  [WARN] Could not extract collection address from logs")
            print("  Check StoryScan for the created collection")
            print(f"  TX: https://www.storyscan.io/tx/{tx_hash.hex()}")
            sys.exit(1)

        print(f"  Collection created: {spg_nft_address}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        print("\n  Trying direct IP Asset registration instead...")

        # Alternative: Just register directly using IPAssetRegistry
        # This requires an existing NFT - let's check if we can use a simpler approach
        print("\n" + "=" * 60)
        print("ALTERNATIVE: Use Story Protocol Web Interface")
        print("=" * 60)
        print("""
The easiest way to register an IP Asset is:

1. Go to: https://app.story.foundation
2. Connect wallet: {0}
3. Click "Register IP"
4. Upload an image/file representing RRA-Module
5. Complete the registration

After registration, copy the IP Asset ID and run:
  python scripts/attach_terms.py --ip-asset <NEW_IP_ASSET_ID>

This will attach license terms ID 28437 to your new IP Asset.
""".format(account.address))
        sys.exit(0)

    # STEP 2: Mint and Register IP
    print("\n" + "-" * 60)
    print("STEP 2: Minting NFT and Registering as IP Asset")
    print("-" * 60)

    workflows = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACTS["registration_workflows"]),
        abi=REGISTRATION_WORKFLOWS_ABI
    )

    ip_metadata = (
        "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/.market.yaml",
        b'\x00' * 32,  # ipMetadataHash (placeholder)
        "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/README.md",
        b'\x00' * 32,  # nftMetadataHash (placeholder)
    )

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = workflows.functions.mintAndRegisterIp(
            spg_nft_address,      # spgNftContract
            account.address,       # recipient
            ip_metadata,           # ipMetadata tuple
            True,                  # allowDuplicates
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 800000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  Minting and registering... TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] != 1:
            print("  [ERROR] Registration failed!")
            sys.exit(1)

        # Extract IP Asset ID from logs
        ip_asset_id = None
        for log in receipt['logs']:
            # Look for IPRegistered event
            if len(log['data']) >= 66:
                potential_addr = '0x' + log['data'].hex()[26:66]
                if len(potential_addr) == 42:
                    try:
                        addr = Web3.to_checksum_address(potential_addr)
                        if registry.functions.isRegistered(addr).call():
                            ip_asset_id = addr
                            break
                    except Exception:
                        pass

        if not ip_asset_id:
            print("  [WARN] Could not extract IP Asset ID from logs")
            print(f"  Check TX: https://www.storyscan.io/tx/{tx_hash.hex()}")
        else:
            print(f"\n  IP Asset ID: {ip_asset_id}")

    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    # STEP 3: Attach License Terms
    if ip_asset_id:
        print("\n" + "-" * 60)
        print("STEP 3: Attaching License Terms")
        print("-" * 60)

        try:
            nonce = w3.eth.get_transaction_count(account.address)

            tx = licensing.functions.attachLicenseTerms(
                ip_asset_id,
                Web3.to_checksum_address(CONTRACTS["pil_template"]),
                LICENSE_TERMS_ID,
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
                'chainId': CHAIN_ID,
            })

            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  Attaching terms... TX: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt['status'] == 1:
                print("  License terms attached successfully!")
            else:
                print("  [WARN] Attachment may have failed - check StoryScan")

        except Exception as e:
            print(f"  [WARN] Could not attach terms: {e}")
            print("  You can attach manually later with attach_terms.py")

    # Summary
    print("\n" + "=" * 60)
    print("REGISTRATION COMPLETE!")
    print("=" * 60)
    if ip_asset_id:
        print(f"\n  IP Asset ID: {ip_asset_id}")
        print(f"  License Terms: {LICENSE_TERMS_ID}")
        print(f"\n  StoryScan: https://www.storyscan.io/ipa/{ip_asset_id}")
        print("\nNEXT STEPS:")
        print(f"  1. Update .market.yaml: ip_asset_id: \"{ip_asset_id}\"")
        print(f"  2. Update buy-license.html: IP_ASSET_ID = \"{ip_asset_id}\"")


if __name__ == "__main__":
    main()
