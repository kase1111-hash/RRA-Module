# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
License Clause Templates Module.

Provides pre-hardened clause templates for common license scenarios:
- Grant clauses with clear scope boundaries
- Termination with defined triggers
- Payment terms with specific formulas
- Dispute resolution with clear procedures
- Jurisdiction-specific legal wrappers
"""

from .hardened_clauses import (
    ClauseTemplate,
    TemplateCategory,
    TemplateLibrary,
    get_default_library,
)
from .legal_wrappers import (
    TemplateType,
    LanguageCode,
    TemplateVariable,
    LegalTemplate,
    RenderedClause,
    LegalTemplateLibrary,
    create_template_library,
)

__all__ = [
    # Hardened Clauses
    "ClauseTemplate",
    "TemplateCategory",
    "TemplateLibrary",
    "get_default_library",
    # Legal Wrapper Templates
    "TemplateType",
    "LanguageCode",
    "TemplateVariable",
    "LegalTemplate",
    "RenderedClause",
    "LegalTemplateLibrary",
    "create_template_library",
]
