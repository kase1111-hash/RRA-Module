# Selling Licenses with Story Protocol - Complete Guide

This guide walks you through monetizing your GitHub repository using Story Protocol. By the end, you'll have a working purchase page where anyone can buy a license to your code.

## Prerequisites

- Python 3.9+
- A Web3 wallet (MetaMask) with some IP tokens for gas
- Your repository with a `.market.yaml` configuration file

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```cmd
pip install web3 pyyaml
```

### Step 2: Configure Your Wallet

Get your private key from MetaMask:
1. Open MetaMask → Click three dots → Account Details → Export Private Key
2. Save it securely (never share or commit this!)

### Step 3: Enable Purchases

```cmd
set STORY_PRIVATE_KEY=0xYourPrivateKeyHere
python scripts/enable_story_purchases.py --ip-asset 0xYourIPAssetID
```

**Expected output:**
```
============================================================
Story Protocol License Enablement
============================================================

Loaded configuration from .market.yaml
Connected to Story Protocol mainnet
  Chain ID: 1514
  Owner: 0xYourAddress

Attaching license terms to IP Asset...
  Transaction sent: 0x...
  Transaction confirmed in block 12345678

============================================================
LICENSE PURCHASES ENABLED!
============================================================

Buyer Interface: marketplace\public\buy-license.html
```

### Step 4: Deploy Your Purchase Page

The script generates `marketplace/public/buy-license.html`. Deploy it:

**Option A: GitHub Pages (Free)**
1. Go to your repo → Settings → Pages
2. Source: Deploy from branch `main`
3. Folder: `/ (root)`
4. Your page will be at: `https://username.github.io/repo/marketplace/public/buy-license.html`

**Option B: Any Web Host**
- Upload `buy-license.html` to Netlify, Vercel, or any static host

### Step 5: Share Your Purchase Link

Add to your README:
```markdown
[![Buy License](https://img.shields.io/badge/Buy_License-0.05_ETH-6366f1)](https://your-purchase-page-url)
```

---

## Complete Walkthrough

### 1. Understanding the Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Your Repo      │────▶│  Story Protocol  │────▶│  Buyer's Wallet │
│  (.market.yaml) │     │  (IP Asset)      │     │  (License NFT)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
        │                        ▼                        │
        │               ┌──────────────────┐              │
        └──────────────▶│  Royalty Vault   │◀─────────────┘
                        │  (Your Revenue)  │
                        └──────────────────┘
```

1. You register your repo as an **IP Asset** on Story Protocol
2. You attach **License Terms** (price, rights, etc.)
3. Buyers mint **License Tokens** (NFTs) by paying your price
4. Revenue goes to your **Royalty Vault**
5. You **claim** funds from the vault to your wallet

### 2. Configuring Your .market.yaml

Create or edit `.market.yaml` in your repo root:

```yaml
# Pricing
license_model: "perpetual"      # perpetual, per-seat, subscription
target_price: "0.05 ETH"        # Your asking price
floor_price: "0.02 ETH"         # Minimum you'll accept

# Story Protocol Settings
defi_integrations:
  story_protocol:
    enabled: true
    network: "mainnet"
    ip_asset_id: "0xYourIPAssetID"  # Filled after registration

    pil_terms:
      commercial_use: true           # Allow commercial use
      derivatives_allowed: true      # Allow forks
      derivatives_attribution: true  # Require attribution

    derivative_royalty_percentage: 0.09  # 9% from derivatives

# Your Wallet
blockchain:
  wallets:
    developer: "0xYourWalletAddress"
```

### 3. Registering Your IP Asset

If you haven't registered yet, use Story Protocol's tools:
- Story Protocol App: https://app.story.foundation
- Or use the SDK programmatically

After registration, you'll receive an **IP Asset ID** (e.g., `0xb77ABcfFbf063a3e6BACA37D72353750475D4E70`).

Add this to your `.market.yaml`:
```yaml
ip_asset_id: "0xYourIPAssetID"
```

### 4. Attaching License Terms

This is what makes your IP Asset **purchasable**:

```cmd
python scripts/enable_story_purchases.py ^
  --ip-asset 0xYourIPAssetID ^
  --market-config .market.yaml ^
  --network mainnet
