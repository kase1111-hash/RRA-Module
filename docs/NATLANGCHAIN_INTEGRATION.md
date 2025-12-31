# NatLangChain Integration Guide

This guide covers integrating the RRA Module with NatLangChain, a natural-language blockchain for economic coordination and conflict resolution.

## Overview

NatLangChain is an economic coordination system designed to reduce the cost of disagreement through time-bounded economic pressure. The RRA Module integrates with NatLangChain to:

- Record licensing transactions on-chain
- Post negotiation intents and outcomes
- Create an immutable audit trail of license agreements
- Enable transparent, verifiable contract negotiations

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   RRA Module    │────▶│ NatLangChain API │────▶│   Blockchain    │
│                 │     │    (HTTP/REST)   │     │   (Entries)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐
│   License NFT   │     │  LLM Validation  │
│  (Story Proto)  │     │    (Optional)    │
└─────────────────┘     └──────────────────┘
```

## Quick Start

### Installation

The NatLangChain client is included in the RRA Module. Ensure `httpx` is installed:

```bash
pip install httpx
```

### Basic Usage

```python
from rra.integration.natlangchain_client import NatLangChainClient

# Initialize the client
client = NatLangChainClient(
    base_url="http://localhost:5000",  # NatLangChain server URL
    agent_id="my-rra-agent"            # Agent identifier for attribution
)

# Check if the chain is healthy
success, health = client.health_check()
if success:
    print(f"Chain status: {health.status}")
    print(f"Total blocks: {health.blocks}")
    print(f"Pending entries: {health.pending_entries}")
```

---

## Client Reference

### NatLangChainClient

Synchronous HTTP client for interacting with NatLangChain.

```python
from rra.integration.natlangchain_client import NatLangChainClient

client = NatLangChainClient(
    base_url="http://localhost:5000",  # API endpoint
    timeout=30.0,                       # Request timeout in seconds
    agent_id="my-agent"                 # Agent identifier
)
```

### AsyncNatLangChainClient

Async/await compatible client for use in async applications.

```python
from rra.integration.natlangchain_client import AsyncNatLangChainClient

async with AsyncNatLangChainClient(base_url="http://localhost:5000") as client:
    success, health = await client.health_check()
```

### Factory Function

```python
from rra.integration.natlangchain_client import get_chain_client

# Get sync client
client = get_chain_client(base_url="http://localhost:5000", agent_id="my-agent")

# Get async client
async_client = get_chain_client(base_url="http://localhost:5000", async_mode=True)
```

---

## Core Operations

### Health Check

Verify the NatLangChain server is running and accessible.

```python
success, health = client.health_check()

if success:
    print(f"Status: {health.status}")           # "healthy"
    print(f"Blocks: {health.blocks}")           # Number of mined blocks
    print(f"Pending: {health.pending_entries}") # Entries awaiting mining
    print(f"LLM Available: {health.llm_validation_available}")
else:
    print("Chain is not accessible")
```

### Post Generic Entry

Post any natural language entry to the chain.

```python
success, result = client.post_entry(
    content="User alice transferred 100 tokens to bob for services rendered.",
    author="alice",
    intent="Token transfer",
    metadata={
        "amount": 100,
        "currency": "RRA",
        "recipient": "bob"
    },
    validate=True,      # Validate entry with LLM (if available)
    auto_mine=False     # Don't immediately mine into a block
)

if success:
    print(f"Entry posted: {result}")
```

---

## RRA-Specific Operations

### Post License Transaction

Record a completed license purchase on the chain.

```python
success, result = client.post_rra_transaction(
    repo_url="https://github.com/owner/repository",
    buyer_id="did:nlc:abc123...",
    license_model="commercial",
    price="0.5 ETH",
    terms={
        "duration": "perpetual",
        "scope": "worldwide",
        "modifications_allowed": True,
        "attribution_required": True,
        "exclusive": False
    },
    agent_id="negotiation-agent-v1"  # Optional, overrides client agent_id
)

if success:
    print(f"Transaction recorded: {result['entry']['id']}")
```

The transaction creates a chain entry with:
- Natural language description of the license grant
- Structured metadata for querying
- Automatic mining into the next block

### Post Negotiation Intent

Record negotiation events on-chain for transparency.

```python
# Record a quote request
success, result = client.post_negotiation_intent(
    repo_url="https://github.com/owner/repository",
    intent_type="quote_requested",
    details={
        "buyer_id": "did:nlc:buyer123",
        "budget": "1 ETH",
        "license_preference": "commercial",
        "usage": "internal development"
    }
)

