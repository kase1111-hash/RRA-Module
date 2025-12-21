# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
DAO Governance module for RRA.

Provides governance mechanisms for collective IP portfolio management,
multi-treasury dispute resolution voting, and reputation-weighted voting.
"""

from .dao import (
    IPDAO,
    DAOMember,
    Proposal,
    ProposalStatus,
    ProposalType,
    Vote,
    VoteChoice,
    DAOGovernanceManager,
    create_governance_manager,
)
from .treasury_votes import (
    TreasuryVoteType,
    TreasuryVoteStatus,
    VoteChoice as TreasuryVoteChoice,
    TreasuryVote,
    TreasuryProposal,
    TreasurySigner,
    VotingTreasury,
    TreasuryVotingManager,
    create_treasury_voting_manager,
)
from .rep_voting import (
    ProposalStatus as RepProposalStatus,
    VoteChoice as RepVoteChoice,
    WeightedVote,
    RepWeightedProposal,
    RepWeightedGovernance,
    create_rep_weighted_governance,
)

__all__ = [
    # DAO Governance
    "IPDAO",
    "DAOMember",
    "Proposal",
    "ProposalStatus",
    "ProposalType",
    "Vote",
    "VoteChoice",
    "DAOGovernanceManager",
    "create_governance_manager",
    # Treasury Voting
    "TreasuryVoteType",
    "TreasuryVoteStatus",
    "TreasuryVoteChoice",
    "TreasuryVote",
    "TreasuryProposal",
    "TreasurySigner",
    "VotingTreasury",
    "TreasuryVotingManager",
    "create_treasury_voting_manager",
    # Reputation-Weighted Voting
    "RepProposalStatus",
    "RepVoteChoice",
    "WeightedVote",
    "RepWeightedProposal",
    "RepWeightedGovernance",
    "create_rep_weighted_governance",
]
