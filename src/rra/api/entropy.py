# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
License Entropy Oracle API Endpoints.

Provides REST API for:
- Clause entropy scoring
- Contract-level dispute prediction
- Pattern analysis and hardening suggestions
- Historical dispute data ingestion

These endpoints power the LEO Dashboard and can be used by
upstream contracts for on-chain entropy queries.
"""

from typing import List, Optional, Dict, Any, cast
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from rra.analytics.entropy_scorer import (
    EntropyScorer,
    ClauseEntropy,
    EntropyLevel,
    DisputeRecord,
)
from rra.analytics.clause_patterns import (
    ClausePatternAnalyzer,
    ClauseCategory,
)
from rra.predictions.dispute_model import (
    DisputePredictor,
    DisputePrediction,
    DisputeType,
)


router = APIRouter(prefix="/entropy", tags=["entropy"])

# Singleton instances (in production, use dependency injection)
_entropy_scorer: Optional[EntropyScorer] = None
_pattern_analyzer: Optional[ClausePatternAnalyzer] = None
_dispute_predictor: Optional[DisputePredictor] = None


def get_entropy_scorer() -> EntropyScorer:
    """Get or create entropy scorer instance."""
    global _entropy_scorer
    if _entropy_scorer is None:
        _entropy_scorer = EntropyScorer()
    return _entropy_scorer


def get_pattern_analyzer() -> ClausePatternAnalyzer:
    """Get or create pattern analyzer instance."""
    global _pattern_analyzer
    if _pattern_analyzer is None:
        _pattern_analyzer = ClausePatternAnalyzer()
    return _pattern_analyzer


def get_dispute_predictor() -> DisputePredictor:
    """Get or create dispute predictor instance."""
    global _dispute_predictor
    if _dispute_predictor is None:
        _dispute_predictor = DisputePredictor()
    return _dispute_predictor


# =============================================================================
# Request/Response Models
# =============================================================================

class ClauseScoreRequest(BaseModel):
    """Request to score a single clause."""
    clause_text: str = Field(..., min_length=10, max_length=10000)


class ClauseScoreResponse(BaseModel):
    """Response with clause entropy score."""
    clause_hash: str
    entropy_score: float
    level: str
    components: Dict[str, float]
    warning: Optional[str]
    suggested_alternatives: List[str]
    confidence: float


class ContractScoreRequest(BaseModel):
    """Request to score a full contract."""
    clauses: List[str] = Field(..., min_length=1, max_length=100)
    repo_id: Optional[str] = None


class ContractScoreResponse(BaseModel):
    """Response with contract-level entropy analysis."""
    overall_entropy: float
    overall_level: str
    total_clauses: int
    high_risk_count: int
    dispute_probability: float
    high_risk_clauses: List[Dict[str, Any]]


class DisputePredictionRequest(BaseModel):
    """Request for dispute prediction."""
    clauses: List[str] = Field(..., min_length=1, max_length=100)
    licensee_prior_disputes: int = Field(default=0, ge=0)
    licensor_prior_disputes: int = Field(default=0, ge=0)


class DisputePredictionResponse(BaseModel):
    """Response with dispute prediction."""
    dispute_probability: float
    expected_disputes: float
    type_probabilities: Dict[str, float]
    expected_resolution: Dict[str, float]
    risk_factors: List[Dict[str, Any]]
    recommended_actions: List[str]
    confidence: float


class PatternAnalysisRequest(BaseModel):
    """Request for pattern analysis."""
    clause_text: str = Field(..., min_length=10, max_length=10000)


class PatternAnalysisResponse(BaseModel):
    """Response with pattern analysis."""
    category: str
    dispute_triggers: List[Dict[str, str]]
    hardening_suggestions: List[Dict[str, Any]]
    similar_patterns: List[Dict[str, Any]]
    risk_level: str


class DisputeRecordRequest(BaseModel):
    """Request to record a dispute for model training."""
    clause_text: str
    dispute_type: str
    resolution_time_days: float = Field(ge=0)
    resolution_cost_usd: float = Field(ge=0)
    outcome: str = Field(pattern="^(settled|escalated|abandoned)$")


class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    version: str
    model_version: str
    training_samples: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check for the entropy API.

    Returns:
        API status and version info
    """
    predictor = get_dispute_predictor()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        model_version=predictor.MODEL_VERSION,
        training_samples=predictor._training_samples,
    )


