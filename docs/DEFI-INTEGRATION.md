# DeFi Integration Guide

**Last Updated:** 2025-12-20
**Status:** ✅ FULLY IMPLEMENTED

---

## Overview

The RRA Module integrates with multiple DeFi protocols to transform code repositories into yield-bearing, composable IP assets. All planned integrations are now implemented and tested.

---

## Implemented Integrations

### 1. Story Protocol - IP Tokenization

**Status:** ✅ Implemented (awaiting mainnet contract addresses)
**Location:** `src/rra/contracts/story_protocol.py`, `src/rra/integrations/story_integration.py`

Story Protocol enables:
- Tokenizing repositories as Programmable IP Assets
- Embedding `.market.yaml` terms into on-chain licenses (PILs)
- Automated royalty enforcement on derivatives
- Derivative tracking for forks and remixes

See [Story Protocol Integration Guide](STORY-PROTOCOL-INTEGRATION.md) for details.

---

### 2. Superfluid - Streaming Payments

**Status:** ✅ Fully Implemented
**Location:** `src/rra/integrations/superfluid.py`
**Tests:** `tests/test_superfluid.py` (21 tests)

Superfluid enables:
- Real-time, per-second subscription payments
- Continuous flow agreements (CFAs)
- Automatic license access revocation when streams stop
- Configurable grace periods for payment interruptions

```python
from rra.integrations.superfluid import SuperfluidManager

manager = SuperfluidManager()
license = manager.create_streaming_license(
    repo_id="my-repo",
    buyer_address="0x...",
    seller_address="0x...",
    monthly_price_usd=50.0,
    token="USDCx",
    grace_period_hours=24
)
```

---

### 3. IPFi Lending (NFTfi-style)

**Status:** ✅ Fully Implemented
**Location:** `src/rra/defi/ipfi_lending.py`
**Tests:** `tests/test_final_features.py`

IPFi Lending enables:
- Collateralized loans against license NFTs
- Loan offers from lenders with customizable terms
- Collateral valuation based on revenue streams
- Liquidation mechanisms for defaulted loans

```python
from rra.defi.ipfi_lending import create_lending_manager

manager = create_lending_manager()

# Register collateral
collateral = manager.register_collateral(
    license_id="license-123",
    owner_address="0x...",
    estimated_value=1000.0
)

# Request a loan
loan = manager.request_loan(
    collateral_id=collateral.collateral_id,
    principal_amount=500.0,
    interest_rate=0.1,
    duration_days=30
)
```

---

### 4. Fractional IP Ownership

**Status:** ✅ Fully Implemented
**Location:** `src/rra/defi/fractional_ip.py`
**Tests:** `tests/test_final_features.py`

Fractional ownership enables:
- ERC-20 style fractionalization of IP assets
- Share trading with buy/sell orders
- Pro-rata revenue distribution to shareholders
- Buyout mechanisms for consolidating ownership

```python
from rra.defi.fractional_ip import create_fractional_manager

manager = create_fractional_manager()

# Fractionalize an asset
asset = manager.fractionalize_asset(
    nft_contract="0x...",
    token_id=123,
    owner="0x...",
    total_shares=10000,
    share_price=0.01
)

# Buy shares
shares = manager.buy_shares(
    asset_id=asset.asset_id,
    buyer="0x...",
    share_count=100
)

# Distribute revenue
distribution = asset.distribute_revenue(1000.0)
```

---

### 5. Yield-Bearing License Tokens

**Status:** ✅ Fully Implemented
**Location:** `src/rra/defi/yield_tokens.py`
**Tests:** `tests/test_yield_tokens.py` (44 tests)

Yield tokens enable:
- Staking license NFTs in yield pools
- Multiple yield strategies:
  - Fixed APY
  - Revenue Share
  - Time-Weighted
  - Value-Weighted
  - Hybrid
- Lock period bonuses (10-50% bonus for longer locks)
- Automatic yield distribution

```python
from rra.defi.yield_tokens import create_staking_manager

manager = create_staking_manager()

# Create a yield pool
pool = manager.create_pool(
    name="repo-yield-pool",
    strategy="revenue_share",
    base_apy=0.10
)

# Stake a license
stake = manager.stake_license(
    pool_id=pool.pool_id,
    license_id="license-123",
    owner="0x...",
    value=1000.0,
    lock_period_days=90  # 25% bonus
)

# Claim yield
yield_amount = manager.claim_yield(stake.stake_id)
```

---

## Multi-Chain Support

**Status:** ✅ Fully Implemented
**Location:** `src/rra/chains/config.py`
**Tests:** `tests/test_new_features.py`

Supported networks:
| Network | Chain ID | Status |
|---------|----------|--------|
| Ethereum Mainnet | 1 | ✅ |
| Polygon | 137 | ✅ |
| Arbitrum | 42161 | ✅ |
| Base | 8453 | ✅ |
| Optimism | 10 | ✅ |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RRA DeFi Stack                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Story     │  │  Superfluid │  │    IPFi Lending     │ │
│  │  Protocol   │  │  Streaming  │  │  (Collateralized)   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                     │            │
│  ┌──────┴────────────────┴─────────────────────┴──────────┐ │
│  │              License NFT (ERC-721)                      │ │
│  └──────┬────────────────┬─────────────────────┬──────────┘ │
│         │                │                     │            │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────────┴──────────┐ │
│  │ Fractional  │  │   Yield     │  │    Multi-Chain      │ │
│  │   Shares    │  │   Pools     │  │     Support         │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

All DeFi features are accessible via the REST API:

| Endpoint | Description |
|----------|-------------|
| `POST /api/streaming/create` | Create streaming license |
| `GET /api/streaming/status/{license_id}` | Check stream status |
| `POST /api/yield/pools` | Create yield pool |
| `POST /api/yield/stake` | Stake a license |
| `POST /api/yield/stake/{id}/claim` | Claim yield |

---

## Configuration

DeFi features are configured in `.market.yaml`:

```yaml
monetization:
  primary_model: streaming_subscription
  flow_rate: "50 USDC per month"
  fallback_model: one_time
  target_price: "0.05 ETH"

defi_hooks:
  collateralizable: true
  supported_protocols: ["Story IPFi", "Superfluid"]
  yield_strategy: revenue_share_staking
  min_ltv: 0.4

royalties:
  derivative_rate: 0.15
  contributor_split: proportional_to_commits
```

---

## Related Documentation

- [Story Protocol Integration](STORY-PROTOCOL-INTEGRATION.md)
- [Blockchain Licensing](BLOCKCHAIN-LICENSING.md)
- [Security Audit](SECURITY-AUDIT.md)
- [Test Results](TESTING-RESULTS.md)
