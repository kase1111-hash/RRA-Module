#!/bin/bash
# Integration Test Runner for RRA-Module
# Runs all integration tests and reports results

set -e

echo "============================================================"
echo "RRA-Module Integration Test Suite"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Helper functions
pass() {
    echo -e "  ${GREEN}[PASS]${NC} $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo -e "  ${RED}[FAIL]${NC} $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

skip() {
    echo -e "  ${YELLOW}[SKIP]${NC} $1"
    SKIP_COUNT=$((SKIP_COUNT + 1))
}

# ------------------------------------------------------------
# Test 1: Node.js Dependencies
# ------------------------------------------------------------
echo "1. Node.js Dependencies"
echo "------------------------------------------------------------"

if [ -f "scripts/package.json" ]; then
    cd scripts
    if npm ls >/dev/null 2>&1; then
        pass "Scripts dependencies installed"
    else
        npm install --silent
        pass "Scripts dependencies installed (fresh)"
    fi
    cd ..
else
    fail "scripts/package.json not found"
fi

if [ -f "marketplace/package.json" ]; then
    cd marketplace
    if npm ls >/dev/null 2>&1; then
        pass "Marketplace dependencies installed"
    else
        npm install --silent
        pass "Marketplace dependencies installed (fresh)"
    fi
    cd ..
else
    fail "marketplace/package.json not found"
fi

echo ""

# ------------------------------------------------------------
# Test 2: Configuration Module
# ------------------------------------------------------------
echo "2. Configuration Module"
echo "------------------------------------------------------------"

cd scripts
CONFIG_TEST=$(node -e "
const config = require('./config');
const errors = [];
if (!config.network) errors.push('network missing');
if (!config.rpcUrl) errors.push('rpcUrl missing');
if (!config.chainId) errors.push('chainId missing');
if (!config.contracts.licensingModule) errors.push('contracts missing');
if (!config.validate) errors.push('validate function missing');
if (errors.length > 0) {
    console.log('FAIL:' + errors.join(','));
    process.exit(1);
}
console.log('OK');
" 2>&1) || true
cd ..

if [ "$CONFIG_TEST" = "OK" ]; then
    pass "Config module loads correctly"
else
    fail "Config module: $CONFIG_TEST"
fi

# Check IP Asset ID from .market.yaml
if grep -q "ip_asset_id:" .market.yaml 2>/dev/null; then
    pass "IP Asset ID configured in .market.yaml"
else
    skip "IP Asset ID not in .market.yaml (using env variable)"
fi

echo ""

# ------------------------------------------------------------
# Test 3: Script Syntax Validation
# ------------------------------------------------------------
echo "3. Script Syntax Validation"
echo "------------------------------------------------------------"

for script in scripts/*.js; do
    if [ -f "$script" ]; then
        if node --check "$script" 2>/dev/null; then
            pass "$(basename $script)"
        else
            fail "$(basename $script) - syntax error"
        fi
    fi
done

echo ""

# ------------------------------------------------------------
# Test 4: Workflow Script Syntax
# ------------------------------------------------------------
echo "4. Workflow Script Syntax"
echo "------------------------------------------------------------"

for script in examples/workflows/*.js; do
    if [ -f "$script" ]; then
        if node --check "$script" 2>/dev/null; then
            pass "$(basename $script)"
        else
            fail "$(basename $script) - syntax error"
        fi
    fi
done

echo ""

# ------------------------------------------------------------
# Test 5: Marketplace Build
# ------------------------------------------------------------
echo "5. Marketplace Build"
echo "------------------------------------------------------------"

cd marketplace

# Lint check
if npm run lint >/dev/null 2>&1; then
    pass "ESLint check"
else
    fail "ESLint check"
fi

# Type check
if npx tsc --noEmit >/dev/null 2>&1; then
    pass "TypeScript type check"
else
    fail "TypeScript type check"
fi

# Build
if npm run build >/dev/null 2>&1; then
    pass "Production build"
else
    fail "Production build"
fi

cd ..

echo ""

# ------------------------------------------------------------
# Test 6: Python Tests (Royalty Claiming)
# ------------------------------------------------------------
echo "6. Python Tests"
echo "------------------------------------------------------------"

if command -v pytest &> /dev/null; then
    PYTEST_RESULT=$(python -m pytest tests/test_royalty_claiming.py -q 2>&1 | tail -1)
    if echo "$PYTEST_RESULT" | grep -q "passed"; then
        PASSED=$(echo "$PYTEST_RESULT" | grep -oP '\d+(?= passed)')
        pass "Royalty claiming tests ($PASSED tests)"
    else
        fail "Royalty claiming tests"
    fi
else
    skip "pytest not installed"
fi

echo ""

# ------------------------------------------------------------
# Test 7: Contract Address Validation
# ------------------------------------------------------------
echo "7. Contract Address Validation"
echo "------------------------------------------------------------"

cd scripts
CONTRACTS_TEST=$(node -e "
const config = require('./config');
const contracts = config.contracts;
const errors = [];
for (const [name, addr] of Object.entries(contracts)) {
    if (!addr || !addr.startsWith('0x') || addr.length !== 42) {
        errors.push(name);
    }
}
if (errors.length > 0) {
    console.log('FAIL:' + errors.join(','));
    process.exit(1);
}
console.log('OK:' + Object.keys(contracts).length);
" 2>&1) || true
cd ..

if [[ "$CONTRACTS_TEST" == OK:* ]]; then
    COUNT=$(echo "$CONTRACTS_TEST" | cut -d: -f2)
    pass "All $COUNT contract addresses valid"
else
    fail "Contract addresses: $CONTRACTS_TEST"
fi

echo ""

# ------------------------------------------------------------
# Test 8: Documentation Files
# ------------------------------------------------------------
echo "8. Documentation Files"
echo "------------------------------------------------------------"

REQUIRED_DOCS=(
    "README.md"
    "docs/README.md"
    "docs/USAGE-GUIDE.md"
    "docs/STORY-PROTOCOL-INTEGRATION.md"
    "docs/SELLING-LICENSES.md"
)

for doc in "${REQUIRED_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        pass "$doc"
    else
        fail "$doc not found"
    fi
done

echo ""

# ------------------------------------------------------------
# Test 9: GitHub Actions Workflows
# ------------------------------------------------------------
echo "9. GitHub Actions Workflows"
echo "------------------------------------------------------------"

for workflow in .github/workflows/*.yml; do
    if [ -f "$workflow" ]; then
        # Basic YAML validation
        if python -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
            pass "$(basename $workflow)"
        else
            fail "$(basename $workflow) - invalid YAML"
        fi
    fi
done

echo ""

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------
echo "============================================================"
echo "Test Summary"
echo "============================================================"
echo ""
echo -e "  ${GREEN}Passed:${NC}  $PASS_COUNT"
echo -e "  ${RED}Failed:${NC}  $FAIL_COUNT"
echo -e "  ${YELLOW}Skipped:${NC} $SKIP_COUNT"
echo ""

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAIL_COUNT of $TOTAL tests failed${NC}"
    exit 1
fi
