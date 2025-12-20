# RRA Module Smart Contracts

Foundry project for RRA Module smart contract development, testing, and deployment.

## Prerequisites

Install Foundry:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

## Setup

```bash
cd contracts

# Install dependencies
forge install OpenZeppelin/openzeppelin-contracts --no-commit

# Build contracts
forge build

# Run tests
forge test
```

## Development Workflow

### 1. Local Development (Anvil)

Start a local node:
```bash
# Terminal 1: Start anvil
anvil

# Terminal 2: Deploy to local node
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80  # Anvil default
forge script script/DeployRepoLicense.s.sol --rpc-url localhost --broadcast
```

### 2. Testnet Deployment (Sepolia)

```bash
# Set environment variables
export PRIVATE_KEY=your_private_key
export SEPOLIA_RPC_URL=https://rpc.sepolia.org
export ETHERSCAN_API_KEY=your_etherscan_key

# Deploy to Sepolia
forge script script/DeployRepoLicense.s.sol --rpc-url sepolia --broadcast --verify

# Deploy to Arbitrum Sepolia
export ARBITRUM_SEPOLIA_RPC_URL=https://sepolia-rollup.arbitrum.io/rpc
forge script script/DeployRepoLicense.s.sol --rpc-url arbitrum_sepolia --broadcast
```

### 3. Mainnet Deployment

**IMPORTANT:** Only deploy to mainnet after thorough testing on testnets.

```bash
export PRIVATE_KEY=your_mainnet_key
export ETH_RPC_URL=your_mainnet_rpc

# Dry run first (no --broadcast)
forge script script/DeployRepoLicense.s.sol --rpc-url mainnet

# If everything looks good, deploy
forge script script/DeployRepoLicense.s.sol --rpc-url mainnet --broadcast --verify
```

## Updating Python Configuration

After deployment, update the addresses in:
- `src/rra/chains/config.py` - Chain-specific addresses
- `src/rra/contracts/story_protocol.py` - Story Protocol addresses

Example:
```python
# In src/rra/chains/config.py
ChainId.ETHEREUM_SEPOLIA.value: ChainConfig(
    ...
    license_nft_address="0x...",  # Your deployed address
    ...
)
```

## Contract Addresses

### Testnets (Development)

| Network | RepoLicense | Status |
|---------|-------------|--------|
| Localhost (31337) | Deployed on each `anvil` run | ✅ |
| Sepolia (11155111) | `0xdead...` | ⏳ Deploy |
| Arbitrum Sepolia (421614) | `0xdead...` | ⏳ Deploy |
| Optimism Sepolia (11155420) | `0xdead...` | ⏳ Deploy |
| Base Sepolia (84532) | `0xdead...` | ⏳ Deploy |

### Mainnets (Production)

| Network | RepoLicense | Status |
|---------|-------------|--------|
| Ethereum (1) | - | ⏳ After testing |
| Arbitrum (42161) | - | ⏳ After testing |
| Optimism (10) | - | ⏳ After testing |
| Base (8453) | - | ⏳ After testing |
| Polygon (137) | - | ⏳ After testing |

## Verification

Contracts are automatically verified when using `--verify` flag with deployment.

Manual verification:
```bash
forge verify-contract \
    --chain-id 11155111 \
    --compiler-version v0.8.20 \
    0xYourContractAddress \
    src/RepoLicense.sol:RepoLicense
```

## Testing

```bash
# Run all tests
forge test

# Run with verbosity
forge test -vvv

# Run specific test
forge test --match-test testIssueLicense

# Gas report
forge test --gas-report

# Coverage
forge coverage
```

## Security

- **ReentrancyGuard**: Added to `issueLicense` and `renewLicense` functions
- **Access Control**: Uses OpenZeppelin's Ownable pattern
- **Input Validation**: All user inputs are validated
- See `/docs/SECURITY-AUDIT.md` for full audit report

## License

FSL-1.1-ALv2 (Functional Source License 1.1 with Apache 2.0 Future Grant)
