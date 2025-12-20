# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
License Clause Templates Module.

Provides pre-hardened clause templates for common license scenarios:
- Grant clauses with clear scope boundaries
- Termination with defined triggers
- Payment terms with specific formulas
- Dispute resolution with clear procedures
"""

from .hardened_clauses import (
    ClauseTemplate,
    TemplateCategory,
    TemplateLibrary,
    get_default_library,
)

__all__ = [
    "ClauseTemplate",
    "TemplateCategory",
    "TemplateLibrary",
    "get_default_library",
]
