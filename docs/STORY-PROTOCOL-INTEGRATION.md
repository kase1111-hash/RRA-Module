# Story Protocol Integration Guide

## Overview

The RRA Module now integrates with **Story Protocol** to enable programmable IP licensing for code repositories. This integration transforms repositories into tokenized IP Assets with automated derivative tracking, royalty enforcement, and programmable licensing terms.

## What is Story Protocol?

Story Protocol is a Layer-1 blockchain (launched February 2025) specifically designed for tokenizing and managing intellectual property. It provides:

- **IP Asset Tokenization**: Register code repositories as on-chain IP Assets
- **Programmable IP Licenses (PIL)**: Machine-readable, legally enforceable license terms
- **Derivative Tracking**: Automatic tracking of forks and remixes
- **Royalty Automation**: Automated revenue distribution from derivatives
- **DeFi Composability**: IP Assets can be used in DeFi protocols (lending, staking, etc.)

## Key Features

### 1. IP Asset Registration

Register your repository as an IP Asset on Story Protocol:

```python
from rra.integrations.story_integration import StoryIntegrationManager
from rra.config.market_config import MarketConfig
from web3 import Web3

# Initialize
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_KEY"))
manager = StoryIntegrationManager(w3, network="mainnet")

# Load market config
config = MarketConfig.from_yaml(".market.yaml")

# Register repository
result = manager.register_repository_as_ip_asset(
    repo_url="https://github.com/youruser/yourrepo",
    market_config=config,
    owner_address="0xYourAddress",
    private_key="0xYourPrivateKey"
)

print(f"IP Asset ID: {result['ip_asset_id']}")
```

### 2. Programmable IP Licenses (PIL)

Define licensing terms in your `.market.yaml`:

```yaml
# Story Protocol Configuration
story_protocol_enabled: true

# PIL Terms
pil_commercial_use: true              # Allow commercial use
pil_derivatives_allowed: true         # Allow forks/derivatives
pil_derivatives_attribution: true     # Require attribution
pil_derivatives_reciprocal: false     # Don't require reciprocal licensing (copyleft)

# Royalty Configuration
derivative_royalty_percentage: 0.15   # 15% royalty on derivatives
```

### 3. Automatic Derivative Tracking

When someone forks your repository and registers it as a derivative:

```python
# Forker registers their fork as a derivative
fork_result = manager.register_derivative_repository(
    parent_repo_url="https://github.com/original/repo",
    parent_ip_asset_id="ip_asset_0xabc123",
    fork_repo_url="https://github.com/fork/repo",
    fork_description="Enhanced version with new features",
    license_terms_id="terms_0xdef456",
    fork_owner_address="0xForkOwner",
    private_key="0xForkPrivateKey"
)
```

**Benefits:**
- Automatic on-chain linkage between parent and fork
- Royalty payments automatically flow from fork revenue to original creator
- Transparent derivative graph visible on-chain

### 4. Royalty Enforcement

Royalties are automatically enforced on-chain:

```python
# Check royalty statistics
stats = manager.get_royalty_stats("ip_asset_0xabc123")

print(f"Royalty Rate: {stats['royalty_percentage']}%")
print(f"Total Collected: {stats['total_collected_eth']} ETH")
print(f"Last Payment: {stats['last_payment_timestamp']}")
```

### 5. View Derivative Graph

Track all forks of your repository:

```python
# Get all derivatives
derivatives = manager.get_repository_derivatives("ip_asset_0xabc123")

print(f"Total Forks: {derivatives['derivative_count']}")
for fork in derivatives['derivatives']:
    print(f"  - Fork ID: {fork['id']}, Owner: {fork['owner']}")
```

## Configuration

### .market.yaml Configuration

Add Story Protocol settings to your `.market.yaml`:

