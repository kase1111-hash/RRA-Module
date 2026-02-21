# Blockchain-Based Code Monetization Guide

## Overview

This guide covers the complete integration between the **FSL-1.1-ALv2 license**, the **RRA Module's blockchain licensing system**, and **Story Protocol** for automated monetization of GitHub code. By the end you will understand how to register your repository as an IP asset, attach license terms, accept on-chain payments, and claim revenue -- all without manual sales handling.

**What you get:**
- A purchase page where anyone can buy a license to your code
- AI-powered negotiation agents that handle buyer inquiries
- NFT-based license tokens that prove ownership on-chain
- Automated revenue distribution to your wallet

### Prerequisites

- Python 3.9+
- A Web3 wallet (MetaMask) with some IP tokens for gas
- Your repository with a `.market.yaml` configuration file
- Node.js (for JavaScript claiming scripts, optional)

---

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```cmd
pip install web3 pyyaml
```

### Step 2: Configure Your Wallet

Get your private key from MetaMask:
1. Open MetaMask -> Click three dots -> Account Details -> Export Private Key
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

Buyer Interface: buy-license.html
```

### Step 4: Deploy Your Purchase Page

The script generates `buy-license.html`. Deploy it:

**Option A: GitHub Pages (Free)**
1. Go to your repo -> Settings -> Pages
2. Source: Deploy from branch `main`
3. Folder: `/ (root)`
4. Your page will be at: `https://username.github.io/repo/buy-license.html`

**Option B: Any Web Host**
- Upload `buy-license.html` to Netlify, Vercel, or any static host

### Step 5: Share Your Purchase Link

Add to your README:
```markdown
[![Buy License](https://img.shields.io/badge/Buy_License-0.05_ETH-6366f1)](https://your-purchase-page-url)
```

---

## Complete Automated Monetization Flow

```
+-------------------------------------------------------------------+
|                    AUTOMATED MONETIZATION FLOW                     |
+-------------------------------------------------------------------+

1. DEVELOPER SETUP
   |
   * Add LICENSE.md (FSL-1.1-ALv2)
   * Add SPDX headers to all source files
   * Create .market.yaml configuration
   * Push to GitHub

2. REPOSITORY INGESTION
   |
   * RRA Module ingests repository
   * Generates knowledge base from code
   * Spawns negotiation agent
   * Links to blockchain smart contract

3. MARKETPLACE LISTING
   |
   * Repository listed in NatLangChain marketplace
   * FSL-1.1-ALv2 terms encoded in smart contract
   * Pricing and terms from .market.yaml
   * Agent ready to negotiate

4. BUYER DISCOVERY
   |
   * Buyer searches marketplace
   * Finds repository
   * Initiates negotiation with agent

5. AI-POWERED NEGOTIATION
   |
   * Buyer Agent <-> Negotiator Agent
   * Natural language discussion
   * Terms, pricing, features discussed
   * Agreement reached

6. ON-CHAIN TRANSACTION
   |
   * Smart contract executes
   * Buyer sends ETH/tokens
   * License NFT minted
   * Revenue distributed automatically

7. ACCESS GRANTED
   |
   * NFT token proves license ownership
   * Buyer gets repository access
   * Terms enforced by blockchain
   * Developer receives payment

8. ONGOING UPDATES
   |
   * Repo updates -> Knowledge base refresh
   * License holders notified on-chain
   * New features -> New negotiations
   * Reputation builds over time
```

### Understanding the Story Protocol Flow

```
+-------------------+     +--------------------+     +-------------------+
|  Your Repo        |---->|  Story Protocol    |---->|  Buyer's Wallet   |
|  (.market.yaml)   |     |  (IP Asset)        |     |  (License NFT)    |
+-------------------+     +--------------------+     +-------------------+
        |                          |                          |
        |                          v                          |
        |                 +--------------------+              |
        +---------------->|  Royalty Vault     |<-------------+
                          |  (Your Revenue)    |
                          +--------------------+
```

