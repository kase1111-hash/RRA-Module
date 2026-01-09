# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for market configuration module."""

import pytest
from pathlib import Path
import tempfile

from rra.config.market_config import (
    MarketConfig,
    LicenseModel,
    NegotiationStyle,
    create_default_config,
)


def test_market_config_creation():
    """Test creating a market configuration."""
    config = MarketConfig(
        target_price="0.05 ETH",
        floor_price="0.02 ETH",
        license_model=LicenseModel.PER_SEAT,
        negotiation_style=NegotiationStyle.CONCISE,
    )

    assert config.target_price == "0.05 ETH"
    assert config.floor_price == "0.02 ETH"
    assert config.license_model == LicenseModel.PER_SEAT
    assert config.negotiation_style == NegotiationStyle.CONCISE


def test_price_validation():
    """Test price format validation."""
    # Valid prices
    config = MarketConfig(target_price="0.05 ETH", floor_price="0.02 ETH")
    assert config.target_price == "0.05 ETH"

    # Invalid format should raise error
    with pytest.raises(ValueError):
        MarketConfig(target_price="invalid", floor_price="0.02 ETH")

    # Negative price should raise error
    with pytest.raises(ValueError):
        MarketConfig(target_price="-0.05 ETH", floor_price="0.02 ETH")


def test_config_to_yaml():
    """Test saving configuration to YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = MarketConfig(
            target_price="0.05 ETH",
            floor_price="0.02 ETH",
            license_model=LicenseModel.SUBSCRIPTION,
        )

        file_path = Path(tmpdir) / "test.yaml"
        config.to_yaml(file_path)

        assert file_path.exists()

        # Load it back
        loaded_config = MarketConfig.from_yaml(file_path)
        assert loaded_config.target_price == config.target_price
        assert loaded_config.floor_price == config.floor_price
        assert loaded_config.license_model == config.license_model


def test_config_from_yaml():
    """Test loading configuration from YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / ".market.yaml"

        # Create a YAML file
        yaml_content = """
target_price: "0.1 ETH"
floor_price: "0.05 ETH"
license_model: "perpetual"
negotiation_style: "persuasive"
allow_custom_fork_rights: true
"""
        with open(file_path, "w") as f:
            f.write(yaml_content)

        config = MarketConfig.from_yaml(file_path)

        assert config.target_price == "0.1 ETH"
        assert config.floor_price == "0.05 ETH"
        assert config.license_model == LicenseModel.PERPETUAL
        assert config.negotiation_style == NegotiationStyle.PERSUASIVE
        assert config.allow_custom_fork_rights is True


def test_config_to_contract_params():
    """Test converting config to smart contract parameters."""
    config = MarketConfig(
        target_price="0.05 ETH",
        floor_price="0.02 ETH",
        license_model=LicenseModel.PER_SEAT,
        royalty_on_derivatives=0.15,
        developer_wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    )

    params = config.to_contract_params()

    assert params["license_model"] == "per-seat"
    assert params["target_price_wei"] > 0
    assert params["floor_price_wei"] > 0
    assert params["royalty_rate"] == 1500  # 15% in basis points
    assert params["developer_address"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


def test_create_default_config():
    """Test creating default configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        config = create_default_config(repo_path)

        assert config.target_price == "0.05 ETH"
        assert config.floor_price == "0.02 ETH"
        assert config.license_model == LicenseModel.PER_SEAT

        # Should have created file
        config_file = repo_path / ".market.yaml"
        assert config_file.exists()
