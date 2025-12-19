# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Base interfaces and protocols for NatLangChain integration.

Defines the core abstractions that allow RRA agents to work both
standalone and integrated with the NatLangChain ecosystem.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, Protocol
from datetime import datetime


class IntegrationMode(str, Enum):
    """Operating mode for RRA agents."""
    STANDALONE = "standalone"  # No ecosystem integration
    INTEGRATED = "integrated"  # Full NatLangChain ecosystem integration
    HYBRID = "hybrid"  # Selective integration based on available components


def get_integration_mode() -> IntegrationMode:
    """
    Detect the current integration mode based on available packages.

    Returns:
        IntegrationMode.INTEGRATED if natlangchain packages are available,
        IntegrationMode.STANDALONE otherwise.
    """
    try:
        # Try importing common base - if available, we're in integrated mode
        import natlangchain.common  # type: ignore
        return IntegrationMode.INTEGRATED
    except ImportError:
        pass

    # Check if any individual components are available
    available_components = []
    components = [
        "agent_os",
        "memory_vault",
        "value_ledger",
        "mediator_node",
        "intent_log",
        "synth_mind",
    ]

    for component in components:
        try:
            __import__(f"natlangchain.{component}")
            available_components.append(component)
        except ImportError:
            pass

    if available_components:
        return IntegrationMode.HYBRID

    return IntegrationMode.STANDALONE


class AgentStateProtocol(Protocol):
    """Protocol for agent state management."""

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save agent state."""
        ...

    def load_state(self) -> Dict[str, Any]:
        """Load agent state."""
        ...

    def clear_state(self) -> None:
        """Clear agent state."""
        ...


class MessageRouterProtocol(Protocol):
    """Protocol for agent message routing."""

    def send_message(self, to_agent: str, message: Dict[str, Any]) -> None:
        """Send a message to another agent."""
        ...

    def receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive a message from another agent."""
        ...


class IntentLoggerProtocol(Protocol):
    """Protocol for logging agent intents and decisions."""

    def log_intent(self, intent: str, context: Dict[str, Any]) -> None:
        """Log an agent intent."""
        ...

    def log_decision(self, decision: str, rationale: Dict[str, Any]) -> None:
        """Log an agent decision."""
        ...


class BaseAgent(ABC):
    """
    Base agent interface for NatLangChain ecosystem.

    This provides the common interface that all RRA agents implement,
    allowing them to work both standalone and integrated with the ecosystem.

    Attributes:
        agent_id: Unique identifier for this agent
        mode: Current integration mode
        state_manager: Optional state persistence (integrated mode)
        message_router: Optional message routing (integrated mode)
        intent_logger: Optional intent logging (integrated mode)
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        mode: Optional[IntegrationMode] = None,
    ):
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier for this agent
            mode: Integration mode (auto-detected if not specified)
        """
        self.agent_id = agent_id or self._generate_agent_id()
        self.mode = mode or get_integration_mode()

        # Integration components (None in standalone mode)
        self.state_manager: Optional[AgentStateProtocol] = None
        self.message_router: Optional[MessageRouterProtocol] = None
        self.intent_logger: Optional[IntentLoggerProtocol] = None

        # Initialize integrations if available
        if self.mode != IntegrationMode.STANDALONE:
            self._initialize_integrations()

    def _generate_agent_id(self) -> str:
        """Generate a unique agent ID."""
        from uuid import uuid4
        return f"rra-{uuid4().hex[:12]}"

    def _initialize_integrations(self) -> None:
        """Initialize ecosystem integrations if available."""
        # Import integration modules dynamically
        try:
            from rra.integration.memory import get_state_manager
            self.state_manager = get_state_manager(self.agent_id)
        except (ImportError, Exception):
            pass

        try:
            from rra.integration.mediator import get_message_router
            self.message_router = get_message_router(self.agent_id)
        except (ImportError, Exception):
            pass

        try:
            from rra.integration.intent_log import get_intent_logger
            self.intent_logger = get_intent_logger(self.agent_id)
        except (ImportError, Exception):
            pass

    @abstractmethod
    def process_message(self, message: str) -> str:
        """
        Process an incoming message and generate a response.

        Args:
            message: Incoming message

        Returns:
            Response message
        """
        pass

    def log_intent(self, intent: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an agent intent (integrated mode only).

        Args:
            intent: Description of the intent
            context: Additional context
        """
        if self.intent_logger:
            self.intent_logger.log_intent(intent, context or {})

    def log_decision(self, decision: str, rationale: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an agent decision (integrated mode only).

        Args:
            decision: Description of the decision
            rationale: Reasoning behind the decision
        """
        if self.intent_logger:
            self.intent_logger.log_decision(decision, rationale or {})

    def save_state(self) -> None:
        """Save agent state to persistent storage (integrated mode only)."""
        if self.state_manager:
            state = self.get_state()
            self.state_manager.save_state(state)

    def load_state(self) -> None:
        """Load agent state from persistent storage (integrated mode only)."""
        if self.state_manager:
            state = self.state_manager.load_state()
            self.restore_state(state)

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        Get current agent state for persistence.

        Returns:
            Dictionary containing agent state
        """
        pass

    @abstractmethod
    def restore_state(self, state: Dict[str, Any]) -> None:
        """
        Restore agent state from dictionary.

        Args:
            state: Previously saved state
        """
        pass

    def is_integrated(self) -> bool:
        """Check if running in integrated mode."""
        return self.mode != IntegrationMode.STANDALONE

    def get_integration_status(self) -> Dict[str, Any]:
        """
        Get status of ecosystem integrations.

        Returns:
            Dictionary showing which integrations are active
        """
        return {
            "mode": self.mode.value,
            "agent_id": self.agent_id,
            "integrations": {
                "state_persistence": self.state_manager is not None,
                "message_routing": self.message_router is not None,
                "intent_logging": self.intent_logger is not None,
            }
        }