1. You register your repo as an **IP Asset** on Story Protocol
2. You attach **License Terms** (price, rights, etc.)
3. Buyers mint **License Tokens** (NFTs) by paying your price
4. Revenue goes to your **Royalty Vault**
5. You **claim** funds from the vault to your wallet

---

## Story Protocol Integration

### Configuring .market.yaml

Create or edit `.market.yaml` in your repo root:

```yaml
# Pricing
license_model: "perpetual"      # perpetual, per-seat, subscription
target_price: "0.05 ETH"        # Your asking price
floor_price: "0.02 ETH"         # Minimum you'll accept

# License Identifier
license_identifier: "FSL-1.1-ALv2"

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

# Revenue Split
revenue_split:
  developer: 91
  platform: 8
  community: 1

# Your Wallet
blockchain:
  wallets:
    developer: "0xYourWalletAddress"
```

The `.market.yaml` file translates your licensing preferences into smart contract parameters:

```yaml
license_identifier: "FSL-1.1-ALv2"  -> Smart contract license type
target_price: "0.05 ETH"            -> Initial NFT mint price
floor_price: "0.02 ETH"             -> Minimum acceptable offer
license_terms: [...]                 -> Encoded in NFT metadata
revenue_split:                       -> On-chain payment distribution
  developer: 91
  platform: 8
  community: 1
```

### Registering Your IP Asset

If you have not registered yet, use Story Protocol's tools:
- Story Protocol App: https://app.story.foundation
- Or use the SDK programmatically

After registration, you receive an **IP Asset ID** (e.g., `0xb77ABcfFbf063a3e6BACA37D72353750475D4E70`).

Add this to your `.market.yaml`:
```yaml
ip_asset_id: "0xYourIPAssetID"
```

### Attaching License Terms

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

### How Buyers Purchase

When someone visits your purchase page:

1. **Connect Wallet** - They click "Connect Wallet"
2. **Switch Network** - Prompted to switch to Story Protocol (Chain ID: 1514)
3. **Purchase** - Click "Purchase License for 0.05 ETH"
4. **Confirm** - Approve transaction in MetaMask
5. **Receive NFT** - License token minted to their wallet

The buyer now owns an NFT proving they have a license to your code.

### Contract Addresses (Mainnet)

| Contract | Address |
|----------|---------|
| Licensing Module | `0xd81fd78f557b457b4350cb95d20b547bfeb4d857` |
| PIL Template | `0x0752b15ee7303033854bde1b32bc7a4008752dc0` |
| Royalty Module | `0x3C27b2D7d30131D4B58C3584FD7c86e104C67883` |
| IP Asset Registry | `0x77319B4031e6eF1250907aa00018B8B1c67a244b` |

---

## How FSL-1.1-ALv2 Integrates with Blockchain

### License as Smart Contract Template

The FSL-1.1-ALv2 license defines the **legal terms**, while the blockchain enforces them:

**Legal Layer (FSL-1.1-ALv2):**
- Defines "Competing Use"
- Specifies permitted purposes
- Sets copyright and attribution requirements
- Grants future Apache 2.0 license

**Blockchain Layer (Smart Contract):**
- Encodes license terms in Solidity
- Enforces payment requirements
- Mints NFT tokens representing licenses
- Automates revenue distribution
- Time-locks future license conversion

### SPDX Headers and On-Chain Verification

Every file with an SPDX header becomes part of the on-chain verification:

```python
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
```

This enables:
- **Proof of ownership** - Copyright holder verified
- **License type identification** - Machine-readable license ID
- **Compliance checking** - Automated verification in smart contracts
- **Audit trails** - Immutable record of licensing

### GitHub Work to Blockchain Asset

Every commit becomes a monetizable blockchain asset:

```
Git Commit
  |
Contains files with SPDX headers
  |
Ingested by RRA Module
  |
Knowledge base generated
  |
Linked to smart contract
  |
Listed in marketplace
  |
Negotiable via AI agent
  |
Purchasable as NFT license
  |
Revenue to developer's wallet
```

---

## The License NFT Structure

When a buyer purchases a license, they receive an ERC-721 NFT token with this metadata:

