# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for new features: Multi-chain, Bundling, Adaptive Pricing.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from rra.chains import (
    ChainId,
    ChainManager,
    CHAIN_CONFIGS,
)
from rra.bundling import (
    BundleType,
    DiscountType,
    BundleDiscount,
    BundledRepo,
    RepoBundle,
    BundleManager,
)
from rra.pricing import (
    PricingStrategy,
    AdaptivePricingEngine,
    create_pricing_engine,
)


# =============================================================================
# Multi-Chain Tests
# =============================================================================


class TestChainConfig:
    """Test chain configuration."""

    def test_chain_configs_exist(self):
        """Test that chain configs are defined."""
        assert len(CHAIN_CONFIGS) > 0
        assert ChainId.ETHEREUM_MAINNET.value in CHAIN_CONFIGS
        assert ChainId.POLYGON_MAINNET.value in CHAIN_CONFIGS
        assert ChainId.ARBITRUM_ONE.value in CHAIN_CONFIGS

    def test_chain_config_properties(self):
        """Test chain config properties."""
        eth = CHAIN_CONFIGS[ChainId.ETHEREUM_MAINNET.value]
        assert eth.chain_id == 1
        assert eth.name == "ethereum"
        assert eth.native_currency == "ETH"
        assert not eth.is_testnet
        assert not eth.is_l2

    def test_l2_chains_marked(self):
        """Test that L2 chains are properly marked."""
        polygon = CHAIN_CONFIGS[ChainId.POLYGON_MAINNET.value]
        arbitrum = CHAIN_CONFIGS[ChainId.ARBITRUM_ONE.value]

        assert polygon.is_l2
        assert arbitrum.is_l2

    def test_testnets_marked(self):
        """Test that testnets are properly marked."""
        sepolia = CHAIN_CONFIGS[ChainId.ETHEREUM_SEPOLIA.value]
        mumbai = CHAIN_CONFIGS[ChainId.POLYGON_MUMBAI.value]

        assert sepolia.is_testnet
        assert mumbai.is_testnet

    def test_explorer_urls(self):
        """Test explorer URL generation."""
        eth = CHAIN_CONFIGS[ChainId.ETHEREUM_MAINNET.value]

        tx_url = eth.get_explorer_tx_url("0x123")
        assert "etherscan.io/tx/0x123" in tx_url

        addr_url = eth.get_explorer_address_url("0xabc")
        assert "etherscan.io/address/0xabc" in addr_url


class TestChainManager:
    """Test chain manager."""

    def test_default_chain(self):
        """Test default chain is Ethereum mainnet."""
        manager = ChainManager()
        assert manager.active_chain_id == ChainId.ETHEREUM_MAINNET.value

    def test_set_active_chain(self):
        """Test setting active chain."""
        manager = ChainManager()
        manager.set_active_chain(ChainId.POLYGON_MAINNET.value)
        assert manager.active_chain_id == ChainId.POLYGON_MAINNET.value
        assert manager.active_chain.name == "polygon"

    def test_invalid_chain_id(self):
        """Test error on invalid chain ID."""
        manager = ChainManager()
        with pytest.raises(ValueError):
            manager.set_active_chain(99999)

    def test_get_chain_by_name(self):
        """Test getting chain by name."""
        manager = ChainManager()
        polygon = manager.get_chain_by_name("polygon")
        assert polygon.chain_id == 137

    def test_list_chains(self):
        """Test listing chains."""
        manager = ChainManager()

        all_chains = manager.list_chains(include_testnets=True)
        mainnets_only = manager.list_chains(include_testnets=False)

        assert len(all_chains) > len(mainnets_only)

    def test_list_l2_chains(self):
        """Test listing L2 chains."""
        manager = ChainManager()
        l2s = manager.list_l2_chains()

        assert len(l2s) >= 3  # Polygon, Arbitrum, Base at minimum
        for chain in l2s:
            assert chain.is_l2
            assert not chain.is_testnet

    def test_get_cheapest_chain(self):
        """Test finding cheapest chain."""
        manager = ChainManager()
        cheapest = manager.get_cheapest_chain()

        # Should be an L2
        assert cheapest.is_l2

    def test_register_contract(self):
        """Test contract registration."""
        manager = ChainManager()
        manager.register_contract(137, "TestContract", "0x123")

        addr = manager.get_contract_address(137, "TestContract")
        assert addr == "0x123"

    def test_get_recommended_chain(self):
        """Test chain recommendations."""
        manager = ChainManager()

        streaming = manager.get_recommended_chain("streaming")
        assert streaming.superfluid_addresses  # Has Superfluid

        high_vol = manager.get_recommended_chain("high_volume")
        assert high_vol.is_l2  # Should be L2 for cost

    def test_estimate_gas_cost(self):
        """Test gas cost estimation."""
        manager = ChainManager()
        cost = manager.estimate_gas_cost_usd(chain_id=137, gas_units=100000, native_price_usd=0.80)
        assert cost > 0
        assert cost < 100  # Should be reasonable


