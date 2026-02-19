# Security Remediation Plan — RRA-Module

## Overview

Fix all 60 findings from `SECURITY-AUDIT-2026-02-19.md` across 4 phases, organized by priority. Each step identifies the exact file, line range, and code change.

---

## Phase 1: Critical & High Severity (Deploy Blockers)

### Step 1: Harden Authentication Defaults

**Files:** `docker-compose.yml`, `src/rra/api/auth.py`, `src/rra/security/api_auth.py`

1. **`docker-compose.yml:29-30`** — Change dev mode default and remove hardcoded API key:
   - `RRA_DEV_MODE=${RRA_DEV_MODE:-true}` → `RRA_DEV_MODE=${RRA_DEV_MODE:-false}`
   - `RRA_API_KEY=${RRA_API_KEY:-dev-api-key}` → `RRA_API_KEY=${RRA_API_KEY:?RRA_API_KEY must be set}`
   - Fixes CRITICAL-01 and HIGH-01

2. **`src/rra/api/auth.py:80-92`** — Remove dev mode bypass from production code. Replace the dev mode fallback block with a startup validation that logs a critical warning and refuses to start in production without keys:
   ```python
   if not api_keys_env:
       raise HTTPException(
           status_code=500,
           detail="Server configuration error: No API keys configured. "
                  "Set RRA_API_KEYS or RRA_API_KEY environment variable.",
       )
   ```
   - Fixes CRITICAL-01

3. **`src/rra/api/auth.py:119-135`** — Fix `optional_api_key` to reject invalid keys instead of downgrading:
   ```python
   def optional_api_key(api_key: str = Security(API_KEY_HEADER)) -> Optional[bool]:
       if api_key is None:
           return None
       # Key was provided but invalid — reject it
       return verify_api_key(api_key)
   ```
   Remove the `try/except` that swallows `HTTPException`. Invalid keys should get 401, not silent downgrade.
   - Fixes MEDIUM-14

4. **`src/rra/security/api_auth.py:30`** — Default auth enabled to `true`:
   ```python
   AUTH_ENABLED = os.environ.get("RRA_AUTH_ENABLED", "true").lower() == "true"
   ```
   - Fixes CRITICAL-02

5. **`src/rra/security/api_auth.py:205`** — Fix timing attack on admin key:
   ```python
   import hmac
   if ADMIN_API_KEY and hmac.compare_digest(api_key, ADMIN_API_KEY):
   ```
   - Fixes HIGH-04

### Step 2: Add Authentication to Unprotected Endpoints

**Files:** `src/rra/api/entropy.py`, `src/rra/api/warnings.py`, `src/rra/api/webhooks.py`

1. **`src/rra/api/entropy.py`** — Import and add auth dependency to all state-modifying endpoints:
   - Add `from rra.api.auth import verify_api_key` import
   - Add `Depends(verify_api_key)` to: `record_dispute`, `batch_score_clauses`, `score_clause`, `score_contract`, `predict_disputes`, `analyze_pattern`
   - Keep `/entropy/health`, `/entropy/categories` unauthenticated (read-only reference data)
   - Fixes HIGH-02 (partial)

2. **`src/rra/api/warnings.py`** — Same pattern:
   - Add auth dependency to: `generate_warnings`, `analyze_terms`, `analyze_single_term`, `find_high_entropy_terms`, `acknowledge_warning`, `resolve_warning`, `batch_analyze_contracts`
   - Keep `/warnings/health`, `/warnings/categories`, `/warnings/alternatives/{term}` unauthenticated
   - Fixes HIGH-02 (partial)

3. **`src/rra/api/webhooks.py:633-636`** — Add auth to credential generation:
   ```python
   async def generate_credentials(
       request: WebhookCredentialsRequest,
       _: bool = Depends(verify_api_key),
   ) -> WebhookCredentialsResponse:
   ```
   - Fixes HIGH-03

### Step 3: Fix GitHub Webhook Verification Bypass

**File:** `src/rra/integrations/github_webhooks.py:107-108`