```yaml
# Base License
license_identifier: "FSL-1.1-ALv2"
copyright_holder: "Your Name"

# Pricing
target_price: "0.05 ETH"
floor_price: "0.02 ETH"

# Developer Wallet
developer_wallet: "0xYourEthereumAddress"

# Story Protocol Integration
story_protocol_enabled: true
ip_asset_id: null  # Auto-populated after registration

# Programmable IP License (PIL) Terms
pil_commercial_use: true
pil_derivatives_allowed: true
pil_derivatives_attribution: true
pil_derivatives_reciprocal: false

# Royalty Settings
derivative_royalty_percentage: 0.15  # 15% royalty on derivative revenue
royalty_on_derivatives: 0.10         # Legacy field (10% - Story uses derivative_royalty_percentage)
```

### Environment Variables

Set up your blockchain connection:

```bash
# .env file
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY
ETHEREUM_PRIVATE_KEY=0xYourPrivateKey
ETHEREUM_ADDRESS=0xYourAddress

# For Story Protocol testnet
STORY_TESTNET_RPC_URL=https://story-testnet-rpc.example.com
```

## Use Cases

### 1. Open Source Monetization

- Register your OSS project as an IP Asset
- Allow free non-commercial derivatives
- Charge royalties for commercial forks
- Automatically track usage in commercial products

### 2. Enterprise Code Licensing

- License proprietary code with automated royalty tracking
- Whitelist approved derivative creators
- Real-time revenue visibility from all derivatives
- On-chain audit trail of all usage

### 3. Code Marketplaces

- List repositories in DeFi-native code marketplaces
- Buyers receive license NFTs
- Sellers receive automated royalties from resale
- Fractional ownership of high-value codebases

### 4. Zombie Repo Resurrection

- Tokenize abandoned repositories
- Create passive income streams from forks
- Bundle multiple repos into IP Asset portfolios
- Stake IP tokens for yield

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                     RRA Module                           │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │  Market Config   │────────▶│ Story Integration│     │
│  │  (.market.yaml)  │         │     Manager      │     │
│  └──────────────────┘         └────────┬─────────┘     │
│                                         │               │
│                               ┌─────────▼─────────┐     │
│                               │ Story Protocol    │     │
│                               │     Client        │     │
│                               └────────┬──────────┘     │
└────────────────────────────────────────┼────────────────┘
                                         │
                                         │ Web3
                                         ▼
                    ┌────────────────────────────────────┐
                    │      Story Protocol Contracts      │
                    ├────────────────────────────────────┤
                    │  • IP Asset Registry               │
                    │  • License Registry                │
                    │  • Royalty Module                  │
                    │  • PIL Framework                   │
                    └────────────────────────────────────┘
```

### Class Hierarchy

```python
StoryProtocolClient
  ├─ register_ip_asset()
  ├─ attach_license_terms()
  ├─ mint_license()
  ├─ register_derivative()
  ├─ set_royalty_policy()
  └─ get_ip_asset_info()

StoryIntegrationManager
  ├─ register_repository_as_ip_asset()
  ├─ register_derivative_repository()
  ├─ mint_license_for_buyer()
  ├─ get_repository_derivatives()
  └─ get_royalty_stats()
