# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for yield-bearing license tokens.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from rra.defi.yield_tokens import (
    StakedLicense,
    YieldPool,
    YieldDistributor,
    StakingManager,
    YieldStrategy,
    create_staking_manager,
)


class TestStakedLicense:
    """Tests for StakedLicense dataclass."""

    def test_create_staked_license(self):
        """Test creating a staked license."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now(),
        )

        assert stake.stake_id == "stake_123"
        assert stake.license_value == 0.5
        assert stake.active is True
        assert stake.earned_yield == 0.0

    def test_stake_duration_days(self):
        """Test stake duration calculation."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now() - timedelta(days=10),
        )

        assert stake.stake_duration_days >= 9.99  # Allow for test execution time

    def test_is_locked_no_unlock(self):
        """Test is_locked when no unlock time set."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now(),
            unlock_time=None,
        )

        assert stake.is_locked is False

    def test_is_locked_future_unlock(self):
        """Test is_locked when unlock time is in future."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now(),
            unlock_time=datetime.now() + timedelta(days=30),
        )

        assert stake.is_locked is True

    def test_is_locked_past_unlock(self):
        """Test is_locked when unlock time has passed."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now() - timedelta(days=30),
            unlock_time=datetime.now() - timedelta(days=1),
        )

        assert stake.is_locked is False

    def test_add_yield(self):
        """Test adding yield to stake."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now(),
        )

        stake.add_yield(0.01)
        assert stake.earned_yield == 0.01

        stake.add_yield(0.02)
        assert stake.earned_yield == 0.03

    def test_claim_yield(self):
        """Test claiming yield."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now(),
            earned_yield=0.05,
        )

        claimed = stake.claim_yield()

        assert claimed == 0.05
        assert stake.earned_yield == 0.0
        assert stake.total_claimed == 0.05
        assert stake.last_yield_claim is not None

    def test_serialization(self):
        """Test to_dict and from_dict."""
        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_xyz",
            staked_at=datetime.now(),
            unlock_time=datetime.now() + timedelta(days=30),
            earned_yield=0.01,
        )

        data = stake.to_dict()
        restored = StakedLicense.from_dict(data)

        assert restored.stake_id == stake.stake_id
        assert restored.license_value == stake.license_value
        assert restored.earned_yield == stake.earned_yield


class TestYieldPool:
    """Tests for YieldPool dataclass."""

    def test_create_pool(self):
        """Test creating a yield pool."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.HYBRID,
            base_apy=0.05,
        )

        assert pool.pool_id == "pool_123"
        assert pool.strategy == YieldStrategy.HYBRID
        assert pool.base_apy == 0.05
        assert pool.active is True

    def test_add_revenue(self):
        """Test adding revenue to pool."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.REVENUE_SHARE,
        )

        pool.add_revenue(1.0)

        assert pool.total_revenue == 1.0
        assert pool.pending_revenue == 1.0

    def test_calculate_share_empty_pool(self):
        """Test share calculation with empty pool."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.VALUE_WEIGHTED,
            total_value_locked=0.0,
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=0.5,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now(),
        )

        assert pool.calculate_share(stake) == 0.0

    def test_calculate_share_value_weighted(self):
        """Test value-weighted share calculation."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.VALUE_WEIGHTED,
            total_value_locked=10.0,
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=2.0,  # 20% of pool
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now(),
        )

        share = pool.calculate_share(stake)
        assert share == 0.2  # 2.0 / 10.0

    def test_calculate_share_time_weighted(self):
        """Test time-weighted share calculation."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.TIME_WEIGHTED,
            total_value_locked=10.0,
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=2.0,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now() - timedelta(days=365),  # 1 year
        )

        share = pool.calculate_share(stake)
        # Base share (0.2) * time multiplier (1 + 365/365 = 2.0)
        assert share >= 0.39  # Should be close to 0.4

    def test_lock_bonus_tiers(self):
        """Test lock bonus multipliers."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.FIXED_APY,
        )

        assert pool.get_lock_bonus(0) == 1.0
        assert pool.get_lock_bonus(29) == 1.0
        assert pool.get_lock_bonus(30) == 1.1
        assert pool.get_lock_bonus(89) == 1.1
        assert pool.get_lock_bonus(90) == 1.25
        assert pool.get_lock_bonus(364) == 1.25
        assert pool.get_lock_bonus(365) == 1.5

    def test_calculate_fixed_apy_yield(self):
        """Test fixed APY yield calculation."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.FIXED_APY,
            base_apy=0.05,  # 5% APY
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=1.0,  # 1 ETH
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now(),
        )

        # 365 days at 5% APY on 1 ETH = 0.05 ETH
        yield_amount = pool.calculate_fixed_apy_yield(stake, 365)
        assert abs(yield_amount - 0.05) < 0.001

    def test_serialization(self):
        """Test pool serialization."""
        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.HYBRID,
            base_apy=0.08,
        )

        data = pool.to_dict()
        restored = YieldPool.from_dict(data)

        assert restored.pool_id == pool.pool_id
        assert restored.strategy == pool.strategy
        assert restored.base_apy == pool.base_apy


