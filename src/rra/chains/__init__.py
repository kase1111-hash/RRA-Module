# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Multi-chain support for RRA Module.

Supports Ethereum, Polygon, Arbitrum, Base, and Optimism.
"""

from .config import (
    ChainId,
    ChainConfig,
    ChainManager,
    CHAIN_CONFIGS,
    chain_manager,
    get_chain_manager,
)

__all__ = [
    "ChainId",
    "ChainConfig",
    "ChainManager",
    "CHAIN_CONFIGS",
    "chain_manager",
    "get_chain_manager",
]