```

## API Reference

### StoryProtocolClient

#### `register_ip_asset(owner_address, metadata, private_key)`

Register a new IP Asset.

**Parameters:**
- `owner_address` (str): Ethereum address of IP owner
- `metadata` (IPAssetMetadata): Asset metadata
- `private_key` (str): Private key for transaction signing

**Returns:**
- Dictionary with `ip_asset_id`, `tx_hash`, `block_number`, `status`

#### `attach_license_terms(ip_asset_id, pil_terms, owner_address, private_key)`

Attach PIL terms to an IP Asset.

**Parameters:**
- `ip_asset_id` (str): IP Asset ID
- `pil_terms` (PILTerms): Programmable IP License terms
- `owner_address` (str): Owner's address
- `private_key` (str): Private key

**Returns:**
- Transaction hash (str)

#### `register_derivative(parent_ip_asset_id, derivative_owner_address, derivative_metadata, license_terms_id, private_key)`

Register a derivative work.

**Parameters:**
- `parent_ip_asset_id` (str): Parent IP Asset ID
- `derivative_owner_address` (str): Derivative owner
- `derivative_metadata` (IPAssetMetadata): Derivative metadata
- `license_terms_id` (str): License terms being used
- `private_key` (str): Private key

**Returns:**
- Dictionary with `derivative_ip_asset_id`, `parent_ip_asset_id`, `tx_hash`, `status`

#### `set_royalty_policy(ip_asset_id, royalty_percentage, payment_token, owner_address, private_key)`

Set royalty policy for an IP Asset.

**Parameters:**
- `ip_asset_id` (str): IP Asset ID
- `royalty_percentage` (int): Royalty in basis points (0-10000)
- `payment_token` (str): ERC20 token address for payments
- `owner_address` (str): Owner's address
- `private_key` (str): Private key

**Returns:**
- Transaction hash (str)

### StoryIntegrationManager

#### `register_repository_as_ip_asset(repo_url, market_config, owner_address, private_key, repo_description=None)`

Register a repository as an IP Asset.

**Parameters:**
- `repo_url` (str): Repository URL
- `market_config` (MarketConfig): Market configuration
- `owner_address` (str): Owner's address
- `private_key` (str): Private key
- `repo_description` (str, optional): Description override

**Returns:**
- Dictionary with registration details and IP Asset ID

#### `get_repository_derivatives(ip_asset_id)`

Get all derivatives for a repository.

**Parameters:**
- `ip_asset_id` (str): IP Asset ID

**Returns:**
- Dictionary with derivative count and list of derivatives

#### `get_royalty_stats(ip_asset_id)`

Get royalty statistics.

**Parameters:**
- `ip_asset_id` (str): IP Asset ID

**Returns:**
- Dictionary with royalty information

## Best Practices

### 1. Network Selection

- **Development**: Use Story Protocol testnet
- **Production**: Use Story Protocol mainnet (live since Feb 2025)

### 2. Royalty Rates

- **Open Source Projects**: 5-15% royalty on commercial derivatives
- **Proprietary Code**: 10-30% royalty
- **Enterprise Libraries**: 15-25% royalty

### 3. PIL Term Configuration

**For Maximum Openness:**
```yaml
pil_commercial_use: true
pil_derivatives_allowed: true
pil_derivatives_attribution: true
pil_derivatives_reciprocal: false
derivative_royalty_percentage: 0.05  # 5%
```

**For Controlled Distribution:**
```yaml
pil_commercial_use: true
pil_derivatives_allowed: true
pil_derivatives_attribution: true
pil_derivatives_reciprocal: true  # Copyleft
derivative_royalty_percentage: 0.20  # 20%
```

### 4. Gas Optimization

- Batch multiple operations when possible
- Use appropriate gas limits
- Monitor network congestion

## Testing

Run Story Protocol integration tests:

```bash
# Run all Story Protocol tests
pytest tests/test_story_protocol.py -v

# Run specific test class
pytest tests/test_story_protocol.py::TestStoryProtocolClient -v

# Run with coverage
pytest tests/test_story_protocol.py --cov=rra.contracts.story_protocol --cov=rra.integrations.story_integration
```

## Scripts

The RRA Module includes ready-to-use scripts for Story Protocol integration:

### enable_story_purchases.py

Attaches license terms to your IP Asset, enabling buyers to purchase licenses.

```bash
# Windows
set STORY_PRIVATE_KEY=0xYourPrivateKey
python scripts/enable_story_purchases.py --ip-asset 0xYourIPAssetID

