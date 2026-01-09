#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Register License Terms with Native IP Payment

Creates new license terms that accept native IP token payment (not WIP),
making it simpler for buyers to purchase licenses.

Usage:
    set STORY_PRIVATE_KEY=0x...
    python scripts/register_native_ip_terms.py
"""

import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses
PIL_TEMPLATE = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316"
LICENSING_MODULE = "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f"
ROYALTY_POLICY_LAP = "0xBe54FB168b3c982b7AaE60dB6CF75Bd8447b390E"

# Payment addresses
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"  # Native IP
WIP_TOKEN = "0x1514000000000000000000000000000000000000"    # Wrapped IP

# IP Asset to attach terms to
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"

# License configuration
MINTING_FEE_WEI = 5000000000000000  # 0.005 IP
REVENUE_SHARE_BPS = 900  # 9% (basis points)


def main():
    private_key = os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Set STORY_PRIVATE_KEY environment variable")
        print("Usage: set STORY_PRIVATE_KEY=0x... && python scripts/register_native_ip_terms.py")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect to Story Protocol")
        sys.exit(1)

    account = w3.eth.account.from_key(private_key)

    print("=" * 60)
    print("Register Native IP License Terms")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} IP")
    print(f"IP Asset: {IP_ASSET_ID}")
    print(f"Minting Fee: {MINTING_FEE_WEI / 10**18} IP")
    print(f"Revenue Share: {REVENUE_SHARE_BPS / 100}%")
    print(f"Currency: Native IP (zero address)")

    # PILTemplate ABI
    pil_template_abi = [
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
                        {"name": "uri", "type": "string"},
                    ],
                    "name": "terms",
                    "type": "tuple",
                }
            ],
            "name": "registerLicenseTerms",
            "outputs": [{"name": "selectedLicenseTermsId", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
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
                        {"name": "uri", "type": "string"},
                    ],
                    "name": "terms",
                    "type": "tuple",
                }
            ],
            "name": "getLicenseTermsId",
            "outputs": [{"name": "selectedLicenseTermsId", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    # LicensingModule ABI
    licensing_module_abi = [
        {
            "inputs": [
                {"name": "ipId", "type": "address"},
                {"name": "licenseTemplate", "type": "address"},
                {"name": "licenseTermsId", "type": "uint256"},
            ],
            "name": "attachLicenseTerms",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        }
    ]

    pil_template = w3.eth.contract(
        address=Web3.to_checksum_address(PIL_TEMPLATE),
        abi=pil_template_abi
    )

    licensing_module = w3.eth.contract(
        address=Web3.to_checksum_address(LICENSING_MODULE),
        abi=licensing_module_abi
    )

    # Build PIL terms with NATIVE IP (zero address)
    pil_terms = (
        True,                                              # transferable
        Web3.to_checksum_address(ROYALTY_POLICY_LAP),     # royaltyPolicy
        MINTING_FEE_WEI,                                  # defaultMintingFee
        0,                                                 # expiration (0 = never)
        True,                                              # commercialUse
        True,                                              # commercialAttribution
        Web3.to_checksum_address(ZERO_ADDRESS),           # commercializerChecker
        b"",                                               # commercializerCheckerData
        REVENUE_SHARE_BPS,                                # commercialRevShare (basis points)
        0,                                                 # commercialRevCeiling (0 = unlimited)
        True,                                              # derivativesAllowed
        True,                                              # derivativesAttribution
        False,                                             # derivativesApproval
        False,                                             # derivativesReciprocal
        0,                                                 # derivativeRevCeiling (0 = unlimited)
        Web3.to_checksum_address(ZERO_ADDRESS),           # currency = NATIVE IP
        "",                                                # uri
    )

    # Step 1: Check if terms already exist
    print("\n" + "-" * 60)
    print("Step 1: Checking if terms already exist...")
    print("-" * 60)

    license_terms_id = None
    try:
        existing_id = pil_template.functions.getLicenseTermsId(pil_terms).call()
        print(f"  getLicenseTermsId returned: {existing_id}")
        if existing_id > 0:
            print(f"  Terms already exist with ID: {existing_id}")
            license_terms_id = existing_id
        else:
            print("  Terms don't exist yet (ID = 0)")
    except Exception as e:
        print(f"  Error checking existing terms: {e}")

    # Step 2: Register terms if needed
    if license_terms_id is None:
        print("\n" + "-" * 60)
        print("Step 2: Registering new license terms...")
        print("-" * 60)

        try:
            nonce = w3.eth.get_transaction_count(account.address)
            tx = pil_template.functions.registerLicenseTerms(pil_terms).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gas": 500000,
                "gasPrice": w3.eth.gas_price,
                "chainId": CHAIN_ID,
            })

            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  TX: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt["status"] == 1:
                license_terms_id = pil_template.functions.getLicenseTermsId(pil_terms).call()
                print(f"  SUCCESS! License Terms ID: {license_terms_id}")
            else:
                print("  FAILED! Transaction reverted")
                sys.exit(1)
        except Exception as e:
            print(f"  ERROR: {e}")
            sys.exit(1)
    else:
        print("\n  Skipping registration (terms already exist)")

    # Step 3: Attach terms to IP Asset
    print("\n" + "-" * 60)
    print("Step 3: Attaching terms to IP Asset...")
    print("-" * 60)

    try:
        nonce = w3.eth.get_transaction_count(account.address)
        tx = licensing_module.functions.attachLicenseTerms(
            Web3.to_checksum_address(IP_ASSET_ID),
            Web3.to_checksum_address(PIL_TEMPLATE),
            license_terms_id,
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 500000,
            "gasPrice": w3.eth.gas_price,
            "chainId": CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt["status"] == 1:
            print("  SUCCESS! Terms attached to IP Asset")
        else:
            print("  Terms may already be attached (transaction reverted)")
    except Exception as e:
        if "already attached" in str(e).lower() or "revert" in str(e).lower():
            print("  Terms may already be attached")
        else:
            print(f"  ERROR: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"\n  License Terms ID: {license_terms_id}")
    print(f"  IP Asset: {IP_ASSET_ID}")
    print(f"  Payment: Native IP (0.005 IP)")
    print(f"\n  UPDATE buy-license.html:")
    print(f"    licenseTermsId: {license_terms_id}")
    print(f"\n  StoryScan: https://www.storyscan.io/ipa/{IP_ASSET_ID}")


if __name__ == "__main__":
    main()
