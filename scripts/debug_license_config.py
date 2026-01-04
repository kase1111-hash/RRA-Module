#!/usr/bin/env python3
"""
Debug License Configuration

Check if there's a licensing config or hook that might be blocking license minting.
"""

import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"

# Contract addresses
LICENSING_MODULE = "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f"
PIL_LICENSE_TEMPLATE = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316"

# IP Asset
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"
LICENSE_TERMS_ID = 28438

# ABI for checking license config
LICENSING_MODULE_ABI = [
    {
        "inputs": [
            {"name": "ipId", "type": "address"},
            {"name": "licenseTemplate", "type": "address"},
            {"name": "licenseTermsId", "type": "uint256"}
        ],
        "name": "getLicensingConfig",
        "outputs": [
            {
                "components": [
                    {"name": "isSet", "type": "bool"},
                    {"name": "mintingFee", "type": "uint256"},
                    {"name": "licensingHook", "type": "address"},
                    {"name": "hookData", "type": "bytes"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "licensorIpId", "type": "address"},
            {"name": "licenseTemplate", "type": "address"},
            {"name": "licenseTermsId", "type": "uint256"}
        ],
        "name": "predictMintingLicenseFee",
        "outputs": [
            {"name": "currencyToken", "type": "address"},
            {"name": "tokenAmount", "type": "uint256"}
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

    licensing_module = w3.eth.contract(
        address=Web3.to_checksum_address(LICENSING_MODULE),
        abi=LICENSING_MODULE_ABI
    )

    ip_asset = Web3.to_checksum_address(IP_ASSET_ID)
    template = Web3.to_checksum_address(PIL_LICENSE_TEMPLATE)

    # Check licensing config
    print(f"\nIP Asset: {ip_asset}")
    print(f"License Terms ID: {LICENSE_TERMS_ID}")

    print("\n" + "-" * 60)
    print("Licensing Config:")
    print("-" * 60)

    try:
        config = licensing_module.functions.getLicensingConfig(
            ip_asset,
            template,
            LICENSE_TERMS_ID
        ).call()
        print(f"  isSet: {config[0]}")
        print(f"  mintingFee: {w3.from_wei(config[1], 'ether')} IP")
        print(f"  licensingHook: {config[2]}")
        if config[2] != "0x0000000000000000000000000000000000000000":
            print("  ⚠️  A licensing hook is set! This may be blocking mints.")
        print(f"  hookData: {config[3].hex() if config[3] else '(empty)'}")
    except Exception as e:
        print(f"  Could not read config: {e}")

    # Check predicted minting fee
    print("\n" + "-" * 60)
    print("Predicted Minting Fee:")
    print("-" * 60)

    try:
        fee = licensing_module.functions.predictMintingLicenseFee(
            ip_asset,
            template,
            LICENSE_TERMS_ID
        ).call()
        print(f"  Currency: {fee[0]}")
        print(f"  Amount: {w3.from_wei(fee[1], 'ether')} tokens")
    except Exception as e:
        print(f"  Could not predict fee: {e}")

    # Also check terms ID 28437 (the original)
    print("\n" + "-" * 60)
    print("Checking Original Terms (ID 28437):")
    print("-" * 60)

    try:
        config = licensing_module.functions.getLicensingConfig(
            ip_asset,
            template,
            28437
        ).call()
        print(f"  isSet: {config[0]}")
        print(f"  mintingFee: {w3.from_wei(config[1], 'ether')} IP")
        print(f"  licensingHook: {config[2]}")
        print(f"  hookData: {config[3].hex() if config[3] else '(empty)'}")
    except Exception as e:
        print(f"  Could not read config: {e}")

    try:
        fee = licensing_module.functions.predictMintingLicenseFee(
            ip_asset,
            template,
            28437
        ).call()
        print(f"  Predicted Fee Currency: {fee[0]}")
        print(f"  Predicted Fee Amount: {w3.from_wei(fee[1], 'ether')} tokens")
    except Exception as e:
        print(f"  Could not predict fee: {e}")


if __name__ == "__main__":
    main()