Change the bypass to reject by default:
```python
if not self.secret:
    logger.warning("GitHub webhook secret not configured — rejecting request")
    return False
```
- Fixes HIGH-05

### Step 4: Fix Smart Contract Access Control — ILRM.sol

**File:** `contracts/src/ILRM.sol`

1. **Lines 361-375** — `submitSettlement`: Add caller authorization requiring the caller to be one of the dispute parties' claim addresses:
   ```solidity
   function submitSettlement(
       uint256 _disputeId,
       uint8 _initiatorShare
   ) external nonReentrant whenNotPaused {
       Dispute storage d = disputes[_disputeId];
       require(d.phase == DisputePhase.Negotiation || d.phase == DisputePhase.Mediation, "Invalid phase");
       require(d.initiatorVerified && d.counterpartyVerified, "Both parties must verify identity");
       require(_initiatorShare <= 100, "Invalid share");
       // NEW: Require caller is a verified party
       require(
           msg.sender == claimAddresses[d.initiatorHash] ||
           msg.sender == claimAddresses[d.counterpartyHash],
           "Not a party to this dispute"
       );
       ...
   ```
   - Fixes CRITICAL-03

2. **Lines 384-387** — `registerMediator`: Add `onlyOwner` modifier:
   ```solidity
   function registerMediator(address _mediator) external onlyOwner {
       registeredMediators[_mediator] = true;
       mediatorReputation[_mediator] = 100;
       emit MediatorRegistered(_mediator);
   }
   ```
   - Add `event MediatorRegistered(address indexed mediator);` to the events section
   - Fixes HIGH-06

### Step 5: Fix Smart Contract Access Control — ComplianceEscrow.sol

**File:** `contracts/src/ComplianceEscrow.sol`

1. **Lines 155-160** — `createEscrow`: Add role restriction:
   ```solidity
   function createEscrow(
       uint256 _disputeId,
       bytes32 _keyCommitment,
       uint8 _threshold,
       uint8 _totalShares
   ) external onlyRole(COMPLIANCE_COUNCIL_ROLE) whenNotPaused returns (uint256) {
   ```
   - Fixes HIGH-07

2. **Line 161** — Fix threshold validation:
   ```solidity
   require(_threshold >= 2 && _threshold <= _totalShares, "Invalid threshold: minimum 2");
   ```
   - Fixes MEDIUM-21

### Step 6: Fix TreasuryCoordinator.sol Critical Bugs

**File:** `contracts/src/TreasuryCoordinator.sol`

1. **Mixed ETH/ERC20 accounting (lines 453-488)**: Refactor to track per-token escrow. Add mappings:
   ```solidity
   // Per-token escrow tracking
   mapping(uint256 => uint256) public disputeEthEscrow;  // disputeId => ETH amount
   mapping(uint256 => mapping(address => uint256)) public disputeTokenEscrow;  // disputeId => token => amount
   ```
   Update `escrowFunds()` to increment `disputeEthEscrow[_disputeId]` and `escrowTokens()` to increment `disputeTokenEscrow[_disputeId][_token]`. Update `participant` struct to track per-token amounts. Update `executeResolution()` to distribute ETH and ERC20 separately.
   - Fixes HIGH-08, HIGH-10

2. **`transfer()` → `call()` (lines 642, 686, 742)**: Replace all three:
   ```solidity
   // Line 642 (requestMediation):
   (bool success, ) = payable(feeRecipient).call{value: mediationFee}("");
   require(success, "Fee transfer failed");
   if (msg.value > mediationFee) {
       (bool refundSuccess, ) = payable(msg.sender).call{value: msg.value - mediationFee}("");
       require(refundSuccess, "Refund failed");
   }

   // Line 686 (executeResolution):
   (bool success, ) = payable(payoutAddress).call{value: payout}("");
   require(success, "Payout failed");

   // Line 742 (_returnStakes):
   (bool success, ) = payable(payoutAddress).call{value: stakeToReturn}("");
   require(success, "Stake return failed");
   ```
   - Add `nonReentrant` to `requestMediation`
   - Fixes HIGH-09, MEDIUM-T7, LOW-T6