@router.post("/score/clause", response_model=ClauseScoreResponse)
async def score_clause(request: ClauseScoreRequest) -> ClauseScoreResponse:
    """
    Score a single clause for entropy/instability.

    Higher entropy scores indicate higher risk of disputes.

    Args:
        request: Clause text to analyze

    Returns:
        Detailed entropy analysis
    """
    scorer = get_entropy_scorer()
    result = scorer.score_clause(request.clause_text)

    return ClauseScoreResponse(
        clause_hash=result.clause_hash,
        entropy_score=round(result.entropy_score, 4),
        level=result.level.value,
        components={
            "dispute_rate": round(result.dispute_rate, 4),
            "ambiguity_score": round(result.ambiguity_score, 4),
            "modification_frequency": round(result.modification_frequency, 4),
            "resolution_difficulty": round(result.resolution_difficulty, 4),
            "semantic_volatility": round(result.semantic_volatility, 4),
        },
        warning=result.warning,
        suggested_alternatives=result.suggested_alternatives,
        confidence=round(result.confidence, 4),
    )


@router.post("/score/contract", response_model=ContractScoreResponse)
async def score_contract(request: ContractScoreRequest) -> ContractScoreResponse:
    """
    Score all clauses in a contract.

    Returns aggregate entropy metrics and identifies high-risk clauses.

    Args:
        request: List of clause texts

    Returns:
        Contract-level entropy analysis
    """
    scorer = get_entropy_scorer()
    result = scorer.score_contract(request.clauses)

    return ContractScoreResponse(
        overall_entropy=result["overall_entropy"],
        overall_level=result["overall_level"],
        total_clauses=result["total_clauses"],
        high_risk_count=result["high_risk_count"],
        dispute_probability=result["dispute_probability"],
        high_risk_clauses=result["high_risk_clauses"],
    )


@router.post("/predict", response_model=DisputePredictionResponse)
async def predict_disputes(request: DisputePredictionRequest) -> DisputePredictionResponse:
    """
    Predict dispute probability for a contract.

    Uses ML model trained on historical dispute data.

    Args:
        request: Contract clauses and optional party history

    Returns:
        Dispute prediction with risk analysis
    """
    predictor = get_dispute_predictor()
    result = predictor.predict(
        clauses=request.clauses,
        licensee_history=request.licensee_prior_disputes,
        licensor_history=request.licensor_prior_disputes,
    )

    return DisputePredictionResponse(
        dispute_probability=round(result.dispute_probability, 4),
        expected_disputes=round(result.expected_disputes, 2),
        type_probabilities={
            t.value: round(p, 4)
            for t, p in result.type_probabilities.items()
        },
        expected_resolution={
            "days": round(result.expected_resolution_days, 1),
            "cost_usd": round(result.expected_resolution_cost, 2),
        },
        risk_factors=[
            {"factor": f, "weight": round(w, 4)}
            for f, w in result.top_risk_factors
        ],
        recommended_actions=result.recommended_actions,
        confidence=round(result.confidence, 4),
    )


@router.post("/analyze/pattern", response_model=PatternAnalysisResponse)
async def analyze_pattern(request: PatternAnalysisRequest) -> PatternAnalysisResponse:
    """
    Analyze clause patterns and identify dispute triggers.

    Args:
        request: Clause text to analyze

    Returns:
        Pattern analysis with hardening suggestions
    """
    analyzer = get_pattern_analyzer()
    result = analyzer.analyze_clause(request.clause_text)

    return PatternAnalysisResponse(
        category=result["category"],
        dispute_triggers=result["dispute_triggers"],
        hardening_suggestions=result["hardening_suggestions"],
        similar_patterns=result["similar_patterns"],
        risk_level=result["risk_level"],
    )