# =============================================================================
# Bundling Tests
# =============================================================================


class TestBundleDiscount:
    """Test bundle discount calculations."""

    def test_percentage_discount(self):
        """Test percentage-based discount."""
        discount = BundleDiscount(
            discount_type=DiscountType.PERCENTAGE,
            value=20.0,
        )
        result = discount.calculate_discount(100.0, 3)
        assert result == 20.0

    def test_fixed_discount(self):
        """Test fixed discount."""
        discount = BundleDiscount(
            discount_type=DiscountType.FIXED,
            value=25.0,
        )
        result = discount.calculate_discount(100.0, 3)
        assert result == 25.0

    def test_per_repo_discount(self):
        """Test per-repo discount."""
        discount = BundleDiscount(
            discount_type=DiscountType.PER_REPO,
            value=10.0,
        )
        # 3 repos, $10 off for each after first = $20
        result = discount.calculate_discount(100.0, 3)
        assert result == 20.0

    def test_tiered_discount(self):
        """Test tiered discount."""
        discount = BundleDiscount(
            discount_type=DiscountType.TIERED,
            value=0,  # Not used for tiered
        )
        # 4 repos = 20% discount (10 + 5*2)
        result = discount.calculate_discount(100.0, 4)
        assert result == 20.0

    def test_min_repos_requirement(self):
        """Test minimum repos requirement."""
        discount = BundleDiscount(
            discount_type=DiscountType.PERCENTAGE,
            value=20.0,
            min_repos=3,
        )
        # Only 2 repos - no discount
        result = discount.calculate_discount(100.0, 2)
        assert result == 0.0

    def test_max_discount_cap(self):
        """Test maximum discount cap."""
        discount = BundleDiscount(
            discount_type=DiscountType.PERCENTAGE,
            value=80.0,  # 80% requested
            max_discount_percent=50.0,  # Cap at 50%
        )
        result = discount.calculate_discount(100.0, 5)
        assert result == 50.0  # Capped at 50


class TestRepoBundle:
    """Test repository bundle."""

    def test_bundle_creation(self):
        """Test creating a bundle."""
        bundle = RepoBundle(
            bundle_id="test-bundle",
            name="Test Bundle",
            description="A test bundle",
            bundle_type=BundleType.COLLECTION,
            owner_address="0x123",
        )
        assert bundle.bundle_id == "test-bundle"
        assert bundle.repo_count == 0

    def test_add_repos(self):
        """Test adding repos to bundle."""
        bundle = RepoBundle(
            bundle_id="test",
            name="Test",
            description="Test",
            bundle_type=BundleType.COLLECTION,
            owner_address="0x123",
        )

        repo1 = BundledRepo(
            repo_id="repo1",
            repo_url="https://github.com/test/repo1",
            name="Repo 1",
            individual_price=50.0,
        )
        repo2 = BundledRepo(
            repo_id="repo2",
            repo_url="https://github.com/test/repo2",
            name="Repo 2",
            individual_price=30.0,
        )

        bundle.add_repo(repo1)
        bundle.add_repo(repo2)

        assert bundle.repo_count == 2
        assert bundle.total_individual_price == 80.0

    def test_bundle_discount_applied(self):
        """Test discount is applied to bundle."""
        discount = BundleDiscount(
            discount_type=DiscountType.PERCENTAGE,
            value=25.0,
        )

        bundle = RepoBundle(
            bundle_id="test",
            name="Test",
            description="Test",
            bundle_type=BundleType.COLLECTION,
            owner_address="0x123",
            repos=[
                BundledRepo("r1", "url1", "Repo 1", individual_price=40.0),
                BundledRepo("r2", "url2", "Repo 2", individual_price=60.0),
            ],
            discount=discount,
        )

        assert bundle.total_individual_price == 100.0
        assert bundle.bundle_price == 75.0  # 25% off
        assert bundle.savings == 25.0
        assert bundle.savings_percent == 25.0

    def test_bundle_serialization(self):
        """Test bundle to/from dict."""
        bundle = RepoBundle(
            bundle_id="test",
            name="Test Bundle",
            description="Description",
            bundle_type=BundleType.SUITE,
            owner_address="0xabc",
            repos=[
                BundledRepo("r1", "url1", "Repo 1", individual_price=100.0),
            ],
            discount=BundleDiscount(
                discount_type=DiscountType.PERCENTAGE,
                value=15.0,
            ),
            tags=["test", "example"],
        )

        data = bundle.to_dict()
        restored = RepoBundle.from_dict(data)

        assert restored.bundle_id == bundle.bundle_id
        assert restored.name == bundle.name
        assert restored.bundle_type == bundle.bundle_type
        assert restored.repo_count == bundle.repo_count
        assert restored.discount.value == bundle.discount.value


