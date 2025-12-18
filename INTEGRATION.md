# RRA Module - NatLangChain Ecosystem Integration

## Overview

The RRA Module is designed as a **first-class NatLangChain extension** that works both standalone and fully integrated with the NatLangChain ecosystem. This modular architecture follows the **langchain-community** pattern - tightly integrated by default but portable and independent.

## Architecture Philosophy

### Best-of-Both-Worlds Approach

1. **Standalone Mode (Default)**: Works out-of-the-box with no dependencies on other NatLangChain components
2. **Integrated Mode**: Automatically leverages ecosystem components when available
3. **Hybrid Mode**: Selectively uses available components with graceful fallbacks

This design maximizes:
- **Ecosystem Synergy**: Tight integration when running in NatLangChain
- **Portability**: Can be used independently or in other frameworks
- **Reliability**: Graceful degradation when services are unavailable

## Integration Components

The RRA Module integrates with the following NatLangChain ecosystem components:

### 1. **common** - Shared Interfaces
- Base agent protocols and interfaces
- Shared data structures
- Common utilities

### 2. **Agent-OS** - Agent Runtime
- Agent lifecycle management
- Distributed agent deployment
- Runtime orchestration

### 3. **memory-vault** - State Persistence
- Distributed agent state storage
- Cross-instance state synchronization
- Conversation history persistence

**Usage:**
```python
from rra.agents.negotiator import NegotiatorAgent

# Standalone: Uses local file storage
agent = NegotiatorAgent(kb)

# Integrated: Uses memory-vault
agent = NegotiatorAgent(kb, integrated=True)
# State automatically persists to memory-vault
agent.save_state()
```

### 4. **value-ledger** - Transaction Tracking
- Revenue and payment tracking
- Cross-repo analytics
- On-chain transaction verification

**Usage:**
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

# Get revenue statistics
stats = ledger.get_revenue_stats()
print(f"Total revenue: {stats['total_revenue']} ETH")
```

### 5. **mediator-node** - Message Routing
- Agent-to-agent communication
- Load balancing and resilience
- Network-wide message routing

**Usage:**
```python
from rra.integration.mediator import get_message_router

router = get_message_router(agent.agent_id)

# Send message to another agent
router.send_message(
    to_agent="buyer_agent_789",
    message={"type": "proposal", "price": "0.05 ETH"}
)

# Receive messages
message = router.receive_message()
```

### 6. **IntentLog** - Decision Auditing
- Agent intent logging
- Decision rationale tracking
- Audit trail for compliance

**Usage:**
```python
# Automatic logging in integrated mode
agent = NegotiatorAgent(kb, integrated=True)

# Log intents automatically
agent.log_intent("negotiate_price", {
    "proposed": "0.03 ETH",
    "floor": "0.02 ETH",
    "target": "0.05 ETH"
})

# Log decisions with rationale
agent.log_decision("accept_offer", {
    "final_price": "0.04 ETH",
    "reason": "Above floor, good faith negotiation"
})
```

### 7. **synth-mind** - LLM Integration
- Shared LLM routing and management
- Cost optimization
- Response caching

### 8. **boundary-daemon** - Permissions
- Access control
- License validation
- Permission boundaries

### 9. **learning-contracts** - Adaptive Contracts
- Self-optimizing pricing
- Dynamic terms adjustment
- Performance-based licensing

## Installation

### Standalone Installation
```bash
pip install rra-module
```

### With NatLangChain Ecosystem
```bash
pip install rra-module[natlangchain]
```

### Full Installation (All Extras)
```bash
pip install rra-module[all]
```

## Usage Examples

### Example 1: Standalone Mode (Default)

```python
from rra.agents.negotiator import NegotiatorAgent
from rra.ingestion.knowledge_base import KnowledgeBase
from rra.config.market_config import MarketConfig, LicenseModel

# Create knowledge base
kb = KnowledgeBase(
    repo_path="./my-repo",
    repo_url="https://github.com/user/my-repo.git"
)
kb.market_config = MarketConfig(
    target_price="0.05 ETH",
    floor_price="0.02 ETH",
    license_model=LicenseModel.PER_SEAT
)

# Create agent in standalone mode
agent = NegotiatorAgent(kb)

# Use normally
intro = agent.start_negotiation()
response = agent.respond("What's the price?")
```

### Example 2: Integrated Mode

```python
from rra.agents.negotiator import NegotiatorAgent

# Create agent with full NatLangChain integration
agent = NegotiatorAgent(kb, integrated=True)

# Automatically uses:
# - memory-vault for state persistence
# - IntentLog for decision auditing
# - mediator-node for message routing
# - value-ledger for transaction tracking

# Check integration status
status = agent.get_integration_status()
print(f"Mode: {status['mode']}")
print(f"State Persistence: {status['integrations']['state_persistence']}")
print(f"Intent Logging: {status['integrations']['intent_logging']}")

# Start negotiation - state automatically persists
intro = agent.start_negotiation()

# Respond to buyer - intents automatically logged
response = agent.respond("I can offer 0.03 ETH")

# State is automatically saved after each interaction
```

### Example 3: Hybrid Mode with Manual Control

```python
from rra.integration.config import IntegrationConfig, set_integration_config

