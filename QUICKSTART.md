# RRA Module - Quick Start Guide

Get started with the Revenant Repo Agent Module in minutes!

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
negotiation_style: "concise"
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

### 3. Start the Negotiation Agent

Launch an interactive negotiation session:

```bash
rra agent path/to/your_repo_kb.json --interactive
```

Or run a simulation:

```bash
rra agent path/to/your_repo_kb.json --simulate
```

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

# 6. Test negotiation
rra agent agent_knowledge_bases/username_my-awesome-project_kb.json --simulate

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

# Start negotiation
curl -X POST http://localhost:8000/api/negotiate/start \
  -H "Content-Type: application/json" \
  -d '{"kb_path": "agent_knowledge_bases/repo_kb.json"}'

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
| `negotiation_style` | string | No | Style: `concise`, `persuasive`, `strict`, `adaptive` (default: `concise`) |
| `features` | list | No | Key features to highlight |
| `developer_wallet` | string | No | Ethereum wallet address for payments |
| `royalty_on_derivatives` | float | No | Royalty percentage (0.0-1.0) for forks |

### CLI Commands

```bash
# Initialize repository
rra init <path> [options]

# Ingest repository
rra ingest <repo-url> [--workspace=./cloned_repos] [--force]

# Manage agents
rra agent <kb-path> [--interactive] [--simulate]

# List repositories
rra list [--workspace=./agent_knowledge_bases]

# Show repository info
rra info <kb-path>

# Show example configuration
rra example
```

## Next Steps

- Read the [full README](README.md) for detailed information
- Check out [examples](examples/) for more use cases
- Review [smart contracts](src/rra/contracts/) for blockchain integration
- Explore the [API documentation](src/rra/api/)

## Getting Help

- CLI help: `rra --help`
- Command help: `rra <command> --help`
- Issues: https://github.com/kase1111-hash/RRA-Module/issues

## License

This project is licensed under the MIT License - see [LICENSE.md](LICENSE.md) for details.
