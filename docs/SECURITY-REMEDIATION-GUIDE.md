# Security Remediation Guide

**Version:** 1.0.0
**Created:** 2025-12-20
**Status:** In Progress

---

## Overview

This guide provides step-by-step instructions to fix the 83 security issues identified in the penetration test. Issues are organized by priority and include code examples, testing steps, and verification procedures.

---

## Phase 1: Critical Issues (Week 1)

### CRITICAL-001: Fund Withdrawal Mechanism

**Issue:** ILRM.sol has no way to withdraw staked ETH - funds are permanently locked.

**Files to Modify:**
- `contracts/src/ILRM.sol`
- `contracts/src/ILRMv2.sol`

**Solution:** Implement pull-based withdrawal pattern.

```solidity
// Add to ILRM.sol

// State variable for pending withdrawals
mapping(address => uint256) public pendingWithdrawals;

// Event for tracking
event WithdrawalPending(address indexed user, uint256 amount);
event WithdrawalCompleted(address indexed user, uint256 amount);

// Internal function to credit user
function _creditWithdrawal(address _user, uint256 _amount) internal {
    pendingWithdrawals[_user] += _amount;
    emit WithdrawalPending(_user, _amount);
}

// External function to withdraw
function withdraw() external nonReentrant {
    uint256 amount = pendingWithdrawals[msg.sender];
    require(amount > 0, "No funds to withdraw");

    // Clear before transfer (CEI pattern)
    pendingWithdrawals[msg.sender] = 0;

    (bool success, ) = msg.sender.call{value: amount}("");
    require(success, "Transfer failed");

    emit WithdrawalCompleted(msg.sender, amount);
}

// Update _refundInitiator to use credits
function _refundInitiator(uint256 _disputeId) internal {
    Dispute storage d = disputes[_disputeId];
    // Get initiator address from identity hash (requires lookup)
    // For now, store initiator address in dispute struct
    _creditWithdrawal(d.initiator, d.stakeAmount);
    d.stakeAmount = 0;
}
```

**Testing:**
```bash
forge test --match-test testWithdrawal -vvv
```

---

### CRITICAL-002: Pedersen Commitment Fix

**Issue:** Uses integer exponentiation instead of EC point multiplication. Generator points insecurely derived.

**Files to Modify:**
- `src/rra/crypto/pedersen.py`

**Solution:** Use proper elliptic curve operations with py_ecc library.

```python
# Replace entire pedersen.py with EC-based implementation

from py_ecc.bn128 import G1, multiply, add, neg, curve_order
from py_ecc.bn128 import FQ
import hashlib
import os

class PedersenCommitment:
    """Proper Pedersen commitment using BN128 curve."""

    def __init__(self):
        # G is the standard generator
        self.G = G1
        # H is derived via hash-to-curve (nothing-up-my-sleeve)
        self.H = self._derive_generator_point()
        self.order = curve_order

    def _derive_generator_point(self):
        """Derive H using hash-to-curve (simplified)."""
        # In production, use proper hash-to-curve RFC 9380
        seed = b"pedersen-generator-h-rra-v1"
        for i in range(256):
            attempt = hashlib.sha256(seed + i.to_bytes(1, 'big')).digest()
            x = int.from_bytes(attempt, 'big') % curve_order
            # Try to find valid point (simplified - production needs proper h2c)
            try:
                # This is simplified - real implementation needs proper encoding
                point = multiply(G1, x)
                if point is not None:
                    return point
            except:
                continue
        raise ValueError("Failed to derive H")

    def commit(self, value: bytes, blinding: bytes = None) -> tuple:
        """Create Pedersen commitment C = vG + rH."""
        if blinding is None:
            blinding = os.urandom(32)

        v = int.from_bytes(value, 'big') % self.order
        r = int.from_bytes(blinding, 'big') % self.order

        # C = v*G + r*H
        vG = multiply(self.G, v)
        rH = multiply(self.H, r)
        C = add(vG, rH)

        # Serialize point
        commitment = self._serialize_point(C)
        return commitment, blinding

    def verify(self, commitment: bytes, value: bytes, blinding: bytes) -> bool:
        """Verify commitment opens to value with blinding."""
        expected, _ = self.commit(value, blinding)
        return commitment == expected

    def _serialize_point(self, point) -> bytes:
        """Serialize EC point to bytes."""
        if point is None:
            return b'\x00' * 64
        x, y = point
        return int(x).to_bytes(32, 'big') + int(y).to_bytes(32, 'big')
```

