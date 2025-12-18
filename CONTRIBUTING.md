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

```bash
# Clone the repository
git clone https://github.com/kase1111-hash/RRA-Module.git
cd RRA-Module

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
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
├── src/rra/           # Main package
│   ├── config/        # Configuration management
│   ├── ingestion/     # Repository ingestion
│   ├── agents/        # Negotiation agents
│   ├── contracts/     # Smart contracts
│   ├── api/           # REST API
│   ├── cli/           # CLI interface
│   └── reputation/    # Reputation tracking
├── tests/             # Test suite
├── examples/          # Usage examples
└── docs/              # Documentation
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

For contract changes:

```bash
# Install Hardhat (if not already installed)
npm install --save-dev hardhat

# Compile contracts
npx hardhat compile

# Run contract tests
npx hardhat test

# Deploy to testnet
npx hardhat run scripts/deploy.js --network sepolia
```

## Documentation

- Update docstrings for all public functions
- Add examples to `examples/` directory
- Update README.md and QUICKSTART.md as needed
- Keep FUTURE.md updated with roadmap items

## Questions?

- Open an issue for bugs or feature requests
- Join discussions in GitHub Discussions
- Contact maintainers via GitHub

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