```json
{
  "name": "RRA Module License",
  "description": "Commercial license for Revenant Repo Agent Module",
  "license_type": "FSL-1.1-ALv2",
  "copyright": "Copyright 2025 Kase Branham",
  "repository": "https://github.com/kase1111-hash/RRA-Module",
  "commit_hash": "13bfc29...",
  "license_tier": "standard",
  "terms": {
    "permitted_uses": [
      "Production deployment",
      "Internal use",
      "Non-competing commercial use"
    ],
    "restrictions": [
      "Cannot build competing RRA systems",
      "Must maintain attribution"
    ],
    "duration": "12 months with updates",
    "seats": 1
  },
  "purchased_at": "2025-12-19T...",
  "purchased_for": "0.05 ETH",
  "buyer_address": "0x...",
  "seller_address": "0x...",
  "future_license": {
    "type": "Apache-2.0",
    "effective_date": "2027-12-19"
  }
}
```

---

## Revenue and Royalties

### Revenue Distribution

When a license is sold for 0.05 ETH:

```
0.05 ETH Payment
  |
Smart Contract Receives
  |
Automatic Distribution:
  * 0.0455 ETH (91%) -> Developer Wallet
  * 0.004 ETH  (8%)  -> NatLangChain Platform
  * 0.0005 ETH (1%)  -> Community Treasury
  |
NFT Minted & Transferred to Buyer
  |
Access Granted via Token Gating
```

**Key Benefits:**
- Instant payment to developer
- No manual invoicing or payment processing
- No intermediaries holding funds
- Transparent revenue splits
- Global accessibility (no payment processor needed)

### Claiming Your Revenue (Story Protocol)

Revenue goes to your IP Asset's **Royalty Vault**, not directly to your wallet. Story Protocol uses a two-step process: snapshot (makes revenue claimable) then claim (transfers to your wallet).

#### Understanding Revenue Flow

```
Buyer pays -> Licensing Module -> Royalty Vault (pending)
                                        |
                               You call snapshot()
                                        |
                               Revenue is claimable
                                        |
                               You call claim()
                                        |
                               Funds go to IP Account
                                        |
                               Transfer to your wallet
```

**Key Concepts:**
- **WIP Token**: Wrapped IP - the native payment token on Story Protocol
- **RT Token**: Royalty Token - represents your share of royalties (100 RT = 100%, uses 6 decimals)
- **IP Account**: ERC-6551 token-bound account associated with your IP Asset

#### Method 1: Python Script (Recommended)

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

#### Method 2: JavaScript via IP Account (Advanced)

For more control, use the JavaScript scripts that interact through the IP Account (ERC-6551):

```bash
# Install dependencies
npm install viem @story-protocol/core-sdk

# Claim via IP Account
PRIVATE_KEY=0xYourPrivateKey node scripts/claim-via-ip-account.js
```

This script:
1. Executes `snapshot()` through your IP Account
2. Claims using `claimByTokenBatchAsSelf()`
3. Transfers WIP tokens from IP Account to your wallet

#### Method 3: Debug and Inspect First

If claiming fails, first inspect your vault state:

```bash
node scripts/debug-vault.js
```

This shows:
- RT (Royalty Token) balances - uses 6 decimals
- Vault WIP balance
- Current snapshot ID
- Claimable amounts

---

## Smart Contract Architecture

```solidity
contract RRALicense {
    // License NFT
    ERC721 public licenseToken;

    // FSL-1.1-ALv2 terms encoded
    LicenseTerms public terms;

    // Revenue split configuration
    RevenueSplit public split;

    // Future license time-lock
    TimeLock public futureApacheLicense;

    function purchaseLicense(
        address buyer,
        LicenseTier tier
    ) external payable {
        require(msg.value >= minPrice, "Below floor price");

        // Mint license NFT
        uint256 tokenId = licenseToken.mint(buyer);

        // Distribute revenue
        distributeRevenue(msg.value);

        // Emit license grant event
        emit LicenseGranted(buyer, tokenId, msg.value);
    }

    function distributeRevenue(uint256 amount) internal {
        uint256 devShare = amount * split.developer / 100;
        uint256 platformShare = amount * split.platform / 100;
        uint256 communityShare = amount * split.community / 100;

        payable(developer).transfer(devShare);
        payable(platform).transfer(platformShare);
        payable(community).transfer(communityShare);
    }

    function checkFutureLicense() public view returns (bool) {
        return block.timestamp >= futureApacheLicense.unlockTime;
    }
}
```

