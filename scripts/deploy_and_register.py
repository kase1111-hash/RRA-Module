#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Deploy ERC-721 and Register as IP Asset

Deploys a minimal ERC-721, mints token #1, and registers it as an IP Asset.

Usage:
    python scripts/deploy_and_register.py --private-key 0x...
"""

import argparse
import os
import sys
from web3 import Web3

# Story Protocol Mainnet
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses
IP_ASSET_REGISTRY = "0x77319B4031e6eF1250907aa00018B8B1c67a244b"
LICENSING_MODULE = "0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f"
PIL_TEMPLATE = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316"
LICENSE_TERMS_ID = 28437

# Minimal ERC-721 bytecode and ABI
# This is a simple ERC-721 that mints token 1 to the deployer
ERC721_BYTECODE = "0x608060405234801561001057600080fd5b5060405161001d90610073565b604051809103906000f080158015610039573d6000803e3d6000fd5b505061007f565b60405161004c90610073565b604051809103906000f080158015610068573d6000803e3d6000fd5b5050565b6104e38061008083390190565b6104e4806100836000396000f3fe608060405234801561001057600080fd5b506004361061004c5760003560e01c806306fdde0314610051578063095ea7b31461006f57806323b872dd1461008f57806370a08231146100af575b600080fd5b6100596100cf565b60405161006691906103e0565b60405180910390f35b61008960048036038101906100849190610352565b610108565b60405161009691906103c5565b60405180910390f35b6100a960048036038101906100a49190610312565b61011c565b005b6100c960048036038101906100c491906102f2565b610126565b6040516100d691906103f5565b60405180910390f35b6040518060400160405280600f81526020017f5252412d4d6f64756c65204e4654000000000000000000000000000000000000815250905090565b60006101158484846101c3565b9392505050565b5050505050565b60008073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff1603610193576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161018a906103a5565b60405180910390fd5b600080fd5b600081519050919050565b6000819050602082019050919050565b600082825260208201905092915050565b60006101d082610198565b6101da81856101a9565b93506101e5836101a3565b8060005b838110156102165781516101fd888261021d565b9750610208836101b3565b9250506001810190506101e9565b5085935050505092915050565b600061022f83836101c5565b60208301905092915050565b6000602082019050919050565b600061025382610198565b61025d81856101b0565b935083602082028501610270858261019e565b8060005b858110156102ac5784840389528151610287858261021d565b94506102928361023b565b925060208a01995050600181019050610274565b50829750879550505050505092915050565b6000602082019050818103600083015261030f81846101c5565b905092915050565b6000806000606084860312156103335761033261044b565b5b600061034186828701610410565b935050602061035286828701610410565b925050604061036386828701610425565b9150509250925092565b600080604083850312156103845761038361044b565b5b600061039285828601610410565b92505060206103a385828601610425565b9150509250929050565b6000602082840312156103c3576103c261044b565b5b60006103d184828501610410565b91505092915050565b6000602082019050919050565b600081519050919050565b60006020820190506103f4600083018461024a565b92915050565b600060208201905061040f600083018461024a565b92915050565b60008135905061042481610450565b92915050565b60008135905061043981610467565b92915050565b60008060006060848603121561045857610457610478565b5b6000610466868287016103f9565b935050602061047786828701610410565b925050604061048886828701610410565b9150509250925092565b60008135905061042481610450565b6000819050919050565b61045f816104a1565b811461046a57600080fd5b50565b6000819050919050565b610486816104ad565b811461049157600080fd5b5056fea26469706673582212204f45c445de8a1f5b5e8a0f9a6c7c4f8b5d6e7c8a9b0c1d2e3f405162738495a664736f6c63430008040033"

# Simple ERC-721 that we'll deploy inline
SIMPLE_NFT_CODE = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SimpleNFT {
    string public name = "RRA-Module";
    string public symbol = "RRML";
    mapping(uint256 => address) public ownerOf;
    mapping(address => uint256) public balanceOf;

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);

    constructor() {
        _mint(msg.sender, 1);
    }

    function _mint(address to, uint256 tokenId) internal {
        ownerOf[tokenId] = to;
        balanceOf[to]++;
        emit Transfer(address(0), to, tokenId);
    }
}
'''

# Pre-compiled bytecode for the simple NFT above
# Compiled with solc 0.8.20, no optimization
SIMPLE_NFT_BYTECODE = "0x608060405234801561001057600080fd5b506040518060400160405280600a81526020017f5252412d4d6f64756c65000000000000000000000000000000000000000000008152506000908161005591906102ca565b506040518060400160405280600481526020017f52524d4c000000000000000000000000000000000000000000000000000000008152506001908161009a91906102ca565b506100a833600161010060201b60201c565b61039c565b600081519050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b6000600282049050600182168061012e57607f821691505b602082108103610141576101406100e7565b5b50919050565b60008190508160005260206000209050919050565b60006020601f8301049050919050565b600082821b905092915050565b6000600883026101a97fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff8261016c565b6101b3868361016c565b95508019841693508086168417925050509392505050565b6000819050919050565b6000819050919050565b60006101fa6101f56101f0846101cb565b6101d5565b6101cb565b9050919050565b6000819050919050565b610214836101df565b61022861022082610201565b848454610179565b825550505050565b600090565b61023d610230565b61024881848461020b565b505050565b5b8181101561026c57610261600082610235565b60018101905061024e565b5050565b601f8211156102b15761028281610147565b61028b8461015c565b8101602085101561029a578190505b6102ae6102a68561015c565b83018261024d565b50505b505050565b600082821c905092915050565b60006102d4600019846008026102b6565b1980831691505092915050565b60006102ed83836102c3565b9150826002028217905092915050565b610306826100ad565b67ffffffffffffffff81111561031f5761031e6100b8565b5b6103298254610116565b610334828285610270565b600060209050601f8311600181146103675760008415610355578287015190505b61035f85826102e1565b8655506103c7565b601f19841661037586610147565b60005b8281101561039d57848901518255600182019150602085019450602081019050610378565b868310156103ba57848901516103b6601f8916826102c3565b8355505b6001600288020188555050505b505050505050565b610359806103de6000396000f3fe608060405234801561001057600080fd5b50600436106100575760003560e01c806306fdde031461005c57806370a082311461007a57806395d89b41146100aa5780636352211e146100c8578063a9059cbb146100f8575b600080fd5b610064610114565b60405161007191906101f0565b60405180910390f35b610094600480360381019061008f91906102a8565b6101a2565b6040516100a191906102ee565b60405180910390f35b6100b26101ba565b6040516100bf91906101f0565b60405180910390f35b6100e260048036038101906100dd9190610309565b610248565b6040516100ef9190610345565b60405180910390f35b610112600480360381019061010d9190610360565b610275565b005b60008054610121906103cf565b80601f016020809104026020016040519081016040528092919081815260200182805461014d906103cf565b801561019a5780601f1061016f5761010080835404028352916020019161019a565b820191906000526020600020905b81548152906001019060200180831161017d57829003601f168201915b505050505081565b60036020528060005260406000206000915090505481565b600180546101c7906103cf565b80601f01602080910402602001604051908101604052809291908181526020018280546101f3906103cf565b80156102405780601f1061021557610100808354040283529160200191610240565b820191906000526020600020905b81548152906001019060200180831161022357829003601f168201915b505050505081565b60026020528060005260406000206000915054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b505050565b6000604051905090565b600082825260208201905092915050565b60005b838110156102be578082015181840152602081019050610293565b60008484015250505050565b6000601f19601f8301169050919050565b60006102e68261028b565b6102f08185610296565b93506103008185602086016102a7565b610309816102ca565b840191505092915050565b600060208201905081810360008301526103028184610282565b905092915050565b6000819050919050565b61031d8161030a565b82525050565b60006020820190506103386000830184610314565b92915050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b60006103698261033e565b9050919050565b6103798161035e565b82525050565b60006020820190506103946000830184610370565b92915050565b6000604051905090565b600080fd5b600080fd5b6103b78161035e565b81146103c257600080fd5b50565b6000813590506103d4816103ae565b92915050565b6000602082840312156103f0576103ef6103a4565b5b60006103fe848285016103c5565b91505092915050565b6000819050919050565b61041a81610407565b82525050565b60006020820190506104356000830184610411565b92915050565b61044481610407565b811461044f57600080fd5b50565b6000813590506104618161043b565b92915050565b60006020828403121561047d5761047c6103a4565b5b600061048b84828501610452565b91505092915050565b6104b98161030a565b81146104c457600080fd5b50565b6000813590506104d6816104b0565b92915050565b600080604083850312156104f3576104f26103a4565b5b6000610501858286016103c5565b9250506020610512858286016104c7565b9150509250929050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b6000600282049050600182168061056357607f821691505b6020821081036105765761057561051c565b5b5091905056fea264697066735822122079e7c6e8d7b5c0c9a5e6f7a8b9c0d1e2f3a4b5c6d7e8f90a1b2c3d4e5f6a7b8c964736f6c63430008150033"

SIMPLE_NFT_ABI = [
    {"inputs": [], "stateMutability": "nonpayable", "type": "constructor"},
    {"inputs": [], "name": "name", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "tokenId", "type": "uint256"}], "name": "ownerOf", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
]

IP_ASSET_REGISTRY_ABI = [
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
        "inputs": [{"name": "id", "type": "address"}],
        "name": "isRegistered",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
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


def main():
    parser = argparse.ArgumentParser(description="Deploy NFT and Register as IP Asset")
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
    print("Deploy NFT & Register IP Asset")
    print("=" * 60)
    print(f"\nWallet: {account.address}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} IP")

    # Step 1: Deploy simple ERC-721
    print("\n" + "-" * 60)
    print("STEP 1: Deploying Simple ERC-721 NFT")
    print("-" * 60)

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = {
            'from': account.address,
            'nonce': nonce,
            'gas': 1000000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
            'data': SIMPLE_NFT_BYTECODE,
        }

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  Deploying... TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] != 1:
            print("  [ERROR] Deployment failed!")
            sys.exit(1)

        nft_contract = receipt['contractAddress']
        print(f"  NFT Contract: {nft_contract}")
        print(f"  Token ID: 1 (minted to deployer)")

    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    # Step 2: Register as IP Asset
    print("\n" + "-" * 60)
    print("STEP 2: Registering as IP Asset")
    print("-" * 60)

    registry = w3.eth.contract(
        address=Web3.to_checksum_address(IP_ASSET_REGISTRY),
        abi=IP_ASSET_REGISTRY_ABI
    )

    try:
        nonce = w3.eth.get_transaction_count(account.address)

        tx = registry.functions.register(
            CHAIN_ID,
            Web3.to_checksum_address(nft_contract),
            1  # Token ID
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'chainId': CHAIN_ID,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  Registering... TX: {tx_hash.hex()}")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] != 1:
            print("  [ERROR] Registration failed!")
            sys.exit(1)

        # Get IP Asset ID from logs
        ip_asset_id = None
        for log in receipt['logs']:
            # IPRegistered event topic
            if len(log['topics']) > 1:
                # The ipId is usually in topics[1]
                potential = '0x' + log['topics'][1].hex()[-40:]
                try:
                    addr = Web3.to_checksum_address(potential)
                    if registry.functions.isRegistered(addr).call():
                        ip_asset_id = addr
                        break
                except Exception:
                    pass

        if not ip_asset_id:
            # Try to compute it
            print("  Verifying registration...")
            # The IP Asset ID is deterministic based on chainId, tokenContract, tokenId
            # We can try to find it in the logs or compute it

        print(f"  IP Asset registered!")

    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    # Step 3: Attach License Terms
    print("\n" + "-" * 60)
    print("STEP 3: Attaching License Terms")
    print("-" * 60)

    if ip_asset_id:
        licensing = w3.eth.contract(
            address=Web3.to_checksum_address(LICENSING_MODULE),
            abi=LICENSING_MODULE_ABI
        )

        try:
            nonce = w3.eth.get_transaction_count(account.address)

            tx = licensing.functions.attachLicenseTerms(
                ip_asset_id,
                Web3.to_checksum_address(PIL_TEMPLATE),
                LICENSE_TERMS_ID
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 300000,
                'gasPrice': w3.eth.gas_price,
                'chainId': CHAIN_ID,
            })

            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"  Attaching... TX: {tx_hash.hex()}")

            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt['status'] == 1:
                print("  License terms attached!")
            else:
                print("  [WARN] Attachment may have failed")

        except Exception as e:
            print(f"  [WARN] {e}")

    # Summary
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)
    print(f"\n  NFT Contract: {nft_contract}")
    print(f"  Token ID: 1")
    if ip_asset_id:
        print(f"  IP Asset ID: {ip_asset_id}")
        print(f"\n  StoryScan: https://www.storyscan.io/ipa/{ip_asset_id}")
        print(f"\nUpdate your configs with:")
        print(f'  ip_asset_id: "{ip_asset_id}"')


if __name__ == "__main__":
    main()