@router.get("/score/{clause_hash}")
async def get_score_by_hash(clause_hash: str) -> Dict[str, Any]:
    """
    Get cached entropy score by clause hash.

    Useful for on-chain contracts querying known clause hashes.

    Args:
        clause_hash: 16-character hex hash of normalized clause

    Returns:
        Cached entropy data if available
    """
    scorer = get_entropy_scorer()
    stats = scorer._clause_stats.get(clause_hash)

    if not stats or stats.get("total_uses", 0) == 0:
        raise HTTPException(404, "Clause hash not found in history")

    # Calculate entropy from historical data
    dispute_rate = stats["disputes"] / stats["total_uses"]
    modification_rate = stats["modifications"] / stats["total_uses"]

    return {
        "clause_hash": clause_hash,
        "historical_dispute_rate": round(dispute_rate, 4),
        "historical_modification_rate": round(modification_rate, 4),
        "sample_size": stats["total_uses"],
        "avg_resolution_days": (
            round(sum(stats["resolution_times"]) / len(stats["resolution_times"]), 1)
            if stats["resolution_times"] else None
        ),
        "avg_resolution_cost": (
            round(sum(stats["resolution_costs"]) / len(stats["resolution_costs"]), 2)
            if stats["resolution_costs"] else None
        ),
    }


@router.post("/record/dispute")
async def record_dispute(request: DisputeRecordRequest) -> Dict[str, str]:
    """
    Record a dispute for model training.

    Improves prediction accuracy over time.

    Args:
        request: Dispute details

    Returns:
        Confirmation
    """
    scorer = get_entropy_scorer()

    # Create dispute record
    import hashlib
    clause_hash = hashlib.sha256(
        " ".join(request.clause_text.lower().split()).encode()
    ).hexdigest()[:16]

    record = DisputeRecord(
        clause_hash=clause_hash,
        clause_text=request.clause_text[:200],
        dispute_type=request.dispute_type,
        resolution_time_days=request.resolution_time_days,
        resolution_cost_usd=request.resolution_cost_usd,
        outcome=request.outcome,
        timestamp=datetime.utcnow(),
    )

    scorer.record_dispute(record)

    return {
        "status": "recorded",
        "clause_hash": clause_hash,
        "message": "Dispute recorded for model improvement",
    }


@router.get("/categories")
async def list_categories() -> Dict[str, List[str]]:
    """
    List available clause categories.

    Returns:
        List of category names and descriptions
    """
    return {
        "categories": [cat.value for cat in ClauseCategory],
        "dispute_types": [dt.value for dt in DisputeType],
        "entropy_levels": [level.value for level in EntropyLevel],
    }


@router.get("/stats")
async def get_statistics() -> Dict[str, Any]:
    """
    Get aggregate statistics from the entropy oracle.

    Returns:
        Statistical summary of analyzed clauses
    """
    scorer = get_entropy_scorer()
    analyzer = get_pattern_analyzer()

    # Aggregate statistics
    total_clauses = sum(
        stats.get("total_uses", 0)
        for stats in scorer._clause_stats.values()
    )
    total_disputes = sum(
        stats.get("disputes", 0)
        for stats in scorer._clause_stats.values()
    )

    return {
        "total_clauses_analyzed": total_clauses,
        "total_disputes_recorded": total_disputes,
        "overall_dispute_rate": (
            round(total_disputes / total_clauses, 4) if total_clauses > 0 else 0
        ),
        "unique_patterns": len(analyzer._patterns),
        "category_stats": analyzer.get_category_stats(),
        "high_risk_patterns": [
            p.to_dict() for p in analyzer.get_high_risk_patterns()
        ],
    }


@router.post("/batch/score")
async def batch_score_clauses(
    clauses: List[str] = Query(..., max_length=50)
) -> Dict[str, Any]:
    """
    Score multiple clauses in a single request.

    Args:
        clauses: List of clause texts (max 50)

    Returns:
        Scores for all clauses
    """
    scorer = get_entropy_scorer()

    results = []
    for clause in clauses:
        result = scorer.score_clause(clause)
        results.append({
            "clause_hash": result.clause_hash,
            "entropy_score": round(result.entropy_score, 4),
            "level": result.level.value,
        })

    avg_entropy = sum(cast(float, r["entropy_score"]) for r in results) / len(results)

    return {
        "count": len(results),
        "avg_entropy": round(avg_entropy, 4),
        "results": results,
    }
