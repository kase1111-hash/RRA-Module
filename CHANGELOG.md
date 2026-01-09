# Changelog

All notable changes to the RRA Module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1-beta] - 2026-01-05

### Fixed

#### GUI Fixes
- Fixed 9 broken documentation links in marketplace docs page
- Fixed breadcrumb navigation links in docs/verification, docs/market-yaml, docs/natlangchain pages
- Removed placeholder social media links (Twitter/Discord) from Footer component
- ChainStatus component now displays blockchain network name ("Aeneid Testnet")

#### Story Protocol Network Standardization
- Unified all Story Protocol references to use Aeneid Testnet (Chain ID: 1315)
- Updated buy-license.html: RPC URL, PIL template address, explorer URL
- Updated StoryProtocolPurchase.tsx to default to testnet
- API chain health endpoint now returns network metadata

### Added
- 22 new crypto tests for v1.0.1-beta features (1,237 total tests)
  - Encrypted key export/import roundtrip tests
  - Pedersen commitment performance tests
  - Shamir secret sharing security tests
  - Backwards compatibility tests
  - Optional dependency detection tests

### Documentation
- Consolidated integration docs into single `docs/INTEGRATIONS.md`:
  - NatLangChain Ecosystem integration
  - NatLangChain API client usage
  - Story Protocol configuration and contracts
- Updated version references to 1.0.1-beta

---

## [1.0.0-rc1] - 2026-01-05

### Security Fixes (24 findings addressed)

#### Critical
- **CRITICAL-001**: BN254 curve constants now verified against EIP-196 at module load
- **CRITICAL-002**: Pedersen commitments reject point-at-infinity (prevents information leakage)

#### High
- **HIGH-001**: Shamir polynomial evaluation uses Horner's method (timing attack resistant)
- **HIGH-002**: Lagrange interpolation uses uniform operations (timing attack resistant)
- **HIGH-003**: Commitment verification uses constant-time comparison (`hmac.compare_digest`)
- **HIGH-004**: Viewing key export now requires explicit `_acknowledge_security_risk=True`
- **HIGH-005**: Added `export_private_encrypted()` for secure password-protected key export

#### Medium
- **MED-001**: Viewing key commitments now use hiding commitment with blinding factor
- **MED-002**: Added `verify_commitment()` with constant-time comparison
- **MED-003**: IV generation uses hybrid counter+random approach (prevents IV reuse)
- **MED-004**: Key expiration enforced before decryption operations

#### Low
- **LOW-001**: All secret comparisons use constant-time comparison
- **LOW-005**: Generator point derivation increased from 256 to 1000 attempts
- **LOW-006**: Generator points validated for correct order at module load
- **LOW-007**: Test vector verification runs at module load
- **LOW-008**: Full subgroup membership validation on point deserialization

### Performance Improvements

#### 25x Faster Pedersen Commitments
- **gmpy2 integration**: 77x faster modular inverse operations
- **Windowed scalar multiplication**: Precomputed tables for generator points
- **Projective coordinates**: Eliminates ~256 inversions per scalar mult
- **py_ecc fallback**: Optimized backend when gmpy2 unavailable

Benchmark results:
- Before: 74ms per commitment
- After: 2.97ms per commitment (25x faster)
- Throughput: 336 commitments/second

#### Shamir Secret Sharing
- **Batch modular inversion**: Montgomery's trick reduces k inversions to 1

### Breaking Changes

#### Deprecated APIs
- `ViewingKey.export_private()`: Deprecated, use `export_private_encrypted()` instead
- `ViewingKeyManager.export_key_for_escrow()`: Now requires `_acknowledge_security_risk=True`

#### Behavioral Changes
- Pedersen commitments now use random blinding factors (not deterministic)
- Commitment verification parameter order: `verify(commitment, value, blinding)`
- `ShamirSecretSharing.verify_share()` now raises `ValueError` when insufficient shares

### Added
- `ViewingKey.export_private_encrypted(password)`: Secure password-protected key export
- `ViewingKey.import_private_encrypted()`: Import password-protected keys
- Optional dependencies: `gmpy2` (recommended), `py_ecc` (fallback)

### Documentation
- Updated CRYPTO-FINDINGS-QUICK-REFERENCE.md with all 24 security fixes
- Added performance optimization documentation in source code

## [1.0.0-beta] - 2026-01-03

### Added
- **Story Protocol Live Integration**: Complete license purchase flow on Story Protocol mainnet
  - IP Asset registered: `0xb77ABcfFbf063a3e6BACA37D72353750475D4E70`
  - PIL license terms attached (Commercial Remix, 0.05 ETH, 9% royalty)
  - Working buyer interface at `marketplace/public/buy-license.html`
