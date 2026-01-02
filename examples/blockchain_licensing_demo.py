#!/usr/bin/env python3
#
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Blockchain Licensing Demonstration

This script demonstrates the complete integration between:
1. FSL-1.1-ALv2 license (legal foundation)
2. SPDX headers (machine-readable licensing)
3. .market.yaml configuration (blockchain monetization)
4. Smart contracts (on-chain enforcement)
5. AI agents (automated negotiation)

This shows how GitHub work is automatically monetized on the blockchain.
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta


class BlockchainLicensingDemo:
    """Demonstrates the blockchain licensing integration."""

    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.license_file = self.repo_root / "LICENSE.md"
        self.market_config = self.repo_root / ".market.yaml"

    def load_market_config(self):
        """Load the .market.yaml configuration."""
        if not self.market_config.exists():
            print("❌ .market.yaml not found")
            return None

        with open(self.market_config, 'r') as f:
            return yaml.safe_load(f)

    def verify_license_file(self):
        """Verify LICENSE.md contains FSL-1.1-ALv2."""
        if not self.license_file.exists():
            return False, "LICENSE.md not found"

        with open(self.license_file, 'r') as f:
            content = f.read()

        checks = [
            ("FSL-1.1-ALv2" in content, "FSL-1.1-ALv2 identifier"),
            ("Copyright 2025 Kase Branham" in content, "Copyright notice"),
            ("Apache License, Version 2.0" in content, "Future license grant"),
        ]

        for passed, desc in checks:
            if not passed:
                return False, f"Missing: {desc}"

        return True, "All license components present"

    def verify_spdx_headers(self):
        """Verify Python files have SPDX headers."""
        src_dir = self.repo_root / "src"
        python_files = list(src_dir.rglob("*.py"))

        if not python_files:
            return False, "No Python files found"

        missing_headers = []
        for py_file in python_files:
            with open(py_file, 'r') as f:
                first_lines = ''.join([next(f, '') for _ in range(5)])

            if "SPDX-License-Identifier" not in first_lines:
                missing_headers.append(py_file.relative_to(self.repo_root))

        if missing_headers:
            return False, f"{len(missing_headers)} files missing headers"

        return True, f"All {len(python_files)} files have SPDX headers"

    def simulate_smart_contract_deployment(self, config):
        """Simulate deploying licensing smart contract."""
        print("\n" + "=" * 70)
        print("SIMULATING SMART CONTRACT DEPLOYMENT")
        print("=" * 70)

        # Contract configuration from .market.yaml
        print("\n📋 Contract Configuration:")
        print(f"   License Type: {config['license_identifier']}")
        print(f"   Target Price: {config['target_price']}")
        print(f"   Floor Price: {config['floor_price']}")
        print(f"   Network: {config['blockchain']['network']}")

        # Revenue split
        split = config['blockchain']['revenue_split']
        print("\n💰 Revenue Split:")
        print(f"   Developer: {split['developer']}%")
        print(f"   Platform: {split['platform']}%")
        print(f"   Community: {split['community']}%")

        # NFT configuration
        nft = config['blockchain']['nft_config']
        print("\n🎫 NFT License Token:")
        print(f"   Standard: {nft['token_standard']}")
        print(f"   Transferable: {nft['transferable']}")
        print(f"   Revocable: {nft['revocable']}")

        # Simulated contract address
        contract_address = "0x" + "1234567890abcdef" * 2 + "12345678"
        print("\n✅ Contract Deployed:")
        print(f"   Address: {contract_address}")
        print(f"   Network: {config['blockchain']['network']}")
        print("   Status: Active")

        return contract_address

    def simulate_license_purchase(self, config, contract_address):
        """Simulate a buyer purchasing a license."""
        print("\n" + "=" * 70)
        print("SIMULATING LICENSE PURCHASE")
        print("=" * 70)

        # Extract price
        price_str = config['target_price']
        price_value = float(price_str.split()[0])
        currency = price_str.split()[1]

        # Revenue calculation
        split = config['blockchain']['revenue_split']
        dev_share = price_value * (split['developer'] / 100)
        platform_share = price_value * (split['platform'] / 100)
        community_share = price_value * (split['community'] / 100)

        print("\n🛒 Purchase Details:")
        print("   License Tier: Standard")
        print(f"   Purchase Price: {price_value} {currency}")
        print("   Buyer: 0xABCD...5678")
        print(f"   Timestamp: {datetime.now().isoformat()}")

        print("\n💸 Revenue Distribution:")
        print(f"   Developer: {dev_share} {currency} ({split['developer']}%)")
        print(f"   Platform: {platform_share} {currency} ({split['platform']}%)")
        print(f"   Community: {community_share} {currency} ({split['community']}%)")

        # NFT token details
        token_id = 1
        print("\n🎫 License NFT Minted:")
        print(f"   Token ID: #{token_id}")
        print(f"   Contract: {contract_address}")
        print("   Owner: 0xABCD...5678")
        print(f"   License Type: {config['license_identifier']}")

        # License terms
        terms = config['license_terms']['standard']['features']
        print("\n📜 License Terms (Encoded in NFT):")
        for term in terms:
            print(f"   ✓ {term}")

        # Future license calculation
        effective_date = datetime.now() + timedelta(days=730)  # 2 years
        print("\n🔮 Future License Grant:")
        print("   Type: Apache-2.0")
        print(f"   Effective Date: {effective_date.strftime('%Y-%m-%d')}")
        print("   Auto-activation: Yes (via time-lock)")

        return token_id

    def simulate_access_verification(self, token_id):
        """Simulate verifying access via NFT token."""
        print("\n" + "=" * 70)
        print("SIMULATING ACCESS VERIFICATION")
        print("=" * 70)

        print("\n🔐 Token-Gated Access:")
        print(f"   Buyer presents NFT token #{token_id}")
        print("   Smart contract verifies ownership")
        print("   ✓ Access granted to repository")
        print("   ✓ License terms enforced on-chain")
        print("   ✓ Update notifications enabled")

    def demonstrate_complete_flow(self):
        """Run complete demonstration."""
        print("=" * 70)
        print("BLOCKCHAIN LICENSING DEMONSTRATION")
        print("Automated GitHub Code Monetization via Smart Contracts")
        print("=" * 70)

        # Step 1: Verify license foundation
        print("\n[1/6] Verifying License Foundation...")
        license_ok, license_msg = self.verify_license_file()
        print(f"    {'✓' if license_ok else '✗'} LICENSE.md: {license_msg}")

        # Step 2: Verify SPDX headers
        print("\n[2/6] Verifying SPDX Headers...")
        spdx_ok, spdx_msg = self.verify_spdx_headers()
        print(f"    {'✓' if spdx_ok else '✗'} Source files: {spdx_msg}")

        # Step 3: Load market configuration
        print("\n[3/6] Loading Blockchain Configuration...")
        config = self.load_market_config()
        if config:
            print("    ✓ .market.yaml loaded")
            print(f"    ✓ License: {config['license_identifier']}")
            print(f"    ✓ Target: {config['target_price']}")
        else:
            print("    ✗ Failed to load .market.yaml")
            return

        # Step 4: Deploy smart contract
        print("\n[4/6] Deploying Smart Contract...")
        contract_address = self.simulate_smart_contract_deployment(config)

        # Step 5: Simulate purchase
        print("\n[5/6] Processing License Purchase...")
        token_id = self.simulate_license_purchase(config, contract_address)

        # Step 6: Verify access
        print("\n[6/6] Verifying Token-Gated Access...")
        self.simulate_access_verification(token_id)

        # Summary
        print("\n" + "=" * 70)
        print("DEMONSTRATION COMPLETE")
        print("=" * 70)
        print("\n✅ Complete Integration Demonstrated:")
        print("   • FSL-1.1-ALv2 license provides legal foundation")
        print("   • SPDX headers enable machine-readable licensing")
        print("   • .market.yaml configures blockchain monetization")
        print("   • Smart contract enforces terms on-chain")
        print("   • NFT tokens represent license ownership")
        print("   • Revenue automatically distributed to developer")
        print("   • Access verified via token gating")
        print("   • Future Apache 2.0 license auto-activates")
        print("\n🎯 Result: GitHub work is automatically monetized on blockchain")
        print("=" * 70)


def main():
    """Run the demonstration."""
    demo = BlockchainLicensingDemo()
    demo.demonstrate_complete_flow()


if __name__ == "__main__":
    main()