3. **Single signer treasury takeover (lines 291-316)**: Require threshold approval. Add a two-step proposal/execute pattern:
   ```solidity
   mapping(bytes32 => SignerUpdateProposal) public signerUpdateProposals;

   function proposeSignerUpdate(bytes32 _treasuryId, address[] calldata _newSigners, uint256 _newThreshold) external {
       // Store proposal, require threshold approvals before execution
   }
   ```
   - Fixes MEDIUM-22

4. **Expired dispute stake recovery (lines 596-621)**: Add a stake withdrawal function:
   ```solidity
   function returnStakesForExpired(uint256 _disputeId) external nonReentrant {
       Dispute storage dispute = disputes[_disputeId];
       require(
           dispute.status == DisputeStatus.Expired ||
           dispute.status == DisputeStatus.Cancelled,
           "Not expired or cancelled"
       );
       _returnStakes(_disputeId);
   }
   ```
   - Fixes MEDIUM-23

---

## Phase 2: Medium Severity — Agent Safety & Auth Hardening

### Step 7: Fix NLP Callback Trust Boundary

**File:** `src/rra/agents/intent_parser.py`

1. **Lines 428-434** — Validate NLP callback responses against a strict schema. Add a consensus check requiring both pattern matching and NLP callback to agree before triggering financial actions:
   ```python
   def _classify_with_nlp(self, message: str) -> Optional[str]:
       if not self.nlp_callback:
           return None
       result = self.nlp_callback(message)
       # Validate against allowed intents and confidence threshold
       if not isinstance(result, dict) or "intent" not in result:
           logger.warning("Invalid NLP callback response format")
           return None
       if result.get("confidence", 0) < 0.8:
           return None
       if result["intent"] not in self.VALID_INTENTS:
           return None
       return result["intent"]
   ```
   - Fixes MEDIUM-03

2. **Lines 620-637** — Restrict `add_pattern()` to initialization. Add a `_locked` flag set after first `respond()` call:
   ```python
   def add_pattern(self, intent: str, pattern: str, ...):
       if self._locked:
           raise RuntimeError("Cannot add patterns after initialization")
       ...
   ```
   - Fixes MEDIUM-05

### Step 8: Add Agent State Integrity Verification

**File:** `src/rra/integration/memory.py`

1. **Lines 42-51** — `save_state()`: Add HMAC-SHA256 signature:
   ```python
   import hmac, hashlib, os

   def save_state(self, state: Dict[str, Any]) -> None:
       state_with_metadata = {
           "agent_id": self.agent_id,
           "timestamp": datetime.now().isoformat(),
           "state": state,
       }
       payload = json.dumps(state_with_metadata, sort_keys=True).encode()
       mac = hmac.new(self._get_mac_key(), payload, hashlib.sha256).hexdigest()
       with open(self.state_file, "w") as f:
           json.dump({"data": state_with_metadata, "mac": mac}, f, indent=2)
   ```

2. **Lines 53-61** — `load_state()`: Verify HMAC before loading:
   ```python
   def load_state(self) -> Dict[str, Any]:
       if not self.state_file.exists():
           return {}
       with open(self.state_file, "r") as f:
           wrapper = json.load(f)
       payload = json.dumps(wrapper["data"], sort_keys=True).encode()
       expected_mac = hmac.new(self._get_mac_key(), payload, hashlib.sha256).hexdigest()
       if not hmac.compare_digest(wrapper.get("mac", ""), expected_mac):
           logger.critical(f"State file integrity check failed for {self.agent_id}")
           raise ValueError("Agent state integrity verification failed")
       return wrapper["data"].get("state", {})
   ```

3. **Line 40** — Sanitize `agent_id`:
   ```python
   import re
   if not re.match(r'^[a-zA-Z0-9_-]+$', agent_id):
       raise ValueError(f"Invalid agent_id: {agent_id}")
   ```
   - Fixes MEDIUM-06, LOW-03

### Step 9: Fix Webhook Credential Storage

**File:** `src/rra/security/webhook_auth.py`

