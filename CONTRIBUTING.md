# Contributing to RRA Module

Thank you for your interest in contributing to the Revenant Repo Agent Module!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/RRA-Module.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Run tests: `pytest`
6. Commit with clear messages
7. Push and create a pull request

## Development Setup

For basic installation, see the [Quick Start Guide](QUICKSTART.md#installation).

For development setup with additional tools:

```bash
# Clone and install (see QUICKSTART.md for details)
git clone https://github.com/kase1111-hash/RRA-Module.git
cd RRA-Module
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your configuration (API keys, wallet addresses, etc.)
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rra --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

## Code Style

We use Black for code formatting and Flake8 for linting:

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

## Project Structure

```
RRA-Module/
├── src/rra/              # Main package (31+ modules)
│   ├── agents/           # Negotiator/Buyer agents
│   ├── api/              # FastAPI server, webhooks, WebSocket
│   ├── analytics/        # Entropy scoring, clause patterns
│   ├── bundling/         # Multi-repo bundle management
│   ├── chains/           # Multi-chain configuration
│   ├── cli/              # Command-line interface
│   ├── config/           # Configuration management
│   ├── contracts/        # Smart contract interfaces
│   ├── crypto/           # Pedersen commitments, Shamir sharing
│   ├── governance/       # DAO, treasury, voting
│   ├── identity/         # DID resolver
│   ├── ingestion/        # Repository ingestion & knowledge base
│   ├── integration/      # NatLangChain ecosystem
│   ├── integrations/     # Story Protocol, Superfluid, GitHub
│   ├── legal/            # Jurisdiction, compliance, RWA
│   ├── negotiation/      # Clause hardening, pressure logic
│   ├── oracles/          # Price oracle, event bridge
│   ├── pricing/          # Adaptive pricing engine
│   ├── privacy/          # Batch queue, secret sharing
│   ├── reconciliation/   # Multi-party dispute resolution
│   ├── reputation/       # Reputation tracking
│   ├── security/         # API auth, secrets management
│   ├── services/         # Deep links, URL generation
│   ├── storage/          # Session storage, persistence
│   ├── transaction/      # Two-step verification
│   └── verification/     # Code verification, blockchain links
├── contracts/            # Solidity smart contracts (Foundry)
├── marketplace/          # Next.js marketplace frontend
├── sdks/                 # iOS and Android SDKs
├── tests/                # Test suite (42 files, 1,237+ tests)
├── scripts/              # Blockchain & automation scripts
├── examples/             # Usage examples and workflows
└── docs/                 # Documentation
```

## Adding New Features

1. **Configuration Changes**: Update `src/rra/config/market_config.py`
2. **Agent Behavior**: Modify `src/rra/agents/negotiator.py`
3. **Ingestion Logic**: Edit `src/rra/ingestion/repo_ingester.py`
4. **API Endpoints**: Add to `src/rra/api/server.py`
5. **CLI Commands**: Update `src/rra/cli/main.py`

Always add tests for new features in the `tests/` directory.

## Commit Messages

Follow conventional commits format:

- `feat: add new negotiation strategy`
- `fix: correct price parsing bug`
- `docs: update README with examples`
- `test: add tests for buyer agent`
- `refactor: simplify knowledge base loading`

## Pull Request Process

1. Update documentation for any user-facing changes
2. Add tests for new functionality
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Request review from maintainers

## Smart Contract Development

The project uses a Foundry-style layout for Solidity contracts in `contracts/`.

```bash
# Install Foundry (if not already installed)
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Compile contracts
forge build

# Run contract tests
forge test

# Deploy (using Foundry scripts)
forge script contracts/script/DeployLicenseEntropyOracle.s.sol --rpc-url <RPC_URL> --broadcast
```

## Documentation

- Update docstrings for all public functions
- Add examples to `examples/` directory
- Update README.md and QUICKSTART.md as needed
- Keep ROADMAP.md updated with roadmap items
- Update relevant docs in `docs/` directory
- Maintain cross-references in docs/README.md

## Reporting Issues

Use our issue templates for better organization:

- **[Bug Reports](https://github.com/kase1111-hash/RRA-Module/issues/new?template=bug_report.yml)** - Report bugs and unexpected behavior
- **[Feature Requests](https://github.com/kase1111-hash/RRA-Module/issues/new?template=feature_request.yml)** - Suggest new features

## Questions?

- Check the [Support Guide](SUPPORT.md) for help resources
- Open an issue for bugs or feature requests
- Join discussions in GitHub Discussions
- Contact maintainers via GitHub

## License

By contributing, you agree that your contributions will be licensed under the FSL-1.1-ALv2 license.

See [LICENSE.md](LICENSE.md) for the complete license text and [LICENSING.md](LICENSING.md) for compliance guidelines.