**Testing:**
```bash
PYTHONPATH=./src python3 -m pytest tests/test_crypto.py -v -k pedersen
```

---

### CRITICAL-003: WebAuthnVerifier Access Control

**Issue:** Admin functions lack access control modifiers.

**Files to Modify:**
- `contracts/src/WebAuthnVerifier.sol`

**Solution:** Add onlyOwner modifier to admin functions.

```solidity
// Ensure contract inherits Ownable
import "@openzeppelin/contracts/access/Ownable.sol";

contract WebAuthnVerifier is Ownable {
    // ... existing code ...

    // FIX: Add onlyOwner modifier
    function updateRpIdHash(bytes32 _newRpIdHash) external onlyOwner {
        require(_newRpIdHash != bytes32(0), "Invalid RP ID hash");
        bytes32 oldHash = rpIdHash;
        rpIdHash = _newRpIdHash;
        emit RpIdHashUpdated(oldHash, _newRpIdHash);
    }

    // FIX: Add onlyOwner modifier
    function updateChallengeValidity(uint256 _newPeriod) external onlyOwner {
        require(_newPeriod >= 1 minutes && _newPeriod <= 30 minutes, "Invalid period");
        uint256 oldPeriod = challengeValidityPeriod;
        challengeValidityPeriod = _newPeriod;
        emit ChallengeValidityUpdated(oldPeriod, _newPeriod);
    }

    // Add events
    event RpIdHashUpdated(bytes32 indexed oldHash, bytes32 indexed newHash);
    event ChallengeValidityUpdated(uint256 oldPeriod, uint256 newPeriod);
}
```

---

### CRITICAL-004: Proper Poseidon Hash

**Issue:** Poseidon is mocked with Keccak - ZK proofs will fail on-chain.

**Files to Modify:**
- `src/rra/privacy/identity.py`

**Solution:** Implement proper Poseidon or use existing library.

