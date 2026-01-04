#!/usr/bin/env python3
"""
Test License Purchase / Verify Payment Routing

This script verifies the license minting configuration and can perform
a test purchase to confirm payment routing.

Usage:
    python scripts/test_license_purchase.py --private-key 0x... [--mint]
"""

import argparse
import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses
LICENSING_MODULE = "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f"
PIL_LICENSE_TEMPLATE = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316"
LICENSE_TOKEN = "0xFe3838BFb30B34170F00030B52eA4893d8aAC6bC"
WIP_TOKEN = "0x1514000000000000000000000000000000000000"
SPG_NFT_COLLECTION = "0x6f1E5AfAC39cBDAa47d22df56A960F2172FbD7a5"

# IP Asset and License Terms
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"
LICENSE_TERMS_ID = 28438  # New terms with custom URI
MINT_FEE = Web3.to_wei(0.005, 'ether')

# Expected recipient
EXPECTED_RECIPIENT = "0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418"

# ABIs
SPGNFT_ABI = [
    {
        "inputs": [],
        "name": "mintFee",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "mintFeeRecipient",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "mintFeeToken",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

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
                    {"name": "uri", "type": "string"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

LICENSING_MODULE_ABI = [
    {
        "inputs": [
            {"name": "licensorIpId", "type": "address"},
            {"name": "licenseTemplate", "type": "address"},
            {"name": "licenseTermsId", "type": "uint256"},
            {"name": "amount", "type": "uint256"},
            {"name": "receiver", "type": "address"},
            {"name": "royaltyContext", "type": "bytes"},
            {"name": "maxMintingFee", "type": "uint256"},
            {"name": "maxRevenueShare", "type": "uint32"}
        ],
        "name": "mintLicenseTokens",
        "outputs": [{"name": "startLicenseTokenId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

WIP_TOKEN_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
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
    parser = argparse.ArgumentParser(description="Test License Purchase")
    parser.add_argument("--private-key", help="Private key")
    parser.add_argument("--mint", action="store_true", help="Actually mint a license (costs 0.005 IP)")
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
    print("License Purchase Configuration Check")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    balance = w3.eth.get_balance(account.address)
    print(f"Balance: {w3.from_wei(balance, 'ether')} IP")

    # Get contracts
    spg_nft = w3.eth.contract(
        address=Web3.to_checksum_address(SPG_NFT_COLLECTION),
        abi=SPGNFT_ABI
    )
    pil_template = w3.eth.contract(
        address=Web3.to_checksum_address(PIL_LICENSE_TEMPLATE),
        abi=PIL_TEMPLATE_ABI
    )
    licensing_module = w3.eth.contract(
        address=Web3.to_checksum_address(LICENSING_MODULE),
        abi=LICENSING_MODULE_ABI
    )
    wip_token = w3.eth.contract(
        address=Web3.to_checksum_address(WIP_TOKEN),
        abi=WIP_TOKEN_ABI
    )

    # Check SPG NFT Collection settings
    print("\n" + "-" * 60)
    print("SPG NFT Collection Settings:")
    print("-" * 60)
    print(f"  Collection: {SPG_NFT_COLLECTION}")

    try:
        mint_fee = spg_nft.functions.mintFee().call()
        print(f"  Mint Fee: {w3.from_wei(mint_fee, 'ether')} IP")
    except Exception as e:
        print(f"  Mint Fee: Could not read ({e})")

    try:
        mint_fee_recipient = spg_nft.functions.mintFeeRecipient().call()
        print(f"  Mint Fee Recipient: {mint_fee_recipient}")
        if mint_fee_recipient.lower() == EXPECTED_RECIPIENT.lower():
            print("  ✓ Recipient matches your wallet!")
        else:
            print(f"  ✗ Expected: {EXPECTED_RECIPIENT}")
    except Exception as e:
        print(f"  Mint Fee Recipient: Could not read ({e})")

    try:
        mint_fee_token = spg_nft.functions.mintFeeToken().call()
        print(f"  Mint Fee Token: {mint_fee_token}")
        if mint_fee_token.lower() == WIP_TOKEN.lower():
            print("  ✓ Token is WIP (Wrapped IP)")
    except Exception as e:
        print(f"  Mint Fee Token: Could not read ({e})")

    # Check License Terms
    print("\n" + "-" * 60)
    print(f"License Terms (ID: {LICENSE_TERMS_ID}):")
    print("-" * 60)

    try:
        terms = pil_template.functions.getLicenseTerms(LICENSE_TERMS_ID).call()
        print(f"  Transferable: {terms[0]}")
        print(f"  Royalty Policy: {terms[1]}")
        print(f"  Default Minting Fee: {w3.from_wei(terms[2], 'ether')} IP")
        print(f"  Commercial Use: {terms[4]}")
        print(f"  Commercial Rev Share: {terms[8] / 100}%")
        print(f"  Derivatives Allowed: {terms[10]}")
        print(f"  Currency: {terms[15]}")
        print(f"  URI: {terms[16][:50]}..." if len(terms[16]) > 50 else f"  URI: {terms[16]}")
    except Exception as e:
        print(f"  Could not read terms: {e}")

    # Summary
    print("\n" + "-" * 60)
    print("Payment Routing Summary:")
    print("-" * 60)
    print(f"  IP Asset: {IP_ASSET_ID}")
    print(f"  License Terms ID: {LICENSE_TERMS_ID}")
    print(f"  Minting Fee: 0.005 IP (paid in WIP)")
    print(f"  Fee Recipient: {EXPECTED_RECIPIENT}")
    print(f"  Revenue Share: 9% (on commercial use)")

    # Test mint if requested
    if args.mint:
        print("\n" + "=" * 60)
        print("PERFORMING TEST MINT")
        print("=" * 60)

        # Check WIP balance
        wip_balance = wip_token.functions.balanceOf(account.address).call()
        print(f"\nWIP Balance: {w3.from_wei(wip_balance, 'ether')} WIP")

        if wip_balance < MINT_FEE:
            print("\nWrapping IP to WIP...")
            try:
                nonce = w3.eth.get_transaction_count(account.address)
                tx = wip_token.functions.deposit().build_transaction({
                    'from': account.address,
                    'value': MINT_FEE,
                    'nonce': nonce,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price,
                    'chainId': CHAIN_ID,
                })
                signed = w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                print(f"  Wrap TX: {tx_hash.hex()}")
                w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                print("  Wrapped successfully!")
            except Exception as e:
                print(f"  [ERROR] Wrap failed: {e}")
                sys.exit(1)

        # Approve LicensingModule to spend WIP
        print("\nApproving LicensingModule...")
        try:
            nonce = w3.eth.get_transaction_count(account.address)
            # Approve a large amount to cover fee + any royalty
            approve_amount = MINT_FEE * 10
            tx = wip_token.functions.approve(
                Web3.to_checksum_address(LICENSING_MODULE),
                approve_amount
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': CHAIN_ID,
            })
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  Approve TX: {tx_hash.hex()}")
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print("  Approved LicensingModule!")
        except Exception as e:
            print(f"  [ERROR] Approve failed: {e}")
            sys.exit(1)

        # Also approve RoyaltyPolicyLAP
        print("\nApproving RoyaltyPolicyLAP...")
        try:
            nonce = w3.eth.get_transaction_count(account.address)
            tx = wip_token.functions.approve(
                Web3.to_checksum_address("0xBe54FB168b3c982b7AaE60dB6CF75Bd8447b390E"),
                approve_amount
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 100000,
                'gasPrice': w3.eth.gas_price,
                'chainId': CHAIN_ID,
            })
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  Approve TX: {tx_hash.hex()}")
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print("  Approved RoyaltyPolicyLAP!")
        except Exception as e:
            print(f"  [WARN] RoyaltyPolicy approve failed: {e}")

        # Get recipient balance before
        recipient_balance_before = w3.eth.get_balance(Web3.to_checksum_address(EXPECTED_RECIPIENT))
        print(f"\nRecipient balance before: {w3.from_wei(recipient_balance_before, 'ether')} IP")

        # Mint license token
        print("\nMinting license token...")
        try:
            nonce = w3.eth.get_transaction_count(account.address)
            # Parameters: licensorIpId, licenseTemplate, licenseTermsId, amount, receiver, royaltyContext, maxMintingFee, maxRevenueShare
            tx = licensing_module.functions.mintLicenseTokens(
                Web3.to_checksum_address(IP_ASSET_ID),
                Web3.to_checksum_address(PIL_LICENSE_TEMPLATE),
                LICENSE_TERMS_ID,
                1,  # amount
                account.address,  # receiver
                b"",  # royaltyContext (empty for PIL)
                MINT_FEE * 10,  # maxMintingFee - set much higher to allow for variations
                100  # maxRevenueShare - 100% (as percentage, not basis points)
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 800000,  # More gas for complex operation
                'gasPrice': w3.eth.gas_price,
                'chainId': CHAIN_ID,
            })
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  Mint TX: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt['status'] == 1:
                print("  License minted successfully!")
                print(f"  Explorer: https://explorer.story.foundation/tx/{tx_hash.hex()}")
            else:
                print("  [ERROR] Mint failed")
                print(f"  Check: https://explorer.story.foundation/tx/{tx_hash.hex()}")
                sys.exit(1)

        except Exception as e:
            print(f"  [ERROR] Mint failed: {e}")
            sys.exit(1)

        # Check recipient balance after
        recipient_balance_after = w3.eth.get_balance(Web3.to_checksum_address(EXPECTED_RECIPIENT))
        print(f"\nRecipient balance after: {w3.from_wei(recipient_balance_after, 'ether')} IP")

        balance_change = recipient_balance_after - recipient_balance_before
        print(f"Balance change: {w3.from_wei(balance_change, 'ether')} IP")

        if balance_change > 0:
            print("\n✓ Payment received! Routing works correctly.")
        else:
            print("\n[INFO] Balance unchanged - fee may be in WIP, not native IP")
            print("       Check WIP balance or royalty vault for the payment")

    else:
        print("\n" + "-" * 60)
        print("To perform a test mint (costs 0.005 IP), run:")
        print(f"  python scripts/test_license_purchase.py --private-key 0x... --mint")
        print("-" * 60)


if __name__ == "__main__":
    main()
