# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Integration with mediator-node for agent-to-agent message routing.

Enables RRA agents to communicate with other agents in the NatLangChain
ecosystem through the mediator network.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from collections import deque

from rra.integration.base import MessageRouterProtocol
from rra.integration.config import get_integration_config


class LocalMessageRouter:
    """
    Local in-memory message router (standalone fallback).

    Simulates message routing for testing and standalone deployments.
    """

    # Class-level message queue for local routing
    _message_queues: Dict[str, deque] = {}

    def __init__(self, agent_id: str):
        """
        Initialize local message router.

        Args:
            agent_id: Unique agent identifier
        """
        self.agent_id = agent_id

        # Initialize queue for this agent
        if agent_id not in self._message_queues:
            self._message_queues[agent_id] = deque(maxlen=100)

    def send_message(self, to_agent: str, message: Dict[str, Any]) -> None:
        """Send a message to another agent (local queue)."""
        envelope = {
            "from": self.agent_id,
            "to": to_agent,
            "timestamp": datetime.now().isoformat(),
            "message": message
        }

        # Add to recipient's queue
        if to_agent not in self._message_queues:
            self._message_queues[to_agent] = deque(maxlen=100)

        self._message_queues[to_agent].append(envelope)

    def receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive next message from queue."""
        queue = self._message_queues.get(self.agent_id, deque())

        if queue:
            return queue.popleft()

        return None

    def peek_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """Peek at next messages without removing them."""
        queue = self._message_queues.get(self.agent_id, deque())
        return list(queue)[:count]


class MediatorNodeRouter:
    """
    Integration with mediator-node service for distributed routing.

    Uses mediator-node when available for cross-network agent communication.
    """

    def __init__(self, agent_id: str, mediator_url: Optional[str] = None):
        """
        Initialize mediator-node router.

        Args:
            agent_id: Unique agent identifier
            mediator_url: URL of mediator-node service
        """
        self.agent_id = agent_id
        self.mediator_url = mediator_url or get_integration_config().mediator_node_url

        # Try to import mediator-node client
        try:
            from mediator_node import MediatorClient  # type: ignore
            self.client = MediatorClient(url=self.mediator_url, agent_id=agent_id)
            self.available = True
        except ImportError:
            self.available = False
            self._fallback = LocalMessageRouter(agent_id)

    def send_message(self, to_agent: str, message: Dict[str, Any]) -> None:
        """Send a message through mediator-node."""
        if not self.available:
            self._fallback.send_message(to_agent, message)
            return

        try:
            self.client.route_message(
                to_agent=to_agent,
                message=message,
                priority="normal"
            )
        except Exception as e:
            print(f"Warning: Failed to send via mediator-node: {e}")
            if not hasattr(self, '_fallback'):
                self._fallback = LocalMessageRouter(self.agent_id)
            self._fallback.send_message(to_agent, message)

    def receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive next message from mediator-node."""
        if not self.available:
            return self._fallback.receive_message()

        try:
            return self.client.poll_message(timeout=0)
        except Exception as e:
            print(f"Warning: Failed to receive from mediator-node: {e}")
            if not hasattr(self, '_fallback'):
                self._fallback = LocalMessageRouter(self.agent_id)
            return self._fallback.receive_message()


def get_message_router(
    agent_id: str,
    prefer_mediator: bool = True
) -> MessageRouterProtocol:
    """
    Get appropriate message router based on configuration.

    Args:
        agent_id: Unique agent identifier
        prefer_mediator: Prefer mediator-node if available

    Returns:
        Message router instance (MediatorNode or Local)
    """
    config = get_integration_config()

    if config.enable_mediator_node and prefer_mediator:
        router = MediatorNodeRouter(agent_id, config.mediator_node_url)
        if router.available:
            return router

    return LocalMessageRouter(agent_id)
