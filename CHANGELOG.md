# Changelog

All notable changes to the RRA Module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
