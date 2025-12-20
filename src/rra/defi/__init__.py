# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
DeFi integration module for RRA.

Provides yield-bearing license tokens and staking functionality.
"""

from .yield_tokens import (
    StakedLicense,
    YieldPool,
    YieldDistributor,
    StakingManager,
    YieldStrategy,
    create_staking_manager,
)

__all__ = [
    "StakedLicense",
    "YieldPool",
    "YieldDistributor",
    "StakingManager",
    "YieldStrategy",
    "create_staking_manager",
]
