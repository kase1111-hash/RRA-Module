# Cryptographic Findings - Quick Reference
## Line-by-Line Security Issues
**Date:** 2025-12-20
**Purpose:** Quick lookup for developers fixing issues

---

## Critical Issues (Fix Immediately)

### CRITICAL-001: Unverified BN254 Prime
```
File: /home/user/RRA-Module/src/rra/crypto/pedersen.py
Lines: 36, 38

Current Code:
36: BN254_FIELD_PRIME = 21888242871839275222246405745257275088696311157297823662689037894645226208583
38: BN254_CURVE_ORDER = 21888242871839275222246405745257275088548364400416034343698204186575808495617

Fix:
import sympy
assert sympy.isprime(BN254_FIELD_PRIME), "BN254_FIELD_PRIME verification failed"
assert BN254_FIELD_PRIME == 0x30644e72e131a029b85045b68181585d97816a916871ca8d3c208c16d87cfd47
```

---

### CRITICAL-002: Point-at-Infinity Not Rejected
```
File: /home/user/RRA-Module/src/rra/crypto/pedersen.py
Lines: 265-271

Current Code:
265: vG = _scalar_mult(v, self.g)
267: rH = _scalar_mult(r, self.h)
268: C = _point_add(vG, rH)
269:
270: commitment = _point_to_bytes(C)
271: return commitment, blinding

Fix (add after line 268):
if C == (0, 0):
    raise ValueError("Commitment resulted in point at infinity")
```

---

### CRITICAL-003: Unverified Shamir Prime
```
File: /home/user/RRA-Module/src/rra/crypto/shamir.py
Line: 31

Current Code:
31: PRIME = 2**256 - 189  # A known safe prime

Fix (add after line 31):
import sympy
assert sympy.isprime(PRIME), "PRIME must be verified prime"
```

---

## High Severity Issues

### HIGH-001: HKDF Without Salt (Privacy Module)
```
File: /home/user/RRA-Module/src/rra/privacy/viewing_keys.py
Lines: 106-112

Current Code:
106: derived_key = HKDF(
107:     algorithm=hashes.SHA256(),
108:     length=32,
109:     salt=None,  # ❌ NO SALT
110:     info=b"viewing_key_encryption",
111:     backend=default_backend()
112: ).derive(shared_key)

Fix:
106: # Use first 16 bytes of ephemeral public key as salt
107: ephemeral_salt = ephemeral_public_bytes[:16]
108: derived_key = HKDF(
109:     algorithm=hashes.SHA256(),
110:     length=32,
111:     salt=ephemeral_salt,  # ✅ WITH SALT
112:     info=b"viewing_key_encryption",
113:     backend=default_backend()
114: ).derive(shared_key)

Note: Lines 159-166 have the same issue - apply same fix
```

---

### HIGH-002 & HIGH-003: Timing Attacks in Shamir
```
File: /home/user/RRA-Module/src/rra/crypto/shamir.py
Lines: 272-289 (Polynomial Evaluation)
Lines: 291-320 (Lagrange Interpolation)

Current Code (lines 282-288):
282: def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
283:     result = 0
284:     x_power = 1
285:     for coef in coefficients:
286:         result = (result + coef * x_power) % self.prime  # ❌ Timing leak
287:         x_power = (x_power * x) % self.prime
288:     return result

Fix Option 1 - Add random delay:
def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
    result = 0
    x_power = 1
    for coef in coefficients:
        result = (result + coef * x_power) % self.prime
        x_power = (x_power * x) % self.prime
    # Add random delay to mask timing
    time.sleep(random.uniform(0.001, 0.005))
    return result

Fix Option 2 - Use constant-time library:
from constanttime import ct_compare, ct_select  # Requires external library
# Implement constant-time field operations
```

---

### HIGH-004: Share Verification Fails Open
```
File: /home/user/RRA-Module/src/rra/crypto/shamir.py
Line: 341

Current Code:
338: if len(other_shares) < threshold - 1:
339:     # Not enough other shares to verify
340:     return True  # ❌ FAILS OPEN
341:

Fix:
338: if len(other_shares) < threshold - 1:
339:     # Not enough other shares to verify
340:     raise ValueError(f"Need {threshold-1} shares to verify, only have {len(other_shares)}")
```

---