class TestYieldDistributor:
    """Tests for YieldDistributor class."""

    def test_calculate_yield_fixed_apy(self):
        """Test yield calculation for fixed APY strategy."""
        distributor = YieldDistributor()

        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.FIXED_APY,
            base_apy=0.10,  # 10% APY
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=10.0,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now(),
        )

        # 30 days at 10% APY on 10 ETH
        yield_amount = distributor.calculate_yield(pool, stake, period_days=30)
        expected = 10.0 * 0.10 * (30 / 365)  # ~0.082 ETH
        assert abs(yield_amount - expected) < 0.001

    def test_calculate_yield_revenue_share(self):
        """Test yield calculation for revenue share strategy."""
        distributor = YieldDistributor()

        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.REVENUE_SHARE,
            total_value_locked=100.0,
            pending_revenue=10.0,
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=25.0,  # 25% of pool
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now(),
        )

        yield_amount = distributor.calculate_yield(pool, stake)
        # 25% of 10 ETH pending = 2.5 ETH
        assert yield_amount == 2.5

    def test_calculate_yield_inactive_stake(self):
        """Test yield calculation for inactive stake."""
        distributor = YieldDistributor()

        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.FIXED_APY,
            base_apy=0.10,
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=10.0,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now(),
            active=False,
        )

        yield_amount = distributor.calculate_yield(pool, stake)
        assert yield_amount == 0.0

    def test_distribute_revenue(self):
        """Test revenue distribution to stakes."""
        distributor = YieldDistributor()

        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.VALUE_WEIGHTED,
            total_value_locked=100.0,
            pending_revenue=10.0,
        )

        stakes = [
            StakedLicense(
                stake_id="stake_1",
                license_id="license_1",
                token_id=1,
                repo_url="https://github.com/user/repo1",
                license_value=60.0,  # 60%
                staker_address="0x1111111111111111111111111111111111111111",
                pool_id="pool_123",
                staked_at=datetime.now(),
            ),
            StakedLicense(
                stake_id="stake_2",
                license_id="license_2",
                token_id=2,
                repo_url="https://github.com/user/repo2",
                license_value=40.0,  # 40%
                staker_address="0x2222222222222222222222222222222222222222",
                pool_id="pool_123",
                staked_at=datetime.now(),
            ),
        ]

        distributions = distributor.distribute_revenue(pool, stakes)

        assert len(distributions) == 2
        assert abs(distributions["stake_1"] - 6.0) < 0.01  # 60% of 10
        assert abs(distributions["stake_2"] - 4.0) < 0.01  # 40% of 10

    def test_get_projected_yield(self):
        """Test yield projection."""
        distributor = YieldDistributor()

        pool = YieldPool(
            pool_id="pool_123",
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.FIXED_APY,
            base_apy=0.05,
        )

        stake = StakedLicense(
            stake_id="stake_123",
            license_id="license_abc",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=1.0,
            staker_address="0x1234567890123456789012345678901234567890",
            pool_id="pool_123",
            staked_at=datetime.now(),
        )

        projections = distributor.get_projected_yield(pool, stake, days=365)

        assert "days_7" in projections
        assert "days_30" in projections
        assert "days_365" in projections
        assert "effective_apy" in projections
        assert projections["effective_apy"] == pytest.approx(0.05, rel=0.01)


