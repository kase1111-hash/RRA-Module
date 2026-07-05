# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Revenant Repo Agent Module (RRA)

Turn dormant GitHub repositories into licensable IP: register repos on
Story Protocol and generate frictionless on-chain purchase links for
license NFTs.
"""

__version__ = "1.0.1-beta"
__author__ = "RRA Contributors"

from rra.config.market_config import MarketConfig
from rra.ingestion.repo_ingester import RepoIngester

__all__ = [
    "MarketConfig",
    "RepoIngester",
]
