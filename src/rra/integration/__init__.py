# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Integration layer for NatLangChain ecosystem.

This module provides optional integrations with NatLangChain components:
- Agent-OS: Agent runtime and lifecycle management
- memory-vault: Persistent storage for agent state
- value-ledger: Transaction and revenue tracking
- mediator-node: Agent-to-agent communication routing
- IntentLog: Agent intent and decision logging
- synth-mind: LLM integration layer
- boundary-daemon: Permission and access control
- learning-contracts: Adaptive smart contracts
- common: Shared interfaces and utilities

Usage:
    The RRA module works standalone by default. Ecosystem integrations
    are activated automatically when the respective packages are installed:

    # Standalone mode (default)
    from rra.agents.negotiator import NegotiatorAgent
    agent = NegotiatorAgent(kb)

    # Integrated mode (when natlangchain is installed)
    from rra.agents.negotiator import NegotiatorAgent
    agent = NegotiatorAgent(kb, integrated=True)
    # Automatically uses Agent-OS, memory-vault, etc.

Installation:
    # Standalone
    pip install rra-module

    # With NatLangChain ecosystem
    pip install rra-module[natlangchain]
"""

from rra.integration.base import BaseAgent, IntegrationMode, get_integration_mode
from rra.integration.config import IntegrationConfig

__all__ = [
    "BaseAgent",
    "IntegrationMode",
    "IntegrationConfig",
    "get_integration_mode",
]
