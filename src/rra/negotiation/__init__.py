# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Negotiation Module for NatLangChain.

Provides negotiation support mechanisms:

- Counter-proposal caps: Limit endless back-and-forth (Phase 6.2)
- Delay costs: Exponential time-based penalties (Phase 6.2)
- Clause hardening: AI-powered clause improvement (Phase 6.5)
- Hardened templates: Pre-vetted low-risk clauses (Phase 6.5)
"""

from .pressure import (
    PressureConfig,
    NegotiationPressure,
    NegotiationState,
    CounterProposal,
    calculate_delay_cost,
)
from .clause_hardener import (
    ClauseHardener,
    HardeningLevel,
    HardeningStrategy,
    HardeningRule,
    HardeningResult,
    HardeningSession,
    HardeningPipeline,
)

__all__ = [
    # Pressure mechanisms (6.2)
    "PressureConfig",
    "NegotiationPressure",
    "NegotiationState",
    "CounterProposal",
    "calculate_delay_cost",
    # Clause hardening (6.5)
    "ClauseHardener",
    "HardeningLevel",
    "HardeningStrategy",
    "HardeningRule",
    "HardeningResult",
    "HardeningSession",
    "HardeningPipeline",
]