# Record an offer
success, result = client.post_negotiation_intent(
    repo_url="https://github.com/owner/repository",
    intent_type="offer_made",
    details={
        "price": "0.8 ETH",
        "license_model": "commercial",
        "terms": {
            "duration": "1 year",
            "scope": "worldwide"
        },
        "expires_at": "2025-02-01T00:00:00Z"
    }
)

# Record a counter-offer
success, result = client.post_negotiation_intent(
    repo_url="https://github.com/owner/repository",
    intent_type="counter_offer",
    details={
        "original_price": "0.8 ETH",
        "counter_price": "0.6 ETH",
        "justification": "Budget constraints for startup"
    }
)
```

**Intent Types:**
| Type | Description |
|------|-------------|
| `quote_requested` | Buyer requests pricing information |
| `offer_made` | Seller presents license terms |
| `counter_offer` | Party proposes modified terms |
| `offer_accepted` | Party accepts current terms |
| `offer_rejected` | Party rejects current terms |
| `negotiation_stalled` | Negotiation inactive for extended period |
| `negotiation_completed` | Negotiation concluded successfully |

---

## Block Mining

### Mine Pending Entries

Trigger mining of pending entries into a new block.

```python
success, result = client.mine_block()

if success:
    print(f"Block mined: {result['block']['hash']}")
    print(f"Block index: {result['block']['index']}")
```

Note: Most RRA operations use `auto_mine=True` to automatically mine transactions.

---

## Querying the Chain

### Get Chain Narrative

Retrieve a human-readable narrative of all chain activity.

```python
success, narrative = client.get_chain_narrative()

if success:
    print("Chain History:")
    print(narrative)
    # Output:
    # Block 1: Genesis block created
    # Block 2: alice grants buyer-123 a commercial license...
    # Block 3: Negotiation started for github.com/owner/repo...
```

### Search Entries

Search for specific entries on the chain.

```python
# Search by text query
success, entries = client.search_entries(
    query="commercial license",
    limit=10
)

# Search by author
success, entries = client.search_entries(
    author="rra-agent",
    limit=5
)

# Search by intent
success, entries = client.search_entries(
    intent="License",
    limit=10
)

# Combined search
success, entries = client.search_entries(
    query="MIT license",
    author="rra-agent",
    limit=20
)

for entry in entries:
    print(f"- {entry['intent']}: {entry['content'][:100]}...")
```

### Get Chain Statistics

Retrieve overall chain statistics.

```python
success, stats = client.get_stats()

if success:
    print(f"Total blocks: {stats['total_blocks']}")
    print(f"Total entries: {stats['total_entries']}")
    print(f"Pending entries: {stats['pending_entries']}")
```

---

## Async Usage

For async applications, use `AsyncNatLangChainClient`:

```python
import asyncio
from rra.integration.natlangchain_client import AsyncNatLangChainClient

async def post_transaction():
    async with AsyncNatLangChainClient(
        base_url="http://localhost:5000",
        agent_id="async-rra-agent"
    ) as client:
        # Check health
        success, health = await client.health_check()
        if not success:
            return None

        # Post transaction
        success, result = await client.post_rra_transaction(
            repo_url="https://github.com/owner/repo",
            buyer_id="buyer-123",
            license_model="MIT",
            price="0.1 ETH",
            terms={"duration": "perpetual"}
        )

        return result

# Run
result = asyncio.run(post_transaction())
```

---

## Integration with RRA Negotiation Flow

### Complete Negotiation Recording

Record the full negotiation lifecycle on-chain:

```python
from rra.integration.natlangchain_client import NatLangChainClient
from rra.agents.negotiator import NegotiationAgent

client = NatLangChainClient(base_url="http://localhost:5000", agent_id="rra-negotiator")
agent = NegotiationAgent()

repo_url = "https://github.com/owner/repo"
buyer_id = "did:nlc:buyer123"

# Step 1: Record quote request
client.post_negotiation_intent(
    repo_url=repo_url,
    intent_type="quote_requested",
    details={"buyer_id": buyer_id, "budget": "1 ETH"}
)

