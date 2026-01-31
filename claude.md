# Claude.md - RRA-Module Development Guide

## Project Overview

**RRA-Module** (Revenant Repo Agent Module) is a Python/Smart-contract extension for the NatLangChain framework that transforms dormant GitHub repositories into autonomous AI-driven licensing agents. The system enables developers to monetize abandoned code through automated negotiations and blockchain-based licensing.

**Core Capabilities:**
- AI-powered license negotiation agents (LLM-based)
- NFT-based license tokens via smart contracts (EVM networks)
- Story Protocol integration for programmable IP licensing
- Zero-touch monetization with `.market.yaml` configuration
- Multi-chain support: Ethereum, Polygon, Arbitrum, Base, Optimism

## Architecture

```
src/rra/
├── config/          # .market.yaml parsing (MarketConfig)
├── ingestion/       # Repository cloning and knowledge base generation
├── agents/          # Negotiator and Buyer agent implementations
├── contracts/       # Smart contract interfaces (license_nft, story_protocol)
├── chains/          # Multi-chain support and RPC handling
├── verification/    # Code quality and security verification
├── crypto/          # Shamir secret sharing, Pedersen commitments
├── privacy/         # Identity management, ZK proofs
├── auth/            # FIDO2/WebAuthn authentication
├── transaction/     # Two-step verification, blockchain transactions
├── defi/            # Yield tokens, IPFi lending
├── pricing/         # Adaptive pricing engine
├── governance/      # DAO, treasury, voting
├── legal/           # Jurisdiction detection, compliance
├── api/             # FastAPI server with webhooks
└── cli/             # Click-based CLI (15+ commands)
```

## Key Entry Points

**CLI:** `rra` command (defined in `src/rra/cli/main.py`)
```bash
rra init          # Initialize repo with .market.yaml
rra ingest        # Clone repo and generate knowledge base
rra agent         # Start negotiation agent
rra verify        # Verify code quality
rra story status  # Check Story Protocol integration
```

**API Server:** `src/rra/api/server.py`
```bash
uvicorn rra.api.server:app --host 0.0.0.0 --port 8000
```

**Core Library:**
```python
from rra import MarketConfig, RepoIngester, NegotiatorAgent
from rra.contracts.story_protocol import StoryProtocolClient
```

## Development Commands

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests (1,237 test cases)
pytest

# Run with coverage
pytest --cov=src/rra --cov-report=html

# Linting
make lint          # Run all linters
black src tests    # Format code
mypy src/rra       # Type checking
ruff check src     # Fast linting

# Build
make build
```

## Testing

- **Framework:** pytest with pytest-asyncio
- **Location:** `tests/` directory (48 test files)
- **Run all tests:** `pytest`
- **Integration tests:** `pytest -m integration`
- **Key fixtures in:** `tests/conftest.py`

Common test patterns:
- Mock NatLangChain server for integration tests
- Async test support via `@pytest.mark.asyncio`
- Fixtures for `market_config`, `knowledge_base`, mock agents

## Configuration

**`.market.yaml`** - Repository monetization config:
- License model (per-seat, subscription, one-time, perpetual)
- Pricing (target, floor, ceiling)
- Negotiation settings (style, personality, max rounds)
- Blockchain config (network, revenue split, wallets)
- Story Protocol settings (IP asset ID, PIL terms, royalties)

## Code Conventions

- **Python:** 3.9+ required (tested on 3.9-3.12)
- **Formatting:** Black with default settings
- **Type hints:** Use throughout, checked with mypy
- **Exceptions:** Custom hierarchy in `src/rra/exceptions.py` with error codes
- **Async:** Use asyncio patterns for I/O operations
- **Web3:** web3.py v7+ with proper gas estimation

## Key Dependencies

- **Web3:** `web3`, `eth-abi`, `eth-utils`
- **API:** `fastapi`, `uvicorn`, `pydantic`
- **CLI:** `click`
- **Crypto:** `cryptography` (v44.0+), optional `gmpy2` (77x faster)
- **Git:** `gitpython`

## Important Patterns

**Transaction Security:**
- Two-step verification for blockchain transactions
- Timeout handling with configurable limits
- Price commitment verification before execution

**Privacy:**
- Shamir secret sharing for key management
- Pedersen commitments for value hiding
- DID integration for identity

**Smart Contracts:**
- Contract ABIs in `contracts/abi/`
- Deployment scripts in `contracts/script/`
- Foundry for contract testing

## Common Tasks

**Adding a new CLI command:**
1. Add command to `src/rra/cli/main.py`
2. Use Click decorators for options/arguments
3. Add tests in `tests/test_cli.py`

**Adding a new API endpoint:**
1. Create route in `src/rra/api/`
2. Add to router in `server.py`
3. Add webhook support if needed

**Adding blockchain support:**
1. Update chain config in `src/rra/chains/`
2. Add RPC endpoints and chain ID
3. Test with local node or testnet

## Documentation

- `docs/USAGE-GUIDE.md` - Comprehensive usage guide
- `docs/BLOCKCHAIN-LICENSING.md` - On-chain licensing
- `docs/SECURITY-AUDIT.md` - Security audit results (A- rating)
- `SPECIFICATION.md` - Full technical specification

## CI/CD

GitHub Actions workflows in `.github/workflows/`:
- `ci.yml` - Python tests and linting
- `contracts.yml` - Smart contract compilation
- `license-verification.yml` - License compliance
- `release.yml` - Release automation