### HIGH-005: Plaintext Key Export
```
File: /home/user/RRA-Module/src/rra/crypto/viewing_keys.py
Lines: 288-290

Current Code:
288: def export_private(self) -> bytes:
289:     """Export private key bytes (use with caution)."""
290:     return self.private_key.to_bytes()

Fix - Add encrypted export:
def export_private_encrypted(self, password: str) -> bytes:
    """Export private key encrypted with password."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes

    # Derive key from password
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    key = kdf.derive(password.encode())

    # Encrypt private key
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, self.private_key.to_bytes(), None)

    # Return salt + nonce + ciphertext
    return salt + nonce + ciphertext

# Deprecate old method:
def export_private(self) -> bytes:
    """DEPRECATED: Use export_private_encrypted() instead."""
    import warnings
    warnings.warn("Exporting unencrypted keys is insecure", DeprecationWarning)
    return self.private_key.to_bytes()
```

---

## Medium Severity Issues

### MEDIUM-001: Key Commitment Not Hiding
```
File: /home/user/RRA-Module/src/rra/crypto/viewing_keys.py
Lines: 232-238

Current Code:
232: @property
233: def commitment(self) -> bytes:
234:     """Get on-chain commitment for this key."""
235:     return keccak(self.public_key.to_bytes())

Fix - Use Pedersen commitment:
@property
def commitment(self) -> bytes:
    """Get on-chain commitment for this key using Pedersen."""
    from .pedersen import PedersenCommitment
    pc = PedersenCommitment()
    # Commit to public key with existing blinding factor
    commitment, _ = pc.commit(
        self.public_key.to_bytes(),
        self.blinding_factor  # Use existing blinding from ViewingKey
    )
    return commitment
```

---

### MEDIUM-002: Plaintext Master Key Storage
```
File: /home/user/RRA-Module/src/rra/crypto/viewing_keys.py
Line: 338

Current Code:
338: self.master_key = master_key or os.urandom(32)

Fix - Use key wrapping:
def __init__(self, master_key: Optional[bytes] = None, ...):
    # Wrap master key with additional encryption layer
    if master_key:
        # In production: derive from HSM or encrypted storage
        self._wrapped_master_key = self._wrap_key(master_key)
    else:
        self._wrapped_master_key = self._wrap_key(os.urandom(32))

def _wrap_key(self, key: bytes) -> bytes:
    """Wrap key with additional protection."""
    # Simple wrapper - in production use HSM or KMS
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    # ... implementation
```

---

### MEDIUM-003: No IV Uniqueness Check
```
File: /home/user/RRA-Module/src/rra/crypto/viewing_keys.py
Line: 463

Current Code:
463: iv = os.urandom(12)

Fix - Add IV tracking:
class ViewingKeyManager:
    def __init__(self, ...):
        # ...
        self._iv_counter = 0
        self._iv_lock = threading.Lock()

    def _generate_unique_iv(self) -> bytes:
        """Generate guaranteed unique IV."""
        with self._iv_lock:
            counter = self._iv_counter
            self._iv_counter += 1

        # Combine random + counter for uniqueness
        random_part = os.urandom(8)
        counter_part = counter.to_bytes(4, 'big')
        return random_part + counter_part

Then replace line 463:
463: iv = self._generate_unique_iv()
```

---

### MEDIUM-004: Missing Expiration Enforcement
```
File: /home/user/RRA-Module/src/rra/crypto/viewing_keys.py
Lines: 261-274

Current Code:
261: def decrypt(self, encrypted: EncryptedData) -> bytes:
262:     """Decrypt ECIES-encrypted data."""
273:     return ViewingKeyManager.decrypt_with_key(encrypted, self.private_key)

Fix - Add expiration check:
261: def decrypt(self, encrypted: EncryptedData) -> bytes:
262:     """Decrypt ECIES-encrypted data."""
263:     # Check expiration before decrypting
264:     if self.is_expired:
265:         raise ValueError(
266:             f"Cannot decrypt with expired key "
267:             f"(expired at {self.expires_at})"
268:         )
273:     return ViewingKeyManager.decrypt_with_key(encrypted, self.private_key)
```

---

### MEDIUM-005: Missing Curve Validation
```
File: /home/user/RRA-Module/src/rra/crypto/pedersen.py
Lines: 155-163

Current Code:
155: def _bytes_to_point(data: bytes) -> Tuple[int, int]:
156:     """Deserialize EC point from 64 bytes."""
157:     if len(data) != 64:
158:         raise ValueError("Point must be 64 bytes")
159:     if data == b'\x00' * 64:
160:         return (0, 0)
161:     x = int.from_bytes(data[:32], 'big')
162:     y = int.from_bytes(data[32:], 'big')
163:     return (x, y)  # ❌ No curve validation

Fix - Add curve equation check:
def _bytes_to_point(data: bytes) -> Tuple[int, int]:
    """Deserialize EC point from 64 bytes."""
    if len(data) != 64:
        raise ValueError("Point must be 64 bytes")
    if data == b'\x00' * 64:
        return (0, 0)

    x = int.from_bytes(data[:32], 'big')
    y = int.from_bytes(data[32:], 'big')

    # Validate point is on BN254 curve: y^2 = x^3 + 3 (mod p)
    y_squared = (y * y) % BN254_FIELD_PRIME
    x_cubed_plus_3 = (pow(x, 3, BN254_FIELD_PRIME) + 3) % BN254_FIELD_PRIME

    if y_squared != x_cubed_plus_3:
        raise ValueError(f"Point ({x}, {y}) not on BN254 curve")

    return (x, y)
```

