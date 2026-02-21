# Vibe-Code Detection Audit v2.0 — RRA-Module

**Repository:** `kase1111-hash/RRA-Module`
**Audit Date:** 2026-02-21
**Methodology:** Vibe-Code Detection Audit v2.0 Framework
**Auditor:** Claude Opus 4.6 (automated code review)

---

## Executive Summary

The RRA-Module (Revenant Repo Agent Module) is a Python/TypeScript project that creates autonomous agents for on-chain repository licensing negotiations, backed by Ethereum smart contracts and a Next.js marketplace frontend.

**Vibe-Code Confidence Score: 20.9% — AI-Assisted**

The codebase was authored predominantly by AI (100% of non-dependabot commits attribute to "Claude"), but it shows clear evidence of iterative human-directed improvement. Multiple review/fix/refactor cycles are visible in the commit history. Core modules—particularly error handling, security infrastructure, smart contracts, and the negotiation engine—exhibit genuine engineering depth. However, the marketplace frontend is presentation-only scaffolding with hardcoded mock data, and several call chains break at integration boundaries, indicating that not all generated code was validated end-to-end.

---

## Scoring Summary

### A. Surface Provenance (20% weight)

| # | Criterion | Score | Evidence |
|---|-----------|-------|----------|
| A1 | Commit patterns | 1/3 (Weak) | 100% of non-dependabot commits authored by "Claude." Uniform commit message style. No individual human developer commits. |
| A2 | Comments/documentation style | 2/3 (Moderate) | Consistent SPDX headers, thorough docstrings. Style is uniform but substantive—not just boilerplate. |
| A3 | Test quality | 3/3 (Strong) | ~50 test files. `conftest.py` builds comprehensive MockWeb3/MockContract infrastructure. Tests cover edge cases (ReDoS, path traversal, rate limiting). Not mere assertion stubs. |
| A4 | Dependencies | 2/3 (Moderate) | Real production dependencies (FastAPI, Web3.py, Pydantic, wagmi, viem) used appropriately. `pyproject.toml` and `requirements.txt` present. |
| A5 | Naming consistency | 2/3 (Moderate) | snake_case Python, camelCase TS/JS. Almost *too* consistent—no natural drift or legacy naming. |
| A6 | Documentation accuracy | 2/3 (Moderate) | Extensive docs (SPECIFICATION, QUICKSTART, ROADMAP, etc.) but some claims don't match implementation (e.g., "Redis-backed sessions" when payload serialization is incomplete). |
| A7 | Dependency utilization | 2/3 (Moderate) | Core dependencies (FastAPI, Web3, Pydantic) are deeply utilized. Some declared features (Superfluid streaming, DeFi integration) have thin `__init__.py`-only modules. |

**Surface Provenance Raw Score: 14/21 = 66.7%**
**Weighted Contribution: 66.7% × 0.20 = 13.3%**

### B. Behavioral Integrity (50% weight)

| # | Criterion | Score | Evidence |
|---|-----------|-------|----------|
| B1 | Error handling | 3/3 (Strong) | `exceptions.py` defines a comprehensive hierarchy: `RRAError` → domain-specific types (ContractError, TransactionError, DisputeError, etc.) with error codes, context dicts, and cause chaining. `sanitize_error_message()` strips file paths, IPs, and connection strings from API responses. |
| B2 | Configuration usage | 3/3 (Strong) | `environment.py` provides full dev/staging/production separation with env variable overrides, feature flags, and `validate_config()` that checks for production misconfigurations. Config is `@lru_cache(maxsize=1)` with explicit `reload_config()`. |
| B3 | Call chain completeness | 2/3 (Moderate) | Most chains are complete (negotiate start → KB load → agent → session → response). **Break found:** `ContractManager.register_repo()` passes 5 args but `LicenseNFTContract.register_repository()` expects 8 (missing nonce, signature). Registration would fail at runtime. |
| B4 | Async correctness | 3/3 (Strong) | Proper async/await in FastAPI endpoints and WebSocket handlers. `asyncio.sleep(0.5)` for typing simulation is appropriate. No blocking calls in async context. |
| B5 | State management | 2/3 (Moderate) | `SessionStore` abstraction with `InMemorySessionStore` and `RedisSessionStore`, proper thread safety (locks, double-checked locking). **Critical gap:** `RedisSessionStore._deserialize()` sets `payload=None`—negotiation agent state cannot survive Redis serialization round-trips. |
| B6 | Security depth | 3/3 (Strong) | Multi-layered: `hmac.compare_digest` for API keys, CSP/HSTS/X-Frame-Options headers, path traversal prevention, SSRF blocking, ReentrancyGuard on Solidity, registrar signature verification with nonce replay protection, WebSocket token auth (single-use, 60s TTL). |
| B7 | Resource cleanup | 2/3 (Moderate) | WebSocket `finally` blocks call `disconnect()`. Session `cleanup_expired()` exists. **Gap:** `_ws_tokens` dict has no size limit—attackers could exhaust memory via POST /ws/token spam. |