class TestStakingManager:
    """Tests for StakingManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        path = Path(tempfile.mkdtemp())
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create staking manager with temp storage."""
        return StakingManager(data_dir=temp_dir)

    def test_create_pool(self, manager):
        """Test pool creation."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test staking pool",
            strategy=YieldStrategy.HYBRID,
            base_apy=0.08,
        )

        assert pool.name == "Test Pool"
        assert pool.strategy == YieldStrategy.HYBRID
        assert pool.base_apy == 0.08
        assert pool.pool_id in manager.pools

    def test_get_pool(self, manager):
        """Test getting a pool by ID."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        retrieved = manager.get_pool(pool.pool_id)
        assert retrieved is not None
        assert retrieved.name == "Test Pool"

    def test_get_pool_not_found(self, manager):
        """Test getting non-existent pool."""
        retrieved = manager.get_pool("nonexistent")
        assert retrieved is None

    def test_list_pools(self, manager):
        """Test listing pools."""
        manager.create_pool(name="Pool 1", description="First pool")
        manager.create_pool(name="Pool 2", description="Second pool")

        pools = manager.list_pools()
        assert len(pools) == 2

    def test_stake_license(self, manager):
        """Test staking a license."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        stake = manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_123",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=1.0,
            staker_address="0x1234567890123456789012345678901234567890",
            lock_days=30,
        )

        assert stake.license_id == "license_123"
        assert stake.pool_id == pool.pool_id
        assert stake.is_locked is True

        # Check pool stats updated
        updated_pool = manager.get_pool(pool.pool_id)
        assert updated_pool.total_value_locked == 1.0
        assert updated_pool.stake_count == 1

    def test_stake_license_pool_not_found(self, manager):
        """Test staking to non-existent pool."""
        with pytest.raises(ValueError, match="Pool not found"):
            manager.stake_license(
                pool_id="nonexistent",
                license_id="license_123",
                token_id=1,
                repo_url="https://github.com/user/repo",
                license_value=1.0,
                staker_address="0x1234567890123456789012345678901234567890",
            )

    def test_stake_license_already_staked(self, manager):
        """Test staking same license twice."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_123",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=1.0,
            staker_address="0x1234567890123456789012345678901234567890",
        )

        with pytest.raises(ValueError, match="already staked"):
            manager.stake_license(
                pool_id=pool.pool_id,
                license_id="license_123",
                token_id=1,
                repo_url="https://github.com/user/repo",
                license_value=1.0,
                staker_address="0x1234567890123456789012345678901234567890",
            )

    def test_unstake_license(self, manager):
        """Test unstaking a license."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        stake = manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_123",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=1.0,
            staker_address="0x1234567890123456789012345678901234567890",
            lock_days=0,  # No lock
        )

        unstaked = manager.unstake_license(stake.stake_id)

        assert unstaked.active is False

        # Check pool stats updated
        updated_pool = manager.get_pool(pool.pool_id)
        assert updated_pool.total_value_locked == 0.0
        assert updated_pool.stake_count == 0

    def test_unstake_license_locked(self, manager):
        """Test unstaking a locked license fails."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        stake = manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_123",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=1.0,
            staker_address="0x1234567890123456789012345678901234567890",
            lock_days=30,  # 30 day lock
        )

        with pytest.raises(ValueError, match="locked"):
            manager.unstake_license(stake.stake_id)

    def test_claim_yield(self, manager):
        """Test claiming yield."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.FIXED_APY,
            base_apy=0.10,
        )

        stake = manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_123",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=10.0,
            staker_address="0x1234567890123456789012345678901234567890",
        )

        # Add some yield manually for testing
        stake.add_yield(0.5)

        claimed = manager.claim_yield(stake.stake_id)

        assert claimed >= 0.5  # At least the added yield

    def test_add_pool_revenue(self, manager):
        """Test adding revenue to pool."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        manager.add_pool_revenue(pool.pool_id, 5.0)

        updated = manager.get_pool(pool.pool_id)
        assert updated.total_revenue == 5.0
        assert updated.pending_revenue == 5.0

    def test_distribute_pool_revenue(self, manager):
        """Test distributing pool revenue."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
            strategy=YieldStrategy.VALUE_WEIGHTED,
        )

        # Create two stakes
        manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_1",
            token_id=1,
            repo_url="https://github.com/user/repo1",
            license_value=6.0,
            staker_address="0x1111111111111111111111111111111111111111",
        )

        manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_2",
            token_id=2,
            repo_url="https://github.com/user/repo2",
            license_value=4.0,
            staker_address="0x2222222222222222222222222222222222222222",
        )

        # Add and distribute revenue
        manager.add_pool_revenue(pool.pool_id, 10.0)
        distributions = manager.distribute_pool_revenue(pool.pool_id)

        assert len(distributions) == 2
        total_distributed = sum(distributions.values())
        assert abs(total_distributed - 10.0) < 0.01

    def test_get_staker_summary(self, manager):
        """Test getting staker summary."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        staker = "0x1234567890123456789012345678901234567890"

        manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_1",
            token_id=1,
            repo_url="https://github.com/user/repo1",
            license_value=5.0,
            staker_address=staker,
        )

        manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_2",
            token_id=2,
            repo_url="https://github.com/user/repo2",
            license_value=3.0,
            staker_address=staker,
        )

        summary = manager.get_staker_summary(staker)

        assert summary["active_stakes"] == 2
        assert summary["total_value_staked"] == 8.0
        assert "projected_earnings" in summary

    def test_get_pool_stats(self, manager):
        """Test getting pool statistics."""
        pool = manager.create_pool(
            name="Test Pool",
            description="A test pool",
        )

        manager.stake_license(
            pool_id=pool.pool_id,
            license_id="license_1",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=5.0,
            staker_address="0x1234567890123456789012345678901234567890",
        )

        stats = manager.get_pool_stats(pool.pool_id)

        assert stats["pool_id"] == pool.pool_id
        assert stats["active_stake_count"] == 1
        assert stats["total_value_locked"] == 5.0
        assert stats["unique_stakers"] == 1

    def test_persistence(self, temp_dir):
        """Test state persistence."""
        # Create manager and add data
        manager1 = StakingManager(data_dir=temp_dir)
        pool = manager1.create_pool(
            name="Persistent Pool",
            description="Test persistence",
        )
        manager1.stake_license(
            pool_id=pool.pool_id,
            license_id="license_persist",
            token_id=1,
            repo_url="https://github.com/user/repo",
            license_value=2.0,
            staker_address="0x1234567890123456789012345678901234567890",
        )

        # Create new manager with same directory
        manager2 = StakingManager(data_dir=temp_dir)

        # Verify data persisted
        assert len(manager2.pools) == 1
        assert len(manager2.stakes) == 1
        assert manager2.pools[pool.pool_id].name == "Persistent Pool"


