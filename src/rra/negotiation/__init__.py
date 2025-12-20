# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Negotiation Module for NatLangChain.

Provides economic pressure mechanisms to encourage timely resolution
of license negotiations:

- Counter-proposal caps: Limit endless back-and-forth
- Delay costs: Exponential time-based penalties
- Deadline enforcement: Hard limits with consequences

Part of Phase 6.2: Counter-Proposal Caps & Delay Costs
"""

from .pressure import (
    PressureConfig,
    NegotiationPressure,
    NegotiationState,
    CounterProposal,
    calculate_delay_cost,
)

__all__ = [
    "PressureConfig",
    "NegotiationPressure",
    "NegotiationState",
    "CounterProposal",
    "calculate_delay_cost",
]
