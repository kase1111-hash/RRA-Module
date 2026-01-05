# RRA Module - Integrations Guide

> **Version:** 1.0.1-beta
> **Last Updated:** January 2026

This guide consolidates all integration documentation for the RRA Module, including NatLangChain ecosystem integration, NatLangChain API, and Story Protocol.

---

## Table of Contents

1. [Overview](#overview)
2. [NatLangChain Ecosystem](#natlangchain-ecosystem)
3. [NatLangChain API](#natlangchain-api)
4. [Story Protocol](#story-protocol)
5. [Installation](#installation)

---

## Overview

The RRA Module integrates with multiple systems to provide comprehensive code licensing:

| Integration | Purpose | Status |
|-------------|---------|--------|
| **NatLangChain Ecosystem** | Agent runtime, state persistence, messaging | ✅ Complete |
| **NatLangChain API** | On-chain transaction recording, intents | ✅ Complete |
| **Story Protocol** | IP asset registration, programmable licenses | ✅ Complete |

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   RRA Module    │────▶│ NatLangChain API │────▶│   Blockchain    │
│                 │     │    (HTTP/REST)   │     │   (Entries)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│ Story Protocol  │     │  NatLangChain    │
│ (Aeneid Testnet)│     │   Ecosystem      │
│  Chain ID: 1315 │     │   Components     │
└─────────────────┘     └──────────────────┘
```

---

## NatLangChain Ecosystem

The RRA Module is designed as a **first-class NatLangChain extension** that works both standalone and fully integrated with the NatLangChain ecosystem.

### Integration Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **Standalone** | No external dependencies, local storage | Development, testing |
| **Integrated** | Full ecosystem integration | Production deployments |
| **Hybrid** | Selective component use | Transitioning deployments |

### Ecosystem Components

#### 1. memory-vault - State Persistence
```python
from rra.agents.negotiator import NegotiatorAgent

# Standalone: Uses local file storage
agent = NegotiatorAgent(kb)

# Integrated: Uses memory-vault
agent = NegotiatorAgent(kb, integrated=True)
agent.save_state()  # Persists to memory-vault
```

#### 2. value-ledger - Transaction Tracking
```python
from rra.integration.ledger import get_ledger

ledger = get_ledger(agent.agent_id)
ledger.record_transaction(
    transaction_id="tx_123",
    buyer_id="buyer_456",
    repo_url="https://github.com/user/repo.git",
    price="0.05 ETH",
    license_model="per-seat"
)
```

#### 3. mediator-node - Message Routing
```python
from rra.integration.mediator import get_message_router

router = get_message_router(agent.agent_id)
router.send_message(
    to_agent="buyer_agent_789",
    message={"type": "proposal", "price": "0.05 ETH"}
)
```

#### 4. IntentLog - Decision Auditing
```python
agent = NegotiatorAgent(kb, integrated=True)
agent.log_intent("negotiate_price", {"proposed": "0.03 ETH"})
agent.log_decision("accept_offer", {"final_price": "0.04 ETH"})
```

---

## NatLangChain API

### Quick Start

```python
from rra.integration.natlangchain_client import NatLangChainClient

client = NatLangChainClient(
    base_url="http://localhost:5000",
    agent_id="my-rra-agent"
)

# Health check
success, health = client.health_check()
if success:
    print(f"Chain status: {health.status}")
    print(f"Total blocks: {health.blocks}")
```

### Post License Transaction

```python
success, result = client.post_rra_transaction(
    repo_url="https://github.com/owner/repository",
    buyer_id="did:nlc:abc123...",
    license_model="commercial",
    price="0.5 ETH",
    terms={
        "duration": "perpetual",
        "scope": "worldwide",
        "modifications_allowed": True
    }
)
```

### Post Negotiation Intent

```python
success, result = client.post_negotiation_intent(
    repo_url="https://github.com/owner/repository",
    intent_type="offer_made",
    details={
        "price": "0.8 ETH",
        "license_model": "commercial",
        "expires_at": "2025-02-01T00:00:00Z"
    }
)
```

**Intent Types:** `quote_requested`, `offer_made`, `counter_offer`, `offer_accepted`, `offer_rejected`, `negotiation_completed`

### Async Client

```python
from rra.integration.natlangchain_client import AsyncNatLangChainClient

async with AsyncNatLangChainClient(base_url="http://localhost:5000") as client:
    success, health = await client.health_check()
    success, result = await client.post_rra_transaction(...)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NATLANGCHAIN_URL` | `http://localhost:5000` | API URL |
| `NATLANGCHAIN_TIMEOUT` | `30` | Timeout (seconds) |
| `NATLANGCHAIN_AGENT_ID` | `rra-agent` | Agent identifier |

---

## Story Protocol

### Network Configuration

| Network | Chain ID | RPC URL | Explorer |
|---------|----------|---------|----------|
| **Aeneid Testnet** | 1315 | `https://aeneid.storyrpc.io` | `https://aeneid.explorer.story.foundation` |
| Mainnet | 1514 | `https://mainnet.storyrpc.io` | `https://storyscan.io` |

> **Note:** RRA v1.0.1-beta defaults to Aeneid Testnet for all operations.

### IP Asset Registration

```python
from rra.integrations.story_integration import StoryIntegrationManager
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://aeneid.storyrpc.io"))
manager = StoryIntegrationManager(w3, network="testnet")

result = manager.register_repository_as_ip_asset(
    repo_url="https://github.com/youruser/yourrepo",
    market_config=config,
    owner_address="0xYourAddress",
    private_key="0xYourPrivateKey"
)
print(f"IP Asset ID: {result['ip_asset_id']}")
```

### Programmable IP Licenses (PIL)

Configure in `.market.yaml`:

```yaml
licensing:
  story_protocol:
    enabled: true
    network: testnet  # Use Aeneid Testnet
    license_terms:
      commercial_use: true
      derivatives_allowed: true
      attribution_required: true
      royalty_percentage: 5
```

### Minting License Tokens

```python
result = manager.mint_license_token(
    ip_asset_id="0xYourIPAssetID",
    license_terms_id=3,
    buyer_address="0xBuyerAddress",
    price_wei=50000000000000000  # 0.05 ETH
)
```

### Contract Addresses (Aeneid Testnet)

| Contract | Address |
|----------|---------|
| Licensing Module | `0xd81fd78f557b457b4350cB95D20b547bFEb4D857` |
| PIL Template | `0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316` |

---

## Installation

### Standalone (Minimal)
```bash
pip install rra-module
```

### With NatLangChain Integration
```bash
pip install rra-module[natlangchain]
```

### With Crypto Optimizations
```bash
pip install rra-module[crypto]
```

### Full Installation
```bash
pip install rra-module[all]
```

---

## Configuration

### Integration Config File

Create `.rra-integration.yaml`:

```yaml
auto_detect_mode: true
force_standalone: false

# Component settings
enable_memory_vault: true
enable_value_ledger: true
enable_mediator_node: true
enable_intent_log: true

# Story Protocol
story_protocol:
  network: testnet
  auto_register: false

# Fallback behavior
fallback_to_standalone: true
```

---

## Migration from v1.0.0-rc1

### Breaking Changes

1. **Story Protocol defaults to testnet** - Update any mainnet-specific code
2. **Explorer URLs changed** - Use `aeneid.explorer.story.foundation` for testnet

### Upgrade Steps

```bash
pip install --upgrade rra-module
```

No code changes required for most users.

---

## Related Documentation

- [CHANGELOG.md](../CHANGELOG.md) - Version history
- [SECURITY.md](../SECURITY.md) - Security practices
- [USAGE-GUIDE.md](./USAGE-GUIDE.md) - Getting started guide

---

## Support

- **GitHub Issues:** https://github.com/kase1111-hash/RRA-Module/issues
- **Documentation:** https://github.com/kase1111-hash/RRA-Module/tree/main/docs
