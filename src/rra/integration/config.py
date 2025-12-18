"""
Configuration for NatLangChain ecosystem integrations.

Manages settings and preferences for how RRA integrates with
the broader NatLangChain ecosystem.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
import yaml


class IntegrationConfig(BaseModel):
    """Configuration for ecosystem integrations."""

    # Mode settings
    auto_detect_mode: bool = Field(
        default=True,
        description="Automatically detect and use available integrations"
    )

    force_standalone: bool = Field(
        default=False,
        description="Force standalone mode even if integrations are available"
    )

    # Component-specific settings
    enable_memory_vault: bool = Field(
        default=True,
        description="Enable memory-vault integration for state persistence"
    )

    enable_value_ledger: bool = Field(
        default=True,
        description="Enable value-ledger integration for transaction tracking"
    )

    enable_mediator_node: bool = Field(
        default=True,
        description="Enable mediator-node integration for message routing"
    )

    enable_intent_log: bool = Field(
        default=True,
        description="Enable IntentLog integration for decision auditing"
    )

    enable_agent_os: bool = Field(
        default=True,
        description="Enable Agent-OS integration for runtime management"
    )

    enable_synth_mind: bool = Field(
        default=True,
        description="Enable synth-mind integration for LLM capabilities"
    )

    # Connection settings
    memory_vault_url: Optional[str] = Field(
        default=None,
        description="URL for memory-vault service"
    )

    value_ledger_url: Optional[str] = Field(
        default=None,
        description="URL for value-ledger service"
    )

    mediator_node_url: Optional[str] = Field(
        default=None,
        description="URL for mediator-node service"
    )

    intent_log_url: Optional[str] = Field(
        default=None,
        description="URL for IntentLog service"
    )

    # Agent-OS settings
    agent_os_runtime: str = Field(
        default="local",
        description="Agent-OS runtime environment: local, distributed, cloud"
    )

    # Fallback behavior
    fallback_to_standalone: bool = Field(
        default=True,
        description="Fall back to standalone mode if integrations fail"
    )

    @classmethod
    def from_yaml(cls, file_path: Path) -> "IntegrationConfig":
        """
        Load integration config from YAML file.

        Args:
            file_path: Path to config file

        Returns:
            IntegrationConfig instance
        """
        if not file_path.exists():
            return cls()

        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_yaml(self, file_path: Path) -> None:
        """
        Save integration config to YAML file.

        Args:
            file_path: Path where to save config
        """
        data = self.model_dump(exclude_none=True, mode='json')

        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# Global configuration instance
_config: Optional[IntegrationConfig] = None


def get_integration_config() -> IntegrationConfig:
    """
    Get the global integration configuration.

    Returns:
        IntegrationConfig instance
    """
    global _config
    if _config is None:
        # Try to load from standard locations
        config_paths = [
            Path(".rra-integration.yaml"),
            Path.home() / ".config" / "rra" / "integration.yaml",
            Path("/etc/rra/integration.yaml"),
        ]

        for path in config_paths:
            if path.exists():
                _config = IntegrationConfig.from_yaml(path)
                break

        if _config is None:
            _config = IntegrationConfig()

    return _config


def set_integration_config(config: IntegrationConfig) -> None:
    """
    Set the global integration configuration.

    Args:
        config: IntegrationConfig to use
    """
    global _config
    _config = config
