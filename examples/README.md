# RRA Module Examples

This directory contains example scripts, workflows, and GitHub Actions demonstrating various features of the RRA Module.

## Quick Start

```bash
# Install dependencies
make install

# Run a workflow
PRIVATE_KEY=0x... make workflow-license
```

## Directory Structure

```
examples/
├── README.md                    # This file
├── workflows/                   # JavaScript workflow examples
│   ├── complete-license-workflow.js
│   ├── royalty-management-workflow.js
│   └── derivative-tracking-workflow.js
├── github-actions/              # GitHub Actions workflow templates
│   ├── royalty-claim.yml
│   ├── release-license.yml
│   └── royalty-report.yml
├── story_protocol_example.py    # Python Story Protocol integration
├── simple_negotiation.py        # Basic negotiation example
└── blockchain_licensing_demo.py # Blockchain demo
```

---

## JavaScript Workflows

Located in `workflows/`, these are complete Node.js scripts for common operations.

### Complete License Workflow

Full licensing process from verification to minting.

```bash
PRIVATE_KEY=0x... node examples/workflows/complete-license-workflow.js
```

### Royalty Management Workflow

Check vault status, view claimable amounts, and understand revenue flow.

```bash
PRIVATE_KEY=0x... node examples/workflows/royalty-management-workflow.js
```

### Derivative Tracking Workflow

Track derivative IP relationships and monitor royalty flows.

```bash
node examples/workflows/derivative-tracking-workflow.js [IP_ASSET_ID]
```

See [workflows/README.md](workflows/README.md) for detailed documentation.

---

## GitHub Actions Templates

Located in `github-actions/`, these are ready-to-use workflow templates.

### Automated Royalty Claiming

Claims pending royalties on a weekly schedule.

```bash
cp examples/github-actions/royalty-claim.yml .github/workflows/
```

### Mint License on Release

Automatically mints a license token when you publish a release.

```bash
cp examples/github-actions/release-license.yml .github/workflows/
```

### Weekly Royalty Report

Generates weekly royalty status reports as GitHub Issues.

```bash
cp examples/github-actions/royalty-report.yml .github/workflows/
```

See [github-actions/README.md](github-actions/README.md) for setup instructions.

---

## Python Examples

### Story Protocol Integration

**File:** `story_protocol_example.py`

Comprehensive example showing Story Protocol integration:

- IP Asset registration for code repositories
- Programmable IP License (PIL) term configuration
- Derivative repository registration with automatic royalty tracking
- Querying derivative graphs and royalty statistics

**Usage:**

```bash
# Set environment variables
export ETHEREUM_RPC_URL="https://sepolia.infura.io/v3/YOUR_KEY"
export ETHEREUM_ADDRESS="0xYourAddress"
export ETHEREUM_PRIVATE_KEY="0xYourPrivateKey"

# Run the example
python examples/story_protocol_example.py
```

**Note:** The example runs in simulation mode by default to prevent accidental transactions. Uncomment the actual transaction code blocks to execute real blockchain operations.

### Simple Negotiation

**File:** `simple_negotiation.py`

Basic example of the negotiation flow.

### Blockchain Licensing Demo

**File:** `blockchain_licensing_demo.py`

Demonstrates blockchain-based licensing concepts.

---

## Configuration Files

### Market YAML Examples

- `default.market.yaml` - Default configuration template
- `example_market.yaml` - Example with all options documented

---

## Prerequisites

### For Python Examples

```bash
pip install -r requirements.txt
```

### For JavaScript Workflows

```bash
cd scripts && npm install
```

### Environment Setup

Create a `.env` file:
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required variables:
- `PRIVATE_KEY` or `STORY_PRIVATE_KEY` - Wallet private key
- `STORY_IP_ASSET_ID` - Your IP Asset address (or set in .market.yaml)

### Get Testnet Tokens

- For Story Protocol testnet: https://faucet.story.foundation/

---

## Using Make

The project includes a Makefile for common operations:

```bash
# Development
make install          # Install all dependencies
make test             # Run all tests
make lint             # Run linters

# Story Protocol
make story-check      # Check royalty vault
make story-mint       # Mint license token
make story-claim      # Claim royalties
make story-debug      # Debug vault state

# Workflows
make workflow-license     # License workflow
make workflow-royalty     # Royalty workflow
make workflow-derivative  # Derivative tracking

# Marketplace
make marketplace-dev   # Start dev server
make marketplace-build # Production build
```

---

## Documentation

For detailed documentation, see:
- [Usage Guide](../docs/USAGE-GUIDE.md) - Complete how-to guide
- [Story Protocol Integration](../docs/STORY-PROTOCOL-INTEGRATION.md) - On-chain integration
- [Selling Licenses](../docs/SELLING-LICENSES.md) - License management
- [Full Documentation Index](../docs/README.md)

---

## License

This project is licensed under FSL-1.1-ALv2.

See [LICENSE.md](../LICENSE.md) for the complete license text and [LICENSING.md](../LICENSING.md) for compliance guidelines.
