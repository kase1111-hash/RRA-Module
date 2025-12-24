# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Code verification and validation modules.

Provides tools for:
- Verifying code does what its README claims
- Running tests and linting
- Security scanning
- Category classification
- Blockchain link generation
"""

from rra.verification.verifier import CodeVerifier, VerificationResult
from rra.verification.readme_parser import ReadmeParser, ReadmeMetadata
from rra.verification.categorizer import CodeCategorizer, CodeCategory
from rra.verification.blockchain_link import BlockchainLinkGenerator, PurchaseLink

__all__ = [
    "CodeVerifier",
    "VerificationResult",
    "ReadmeParser",
    "ReadmeMetadata",
    "CodeCategorizer",
    "CodeCategory",
    "BlockchainLinkGenerator",
    "PurchaseLink",
]