---

## Example Negotiation

Here is how a real negotiation might look:

**Buyer Agent:**
> "I'm interested in licensing the RRA Module for my startup. What's your pricing?"

**Negotiator Agent (Your Repository):**
> "The RRA Module is licensed under FSL-1.1-ALv2 at 0.05 ETH for a standard per-seat license. This includes full source code access, 12 months of updates, and production deployment rights. Our module has 31 fully-tested Python files with 85% test coverage and comprehensive documentation. Would you like to discuss specific licensing terms?"

**Buyer Agent:**
> "Can you do 0.03 ETH? We're an early-stage startup."

**Negotiator Agent:**
> "I appreciate you're early-stage. I can offer 0.04 ETH as my best price, which is very close to my floor. In return, you'll get a high-quality, battle-tested codebase that's already saved hundreds of hours of development time for other users. This investment will pay for itself quickly. Shall we proceed?"

**Buyer Agent:**
> "That works. How do we complete the purchase?"

**Negotiator Agent:**
> "Great! I'll generate the smart contract transaction. You'll send 0.04 ETH to the contract address, and you'll immediately receive an NFT token representing your license. This token proves ownership and grants access to the repository. Ready to proceed?"

**Buyer Agent:**
> "Yes, let's do it."

**-> Smart Contract Executes**
**-> 0.04 ETH Transferred**
**-> License NFT Minted**
**-> Access Granted**
**-> Developer Receives 0.034 ETH**

---

## Advanced Topics

### Verification and Trust

#### On-Chain Verification

Buyers can verify before purchase:

1. **License Authenticity** - Check LICENSE.md hash on-chain
2. **SPDX Compliance** - Verify all files have proper headers
3. **Test Results** - See CI/CD test results on-chain
4. **Reputation Score** - View developer's on-chain reputation
5. **Previous Sales** - See transaction history

#### Continuous Compliance

The GitHub Actions workflow ensures ongoing compliance:

```yaml
# .github/workflows/license-verification.yml
- Runs on every commit
- Verifies all SPDX headers
- Checks LICENSE.md validity
- Confirms copyright notices
- Updates on-chain metadata
```

### Future License Transition

The FSL-1.1-ALv2 includes an automatic transition to Apache 2.0:

**Timeline:**
```
Day 0 (2025-12-19)
  |
  FSL-1.1-ALv2 Active
  * Restricted commercial use
  * Blockchain licensing required
  * Revenue flowing to developer
  |
Day 730 (2027-12-19)
  |
  Apache 2.0 Activated
  * Fully permissive
  * Free for all uses
  * No restrictions
```

**Smart Contract Implementation:**
```solidity
function getCurrentLicense() public view returns (string) {
    if (block.timestamp < FUTURE_LICENSE_DATE) {
        return "FSL-1.1-ALv2";
    } else {
        return "Apache-2.0";
    }
}
```

This ensures:
- Developers earn during initial period
- Code eventually becomes fully open
- Automatic transition (no manual updates needed)
- Verifiable on-chain

### Why Blockchain Over Traditional Licensing

#### For Developers

**Traditional Way:**
- Manual sales and invoicing
- Payment processor fees (3-5%)
- Geographic restrictions
- Legal complexity
- High barrier to entry

**Blockchain Way:**
- Fully automated sales
- Minimal fees (~1-2% gas)
- Global accessibility
- Smart contract enforcement
- Zero barrier to entry

#### For Buyers

**Traditional Way:**
- Negotiate via email
- Manual license agreements
- Payment friction
- Unclear terms
- No transferability