1. **Lines 421-425** — `_save_credentials()`: Integrate existing `CredentialEncryption` class:
   ```python
   def _save_credentials(self) -> None:
       self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
       encryptor = CredentialEncryption()
       encrypted_creds = {}
       for agent_id, cred in self._credentials.items():
           encrypted_creds[agent_id] = {
               **cred,
               "secret_key": encryptor.encrypt(cred["secret_key"]),
           }
       with open(self.credentials_path, "w") as f:
           json.dump(encrypted_creds, f, indent=2, default=str)
       os.chmod(self.credentials_path, 0o600)
   ```
   - Update `_load_credentials()` to decrypt on load
   - Fixes MEDIUM-09, LOW-11

### Step 10: Sanitize Error Messages Across All API Modules

**Files:** `src/rra/api/verification_api.py`, `src/rra/api/websocket.py`, `src/rra/api/webhooks.py`, `src/rra/integrations/github_webhooks.py`

1. Import `sanitize_error_message` from `src/rra/api/server.py` (or extract to a shared utility)
2. Replace all `str(e)` in client-facing responses:
   - `verification_api.py:238-240` → `sanitize_error_message(str(e))`
   - `websocket.py:409` → `sanitize_error_message(str(e))`
   - `webhooks.py:352` → `sanitize_error_message(str(e))`
   - `github_webhooks.py:330` → `sanitize_error_message(str(e))`
   - Fixes MEDIUM-08

### Step 11: Fix Replay Protection & Rate Limiting

**Files:** `src/rra/api/webhooks.py`, `src/rra/api/rate_limiter.py`

1. **`webhooks.py:417-423`** — Enforce timestamp validation when webhook credentials are present (not just when the header is sent):
   ```python
   if agent_creds:  # credentials exist for this agent
       if not timestamp:
           raise HTTPException(400, "X-Request-Timestamp required for authenticated webhooks")
   ```
   - Fixes MEDIUM-13

2. **`rate_limiter.py:316-319`** — Only trust X-Forwarded-For from configured proxy IPs:
   ```python
   TRUSTED_PROXIES = set(os.environ.get("RRA_TRUSTED_PROXIES", "").split(","))

   forwarded = request.headers.get("X-Forwarded-For", "")
   if forwarded and request.client and request.client.host in TRUSTED_PROXIES:
       client_ip = forwarded.split(",")[0].strip()
   ```
   - Fixes MEDIUM-15

### Step 12: Fix SSRF in DID:web Resolver

**File:** `src/rra/identity/did_resolver.py:345`

Before making the HTTP request, validate the resolved hostname against blocked networks (reuse the SSRF validation from `webhook_auth.py`):
```python
from rra.security.webhook_auth import validate_callback_url

async def resolve(self, did: str) -> Optional[DIDDocument]:
    url = self._did_to_url(did)
    # SSRF protection
    try:
        validate_callback_url(url)
    except ValueError as e:
        logger.warning(f"DID:web resolution blocked by SSRF protection: {e}")
        return None
    ...
```
- Fixes MEDIUM-18

### Step 13: Fix Widget Origin Wildcard

**File:** `src/rra/api/widget.py:35`

```python
ALLOWED_WIDGET_ORIGINS = set(
    os.environ.get("RRA_WIDGET_ORIGINS", "").split(",")
) - {""}
if not ALLOWED_WIDGET_ORIGINS:
    ALLOWED_WIDGET_ORIGINS = {"self"}  # Restrict to same-origin by default
```
- Fixes MEDIUM-02

### Step 14: Fix WebSocket API Key in URL

**File:** `src/rra/api/websocket.py`

Add a token exchange endpoint. Client authenticates via HTTP POST to get a short-lived WebSocket token, then uses that token (not the API key) in the WebSocket URL query parameter. Add:
```python
@router.post("/ws/token")
async def get_ws_token(_: bool = Depends(verify_api_key)) -> Dict[str, str]:
    token = secrets.token_urlsafe(32)
    _ws_tokens[token] = {"created": datetime.utcnow(), "ttl": 60}
    return {"token": token}
```
Then modify the WebSocket endpoint to accept `token` instead of `api_key`.
- Fixes MEDIUM-16

