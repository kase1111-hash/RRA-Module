#!/usr/bin/env python3
"""
Register Custom License Terms with URI

This script registers new PIL license terms with a custom URI pointing to
license metadata that includes the custom license name.

Usage:
    python scripts/register_custom_license.py --private-key 0x...
"""

import argparse
import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses
PIL_LICENSE_TEMPLATE = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316"
LICENSING_MODULE = "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f"
ROYALTY_POLICY_LAP = "0xBe54FB168b3c982b7AaE60dB6CF75Bd8447b390E"
WIP_TOKEN = "0x1514000000000000000000000000000000000000"

# Our IP Asset
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"

# License terms metadata URI
LICENSE_TERMS_URI = "https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/license-terms-metadata.json"

# PILicenseTemplate ABI
PIL_TEMPLATE_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "transferable", "type": "bool"},
                    {"name": "royaltyPolicy", "type": "address"},
                    {"name": "defaultMintingFee", "type": "uint256"},
                    {"name": "expiration", "type": "uint256"},
                    {"name": "commercialUse", "type": "bool"},
                    {"name": "commercialAttribution", "type": "bool"},
                    {"name": "commercializerChecker", "type": "address"},
                    {"name": "commercializerCheckerData", "type": "bytes"},
                    {"name": "commercialRevShare", "type": "uint32"},
                    {"name": "commercialRevCeiling", "type": "uint256"},
                    {"name": "derivativesAllowed", "type": "bool"},
                    {"name": "derivativesAttribution", "type": "bool"},
                    {"name": "derivativesApproval", "type": "bool"},
                    {"name": "derivativesReciprocal", "type": "bool"},
                    {"name": "derivativeRevCeiling", "type": "uint256"},
                    {"name": "currency", "type": "address"},
                    {"name": "uri", "type": "string"}
                ],
                "name": "terms",
                "type": "tuple"
            }
        ],
        "name": "registerLicenseTerms",
        "outputs": [{"name": "id", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "id", "type": "uint256"}],
        "name": "exists",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# LicensingModule ABI
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


def main():
    parser = argparse.ArgumentParser(description="Register Custom License Terms")
    parser.add_argument("--private-key", help="Private key (or set STORY_PRIVATE_KEY)")
    args = parser.parse_args()

    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Private key required")
        sys.exit(1)

    # Connect
    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect to Story Protocol")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)
    print("=" * 60)
    print("Register Custom License Terms")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} IP")

    # Get contracts
    pil_template = w3.eth.contract(
        address=Web3.to_checksum_address(PIL_LICENSE_TEMPLATE),
        abi=PIL_TEMPLATE_ABI
    )
    licensing_module = w3.eth.contract(
        address=Web3.to_checksum_address(LICENSING_MODULE),
        abi=LICENSING_MODULE_ABI
    )

    # License terms with custom URI
    # Same parameters as ID 28437, but with uri pointing to our metadata
    license_terms = (
        True,  # transferable
        Web3.to_checksum_address(ROYALTY_POLICY_LAP),  # royaltyPolicy
        w3.to_wei(0.005, 'ether'),  # defaultMintingFee (0.005 IP)
        0,  # expiration (0 = never)
        True,  # commercialUse
        True,  # commercialAttribution
        "0x0000000000000000000000000000000000000000",  # commercializerChecker
        b"",  # commercializerCheckerData
        900,  # commercialRevShare (9% = 900 basis points)
        0,  # commercialRevCeiling
        True,  # derivativesAllowed
        True,  # derivativesAttribution
        False,  # derivativesApproval
        True,  # derivativesReciprocal
        0,  # derivativeRevCeiling
        Web3.to_checksum_address(WIP_TOKEN),  # currency (WIP)
        LICENSE_TERMS_URI  # uri - CUSTOM METADATA!
    )

    print("\n" + "-" * 60)
    print("License Terms Configuration:")
    print("-" * 60)
    print(f"  Minting Fee: 0.005 IP")
    print(f"  Revenue Share: 9%")
    print(f"  Commercial Use: Yes")
    print(f"  Derivatives: Yes (with attribution)")
    print(f"  URI: {LICENSE_TERMS_URI}")

    # Register new license terms
    print("\n" + "-" * 60)
    print("Step 1: Registering License Terms...")
    print("-" * 60)

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = pil_template.functions.registerLicenseTerms(
            license_terms
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

        if receipt['status'] != 1:
            print("  [ERROR] Registration failed")
            print(f"  Check: https://explorer.story.foundation/tx/{tx_hash.hex()}")
            sys.exit(1)

        # Extract license terms ID from logs
        new_terms_id = None
        for log in receipt['logs']:
            # Look for LicenseTermsRegistered event
            if len(log['topics']) > 1:
                try:
                    new_terms_id = int(log['topics'][1].hex(), 16)
                    print(f"  New License Terms ID: {new_terms_id}")
                    break
                except:
                    pass

        if not new_terms_id:
            print("  [WARN] Could not extract terms ID from logs")
            print(f"  Check TX: https://explorer.story.foundation/tx/{tx_hash.hex()}")

    except Exception as e:
        error_str = str(e)
        if "already registered" in error_str.lower() or "exists" in error_str.lower():
            print("  [INFO] These terms may already exist")
        else:
            print(f"  [ERROR] {e}")
            sys.exit(1)

    # Attach to IP Asset
    if new_terms_id:
        print("\n" + "-" * 60)
        print("Step 2: Attaching to IP Asset...")
        print("-" * 60)
        print(f"  IP Asset: {IP_ASSET_ID}")
        print(f"  Terms ID: {new_terms_id}")

        try:
            nonce = w3.eth.get_transaction_count(account.address)

            tx = licensing_module.functions.attachLicenseTerms(
                Web3.to_checksum_address(IP_ASSET_ID),
                Web3.to_checksum_address(PIL_LICENSE_TEMPLATE),
                new_terms_id
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
                print("  License terms attached successfully!")
            else:
                print("  [WARN] Attachment may have failed")
                print(f"  Check: https://explorer.story.foundation/tx/{tx_hash.hex()}")

        except Exception as e:
            print(f"  [ERROR] {e}")

    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    if new_terms_id:
        print(f"\n  New License Terms ID: {new_terms_id}")
        print(f"  Metadata URI: {LICENSE_TERMS_URI}")
        print(f"\n  Story Explorer: https://explorer.story.foundation/ipa/{IP_ASSET_ID}")
        print("\n  Note: Old terms (ID 28437) remain attached. Users can choose either.")


if __name__ == "__main__":
    main()
