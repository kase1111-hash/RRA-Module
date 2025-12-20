# FIDO2/WebAuthn Hardware Authentication

**Version:** 1.0.0
**Last Updated:** 2025-12-20
**Status:** ✅ Complete (Phase 5)

---

## Overview

The RRA Module supports hardware-backed authentication using FIDO2/WebAuthn standards, enabling secure license transactions with YubiKeys, biometric authenticators, and other FIDO2-compliant devices.

### Key Features

| Feature | Description |
|---------|-------------|
| **Hardware-Verified Identity** | Cryptographic proof of hardware credential ownership |
| **Anonymous Group Membership** | Semaphore-style ZK proofs for privacy |
| **Scoped Delegation** | Agent authorization with spending limits |
| **Three Auth Modes** | Direct FIDO2, Anonymous ZK, Delegated |
| **EIP-7212 Support** | Native secp256r1 verification with fallback |

---

## Architecture

```
User Device (YubiKey, Biometric)
    ↓
[WebAuthn Client] ─────────────────────────────────────────────┐
    ├─ Challenge generation                                    │
    ├─ Credential registration                                 │
    └─ Assertion signing (secp256r1)                          │
    ↓                                                          │
[P256Verifier.sol]                                             │
    ├─ EIP-7212 precompile detection                          │
    ├─ Native P-256 verification (~100k gas on L2)            │
    └─ Pure Solidity fallback (~300k gas)                     │
    ↓                                                          │
[WebAuthnVerifier.sol]                                         │
    ├─ Challenge management with expiry                        │
    ├─ Credential registration                                 │
    └─ Full assertion verification                            │
    ↓                                                          │
[ILRMv2.sol] ─────────────────────────────────────────────────┘
    ├─ AuthMode: DirectFIDO2, AnonymousZK, Delegated
    ├─ HardwareAction audit logging
    └─ Integration with HardwareIdentityGroup
```

---

## Components

### Smart Contracts

#### P256Verifier.sol
Provides secp256r1 (P-256) signature verification for FIDO2 authentication.

```solidity
// Location: contracts/src/P256Verifier.sol

interface IP256Verifier {
    function verify(
        bytes32 messageHash,
        bytes32 r,
        bytes32 s,
        uint256 qx,
        uint256 qy
    ) external view returns (bool);
}
```

**Features:**
- EIP-7212 precompile auto-detection
- Pure Solidity fallback for chains without precompile
- ~100k gas with precompile, ~300k without

#### WebAuthnVerifier.sol
Full FIDO2/WebAuthn assertion verification.

```solidity
// Location: contracts/src/WebAuthnVerifier.sol

struct WebAuthnCredential {
    bytes credentialId;
    uint256 publicKeyX;
    uint256 publicKeyY;
    uint256 counter;
    address owner;
}

function verifyAssertion(
    bytes32 challenge,
    bytes calldata authenticatorData,
    bytes calldata clientDataJSON,
    bytes32 r,
    bytes32 s,
    bytes calldata credentialId
) external returns (bool);
```

**Features:**
- Challenge creation with expiry (5 minutes default)
- Credential registration and lookup
- Replay attack prevention with counter validation
- Full WebAuthn assertion verification

#### ScopedDelegation.sol
Hardware-backed agent authorization with spending limits.

```solidity
// Location: contracts/src/ScopedDelegation.sol

struct Delegation {
    address owner;
    address agent;
    uint256 expiresAt;
    uint256 ethLimit;
    mapping(address => uint256) tokenLimits;
    mapping(ActionType => bool) allowedActions;
}

enum ActionType {
    MarketMatch,
    DisputeStake,
    LicenseTransfer,
    RoyaltyCollection,
    MetadataUpdate
}
```

**Features:**
- Per-token spending limits
- Per-ETH spending limits
- Action-type restrictions
- Hardware-verified delegation creation
- Expiration support

#### HardwareIdentityGroup.sol
Semaphore-style anonymous group membership for privacy-preserving authentication.

```solidity
// Location: contracts/src/HardwareIdentityGroup.sol

function addMember(
    uint256 identityCommitment,
    bytes32 r,
    bytes32 s,
    bytes calldata credentialId
) external;

function verifyMembership(
    uint256 merkleRoot,
    uint256 nullifierHash,
    uint256 externalNullifier,
    uint256[8] calldata proof
) external returns (bool);
```

