#!/bin/bash
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
#
# Compile Solidity contracts using Foundry.
# Run this script before deploying contracts via Python.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONTRACTS_DIR="$PROJECT_ROOT/contracts"

echo "=== RRA Contract Compilation ==="
echo ""

# Check if Foundry is installed
if ! command -v forge &> /dev/null; then
    echo "Error: Foundry (forge) is not installed."
    echo ""
    echo "Install Foundry with:"
    echo "  curl -L https://foundry.paradigm.xyz | bash"
    echo "  foundryup"
    echo ""
    exit 1
fi

# Change to contracts directory
cd "$CONTRACTS_DIR"

echo "Checking dependencies..."

# Install dependencies if remappings.txt doesn't exist or lib is empty
if [ ! -d "lib/openzeppelin-contracts" ]; then
    echo "Installing OpenZeppelin contracts..."
    forge install OpenZeppelin/openzeppelin-contracts --no-commit
fi

echo ""
echo "Compiling contracts..."
forge build

echo ""
echo "=== Compilation Complete ==="
echo ""
echo "Compiled artifacts are in: $CONTRACTS_DIR/out/"
echo ""

# List compiled contracts
echo "Available contracts:"
for dir in out/*.sol; do
    if [ -d "$dir" ]; then
        contract_name=$(basename "$dir" .sol)
        echo "  - $contract_name"
    fi
done

echo ""
echo "You can now deploy contracts using Python:"
echo ""
echo "  from rra.contracts.manager import ContractManager"
echo "  manager = ContractManager(network='localhost')"
echo "  address = manager.deploy_license_contract(deployer, private_key)"
echo ""