class TestBundleManager:
    """Test bundle manager."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = BundleManager(storage_path=Path(self.temp_dir) / "bundles.json")

    def teardown_method(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_bundle(self):
        """Test creating a bundle."""
        bundle = self.manager.create_bundle(
            name="My Bundle",
            description="A bundle",
            bundle_type=BundleType.PORTFOLIO,
            owner_address="0x123",
        )

        assert bundle.bundle_id.startswith("bnd_")
        assert bundle.name == "My Bundle"

    def test_get_bundle(self):
        """Test retrieving a bundle."""
        created = self.manager.create_bundle(
            name="Test",
            description="Test",
            bundle_type=BundleType.COLLECTION,
            owner_address="0x123",
        )

        retrieved = self.manager.get_bundle(created.bundle_id)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_list_bundles(self):
        """Test listing bundles."""
        self.manager.create_bundle(
            name="Bundle 1",
            description="First",
            bundle_type=BundleType.PORTFOLIO,
            owner_address="0xaaa",
        )
        self.manager.create_bundle(
            name="Bundle 2",
            description="Second",
            bundle_type=BundleType.COLLECTION,
            owner_address="0xbbb",
        )

        all_bundles = self.manager.list_bundles()
        assert len(all_bundles) == 2

        owner_bundles = self.manager.list_bundles(owner_address="0xaaa")
        assert len(owner_bundles) == 1

    def test_search_bundles(self):
        """Test searching bundles."""
        self.manager.create_bundle(
            name="Python Toolkit",
            description="Tools for Python",
            bundle_type=BundleType.SUITE,
            owner_address="0x123",
            tags=["python", "tools"],
        )

        results = self.manager.search_bundles("python")
        assert len(results) == 1


# =============================================================================
# Adaptive Pricing Tests
# =============================================================================


class TestAdaptivePricing:
    """Test adaptive pricing engine."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fixed_strategy(self):
        """Test fixed pricing strategy."""
        engine = AdaptivePricingEngine(
            base_price=100.0,
            strategy=PricingStrategy.FIXED,
        )

        rec = engine.get_recommendation()
        assert rec.recommended_price == 100.0
        assert rec.strategy_used == PricingStrategy.FIXED

    def test_demand_based_strategy(self):
        """Test demand-based pricing."""
        engine = AdaptivePricingEngine(
            base_price=100.0,
            strategy=PricingStrategy.DEMAND_BASED,
            storage_path=Path(self.temp_dir),
        )

        rec = engine.get_recommendation()
        assert rec.recommended_price > 0
        assert rec.price_range[0] <= rec.recommended_price <= rec.price_range[1]

    def test_record_signals(self):
        """Test recording pricing signals."""
        engine = AdaptivePricingEngine(
            base_price=100.0,
            strategy=PricingStrategy.DEMAND_BASED,
            storage_path=Path(self.temp_dir),
        )

        engine.record_view()
        engine.record_negotiation_start()
        engine.record_sale(95.0)

        metrics = engine.get_metrics()
        assert metrics.views_24h >= 1
        assert metrics.negotiations_24h >= 1
        assert metrics.conversions_24h >= 1

    def test_recommendation_confidence(self):
        """Test confidence increases with data."""
        engine = AdaptivePricingEngine(
            base_price=100.0,
            strategy=PricingStrategy.DEMAND_BASED,
            storage_path=Path(self.temp_dir),
        )

        # Low confidence with no data
        rec1 = engine.get_recommendation()

        # Add signals
        for _ in range(50):
            engine.record_view()
        for _ in range(10):
            engine.record_negotiation_start()
        for _ in range(3):
            engine.record_sale(100.0)

        rec2 = engine.get_recommendation()
        assert rec2.confidence > rec1.confidence

    def test_price_simulation(self):
        """Test price simulation."""
        engine = AdaptivePricingEngine(
            base_price=100.0,
            strategy=PricingStrategy.DEMAND_BASED,
        )

        sim = engine.simulate_price(80.0, expected_views=100)

        assert "test_price" in sim
        assert "expected_revenue" in sim
        assert "expected_conversions" in sim

    def test_price_bounds(self):
        """Test price stays within bounds."""
        engine = AdaptivePricingEngine(
            base_price=100.0,
            strategy=PricingStrategy.DEMAND_BASED,
            storage_path=Path(self.temp_dir),
        )

        rec = engine.get_recommendation()

        min_price = 100.0 * engine.MIN_ADJUSTMENT
        max_price = 100.0 * engine.MAX_ADJUSTMENT

        assert rec.recommended_price >= min_price
        assert rec.recommended_price <= max_price

    def test_factory_function(self):
        """Test factory function."""
        engine = create_pricing_engine(
            base_price=50.0,
            strategy="conversion_optimized",
            repo_id="test-repo",
        )

        assert engine.base_price == 50.0
        assert engine.strategy == PricingStrategy.CONVERSION_OPTIMIZED
