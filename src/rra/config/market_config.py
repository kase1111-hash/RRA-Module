# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Market configuration parser and validator for .market.yaml files.

This module handles the parsing and validation of developer intent
captured in .market.yaml configuration files.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field, validator


class LicenseModel(str, Enum):
    """Supported license models for code monetization."""
    PER_SEAT = "per-seat"
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one-time"
    PERPETUAL = "perpetual"
    CUSTOM = "custom"


class NegotiationStyle(str, Enum):
    """Negotiation styles for the agent."""
    CONCISE = "concise"
    PERSUASIVE = "persuasive"
    STRICT = "strict"
    ADAPTIVE = "adaptive"


class UpdateFrequency(str, Enum):
    """Update frequency for repo monitoring."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_PUSH = "on-push"


class MarketConfig(BaseModel):
    """
    Represents the .market.yaml configuration for a repository.

    This configuration captures developer intent for automated licensing
    and negotiation.
    """

    license_model: LicenseModel = Field(
        default=LicenseModel.PER_SEAT,
        description="Licensing model for the codebase"
    )

    target_price: str = Field(
        ...,
        description="Suggested starting price (e.g., '0.05 ETH', '50 USDC')"
    )

    floor_price: str = Field(
        ...,
        description="Minimum acceptable price"
    )

    negotiation_style: NegotiationStyle = Field(
        default=NegotiationStyle.CONCISE,
        description="Negotiation approach for the agent"
    )

    allow_custom_fork_rights: bool = Field(
        default=False,
        description="Allow buyers to negotiate custom forking permissions"
    )

    update_frequency: UpdateFrequency = Field(
        default=UpdateFrequency.WEEKLY,
        description="How often to poll for repo updates"
    )

    sandbox_tests: Optional[str] = Field(
        default=None,
        description="Path to verification scripts for code quality proofs"
    )

    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the codebase's value proposition"
    )

    features: Optional[list[str]] = Field(
        default_factory=list,
        description="Key features or capabilities to highlight in negotiations"
    )

    min_license_duration: Optional[str] = Field(
        default=None,
        description="Minimum license duration (e.g., '1 month', '1 year')"
    )

    max_seats: Optional[int] = Field(
        default=None,
        description="Maximum seats for per-seat licensing"
    )

    auto_renewal: bool = Field(
        default=False,
        description="Enable automatic license renewal"
    )

    royalty_on_derivatives: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Royalty percentage on derivative works (0.0-1.0)"
    )

    developer_wallet: Optional[str] = Field(
        default=None,
        description="Ethereum wallet address for receiving payments"
    )

    # Story Protocol Integration
    story_protocol_enabled: bool = Field(
        default=False,
        description="Enable Story Protocol for programmable IP licensing"
    )

    ip_asset_id: Optional[str] = Field(
        default=None,
        description="Story Protocol IP Asset ID (auto-generated on registration)"
    )

    pil_commercial_use: bool = Field(
        default=True,
        description="Allow commercial use in PIL terms"
    )

    pil_derivatives_allowed: bool = Field(
        default=True,
        description="Allow derivative works in PIL terms"
    )

    pil_derivatives_attribution: bool = Field(
        default=True,
        description="Require attribution for derivatives in PIL terms"
    )

    pil_derivatives_reciprocal: bool = Field(
        default=False,
        description="Require reciprocal licensing for derivatives (copyleft)"
    )

    derivative_royalty_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Royalty percentage for derivatives via Story Protocol (0.0-1.0)"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom metadata"
    )

    @validator('target_price', 'floor_price')
    def validate_price_format(cls, v):
        """Validate that prices are in acceptable format."""
        # Basic validation - should contain amount and currency
        parts = v.strip().split()
        if len(parts) != 2:
            raise ValueError(
                f"Price must be in format '<amount> <currency>' (e.g., '0.05 ETH')"
            )

        try:
            amount = float(parts[0])
            if amount <= 0:
                raise ValueError("Price amount must be positive")
        except ValueError:
            raise ValueError(f"Invalid price amount: {parts[0]}")

        return v

    @classmethod
    def from_yaml(cls, file_path: Path) -> "MarketConfig":
        """
        Load configuration from a .market.yaml file.

        Args:
            file_path: Path to the .market.yaml file

        Returns:
            MarketConfig instance

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the YAML is invalid or missing required fields
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Market config not found: {file_path}")

        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty or invalid YAML file: {file_path}")

        return cls(**data)

    def to_yaml(self, file_path: Path) -> None:
        """
        Save configuration to a .market.yaml file.

        Args:
            file_path: Path where to save the configuration
        """
        data = self.model_dump(exclude_none=True, mode='json')

        # Convert enum values to strings for clean YAML serialization
        for key, value in data.items():
            if isinstance(value, Enum):
                data[key] = value.value

        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def to_contract_params(self) -> Dict[str, Any]:
        """
        Convert configuration to smart contract parameters.

        Returns:
            Dictionary of parameters suitable for smart contract deployment
        """
        params = {
            "license_model": self.license_model.value,
            "target_price_wei": self._parse_price_to_wei(self.target_price),
            "floor_price_wei": self._parse_price_to_wei(self.floor_price),
            "allow_custom_fork_rights": self.allow_custom_fork_rights,
            "royalty_rate": int((self.royalty_on_derivatives or 0) * 10000),  # Basis points
            "developer_address": self.developer_wallet or "0x0",
            "auto_renewal": self.auto_renewal,
        }

        # Add Story Protocol parameters if enabled
        if self.story_protocol_enabled:
            params["story_protocol"] = {
                "enabled": True,
                "ip_asset_id": self.ip_asset_id,
                "pil_commercial_use": self.pil_commercial_use,
                "pil_derivatives_allowed": self.pil_derivatives_allowed,
                "pil_derivatives_attribution": self.pil_derivatives_attribution,
                "pil_derivatives_reciprocal": self.pil_derivatives_reciprocal,
                "derivative_royalty_bps": int((self.derivative_royalty_percentage or 0) * 10000),
            }

        return params

    def to_pil_terms(self) -> Dict[str, Any]:
        """
        Convert configuration to Story Protocol PIL terms.

        Returns:
            Dictionary of PIL terms for Story Protocol
        """
        royalty_percentage = self.derivative_royalty_percentage or self.royalty_on_derivatives or 0.0

        return {
            "commercial_use": self.pil_commercial_use,
            "derivatives_allowed": self.pil_derivatives_allowed,
            "derivatives_approve": False,  # Auto-approve derivatives
            "derivatives_attribution": self.pil_derivatives_attribution,
            "derivatives_reciprocal": self.pil_derivatives_reciprocal,
            "royalty_policy": "automated",
            "commercial_revenue_share": int(royalty_percentage * 10000),  # Basis points
            "territory_restriction": None,
            "distribution_channels": None,
        }

    @staticmethod
    def _parse_price_to_wei(price_str: str) -> int:
        """
        Parse price string to wei (smallest ETH unit).

        Args:
            price_str: Price string like "0.05 ETH"

        Returns:
            Price in wei
        """
        parts = price_str.strip().split()
        amount = float(parts[0])
        currency = parts[1].upper()

        # For now, assume ETH - in production would handle multiple currencies
        if currency in ["ETH", "ETHER"]:
            return int(amount * 10**18)

        # Default to treating as wei
        return int(amount)


def create_default_config(repo_path: Path) -> MarketConfig:
    """
    Create a default .market.yaml configuration for a repository.

    Args:
        repo_path: Path to the repository

    Returns:
        Default MarketConfig instance
    """
    config = MarketConfig(
        target_price="0.05 ETH",
        floor_price="0.02 ETH",
        license_model=LicenseModel.PER_SEAT,
        negotiation_style=NegotiationStyle.CONCISE,
        allow_custom_fork_rights=True,
        update_frequency=UpdateFrequency.WEEKLY,
        description="Automated licensing for this repository",
        features=["Full source code access", "Updates included", "Developer support"],
    )

    # Save to repo
    config_path = repo_path / ".market.yaml"
    config.to_yaml(config_path)

    return config
