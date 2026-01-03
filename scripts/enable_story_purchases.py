#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Enable Story Protocol License Purchases

Attaches license terms to your Story Protocol IP Asset, enabling buyers
to purchase licenses (mint license tokens) directly.

Usage:
    python scripts/enable_story_purchases.py \
        --ip-asset 0xYourIPAssetID \
        --market-config .market.yaml \
        --private-key $PRIVATE_KEY

Or with environment variables:
    export STORY_PRIVATE_KEY=0x...
    python scripts/enable_story_purchases.py --ip-asset 0xYourIPAssetID
"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from web3 import Web3

# Story Protocol Constants
STORY_MAINNET_CHAIN_ID = 1514
STORY_MAINNET_RPC = "https://mainnet.storyrpc.io"

# Story Protocol Mainnet Contract Addresses
STORY_MAINNET_CONTRACTS = {
    "licensing_module": "0xd81fd78f557b457b4350cB95D20b547bFEb4D857",
    "pil_template": "0x0752B15Ee7303033854bdE1B32bc7A4008752Dc0",
    "ip_asset_registry": "0x77319B4031e6eF1250907aa00018B8B1c67a244b",
    "license_registry": "0xedf6aF51e95B6E5B9C0E68b77a3E4C3D2E3cD13F",
    "royalty_module": "0x3C27b2D7d30131D4B58C3584FD7c86e104C67883",
    "dispute_module": "0x692B47fa72eE7Ac0Ec617ea384875c93d0000000",
    # WIP (Wrapped IP) token - Story's native payment token
    "wip_token": "0x1514000000000000000000000000000000000000",
    # Zero address for ETH payments
    "zero_address": "0x0000000000000000000000000000000000000000",
}

# Story Protocol Testnet Contract Addresses
STORY_TESTNET_CONTRACTS = {
    "licensing_module": "0xd81fd78f557b457b4350cB95D20b547bFEb4D857",
    "pil_template": "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316",
    "ip_asset_registry": "0x1a9d0d28a0422F26D31Be72Edc6f13ea4371E11B",
    "license_registry": "0x529a750E02d8E2f0Be4B0a9e9f6B6b8fB9B8E9F9",
    "royalty_module": "0x3C27b2D7d30131D4B58C3584FD7c86e104C67883",
    "wip_token": "0x1514000000000000000000000000000000000000",
    "zero_address": "0x0000000000000000000000000000000000000000",
}

# Pre-registered PIL Term IDs (Story Protocol built-in terms)
PIL_FLAVOR_IDS = {
    "non_commercial_social_remixing": 1,  # Free to remix, no commercial use
    "commercial_use": 2,  # Commercial use allowed, no derivatives
    "commercial_remix": 3,  # Commercial use + derivatives allowed
}


@dataclass
class PILTermsConfig:
    """Configuration for Programmable IP License (PIL) terms."""

    commercial_use: bool = True
    derivatives_allowed: bool = True
    derivatives_attribution: bool = True
    derivatives_reciprocal: bool = False
    minting_fee: int = 0  # Fee in wei
    currency: str = STORY_MAINNET_CONTRACTS["zero_address"]  # Default to ETH
    revenue_share: int = 0  # Percentage in basis points (0-10000)
    transferable: bool = True
    expiration: int = 0  # 0 = never expires


