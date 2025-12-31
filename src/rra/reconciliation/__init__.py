# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Multi-Party Reconciliation Module.

Provides N-party dispute resolution infrastructure:
- Multi-party dispute orchestration
- Weighted voting mechanisms
- Coalition formation and management
- Privacy-preserving identity verification
"""

from .multi import (
    MultiPartyDispute,
    DisputeParty,
    DisputePhase,
    MultiPartyOrchestrator,
    ProposalSubmission,
    CoalitionRequest,
)
from .voting import (
    VotingSystem,
    Vote,
    VoteChoice,
    Proposal,
    ProposalStatus,
    VotingResult,
    QuorumConfig,
)

__all__ = [
    # Multi-party orchestration
    "MultiPartyDispute",
    "DisputeParty",
    "DisputePhase",
    "MultiPartyOrchestrator",
    "ProposalSubmission",
    "CoalitionRequest",
    # Voting
    "VotingSystem",
    "Vote",
    "VoteChoice",
    "Proposal",
    "ProposalStatus",
    "VotingResult",
    "QuorumConfig",
]