```

**What this does:**
- Reads your `.market.yaml` pricing
- Converts to Story Protocol PIL (Programmable IP License) terms
- Attaches terms on-chain via `LicensingModule.attachLicenseTerms()`
- Generates buyer interface HTML

### 5. How Buyers Purchase

When someone visits your purchase page:

1. **Connect Wallet** - They click "Connect Wallet"
2. **Switch Network** - Prompted to switch to Story Protocol (Chain ID: 1514)
3. **Purchase** - Click "Purchase License for 0.05 ETH"
4. **Confirm** - Approve transaction in MetaMask
5. **Receive NFT** - License token minted to their wallet

The buyer now owns an NFT proving they have a license to your code.

### 6. Claiming Your Revenue

Revenue goes to your IP Asset's **Royalty Vault**, not directly to your wallet.

**Check and claim your funds:**

```cmd
set STORY_PRIVATE_KEY=0xYourPrivateKeyHere
python scripts/claim_royalties.py --ip-asset 0xYourIPAssetID
```

**Output:**
```
============================================================
Story Protocol Royalty Claim
============================================================

Looking up Royalty Vault...
  Royalty Vault: 0x...

Checking balances...
  Pending in vault: 0.05 ETH/IP

Step 1: Snapshotting pending revenue...
Step 2: Claiming revenue...

CLAIM COMPLETE!
Your wallet balance: 0.15 IP
```

---

## Troubleshooting

### "bad address checksum" Error

The purchase page uses lowercase addresses. If you see this error:
- Make sure you're using the latest `buy-license.html`
- All addresses should be lowercase in the JavaScript

### "No Royalty Vault found"

This means either:
- The IP Asset wasn't registered with a royalty policy
- No purchases have been made yet
- Check StoryScan for your IP Asset's vault

### "Transaction failed" on Purchase

Common causes:
- Insufficient IP tokens for gas
- Wrong network (should be Story Protocol, Chain ID 1514)
- License terms not attached yet

### Can't Find My Revenue

Revenue flow:
1. Buyer pays → Licensing Module
2. Licensing Module → Your Royalty Vault (pending)
3. You call `snapshot()` → Makes funds claimable
4. You call `claimRevenue()` → Funds to your wallet

Use `claim_royalties.py` to do steps 3 and 4.

---

## Scripts Reference

### enable_story_purchases.py

Attaches license terms to enable purchasing.

```cmd
python scripts/enable_story_purchases.py [OPTIONS]

Options:
  --ip-asset       IP Asset address (required)
  --market-config  Path to .market.yaml (default: .market.yaml)
  --private-key    Your private key (or use STORY_PRIVATE_KEY env var)
  --network        mainnet or testnet (default: mainnet)
  --output-dir     Where to save buyer HTML (default: marketplace/public)
```

### claim_royalties.py

Claims pending revenue from your Royalty Vault.

```cmd
python scripts/claim_royalties.py [OPTIONS]

Options:
  --ip-asset     IP Asset address (default: from .market.yaml)
  --private-key  Your private key (or use STORY_PRIVATE_KEY env var)
  --network      mainnet or testnet (default: mainnet)
```

---

## Contract Addresses (Mainnet)

| Contract | Address |
|----------|---------|
| Licensing Module | `0xd81fd78f557b457b4350cb95d20b547bfeb4d857` |
| PIL Template | `0x0752b15ee7303033854bde1b32bc7a4008752dc0` |
| Royalty Module | `0x3C27b2D7d30131D4B58C3584FD7c86e104C67883` |
| IP Asset Registry | `0x77319B4031e6eF1250907aa00018B8B1c67a244b` |

---

## Example: RRA-Module

This repository is monetized using this exact process:

- **IP Asset:** `0xb77ABcfFbf063a3e6BACA37D72353750475D4E70`
- **Price:** 0.05 ETH
- **License Terms ID:** 3 (Commercial Remix)
- **Purchase Page:** [Buy License](https://kase1111-hash.github.io/RRA-Module/marketplace/public/buy-license.html)
- **StoryScan:** [View IP Asset](https://www.storyscan.io/token/0xb77ABcfFbf063a3e6BACA37D72353750475D4E70)

---

## Next Steps

1. **Test with a small purchase** - Buy your own license to verify flow
2. **Add badge to README** - Make purchasing visible
3. **Share your purchase link** - Twitter, Discord, etc.
4. **Set up royalty claiming schedule** - Weekly or after each sale

## Resources

- [Story Protocol Docs](https://docs.story.foundation)
- [StoryScan Explorer](https://storyscan.io)
- [RRA Module Documentation](./README.md)
