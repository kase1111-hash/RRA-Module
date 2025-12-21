# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Legal Wrapper Generation module for RRA.

Provides legal documentation for:
- Assignment and license agreements
- Security interest documents
- Regulatory disclosures
- Jurisdiction-specific wrappers
- Jurisdiction detection
- Per-jurisdiction compliance rules
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
from .jurisdiction import (
    JurisdictionCode,
    JurisdictionRegion,
    DetectionMethod,
    ConfidenceLevel,
    JurisdictionSignal,
    JurisdictionResult,
    ParticipantJurisdiction,
    JurisdictionDetector,
    create_jurisdiction_detector,
)
from .compliance_rules import (
    RegulatoryFramework,
    ContractLaw,
    DisputeResolution,
    IPLawTreaty,
    TaxRequirements,
    DisclosureRequirements,
    InvestorRequirements,
    ContractRequirements,
    IPLawRequirements,
    JurisdictionRules,
    JurisdictionRulesRegistry,
    create_rules_registry,
)

__all__ = [
    # RWA Wrappers
    "WrapperType",
    "JurisdictionType",
    "AssetClassification",
    "LegalParty",
    "WrapperClause",
    "WrapperTemplate",
    "GeneratedWrapper",
    "LegalWrapperGenerator",
    "create_wrapper_generator",
    # Jurisdiction Detection
    "JurisdictionCode",
    "JurisdictionRegion",
    "DetectionMethod",
    "ConfidenceLevel",
    "JurisdictionSignal",
    "JurisdictionResult",
    "ParticipantJurisdiction",
    "JurisdictionDetector",
    "create_jurisdiction_detector",
    # Compliance Rules
    "RegulatoryFramework",
    "ContractLaw",
    "DisputeResolution",
    "IPLawTreaty",
    "TaxRequirements",
    "DisclosureRequirements",
    "InvestorRequirements",
    "ContractRequirements",
    "IPLawRequirements",
    "JurisdictionRules",
    "JurisdictionRulesRegistry",
    "create_rules_registry",
]