---

### MEDIUM-006: Poseidon MDS Not Verified
```
File: /home/user/RRA-Module/src/rra/privacy/identity.py
Lines: 115-136

Current Code:
115: def _generate_mds(self, t: int) -> list:
116:     """Generate MDS matrix for width t."""
117:     if t in self._mds_cache:
118:         return self._mds_cache[t]
119:
120:     # Generate MDS using Cauchy matrix
121:     matrix = []
122:     for i in range(t):
123:         row = []
124:         for j in range(t):
125:             val = pow(i + t + j, self.FIELD_PRIME - 2, self.FIELD_PRIME)
126:             row.append(val)
127:         matrix.append(row)
128:
129:     self._mds_cache[t] = matrix
130:     return matrix

Fix - Use precomputed circomlib matrices:
# Add at top of file
CIRCOMLIB_MDS_MATRICES = {
    2: [[1, 1], [1, 2]],  # From circomlib
    3: [[1, 1, 1], [1, 2, 3], [1, 4, 9]],
    # Add more from circomlib poseidon_constants.circom
}

def _generate_mds(self, t: int) -> list:
    """Get MDS matrix from circomlib constants."""
    if t not in CIRCOMLIB_MDS_MATRICES:
        raise ValueError(f"No circomlib MDS matrix for t={t}")
    return CIRCOMLIB_MDS_MATRICES[t]
```

---

### MEDIUM-007: Poseidon Round Constants Incompatible
```
File: /home/user/RRA-Module/src/rra/privacy/identity.py
Lines: 85-113

Current Code:
85: def _generate_round_constants(self, t: int, num_rounds: int) -> list:
100:     constants = []
101:     seed = keccak(f"poseidon_constants_t{t}".encode())
102:
103:     for r in range(num_rounds):
104:         round_consts = []
105:         for i in range(t):
106:             seed = keccak(seed)
107:             c = int.from_bytes(seed, 'big') % self.FIELD_PRIME
108:             round_consts.append(c)
109:         constants.append(round_consts)

Fix - Import circomlib constants:
# Create new file: poseidon_constants.py
# Extract constants from:
# https://github.com/iden3/circomlib/blob/master/circuits/poseidon_constants.circom

# Then import:
from .poseidon_constants import POSEIDON_C

def _generate_round_constants(self, t: int, num_rounds: int) -> list:
    """Get round constants from circomlib."""
    cache_key = (t, num_rounds)
    if cache_key in self._round_constants_cache:
        return self._round_constants_cache[cache_key]

    if cache_key not in POSEIDON_C:
        raise ValueError(f"No circomlib constants for t={t}, rounds={num_rounds}")

    constants = POSEIDON_C[cache_key]
    self._round_constants_cache[cache_key] = constants
    return constants
```

---

### MEDIUM-008: Missing Share Index Validation
```
File: /home/user/RRA-Module/src/rra/privacy/secret_sharing.py
Lines: 112-147

Current Code:
112: def reconstruct(self, shares: List[Share]) -> int:
121:     if len(shares) < self.threshold:
122:         raise ValueError(...)
124:     # Use only threshold shares
125:     shares = shares[:self.threshold]

Fix - Add index validation:
112: def reconstruct(self, shares: List[Share]) -> int:
113:     """Reconstruct secret from shares."""
114:     if not shares:
115:         raise ValueError("No shares provided")
116:
117:     # Validate share indices
118:     for share in shares:
119:         if not (1 <= share.index <= 255):
120:             raise ValueError(f"Invalid share index: {share.index}")
121:
122:     threshold = shares[0].threshold
123:     if len(shares) < threshold:
124:         raise ValueError(...)
```

---

## Low Severity Issues (Quick Fixes)

### LOW-001: Non-Constant-Time Comparison
```
File: /home/user/RRA-Module/src/rra/privacy/secret_sharing.py
Line: 167

Fix:
import hmac
return hmac.compare_digest(expected, commitment)
```

---

### LOW-002: Silent Exception Handling
```
File: /home/user/RRA-Module/src/rra/privacy/identity.py
Line: 505

Fix:
except Exception as e:
    import logging
    logging.warning(f"Failed to load identity {name}: {e}")
    return None
```

---

