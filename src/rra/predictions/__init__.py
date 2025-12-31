# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
License Entropy Oracle - Predictions Module.

Machine learning models for predicting:
- Dispute probability for contracts
- Expected resolution time and cost
- Likelihood of successful negotiation
- Predictive dispute warnings (Phase 6.6)
"""

from .dispute_model import (
    DisputePredictor,
    DisputePrediction,
    PredictionFeatures,
    DisputeType,
    predict_dispute_probability,
)
from .dispute_warning import (
    DisputeWarningGenerator,
    DisputeWarning,
    WarningReport,
    WarningSeverity,
    WarningCategory,
    Mitigation,
    generate_dispute_warnings,
)

__all__ = [
    # Dispute prediction
    "DisputePredictor",
    "DisputePrediction",
    "PredictionFeatures",
    "DisputeType",
    "predict_dispute_probability",
    # Dispute warnings (6.6)
    "DisputeWarningGenerator",
    "DisputeWarning",
    "WarningReport",
    "WarningSeverity",
    "WarningCategory",
    "Mitigation",
    "generate_dispute_warnings",
]
