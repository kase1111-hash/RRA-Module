"""
Revenant Repo Agent Module (RRA)

A transformative module for resurrecting dormant GitHub repositories
into self-sustaining, autonomous agents capable of generating revenue
through on-chain negotiations and licensing.
"""

__version__ = "0.1.0"
__author__ = "RRA Contributors"

from rra.config.market_config import MarketConfig
from rra.ingestion.repo_ingester import RepoIngester
from rra.agents.negotiator import NegotiatorAgent

__all__ = [
    "MarketConfig",
    "RepoIngester",
    "NegotiatorAgent",
]