# Step 2: Run negotiation
result = agent.negotiate(repo_url, buyer_id)

# Step 3: Record each offer/counter-offer
for round in result.rounds:
    client.post_negotiation_intent(
        repo_url=repo_url,
        intent_type=round.type,
        details=round.details
    )

# Step 4: Record final transaction
if result.success:
    client.post_rra_transaction(
        repo_url=repo_url,
        buyer_id=buyer_id,
        license_model=result.license_model,
        price=result.final_price,
        terms=result.terms
    )
```

---

## Data Models

### ChainEntry

```python
@dataclass
class ChainEntry:
    content: str                    # Natural language content
    author: str                     # Entry creator identifier
    intent: str                     # Brief purpose summary
    timestamp: str                  # ISO timestamp
    status: str                     # pending, mined, validated
    entry_id: Optional[str]         # Unique entry identifier
    block_hash: Optional[str]       # Block hash if mined
    validation_status: Optional[str] # LLM validation result
```

### ChainHealth

```python
@dataclass
class ChainHealth:
    status: str                     # healthy, degraded, error
    service: str                    # Service name
    blocks: int                     # Number of blocks
    pending_entries: int            # Entries awaiting mining
    llm_validation_available: bool  # Whether LLM validation is enabled
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NATLANGCHAIN_URL` | `http://localhost:5000` | NatLangChain API URL |
| `NATLANGCHAIN_TIMEOUT` | `30` | Request timeout (seconds) |
| `NATLANGCHAIN_AGENT_ID` | `rra-agent` | Default agent identifier |

### Per-Environment Configuration

```python
# Development
client = NatLangChainClient(base_url="http://localhost:5000")

# Staging
client = NatLangChainClient(base_url="https://staging.natlangchain.io")

# Production
client = NatLangChainClient(base_url="https://api.natlangchain.io")
```

---

## Error Handling

All client methods return a tuple of `(success: bool, result)`:

```python
success, result = client.post_entry(...)

if not success:
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Failed: {result}")
```

Common error scenarios:
- Connection refused: NatLangChain server not running
- Timeout: Server is slow or overloaded
- Validation failed: LLM rejected the entry content
- Invalid payload: Missing required fields

---

## Testing

### Unit Tests

Run unit tests (no server required):

```bash
pytest tests/test_natlangchain_integration.py -v
```

### Integration Tests

Run integration tests against a live server:

```bash
# Start NatLangChain server first
cd /path/to/NatLangChain
python run_server.py

# Run integration tests
pytest tests/test_natlangchain_integration.py -v -m integration
```

### Mock Server

For development, use the mock server:

```python
# tests/mock_natlangchain_server.py provides a mock implementation
from tests.mock_natlangchain_server import MockNatLangChainServer

server = MockNatLangChainServer()
server.start(port=5001)

# Test against mock
client = NatLangChainClient(base_url="http://localhost:5001")
```

---

## Best Practices

### 1. Use Meaningful Intents
Intents should be concise summaries that enable searching:
```python
# Good
intent = "License github.com/owner/repo to buyer-123"

# Bad
intent = "Transaction"
```

### 2. Include Structured Metadata
Always include queryable metadata:
```python
metadata = {
    "type": "rra_transaction",
    "repo_url": repo_url,
    "buyer_id": buyer_id,
    "price": price,
    "timestamp": datetime.now().isoformat()
}
```

### 3. Handle Connection Failures
```python
success, health = client.health_check()
if not success:
    # Fall back to local recording or retry later
    logger.warning("NatLangChain unavailable, queuing transaction")
    queue_for_later(transaction)
```

### 4. Use Async for High Throughput
For applications with many concurrent transactions:
```python
async def batch_post_transactions(transactions):
    async with AsyncNatLangChainClient() as client:
        tasks = [
            client.post_rra_transaction(**tx)
            for tx in transactions
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

---

## Related Documentation

- [NatLangChain Roadmap](../NatLangChain-roadmap.md) - Project vision and phases
- [Blockchain Licensing](./BLOCKCHAIN-LICENSING.md) - License NFT integration
- [Story Protocol](./STORY_PROTOCOL.md) - IP asset management
- [API Reference](./README.md) - Full API documentation

## Support

- GitHub Issues: https://github.com/natlangchain/rra-module/issues
- Discord: https://discord.gg/natlangchain