**Blockchain Way:**
- AI-powered instant negotiation
- Clear, encoded terms
- One-click purchase
- Transparent on-chain record
- Transferable NFT licenses

### Troubleshooting

#### "bad address checksum" Error

The purchase page uses lowercase addresses. If you see this error:
- Make sure you are using the latest `buy-license.html`
- All addresses should be lowercase in the JavaScript

#### "No Royalty Vault found"

This means either:
- The IP Asset was not registered with a royalty policy
- No purchases have been made yet
- Check StoryScan for your IP Asset's vault

#### "Transaction failed" on Purchase

Common causes:
- Insufficient IP tokens for gas
- Wrong network (should be Story Protocol, Chain ID 1514)
- License terms not attached yet

#### Can't Find My Revenue

Revenue flow:
1. Buyer pays -> Licensing Module
2. Licensing Module -> Your Royalty Vault (pending)
3. You call `snapshot()` -> Makes funds claimable
4. You call `claimRevenue()` -> Funds go to IP Account
5. Transfer from IP Account -> Your wallet

Use `claim_royalties.py` or `claim-via-ip-account.js` to complete this flow.

#### RT Token Shows Tiny Balance

RT (Royalty Tokens) use 6 decimals, not 18 like ETH. A balance of `100000000` means:
- Raw value: 100,000,000
- With 6 decimals: 100 RT (= 100% ownership)

Use `formatUnits(balance, 6)` in JavaScript, not `formatEther()`.

#### Claim Methods Return "Unauthorized"

The IP Account (your IP Asset address) is an ERC-6551 token-bound account. Only the NFT owner can execute transactions through it. Verify:

```bash
# Check IP Account ownership
node scripts/debug-vault.js
```

If ownership shows a different address, you need to claim from that wallet.

#### "Snapshot ID Not Found" Error

You need to create a snapshot before claiming:
1. Call `vault.snapshot()` first
2. Wait for transaction confirmation
3. Then call the claim function with the snapshot ID

The `claim-via-ip-account.js` script handles this automatically.

#### Vault Has Funds But Nothing Claimable

This typically means:
- Revenue has not been snapshotted yet
- You have already claimed for the current snapshot
- The funds are allocated to a different RT holder

Run `debug-vault.js` to see current claimable amounts.

---

## Scripts Reference

### Python Scripts

#### enable_story_purchases.py

Attaches license terms to enable purchasing.

```cmd
python scripts/enable_story_purchases.py [OPTIONS]

Options:
  --ip-asset       IP Asset address (required)
  --market-config  Path to .market.yaml (default: .market.yaml)
  --private-key    Your private key (or use STORY_PRIVATE_KEY env var)
  --network        mainnet or testnet (default: mainnet)
  --output-dir     Where to save buyer HTML (default: public)
```

#### claim_royalties.py

Claims pending revenue from your Royalty Vault.

```cmd
python scripts/claim_royalties.py [OPTIONS]

Options:
  --ip-asset     IP Asset address (default: from .market.yaml)
  --private-key  Your private key (or use STORY_PRIVATE_KEY env var)
  --network      mainnet or testnet (default: mainnet)
```

### JavaScript Scripts

Install dependencies first:
```bash
npm install viem @story-protocol/core-sdk
```

| Script | Purpose | Usage |
|--------|---------|-------|
| `mint-license.js` | Mint license via SDK | `PRIVATE_KEY=0x... node scripts/mint-license.js` |
| `debug-vault.js` | Inspect vault state | `node scripts/debug-vault.js` |
| `claim-via-ip-account.js` | Claim via ERC-6551 | `PRIVATE_KEY=0x... node scripts/claim-via-ip-account.js` |
| `claim-via-module.js` | Claim via RoyaltyModule | `PRIVATE_KEY=0x... node scripts/claim-via-module.js` |
| `claim-fixed.js` | Claim with 6-decimal RT | `PRIVATE_KEY=0x... node scripts/claim-fixed.js` |
| `check-royalty-vault.js` | Quick vault check | `node scripts/check-royalty-vault.js` |
| `pay-royalty.js` | Test royalty payment | `PRIVATE_KEY=0x... node scripts/pay-royalty.js` |

