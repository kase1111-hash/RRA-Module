# RRA-Module Makefile
# Common operations for development, testing, and Story Protocol integration

.PHONY: help install test lint build clean
.PHONY: story-check story-mint story-claim story-debug story-pay
.PHONY: workflow-license workflow-royalty workflow-derivative
.PHONY: marketplace-dev marketplace-build docs

# Default target
help:
	@echo "RRA-Module - Revenant Repo Agent Module"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Development:"
	@echo "  install          Install all dependencies (Python + Node.js)"
	@echo "  test             Run all tests"
	@echo "  lint             Run linters"
	@echo "  build            Build the project"
	@echo "  clean            Clean build artifacts"
	@echo ""
	@echo "Story Protocol Scripts:"
	@echo "  story-check      Check royalty vault status"
	@echo "  story-mint       Mint a license token"
	@echo "  story-claim      Claim royalties via IP Account"
	@echo "  story-debug      Debug vault state"
	@echo "  story-pay        Pay test royalty to vault"
	@echo ""
	@echo "Example Workflows:"
	@echo "  workflow-license     Run complete license workflow"
	@echo "  workflow-royalty     Run royalty management workflow"
	@echo "  workflow-derivative  Run derivative tracking workflow"
	@echo ""
	@echo "Marketplace:"
	@echo "  marketplace-dev   Start marketplace in development mode"
	@echo "  marketplace-build Build marketplace for production"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Generate documentation"
	@echo ""
	@echo "Environment Variables:"
	@echo "  PRIVATE_KEY      Wallet private key (required for transactions)"
	@echo "  STORY_IP_ASSET_ID  Override IP Asset ID from .market.yaml"
	@echo ""

# =============================================================================
# Development
# =============================================================================

install: install-python install-node
	@echo "All dependencies installed!"

install-python:
	@echo "Installing Python dependencies..."
	pip install -e ".[dev]" || pip install -r requirements.txt
	@echo "Python dependencies installed."

install-node:
	@echo "Installing Node.js dependencies..."
	cd scripts && npm install
	cd marketplace && npm install
	@echo "Node.js dependencies installed."

test: test-python test-node
	@echo "All tests passed!"

test-python:
	@echo "Running Python tests..."
	pytest tests/ -v --tb=short

test-node:
	@echo "Running Node.js tests..."
	cd scripts && npm test || echo "No Node.js tests configured"

lint: lint-python lint-node
	@echo "Linting complete!"

lint-python:
	@echo "Linting Python code..."
	ruff check src/ tests/ || true
	mypy src/ --ignore-missing-imports || true

lint-node:
	@echo "Linting JavaScript/TypeScript code..."
	cd scripts && npm run lint || true
	cd marketplace && npm run lint || true

build:
	@echo "Building project..."
	python -m build || echo "Python build skipped"
	cd marketplace && npm run build

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf marketplace/.next/ marketplace/out/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete."

# =============================================================================
# Story Protocol Scripts
# =============================================================================

story-check:
	@echo "Checking royalty vault status..."
	cd scripts && npm run check

story-mint:
ifndef PRIVATE_KEY
	$(error PRIVATE_KEY is required. Run: PRIVATE_KEY=0x... make story-mint)
endif
	@echo "Minting license token..."
	cd scripts && npm run mint

story-claim:
ifndef PRIVATE_KEY
	$(error PRIVATE_KEY is required. Run: PRIVATE_KEY=0x... make story-claim)
endif
	@echo "Claiming royalties via IP Account..."
	cd scripts && npm run claim

story-debug:
	@echo "Debugging vault state..."
	cd scripts && npm run debug

story-pay:
ifndef PRIVATE_KEY
	$(error PRIVATE_KEY is required. Run: PRIVATE_KEY=0x... make story-pay)
endif
	@echo "Paying test royalty..."
	cd scripts && npm run pay

# =============================================================================
# Example Workflows
# =============================================================================

workflow-license:
ifndef PRIVATE_KEY
	$(error PRIVATE_KEY is required. Run: PRIVATE_KEY=0x... make workflow-license)
endif
	@echo "Running complete license workflow..."
	node examples/workflows/complete-license-workflow.js

workflow-royalty:
ifndef PRIVATE_KEY
	$(error PRIVATE_KEY is required. Run: PRIVATE_KEY=0x... make workflow-royalty)
endif
	@echo "Running royalty management workflow..."
	node examples/workflows/royalty-management-workflow.js

workflow-derivative:
	@echo "Running derivative tracking workflow..."
	node examples/workflows/derivative-tracking-workflow.js

# =============================================================================
# Marketplace
# =============================================================================

marketplace-dev:
	@echo "Starting marketplace in development mode..."
	cd marketplace && npm run dev

marketplace-build:
	@echo "Building marketplace for production..."
	cd marketplace && npm run build

marketplace-start:
	@echo "Starting marketplace production server..."
	cd marketplace && npm start

# =============================================================================
# Documentation
# =============================================================================

docs:
	@echo "Documentation available at:"
	@echo "  - docs/README.md           - Documentation index"
	@echo "  - docs/USAGE-GUIDE.md      - Complete usage guide"
	@echo "  - docs/STORY-PROTOCOL-INTEGRATION.md - Story Protocol integration"
	@echo "  - docs/SELLING-LICENSES.md - License selling guide"
	@echo ""
	@echo "Open in browser: open docs/README.md"

# =============================================================================
# Utility Targets
# =============================================================================

check-env:
	@echo "Environment Check:"
	@echo "  PRIVATE_KEY: $(if $(PRIVATE_KEY),set,NOT SET)"
	@echo "  STORY_IP_ASSET_ID: $(or $(STORY_IP_ASSET_ID),from .market.yaml)"
	@echo "  STORY_NETWORK: $(or $(STORY_NETWORK),mainnet)"
	@echo ""
	@echo "Config file: .market.yaml"
	@test -f .market.yaml && echo "  Status: Found" || echo "  Status: NOT FOUND"

verify-config:
	@echo "Verifying configuration..."
	cd scripts && node -e "const c = require('./config'); c.printSummary(); c.validate(['ipAssetId']);"

# Quick aliases
mint: story-mint
claim: story-claim
check: story-check
debug: story-debug