# Configure selective integration
config = IntegrationConfig(
    enable_memory_vault=True,   # Use distributed state
    enable_value_ledger=True,   # Track transactions
    enable_mediator_node=False, # Disable message routing
    enable_intent_log=False,    # Disable intent logging
    fallback_to_standalone=True # Gracefully fall back if services fail
)
set_integration_config(config)

# Agent will use only enabled integrations
agent = NegotiatorAgent(kb, integrated=True)
```

## Configuration

### Integration Configuration File

Create `.rra-integration.yaml` in your project root:

```yaml
# Auto-detect available integrations
auto_detect_mode: true

# Force standalone mode even if integrations are available
force_standalone: false

# Component-specific settings
enable_memory_vault: true
enable_value_ledger: true
enable_mediator_node: true
enable_intent_log: true
enable_agent_os: true
enable_synth_mind: true

# Service URLs (optional, auto-discovered if not specified)
memory_vault_url: "http://localhost:5001"
value_ledger_url: "http://localhost:5002"
mediator_node_url: "http://localhost:5003"
intent_log_url: "http://localhost:5004"

# Agent-OS settings
agent_os_runtime: "distributed"  # local, distributed, cloud

# Fallback behavior
fallback_to_standalone: true
```

## Integration Modes

### Standalone Mode
- **No external dependencies**: Works completely independently
- **Local storage**: Uses local files for state/logs/transactions
- **Direct communication**: No mediator routing
- **Best for**: Development, testing, single-instance deployments

### Integrated Mode
- **Full ecosystem integration**: Uses all available NatLangChain components
- **Distributed**: Multi-instance agent deployments
- **Networked**: Cross-agent communication via mediator nodes
- **Best for**: Production, multi-repo marketplaces, enterprise deployments

### Hybrid Mode
- **Selective integration**: Use only specific components
- **Graceful degradation**: Falls back to local when services unavailable
- **Best for**: Transitioning to full integration, partial deployments

## Migration Guide

### From Standalone to Integrated

1. **Install ecosystem packages**:
   ```bash
   pip install rra-module[natlangchain]
   ```

2. **Enable integration mode**:
   ```python
   # Before
   agent = NegotiatorAgent(kb)

   # After
   agent = NegotiatorAgent(kb, integrated=True)
   ```

3. **Configure services** (optional):
   Create `.rra-integration.yaml` with service URLs

4. **Migrate existing state**:
   ```python
   # Load old state from local files
   from pathlib import Path
   import json

   old_state = json.load(open("./agent_states/agent_123.json"))

   # Create integrated agent
   agent = NegotiatorAgent(kb, integrated=True, agent_id="agent_123")

   # Restore state (automatically persists to memory-vault)
   agent.restore_state(old_state["state"])
   ```

## Benefits of Integration

### 1. Ecosystem Synergy
- **Unified marketplace**: All RRA agents visible in NatLangChain discovery
- **Cross-agent communication**: Buyers can negotiate with multiple repos
- **Shared reputation**: Reputation scores across the network

### 2. Virality Flywheel
- **Self-selling**: Every negotiation demonstrates the system
- **Network effects**: Each new repo increases value for all
- **Seamless upsell**: "Add .market.yaml to your repo" in every interaction

### 3. Operational Excellence
- **High availability**: Distributed state and load balancing
- **Observability**: Centralized logging and monitoring
- **Analytics**: Cross-repo insights and optimization

### 4. Developer Experience
- **Zero configuration**: Works out of the box
- **Progressive enhancement**: Add integrations as needed
- **Backward compatible**: Existing code continues to work

## Roadmap

### Phase 1: Foundation (Current)
- ✅ Standalone mode fully functional
- ✅ Integration layer architecture
- ✅ Optional dependencies configured
- ✅ Core integrations (memory-vault, value-ledger, mediator-node, IntentLog)

### Phase 2: Ecosystem Integration
- 🔄 Publish to NatLangChain package registry
- 🔄 Agent-OS runtime integration
- 🔄 synth-mind LLM integration
- 🔄 boundary-daemon permissions

### Phase 3: Advanced Features
- ⏳ learning-contracts adaptive pricing
- ⏳ Multi-repo bundling
- ⏳ Cross-chain support (Solana, Polygon)
- ⏳ Story Protocol integration for IP licensing

### Phase 4: Platform Features
- ⏳ Marketplace UI
- ⏳ Webhook endpoints
- ⏳ Embeddable widgets
- ⏳ Mobile SDKs

## Contributing

We welcome contributions to enhance NatLangChain integration! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Integration Development

1. **Add new integration**:
   - Create integration module in `src/rra/integration/`
   - Implement fallback for standalone mode
   - Add configuration options
   - Update documentation

2. **Test both modes**:
   ```bash
   # Test standalone
   pytest tests/

   # Test integrated (requires services)
   INTEGRATION_MODE=true pytest tests/integration/
   ```

## Support

- **Issues**: https://github.com/kase1111-hash/RRA-Module/issues
- **Discussions**: https://github.com/kase1111-hash/RRA-Module/discussions
- **NatLangChain Docs**: [Coming soon]

## License

MIT License - See [LICENSE.md](LICENSE.md)
