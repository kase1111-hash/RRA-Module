# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Status module for RRA.

Provides dreaming status updates for real-time visibility into processing.
The dreaming status shows start and completion of operations, updating
every 5 seconds to minimize performance overhead.

Usage:
    from rra.status import get_dreaming_status

    dreaming = get_dreaming_status()
    dreaming.start("Processing data")
    # ... do work ...
    dreaming.complete("Processing data")
"""

from rra.status.dreaming import (
    DreamingStatus,
    get_dreaming_status,
    configure_dreaming,
    StatusEntry,
    StatusType,
)

__all__ = [
    "DreamingStatus",
    "get_dreaming_status",
    "configure_dreaming",
    "StatusEntry",
    "StatusType",
]
