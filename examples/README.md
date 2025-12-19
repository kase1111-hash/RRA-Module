# RRA Module Examples

This directory contains example scripts demonstrating various features of the RRA Module.

## Story Protocol Integration

### story_protocol_example.py

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

## Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. Get testnet ETH:
   - For Sepolia: https://sepoliafaucet.com/
   - For Story Protocol testnet: Contact Story Protocol team

## Additional Examples (Coming Soon)

- Superfluid streaming payment integration
- Multi-chain deployment
- Automated derivative detection via GitHub webhooks
- IPFi lending integration

## Documentation

For detailed documentation, see:
- [Story Protocol Integration Guide](../docs/STORY-PROTOCOL-INTEGRATION.md)
- [DeFi Integration Feasibility](../docs/DEFI-INTEGRATION.md)
- [Full Documentation Index](../docs/README.md)
- [Main README](../README.md)
