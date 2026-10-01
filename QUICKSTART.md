# RRA Module - Quick Start Guide

Get started with the Revenant Repo Agent Module in minutes!

**Version:** 1.0.1-beta | **Tests:** 1,237 passing | **Security:** A- rating

## Installation

```bash
# Install from PyPI (when published)
pip install rra-module

# Or install from source
git clone https://github.com/kase1111-hash/RRA-Module.git
cd RRA-Module
pip install -e .
```

## Quick Start

### 1. Initialize Your Repository

Create a `.market.yaml` configuration file in your repository:

```bash
cd your-repository
rra init .
```

This creates a default configuration that you can customize:

```yaml
license_model: "per-seat"
target_price: "0.05 ETH"
floor_price: "0.02 ETH"
allow_custom_fork_rights: true
features:
  - "Full source code access"
  - "Regular updates"
  - "Developer support"
```

### 2. Ingest Your Repository

Generate a knowledge base for your repository:

```bash
rra ingest https://github.com/your-username/your-repo.git
```

This will:
- Clone your repository
- Parse code structure and dependencies
- Extract API endpoints and documentation
- Create an Agent Knowledge Base (AKB)

### 3. Generate Purchase Links

Purchase links point at your repository's Story Protocol IP asset, so register it first
(`rra story register`, below), then add its `license_terms_id` to `.market.yaml`.
Create shareable purchase links, badges, and QR codes:

```bash
rra purchase-link https://github.com/username/my-awesome-project --config .market.yaml
rra links https://github.com/username/my-awesome-project --config .market.yaml --register
```

Or pass the IDs directly: `--ip-asset 0x... --terms 12345 [--network testnet]`.

### 4. Automated GitHub Actions (Optional)

Add the RRA workflow to your repository to enable automatic ingestion on push:

```yaml
# .github/workflows/rra-ingest.yml
name: RRA Repository Ingestion

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install rra-module
      - run: rra ingest https://github.com/${{ github.repository }}.git
```

## Example: Complete Workflow

```bash
# 1. Create a new repository or use existing one
cd my-awesome-project

# 2. Initialize RRA
rra init .

# 3. Customize .market.yaml
# Edit target_price, floor_price, features, etc.

# 4. Ingest repository
rra ingest https://github.com/username/my-awesome-project.git

# 5. View repository info
rra info agent_knowledge_bases/username_my-awesome-project_kb.json

# 6. Register on Story Protocol, then generate purchase links
rra story register https://github.com/username/my-awesome-project.git --wallet 0xYourWallet
rra purchase-link https://github.com/username/my-awesome-project.git --config .market.yaml

# 7. List all ingested repos
rra list
```

## API Server

Run the RRA API server for programmatic access:

```bash
# Start the server
python -m rra.api.server

# Or with uvicorn
uvicorn rra.api.server:app --reload
```

Then access the API:

```bash
# Ingest a repository
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo.git"}'

# Generate purchase links
curl -X POST http://localhost:8000/api/links/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $RRA_API_KEY" \
  -d '{"repo_url": "https://github.com/user/repo.git"}'

# List repositories
curl http://localhost:8000/api/repositories
```

## Configuration Reference

### .market.yaml Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `license_model` | string | Yes | Licensing model: `per-seat`, `subscription`, `one-time`, `perpetual`, `custom` |
| `target_price` | string | Yes | Target price (e.g., "0.05 ETH") |
| `floor_price` | string | Yes | Minimum acceptable price |
| `protocol_integrations.story_protocol` | map | No | Story Protocol settings: `enabled`, `network`, `ip_asset_id`, `license_terms_id` (used by `--config`) |
| `features` | list | No | Key features to highlight |
| `developer_wallet` | string | No | Ethereum wallet address for payments |
| `royalty_on_derivatives` | float | No | Royalty percentage (0.0-1.0) for forks |

### CLI Commands

```bash
# Initialize repository with .market.yaml
rra init <path> [--target-price=0.05 ETH] [--floor-price=0.02 ETH]
                 [--license-model=per-seat] [--wallet=0x...]

# Ingest repository and generate knowledge base
rra ingest <repo-url> [--workspace=./cloned_repos] [--force]
                      [--verify/--no-verify] [--categorize/--no-categorize]
                      [--wallet=0x...] [--network=testnet]

# Generate the purchase link for a registered IP asset
rra purchase-link <repo-url> (--config .market.yaml | --ip-asset 0x... --terms <id>)
                  [--network=mainnet|testnet] [--format=table|json|markdown]

# Generate shareable links, badges, and QR codes
rra links <repo-url> [--config .market.yaml | --ip-asset 0x... --terms <id>]
                     [--register] [--format=table|json|markdown]

# List all ingested repositories
rra list [--workspace=./agent_knowledge_bases]

# Show repository info
rra info <kb-path>

# Show example .market.yaml configuration
rra example

# Resolve a repository ID to its URL
rra resolve <repo-id>

# Verify repository code quality
rra verify <repo-url> [--skip-tests] [--skip-security] [--workspace=./cloned_repos]

# Categorize a repository
rra categorize <repo-url> [--workspace=./cloned_repos]

# Story Protocol commands
rra story status                    # Show deployment status
rra story register <repo-url>       # Register as IP Asset
rra story info <ip-asset-id>        # Get IP Asset info
rra story royalties <ip-asset-id>   # Get royalty statistics
```

## Advanced Usage

### Code Verification

Verify repository code quality before ingestion:

```bash
rra verify https://github.com/user/repo.git
```

This runs:
- Test suite detection and execution
- Linting and code quality checks
- Security vulnerability scanning
- Build/installation verification
- README alignment checking

### Story Protocol Registration

Register your repository as an IP Asset on Story Protocol:

```bash
# Set environment variables
export STORY_PRIVATE_KEY=0x...
export STORY_RPC_URL=https://aeneid.storyrpc.io

# Register IP Asset (with dry run first)
rra story register https://github.com/user/repo.git \
    --wallet 0x... --network testnet --dry-run

# Execute registration
rra story register https://github.com/user/repo.git \
    --wallet 0x... --network testnet
```

### Deep Links and Embedding

Generate shareable links for your repository:

```bash
# Generate all link formats for your registered IP asset
rra links https://github.com/user/repo.git --ip-asset 0x... --terms 12345

# Output includes:
# - Purchase page URL (one-click license mint)
# - Story Protocol explorer URL
# - QR code URL
# - README badge markdown
# - Embeddable buy button HTML
```

The IP asset details are saved, so later runs for the same repository don't need the flags.
Use `--format json` for machine-readable output.

## Next Steps

- Read the [full README](README.md) for detailed information
- Check out [examples](examples/README.md) for more use cases
- Review [blockchain licensing guide](docs/BLOCKCHAIN-LICENSING.md) for monetization
- Explore [Story Protocol integration](docs/INTEGRATIONS.md#story-protocol) for programmable IP
- See [DeFi integration](docs/DEFI-INTEGRATION.md) for yield tokens and lending
- Review [security audit](docs/SECURITY-AUDIT.md) for security best practices
- See [full documentation index](docs/README.md) for all guides

## Getting Help

- CLI help: `rra --help`
- Command help: `rra <command> --help`
- Story Protocol: `rra story --help`
- Issues: https://github.com/kase1111-hash/RRA-Module/issues
- Documentation: [docs/README.md](docs/README.md)

## License

This project is licensed under FSL-1.1-ALv2.

See [LICENSE.md](LICENSE.md) for the complete license text and [LICENSING.md](LICENSING.md) for compliance guidelines.
