# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Legal Wrapper Generation module for RRA.

Provides legal documentation for:
- Assignment and license agreements
- Security interest documents
- Regulatory disclosures
- Jurisdiction-specific wrappers
"""

from .rwa_wrappers import (
    WrapperType,
    JurisdictionType,
    AssetClassification,
    LegalParty,
    WrapperClause,
    WrapperTemplate,
    GeneratedWrapper,
    LegalWrapperGenerator,
    create_wrapper_generator,
)

__all__ = [
    "WrapperType",
    "JurisdictionType",
    "AssetClassification",
    "LegalParty",
    "WrapperClause",
    "WrapperTemplate",
    "GeneratedWrapper",
    "LegalWrapperGenerator",
    "create_wrapper_generator",
]
