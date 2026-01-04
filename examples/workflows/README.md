# Example Workflows

This directory contains complete workflow examples demonstrating common Story Protocol operations.

## Available Workflows

### 1. Complete License Workflow

**File:** `complete-license-workflow.js`

Demonstrates the full licensing workflow:
1. Validate configuration
2. Verify IP Asset registration
3. Check wallet balance
4. Mint a license token
5. Verify ownership

**Usage:**
```bash
PRIVATE_KEY=0x... node examples/workflows/complete-license-workflow.js
```

**Prerequisites:**
- Wallet with IP tokens for gas
- IP Asset registered on Story Protocol
- Configuration in `.market.yaml` or environment variables

---

### 2. Royalty Management Workflow

**File:** `royalty-management-workflow.js`

Demonstrates royalty lifecycle management:
1. Lookup royalty vault
2. Check vault status
3. View claimable royalties
4. Check IP Account balance
5. Show owner wallet balance

**Usage:**
```bash
PRIVATE_KEY=0x... node examples/workflows/royalty-management-workflow.js
```

**Output includes:**
- RT token balances and ownership percentages
- Current snapshot information
- Claimable WIP amounts
- Step-by-step guidance for claiming

---

### 3. Derivative Tracking Workflow

**File:** `derivative-tracking-workflow.js`

Demonstrates derivative IP tracking:
1. Verify IP Asset registration
2. Check derivative relationships
3. View royalty configuration
4. Understand revenue flow
5. Monitoring recommendations

**Usage:**
```bash
# With IP Asset from config
node examples/workflows/derivative-tracking-workflow.js

# With specific IP Asset
node examples/workflows/derivative-tracking-workflow.js 0xYourIPAsset
```

---

## Quick Start

1. **Install dependencies:**
   ```bash
   cd scripts && npm install
   ```

2. **Set up configuration:**
   ```bash
   # Option 1: Use .market.yaml (recommended)
   # Your .market.yaml should have:
   # defi_integrations:
   #   story_protocol:
   #     ip_asset_id: "0x..."

   # Option 2: Use environment variables
   export STORY_IP_ASSET_ID=0x...
   export PRIVATE_KEY=0x...
   ```

3. **Run a workflow:**
   ```bash
   PRIVATE_KEY=0x... node examples/workflows/complete-license-workflow.js
   ```

## Using Make

You can also run workflows via Make:

```bash
# License workflow
make workflow-license

# Royalty workflow
make workflow-royalty

# Derivative tracking
make workflow-derivative
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `PRIVATE_KEY` | Wallet private key | For transactions |
| `STORY_IP_ASSET_ID` | IP Asset address | If not in .market.yaml |
| `STORY_VAULT_ADDRESS` | Royalty vault address | Optional |
| `STORY_NETWORK` | Network (mainnet/testnet) | Default: mainnet |

## Extending Workflows

These workflows are designed as templates. To customize:

1. Copy the workflow file
2. Modify the steps for your use case
3. Add error handling as needed
4. Integrate with your notification systems

### Example: Add Slack Notification

```javascript
// After claiming royalties
const { WebClient } = require('@slack/web-api');

async function notifySlack(amount) {
    const slack = new WebClient(process.env.SLACK_TOKEN);
    await slack.chat.postMessage({
        channel: '#royalties',
        text: `Claimed ${amount} WIP from royalty vault!`
    });
}
```

## Troubleshooting

### "Configuration Error: Missing IP_ASSET_ID"

Set your IP Asset ID:
```bash
export STORY_IP_ASSET_ID=0xYourIPAssetAddress
```

Or add to `.market.yaml`:
```yaml
defi_integrations:
  story_protocol:
    ip_asset_id: "0xYourIPAssetAddress"
```

### "No Royalty Vault exists"

This means no royalties have been paid to your IP Asset yet. Either:
- Wait for licensees to make payments
- Test with: `node scripts/pay-royalty.js`

### "Insufficient balance"

Your wallet needs IP tokens for gas fees. Get testnet tokens from the Story Protocol faucet.

## Related Resources

- [Story Protocol Scripts](../../scripts/README.md)
- [Usage Guide](../../docs/USAGE-GUIDE.md)
- [Story Protocol Integration](../../docs/STORY-PROTOCOL-INTEGRATION.md)
