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

from rra.integration.boundary_daemon import (
    BoundaryDaemon,
    Permission,
    ResourceType,
    AccessPolicy,
    Principal,
    AccessToken,
    BoundaryMode,
    BoundaryEvent,
    EventSeverity,
    ModeConstraints,
    DaemonConnection,
    EventSigner,
    create_boundary_daemon,
    create_connected_boundary_daemon,
)

from rra.integration.boundary_siem import (
    BoundarySIEMClient,
    SIEMConfig,
    SIEMProtocol,
    SIEMAlert,
    AlertSeverity,
    AlertStatus,
    DetectionRule,
    RRA_DETECTION_RULES,
    create_siem_client,
    create_siem_event_callback,
)

from rra.integration.synth_mind import (
    SynthMindRouter,
    ModelConfig,
    ModelProvider,
    ModelCapability,
    LLMRequest,
    LLMResponse,
    RequestPriority,
    create_synth_mind_router,
)

from rra.integration.agent_os import (
    AgentOSRuntime,
    AgentInstance,
    AgentConfig,
    AgentStatus,
    AgentType,
    RuntimeNode,
    ResourceAllocation,
    ResourceTier,
    create_agent_os_runtime,
)

__all__ = [
    # Base
    "BaseAgent",
    "IntegrationMode",
    "IntegrationConfig",
    "get_integration_mode",
    # Boundary Daemon
    "BoundaryDaemon",
    "Permission",
    "ResourceType",
    "AccessPolicy",
    "Principal",
    "AccessToken",
    "BoundaryMode",
    "BoundaryEvent",
    "EventSeverity",
    "ModeConstraints",
    "DaemonConnection",
    "EventSigner",
    "create_boundary_daemon",
    "create_connected_boundary_daemon",
    # Boundary SIEM
    "BoundarySIEMClient",
    "SIEMConfig",
    "SIEMProtocol",
    "SIEMAlert",
    "AlertSeverity",
    "AlertStatus",
    "DetectionRule",
    "RRA_DETECTION_RULES",
    "create_siem_client",
    "create_siem_event_callback",
    # Synth Mind
    "SynthMindRouter",
    "ModelConfig",
    "ModelProvider",
    "ModelCapability",
    "LLMRequest",
    "LLMResponse",
    "RequestPriority",
    "create_synth_mind_router",
    # Agent OS
    "AgentOSRuntime",
    "AgentInstance",
    "AgentConfig",
    "AgentStatus",
    "AgentType",
    "RuntimeNode",
    "ResourceAllocation",
    "ResourceTier",
    "create_agent_os_runtime",
]