- **Royalty Claiming**: `scripts/claim_royalties.py` for claiming revenue from Royalty Vault
- **Purchase Enablement Script**: `scripts/enable_story_purchases.py` for attaching license terms
- **Selling Licenses Guide**: `docs/SELLING-LICENSES.md` - complete monetization walkthrough

### Changed
- Updated all documentation to reflect implemented vs. planned features
- Moved future features (React Native, Flutter SDKs) to `FUTURE.md`
- Updated `docs/STORY-PROTOCOL-INTEGRATION.md` with Implementation Status section
- Cleaned up `docs/MOBILE_SDK.md` to reflect iOS/Android only (current)

### Fixed
- Address checksum errors in buy-license.html (ethers.js v6 compatibility)
- Lowercase addresses bypass checksum validation for contract interactions

### Documentation
- Added purchase badge to README.md
- Added prominent "Purchase a License" section
- Comprehensive troubleshooting for Story Protocol issues

## [0.1.0-alpha] - 2026-01-01

### Added

#### Core Features
- **Repository Ingestion**: Clone, parse, and vectorize GitHub repositories into Agent Knowledge Bases (AKB)
- **Market Configuration**: `.market.yaml` file support for defining licensing terms, pricing, and negotiation style
- **Negotiator Agent**: AI-driven agent for real-time multi-turn negotiations with natural language
- **Buyer Agent Interface**: Lightweight agent for requesting previews, proposing terms, and simulating deals

#### Blockchain Layer
- **Multi-chain Support**: Ethereum, Polygon, Arbitrum, Base, and Optimism networks
- **Smart Contracts**: License NFT (ERC-721) and License Manager contracts
- **Oracle Integration**: Event bridging and real-world data validators
- **Transaction Security**: Two-step verification with timeout and price commitment

#### Security & Privacy
- **FIDO2/WebAuthn**: Hardware authentication with zero-knowledge proofs
- **DID Authentication**: Decentralized identity support with scoped delegation
- **Cryptographic Primitives**: Shamir secret sharing, Pedersen commitments, viewing keys
- **Privacy Protection**: Identity management, batch queue processing, inference attack prevention

#### DeFi Integration
- **Yield Tokens**: Tokenized future revenue streams
- **IPFi Lending**: Intellectual property-backed lending protocol
- **Fractional Ownership**: Multi-party IP ownership support
- **Superfluid Integration**: Real-time streaming payments
- **Story Protocol**: Programmable IP licensing and royalty distribution

#### Platform Features
- **REST API Server**: FastAPI-based server with webhooks, analytics, and streaming
- **CLI Tool**: 10+ commands including `init`, `ingest`, `agent`, `verify`, `categorize`, `links`, `story`
- **Code Verification**: Test suite detection, security scanning, quality checks
- **Deep Links**: Shareable links for agent pages, direct chat, and license tiers

#### Advanced Features
- **L3 Rollup**: Batch processing and sequencer for high-throughput dispute resolution
- **Dispute Resolution**: Multi-party orchestration with voting systems
- **Adaptive Pricing**: Demand-based pricing strategies with floor/ceiling controls
- **Repository Bundling**: Multi-repo bundles with discount strategies
- **Governance**: DAO management, treasury voting, reputation-weighted voting
- **Legal Compliance**: Jurisdiction detection, compliance rules, RWA wrappers

#### Integrations
- **NatLangChain Ecosystem**: Agent-OS, synth-mind, boundary-daemon integration
- **GitHub Integration**: Webhook support, fork detection, repository status
- **Mobile SDKs**: iOS and Android integration guides

#### Documentation
- Comprehensive README and Quick Start guide
- Full technical specification (SPECIFICATION.md)
- Security audit reports with A- rating
- Cryptographic security audit
- Penetration test report
- Integration guides for all major features

#### Testing
- 1,085 tests across 43 test files
- Async test support with pytest-asyncio
- Integration test markers for selective testing

### Security
- Pinned `cryptography>=43.0.1` to fix CVE-2023-50782 and CVE-2024-0727
- Pinned `setuptools>=70.0` to fix CVE-2024-6345
- Rate limiting and API key management
- Webhook authentication with signed payloads
- Secrets management with secure storage

### Infrastructure
- Docker multi-stage build (Builder, Production, Development)
- Docker Compose for development and production
- Health checks and monitoring endpoints
- Windows batch files for build and run
- Non-root user security in containers

## License

This project is licensed under FSL-1.1-ALv2 (Functional Source License 1.1 with Apache 2.0 Future Grant).