**Behavioral Integrity Raw Score: 18/21 = 85.7%**
**Weighted Contribution: 85.7% × 0.50 = 42.9%**

### C. Interface Authenticity (30% weight)

| # | Criterion | Score | Evidence |
|---|-----------|-------|----------|
| C1 | API design consistency | 3/3 (Strong) | Uniform patterns: Pydantic request/response models, `Depends(verify_api_key)` auth, structured error responses, proper HTTP status codes. Root endpoint returns different detail based on auth state. |
| C2 | Frontend implementation depth | 1/3 (Weak) | Next.js marketplace renders correctly but uses 100% hardcoded mock data (`featuredRepos`, `marketConfigs`, `verificationData` as inline constants in `page.tsx`). No API calls, no data fetching, no `useEffect` for backend integration. Pure visual scaffolding. |
| C3 | State management | 2/3 (Moderate) | Backend: proper session store abstraction with Redis path. Frontend: `useState` only, no global state (Redux/Zustand/Context), no optimistic updates, no cache invalidation. |
| C4 | Security infrastructure | 3/3 (Strong) | See B6. Both backend (CSP, CORS, HSTS, rate limiting, error sanitization) and frontend (`rel="noopener noreferrer"`, proper wallet connection handling) have security considerations. |
| C5 | WebSocket implementation | 3/3 (Strong) | Full implementation: token-based auth, ConnectionManager with per-repo tracking, proper disconnect handling, typing indicators, phase change notifications, dreaming status endpoint with ping/pong keepalive. |
| C6 | Error UX | 2/3 (Moderate) | Backend errors are sanitized and structured. `StoryProtocolPurchase` component shows error/success states. `NegotiationChat` has loading indicators. But error recovery paths (retry, fallback) are minimal. |
| C7 | Observability | 2/3 (Moderate) | "Dreaming" status system for real-time operation visibility, analytics endpoints (`/api/analytics/*`), monitoring config (metrics, tracing, health checks). Logging is comprehensive throughout. |

**Interface Authenticity Raw Score: 16/21 = 76.2%**
**Weighted Contribution: 76.2% × 0.30 = 22.9%**

---

## Final Score Calculation

```
Vibe-Code Confidence = 100% - [(A% × 0.20) + (B% × 0.50) + (C% × 0.30)]
                     = 100% - [(66.7% × 0.20) + (85.7% × 0.50) + (76.2% × 0.30)]
                     = 100% - [13.3% + 42.9% + 22.9%]
                     = 100% - 79.1%
                     = 20.9%
```

**Classification: AI-Assisted (16–35%)**

---

## High Severity Findings

### H-001: RedisSessionStore Cannot Persist Negotiation State
**File:** `src/rra/storage/session_store.py:326-334`

The `_deserialize()` method sets `payload=None` with a comment "Payload must be reconstructed by caller." Since the negotiation agent (`NegotiatorAgent`) instance is the payload, Redis-backed sessions cannot restore agent state. This breaks the production horizontal scaling story that the documentation promises.

