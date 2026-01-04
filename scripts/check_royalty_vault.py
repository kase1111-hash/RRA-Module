#!/usr/bin/env python3
"""
Check Royalty Vault Status (Read-Only)

Checks the royalty vault balance and claimable amounts for an IP Asset.

Usage:
    python scripts/check_royalty_vault.py
"""

from web3 import Web3

# Story Protocol Constants
STORY_RPC = "https://mainnet.storyrpc.io"
CHAIN_ID = 1514

# Contract addresses
ROYALTY_MODULE = "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086"
IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"
WIP_TOKEN = "0x1514000000000000000000000000000000000000"
EXPECTED_OWNER = "0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418"

# ABIs
ROYALTY_MODULE_ABI = [
    {
        "inputs": [{"name": "ipId", "type": "address"}],
        "name": "ipRoyaltyVaults",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

ROYALTY_VAULT_ABI = [
    {
        "inputs": [{"name": "token", "type": "address"}],
        "name": "claimableRevenue",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "pendingVaultAmount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "ipId",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "lastSnapshotTimestamp",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def main():
    print("=" * 60)
    print("Royalty Vault Status Check")
    print("=" * 60)

    # Connect
    w3 = Web3(Web3.HTTPProvider(STORY_RPC))
    if not w3.is_connected():
        print("[ERROR] Failed to connect to Story Protocol")
        return

    print(f"\nConnected to Story Protocol Mainnet")
    print(f"IP Asset: {IP_ASSET_ID}")

    # Get Royalty Module
    royalty_module = w3.eth.contract(
        address=Web3.to_checksum_address(ROYALTY_MODULE),
        abi=ROYALTY_MODULE_ABI
    )

    # Get Royalty Vault address
    print("\n" + "-" * 60)
    print("Looking up Royalty Vault...")
    print("-" * 60)

    try:
        vault_address = royalty_module.functions.ipRoyaltyVaults(
            Web3.to_checksum_address(IP_ASSET_ID)
        ).call()
        print(f"  Royalty Vault: {vault_address}")

        if vault_address == "0x0000000000000000000000000000000000000000":
            print("\n[WARNING] No Royalty Vault exists for this IP Asset yet.")
            print("This means no royalties have been paid to this IP Asset.")
            return

    except Exception as e:
        print(f"[ERROR] Failed to get vault: {e}")
        return

    # Get vault contract
    vault = w3.eth.contract(
        address=Web3.to_checksum_address(vault_address),
        abi=ROYALTY_VAULT_ABI
    )

    # Check vault info
    print("\n" + "-" * 60)
    print("Vault Information:")
    print("-" * 60)

    try:
        vault_ip = vault.functions.ipId().call()
        print(f"  IP ID: {vault_ip}")
    except Exception as e:
        print(f"  IP ID: Could not read ({e})")

    try:
        last_snapshot = vault.functions.lastSnapshotTimestamp().call()
        print(f"  Last Snapshot: {last_snapshot}")
    except Exception as e:
        print(f"  Last Snapshot: Could not read ({e})")

    # Check WIP balance of vault
    print("\n" + "-" * 60)
    print("Vault Balances:")
    print("-" * 60)

    wip = w3.eth.contract(
        address=Web3.to_checksum_address(WIP_TOKEN),
        abi=ERC20_ABI
    )

    try:
        wip_balance = wip.functions.balanceOf(vault_address).call()
        print(f"  WIP Balance: {w3.from_wei(wip_balance, 'ether')} WIP")
    except Exception as e:
        print(f"  WIP Balance: Could not read ({e})")

    native_balance = w3.eth.get_balance(vault_address)
    print(f"  Native IP Balance: {w3.from_wei(native_balance, 'ether')} IP")

    # Check claimable revenue
    print("\n" + "-" * 60)
    print("Claimable Revenue:")
    print("-" * 60)

    try:
        pending = vault.functions.pendingVaultAmount().call()
        print(f"  Pending (unsnapshotted): {w3.from_wei(pending, 'ether')}")
    except Exception as e:
        print(f"  Pending: Could not read ({e})")

    try:
        claimable_wip = vault.functions.claimableRevenue(
            Web3.to_checksum_address(WIP_TOKEN)
        ).call()
        print(f"  Claimable WIP: {w3.from_wei(claimable_wip, 'ether')} WIP")
    except Exception as e:
        print(f"  Claimable WIP: Could not read ({e})")

    try:
        claimable_native = vault.functions.claimableRevenue(
            "0x0000000000000000000000000000000000000000"
        ).call()
        print(f"  Claimable Native: {w3.from_wei(claimable_native, 'ether')} IP")
    except Exception as e:
        print(f"  Claimable Native: Could not read ({e})")

    # Check owner wallet balance
    print("\n" + "-" * 60)
    print("Owner Wallet Status:")
    print("-" * 60)

    owner_balance = w3.eth.get_balance(Web3.to_checksum_address(EXPECTED_OWNER))
    print(f"  Owner: {EXPECTED_OWNER}")
    print(f"  IP Balance: {w3.from_wei(owner_balance, 'ether')} IP")

    try:
        owner_wip = wip.functions.balanceOf(
            Web3.to_checksum_address(EXPECTED_OWNER)
        ).call()
        print(f"  WIP Balance: {w3.from_wei(owner_wip, 'ether')} WIP")
    except Exception as e:
        print(f"  WIP Balance: Could not read ({e})")

    print("\n" + "-" * 60)
    print("Summary:")
    print("-" * 60)
    print("  The minting fee (0.005 WIP) was paid directly to the IP owner")
    print("  when the license was minted.")
    print("")
    print("  Royalty payments from commercial use would go to the Royalty")
    print("  Vault and be claimable proportional to Royalty Token holdings.")
    print("")
    print("  To test royalty claiming, someone would need to call")
    print("  payRoyaltyOnBehalf() to pay royalties to this IP Asset.")
    print("-" * 60)


if __name__ == "__main__":
    main()
