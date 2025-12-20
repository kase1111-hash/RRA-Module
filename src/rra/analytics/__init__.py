# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
License Entropy Oracle - Analytics Module.

Provides clause stability scoring, pattern analysis, and dispute prediction
for NatLangChain license negotiations.

Components:
- entropy_scorer: Core entropy/instability scoring for clauses
- clause_patterns: Pattern clustering and similarity analysis
- term_analysis: High-entropy term detection (Phase 6.6)
"""

from .entropy_scorer import (
    EntropyScorer,
    ClauseEntropy,
    EntropyLevel,
    calculate_clause_entropy,
)
from .clause_patterns import (
    ClausePattern,
    PatternCluster,
    ClausePatternAnalyzer,
)
from .term_analysis import (
    TermAnalyzer,
    TermAnalysis,
    TermReport,
    TermRiskLevel,
    TermCategory,
    find_high_entropy_terms,
)

__all__ = [
    # Entropy scoring
    "EntropyScorer",
    "ClauseEntropy",
    "EntropyLevel",
    "calculate_clause_entropy",
    # Pattern analysis
    "ClausePattern",
    "PatternCluster",
    "ClausePatternAnalyzer",
    # Term analysis (6.6)
    "TermAnalyzer",
    "TermAnalysis",
    "TermReport",
    "TermRiskLevel",
    "TermCategory",
    "find_high_entropy_terms",
]