**Impact:** Production deployments with Redis would lose all negotiation context on any server restart or load-balanced request routing to a different instance.

**Remediation:** Implement serialization/deserialization for `NegotiatorAgent` state. The agent already has `get_state()`/`restore_state()` methods—wire these into the Redis store's serialize/deserialize cycle.

### H-002: Marketplace Frontend Is Presentation-Only Scaffolding
**File:** `marketplace/src/app/page.tsx:8-109`

The homepage declares `featuredRepos`, `marketConfigs`, and `verificationData` as hardcoded JavaScript constants. No `fetch()`, no `useEffect`, no `getServerSideProps`/`getStaticProps`, no API route calls. Every marketplace page renders static mock data only.

**Impact:** The marketplace is non-functional as a product. Users cannot discover real repositories, initiate negotiations, or purchase licenses through the frontend.

**Remediation:** Replace mock data with API calls to the FastAPI backend (`/api/marketplace/repos`, `/api/marketplace/featured`). Implement server components or client-side data fetching with loading/error states.

### H-003: ContractManager.register_repo() Call Chain Broken
**File:** `src/rra/contracts/manager.py:226-323`

`register_repo()` calls `self.license_contract.register_repository()` with positional arguments `(repo_url, target_wei, floor_wei, developer_address, private_key)`. But `LicenseNFTContract.register_repository()` at `license_nft.py:164` expects `(repo_url, target_price_wei, floor_price_wei, nonce, signature, developer_address, private_key)`. The `nonce` and `signature` parameters are missing entirely from the manager's interface.

**Impact:** Repository registration via the Python API would raise a `TypeError` at runtime. The smart contract's front-running protection (signature verification) is effectively bypassed at the integration layer.

**Remediation:** Add `nonce` and `signature` parameters to `ContractManager.register_repo()` and pass them through. Implement a helper to generate the registrar signature (EIP-712 or ethSignedMessage).

---

## Medium Severity Findings

### M-001: WebSocket Token Store Has No Size Limit
**File:** `src/rra/api/websocket.py:106`

`_ws_tokens: Dict[str, Dict] = {}` grows unboundedly. While cleanup occurs on validation, tokens that are generated but never used (never validated) accumulate forever. An attacker could call `POST /ws/token` repeatedly (rate limiting applies to the overall API, not specifically to token generation).

**Remediation:** Add a maximum size (e.g., 10,000 entries) and reject new token requests when full, or run periodic cleanup on a background timer.

### M-002: WebSocket KB Loader Ignores Compressed Files
**File:** `src/rra/api/websocket.py:373`

`load_knowledge_base()` only globs `*_kb.json` but the server's `/api/repositories` endpoint also checks `*_kb.json.gz`. Knowledge bases that have been compressed (as supported by the `storage/compression.py` module) will be invisible to WebSocket negotiation.

**Remediation:** Add `*_kb.json.gz` to the glob pattern and handle decompression, matching the behavior in the REST endpoint.

### M-003: Dual Auth Systems Not Integrated
**Files:** `src/rra/api/auth.py` and `src/rra/security/api_auth.py`

Two separate authentication modules exist. The API server uses the simpler `api/auth.py` (env-variable-based key comparison). The richer `security/api_auth.py` provides `APIKeyManager` with hashed key storage, scopes, expiration, and revocation—but nothing in the application uses it. This creates confusion about which auth system is canonical.

**Remediation:** Either integrate `APIKeyManager` into the main server as the production auth path, or remove it to reduce confusion. If keeping both, document which is used where and why.

### M-004: Decimal/Float Type Mismatch in Transaction Safeguards
**File:** `src/rra/transaction/safeguards.py:459,474`

`_to_usd()` returns `Decimal` but `_determine_safeguard_level()` accepts `float` and compares against `int` thresholds. While Python handles mixed Decimal/float/int comparisons, this can produce unexpected results with edge-case values and violates the purpose of using `Decimal` for financial precision.

**Remediation:** Keep the full chain in `Decimal` through to the safeguard level determination, or explicitly convert at the boundary with `float(usd_value)`.

---

