# Revenant Repo Agent (RRA Module)

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)
[![Security](https://img.shields.io/badge/security-A--rating-blue)](SECURITY-REPORTS.md)
[![License](https://img.shields.io/badge/license-FSL--1.1--ALv2-orange)](LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](pyproject.toml)
[![Buy License](https://img.shields.io/badge/Buy_License-10_IP-6366f1)](https://kase1111-hash.github.io/RRA-Module/buy-license.html)

---

## What is RRA?

**Turn abandoned GitHub repos into autonomous licensing agents.**

RRA clones a dormant repository, analyzes it, spawns an AI negotiation agent, and sells licenses as on-chain NFTs. The developer configures a `.market.yaml`, and the agent handles everything: marketing the code, negotiating terms, minting license tokens, and distributing revenue.

**One sentence:** Dead code makes money while you sleep.

---

## Purchase a License

This repository is **live on Story Protocol**. Buy a license NFT to use this code commercially.

| | |
|---|---|
| **Price** | 10 IP |
| **License Type** | Perpetual, Transferable |
| **What You Get** | Full source access, commercial use, derivative rights |
| **Purchase** | **[Buy Now](https://kase1111-hash.github.io/RRA-Module/buy-license.html)** |
| **Verify on Chain** | [Story Explorer](https://aeneid.explorer.story.foundation/token/0xb77ABcfFbf063a3e6BACA37D72353750475D4E70) |

---

## How It Works

```
1. Configure   (.market.yaml — pricing, terms, agent personality)
2. Ingest      (clone repo, parse code, build knowledge base)
3. Negotiate   (AI agent handles multi-turn license negotiations)
4. Sell        (mint ERC-721 license NFT, distribute revenue on-chain)
```

## Quick Start

```bash
# Install
pip install -e .

# Initialize your repo with a .market.yaml config
rra init /path/to/your-repo

# Ingest a repository and build its knowledge base
rra ingest https://github.com/your/repo

# Start the negotiation agent
rra agent agent_knowledge_bases/repo_kb.json --simulate

# Launch the API server
uvicorn rra.api.server:app --reload
```

## Core Architecture

RRA is focused on four things:

### 1. Repository Ingestion (`rra.ingestion`)
Clone repos, parse code across languages, extract dependencies, generate a knowledge base the agent can use to sell the code intelligently.

### 2. AI Negotiation Agents (`rra.agents`)
Autonomous negotiator and buyer agents that conduct multi-turn license negotiations. Configurable personality, pricing flexibility, and negotiation strategies.

### 3. Blockchain Licensing (`rra.contracts`, `rra.chains`)
ERC-721 license NFTs with on-chain terms enforcement. Two-step transaction verification. Story Protocol integration for programmable IP licensing.

### 4. API & Marketplace (`rra.api`, `rra.cli`)
FastAPI server with REST endpoints, WebSocket real-time chat, webhook integration, embeddable widget, and a CLI with 10+ commands.

## Module Overview

| Layer | Modules | Purpose |
|-------|---------|---------|
| **Core** | `config`, `ingestion`, `agents`, `exceptions` | Repo parsing, knowledge base, agent lifecycle |
| **Blockchain** | `contracts`, `chains`, `transaction`, `oracles` | Smart contracts, multi-chain, tx verification |
| **Security** | `security`, `crypto`, `privacy` | API auth, Pedersen commitments, viewing keys |
| **Negotiation** | `negotiation`, `pricing`, `bundling` | Clause hardening, adaptive pricing, bundling |
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
- **[Selling Licenses](docs/SELLING-LICENSES.md)** — Monetize your repo with Story Protocol
- **[Blockchain Licensing](docs/BLOCKCHAIN-LICENSING.md)** — Automated monetization guide
- **[Integrations](docs/INTEGRATIONS.md)** — NatLangChain, API client, Story Protocol

### Security
- **[Security Reports](SECURITY-REPORTS.md)** — A- security rating
- **[Cryptographic Audit](CRYPTOGRAPHIC-SECURITY-AUDIT-2025-12-20.md)** — 24 crypto fixes applied
- **[Transaction Security](docs/TRANSACTION-SECURITY.md)** — Two-step verification

### Community
- **[Contributing](CONTRIBUTING.md)** — How to contribute
- **[Roadmap](ROADMAP.md)** — Product roadmap
- **[Support](SUPPORT.md)** — How to get help

## Part of the NatLangChain Ecosystem

RRA-Module is part of a larger ecosystem for natural language blockchain, autonomous agents, and digital sovereignty.

- **[NatLangChain](https://github.com/kase1111-hash/NatLangChain)** — Prose-first blockchain protocol
- **[Agent-OS](https://github.com/kase1111-hash/Agent-OS)** — Natural-language operating system for AI agents
- **[ILR-module](https://github.com/kase1111-hash/ILR-module)** — IP & Licensing Reconciliation

## License

FSL-1.1-ALv2 (Functional Source License 1.1 with Apache 2.0 Future Grant).

See [LICENSE.md](LICENSE.md) for the complete license text and [LICENSING.md](LICENSING.md) for compliance guidelines.