# Linux/Mac
export STORY_PRIVATE_KEY=0xYourPrivateKey
python scripts/enable_story_purchases.py --ip-asset 0xYourIPAssetID
```

**Options:**
- `--ip-asset` - Your IP Asset address (required)
- `--market-config` - Path to .market.yaml (default: .market.yaml)
- `--network` - mainnet or testnet (default: mainnet)
- `--output-dir` - Where to save buyer HTML (default: marketplace/public)

**Output:**
- Attaches PIL license terms on-chain
- Generates `buy-license.html` buyer interface

### claim_royalties.py

Claims pending revenue from your IP Asset's Royalty Vault.

```bash
# Windows
set STORY_PRIVATE_KEY=0xYourPrivateKey
python scripts/claim_royalties.py --ip-asset 0xYourIPAssetID

# Linux/Mac
export STORY_PRIVATE_KEY=0xYourPrivateKey
python scripts/claim_royalties.py --ip-asset 0xYourIPAssetID
```

**Options:**
- `--ip-asset` - Your IP Asset address (default: reads from .market.yaml)
- `--network` - mainnet or testnet (default: mainnet)

**What it does:**
1. Finds your IP Asset's Royalty Vault
2. Snapshots pending revenue (makes it claimable)
3. Claims revenue to your wallet

## Live Example

This repository (RRA-Module) is live on Story Protocol:

| Field | Value |
|-------|-------|
| IP Asset | `0xb77ABcfFbf063a3e6BACA37D72353750475D4E70` |
| License Terms ID | 3 (Commercial Remix) |
| Price | 0.05 ETH |
| Purchase Page | [Buy License](https://kase1111-hash.github.io/RRA-Module/marketplace/public/buy-license.html) |
| StoryScan | [View on Chain](https://www.storyscan.io/token/0xb77ABcfFbf063a3e6BACA37D72353750475D4E70) |

## Troubleshooting

### Issue: "Contract not initialized"

**Solution**: Ensure Web3 is connected to the correct network and Story Protocol contracts are deployed.

### Issue: "Story Protocol not enabled in market config"

**Solution**: Set `story_protocol_enabled: true` in your `.market.yaml`.

### Issue: "Royalty percentage cannot exceed 100%"

**Solution**: Use values between 0.0 and 1.0 for royalty percentages (e.g., 0.15 for 15%).

### Issue: Transaction fails with "insufficient funds"

**Solution**: Ensure your wallet has enough ETH for gas fees and any required payments.

### Issue: "bad address checksum" error

**Solution**: Use lowercase addresses in JavaScript. The `buy-license.html` uses lowercase addresses to bypass ethers.js checksum validation.

### Issue: Can't find revenue after purchase

**Solution**: Revenue goes to your IP Asset's Royalty Vault, not directly to your wallet. Use `claim_royalties.py` to claim:
```bash
python scripts/claim_royalties.py --ip-asset 0xYourIPAssetID
```

### Issue: "No Royalty Vault found"

**Solution**: This means either:
- No purchases have been made yet
- The IP Asset wasn't registered with royalty support
- Check StoryScan for your IP Asset's vault address

## Resources

- [Story Protocol Documentation](https://docs.story.foundation)
- [Story Protocol Whitepaper](https://story.foundation/whitepaper)
- [RRA Module Repository](https://github.com/kase1111-hash/RRA-Module)
- [DeFi Integration Feasibility](DEFI-INTEGRATION.md)
- [Full Documentation Index](README.md)

## Roadmap

### Phase 3 (Current - Q1 2025)
- ✅ Story Protocol contract integration
- ✅ IP Asset registration
- ✅ PIL terms implementation
- ✅ Derivative tracking
- ✅ Royalty enforcement

### Phase 4 (Q2 2025)
- ⏳ Multi-chain support (Ethereum, Polygon, Arbitrum)
- ⏳ Automated derivative detection (GitHub webhooks)
- ⏳ Story Protocol L1 native deployment
- ⏳ IPFi lending integration (NFTfi)

### Phase 5 (Q3 2025)
- ⏳ Fractional IP ownership
- ⏳ Yield-bearing license tokens
- ⏳ DAO governance for IP portfolios
- ⏳ Marketplace UI integration

## License

This integration is licensed under FSL-1.1-ALv2.

Copyright 2025 Kase Branham
