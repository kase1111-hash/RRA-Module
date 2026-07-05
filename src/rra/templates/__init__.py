# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
License Clause Templates Module.

Provides jurisdiction-specific legal wrapper templates for licensing.
"""

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
    # Legal Wrapper Templates
    "TemplateType",
    "LanguageCode",
    "TemplateVariable",
    "LegalTemplate",
    "RenderedClause",
    "LegalTemplateLibrary",
    "create_template_library",
]
