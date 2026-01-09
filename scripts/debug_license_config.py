#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Debug License Configuration

Check if license terms are attached and if minting is possible.
"""

import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"

# Contract addresses
LICENSING_MODULE = "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f"
PIL_LICENSE_TEMPLATE = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316"
LICENSE_REGISTRY = "0x529a750E02d8E2f15649c13D69a465286a780e24"

# IP Asset
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"
LICENSE_TERMS_ID = 28438

# ABI for checking license attachment
LICENSE_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "licenseTemplate", "type": "address"},
            {"name": "licenseTermsId", "type": "uint256"}
        ],
        "name": "hasIpAttachedLicenseTerms",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "ipId", "type": "address"}],
        "name": "getAttachedLicenseTermsCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "index", "type": "uint256"}
        ],
        "name": "getAttachedLicenseTerms",
        "outputs": [
            {"name": "licenseTemplate", "type": "address"},
            {"name": "licenseTermsId", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

def main():
    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("Failed to connect")
        sys.exit(1)

    print("=" * 60)
    print("Debug License Configuration")
    print("=" * 60)

    license_registry = w3.eth.contract(
        address=Web3.to_checksum_address(LICENSE_REGISTRY),
        abi=LICENSE_REGISTRY_ABI
    )

    ip_asset = Web3.to_checksum_address(IP_ASSET_ID)
    template = Web3.to_checksum_address(PIL_LICENSE_TEMPLATE)

    print(f"\nIP Asset: {ip_asset}")

    # Check how many license terms are attached
    print("\n" + "-" * 60)
    print("Attached License Terms:")
    print("-" * 60)

    try:
        count = license_registry.functions.getAttachedLicenseTermsCount(ip_asset).call()
        print(f"  Count: {count}")

        for i in range(count):
            terms = license_registry.functions.getAttachedLicenseTerms(ip_asset, i).call()
            print(f"  [{i}] Template: {terms[0]}, Terms ID: {terms[1]}")
    except Exception as e:
        print(f"  Could not read attached terms: {e}")

    # Check specific terms
    print("\n" + "-" * 60)
    print(f"Checking Terms ID {LICENSE_TERMS_ID}:")
    print("-" * 60)

    try:
        has_terms = license_registry.functions.hasIpAttachedLicenseTerms(
            ip_asset, template, LICENSE_TERMS_ID
        ).call()
        print(f"  Has terms {LICENSE_TERMS_ID} attached: {has_terms}")
    except Exception as e:
        print(f"  Could not check: {e}")

    # Check original terms
    print("\n" + "-" * 60)
    print("Checking Original Terms ID 28437:")
    print("-" * 60)

    try:
        has_terms = license_registry.functions.hasIpAttachedLicenseTerms(
            ip_asset, template, 28437
        ).call()
        print(f"  Has terms 28437 attached: {has_terms}")
    except Exception as e:
        print(f"  Could not check: {e}")

    # Check license terms details from PILTemplate
    print("\n" + "-" * 60)
    print("License Terms Details (ID 28437):")
    print("-" * 60)

    PIL_TEMPLATE_ABI = [
        {
            "inputs": [{"name": "licenseTermsId", "type": "uint256"}],
            "name": "getLicenseTerms",
            "outputs": [
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
            "stateMutability": "view",
            "type": "function"
        }
    ]

    pil_template = w3.eth.contract(
        address=Web3.to_checksum_address(PIL_LICENSE_TEMPLATE),
        abi=PIL_TEMPLATE_ABI
    )

    try:
        terms = pil_template.functions.getLicenseTerms(28437).call()
        print(f"  Transferable: {terms[0]}")
        print(f"  Royalty Policy: {terms[1]}")
        print(f"  Minting Fee: {terms[2]} wei ({terms[2] / 10**18} IP)")
        print(f"  Currency: {terms[15]}")
        print(f"  Commercial Use: {terms[4]}")
        print(f"  Derivatives Allowed: {terms[10]}")
        print(f"  Revenue Share: {terms[8] / 100}%")

        # Check currency
        if terms[15] == "0x0000000000000000000000000000000000000000":
            print("\n  >> Payment: Native IP (send value with transaction)")
        elif terms[15] == "0x1514000000000000000000000000000000000000":
            print("\n  >> Payment: WIP Token (need to approve + no value)")
        else:
            print(f"\n  >> Payment: ERC20 token at {terms[15]}")
    except Exception as e:
        print(f"  Could not get terms: {e}")


if __name__ == "__main__":
    main()