## Evidence of Genuine Engineering

Despite the strong AI-authorship signal from commit history, several areas demonstrate authentic engineering depth that goes beyond typical AI scaffolding:

1. **Exception hierarchy** (`exceptions.py`): The multi-level hierarchy with error codes (1xxx–10xxx), structured context, cause chaining, and `wrap_exception()` helper shows domain modeling thought—not just pattern completion.

2. **Solidity contract** (`RepoLicense.sol`): Follows Checks-Effects-Interactions pattern with explicit comments explaining ordering. Registrar signature verification includes `block.chainid` and `address(this)` in the hash to prevent cross-chain/cross-contract replay. `ReentrancyGuard` on payable functions. This code would survive a basic security audit.

3. **Test infrastructure** (`conftest.py`): The `MockWeb3` class simulates a realistic blockchain environment (nonce management, transaction receipts, contract deployment, signed transactions). This isn't stub-level mocking—it models actual Web3 behavior.

4. **Security layering**: Constant-time API key comparison, WebSocket single-use tokens with TTL, SSRF protection blocking RFC1918/cloud metadata endpoints, CSP headers with dynamic connect-src from CORS config. These are defense-in-depth measures that show security awareness.

5. **Transaction safeguards** (`safeguards.py`): Tiered confirmation system with price oracle integration, Decimal-based price parsing, rate limiting per buyer, formatted confirmation screens. This module addresses real UX concerns about accidental blockchain transactions.

6. **Iterative improvement**: Commit history shows multiple audit→fix cycles: "Add comprehensive security audit report" followed by "Fix 55 security findings," then "Fix 17 issues that pass tests but don't fully function." This indicates human review directing AI remediation.

---

## Vibe-Coded Elements

Areas that show signs of AI generation without full human validation:

1. **SDK directories** (`sdks/android/`, `sdks/ios/`): Skeleton implementations of Kotlin and Swift clients. These appear structurally complete but have no tests and no evidence of being run against actual mobile builds.

2. **Thin modules**: Several packages contain only `__init__.py` re-exports or minimal stubs: `src/rra/defi/__init__.py`, `src/rra/predictions/`, `src/rra/pricing/`. These exist to fill out the project structure per the SPECIFICATION but contain minimal logic.

3. **Documentation volume**: 20+ markdown files covering everything from roadmap to founding contributor pledge to buyer beware notices. The volume is disproportionate to the code maturity. Several docs reference features that don't fully exist.

4. **Marketplace frontend**: As detailed in H-002, this is visual scaffolding. The components are well-crafted (proper TypeScript, accessible markup, dark mode support) but disconnected from any data layer.

5. **Multiple overlapping scripts**: The `scripts/` directory contains ~25 JavaScript and Python scripts for blockchain operations, with significant overlap (e.g., `claim-royalties.js`, `claim-fixed.js`, `claim-as-ip-owner.js`, `claim-via-ip-account.js`, `claim-via-module.js`). These appear to be iterative AI attempts at the same operation.

---

## Remediation Checklist

### Critical (address before any production deployment)
- [ ] **H-001**: Wire `NegotiatorAgent.get_state()`/`restore_state()` into `RedisSessionStore` serialization
- [ ] **H-003**: Fix `ContractManager.register_repo()` to pass nonce and signature through to the contract

### High (address before public beta)
- [ ] **H-002**: Replace marketplace mock data with real API integration
- [ ] **M-003**: Consolidate to a single auth system or clearly document the boundary

### Medium (address in normal development)
- [ ] **M-001**: Add size cap and periodic cleanup for `_ws_tokens`
- [ ] **M-002**: Add `.json.gz` glob support to WebSocket KB loader
- [ ] **M-004**: Maintain `Decimal` type consistency in safeguards module

### Low (quality improvements)
- [ ] Remove or flesh out stub modules (`defi/`, `predictions/`, `pricing/`)
- [ ] Consolidate overlapping claim scripts in `scripts/`
- [ ] Add integration tests that exercise full API→contract call chains
- [ ] Connect SDK directories to CI or remove them