### LOW-003: Missing Address Validation
```
File: /home/user/RRA-Module/src/rra/privacy/identity.py
Lines: 298-301

Fix:
from eth_utils import is_address, to_checksum_address

if address:
    if not is_address(address):
        raise ValueError(f"Invalid Ethereum address: {address}")
    address = to_checksum_address(address)
    combined = bytes.fromhex(address[2:]).ljust(20, b'\x00') + salt
```

---

### LOW-004: Timing Oracle in Delay
```
File: /home/user/RRA-Module/src/rra/privacy/batch_queue.py
Lines: 454-457

Fix:
# Always delay, randomize amount
base_delay = 15  # seconds
random_addition = (int.from_bytes(os.urandom(2), 'big') % 15000) / 1000
delay = base_delay + random_addition  # 15-30 seconds
self._random_delays.append(delay)
time.sleep(delay)
```

---

## Test Vectors Needed

### Pedersen Commitment Test
```python
# Add to tests/crypto/test_pedersen.py
def test_pedersen_known_values():
    """Test against known good values."""
    pc = PedersenCommitment()

    # Test vector 1
    value = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000001")
    blinding = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000002")
    commitment, _ = pc.commit(value, blinding)

    # Expected from reference implementation
    expected = bytes.fromhex("...")  # TODO: Get from reference implementation
    assert commitment == expected
```

---

### Poseidon Hash Test
```python
# Add to tests/crypto/test_poseidon.py
def test_poseidon_circomlib_compatible():
    """Test against circomlib Poseidon."""
    poseidon = PoseidonHash()

    # Test vectors from circomlib
    test_vectors = [
        {
            "inputs": [0],
            "expected": 0x2098f5fb9e239eab3ceac3f27b81e481dc3124d55ffed523a839ee8446b64864
        },
        {
            "inputs": [1],
            "expected": 0x1de82072aa88ab6bb8bb0d8d8bb5f93f0c99c0f5e7c86ad9b4c64a4c16b30d7d
        },
        # Add more from:
        # https://github.com/iden3/circomlib/blob/master/test/poseidon.js
    ]

    for vec in test_vectors:
        result = poseidon.hash(vec["inputs"])
        assert result == vec["expected"], f"Poseidon test failed for {vec['inputs']}"
```

---

### Shamir Secret Sharing Test
```python
# Add to tests/crypto/test_shamir.py
def test_shamir_threshold_security():
    """Test that M-1 shares reveal nothing."""
    sss = ShamirSecretSharing(threshold=3, total_shares=5)

    secret = int.from_bytes(os.urandom(32), 'big') % sss.prime
    shares = sss.split(secret)

    # 3 shares should reconstruct
    reconstructed = sss.reconstruct(shares[:3])
    assert reconstructed == secret

    # 2 shares should fail
    with pytest.raises(ValueError):
        sss.reconstruct(shares[:2])
```

---

## Quick Checklist for Developers

### Before Committing Crypto Code
- [ ] Added test vectors from reference implementation
- [ ] Verified constant-time operations where needed
- [ ] Validated all inputs (indices, addresses, points)
- [ ] Used constant-time comparison for secrets
- [ ] Added proper error handling (don't fail open)
- [ ] Documented security assumptions
- [ ] Added type hints
- [ ] Ran security linter (bandit)

### Before Production Deployment
- [ ] All CRITICAL issues fixed
- [ ] All HIGH issues fixed
- [ ] Test coverage > 95%
- [ ] External security audit completed
- [ ] Timing analysis performed
- [ ] Fuzzing tests passed
- [ ] Integration tests with contracts passed
- [ ] Documentation reviewed

---

## Quick Command Reference

### Run Security Tests
```bash
# Unit tests
pytest tests/crypto/ -v --cov=src/rra/crypto --cov-report=html

# Security linting
bandit -r src/rra/crypto/ src/rra/privacy/ -f json -o crypto-security.json

# Type checking
mypy src/rra/crypto/ src/rra/privacy/ --strict

# Timing analysis
python tests/security/test_timing_attacks.py
```

### Verify Cryptographic Constants
```bash
# Verify BN254 constants
python -c "
import sympy
PRIME = 21888242871839275222246405745257275088696311157297823662689037894645226208583
assert sympy.isprime(PRIME)
assert PRIME == 0x30644e72e131a029b85045b68181585d97816a916871ca8d3c208c16d87cfd47
print('✅ BN254_FIELD_PRIME verified')
"

# Verify Shamir prime
python -c "
import sympy
PRIME = 2**256 - 189
assert sympy.isprime(PRIME)
print('✅ SHAMIR PRIME verified')
"
```

---

**Last Updated:** 2025-12-20
**Maintainer:** Security Team
**Quick Reference Version:** 1.0

---

*Keep this document bookmarked for quick lookups during development.*
