# Revenant Repo Agent (RRA Module)

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Security](https://img.shields.io/badge/security-A--rating-blue)](docs/SECURITY-AUDIT.md)
[![License](https://img.shields.io/badge/license-FSL--1.1--ALv2-orange)](LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](pyproject.toml)
[![Buy License](https://img.shields.io/badge/Buy_License-0.005_IP-6366f1)](https://kase1111-hash.github.io/RRA-Module/buy-license.html)

---

## What is RRA?

**Turn abandoned GitHub repos into licensable IP with one-click purchase links.**

RRA registers a repository as an IP asset on Story Protocol, attaches programmable license terms, and generates frictionless purchase links: a buyer clicks a link, connects a wallet, and mints a license NFT in one transaction. The developer configures a `.market.yaml`; RRA handles registration, link/badge/QR generation, and on-chain royalty distribution.

**One sentence:** Dead code earns license revenue while you sleep.

---

## Purchase a License

This repository is **live on Story Protocol**. Buy a license NFT to use this code commercially.

| | |
|---|---|
| **Price** | 0.005 IP (read live from the on-chain license terms) |
| **License Type** | Perpetual, Transferable |
| **What You Get** | Full source access, commercial use, derivative rights |
| **Purchase** | **[Buy Now](https://kase1111-hash.github.io/RRA-Module/buy-license.html)** |
| **Verify on Chain** | [Story Explorer](https://explorer.story.foundation/ipa/0xf08574c30337dde7C38869b8d399BA07ab23a07F) |

---

## How It Works

```
1. Configure   (.market.yaml — pricing, license terms, Story Protocol settings)
2. Register    (register the repo as an IP asset with license terms on Story)
3. Share       (generate purchase links, README badges, QR codes)
4. Sell        (buyer opens the link and mints a license NFT on-chain)
```

## Quick Start

```bash
# Install
pip install -e .

# Initialize your repo with a .market.yaml config
rra init /path/to/your-repo

# Ingest a repository and build its knowledge base
rra ingest https://github.com/your/repo

# Generate blockchain purchase links
rra purchase-link https://github.com/your/repo --wallet 0xYourWallet --network mainnet

# Generate shareable links, badges, and QR codes
rra links https://github.com/your/repo --register

# Launch the API server
uvicorn rra.api.server:app --reload
```

## Core Architecture

RRA is focused on four things:

### 1. Repository Ingestion (`rra.ingestion`)
Clone repos, parse code across languages, extract dependencies, and verify code quality so buyers know what they are licensing.

### 2. Purchase Links (`rra.services`, `rra.verification`)
Generate frictionless purchase links, README badges, QR codes, and embeddable buy buttons that point at a hosted purchase page or the Story Protocol explorer.

### 3. Blockchain Licensing (`rra.contracts`, `rra.chains`)
License NFTs with on-chain terms enforcement. Two-step transaction verification. Story Protocol integration for programmable IP licensing and royalties.

### 4. API & CLI (`rra.api`, `rra.cli`)
FastAPI server with REST endpoints for link generation and verification, and a CLI covering the full register-and-sell flow.

## Module Overview

| Layer | Modules | Purpose |
|-------|---------|---------|
| **Core** | `config`, `ingestion`, `exceptions` | Repo parsing, knowledge base, verification |
| **Blockchain** | `contracts`, `chains`, `transaction`, `oracles` | Smart contracts, multi-chain, tx verification |
| **Security** | `security`, `crypto`, `privacy` | API auth, Pedersen commitments, viewing keys |
| **Pricing** | `pricing`, `bundling` | Adaptive pricing, bundling |
| **Platform** | `api`, `cli`, `verification`, `services` | REST API, CLI, code verification, deep links |
| **Governance** | `governance`, `legal`, `reconciliation` | DAO voting, compliance, dispute resolution |
| **Integration** | `integration`, `integrations`, `identity` | NatLangChain ecosystem, Story Protocol, DID |
| **Analytics** | `analytics`, `reputation`, `predictions` | Entropy scoring, reputation tracking |
| **Storage** | `storage` | Session management, persistence |

## Key Statistics

- **~45,000+ lines** of Python code (core licensing flow)
- **30+ modules** with specialized functionality
- **1,000+ tests** across test files
- **Story Protocol** integration for programmable IP
- **Security Score: A-** based on comprehensive audit

## Documentation

### Getting Started
- **[Quick Start Guide](QUICKSTART.md)** — Installation and basic usage
- **[Usage Guide](docs/USAGE-GUIDE.md)** — Comprehensive how-to
- **[Specification](SPECIFICATION.md)** — Technical specification

### Licensing & Commerce
- **[Blockchain Licensing](docs/BLOCKCHAIN-LICENSING.md)** — Monetize your repo with Story Protocol
- **[Integrations](docs/INTEGRATIONS.md)** — NatLangChain, API client, Story Protocol

### Security
- **[Security Audit](docs/SECURITY-AUDIT.md)** — Full audit history, findings, and remediation
- **[Transaction Security](docs/TRANSACTION-SECURITY.md)** — Two-step verification

### Community
- **[Contributing](CONTRIBUTING.md)** — How to contribute
- **[Roadmap](ROADMAP.md)** — Vision, roadmap, and future development
- **[Documentation Index](docs/README.md)** — Full documentation index and support

## Part of the NatLangChain Ecosystem

RRA-Module is part of a larger ecosystem for natural language blockchain, autonomous agents, and digital sovereignty.

- **[NatLangChain](https://github.com/kase1111-hash/NatLangChain)** — Prose-first blockchain protocol
- **[Agent-OS](https://github.com/kase1111-hash/Agent-OS)** — Natural-language operating system for AI agents
- **[ILR-module](https://github.com/kase1111-hash/ILR-module)** — IP & Licensing Reconciliation

## License

FSL-1.1-ALv2 (Functional Source License 1.1 with Apache 2.0 Future Grant).

See [LICENSE.md](LICENSE.md) for the complete license text and [LICENSING.md](LICENSING.md) for compliance guidelines.