### Step 15: Fix API Key Hashing

**File:** `src/rra/security/api_auth.py:60-62`

Replace unsalted SHA-256 with bcrypt:
```python
import bcrypt

def _hash_key(self, key: str) -> str:
    return bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode()

def validate_key(self, key: str) -> Optional[Dict[str, Any]]:
    for key_hash, key_data in self._keys.items():
        if bcrypt.checkpw(key.encode(), key_hash.encode()):
            ...
```
- Fixes MEDIUM-17

### Step 16: Fix Boundary Daemon Default for Financial Transactions

**File:** `src/rra/integration/boundary_daemon.py:357-389`

For OPEN, RESTRICTED, and TRUSTED modes, set `require_human_approval=True` when `blockchain_write_allowed=True`:
```python
BoundaryMode.OPEN: cls(
    ...
    require_human_approval=True,  # Changed: require approval for financial ops
),
BoundaryMode.RESTRICTED: cls(
    ...
    require_human_approval=True,  # Changed
),
```
- Fixes MEDIUM-19

### Step 17: Fix Transaction Safeguards

**File:** `src/rra/transaction/safeguards.py`

1. **Lines 178-190** — Force elevated safeguard level when using fallback rates:
   ```python
   if currency in fallback_rates:
       logger.warning(...)
       return fallback_rates[currency], "fallback (hardcoded, ELEVATED_SAFEGUARD)"
   ```
   In `validate_price()`, check for "fallback" in source and force safeguard to at minimum MEDIUM.
   - Fixes MEDIUM-28

2. **Lines 319-346** — Make rate limiting per-buyer:
   ```python
   self.transaction_timestamps: Dict[str, List[datetime]] = {}

   def check_rate_limit(self, buyer_id: str) -> Tuple[bool, str]:
       ...
       buyer_timestamps = self.transaction_timestamps.setdefault(buyer_id, [])
       buyer_timestamps[:] = [ts for ts in buyer_timestamps if ts > hour_ago]
       if len(buyer_timestamps) >= self.MAX_TRANSACTIONS_PER_HOUR:
           ...
   ```
   - Fixes MEDIUM-29

### Step 18: Fix Anvil Key in Documentation

**File:** `contracts/README.md:38`

Truncate the full private key to `0xac0974...f2ff80` with a note: "See Foundry/Anvil docs for default test accounts."
- Fixes MEDIUM-01

### Step 19: Fix RepoLicense.sol

**File:** `contracts/src/RepoLicense.sol`

1. **Lines 199-203** — Reorder: transfer ETH before minting to prevent callback issues:
   ```solidity
   // 5. Transfer payment to developer FIRST
   (bool success, ) = developer.call{value: msg.value}("");
   require(success, "Payment transfer failed");

   // 6. Then mint token
   _safeMint(_licensee, tokenId);
   _setTokenURI(tokenId, _tokenURI);
   ```
   - Fixes MEDIUM-20

2. **Lines 322-334** — Add price validation to `updateRepository`:
   ```solidity
   require(_newTargetPrice >= _newFloorPrice, "Target must be >= floor");
   ```
   - Fixes LOW-08

---

## Phase 3: Medium Severity — Crypto & Remaining

### Step 20: Fix Pedersen Constant-Time Scalar Multiplication

**File:** `src/rra/crypto/pedersen.py:331-337`

Replace the branching double-and-add with Montgomery ladder:
```python
def _scalar_mult_projective(k: int, point: Tuple) -> Tuple:
    if k == 0 or point == (0, 0):
        return (0, 0)
    k = k % BN254_CURVE_ORDER
    proj_point = _affine_to_projective(point)
    R0 = (0, 1, 0)  # identity
    R1 = proj_point
    for i in range(k.bit_length() - 1, -1, -1):
        if (k >> i) & 1:
            R0 = _projective_add(R0, R1)
            R1 = _projective_double(R1)
        else:
            R1 = _projective_add(R0, R1)
            R0 = _projective_double(R0)
    return _projective_to_affine(R0)
```
- Fixes MEDIUM-24

### Step 21: Fix Shamir PRNG and Prime Validation

