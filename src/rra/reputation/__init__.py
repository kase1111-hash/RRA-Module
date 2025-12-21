# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Reputation System for RRA.

Provides reputation-weighted participation:
- Historical resolution success tracking
- Reputation score management
- Voting power calculation with reputation multipliers
- Good-faith behavior incentives
"""

from .weighted import (
    ReputationAction,
    ReputationChange,
    ParticipantReputation,
    VotingPower,
    ReputationConfig,
    ReputationManager,
    create_reputation_manager,
)

__all__ = [
    "ReputationAction",
    "ReputationChange",
    "ParticipantReputation",
    "VotingPower",
    "ReputationConfig",
    "ReputationManager",
    "create_reputation_manager",
]
