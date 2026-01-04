# RRA Module Usage Guide

A comprehensive guide to using the Revenant Repo Agent Module for monetizing your GitHub repositories.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [CLI Commands](#cli-commands)
5. [API Usage](#api-usage)
6. [Story Protocol Integration](#story-protocol-integration)
7. [Royalty Management](#royalty-management)
8. [Scripts Reference](#scripts-reference)
9. [Common Workflows](#common-workflows)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

Get your repository monetized in 5 minutes:

```bash
# 1. Install the module
pip install rra-module

# 2. Create configuration in your repo root
cat > .market.yaml << 'EOF'
license_model: "perpetual"
target_price: "0.05 ETH"
floor_price: "0.02 ETH"
negotiation_style: "concise"
EOF

# 3. Initialize and ingest your repo
rra init
rra ingest https://github.com/youruser/yourrepo

# 4. Start the negotiation agent
rra agent
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- Node.js 18+ (for JavaScript scripts)
- A Web3 wallet (MetaMask) with IP tokens for gas

### Python Installation

```bash
# From PyPI (when available)
pip install rra-module

# From source
git clone https://github.com/kase1111-hash/RRA-Module.git
cd RRA-Module
pip install -e .
```

### JavaScript Dependencies

For blockchain scripts:

```bash
npm install viem @story-protocol/core-sdk
```

### Environment Setup

Create a `.env` file for sensitive configuration:

```bash
# Wallet configuration
STORY_PRIVATE_KEY=0xYourPrivateKeyHere
ETHEREUM_ADDRESS=0xYourWalletAddress

# RPC endpoints
STORY_RPC_URL=https://mainnet.storyrpc.io
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY

# Optional: API keys
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
```

---

## Configuration

### .market.yaml Reference

The `.market.yaml` file in your repository root defines licensing terms:

```yaml
# === License Model ===
license_model: "perpetual"      # perpetual | per-seat | subscription | one-time | custom
license_identifier: "FSL-1.1-ALv2"
copyright_holder: "Your Name"

# === Pricing ===
target_price: "0.05 ETH"        # Your asking price
floor_price: "0.02 ETH"         # Minimum you'll accept
ceiling_price: "0.15 ETH"       # Maximum (for premium features)

# === Negotiation ===
negotiation_style: "concise"    # concise | persuasive | strict | adaptive
negotiation_rounds_max: 5
allow_custom_fork_rights: true

# === Updates ===
update_frequency: "weekly"      # daily | weekly | monthly | on-push
sandbox_tests: "tests/sandbox.py"

# === Blockchain ===
blockchain:
  network: "story"              # story | ethereum | polygon | arbitrum | base | optimism
  wallets:
    developer: "0xYourWalletAddress"
  revenue_split:
    developer: 91
    platform: 8
    community: 1

# === Story Protocol ===
defi_integrations:
  story_protocol:
    enabled: true
    network: "mainnet"
    ip_asset_id: "0xYourIPAssetID"  # Filled after registration
    license_terms_id: 3

    pil_terms:
      commercial_use: true
      derivatives_allowed: true
      derivatives_attribution: true
      derivatives_reciprocal: false

    derivative_royalty_percentage: 0.09  # 9%
```

### Negotiation Styles

| Style | Behavior |
|-------|----------|
| `concise` | Quick, to-the-point responses. Fast deal closure. |
| `persuasive` | Highlights repo strengths, upsells premium features |
| `strict` | No negotiations below floor price, minimal concessions |
| `adaptive` | Learns from buyer behavior, adjusts approach dynamically |

---

## CLI Commands

### Core Commands

```bash
# Initialize a new repository for monetization
rra init [--config .market.yaml]

# Ingest repository and build knowledge base
rra ingest <repo_url> [--verify] [--categorize]

# Start interactive negotiation agent
rra agent [--repo <repo_name>]

# List all ingested repositories
rra list

# Show repository information
rra info <repo_name>

# Verify code quality (tests, linting, security)
rra verify <repo_path>

# Categorize repository automatically
rra categorize <repo_path>

# Generate blockchain purchase link
rra purchase_link <repo_name>
```

### Story Protocol Commands

```bash
# Register repository as IP Asset
rra story register --repo <repo_name>

# Get Story Protocol asset info
rra story_info --ip-asset <address>

# Check royalty information
rra royalties --ip-asset <address>
```

### Status Commands

```bash
# Show processing status
rra dreaming

# Health check
rra health
```

### Command Examples

```bash
# Full workflow example
rra init
rra ingest https://github.com/myuser/myrepo --verify --categorize
rra info myrepo
rra agent --repo myrepo

# Story Protocol workflow
rra story register --repo myrepo
rra story_info --ip-asset 0x123...
rra royalties --ip-asset 0x123...
```

---

## API Usage

### Starting the API Server

```bash
# Start FastAPI server
rra serve --host 0.0.0.0 --port 8000

# Or directly with uvicorn
uvicorn rra.api.server:app --reload --port 8000
```

### REST API Endpoints

#### Repository Management

```bash
# Ingest a repository
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo"}'

# List repositories
curl http://localhost:8000/api/repositories

# Get repository info
curl http://localhost:8000/api/repository/myrepo
```

#### Negotiation

```bash
# Start negotiation session
curl -X POST http://localhost:8000/api/negotiate/start \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "myrepo"}'

# Send negotiation message
curl -X POST http://localhost:8000/api/negotiate/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "I want to buy a license"}'

# Get negotiation summary
curl http://localhost:8000/api/negotiate/summary/abc123
```

#### License Verification

```bash
# Verify a license
curl -X POST http://localhost:8000/api/verify \
  -H "Content-Type: application/json" \
  -d '{"license_token_id": "123", "wallet_address": "0x..."}'

# Initiate purchase
curl -X POST http://localhost:8000/api/purchase \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "myrepo", "buyer_address": "0x..."}'
```

#### Marketplace

```bash
# Discover repositories
curl http://localhost:8000/api/marketplace

# Get license terms for a repo
curl http://localhost:8000/api/marketplace/myrepo/terms
```

### WebSocket API

For real-time negotiation:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/negotiate/session123');

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('Agent:', response.message);
};

ws.send(JSON.stringify({ message: "I want to buy a license" }));
```

### Python SDK

```python
from rra import MarketConfig, RepoIngester, NegotiatorAgent

# Load configuration
config = MarketConfig.from_yaml(".market.yaml")

# Ingest repository
ingester = RepoIngester(workspace_dir="./workspace")
knowledge_base = ingester.ingest_repo("https://github.com/user/repo")

# Start negotiation
agent = NegotiatorAgent(knowledge_base)
session_id = agent.start_negotiation()

# Conduct negotiation
response = agent.respond("I'm interested in buying a license")
print(response)

# Get summary
summary = agent.get_negotiation_summary()
print(f"Current offer: {summary['current_price']}")
```

---

## Story Protocol Integration

### Registering Your Repository

1. **Register on Story Protocol** using their app: https://app.story.foundation

2. **Get your IP Asset ID** after registration (e.g., `0xb77ABcfFbf063a3e6BACA37D72353750475D4E70`)

3. **Update your .market.yaml**:
   ```yaml
   defi_integrations:
     story_protocol:
       enabled: true
       ip_asset_id: "0xYourIPAssetID"
   ```

4. **Enable purchases**:
   ```bash
   export STORY_PRIVATE_KEY=0xYourPrivateKey
   python scripts/enable_story_purchases.py --ip-asset 0xYourIPAssetID
   ```

### License Minting

Buyers can mint licenses via:

1. **Web Interface**: Use the generated `buy-license.html`
2. **SDK**: Using Story Protocol SDK
3. **Script**: `node scripts/mint-license.js`

### Revenue Flow

```
Buyer Pays → Licensing Module → Royalty Vault → Snapshot → Claim → Your Wallet
```

---

## Royalty Management

### Checking Vault State

```bash
# Quick check
node scripts/check-royalty-vault.js

# Detailed debug
node scripts/debug-vault.js
```

### Claiming Royalties

#### Method 1: Python (Recommended)

```bash
export STORY_PRIVATE_KEY=0xYourPrivateKey
python scripts/claim_royalties.py --ip-asset 0xYourIPAssetID
```

#### Method 2: JavaScript via IP Account

```bash
PRIVATE_KEY=0xYourPrivateKey node scripts/claim-via-ip-account.js
```

#### Method 3: RoyaltyModule

```bash
PRIVATE_KEY=0xYourPrivateKey node scripts/claim-via-module.js
```

### Understanding Royalty Tokens

- **WIP**: Wrapped IP token (18 decimals) - payment currency
- **RT**: Royalty Token (6 decimals) - represents royalty share
- **100 RT** = 100% of royalties
- IP Asset initially owns all RT

### Claiming Process

1. **Snapshot**: Call `vault.snapshot()` to make pending revenue claimable
2. **Claim**: Call claim function to move funds to IP Account
3. **Transfer**: Move funds from IP Account to your wallet

The scripts handle all three steps automatically.

---

## Scripts Reference

### Python Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `enable_story_purchases.py` | Enable license purchases | `python scripts/enable_story_purchases.py --ip-asset 0x...` |
| `claim_royalties.py` | Claim royalties from vault | `python scripts/claim_royalties.py --ip-asset 0x...` |

### JavaScript Scripts

| Script | Description | Usage |
|--------|-------------|-------|
| `mint-license.js` | Mint license token | `PRIVATE_KEY=0x... node scripts/mint-license.js` |
| `debug-vault.js` | Debug vault state | `node scripts/debug-vault.js` |
| `claim-via-ip-account.js` | Claim via ERC-6551 | `PRIVATE_KEY=0x... node scripts/claim-via-ip-account.js` |
| `claim-via-module.js` | Claim via RoyaltyModule | `PRIVATE_KEY=0x... node scripts/claim-via-module.js` |
| `claim-fixed.js` | Claim with 6-decimal RT | `PRIVATE_KEY=0x... node scripts/claim-fixed.js` |
| `claim-as-ip-owner.js` | Claim as IP owner | `PRIVATE_KEY=0x... node scripts/claim-as-ip-owner.js` |
| `check-royalty-vault.js` | Quick vault check | `node scripts/check-royalty-vault.js` |
| `pay-royalty.js` | Test royalty payment | `PRIVATE_KEY=0x... node scripts/pay-royalty.js` |

### Script Dependencies

```bash
# Python
pip install web3 pyyaml click

# JavaScript
npm install viem @story-protocol/core-sdk
```

---

## Common Workflows

### Workflow 1: First-Time Setup

```bash
# 1. Clone your repo
git clone https://github.com/youruser/yourrepo
cd yourrepo

# 2. Create market configuration
cat > .market.yaml << 'EOF'
license_model: "perpetual"
target_price: "0.05 ETH"
floor_price: "0.02 ETH"
negotiation_style: "concise"
blockchain:
  wallets:
    developer: "0xYourWalletAddress"
EOF

# 3. Register on Story Protocol
# Visit https://app.story.foundation

# 4. Enable purchases
export STORY_PRIVATE_KEY=0xYourPrivateKey
python scripts/enable_story_purchases.py --ip-asset 0xYourIPAssetID

# 5. Deploy purchase page
# Copy marketplace/public/buy-license.html to your website
```

### Workflow 2: Claiming Revenue

```bash
# 1. Check vault state
node scripts/debug-vault.js

# 2. Claim royalties
PRIVATE_KEY=0xYourPrivateKey node scripts/claim-via-ip-account.js

# 3. Verify claim
node scripts/check-royalty-vault.js
```

### Workflow 3: Running Negotiation Agent

```bash
# 1. Ingest repository
rra ingest https://github.com/youruser/yourrepo

# 2. Start agent
rra agent --repo yourrepo

# 3. Or start API server
rra serve --port 8000

# 4. Connect via WebSocket for real-time chat
```

### Workflow 4: Testing License Purchase

```bash
# 1. Mint a test license
PRIVATE_KEY=0xYourPrivateKey node scripts/mint-license.js

# 2. Check that royalties appeared
node scripts/debug-vault.js

# 3. Claim the test revenue
PRIVATE_KEY=0xYourPrivateKey node scripts/claim-via-ip-account.js
```

---

## Troubleshooting

### Installation Issues

**Problem**: `pip install` fails

```bash
# Try with virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e .
```

**Problem**: Node.js scripts fail

```bash
# Check Node version (need 18+)
node --version

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install viem @story-protocol/core-sdk
```

### Connection Issues

**Problem**: "Cannot connect to RPC"

```bash
# Check RPC endpoint
curl https://mainnet.storyrpc.io/health

# Try alternative RPC
export STORY_RPC_URL=https://rpc.ankr.com/story
```

**Problem**: "Transaction failed - insufficient funds"

- Ensure you have IP tokens for gas
- Story Protocol uses IP as the native token
- Get IP from exchanges or bridges

### Claiming Issues

**Problem**: "No Royalty Vault found"

- No purchases have been made yet
- IP Asset wasn't registered with royalty support
- Check StoryScan for your IP Asset

**Problem**: "Unauthorized" error

- Only IP Asset owner can claim
- Check ownership with `debug-vault.js`
- Ensure you're using the correct wallet

**Problem**: "Snapshot ID not found"

- Create snapshot first: `vault.snapshot()`
- The claiming scripts handle this automatically

**Problem**: RT balance shows tiny number

- RT uses 6 decimals, not 18
- 100000000 raw = 100 RT (100%)
- Use `formatUnits(balance, 6)`

### Negotiation Issues

**Problem**: Agent not responding

- Check that knowledge base was generated
- Verify `rra info <repo>` shows data
- Check API server logs

**Problem**: Prices not matching config

- Reload config: `rra init`
- Check `.market.yaml` syntax
- Verify no YAML indentation errors

---

## Contract Addresses (Story Protocol Mainnet)

| Contract | Address |
|----------|---------|
| Licensing Module | `0xd81fd78f557b457b4350cb95d20b547bfeb4d857` |
| PIL Template | `0x0752b15ee7303033854bde1b32bc7a4008752dc0` |
| Royalty Module | `0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086` |
| IP Asset Registry | `0x77319B4031e6eF1250907aa00018B8B1c67a244b` |
| WIP Token | `0x1514000000000000000000000000000000000000` |
| Access Controller | `0x4557F9Bc90e64D6D6E628d1BC9a9FEBF8C79d4E1` |

---

## Additional Resources

- [Story Protocol Documentation](https://docs.story.foundation)
- [StoryScan Explorer](https://storyscan.io)
- [RRA Module GitHub](https://github.com/kase1111-hash/RRA-Module)
- [Selling Licenses Guide](SELLING-LICENSES.md)
- [Story Protocol Integration](STORY-PROTOCOL-INTEGRATION.md)
- [DeFi Integration Guide](DEFI-INTEGRATION.md)
- [Full Documentation Index](README.md)

---

## License

This documentation is part of the RRA Module, licensed under FSL-1.1-ALv2.

Copyright 2025 Kase Branham
