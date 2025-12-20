# Transaction Security: Two-Step Verification with Timeout

**Version:** 1.0.0
**Last Updated:** 2025-12-20
**Status:** ✅ Complete (Phase 5)

---

## Overview

The RRA Module implements comprehensive transaction security to prevent accidental purchases, price manipulation, and state machine vulnerabilities. This system was developed after a 100-transaction security simulation that identified 26 critical vulnerabilities.

### Vulnerabilities Addressed

| Category | Count | Description | Solution |
|----------|-------|-------------|----------|
| Soft Locks | 4 | No timeout in negotiation phases | Timeout auto-cancellation |
| Validation Bypass | 12 | Negative values, floor > target, overflow | Price validation and bounds |
| Price Manipulation | 10 | Bait-and-switch, currency confusion, injection | Cryptographic price commitment |

---

## Architecture

```
User Agreement
    ↓
[PriceCommitment] ─────────────────────────────────────────────┐
    ├─ Cryptographic hash of price                            │
    ├─ Timestamp binding                                       │
    └─ Nonce for uniqueness                                   │
    ↓                                                          │
[PendingTransaction] ─────────────────────────────────────────┤
    ├─ Locked price (cannot be changed)                       │
    ├─ Expiry timestamp                                        │
    ├─ Confirmation counter                                    │
    └─ Validation status                                       │
    ↓                                                          │
[TransactionConfirmation] ────────────────────────────────────┤
    ├─ Step 1: create_pending_transaction()                   │
    ├─ Step 2: confirm_transaction()                          │
    ├─ Timeout: cleanup_expired()                             │
    └─ Audit: get_audit_log()                                 │
    ↓                                                          │
[TransactionSafeguards] ──────────────────────────────────────┘
    ├─ Safeguard levels (LOW, MEDIUM, HIGH, CRITICAL)
    ├─ Rate limiting
    ├─ Price display formatting
    └─ Explicit confirmation prompts
```

---

## Components

### PriceCommitment

Cryptographic commitment to a specific price that prevents price manipulation.

```python
# Location: src/rra/transaction/confirmation.py

from rra.transaction import PriceCommitment

# Create commitment (locks in price)
commitment = PriceCommitment.create("0.5 ETH")

print(commitment.amount)      # 0.5
print(commitment.currency)    # "ETH"
print(commitment.commitment_hash)  # bytes32 hash

# Verify price matches commitment
assert commitment.verify("0.5 ETH") == True
assert commitment.verify("0.6 ETH") == False  # Price changed!
```

**Security Properties:**
- Hash includes timestamp and random nonce
- Each commitment is unique, even for same price
- Cannot be modified after creation

### PendingTransaction

Transaction awaiting user confirmation with timeout protection.

```python
# Location: src/rra/transaction/confirmation.py

from rra.transaction import PendingTransaction, TransactionStatus

@dataclass
class PendingTransaction:
    transaction_id: str
    buyer_id: str
    seller_id: str
    repo_url: str
    license_model: str
    price_commitment: PriceCommitment
    floor_price: float
    target_price: float
    created_at: datetime
    expires_at: datetime
    status: TransactionStatus
    confirmation_count: int
    required_confirmations: int

# Check transaction state
assert pending.is_pending == True
assert pending.is_expired == False
assert pending.time_remaining.total_seconds() > 0

# Validate price bounds
validation = pending.validate_price()
# {"valid": True, "warnings": ["Price below target"]}
```

**Lifecycle States:**
```
PENDING_CONFIRMATION → CONFIRMED → EXECUTED
                    ↘
                     CANCELLED / EXPIRED / FAILED
```

### TransactionConfirmation

Manager for two-step verification with callbacks and cleanup.

```python
# Location: src/rra/transaction/confirmation.py

from rra.transaction import TransactionConfirmation

# Configure manager
def on_confirmed(tx):
    print(f"Transaction {tx.transaction_id} confirmed!")

def on_expired(tx):
    print(f"Transaction {tx.transaction_id} expired!")

manager = TransactionConfirmation(
    default_timeout=300,  # 5 minutes
    on_confirmed=on_confirmed,
    on_expired=on_expired,
    require_double_confirmation=False
)

# Step 1: Create pending transaction
pending = manager.create_pending_transaction(
    buyer_id="buyer123",
    seller_id="seller456",
    repo_url="https://github.com/example/repo",
    license_model="perpetual",
    agreed_price="0.5 ETH",
    floor_price="0.3 ETH",
    target_price="0.6 ETH",
    timeout_seconds=300  # Override default
)

# Show confirmation UI
display = pending.to_confirmation_display()
print(display["confirmation_message"])

# Step 2: User confirms
result = manager.confirm_transaction(pending.transaction_id)
if result["success"]:
    print("Ready to execute!")
else:
    print(f"Error: {result['error']}")

# Cleanup expired transactions (run periodically)
expired_count = manager.cleanup_expired()
```

**Configuration Options:**

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `default_timeout` | 300s (5 min) | 30s-3600s | Time before auto-cancel |
| `require_double_confirmation` | False | - | Require 2 confirmations |
| `on_confirmed` | None | - | Callback when confirmed |
| `on_expired` | None | - | Callback when expired |
| `min_timeout` | 30s | - | Minimum allowed timeout |