**Files:** `src/rra/crypto/shamir.py`, `src/rra/privacy/secret_sharing.py`

1. **`shamir.py:63-64`** — Use cryptographic PRNG:
   ```python
   import secrets
   a = secrets.randbelow(n - 3) + 2
   ```
   - Fixes MEDIUM-25 (labeled LOW)

2. **`shamir.py:231`** — Validate custom primes:
   ```python
   def __init__(self, prime: int = PRIME):
       if prime != PRIME and not _is_probable_prime(prime):
           raise ValueError("Custom prime failed primality test")
       self.prime = prime
   ```
   - Fixes MEDIUM-26

3. **`privacy/secret_sharing.py:26`** — Add primality verification at module load:
   ```python
   from rra.crypto.shamir import _is_probable_prime
   if not _is_probable_prime(PRIME):
       raise ValueError("PRIME constant failed primality check")
   ```
   - Fixes MEDIUM-27

### Step 22: Fix Callback Data Exfiltration

**File:** `src/rra/api/webhooks.py:356-383`

Limit callback payload to status information only:
```python
callback_payload = {
    "session_id": session_id,
    "phase": agent.current_phase.value,
    "status": "response_ready",
    # Do NOT include full response content
}
```
- Fixes MEDIUM-07

### Step 23: Fix Agent State Namespace Isolation

**Files:** `src/rra/api/webhooks.py:126-127`, `src/rra/storage/session_store.py:482-497`

1. **`webhooks.py:126-127`** — Add session bounds and TTL:
   ```python
   MAX_SESSIONS = int(os.environ.get("RRA_MAX_SESSIONS", "1000"))
   SESSION_TTL_HOURS = 24

   # In session creation:
   if len(_webhook_sessions) >= MAX_SESSIONS:
       # Evict oldest expired session
       ...
   ```
   - Fixes MEDIUM-11, LOW-06

2. **`session_store.py:482-497`** — Fix thread-safe singleton:
   ```python
   import threading
   _session_store_lock = threading.Lock()

   def get_session_store():
       global _session_store
       if _session_store is None:
           with _session_store_lock:
               if _session_store is None:
                   _session_store = SessionStore()
       return _session_store
   ```
   - Fixes LOW-16

---

## Phase 4: Low Severity & Informational

### Step 24: Fix Path Traversal in Identity Storage

**File:** `src/rra/privacy/identity.py:546,571`

```python
import re
if not re.match(r'^[a-zA-Z0-9_-]+$', name):
    raise ValueError(f"Invalid identity name: {name}")
file_path = self.storage_path / f"{name}.identity"
if not file_path.resolve().is_relative_to(self.storage_path.resolve()):
    raise ValueError("Path traversal detected")
```
- Fixes LOW-10

### Step 25: Fix Environment Config Files

Rename tracked config templates:
```bash
mv config/environments/.env.development config/environments/.env.development.example
mv config/environments/.env.staging config/environments/.env.staging.example
mv config/environments/.env.production config/environments/.env.production.example
```
Add to `.gitignore`:
```
config/environments/.env.development
config/environments/.env.staging
config/environments/.env.production
```
- Fixes LOW-02

### Step 26: Fix DNS Rebinding in SSRF Protection

**File:** `src/rra/security/webhook_auth.py:84-94`

Pin the resolved IP and pass to HTTP client:
```python
resolved_ip = socket.getaddrinfo(hostname, None)[0][4][0]
# Use resolved_ip in the actual HTTP request
async with httpx.AsyncClient() as client:
    response = await client.post(
        url, json=payload,
        extensions={"sni_hostname": hostname},
        transport=httpx.AsyncHTTPTransport(local_address=resolved_ip)
    )
```
- Fixes LOW-04

### Step 27: Fix IPFS CID Validation

**File:** `src/rra/storage/encrypted_ipfs.py:587,596`

```python
import re
CID_PATTERN = re.compile(r'^(Qm[1-9A-HJ-NP-Za-km-z]{44}|bafy[a-z2-7]{55})$')

def _validate_cid(cid: str) -> str:
    if not CID_PATTERN.match(cid):
        raise ValueError(f"Invalid IPFS CID format: {cid}")
    return cid
```
- Fixes LOW-05