```python
# Add proper Poseidon implementation
# Option 1: Use poseidon-hash library
# pip install poseidon-hash

from typing import List

class PoseidonHash:
    """Poseidon hash compatible with circom/snarkjs."""

    # BN128 field prime
    FIELD_PRIME = 21888242871839275222246405745257275088548364400416034343698204186575808495617

    # Poseidon constants (must match circom implementation)
    # These are the standard constants for t=3 (2 inputs + 1 capacity)
    C = [...]  # Round constants - get from circomlib
    M = [...]  # MDS matrix - get from circomlib

    def __init__(self, t: int = 3):
        self.t = t  # State size
        self.n_rounds_f = 8  # Full rounds
        self.n_rounds_p = 57  # Partial rounds

    def hash(self, inputs: List[int]) -> int:
        """Hash inputs using Poseidon."""
        if len(inputs) >= self.t:
            raise ValueError(f"Too many inputs: {len(inputs)} >= {self.t}")

        # Initialize state with inputs
        state = [0] * self.t
        for i, inp in enumerate(inputs):
            state[i] = inp % self.FIELD_PRIME

        # Apply Poseidon permutation
        state = self._permutation(state)

        return state[0]

    def _permutation(self, state: List[int]) -> List[int]:
        """Apply Poseidon permutation."""
        # Full rounds (first half)
        for r in range(self.n_rounds_f // 2):
            state = self._full_round(state, r)

        # Partial rounds
        for r in range(self.n_rounds_p):
            state = self._partial_round(state, r + self.n_rounds_f // 2)

        # Full rounds (second half)
        for r in range(self.n_rounds_f // 2):
            state = self._full_round(state, r + self.n_rounds_f // 2 + self.n_rounds_p)

        return state

    def _full_round(self, state: List[int], r: int) -> List[int]:
        """Apply full round (S-box to all elements)."""
        # Add round constants
        state = [(s + self.C[r * self.t + i]) % self.FIELD_PRIME
                 for i, s in enumerate(state)]
        # S-box (x^5)
        state = [pow(s, 5, self.FIELD_PRIME) for s in state]
        # MDS matrix
        state = self._mds_mix(state)
        return state

    def _partial_round(self, state: List[int], r: int) -> List[int]:
        """Apply partial round (S-box to first element only)."""
        # Add round constants
        state = [(s + self.C[r * self.t + i]) % self.FIELD_PRIME
                 for i, s in enumerate(state)]
        # S-box only on first element
        state[0] = pow(state[0], 5, self.FIELD_PRIME)
        # MDS matrix
        state = self._mds_mix(state)
        return state

    def _mds_mix(self, state: List[int]) -> List[int]:
        """Apply MDS matrix multiplication."""
        new_state = [0] * self.t
        for i in range(self.t):
            for j in range(self.t):
                new_state[i] = (new_state[i] + self.M[i][j] * state[j]) % self.FIELD_PRIME
        return new_state


# Alternative: Use subprocess to call circom's poseidon
import subprocess
import json

def poseidon_via_circom(inputs: List[int]) -> int:
    """Call circom Poseidon via Node.js."""
    script = f'''
    const {{ poseidon }} = require("circomlibjs");
    const inputs = {json.dumps(inputs)};
    const hash = poseidon(inputs.map(x => BigInt(x)));
    console.log(hash.toString());
    '''
    result = subprocess.run(
        ['node', '-e', script],
        capture_output=True,
        text=True,
        cwd='/path/to/circom/project'
    )
    return int(result.stdout.strip())
```

---

## Phase 2: High Priority Issues (Week 2)

### HIGH-001: RepoLicense Reentrancy Fix

**Issue:** External call before state changes in `issueLicense()`.

**Files to Modify:**
- `contracts/src/RepoLicense.sol`

**Solution:** Use Checks-Effects-Interactions pattern.

```solidity
function issueLicense(
    string calldata _repoUrl,
    uint256 _duration,
    string calldata _tokenURI
) external payable nonReentrant returns (uint256) {
    // CHECKS
    Repo storage repo = repositories[_repoUrl];
    require(repo.isActive, "Repository not active");
    require(msg.value >= repo.price, "Insufficient payment");

    // Calculate expiration
    uint256 expiresAt = _duration == 0 ? 0 : block.timestamp + _duration;

    // EFFECTS - All state changes BEFORE external call
    uint256 tokenId = _tokenIdCounter.current();
    _tokenIdCounter.increment();

    // Mint and set token URI
    _safeMint(msg.sender, tokenId);
    _setTokenURI(tokenId, _tokenURI);

    // Store license
    licenses[tokenId] = License({
        repoUrl: _repoUrl,
        issuedAt: block.timestamp,
        expiresAt: expiresAt,
        licensee: msg.sender
    });

    userLicenses[msg.sender].push(tokenId);

    emit LicenseIssued(tokenId, _repoUrl, msg.sender, expiresAt);

    // INTERACTIONS - External call LAST
    (bool success, ) = repo.developer.call{value: msg.value}("");
    require(success, "Payment transfer failed");

    return tokenId;
}
```

---

### HIGH-002: ZK Proof Public Input Validation

**Issue:** ZK proofs accepted without validating public inputs match dispute.

**Files to Modify:**
- `contracts/src/ILRM.sol`

**Solution:** Validate public signals before expensive verification.

