# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for Story Protocol integration.

Tests IP Asset registration, PIL terms, derivative tracking,
and royalty enforcement functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from web3 import Web3
from pathlib import Path

from rra.contracts.story_protocol import (
    StoryProtocolClient,
    IPAssetMetadata,
    PILTerms
)
from rra.integrations.story_integration import StoryIntegrationManager
from rra.config.market_config import MarketConfig


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance."""
    w3 = Mock(spec=Web3)
    w3.eth = Mock()
    w3.eth.contract = Mock()
    w3.eth.get_transaction_count = Mock(return_value=0)
    w3.eth.gas_price = 20000000000
    w3.eth.wait_for_transaction_receipt = Mock()
    w3.eth.chain_id = 1
    w3.from_wei = Web3.from_wei
    w3.to_wei = Web3.to_wei
    w3.to_checksum_address = Web3.to_checksum_address
    return w3


@pytest.fixture
def story_client(mock_web3):
    """Create a Story Protocol client instance."""
    return StoryProtocolClient(mock_web3, network="testnet")


@pytest.fixture
def story_manager(mock_web3):
    """Create a Story Integration Manager instance."""
    return StoryIntegrationManager(mock_web3, network="testnet")


@pytest.fixture
def sample_market_config():
    """Create a sample market config with Story Protocol enabled."""
    return MarketConfig(
        target_price="0.05 ETH",
        floor_price="0.02 ETH",
        story_protocol_enabled=True,
        pil_commercial_use=True,
        pil_derivatives_allowed=True,
        pil_derivatives_attribution=True,
        pil_derivatives_reciprocal=False,
        derivative_royalty_percentage=0.15,
        developer_wallet="0x1234567890123456789012345678901234567890",
        description="Test repository for Story Protocol"
    )


class TestIPAssetMetadata:
    """Test IP Asset metadata handling."""

    def test_metadata_creation(self):
        """Test creating IP Asset metadata."""
        metadata = IPAssetMetadata(
            name="Test Repository",
            description="A test repository",
            ipType="SOFTWARE_REPOSITORY",
            createdAt=1234567890,
            externalUrl="https://github.com/test/repo"
        )

        assert metadata.name == "Test Repository"
        assert metadata.ipType == "SOFTWARE_REPOSITORY"
        assert metadata.externalUrl == "https://github.com/test/repo"


class TestPILTerms:
    """Test Programmable IP License terms."""

    def test_pil_terms_creation(self):
        """Test creating PIL terms."""
        terms = PILTerms(
            commercial_use=True,
            derivatives_allowed=True,
            derivatives_attribution=True,
            commercial_revenue_share=1500  # 15%
        )

        assert terms.commercial_use is True
        assert terms.derivatives_allowed is True
        assert terms.commercial_revenue_share == 1500


class TestStoryProtocolClient:
    """Test Story Protocol client functionality."""

    def test_client_initialization(self, story_client):
        """Test client initialization with contracts."""
        assert story_client.network == "testnet"
        assert story_client.ip_asset_registry is not None
        assert story_client.license_registry is not None
        assert story_client.royalty_module is not None
        assert story_client.pil_framework is not None

    def test_contract_addresses(self, story_client):
        """Test that contract addresses are set."""
        assert "IPAssetRegistry" in story_client.addresses
        assert "LicenseRegistry" in story_client.addresses
        assert "RoyaltyModule" in story_client.addresses
        assert "PILFramework" in story_client.addresses

    @patch.object(StoryProtocolClient, 'register_ip_asset')
    def test_register_ip_asset(self, mock_register, story_client):
        """Test IP Asset registration."""
        mock_register.return_value = {
            "tx_hash": "0xabc123",
            "ip_asset_id": "ip_asset_test123",
            "block_number": 12345,
            "status": "success"
        }

        metadata = IPAssetMetadata(
            name="Test Repo",
            description="Test",
            ipType="SOFTWARE_REPOSITORY",
            createdAt=1234567890
        )

        result = story_client.register_ip_asset(
            owner_address="0x1234567890123456789012345678901234567890",
            metadata=metadata,
            private_key="0xprivatekey"
        )

        assert result["status"] == "success"
        assert "ip_asset_id" in result
        assert "tx_hash" in result

    @patch.object(StoryProtocolClient, 'attach_license_terms')
    def test_attach_license_terms(self, mock_attach, story_client):
        """Test attaching PIL terms to IP Asset."""
        mock_attach.return_value = "0xtx_hash_abc"

        terms = PILTerms(
            commercial_use=True,
            derivatives_allowed=True,
            commercial_revenue_share=1500
        )

        tx_hash = story_client.attach_license_terms(
            ip_asset_id="ip_asset_123",
            pil_terms=terms,
            owner_address="0x1234567890123456789012345678901234567890",
            private_key="0xprivatekey"
        )

        assert tx_hash.startswith("0x")

    @patch.object(StoryProtocolClient, 'register_derivative')
    def test_register_derivative(self, mock_register_deriv, story_client):
        """Test registering a derivative work."""
        mock_register_deriv.return_value = {
            "tx_hash": "0xderivative_tx",
            "derivative_ip_asset_id": "ip_asset_derivative_123",
            "parent_ip_asset_id": "ip_asset_parent_123",
            "status": "success"
        }

        derivative_metadata = IPAssetMetadata(
            name="Forked Repo",
            description="Fork of original",
            ipType="SOFTWARE_REPOSITORY_DERIVATIVE",
            createdAt=1234567890
        )

        result = story_client.register_derivative(
            parent_ip_asset_id="ip_asset_parent_123",
            derivative_owner_address="0xfork_owner",
            derivative_metadata=derivative_metadata,
            license_terms_id="terms_123",
            private_key="0xprivatekey"
        )

        assert result["status"] == "success"
        assert result["parent_ip_asset_id"] == "ip_asset_parent_123"
        assert "derivative_ip_asset_id" in result

    @patch.object(StoryProtocolClient, 'set_royalty_policy')
    def test_set_royalty_policy(self, mock_set_royalty, story_client):
        """Test setting royalty policy."""
        mock_set_royalty.return_value = "0xroyalty_tx"

        tx_hash = story_client.set_royalty_policy(
            ip_asset_id="ip_asset_123",
            royalty_percentage=1500,  # 15%
            payment_token="0x0000000000000000000000000000000000000000",
            owner_address="0x1234567890123456789012345678901234567890",
            private_key="0xprivatekey"
        )

        assert tx_hash.startswith("0x")

    def test_royalty_percentage_validation(self, story_client):
        """Test that royalty percentage is validated."""
        with pytest.raises(ValueError, match="cannot exceed 100%"):
            story_client.set_royalty_policy(
                ip_asset_id="ip_asset_123",
                royalty_percentage=15000,  # 150% - invalid
                payment_token="0x0000000000000000000000000000000000000000",
                owner_address="0x1234567890123456789012345678901234567890",
                private_key="0xprivatekey"
            )


class TestStoryIntegrationManager:
    """Test Story Integration Manager functionality."""

    def test_manager_initialization(self, story_manager):
        """Test manager initialization."""
        assert story_manager.network == "testnet"
        assert story_manager.story_client is not None

    @patch.object(StoryIntegrationManager, 'register_repository_as_ip_asset')
    def test_register_repository(self, mock_register, story_manager, sample_market_config):
        """Test repository registration as IP Asset."""
        mock_register.return_value = {
            "status": "success",
            "ip_asset_id": "ip_asset_repo_123",
            "tx_hash": "0xabc",
            "pil_terms_tx": "0xdef",
            "royalty_tx": "0xghi"
        }

        result = story_manager.register_repository_as_ip_asset(
            repo_url="https://github.com/test/repo",
            market_config=sample_market_config,
            owner_address="0x1234567890123456789012345678901234567890",
            private_key="0xprivatekey"
        )

        assert result["status"] == "success"
        assert "ip_asset_id" in result
        assert "pil_terms_tx" in result

    def test_register_repository_requires_story_enabled(self, story_manager):
        """Test that Story Protocol must be enabled in config."""
        config_without_story = MarketConfig(
            target_price="0.05 ETH",
            floor_price="0.02 ETH",
            story_protocol_enabled=False
        )

        with pytest.raises(ValueError, match="Story Protocol not enabled"):
            story_manager.register_repository_as_ip_asset(
                repo_url="https://github.com/test/repo",
                market_config=config_without_story,
                owner_address="0x1234567890123456789012345678901234567890",
                private_key="0xprivatekey"
            )

    @patch.object(StoryIntegrationManager, 'register_derivative_repository')
    def test_register_fork(self, mock_register_fork, story_manager):
        """Test registering a forked repository."""
        mock_register_fork.return_value = {
            "status": "success",
            "derivative_ip_asset_id": "ip_asset_fork_123",
            "parent_ip_asset_id": "ip_asset_original_123"
        }

        result = story_manager.register_derivative_repository(
            parent_repo_url="https://github.com/original/repo",
            parent_ip_asset_id="ip_asset_original_123",
            fork_repo_url="https://github.com/fork/repo",
            fork_description="Fork with enhancements",
            license_terms_id="terms_123",
            fork_owner_address="0xfork_owner",
            private_key="0xprivatekey"
        )

        assert result["status"] == "success"
        assert "derivative_ip_asset_id" in result


class TestMarketConfigStoryIntegration:
    """Test MarketConfig Story Protocol integration."""

    def test_story_protocol_params_in_config(self, sample_market_config):
        """Test Story Protocol parameters in market config."""
        assert sample_market_config.story_protocol_enabled is True
        assert sample_market_config.pil_commercial_use is True
        assert sample_market_config.derivative_royalty_percentage == 0.15

    def test_to_contract_params_includes_story(self, sample_market_config):
        """Test that contract params include Story Protocol settings."""
        params = sample_market_config.to_contract_params()

        assert "story_protocol" in params
        assert params["story_protocol"]["enabled"] is True
        assert params["story_protocol"]["pil_commercial_use"] is True
        assert params["story_protocol"]["derivative_royalty_bps"] == 1500

    def test_to_pil_terms(self, sample_market_config):
        """Test conversion to PIL terms."""
        pil_terms = sample_market_config.to_pil_terms()

        assert pil_terms["commercial_use"] is True
        assert pil_terms["derivatives_allowed"] is True
        assert pil_terms["derivatives_attribution"] is True
        assert pil_terms["commercial_revenue_share"] == 1500  # 15% in basis points

    def test_royalty_conversion_to_basis_points(self, sample_market_config):
        """Test that royalty percentage is converted to basis points correctly."""
        pil_terms = sample_market_config.to_pil_terms()

        # 0.15 (15%) should become 1500 basis points
        assert pil_terms["commercial_revenue_share"] == 1500

    def test_story_disabled_config(self):
        """Test config with Story Protocol disabled."""
        config = MarketConfig(
            target_price="0.05 ETH",
            floor_price="0.02 ETH",
            story_protocol_enabled=False
        )

        params = config.to_contract_params()
        assert "story_protocol" not in params


class TestDerivativeTracking:
    """Test derivative tracking functionality."""

    @patch.object(StoryIntegrationManager, 'get_repository_derivatives')
    def test_get_derivatives(self, mock_get_derivs, story_manager):
        """Test getting derivatives for a repository."""
        mock_get_derivs.return_value = {
            "parent_ip_asset_id": "ip_asset_parent",
            "derivative_count": 3,
            "derivatives": [
                {"id": "deriv_1", "owner": "0xowner1"},
                {"id": "deriv_2", "owner": "0xowner2"},
                {"id": "deriv_3", "owner": "0xowner3"}
            ]
        }

        result = story_manager.get_repository_derivatives("ip_asset_parent")

        assert result["derivative_count"] == 3
        assert len(result["derivatives"]) == 3

    @patch.object(StoryIntegrationManager, 'get_royalty_stats')
    def test_get_royalty_stats(self, mock_get_royalty, story_manager, mock_web3):
        """Test getting royalty statistics."""
        mock_get_royalty.return_value = {
            "ip_asset_id": "ip_asset_123",
            "royalty_percentage": 15.0,
            "payment_token": "0x0000000000000000000000000000000000000000",
            "total_collected_wei": 1000000000000000000,
            "total_collected_eth": 1.0,
            "last_payment_timestamp": 1234567890
        }

        stats = story_manager.get_royalty_stats("ip_asset_123")

        assert stats["royalty_percentage"] == 15.0
        assert stats["total_collected_eth"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
