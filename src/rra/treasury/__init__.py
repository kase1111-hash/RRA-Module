# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Treasury Coordination Module.

Provides multi-treasury coordination for dispute resolution:

- Treasury registration and management
- Multi-treasury dispute creation
- Stake-weighted voting coordination
- Fund escrow and distribution
- Advisory resolution mechanisms

Use Cases:
- DAO treasury disagreements
- Contributor compensation disputes
- Shared asset licensing decisions
- Economic pressure for resolution
"""

from .coordinator import (
    TreasuryCoordinator,
    Treasury,
    TreasuryType,
    TreasuryDispute,
    DisputeStatus,
    TreasuryParticipant,
    Proposal,
    ProposalType,
    VoteChoice,
    create_treasury_coordinator,
)

__all__ = [
    "TreasuryCoordinator",
    "Treasury",
    "TreasuryType",
    "TreasuryDispute",
    "DisputeStatus",
    "TreasuryParticipant",
    "Proposal",
    "ProposalType",
    "VoteChoice",
    "create_treasury_coordinator",
]
