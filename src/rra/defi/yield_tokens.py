# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Yield-bearing license tokens implementation.

Enables license holders to stake their licenses and earn yield from
licensing revenue distribution. Supports multiple yield strategies
and automatic reward calculation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import secrets


class YieldStrategy(Enum):
    """Yield distribution strategies."""

    # Fixed APY regardless of pool activity
    FIXED_APY = "fixed_apy"

    # Revenue share - yield from actual license sales
    REVENUE_SHARE = "revenue_share"

    # Time-weighted - longer stakes earn more
    TIME_WEIGHTED = "time_weighted"

    # Value-weighted - higher value licenses earn more
    VALUE_WEIGHTED = "value_weighted"

    # Hybrid - combination of time and value weighting
    HYBRID = "hybrid"


@dataclass
class StakedLicense:
    """Represents a staked license earning yield."""

    # Unique stake ID
    stake_id: str

    # License information
    license_id: str
    token_id: int
    repo_url: str
    license_value: float  # Value in ETH

    # Staker information
    staker_address: str

    # Staking details
    pool_id: str
    staked_at: datetime
    unlock_time: Optional[datetime] = None  # None = no lock

    # Yield tracking
    earned_yield: float = 0.0
    last_yield_claim: Optional[datetime] = None
    total_claimed: float = 0.0

    # Status
    active: bool = True

    @property
    def stake_duration_days(self) -> float:
        """Calculate how long the license has been staked."""
        if not self.active:
            return 0.0
        delta = datetime.now() - self.staked_at
        return delta.total_seconds() / 86400

    @property
    def is_locked(self) -> bool:
        """Check if the stake is still in lock period."""
        if self.unlock_time is None:
            return False
        return datetime.now() < self.unlock_time

    @property
    def time_until_unlock(self) -> Optional[timedelta]:
        """Get time remaining until unlock."""
        if self.unlock_time is None:
            return None
        if datetime.now() >= self.unlock_time:
            return timedelta(0)
        return self.unlock_time - datetime.now()

    def add_yield(self, amount: float) -> None:
        """Add yield to this stake."""
        self.earned_yield += amount

    def claim_yield(self) -> float:
        """Claim all earned yield."""
        claimed = self.earned_yield
        self.total_claimed += claimed
        self.earned_yield = 0.0
        self.last_yield_claim = datetime.now()
        return claimed

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "stake_id": self.stake_id,
            "license_id": self.license_id,
            "token_id": self.token_id,
            "repo_url": self.repo_url,
            "license_value": self.license_value,
            "staker_address": self.staker_address,
            "pool_id": self.pool_id,
            "staked_at": self.staked_at.isoformat(),
            "unlock_time": self.unlock_time.isoformat() if self.unlock_time else None,
            "earned_yield": self.earned_yield,
            "last_yield_claim": self.last_yield_claim.isoformat() if self.last_yield_claim else None,
            "total_claimed": self.total_claimed,
            "active": self.active,
            "stake_duration_days": self.stake_duration_days,
            "is_locked": self.is_locked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StakedLicense":
        """Deserialize from dictionary."""
        return cls(
            stake_id=data["stake_id"],
            license_id=data["license_id"],
            token_id=data["token_id"],
            repo_url=data["repo_url"],
            license_value=data["license_value"],
            staker_address=data["staker_address"],
            pool_id=data["pool_id"],
            staked_at=datetime.fromisoformat(data["staked_at"]),
            unlock_time=datetime.fromisoformat(data["unlock_time"]) if data.get("unlock_time") else None,
            earned_yield=data.get("earned_yield", 0.0),
            last_yield_claim=datetime.fromisoformat(data["last_yield_claim"]) if data.get("last_yield_claim") else None,
            total_claimed=data.get("total_claimed", 0.0),
            active=data.get("active", True),
        )


