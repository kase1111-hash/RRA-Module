# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
License Entropy Oracle - Predictions Module.

Machine learning models for predicting:
- Dispute probability for contracts
- Expected resolution time and cost
- Likelihood of successful negotiation
"""

from .dispute_model import (
    DisputePredictor,
    DisputePrediction,
    PredictionFeatures,
    predict_dispute_probability,
)

__all__ = [
    "DisputePredictor",
    "DisputePrediction",
    "PredictionFeatures",
    "predict_dispute_probability",
]