### TransactionSafeguards

UI/UX protection layer with safeguard levels and rate limiting.

```python
# Location: src/rra/transaction/safeguards.py

from rra.transaction import TransactionSafeguards, SafeguardLevel

safeguards = TransactionSafeguards(
    enable_rate_limiting=True,
    custom_rates={"ETH": 2500}  # Override default ETH/USD rate
)

# Validate price with context
validation = safeguards.validate_price(
    price_str="0.5 ETH",
    floor_price="0.3 ETH",
    target_price="0.6 ETH",
    context="perpetual license"
)

print(validation.is_valid)           # True
print(validation.safeguard_level)    # SafeguardLevel.HIGH (~$1000)
print(validation.display_string)     # "0.5000 ETH (~$1,250.00 USD)"
print(validation.warnings)           # ["Price is 16.7% below target price"]
print(validation.confirmation_prompt) # Formatted prompt for user

# Check rate limit
allowed, message = safeguards.check_rate_limit("buyer123")
if not allowed:
    print(message)  # "Rate limit exceeded..."

# Verify user confirmation input
valid, error = safeguards.verify_explicit_confirmation(
    user_input="CONFIRM",
    expected_amount=0.5,
    expected_currency="ETH",
    level=SafeguardLevel.HIGH
)

# Generate formatted confirmation screen
screen = safeguards.format_confirmation_screen(
    transaction_data={
        "repo_url": "https://github.com/example/repo",
        "license_model": "perpetual",
        "price": "0.5 ETH",
        "warnings": ["Price below target"]
    },
    time_remaining=120  # seconds
)
print(screen)
```

---

## Safeguard Levels

The system automatically determines safeguard level based on USD value:

| Level | USD Threshold | Confirmation Required |
|-------|--------------|----------------------|
| LOW | < $50 | Click "CONFIRM" |
| MEDIUM | < $500 | Click "CONFIRM" |
| HIGH | < $5,000 | Type "CONFIRM" |
| CRITICAL | ≥ $5,000 | Type exact amount (e.g., "10 ETH") |

**Currency Conversion (Default Rates):**
```python
CURRENCY_RATES = {
    "ETH": 2000,   # ~$2000/ETH
    "USDC": 1,
    "USDT": 1,
    "DAI": 1,
    "USD": 1,
}
```

---

## Confirmation Flow

### Standard Flow (Single Confirmation)

```
User                    System                  Ledger
  │                         │                       │
  ├──[1] Agree to price────►│                       │
  │                         │                       │
  │                         ├──[2] Create pending──►│
  │                         │     (lock price)      │
  │                         │                       │
  │◄─[3] Show confirmation──┤                       │
  │     screen              │                       │
  │                         │                       │
  ├──[4] Type "CONFIRM"────►│                       │
  │                         │                       │
  │                         ├──[5] Execute─────────►│
  │                         │                       │
  │◄─[6] Transaction ID─────┤                       │
```

### Double Confirmation Flow (High Security)

```
User                    System                  Ledger
  │                         │                       │
  ├──[1] Agree to price────►│                       │
  │                         ├──[2] Create pending──►│
  │                         │                       │
  │◄─[3] First confirm──────┤                       │
  ├──[4] "CONFIRM"─────────►│                       │
  │                         │                       │
  │◄─[5] Second confirm─────┤                       │
  │     (CRITICAL only)     │                       │
  ├──[6] Type "0.5 ETH"────►│                       │
  │                         │                       │
  │                         ├──[7] Execute─────────►│
  │◄─[8] Transaction ID─────┤                       │
```

### Timeout Flow (Auto-Cancel)

```
User                    System                  Ledger
  │                         │                       │
  ├──[1] Agree to price────►│                       │
  │                         ├──[2] Create pending──►│
  │                         │     (expires 5 min)   │
  │                         │                       │
  │◄─[3] Show confirmation──┤                       │
  │                         │                       │
  │    (user walks away)    │                       │
  │                         │                       │
  │                         ├──[4] Timeout──────────┤
  │                         │     (cleanup daemon)  │
  │                         │                       │
  │                         ├──[5] Mark expired────►│
  │                         │                       │
  │◄─[6] "Transaction expired"                      │
```

---

## Confirmation UI Example

```
==================================================
           TRANSACTION CONFIRMATION
==================================================

  Repository: https://github.com/example/repo
  License:    perpetual

--------------------------------------------------
  TOTAL PRICE: 0.5000 ETH (~$1,250.00 USD)
--------------------------------------------------

  WARNINGS:
    ! Price is 16.7% below target price

  Time remaining: 4:32

  This transaction is FINAL and cannot be undone.

==================================================
  Type 'CONFIRM' to proceed
  Type 'CANCEL' to abort
==================================================
```

---

## Rate Limiting

Prevents transaction spam and protects users from rapid-fire mistakes.

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max transactions/hour | 10 | Per buyer |
| Cooldown period | 1 hour | Rolling window |