### Step 28: Fix Root Endpoint Information Leakage

**File:** `src/rra/api/server.py:368-434`

Restrict endpoint listing to public endpoints or require authentication:
```python
@app.get("/")
async def root(auth: Optional[bool] = Depends(optional_api_key)):
    if auth:
        return full_endpoint_listing  # Authenticated: show all
    return {"status": "ok", "version": "1.0.1-beta"}  # Public: minimal
```
- Fixes LOW-07

### Step 29: Fix CSP frame-ancestors Wildcard

**File:** `src/rra/api/server.py:335`

```python
allowed_origins = os.environ.get("RRA_WIDGET_ORIGINS", "'self'")
csp_header = f"frame-ancestors 'self' {allowed_origins}"
```
- Fixes LOW-12

### Step 30: Fix Floating-Point Financial Calculations

**File:** `src/rra/transaction/safeguards.py:436,456`

Replace `float` with `Decimal`:
```python
from decimal import Decimal
amount = Decimal(str(amount_str))
usd_value = amount * Decimal(str(rate))
```
- Fixes LOW-13

### Step 31: Fix Transaction ID Truncation

**File:** `src/rra/transaction/confirmation.py:383-386`

Use 128 bits (32 hex chars) instead of 64 bits (16 hex chars):
```python
tx_id = keccak(...).hex()[:32]  # 128-bit collision resistance
```
- Fixes LOW-14

### Step 32: Fix Unbounded Memory Growth

**Files:** `src/rra/transaction/confirmation.py:303-304`, `src/rra/crypto/pedersen.py:357`

1. **`confirmation.py`** — Add periodic pruning. Use `collections.deque` with maxlen for audit log:
   ```python
   from collections import deque
   self.audit_log: deque = deque(maxlen=10000)
   # Prune completed_transactions older than 24h
   ```
   - Fixes LOW-15

2. **`pedersen.py:357`** — Bound precomputed table cache to generator points only:
   ```python
   _MAX_PRECOMPUTED_TABLES = 4  # Only G_POINT, H_POINT + 2 spare
   if len(_precomputed_tables) >= _MAX_PRECOMPUTED_TABLES:
       return _scalar_mult_projective(k, point)  # Fallback to non-cached
   ```
   - Fixes LOW-17

### Step 33: Fix Thread Pool Lazy Init

**File:** `src/rra/crypto/pedersen.py:570-587`

Initialize lock at module level:
```python
_thread_pool_lock = threading.Lock()  # Initialize immediately, not lazily
_thread_pool = None
```
- Fixes LOW-18

### Step 34: Fix Pedersen Test Vectors

**File:** `src/rra/crypto/pedersen.py:93-112`

Add expected output coordinates to test vectors and validate during `_verify_test_vectors_on_load()`:
```python
PEDERSEN_TEST_VECTORS = [
    {
        "value": 42,
        "blinding_hex": "...",
        "expected_x": "0x...",
        "expected_y": "0x...",
    },
    ...
]
```
- Fixes LOW-09

### Step 35: Run Tests and Verify

After all changes:
```bash
pytest tests/ -v
cd contracts && forge test
```

Verify no regressions in:
- `test_security.py`
- `test_crypto.py`
- `test_crypto_security_integration.py`
- `test_secrets.py`
- `test_verification.py`
- All contract tests

---

## Summary

| Phase | Steps | Findings Fixed | Files Modified |
|-------|-------|----------------|----------------|
| 1: Critical+High | Steps 1-6 | 11 findings (3C, 8H) | 10 files |
| 2: Medium (Agent/Auth) | Steps 7-19 | 19 findings | 15 files |
| 3: Medium (Crypto) | Steps 20-23 | 7 findings | 5 files |
| 4: Low+Info | Steps 24-35 | 18 findings | 12 files |
| **Total** | **35 steps** | **55 actionable findings** | **~30 files** |

5 informational findings require no code changes (deprecated API notices, missing events that are documentation-only).
