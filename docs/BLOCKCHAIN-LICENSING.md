# Blockchain-Based Automated Code Monetization

## Overview

This repository demonstrates the complete integration between the **FSL-1.1-ALv2 license** and the **RRA Module's blockchain licensing system**. This enables automated monetization of GitHub code without manual sales handling.

## The Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMATED MONETIZATION FLOW                  │
└─────────────────────────────────────────────────────────────────┘

1. DEVELOPER SETUP
   ↓
   • Add LICENSE.md (FSL-1.1-ALv2)
   • Add SPDX headers to all source files
   • Create .market.yaml configuration
   • Push to GitHub

2. REPOSITORY INGESTION
   ↓
   • RRA Module ingests repository
   • Generates knowledge base from code
   • Spawns negotiation agent
   • Links to blockchain smart contract

3. MARKETPLACE LISTING
   ↓
   • Repository listed in NatLangChain marketplace
   • FSL-1.1-ALv2 terms encoded in smart contract
   • Pricing and terms from .market.yaml
   • Agent ready to negotiate

4. BUYER DISCOVERY
   ↓
   • Buyer searches marketplace
   • Finds repository
   • Initiates negotiation with agent

5. AI-POWERED NEGOTIATION
   ↓
   • Buyer Agent ←→ Negotiator Agent
   • Natural language discussion
   • Terms, pricing, features discussed
   • Agreement reached

6. ON-CHAIN TRANSACTION
   ↓
   • Smart contract executes
   • Buyer sends ETH/tokens
   • License NFT minted
   • Revenue distributed automatically

7. ACCESS GRANTED
   ↓
   • NFT token proves license ownership
   • Buyer gets repository access
   • Terms enforced by blockchain
   • Developer receives payment

8. ONGOING UPDATES
   ↓
   • Repo updates → Knowledge base refresh
   • License holders notified on-chain
   • New features → New negotiations
   • Reputation builds over time
```

## How FSL-1.1-ALv2 Integrates with Blockchain

### 1. License as Smart Contract Template

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

### 2. SPDX Headers → On-Chain Verification

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

### 3. .market.yaml → Smart Contract Configuration

The `.market.yaml` file translates your licensing preferences into smart contract parameters:

```yaml
license_identifier: "FSL-1.1-ALv2"  → Smart contract license type
target_price: "0.05 ETH"            → Initial NFT mint price
floor_price: "0.02 ETH"             → Minimum acceptable offer
license_terms: [...]                → Encoded in NFT metadata
revenue_split:                      → On-chain payment distribution
  developer: 85
  platform: 10
  community: 5
```

### 4. GitHub Work → Blockchain Asset

Every commit becomes a monetizable blockchain asset:

```
Git Commit
  ↓
Contains files with SPDX headers
  ↓
Ingested by RRA Module
  ↓
Knowledge base generated
  ↓
Linked to smart contract
  ↓
Listed in marketplace
  ↓
Negotiable via AI agent
  ↓
Purchasable as NFT license
  ↓
Revenue to developer's wallet
```

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

## Revenue Flow

When a license is sold for 0.05 ETH:

```
0.05 ETH Payment
  ↓
Smart Contract Receives
  ↓
Automatic Distribution:
  • 0.0425 ETH (85%) → Developer Wallet
  • 0.005 ETH  (10%) → NatLangChain Platform
  • 0.0025 ETH (5%)  → Community Treasury
  ↓
NFT Minted & Transferred to Buyer
  ↓
Access Granted via Token Gating
```

**Key Benefits:**
- ✅ Instant payment to developer
- ✅ No manual invoicing or payment processing
- ✅ No intermediaries holding funds
- ✅ Transparent revenue splits
- ✅ Global accessibility (no payment processor needed)

## Developer Workflow

### Step 1: Add License to Your Repository

```bash
# 1. Add LICENSE.md
cp templates/LICENSE.md ./LICENSE.md

# 2. Add SPDX headers to all files
python scripts/add_license_headers.py

# 3. Verify compliance
python scripts/verify_license.py
```

### Step 2: Configure Monetization

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

### Step 3: Deploy to Blockchain

```bash
# Initialize RRA for your repository
natlang rra init https://github.com/yourname/yourrepo

