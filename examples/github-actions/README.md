# Example GitHub Actions Workflows

This directory contains example GitHub Actions workflows for automating Story Protocol operations.

## Available Workflows

### 1. Automated Royalty Claiming

**File:** `royalty-claim.yml`

Automatically claims pending royalties on a schedule.

**Features:**
- Weekly scheduled runs (configurable)
- Checks for claimable amounts before attempting claim
- Dry-run option for testing
- Summary reports

**Setup:**
1. Copy to `.github/workflows/royalty-claim.yml`
2. Add repository secrets:
   - `PRIVATE_KEY` - Your wallet private key
3. Add repository variables:
   - `STORY_IP_ASSET_ID` - Your IP Asset address

**Usage:**
```yaml
# Trigger manually
gh workflow run "Claim Royalties" --field dry_run=true
```

---

### 2. Mint License on Release

**File:** `release-license.yml`

Mints a license token when you publish a GitHub release.

**Features:**
- Triggers on new releases
- Manual trigger with recipient selection
- Updates release notes with license info
- Supports different license tiers

**Setup:**
1. Copy to `.github/workflows/release-license.yml`
2. Add repository secrets:
   - `PRIVATE_KEY` - Your wallet private key
3. Add repository variables:
   - `STORY_IP_ASSET_ID` - Your IP Asset address
   - `DEFAULT_LICENSE_RECIPIENT` - Default recipient address

**Usage:**
```yaml
# Create a release via GitHub UI, or:
gh release create v1.0.0 --title "Version 1.0" --notes "Release notes"
```

---

### 3. Weekly Royalty Report

**File:** `royalty-report.yml`

Generates weekly reports on royalty status as GitHub Issues.

**Features:**
- Scheduled weekly reports
- Creates/updates a tracking issue
- Includes vault status and metrics
- Actionable checklist

**Setup:**
1. Copy to `.github/workflows/royalty-report.yml`
2. Add repository variables:
   - `STORY_IP_ASSET_ID` - Your IP Asset address
3. Enable Issues in your repository

**Output:**
Creates a GitHub Issue with:
- Vault WIP balance
- Current snapshot ID
- RT supply information
- Links to explorers
- Checklist of recommended actions

---

## Quick Setup

### 1. Copy Workflow Files

```bash
# From your repository root
mkdir -p .github/workflows

# Copy the workflow you want
cp examples/github-actions/royalty-claim.yml .github/workflows/
cp examples/github-actions/royalty-report.yml .github/workflows/
```

### 2. Add Secrets

Go to your repository Settings > Secrets and variables > Actions:

**Secrets (encrypted):**
- `PRIVATE_KEY` - Your wallet private key (never share!)

**Variables (visible):**
- `STORY_IP_ASSET_ID` - Your registered IP Asset address
- `STORY_NETWORK` - Network (`mainnet` or `testnet`)

### 3. Enable Workflows

Workflows run automatically on their triggers. You can also:

```bash
# Run manually
gh workflow run "Claim Royalties"

# View workflow runs
gh run list

# View workflow status
gh run view
```

---

## Customization

### Change Schedule

Edit the `cron` expression in the workflow:

```yaml
on:
  schedule:
    # Every day at midnight
    - cron: '0 0 * * *'

    # Every Monday at 9am
    - cron: '0 9 * * 1'

    # Every hour
    - cron: '0 * * * *'
```

### Add Notifications

#### Slack

```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    channel-id: 'C0123456789'
    slack-message: 'Claimed ${{ steps.claim.outputs.amount }} WIP'
  env:
    SLACK_BOT_TOKEN: ${{ secrets.SLACK_TOKEN }}
```

#### Discord

```yaml
- name: Notify Discord
  uses: sarisia/actions-status-discord@v1
  with:
    webhook: ${{ secrets.DISCORD_WEBHOOK }}
    title: "Royalty Claimed"
    description: "Amount: ${{ steps.claim.outputs.amount }} WIP"
```

#### Email

```yaml
- name: Send Email
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 587
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: "Royalty Report - ${{ github.repository }}"
    body: "Claimed ${{ steps.claim.outputs.amount }} WIP"
    to: your@email.com
```

### Conditional Claiming

Only claim if amount exceeds threshold:

```yaml
- name: Check threshold
  id: threshold
  run: |
    AMOUNT=${{ steps.check.outputs.claimable_amount }}
    if (( $(echo "$AMOUNT > 0.1" | bc -l) )); then
      echo "should_claim=true" >> $GITHUB_OUTPUT
    else
      echo "should_claim=false" >> $GITHUB_OUTPUT
    fi

- name: Claim royalties
  if: steps.threshold.outputs.should_claim == 'true'
  run: node scripts/claim-via-ip-account.js
```

---

## Security Considerations

1. **Never commit private keys** - Always use GitHub Secrets
2. **Use environment protection** - Consider requiring approvals for claiming
3. **Limit workflow permissions** - Use minimal `GITHUB_TOKEN` permissions
4. **Review workflow runs** - Monitor for unexpected behavior
5. **Test on testnet first** - Verify workflows before mainnet

### Environment Protection

For production, consider adding environment protection:

```yaml
jobs:
  claim:
    environment: production  # Requires approval
    runs-on: ubuntu-latest
```

---

## Troubleshooting

### Workflow not running

1. Check Actions are enabled in repository settings
2. Verify cron syntax at [crontab.guru](https://crontab.guru/)
3. Check for syntax errors in YAML

### Secret not found

Ensure secrets are set at the correct level:
- Repository secrets for single repo
- Organization secrets for multiple repos

### Script failures

Check the workflow logs:
```bash
gh run view --log
```

---

## Related Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [RRA Module Scripts](../../scripts/README.md)
- [Usage Guide](../../docs/USAGE-GUIDE.md)