**Features:**
- Merkle tree membership (depth=20, ~1M members)
- Nullifier tracking for replay prevention
- ZK proof verification integration
- Hardware-verified member addition

#### ILRMv2.sol
IP Licensing Reconciliation Module with hardware authentication.

```solidity
// Location: contracts/src/ILRMv2.sol

enum AuthMode {
    DirectFIDO2,   // Standard hardware key verification
    AnonymousZK,   // Privacy-preserving group membership
    Delegated      // Agent acting on behalf of hardware owner
}

struct HardwareAction {
    AuthMode mode;
    address actor;
    uint256 timestamp;
    bytes32 actionHash;
}
```

---

### ZK Circuits

#### hardware_identity.circom
Zero-knowledge proof of hardware credential ownership.

```circom
// Location: circuits/hardware_identity.circom

template HardwareIdentity() {
    signal input credentialSecret;     // Private: raw credential secret
    signal input salt;                 // Private: additional entropy
    signal output identityCommitment;  // Public: Poseidon hash
    signal output nullifier;           // Public: prevents double-use

    // Poseidon hash for identity commitment
    identityCommitment <== Poseidon(2)([credentialSecret, salt]);

    // Nullifier for specific context
    nullifier <== Poseidon(2)([identityCommitment, externalNullifier]);
}
```

**Use Cases:**
- Prove hardware credential ownership without revealing credential
- Generate unique nullifiers per-action to prevent replay
- Compatible with Semaphore group membership

#### semaphore_membership.circom
Anonymous group membership proof.

```circom
// Location: circuits/semaphore_membership.circom

template SemaphoreMembership(levels) {
    signal input identityCommitment;   // Private
    signal input pathIndices[levels];  // Private: Merkle path
    signal input siblings[levels];     // Private: Merkle siblings
    signal input root;                 // Public: Merkle root
    signal input nullifierHash;        // Public
    signal input externalNullifier;    // Public

    // Verify Merkle inclusion
    // Verify nullifier derivation
}
```

**Features:**
- Tree depth: 20 levels (~1M members)
- Poseidon hashing for efficiency
- Standard Semaphore protocol compatible

---

### Python Client

#### WebAuthn Client
```python
# Location: src/rra/auth/webauthn.py

from rra.auth.webauthn import WebAuthnClient

client = WebAuthnClient(rp_id="natlangchain.io")

# Register credential
credential = await client.register(
    user_id="user123",
    user_name="alice@example.com"
)

# Authenticate
assertion = await client.authenticate(
    challenge=b"random_challenge",
    credential_id=credential.id
)

# Verify signature (P-256)
valid = client.verify_signature(
    message_hash=assertion.client_data_hash,
    signature=assertion.signature,
    public_key=credential.public_key
)
```

#### Hardware Identity Manager
```python
# Location: src/rra/auth/identity.py

from rra.auth.identity import HardwareIdentity, IdentityGroupManager

# Create identity from credential
identity = HardwareIdentity.from_credential(
    credential_secret=credential.secret,
    salt=os.urandom(32)
)

# Get identity commitment for on-chain registration
commitment = identity.commitment  # bytes32

# Generate ZK proof inputs
proof_inputs = identity.generate_proof_inputs(
    external_nullifier=action_id
)
```

#### Scoped Delegation Manager
```python
# Location: src/rra/auth/delegation.py

from rra.auth.delegation import DelegationManager, DelegationScope

manager = DelegationManager(contract_address="0x...")

# Create delegation with limits
delegation = await manager.create_delegation(
    agent_address="0x...",
    scope=DelegationScope(
        eth_limit=1.0,
        token_limits={"USDC": 1000},
        allowed_actions=[
            ActionType.MarketMatch,
            ActionType.LicenseTransfer
        ],
        expires_in=timedelta(days=30)
    ),
    credential=hardware_credential
)
```

---

## Authentication Flows

### Flow 1: Direct FIDO2 Authentication