```python
# Check before creating transaction
allowed, message = safeguards.check_rate_limit(buyer_id)
if not allowed:
    raise RateLimitError(message)

# Record successful transaction
safeguards.record_transaction()
```

---

## Audit Logging

All transaction actions are logged for audit trail.

```python
# Get audit log for specific transaction
logs = manager.get_audit_log(transaction_id="abc123")

# Sample log entries:
[
    {
        "timestamp": "2025-12-20T10:00:00Z",
        "action": "created",
        "transaction_id": "abc123",
        "buyer_id": "buyer456",
        "seller_id": "seller789",
        "price": "0.5 ETH",
        "status": "pending_confirmation"
    },
    {
        "timestamp": "2025-12-20T10:02:30Z",
        "action": "confirmed",
        "transaction_id": "abc123",
        ...
    }
]

# Get system-wide statistics
stats = manager.get_stats()
# {
#     "pending": 3,
#     "confirmed": 145,
#     "cancelled": 12,
#     "expired": 28,
#     "confirmation_rate": 0.78,
#     "expiry_rate": 0.15
# }
```

---

## Integration Example

### Complete License Purchase Flow

```python
from rra.transaction import TransactionConfirmation, TransactionSafeguards
from rra.auth import WebAuthnClient

# Initialize components
safeguards = TransactionSafeguards()
manager = TransactionConfirmation(default_timeout=300)

async def purchase_license(
    buyer_wallet: str,
    repo_url: str,
    agreed_price: str,
    floor_price: str,
    target_price: str
):
    # 1. Validate price
    validation = safeguards.validate_price(
        agreed_price,
        floor_price=floor_price,
        target_price=target_price
    )

    if not validation.is_valid:
        raise ValueError(f"Price validation failed: {validation.errors}")

    if validation.warnings:
        print(f"Warnings: {validation.warnings}")

    # 2. Check rate limit
    allowed, msg = safeguards.check_rate_limit(buyer_wallet)
    if not allowed:
        raise RateLimitError(msg)

    # 3. Create pending transaction (Step 1)
    pending = manager.create_pending_transaction(
        buyer_id=buyer_wallet,
        seller_id=get_repo_owner(repo_url),
        repo_url=repo_url,
        license_model="perpetual",
        agreed_price=agreed_price,
        floor_price=floor_price,
        target_price=target_price
    )

    # 4. Show confirmation UI
    display = pending.to_confirmation_display()
    user_input = await show_confirmation_screen(display)

    # 5. Verify confirmation input
    valid, error = safeguards.verify_explicit_confirmation(
        user_input,
        pending.price_commitment.amount,
        pending.price_commitment.currency,
        validation.safeguard_level
    )

    if not valid:
        manager.cancel_transaction(pending.transaction_id)
        raise ConfirmationError(error)

    # 6. Confirm transaction (Step 2)
    result = manager.confirm_transaction(pending.transaction_id)

    if not result["success"]:
        raise TransactionError(result["error"])

    # 7. Execute on-chain
    tx_hash = await execute_on_chain(result["transaction"])

    # 8. Record for rate limiting
    safeguards.record_transaction()

    return tx_hash
```

---

## Testing

All transaction security components have comprehensive test coverage:

```bash
# Run transaction security tests (36 tests)
PYTHONPATH=./src pytest tests/test_transaction_confirmation.py -v

# Expected output:
# 36 passed
```

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| PriceCommitment | 8 | Creation, validation, uniqueness |
| TransactionConfirmation | 12 | Create, confirm, cancel, timeout |
| TransactionSafeguards | 9 | Validation, levels, rate limiting |
| Integration | 3 | Full flow, timeout, manipulation |
| Security | 4 | Concurrency, edge cases |

---

## Security Considerations

### Price Manipulation Prevention
- Cryptographic commitment binds price at agreement
- Hash includes random nonce - cannot be precomputed
- Timestamp binding prevents replay attacks

### Soft Lock Prevention
- All pending transactions have expiry
- Background cleanup daemon runs every 10 seconds
- Manual cleanup available: `manager.cleanup_expired()`

### Validation Bypass Prevention
- Floor price enforced at creation time
- Negative prices rejected at parsing
- Overflow protection with maximum bounds

### Accidental Click Prevention
- Two-step confirmation required
- Safeguard levels scale with value
- Critical transactions require typing exact amount
- Rate limiting prevents rapid mistakes

---

## Background Cleanup Daemon

For production deployments, start the cleanup daemon:

```python
manager = TransactionConfirmation()

# Start background cleanup (runs every 10 seconds)
manager.start_cleanup_daemon(interval_seconds=10)

# Stop when shutting down
manager.stop_cleanup_daemon()
```

---

## Related Documentation

- **[Hardware Authentication](HARDWARE-AUTHENTICATION.md)** - FIDO2 integration
- **[Security Audit](SECURITY-AUDIT.md)** - Security review
- **[Blockchain Licensing](BLOCKCHAIN-LICENSING.md)** - On-chain execution
- **[SPECIFICATION.md](../SPECIFICATION.md)** - Phase 5 status

---

## License

Copyright 2025 Kase Branham. Licensed under FSL-1.1-ALv2.