@dataclass
class YieldPool:
    """A staking pool for yield-bearing licenses."""

    # Pool identification
    pool_id: str
    name: str
    description: str

    # Pool configuration
    strategy: YieldStrategy
    base_apy: float = 0.05  # 5% base APY
    min_stake_duration_days: int = 0  # Minimum lock period
    max_stakes: int = 0  # 0 = unlimited

    # Revenue tracking
    total_revenue: float = 0.0  # Total revenue collected
    distributed_revenue: float = 0.0  # Revenue already distributed
    pending_revenue: float = 0.0  # Revenue to be distributed

    # Pool state
    total_value_locked: float = 0.0
    stake_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True

    # Bonus multipliers
    lock_bonus_30d: float = 1.1   # 10% bonus for 30-day lock
    lock_bonus_90d: float = 1.25  # 25% bonus for 90-day lock
    lock_bonus_365d: float = 1.5  # 50% bonus for 365-day lock

    def add_revenue(self, amount: float) -> None:
        """Add revenue to the pool for distribution."""
        self.total_revenue += amount
        self.pending_revenue += amount

    def calculate_share(self, stake: StakedLicense) -> float:
        """Calculate a stake's share of the pool."""
        if self.total_value_locked == 0:
            return 0.0

        base_share = stake.license_value / self.total_value_locked

        # Apply strategy-specific modifiers
        if self.strategy == YieldStrategy.TIME_WEIGHTED:
            # Longer stakes get higher share
            time_multiplier = min(2.0, 1.0 + (stake.stake_duration_days / 365))
            return base_share * time_multiplier

        elif self.strategy == YieldStrategy.VALUE_WEIGHTED:
            # Pure value-based share
            return base_share

        elif self.strategy == YieldStrategy.HYBRID:
            # Combination of time and value
            time_multiplier = min(1.5, 1.0 + (stake.stake_duration_days / 730))
            return base_share * time_multiplier

        return base_share

    def get_lock_bonus(self, lock_days: int) -> float:
        """Get bonus multiplier for lock duration."""
        if lock_days >= 365:
            return self.lock_bonus_365d
        elif lock_days >= 90:
            return self.lock_bonus_90d
        elif lock_days >= 30:
            return self.lock_bonus_30d
        return 1.0

    def calculate_fixed_apy_yield(
        self,
        stake: StakedLicense,
        days: float
    ) -> float:
        """Calculate yield for fixed APY strategy."""
        # Daily rate from annual rate
        daily_rate = self.base_apy / 365

        # Calculate base yield
        base_yield = stake.license_value * daily_rate * days

        # Apply lock bonus if applicable
        lock_days = 0
        if stake.unlock_time:
            lock_period = stake.unlock_time - stake.staked_at
            lock_days = lock_period.days

        bonus = self.get_lock_bonus(lock_days)

        return base_yield * bonus

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pool_id": self.pool_id,
            "name": self.name,
            "description": self.description,
            "strategy": self.strategy.value,
            "base_apy": self.base_apy,
            "min_stake_duration_days": self.min_stake_duration_days,
            "max_stakes": self.max_stakes,
            "total_revenue": self.total_revenue,
            "distributed_revenue": self.distributed_revenue,
            "pending_revenue": self.pending_revenue,
            "total_value_locked": self.total_value_locked,
            "stake_count": self.stake_count,
            "created_at": self.created_at.isoformat(),
            "active": self.active,
            "lock_bonus_30d": self.lock_bonus_30d,
            "lock_bonus_90d": self.lock_bonus_90d,
            "lock_bonus_365d": self.lock_bonus_365d,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "YieldPool":
        """Deserialize from dictionary."""
        return cls(
            pool_id=data["pool_id"],
            name=data["name"],
            description=data["description"],
            strategy=YieldStrategy(data["strategy"]),
            base_apy=data.get("base_apy", 0.05),
            min_stake_duration_days=data.get("min_stake_duration_days", 0),
            max_stakes=data.get("max_stakes", 0),
            total_revenue=data.get("total_revenue", 0.0),
            distributed_revenue=data.get("distributed_revenue", 0.0),
            pending_revenue=data.get("pending_revenue", 0.0),
            total_value_locked=data.get("total_value_locked", 0.0),
            stake_count=data.get("stake_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            active=data.get("active", True),
            lock_bonus_30d=data.get("lock_bonus_30d", 1.1),
            lock_bonus_90d=data.get("lock_bonus_90d", 1.25),
            lock_bonus_365d=data.get("lock_bonus_365d", 1.5),
        )


class YieldDistributor:
    """Handles yield calculation and distribution."""

    def __init__(self):
        self.distribution_history: List[Dict[str, Any]] = []

    def calculate_yield(
        self,
        pool: YieldPool,
        stake: StakedLicense,
        period_days: Optional[float] = None
    ) -> float:
        """
        Calculate yield for a stake.

        Args:
            pool: The yield pool
            stake: The staked license
            period_days: Optional period override (default: since last claim)

        Returns:
            Yield amount in ETH
        """
        if not stake.active:
            return 0.0

        # Determine period
        if period_days is None:
            if stake.last_yield_claim:
                delta = datetime.now() - stake.last_yield_claim
            else:
                delta = datetime.now() - stake.staked_at
            period_days = delta.total_seconds() / 86400

        if period_days <= 0:
            return 0.0

        # Calculate based on strategy
        if pool.strategy == YieldStrategy.FIXED_APY:
            return pool.calculate_fixed_apy_yield(stake, period_days)

        elif pool.strategy == YieldStrategy.REVENUE_SHARE:
            # Share of pending revenue
            share = pool.calculate_share(stake)
            return pool.pending_revenue * share

        elif pool.strategy in (YieldStrategy.TIME_WEIGHTED, YieldStrategy.VALUE_WEIGHTED, YieldStrategy.HYBRID):
            # Combination of fixed APY and revenue share
            fixed_yield = pool.calculate_fixed_apy_yield(stake, period_days)
            share = pool.calculate_share(stake)
            revenue_yield = pool.pending_revenue * share * 0.5  # 50% of revenue
            return fixed_yield + revenue_yield

        return 0.0

    def distribute_revenue(
        self,
        pool: YieldPool,
        stakes: List[StakedLicense]
    ) -> Dict[str, float]:
        """
        Distribute pending revenue to all stakes in a pool.

        Args:
            pool: The yield pool
            stakes: All active stakes in the pool

        Returns:
            Dictionary mapping stake_id to distributed amount
        """
        if pool.pending_revenue <= 0:
            return {}

        distributions: Dict[str, float] = {}
        total_distributed = 0.0

        # Calculate total share weight
        active_stakes = [s for s in stakes if s.active and s.pool_id == pool.pool_id]

        if not active_stakes:
            return {}

        total_share_weight = sum(pool.calculate_share(s) for s in active_stakes)

        if total_share_weight == 0:
            return {}

        # Distribute revenue proportionally
        for stake in active_stakes:
            share = pool.calculate_share(stake) / total_share_weight
            amount = pool.pending_revenue * share

            stake.add_yield(amount)
            distributions[stake.stake_id] = amount
            total_distributed += amount

        # Update pool state
        pool.distributed_revenue += total_distributed
        pool.pending_revenue -= total_distributed

        # Record distribution
        self.distribution_history.append({
            "pool_id": pool.pool_id,
            "timestamp": datetime.now().isoformat(),
            "total_distributed": total_distributed,
            "stake_count": len(active_stakes),
            "distributions": distributions,
        })

        return distributions

    def get_projected_yield(
        self,
        pool: YieldPool,
        stake: StakedLicense,
        days: int = 365
    ) -> Dict[str, float]:
        """
        Project future yield for a stake.

        Args:
            pool: The yield pool
            stake: The staked license
            days: Number of days to project

        Returns:
            Dictionary with projected yields at various timeframes
        """
        projections = {}

        for period in [7, 30, 90, 180, 365]:
            if period <= days:
                projected = self.calculate_yield(pool, stake, period_days=period)
                projections[f"days_{period}"] = projected

        # Calculate effective APY
        annual_yield = self.calculate_yield(pool, stake, period_days=365)
        effective_apy = annual_yield / stake.license_value if stake.license_value > 0 else 0
        projections["effective_apy"] = effective_apy

        return projections


class StakingManager:
    """Manages staking pools and stakes."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/staking")
        self.pools: Dict[str, YieldPool] = {}
        self.stakes: Dict[str, StakedLicense] = {}
        self.distributor = YieldDistributor()

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        """Generate a unique ID."""
        return f"{prefix}{secrets.token_hex(8)}"

    def create_pool(
        self,
        name: str,
        description: str,
        strategy: YieldStrategy = YieldStrategy.HYBRID,
        base_apy: float = 0.05,
        min_stake_duration_days: int = 0,
        max_stakes: int = 0
    ) -> YieldPool:
        """
        Create a new yield pool.

        Args:
            name: Pool name
            description: Pool description
            strategy: Yield distribution strategy
            base_apy: Base annual percentage yield
            min_stake_duration_days: Minimum lock period
            max_stakes: Maximum number of stakes (0 = unlimited)

        Returns:
            Created yield pool
        """
        pool = YieldPool(
            pool_id=self._generate_id("pool_"),
            name=name,
            description=description,
            strategy=strategy,
            base_apy=base_apy,
            min_stake_duration_days=min_stake_duration_days,
            max_stakes=max_stakes,
        )

        self.pools[pool.pool_id] = pool
        self._save_state()

        return pool

    def get_pool(self, pool_id: str) -> Optional[YieldPool]:
        """Get a pool by ID."""
        return self.pools.get(pool_id)

    def list_pools(self, active_only: bool = True) -> List[YieldPool]:
        """List all pools."""
        pools = list(self.pools.values())
        if active_only:
            pools = [p for p in pools if p.active]
        return pools

    def stake_license(
        self,
        pool_id: str,
        license_id: str,
        token_id: int,
        repo_url: str,
        license_value: float,
        staker_address: str,
        lock_days: int = 0
    ) -> StakedLicense:
        """
        Stake a license in a pool.

        Args:
            pool_id: Target pool ID
            license_id: License identifier
            token_id: NFT token ID
            repo_url: Repository URL
            license_value: License value in ETH
            staker_address: Staker's address
            lock_days: Lock period in days (0 = no lock)

        Returns:
            Created staked license

        Raises:
            ValueError: If pool not found or validation fails
        """
        pool = self.pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool not found: {pool_id}")

        if not pool.active:
            raise ValueError(f"Pool is not active: {pool_id}")

        if pool.max_stakes > 0 and pool.stake_count >= pool.max_stakes:
            raise ValueError(f"Pool has reached maximum stakes: {pool.max_stakes}")

        if lock_days < pool.min_stake_duration_days:
            raise ValueError(
                f"Lock period must be at least {pool.min_stake_duration_days} days"
            )

        # Check if license already staked
        for stake in self.stakes.values():
            if stake.license_id == license_id and stake.active:
                raise ValueError(f"License already staked: {license_id}")

        now = datetime.now()
        unlock_time = now + timedelta(days=lock_days) if lock_days > 0 else None

        stake = StakedLicense(
            stake_id=self._generate_id("stake_"),
            license_id=license_id,
            token_id=token_id,
            repo_url=repo_url,
            license_value=license_value,
            staker_address=staker_address,
            pool_id=pool_id,
            staked_at=now,
            unlock_time=unlock_time,
        )

        self.stakes[stake.stake_id] = stake

        # Update pool stats
        pool.total_value_locked += license_value
        pool.stake_count += 1

        self._save_state()

        return stake

    def unstake_license(self, stake_id: str) -> StakedLicense:
        """
        Unstake a license.

        Args:
            stake_id: Stake ID

        Returns:
            Updated staked license

        Raises:
            ValueError: If stake not found or still locked
        """
        stake = self.stakes.get(stake_id)
        if not stake:
            raise ValueError(f"Stake not found: {stake_id}")

        if not stake.active:
            raise ValueError(f"Stake already inactive: {stake_id}")

        if stake.is_locked:
            raise ValueError(
                f"Stake is locked until {stake.unlock_time.isoformat()}"
            )

        # Claim any remaining yield first
        pool = self.pools.get(stake.pool_id)
        if pool:
            yield_amount = self.distributor.calculate_yield(pool, stake)
            stake.add_yield(yield_amount)

            # Update pool stats
            pool.total_value_locked -= stake.license_value
            pool.stake_count -= 1

        stake.active = False
        self._save_state()

        return stake

    def claim_yield(self, stake_id: str) -> float:
        """
        Claim earned yield for a stake.

        Args:
            stake_id: Stake ID

        Returns:
            Claimed yield amount

        Raises:
            ValueError: If stake not found
        """
        stake = self.stakes.get(stake_id)
        if not stake:
            raise ValueError(f"Stake not found: {stake_id}")

        if not stake.active:
            raise ValueError(f"Stake is not active: {stake_id}")

        pool = self.pools.get(stake.pool_id)
        if pool:
            # Calculate and add pending yield
            pending = self.distributor.calculate_yield(pool, stake)
            stake.add_yield(pending)

        claimed = stake.claim_yield()
        self._save_state()

        return claimed

    def get_stake(self, stake_id: str) -> Optional[StakedLicense]:
        """Get a stake by ID."""
        return self.stakes.get(stake_id)

    def get_stakes_by_staker(self, staker_address: str) -> List[StakedLicense]:
        """Get all stakes for a staker."""
        return [
            s for s in self.stakes.values()
            if s.staker_address.lower() == staker_address.lower()
        ]

    def get_stakes_by_pool(self, pool_id: str) -> List[StakedLicense]:
        """Get all stakes in a pool."""
        return [s for s in self.stakes.values() if s.pool_id == pool_id]

    def add_pool_revenue(self, pool_id: str, amount: float) -> None:
        """
        Add revenue to a pool for distribution.

        Args:
            pool_id: Pool ID
            amount: Revenue amount in ETH

        Raises:
            ValueError: If pool not found
        """
        pool = self.pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool not found: {pool_id}")

        pool.add_revenue(amount)
        self._save_state()

    def distribute_pool_revenue(self, pool_id: str) -> Dict[str, float]:
        """
        Distribute pending revenue to all stakes in a pool.

        Args:
            pool_id: Pool ID

        Returns:
            Dictionary mapping stake_id to distributed amount

        Raises:
            ValueError: If pool not found
        """
        pool = self.pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool not found: {pool_id}")

        stakes = self.get_stakes_by_pool(pool_id)
        distributions = self.distributor.distribute_revenue(pool, stakes)

        self._save_state()

        return distributions

    def get_staker_summary(self, staker_address: str) -> Dict[str, Any]:
        """
        Get staking summary for a staker.

        Args:
            staker_address: Staker's address

        Returns:
            Summary dictionary with total staked, earned, etc.
        """
        stakes = self.get_stakes_by_staker(staker_address)
        active_stakes = [s for s in stakes if s.active]

        total_staked = sum(s.license_value for s in active_stakes)
        total_earned = sum(s.earned_yield for s in active_stakes)
        total_claimed = sum(s.total_claimed for s in stakes)

        # Calculate projected earnings
        projected_earnings = {}
        for stake in active_stakes:
            pool = self.pools.get(stake.pool_id)
            if pool:
                projected = self.distributor.get_projected_yield(pool, stake)
                for period, amount in projected.items():
                    projected_earnings[period] = projected_earnings.get(period, 0) + amount

        return {
            "staker_address": staker_address,
            "active_stakes": len(active_stakes),
            "total_stakes": len(stakes),
            "total_value_staked": total_staked,
            "unclaimed_yield": total_earned,
            "total_claimed": total_claimed,
            "projected_earnings": projected_earnings,
            "stakes": [s.to_dict() for s in active_stakes],
        }

    def get_pool_stats(self, pool_id: str) -> Dict[str, Any]:
        """
        Get statistics for a pool.

        Args:
            pool_id: Pool ID

        Returns:
            Pool statistics dictionary
        """
        pool = self.pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool not found: {pool_id}")

        stakes = self.get_stakes_by_pool(pool_id)
        active_stakes = [s for s in stakes if s.active]

        total_earned = sum(s.earned_yield + s.total_claimed for s in stakes)
        avg_stake_duration = 0.0
        if active_stakes:
            avg_stake_duration = sum(s.stake_duration_days for s in active_stakes) / len(active_stakes)

        return {
            **pool.to_dict(),
            "active_stake_count": len(active_stakes),
            "total_stake_count": len(stakes),
            "total_yield_distributed": total_earned,
            "average_stake_duration_days": avg_stake_duration,
            "unique_stakers": len(set(s.staker_address for s in active_stakes)),
        }

    def _save_state(self) -> None:
        """Save state to disk."""
        if not self.data_dir:
            return

        state = {
            "pools": {pid: p.to_dict() for pid, p in self.pools.items()},
            "stakes": {sid: s.to_dict() for sid, s in self.stakes.items()},
            "distribution_history": self.distributor.distribution_history[-100:],  # Keep last 100
        }

        state_file = self.data_dir / "staking_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        """Load state from disk."""
        state_file = self.data_dir / "staking_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.pools = {
                pid: YieldPool.from_dict(pdata)
                for pid, pdata in state.get("pools", {}).items()
            }

            self.stakes = {
                sid: StakedLicense.from_dict(sdata)
                for sid, sdata in state.get("stakes", {}).items()
            }

            self.distributor.distribution_history = state.get("distribution_history", [])
        except (json.JSONDecodeError, KeyError) as e:
            # Start fresh if state is corrupted
            self.pools = {}
            self.stakes = {}


def create_staking_manager(data_dir: Optional[str] = None) -> StakingManager:
    """
    Factory function to create a staking manager.

    Args:
        data_dir: Optional data directory path

    Returns:
        Configured StakingManager instance
    """
    path = Path(data_dir) if data_dir else None
    return StakingManager(data_dir=path)