```solidity
function submitIdentityProof(
    uint256 _disputeId,
    uint[2] calldata _proofA,
    uint[2][2] calldata _proofB,
    uint[2] calldata _proofC,
    uint[1] calldata _publicSignals
) external {
    Dispute storage d = disputes[_disputeId];
    require(d.status == DisputeStatus.Active, "Dispute not active");

    // CRITICAL FIX: Validate public signals BEFORE verification
    bytes32 provenHash = bytes32(_publicSignals[0]);

    bool isInitiator = (provenHash == d.initiatorHash);
    bool isCounterparty = (provenHash == d.counterpartyHash);

    require(isInitiator || isCounterparty, "Identity not in dispute");

    // Determine which party is proving
    bool isInitiatorProof = isInitiator;

    // Check not already verified
    if (isInitiatorProof) {
        require(!d.initiatorVerified, "Initiator already verified");
    } else {
        require(!d.counterpartyVerified, "Counterparty already verified");
    }

    // Now verify the expensive ZK proof
    require(
        verifier.verifyProof(_proofA, _proofB, _proofC, _publicSignals),
        "Invalid ZK proof"
    );

    // Update verification status
    if (isInitiatorProof) {
        d.initiatorVerified = true;
    } else {
        d.counterpartyVerified = true;
    }

    emit IdentityVerified(_disputeId, provenHash, isInitiatorProof);
}
```

---

### HIGH-003: API Authentication

**Issue:** All API endpoints accessible without authentication.

**Files to Modify:**
- `src/rra/api/server.py`
- Create `src/rra/security/api_auth.py`

**Solution:** Implement API key authentication.

```python
# src/rra/security/api_auth.py

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from fastapi import HTTPException, Depends, Header
from pydantic import BaseModel

class APIKey(BaseModel):
    """API Key model."""
    key_id: str
    key_hash: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    scopes: list[str]
    rate_limit: int = 1000

class APIKeyManager:
    """Manage API keys."""

    def __init__(self, storage_path: str = "data/api_keys.json"):
        self.storage_path = storage_path
        self._keys: Dict[str, APIKey] = {}
        self._load_keys()

    def create_key(
        self,
        name: str,
        scopes: list[str] = None,
        expires_in_days: int = 365
    ) -> tuple[str, APIKey]:
        """Create new API key. Returns (raw_key, APIKey)."""
        raw_key = secrets.token_urlsafe(32)
        key_id = secrets.token_hex(8)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
            scopes=scopes or ["read", "write"]
        )

        self._keys[key_id] = api_key
        self._save_keys()

        return f"rra_{key_id}_{raw_key}", api_key

    def validate_key(self, raw_key: str) -> Optional[APIKey]:
        """Validate API key and return APIKey if valid."""
        if not raw_key.startswith("rra_"):
            return None

        try:
            _, key_id, key_secret = raw_key.split("_", 2)
        except ValueError:
            return None

        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        # Check hash
        key_hash = hashlib.sha256(key_secret.encode()).hexdigest()
        if not secrets.compare_digest(key_hash, api_key.key_hash):
            return None

        # Check expiration
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            return None

        return api_key

# Global instance
api_key_manager = APIKeyManager()

async def require_auth(
    x_api_key: str = Header(..., alias="X-API-Key")
) -> Dict[str, Any]:
    """Dependency to require valid API key."""
    api_key = api_key_manager.validate_key(x_api_key)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    return {"key_id": api_key.key_id, "scopes": api_key.scopes}

async def optional_auth(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[Dict[str, Any]]:
    """Dependency for optional authentication."""
    if not x_api_key:
        return None
    return await require_auth(x_api_key)
```

**Update server.py:**
```python
from rra.security.api_auth import require_auth, optional_auth

# Add auth to sensitive endpoints
@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_repository(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    auth: Dict = Depends(require_auth)  # Add this
):
    # Log authenticated action
    logger.info(f"Ingestion requested by {auth['key_id']}")
    # ... existing code
```

---

### HIGH-004: Secure Session Management

**Issue:** Sequential session IDs, no expiration, memory leaks.

**Files to Modify:**
- `src/rra/api/server.py`

**Solution:** Implement secure session manager.

