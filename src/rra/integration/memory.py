# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Integration with memory-vault for persistent state storage.

Provides state persistence for agents when running in integrated mode.
Falls back to local file storage in standalone mode.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)

from rra.integration.base import AgentStateProtocol
from rra.integration.config import get_integration_config


class LocalStateManager:
    """
    Local file-based state manager (standalone fallback).

    Stores agent state in local JSON files when memory-vault is unavailable.
    """

    def __init__(self, agent_id: str, storage_dir: Optional[Path] = None):
        """
        Initialize local state manager.

        Args:
            agent_id: Unique agent identifier
            storage_dir: Directory for state files (default: ./agent_states)
        """
        self.agent_id = agent_id
        self.storage_dir = storage_dir or Path("./agent_states")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.storage_dir / f"{agent_id}.json"

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save agent state to local file."""
        state_with_metadata = {
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "state": state,
        }

        with open(self.state_file, "w") as f:
            json.dump(state_with_metadata, f, indent=2)

    def load_state(self) -> Dict[str, Any]:
        """Load agent state from local file."""
        if not self.state_file.exists():
            return {}

        with open(self.state_file, "r") as f:
            data = json.load(f)

        return data.get("state", {})

    def clear_state(self) -> None:
        """Clear agent state."""
        if self.state_file.exists():
            self.state_file.unlink()


class MemoryVaultStateManager:
    """
    Integration with memory-vault service for distributed state storage.

    Uses memory-vault when available for multi-instance agent deployments.
    """

    def __init__(self, agent_id: str, vault_url: Optional[str] = None):
        """
        Initialize memory-vault state manager.

        Args:
            agent_id: Unique agent identifier
            vault_url: URL of memory-vault service
        """
        self.agent_id = agent_id
        self.vault_url = vault_url or get_integration_config().memory_vault_url

        # Try to import memory-vault client
        try:
            from memory_vault import VaultClient  # type: ignore

            self.client = VaultClient(url=self.vault_url)
            self.available = True
        except ImportError:
            self.available = False
            # Fall back to local storage
            self._fallback = LocalStateManager(agent_id)

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save agent state to memory-vault."""
        if not self.available:
            self._fallback.save_state(state)
            return

        try:
            self.client.store(
                key=f"agent_state:{self.agent_id}",
                value=state,
                metadata={
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat(),
                    "type": "rra_agent_state",
                },
            )
        except Exception as e:
            # Fall back to local storage on error
            logger.warning(f"Failed to save to memory-vault: {e}")
            if not hasattr(self, "_fallback"):
                self._fallback = LocalStateManager(self.agent_id)
            self._fallback.save_state(state)

    def load_state(self) -> Dict[str, Any]:
        """Load agent state from memory-vault."""
        if not self.available:
            return self._fallback.load_state()

        try:
            result = self.client.retrieve(f"agent_state:{self.agent_id}")
            return result.get("value", {}) if result else {}
        except Exception as e:
            logger.warning(f"Failed to load from memory-vault: {e}")
            if not hasattr(self, "_fallback"):
                self._fallback = LocalStateManager(self.agent_id)
            return self._fallback.load_state()

    def clear_state(self) -> None:
        """Clear agent state from memory-vault."""
        if not self.available:
            self._fallback.clear_state()
            return

        try:
            self.client.delete(f"agent_state:{self.agent_id}")
        except Exception:
            pass


def get_state_manager(agent_id: str, prefer_vault: bool = True) -> AgentStateProtocol:
    """
    Get appropriate state manager based on configuration and availability.

    Args:
        agent_id: Unique agent identifier
        prefer_vault: Prefer memory-vault if available

    Returns:
        State manager instance (MemoryVault or Local)
    """
    config = get_integration_config()

    # Check if memory-vault is enabled and should be used
    if config.enable_memory_vault and prefer_vault:
        manager = MemoryVaultStateManager(agent_id, config.memory_vault_url)
        if manager.available:
            return manager

    # Fall back to local storage
    return LocalStateManager(agent_id)