### Developer Workflow Summary

#### Step 1: Add License to Your Repository

```bash
# 1. Add LICENSE.md
cp templates/LICENSE.md ./LICENSE.md

# 2. Add SPDX headers to all files
python scripts/add_license_headers.py

# 3. Verify compliance
python scripts/verify_license.py
```

#### Step 2: Configure Monetization

```bash
# Create .market.yaml with your terms
cat > .market.yaml <<EOF
license_identifier: "FSL-1.1-ALv2"
target_price: "0.05 ETH"
floor_price: "0.02 ETH"
license_model: "Per-seat"
# ... additional configuration
EOF
```

#### Step 3: Deploy to Blockchain

```bash
# Initialize RRA for your repository
rra init
rra ingest https://github.com/yourname/yourrepo

# This will:
# - Ingest your repository
# - Generate knowledge base
# - Spawn negotiation agent
# - Deploy smart contract
# - List in marketplace
```

#### Step 4: Earn Automatically

**That's it!** Your repository is now:
- Listed in the NatLangChain marketplace
- Represented by an AI negotiation agent
- Purchasable via blockchain transactions
- Earning revenue automatically

---

## Integration Points

This repository demonstrates all integration points:

| Component | Location | Purpose |
|-----------|----------|---------|
| **License File** | `LICENSE.md` | Legal foundation (FSL-1.1-ALv2) |
| **SPDX Headers** | All `.py` files | Machine-readable licensing |
| **Market Config** | `.market.yaml` | Blockchain monetization settings |
| **Verification** | `scripts/verify_license.py` | Compliance checking |
| **Automation** | `.github/workflows/` | Continuous verification |
| **Smart Contract** | `src/rra/contracts/` | On-chain enforcement |
| **Agents** | `src/rra/agents/` | Automated negotiation |
| **Documentation** | `LICENSING.md` | Human-readable guide |

---

## Example: RRA-Module

This repository is monetized using this exact process:

- **IP Asset:** `0xb77ABcfFbf063a3e6BACA37D72353750475D4E70`
- **Price:** 0.05 ETH
- **License Terms ID:** 3 (Commercial Remix)
- **Purchase Page:** [Buy License](https://kase1111-hash.github.io/RRA-Module/buy-license.html)
- **StoryScan:** [View IP Asset](https://www.storyscan.io/token/0xb77ABcfFbf063a3e6BACA37D72353750475D4E70)

---

## Next Steps

1. **Test with a small purchase** - Buy your own license to verify flow
2. **Add badge to README** - Make purchasing visible
3. **Share your purchase link** - Twitter, Discord, etc.
4. **Set up royalty claiming schedule** - Weekly or after each sale

---

## Vision

This system enables:

- **Global monetization** - Developers anywhere can earn
- **Automation** - No manual sales or negotiation needed
- **Blockchain enforcement** - Terms guaranteed by smart contracts
- **Fair revenue** - Direct payment to developers
- **Low barrier** - Anyone can start earning from their code
- **Reputation building** - On-chain track record grows over time
- **Future freedom** - Code eventually becomes fully open

**The future of code monetization is automated, blockchain-based, and globally accessible.**

---

## Support and Resources

- **Full Documentation:** [docs/README.md](README.md)
- **License Compliance Guide:** [../LICENSING.md](../LICENSING.md)
- **License Terms:** [../LICENSE.md](../LICENSE.md)
- **Buyer Notice:** [../Buyer-Beware.md](../Buyer-Beware.md)
- **RRA Module Overview:** [../README.md](../README.md)
- **GitHub Issues:** https://github.com/kase1111-hash/RRA-Module/issues
- **Story Protocol Docs:** https://docs.story.foundation
- **StoryScan Explorer:** https://storyscan.io

---

**License:** FSL-1.1-ALv2
**Copyright:** 2025 Kase Branham
**Last Updated:** 2025-12-19