class TestCreateStakingManager:
    """Tests for factory function."""

    def test_create_without_path(self):
        """Test creating manager without data directory."""
        manager = create_staking_manager()
        assert manager is not None

    def test_create_with_path(self):
        """Test creating manager with data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = create_staking_manager(temp_dir)
            assert manager is not None
            assert manager.data_dir == Path(temp_dir)


class TestYieldAPI:
    """Tests for yield API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from rra.api.yield_api import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_create_pool_endpoint(self, client):
        """Test POST /api/yield/pools endpoint."""
        response = client.post(
            "/api/yield/pools",
            json={
                "name": "API Test Pool",
                "description": "Created via API",
                "strategy": "hybrid",
                "base_apy": 0.05,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API Test Pool"
        assert data["strategy"] == "hybrid"

    def test_list_pools_endpoint(self, client):
        """Test GET /api/yield/pools endpoint."""
        # Create a pool first
        client.post(
            "/api/yield/pools",
            json={
                "name": "List Test Pool",
                "description": "For list testing",
            }
        )

        response = client.get("/api/yield/pools")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_stake_license_endpoint(self, client):
        """Test POST /api/yield/stake endpoint."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        # Create pool first
        pool_resp = client.post(
            "/api/yield/pools",
            json={
                "name": "Stake Test Pool",
                "description": "For staking test",
            }
        )
        pool_id = pool_resp.json()["pool_id"]

        response = client.post(
            "/api/yield/stake",
            json={
                "pool_id": pool_id,
                "license_id": f"test_license_{unique_id}",
                "token_id": 1,
                "repo_url": "https://github.com/test/repo",
                "license_value": 1.0,
                "staker_address": "0x1234567890123456789012345678901234567890",
                "lock_days": 0,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["license_id"] == f"test_license_{unique_id}"
        assert data["active"] is True

    def test_get_overview_endpoint(self, client):
        """Test GET /api/yield/overview endpoint."""
        response = client.get("/api/yield/overview")

        assert response.status_code == 200
        data = response.json()
        assert "total_pools" in data
        assert "total_value_locked" in data
        assert "strategies_available" in data

    def test_invalid_strategy_validation(self, client):
        """Test validation rejects invalid strategy."""
        response = client.post(
            "/api/yield/pools",
            json={
                "name": "Invalid Pool",
                "description": "Has invalid strategy",
                "strategy": "invalid_strategy",
            }
        )

        assert response.status_code == 422  # Validation error

    def test_invalid_address_validation(self, client):
        """Test validation rejects invalid addresses."""
        pool_resp = client.post(
            "/api/yield/pools",
            json={"name": "Test", "description": "Test"}
        )
        pool_id = pool_resp.json()["pool_id"]

        response = client.post(
            "/api/yield/stake",
            json={
                "pool_id": pool_id,
                "license_id": "test",
                "token_id": 1,
                "repo_url": "https://github.com/test/repo",
                "license_value": 1.0,
                "staker_address": "not_an_address",
            }
        )

        assert response.status_code == 422  # Validation error