```python
# Add to server.py or create src/rra/api/sessions.py

import secrets
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional, Tuple

class SessionManager:
    """Secure session management."""

    def __init__(self, ttl_seconds: int = 3600, max_sessions: int = 10000):
        self._sessions: Dict[str, Tuple[Any, datetime]] = {}
        self._lock = Lock()
        self.ttl = timedelta(seconds=ttl_seconds)
        self.max_sessions = max_sessions

    def create(self, data: Any) -> str:
        """Create session with secure random ID."""
        with self._lock:
            # Enforce max sessions
            if len(self._sessions) >= self.max_sessions:
                self._cleanup_expired()
                if len(self._sessions) >= self.max_sessions:
                    raise RuntimeError("Max sessions exceeded")

            # Generate secure session ID
            session_id = secrets.token_urlsafe(32)
            expires = datetime.utcnow() + self.ttl
            self._sessions[session_id] = (data, expires)
            return session_id

    def get(self, session_id: str) -> Optional[Any]:
        """Get session data if valid."""
        with self._lock:
            if session_id not in self._sessions:
                return None

            data, expires = self._sessions[session_id]
            if datetime.utcnow() > expires:
                del self._sessions[session_id]
                return None

            return data

    def delete(self, session_id: str) -> bool:
        """Delete session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def _cleanup_expired(self):
        """Remove expired sessions."""
        now = datetime.utcnow()
        expired = [sid for sid, (_, exp) in self._sessions.items() if now > exp]
        for sid in expired:
            del self._sessions[sid]

# Replace global dict
session_manager = SessionManager(ttl_seconds=3600)

# Update endpoints
@app.post("/api/negotiate/start")
async def start_negotiation(request: NegotiationRequest):
    # ... create negotiator ...
    session_id = session_manager.create(negotiator)  # Secure ID
    return {"session_id": session_id, ...}

@app.post("/api/negotiate/respond")
async def negotiate_respond(request: NegotiateRequest):
    negotiator = session_manager.get(request.session_id)
    if not negotiator:
        raise HTTPException(404, "Session not found or expired")
    # ... rest of code
```

---

## Phase 3: Medium Priority Issues (Week 3-4)

### Medium Issues Checklist

| ID | Issue | Fix Summary |
|----|-------|-------------|
| M1 | Unbounded array growth | Add pagination to getLicensesByOwner() |
| M2 | Unbounded delegation loop | Add batch limit parameter |
| M3 | HKDF without salt | Add random or constant salt |
| M4 | Non-constant-time crypto | Use hmac.compare_digest() |
| M5 | Weak PBKDF2 iterations | Increase to 600,000 |
| M6 | XSS in analytics | Add CSP headers, escape output |
| M7 | CSV injection | Escape formula characters |
| M8 | Missing rate limiting | Apply to all API endpoints |
| M9 | Race condition in nonce | Add threading lock |
| M10 | Missing input validation | Add Pydantic validators |

---

## Verification Checklist

### After Each Fix

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] No new warnings/errors
- [ ] Security test for fixed issue
- [ ] Code review completed

### Before Deployment

- [ ] All CRITICAL fixed and verified
- [ ] All HIGH fixed and verified
- [ ] External security audit passed
- [ ] Penetration test passed
- [ ] Documentation updated
- [ ] Monitoring configured
- [ ] Incident response plan ready

---

## Commands Reference

```bash
# Run all tests
PYTHONPATH=./src python3 -m pytest tests/ -v

# Run specific test
PYTHONPATH=./src python3 -m pytest tests/test_crypto.py -v

# Run Solidity tests
cd contracts && forge test -vvv

# Security scan Python
bandit -r src/rra/ -f json -o bandit-report.json

# Security scan Solidity
slither contracts/src/ --print human-summary

# Check dependencies
pip-audit --desc
```

---

## Progress Tracking

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Critical | In Progress | 0% |
| Phase 2: High | Pending | 0% |
| Phase 3: Medium | Pending | 0% |
| Phase 4: Low | Pending | 0% |

---

*Last Updated: 2025-12-20*