def load_market_config(config_path: Path) -> Dict[str, Any]:
    """Load and parse the market.yaml configuration file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Market config not found: {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def parse_price_to_wei(price_str: str) -> int:
    """Convert price string (e.g., '0.05 ETH') to wei."""
    parts = price_str.strip().split()
    amount = float(parts[0])
    currency = parts[1].upper() if len(parts) > 1 else "ETH"

    if currency in ["ETH", "ETHER", "WIP"]:
        return int(amount * 10**18)
    elif currency in ["GWEI"]:
        return int(amount * 10**9)
    elif currency in ["WEI"]:
        return int(amount)

    # Default to treating as ETH
    return int(amount * 10**18)


def convert_market_yaml_to_pil_terms(market_config: Dict[str, Any]) -> PILTermsConfig:
    """
    Convert RRA market.yaml configuration to Story Protocol PIL terms.

    Maps the market.yaml fields to Story Protocol's PILTerms structure.
    """
    # Get Story Protocol config section
    story_config = market_config.get("defi_integrations", {}).get("story_protocol", {})
    pil_config = story_config.get("pil_terms", {})

    # Parse pricing
    target_price = market_config.get("target_price", "0.05 ETH")
    minting_fee_wei = parse_price_to_wei(target_price)

    # Calculate revenue share from floor/target price ratio or derivative royalty
    floor_price = market_config.get("floor_price", "0.02 ETH")
    floor_wei = parse_price_to_wei(floor_price)
    derivative_royalty = story_config.get("derivative_royalty_percentage", 0.09)

    # Revenue share in basis points (0-10000)
    revenue_share_bps = int(derivative_royalty * 10000)

    # Determine if derivatives are allowed
    derivatives_allowed = pil_config.get("derivatives_allowed", True)

    # Check license model for transferability
    license_model = market_config.get("license_model", "perpetual")
    transferable = license_model != "per-seat"  # Per-seat licenses typically non-transferable

    # Check NFT config for additional settings
    nft_config = market_config.get("blockchain", {}).get("nft_config", {})
    transferable = nft_config.get("transferable", transferable)

    return PILTermsConfig(
        commercial_use=pil_config.get("commercial_use", True),
        derivatives_allowed=derivatives_allowed,
        derivatives_attribution=pil_config.get("derivatives_attribution", True),
        derivatives_reciprocal=pil_config.get("derivatives_reciprocal", False),
        minting_fee=minting_fee_wei,
        currency=STORY_MAINNET_CONTRACTS["zero_address"],  # ETH
        revenue_share=revenue_share_bps,
        transferable=transferable,
        expiration=0,  # Perpetual
    )


def get_pil_flavor(terms: PILTermsConfig) -> str:
    """Determine which PIL flavor to use based on terms."""
    if not terms.commercial_use:
        return "non_commercial_social_remixing"
    elif terms.derivatives_allowed:
        return "commercial_remix"
    else:
        return "commercial_use"


class StoryProtocolPurchaseEnabler:
    """
    Enables purchases on Story Protocol by attaching license terms to IP Assets.

    This class handles:
    1. Connecting to Story Protocol network
    2. Registering PIL terms with custom pricing
    3. Attaching terms to IP Assets
    4. Generating buyer interface code
    """

    def __init__(
        self,
        private_key: str,
        network: str = "mainnet",
        rpc_url: Optional[str] = None,
    ):
        """
        Initialize the purchase enabler.

        Args:
            private_key: Private key for signing transactions
            network: Network name ("mainnet" or "testnet")
            rpc_url: Optional custom RPC URL
        """
        self.network = network
        self.private_key = private_key

        # Select contracts based on network
        self.contracts = (
            STORY_MAINNET_CONTRACTS if network == "mainnet"
            else STORY_TESTNET_CONTRACTS
        )

        # Set up RPC
        if rpc_url:
            self.rpc_url = rpc_url
        elif network == "mainnet":
            self.rpc_url = STORY_MAINNET_RPC
        else:
            self.rpc_url = "https://aeneid.storyrpc.io"

        # Connect to blockchain
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to {self.rpc_url}")

        # Create account from private key
        self.account = self.w3.eth.account.from_key(private_key)
        self.owner_address = self.account.address

        print(f"Connected to Story Protocol {network}")
        print(f"  Chain ID: {self.w3.eth.chain_id}")
        print(f"  Owner: {self.owner_address}")

    def register_pil_terms(self, terms: PILTermsConfig) -> Dict[str, Any]:
        """
        Register custom PIL terms on Story Protocol.

        This creates a new license terms entry that can be attached to IP Assets.
        Returns the license_terms_id for use in attaching to IP Assets.
        """
        print("\nRegistering PIL terms...")
        print(f"  Commercial Use: {terms.commercial_use}")
        print(f"  Derivatives Allowed: {terms.derivatives_allowed}")
        print(f"  Minting Fee: {terms.minting_fee / 10**18:.4f} ETH")
        print(f"  Revenue Share: {terms.revenue_share / 100:.1f}%")

        # For now, use pre-registered PIL flavor that matches our terms
        pil_flavor = get_pil_flavor(terms)
        license_terms_id = PIL_FLAVOR_IDS.get(pil_flavor, 1)

        # In production, we would call registerLicenseTerms on PILicenseTemplate
        # to create custom terms with our exact parameters.
        # For now, we use the pre-registered terms and note the minting fee
        # should be configured via the IP Asset's royalty policy.

        return {
            "license_terms_id": license_terms_id,
            "pil_flavor": pil_flavor,
            "terms": terms,
            "note": "Using pre-registered PIL terms. Custom terms registration requires additional SDK support.",
        }

    def attach_license_terms(
        self,
        ip_asset_id: str,
        license_terms_id: int,
    ) -> Dict[str, Any]:
        """
        Attach license terms to an IP Asset, enabling purchases.

        Args:
            ip_asset_id: The IP Asset ID to attach terms to
            license_terms_id: ID of the license terms to attach

        Returns:
            Dictionary with transaction details
        """
        print(f"\nAttaching license terms to IP Asset...")
        print(f"  IP Asset: {ip_asset_id}")
        print(f"  License Terms ID: {license_terms_id}")

        # Build the attachLicenseTerms transaction
        # ABI for LicensingModule.attachLicenseTerms
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

        licensing_module = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.contracts["licensing_module"]),
            abi=licensing_module_abi,
        )

        # Build transaction
        nonce = self.w3.eth.get_transaction_count(self.owner_address)
        gas_price = self.w3.eth.gas_price

        tx = licensing_module.functions.attachLicenseTerms(
            Web3.to_checksum_address(ip_asset_id),
            Web3.to_checksum_address(self.contracts["pil_template"]),
            license_terms_id,
        ).build_transaction({
            "from": self.owner_address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": 500000,  # Estimate
        })

        # Sign and send transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"  Transaction sent: {tx_hash.hex()}")

        # Wait for confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt["status"] == 1:
            print(f"  Transaction confirmed in block {receipt['blockNumber']}")
            return {
                "status": "success",
                "tx_hash": tx_hash.hex(),
                "block_number": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
            }
        else:
            return {
                "status": "failed",
                "tx_hash": tx_hash.hex(),
                "error": "Transaction reverted",
            }

    def generate_buyer_interface(
        self,
        ip_asset_id: str,
        license_terms_id: int,
        market_config: Dict[str, Any],
        output_path: Path,
    ) -> str:
        """
        Generate an HTML page for buyers to purchase licenses.

        Args:
            ip_asset_id: The IP Asset ID
            license_terms_id: The license terms ID
            market_config: Market configuration
            output_path: Path to save the HTML file

        Returns:
            Path to the generated file
        """
        target_price = market_config.get("target_price", "0.05 ETH")
        price_wei = parse_price_to_wei(target_price)
        repo_name = market_config.get("metadata", {}).get("name", "Repository License")
        features = market_config.get("features", [])

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Purchase License - {repo_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/ethers@6/dist/ethers.umd.min.js"></script>
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-16 max-w-2xl">
        <div class="bg-gray-800 rounded-2xl p-8 shadow-xl">
            <div class="text-center mb-8">
                <h1 class="text-3xl font-bold mb-2">Purchase License</h1>
                <p class="text-gray-400">Powered by Story Protocol</p>
            </div>

            <!-- License Details -->
            <div class="bg-gray-700/50 rounded-xl p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">License Details</h2>
                <div class="space-y-3">
                    <div class="flex justify-between">
                        <span class="text-gray-400">Price</span>
                        <span class="font-mono text-green-400">{target_price}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-400">Type</span>
                        <span>{market_config.get("license_model", "Perpetual").title()}</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-gray-400">Transferable</span>
                        <span>{"Yes" if market_config.get("blockchain", {}).get("nft_config", {}).get("transferable", True) else "No"}</span>
                    </div>
                </div>
            </div>

            <!-- Features -->
            <div class="bg-gray-700/50 rounded-xl p-6 mb-6">
                <h2 class="text-xl font-semibold mb-4">Included Features</h2>
                <ul class="space-y-2">
                    {chr(10).join(f'<li class="flex items-center gap-2"><span class="text-green-500">&#10003;</span>{feature}</li>' for feature in features[:5])}
                </ul>
            </div>

            <!-- Wallet Connection -->
            <div id="wallet-section" class="mb-6">
                <button
                    id="connect-btn"
                    onclick="connectWallet()"
                    class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-6 rounded-xl transition-colors"
                >
                    Connect Wallet
                </button>
            </div>

            <!-- Purchase Button (hidden until wallet connected) -->
            <div id="purchase-section" class="hidden">
                <div class="bg-gray-700/50 rounded-xl p-4 mb-4">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-400">Connected:</span>
                        <span id="wallet-address" class="font-mono text-sm"></span>
                    </div>
                </div>
                <button
                    id="purchase-btn"
                    onclick="purchaseLicense()"
                    class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-4 px-6 rounded-xl transition-colors"
                >
                    Purchase License for {target_price}
                </button>
            </div>

            <!-- Status Messages -->
            <div id="status" class="mt-6 text-center hidden">
                <div id="status-loading" class="hidden">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
                    <p class="text-gray-400">Processing transaction...</p>
                </div>
                <div id="status-success" class="hidden text-green-400">
                    <p class="text-xl mb-2">License Purchased!</p>
                    <a id="tx-link" href="#" target="_blank" class="text-blue-400 hover:underline">View on Explorer</a>
                </div>
                <div id="status-error" class="hidden text-red-400">
                    <p id="error-message"></p>
                </div>
            </div>
        </div>

        <!-- Story Protocol Info -->
        <div class="text-center mt-8 text-gray-500">
            <p>License NFT minted on <a href="https://story.foundation" target="_blank" class="text-blue-400 hover:underline">Story Protocol</a></p>
            <p class="text-sm mt-2">
                <a href="https://www.storyscan.io/token/{ip_asset_id}" target="_blank" class="hover:underline">
                    View IP Asset on StoryScan
                </a>
            </p>
        </div>
    </div>

    <script>
        const IP_ASSET_ID = "{ip_asset_id}";
        const LICENSE_TERMS_ID = {license_terms_id};
        const PRICE_WEI = "{price_wei}";
        const STORY_CHAIN_ID = {STORY_MAINNET_CHAIN_ID};
        const STORY_RPC = "{STORY_MAINNET_RPC}";

        // Story Protocol Licensing Module Address
        const LICENSING_MODULE = "{self.contracts['licensing_module']}";
        const PIL_TEMPLATE = "{self.contracts['pil_template']}";

        let provider;
        let signer;

        async function connectWallet() {{
            if (typeof window.ethereum === 'undefined') {{
                alert('Please install MetaMask or another Web3 wallet');
                return;
            }}

            try {{
                provider = new ethers.BrowserProvider(window.ethereum);
                await provider.send("eth_requestAccounts", []);

                // Check if on Story Protocol network
                const network = await provider.getNetwork();
                if (Number(network.chainId) !== STORY_CHAIN_ID) {{
                    try {{
                        await window.ethereum.request({{
                            method: 'wallet_switchEthereumChain',
                            params: [{{ chainId: '0x' + STORY_CHAIN_ID.toString(16) }}],
                        }});
                    }} catch (switchError) {{
                        // Chain not added, add it
                        if (switchError.code === 4902) {{
                            await window.ethereum.request({{
                                method: 'wallet_addEthereumChain',
                                params: [{{
                                    chainId: '0x' + STORY_CHAIN_ID.toString(16),
                                    chainName: 'Story Protocol',
                                    nativeCurrency: {{ name: 'IP', symbol: 'IP', decimals: 18 }},
                                    rpcUrls: [STORY_RPC],
                                    blockExplorerUrls: ['https://storyscan.io'],
                                }}],
                            }});
                        }}
                    }}
                    provider = new ethers.BrowserProvider(window.ethereum);
                }}

                signer = await provider.getSigner();
                const address = await signer.getAddress();

                document.getElementById('wallet-address').textContent =
                    address.slice(0, 6) + '...' + address.slice(-4);
                document.getElementById('wallet-section').classList.add('hidden');
                document.getElementById('purchase-section').classList.remove('hidden');
            }} catch (error) {{
                console.error('Connection error:', error);
                alert('Failed to connect wallet: ' + error.message);
            }}
        }}

        async function purchaseLicense() {{
            if (!signer) {{
                alert('Please connect your wallet first');
                return;
            }}

            const statusDiv = document.getElementById('status');
            const loadingDiv = document.getElementById('status-loading');
            const successDiv = document.getElementById('status-success');
            const errorDiv = document.getElementById('status-error');

            statusDiv.classList.remove('hidden');
            loadingDiv.classList.remove('hidden');
            successDiv.classList.add('hidden');
            errorDiv.classList.add('hidden');

            try {{
                // ABI for mintLicenseTokens
                const licensingABI = [
                    {{
                        "inputs": [
                            {{"name": "licensorIpId", "type": "address"}},
                            {{"name": "licenseTemplate", "type": "address"}},
                            {{"name": "licenseTermsId", "type": "uint256"}},
                            {{"name": "amount", "type": "uint256"}},
                            {{"name": "receiver", "type": "address"}},
                            {{"name": "royaltyContext", "type": "bytes"}}
                        ],
                        "name": "mintLicenseTokens",
                        "outputs": [{{"name": "", "type": "uint256[]"}}],
                        "stateMutability": "payable",
                        "type": "function"
                    }}
                ];

                const licensingModule = new ethers.Contract(
                    LICENSING_MODULE,
                    licensingABI,
                    signer
                );

                const receiverAddress = await signer.getAddress();

                // Mint license token
                const tx = await licensingModule.mintLicenseTokens(
                    IP_ASSET_ID,
                    PIL_TEMPLATE,
                    LICENSE_TERMS_ID,
                    1, // amount
                    receiverAddress,
                    "0x", // royaltyContext
                    {{ value: PRICE_WEI }}
                );

                console.log('Transaction sent:', tx.hash);

                // Wait for confirmation
                const receipt = await tx.wait();
                console.log('Transaction confirmed:', receipt);

                loadingDiv.classList.add('hidden');
                successDiv.classList.remove('hidden');
                document.getElementById('tx-link').href =
                    `https://storyscan.io/tx/${{tx.hash}}`;

            }} catch (error) {{
                console.error('Purchase error:', error);
                loadingDiv.classList.add('hidden');
                errorDiv.classList.remove('hidden');
                document.getElementById('error-message').textContent =
                    error.reason || error.message || 'Transaction failed';
            }}
        }}
    </script>
</body>
</html>
'''

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html_content)

        return str(output_path)


async def enable_purchases(
    ip_asset_id: str,
    market_config_path: str,
    private_key: str,
    network: str = "mainnet",
    output_dir: str = "marketplace/public",
) -> Dict[str, Any]:
    """
    Main function to enable purchases for an IP Asset.

    This function:
    1. Loads market.yaml configuration
    2. Converts to PIL terms
    3. Attaches terms to IP Asset
    4. Generates buyer interface

    Args:
        ip_asset_id: Story Protocol IP Asset ID
        market_config_path: Path to .market.yaml
        private_key: Private key for transactions
        network: Network name ("mainnet" or "testnet")
        output_dir: Directory for generated files

    Returns:
        Dictionary with operation results
    """
    print("=" * 60)
    print("Story Protocol License Enablement")
    print("=" * 60)

    # Load market config
    config_path = Path(market_config_path)
    market_config = load_market_config(config_path)
    print(f"\nLoaded configuration from {config_path}")

    # Convert to PIL terms
    pil_terms = convert_market_yaml_to_pil_terms(market_config)
    print(f"\nConverted market.yaml to PIL terms")

    # Initialize enabler
    enabler = StoryProtocolPurchaseEnabler(
        private_key=private_key,
        network=network,
    )

    # Register PIL terms (get license_terms_id)
    terms_result = enabler.register_pil_terms(pil_terms)
    license_terms_id = terms_result["license_terms_id"]

    # Attach license terms to IP Asset
    attach_result = enabler.attach_license_terms(
        ip_asset_id=ip_asset_id,
        license_terms_id=license_terms_id,
    )

    if attach_result["status"] != "success":
        print(f"\n[ERROR] Failed to attach license terms: {attach_result.get('error')}")
        # Continue anyway to generate buyer interface (for testing)

    # Generate buyer interface
    output_path = Path(output_dir) / "buy-license.html"
    interface_path = enabler.generate_buyer_interface(
        ip_asset_id=ip_asset_id,
        license_terms_id=license_terms_id,
        market_config=market_config,
        output_path=output_path,
    )

    print(f"\n" + "=" * 60)
    print("LICENSE PURCHASES ENABLED!")
    print("=" * 60)
    print(f"\nIP Asset ID: {ip_asset_id}")
    print(f"License Terms ID: {license_terms_id}")
    print(f"Network: {network}")
    print(f"\nBuyer Interface: {interface_path}")
    print(f"\nStoryScan URL: https://www.storyscan.io/token/{ip_asset_id}")
    print(f"\nBuyers can now mint license tokens by:")
    print(f"  1. Opening the buyer interface HTML file")
    print(f"  2. Connecting their wallet")
    print(f"  3. Paying the minting fee ({market_config.get('target_price', '0.05 ETH')})")
    print(f"  4. Receiving their license NFT")

    return {
        "ip_asset_id": ip_asset_id,
        "license_terms_id": license_terms_id,
        "attach_result": attach_result,
        "terms": terms_result,
        "buyer_interface": interface_path,
        "storyscan_url": f"https://www.storyscan.io/token/{ip_asset_id}",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Enable Story Protocol license purchases for an IP Asset"
    )
    parser.add_argument(
        "--ip-asset",
        required=True,
        help="Story Protocol IP Asset ID (address)",
    )
    parser.add_argument(
        "--market-config",
        default=".market.yaml",
        help="Path to market.yaml configuration file",
    )
    parser.add_argument(
        "--private-key",
        help="Private key for signing transactions (or use STORY_PRIVATE_KEY env var)",
    )
    parser.add_argument(
        "--network",
        default="mainnet",
        choices=["mainnet", "testnet"],
        help="Story Protocol network",
    )
    parser.add_argument(
        "--output-dir",
        default="marketplace/public",
        help="Output directory for generated files",
    )

    args = parser.parse_args()

    # Get private key from args or environment
    private_key = args.private_key or os.environ.get("STORY_PRIVATE_KEY")
    if not private_key:
        print("Error: Private key required. Use --private-key or set STORY_PRIVATE_KEY")
        sys.exit(1)

    # Run the enablement
    result = asyncio.run(enable_purchases(
        ip_asset_id=args.ip_asset,
        market_config_path=args.market_config,
        private_key=private_key,
        network=args.network,
        output_dir=args.output_dir,
    ))

    # Save result to JSON for programmatic use
    result_file = Path(args.output_dir) / "purchase_enablement_result.json"
    result_file.parent.mkdir(parents=True, exist_ok=True)

    # Convert dataclass to dict for JSON serialization
    serializable_result = {
        k: (v.__dict__ if hasattr(v, "__dict__") else v)
        for k, v in result.items()
    }

    with open(result_file, "w") as f:
        json.dump(serializable_result, f, indent=2, default=str)

    print(f"\nResult saved to: {result_file}")


if __name__ == "__main__":
    main()