```
User                    WebAuthn                 ILRMv2
  │                         │                       │
  ├──[1] Request action────►│                       │
  │                         │                       │
  │◄─[2] Challenge──────────┤                       │
  │                         │                       │
  ├──[3] Sign with YubiKey─►│                       │
  │                         │                       │
  │                         ├──[4] Verify sig──────►│
  │                         │     (P256Verifier)    │
  │                         │                       │
  │                         │◄─[5] Action executed──┤
  │◄────────────────────────┤                       │
```

### Flow 2: Anonymous ZK Authentication

```
User                    ZK Prover               ILRMv2
  │                         │                       │
  ├──[1] Generate proof────►│                       │
  │     (identity + path)   │                       │
  │                         │                       │
  │◄─[2] ZK proof───────────┤                       │
  │                         │                       │
  ├──[3] Submit proof──────────────────────────────►│
  │     (no identity revealed)                      │
  │                         │                       │
  │◄─[4] Action executed (anonymous)────────────────┤
```

### Flow 3: Delegated Agent Authentication

```
Owner                   Agent                   ILRMv2
  │                         │                       │
  ├──[1] Create delegation─────────────────────────►│
  │     (FIDO2 signed)      │                       │
  │                         │                       │
  │                         ├──[2] Request action──►│
  │                         │     (as delegate)     │
  │                         │                       │
  │                         │◄─[3] Check limits─────┤
  │                         │                       │
  │                         │◄─[4] Action executed──┤
```

---

## Gas Costs

| Operation | With EIP-7212 | Without Precompile |
|-----------|---------------|-------------------|
| P256 Signature Verify | ~100k | ~300k |
| WebAuthn Assertion | ~150k | ~350k |
| Create Delegation | ~80k | ~80k |
| ZK Proof Verify | ~200k | ~200k |

**Recommended Chains:**
- Ethereum L2s (Optimism, Base, Arbitrum) - Lower gas costs
- Polygon - EIP-7212 support expected
- zkSync - Native ZK support

---

## Security Considerations

### Hardware Security
- Private keys never leave the hardware device
- Credential secrets are derived from hardware-protected storage
- Counter-based replay prevention

### ZK Privacy
- Identity commitments are one-way hashes
- Nullifiers prevent double-use without revealing identity
- Merkle proofs reveal nothing about group position

### Delegation Safety
- Spending limits prevent excessive agent actions
- Action-type restrictions limit scope
- Expiration enforces time-bounded access
- Hardware-verified creation prevents unauthorized delegation

---

## Integration Example

### License Purchase with Hardware Auth

```python
from rra.auth import WebAuthnClient, HardwareIdentity
from rra.transaction import TransactionConfirmation

# 1. Authenticate with hardware key
client = WebAuthnClient(rp_id="natlangchain.io")
assertion = await client.authenticate(challenge)

# 2. Create pending transaction with two-step verification
confirmation = TransactionConfirmation()
pending = confirmation.create_pending_transaction(
    buyer_id=wallet_address,
    seller_id=repo_owner,
    repo_url="https://github.com/example/repo",
    license_model="perpetual",
    agreed_price="0.5 ETH",
    floor_price="0.3 ETH",
    target_price="0.6 ETH",
)

# 3. User confirms with hardware key
result = confirmation.confirm_transaction(
    pending.transaction_id,
    hardware_signature=assertion.signature
)

# 4. Execute on-chain with FIDO2 verification
tx = await ilrm.execute_purchase(
    auth_mode=AuthMode.DirectFIDO2,
    credential_id=credential.id,
    assertion=assertion
)
```

---

## Testing

All hardware authentication components have comprehensive test coverage:

```bash
# Run hardware auth tests (21 tests)
PYTHONPATH=./src pytest tests/test_hardware_auth.py -v

# Expected output:
# 21 passed
```

### Test Categories
- WebAuthn client registration and authentication
- P-256 signature verification
- Identity commitment generation
- Delegation creation and validation
- ZK proof generation and verification

---

## Related Documentation

- **[Transaction Security](TRANSACTION-SECURITY.md)** - Two-step verification integration
- **[Dispute Membership Circuit](Dispute-Membership-Circuit.md)** - ZK identity proofs for disputes
- **[Security Audit](SECURITY-AUDIT.md)** - Security review and recommendations
- **[SPECIFICATION.md](../SPECIFICATION.md)** - Phase 5 implementation status

---

## License

Copyright 2025 Kase Branham. Licensed under FSL-1.1-ALv2.
