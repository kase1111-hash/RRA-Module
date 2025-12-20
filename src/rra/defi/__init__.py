# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
DeFi integration module for RRA.

Provides yield-bearing license tokens, IP-backed lending,
and fractional IP ownership functionality.
"""

from .yield_tokens import (
    StakedLicense,
    YieldPool,
    YieldDistributor,
    StakingManager,
    YieldStrategy,
    create_staking_manager,
)

from .ipfi_lending import (
    Loan,
    LoanOffer,
    LoanTerms,
    LoanStatus,
    Collateral,
    CollateralType,
    CollateralValuator,
    IPFiLendingManager,
    create_lending_manager,
)

from .fractional_ip import (
    FractionalAsset,
    FractionStatus,
    ShareHolder,
    ShareOrder,
    FractionalIPManager,
    create_fractional_manager,
)

__all__ = [
    # Yield tokens
    "StakedLicense",
    "YieldPool",
    "YieldDistributor",
    "StakingManager",
    "YieldStrategy",
    "create_staking_manager",
    # IPFi Lending
    "Loan",
    "LoanOffer",
    "LoanTerms",
    "LoanStatus",
    "Collateral",
    "CollateralType",
    "CollateralValuator",
    "IPFiLendingManager",
    "create_lending_manager",
    # Fractional IP
    "FractionalAsset",
    "FractionStatus",
    "ShareHolder",
    "ShareOrder",
    "FractionalIPManager",
    "create_fractional_manager",
]