# This will:
# - Ingest your repository
# - Generate knowledge base
# - Spawn negotiation agent
# - Deploy smart contract
# - List in marketplace
```

### Step 4: Earn Automatically

**That's it!** Your repository is now:
- ✅ Listed in the NatLangChain marketplace
- ✅ Represented by an AI negotiation agent
- ✅ Purchasable via blockchain transactions
- ✅ Earning revenue automatically

## Example Negotiation

Here's how a real negotiation might look:

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

**→ Smart Contract Executes**
**→ 0.04 ETH Transferred**
**→ License NFT Minted**
**→ Access Granted**
**→ Developer Receives 0.034 ETH**

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

## Verification & Trust

### On-Chain Verification

Buyers can verify before purchase:

1. **License Authenticity** - Check LICENSE.md hash on-chain
2. **SPDX Compliance** - Verify all files have proper headers
3. **Test Results** - See CI/CD test results on-chain
4. **Reputation Score** - View developer's on-chain reputation
5. **Previous Sales** - See transaction history

### Continuous Compliance

The GitHub Actions workflow ensures ongoing compliance:

```yaml
# .github/workflows/license-verification.yml
- Runs on every commit
- Verifies all SPDX headers
- Checks LICENSE.md validity
- Confirms copyright notices
- Updates on-chain metadata
```

## Why This Matters

### For Developers

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

### For Buyers

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

## Future License Transition

The FSL-1.1-ALv2 includes an automatic transition to Apache 2.0:

**Timeline:**
```
Day 0 (2025-12-19)
  ↓
  FSL-1.1-ALv2 Active
  • Restricted commercial use
  • Blockchain licensing required
  • Revenue flowing to developer
  ↓
Day 730 (2027-12-19)
  ↓
  Apache 2.0 Activated
  • Fully permissive
  • Free for all uses
  • No restrictions
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
- ✅ Developers earn during initial period
- ✅ Code eventually becomes fully open
- ✅ Automatic transition (no manual updates needed)
- ✅ Verifiable on-chain

## Getting Started

### For This Repository

This repository is already configured and ready:

```bash
# Verify licensing setup
python scripts/verify_license.py

# View market configuration
cat .market.yaml

# Run compliance tests
python tests/test_licensing.py

# Deploy to blockchain (when ready)
natlang rra init https://github.com/kase1111-hash/RRA-Module
```

### For Your Own Repository

```bash
# 1. Clone RRA Module
git clone https://github.com/kase1111-hash/RRA-Module

# 2. Copy licensing templates
cp RRA-Module/LICENSE.md ./LICENSE.md
cp RRA-Module/.market.yaml ./.market.yaml
cp -r RRA-Module/scripts ./scripts

# 3. Add SPDX headers
python scripts/add_license_headers.py

# 4. Customize .market.yaml
vim .market.yaml

# 5. Verify compliance
python scripts/verify_license.py

# 6. Deploy to blockchain
natlang rra init https://github.com/yourname/yourrepo
```

## Support & Resources

- **Full Documentation:** [docs/README.md](README.md)
- **License Compliance Guide:** [../LICENSING.md](../LICENSING.md)
- **License Terms:** [../LICENSE.md](../LICENSE.md)
- **Buyer Notice:** [../Buyer-Beware.md](../Buyer-Beware.md)
- **RRA Module Overview:** [../README.md](../README.md)
- **GitHub Issues:** https://github.com/kase1111-hash/RRA-Module/issues

## Vision

This system enables:

- 🌍 **Global monetization** - Developers anywhere can earn
- 🤖 **Automation** - No manual sales or negotiation needed
- ⛓️ **Blockchain enforcement** - Terms guaranteed by smart contracts
- 💰 **Fair revenue** - Direct payment to developers
- 🚀 **Low barrier** - Anyone can start earning from their code
- 📈 **Reputation building** - On-chain track record grows over time
- 🔓 **Future freedom** - Code eventually becomes fully open

**The future of code monetization is automated, blockchain-based, and globally accessible.**

---

**License:** FSL-1.1-ALv2
**Copyright:** 2025 Kase Branham
**Last Updated:** 2025-12-19
