# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Predictive Dispute Warning API Endpoints.

Provides REST API for:
- Contract dispute warning generation
- High-entropy term detection
- Warning acknowledgment and resolution
- Risk scoring and analytics

Part of Phase 6.6: Predictive Dispute Warnings
"""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from rra.predictions.dispute_warning import (
    DisputeWarningGenerator,
    DisputeWarning,
    WarningReport,
    WarningSeverity,
    WarningCategory,
)
from rra.analytics.term_analysis import (
    TermAnalyzer,
    TermAnalysis,
    TermReport,
    TermRiskLevel,
    TermCategory,
)


router = APIRouter(prefix="/warnings", tags=["warnings"])

# Singleton instances
_warning_generator: Optional[DisputeWarningGenerator] = None
_term_analyzer: Optional[TermAnalyzer] = None


def get_warning_generator() -> DisputeWarningGenerator:
    """Get or create warning generator instance."""
    global _warning_generator
    if _warning_generator is None:
        _warning_generator = DisputeWarningGenerator()
    return _warning_generator


def get_term_analyzer() -> TermAnalyzer:
    """Get or create term analyzer instance."""
    global _term_analyzer
    if _term_analyzer is None:
        _term_analyzer = TermAnalyzer()
    return _term_analyzer


# =============================================================================
# Request/Response Models
# =============================================================================

class WarningRequest(BaseModel):
    """Request to generate warnings for a contract."""
    clauses: List[str] = Field(..., min_length=1, max_length=100)
    contract_id: Optional[str] = None
    license_type: str = Field(default="commercial", pattern="^(commercial|saas|open_source)$")
    licensee_prior_disputes: int = Field(default=0, ge=0)
    licensor_prior_disputes: int = Field(default=0, ge=0)


class WarningResponse(BaseModel):
    """Response with warning report."""
    contract_id: str
    overall_risk_score: float
    dispute_probability: float
    summary: Dict[str, int]
    warnings: List[Dict[str, Any]]
    prediction: Dict[str, Any]
    generated_at: str


class TermAnalysisRequest(BaseModel):
    """Request to analyze terms in a contract."""
    clauses: List[str] = Field(..., min_length=1, max_length=100)
    contract_id: Optional[str] = None


class TermAnalysisResponse(BaseModel):
    """Response with term analysis."""
    contract_id: str
    summary: Dict[str, Any]
    risk_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    top_concerns: List[str]
    terms: List[Dict[str, Any]]
    analyzed_at: str


class SingleTermRequest(BaseModel):
    """Request to analyze a single term."""
    term: str = Field(..., min_length=1, max_length=100)
    context: Optional[str] = None


class SingleTermResponse(BaseModel):
    """Response with single term analysis."""
    term: str
    normalized_form: str
    category: str
    risk_level: str
    entropy_score: float
    dispute_rate: float
    alternatives: List[str]
    explanation: str


class HighEntropyRequest(BaseModel):
    """Request to find high-entropy terms."""
    clauses: List[str] = Field(..., min_length=1, max_length=100)
    threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class WarningAcknowledgeRequest(BaseModel):
    """Request to acknowledge a warning."""
    warning_id: str


class WarningResolveRequest(BaseModel):
    """Request to resolve a warning."""
    warning_id: str
    resolution_notes: Optional[str] = None


class HealthResponse(BaseModel):
    """API health check response."""
    status: str
    version: str
    warning_history_count: int
    term_database_size: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check for the warnings API.

    Returns:
        API status and version info
    """
    generator = get_warning_generator()
    analyzer = get_term_analyzer()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        warning_history_count=len(generator._warning_history),
        term_database_size=len(analyzer.TERM_DATABASE),
    )


@router.post("/generate", response_model=WarningResponse)
async def generate_warnings(request: WarningRequest) -> WarningResponse:
    """
    Generate dispute warnings for a contract.

    Analyzes contract clauses and returns:
    - Overall risk score
    - Dispute probability
    - Individual warnings with mitigations
    - Prediction details

    Args:
        request: Contract clauses and context

    Returns:
        Complete warning report
    """
    generator = get_warning_generator()

    context = {
        "licensee_prior_disputes": request.licensee_prior_disputes,
        "licensor_prior_disputes": request.licensor_prior_disputes,
    }

    report = generator.generate_warnings(
        clauses=request.clauses,
        contract_id=request.contract_id,
        license_type=request.license_type,
        context=context,
    )

    return WarningResponse(
        contract_id=report.contract_id,
        overall_risk_score=round(report.overall_risk_score, 4),
        dispute_probability=round(report.dispute_probability, 4),
        summary={
            "total": report.total_count,
            "critical": report.critical_count,
            "high": report.high_count,
            "unresolved": report.unresolved_count,
        },
        warnings=[w.to_dict() for w in report.warnings],
        prediction=report.prediction.to_dict(),
        generated_at=report.generated_at.isoformat(),
    )


@router.post("/analyze/terms", response_model=TermAnalysisResponse)
async def analyze_terms(request: TermAnalysisRequest) -> TermAnalysisResponse:
    """
    Analyze terms in contract clauses.

    Identifies high-entropy terms that may lead to disputes.

    Args:
        request: Contract clauses

    Returns:
        Complete term analysis report
    """
    analyzer = get_term_analyzer()

    report = analyzer.analyze_contract(
        clauses=request.clauses,
        contract_id=request.contract_id,
    )

    return TermAnalysisResponse(
        contract_id=report.contract_id,
        summary={
            "term_count": len(report.terms),
            "high_risk_count": report.high_risk_count,
            "total_entropy": round(report.total_entropy, 4),
            "avg_entropy": round(report.avg_entropy, 4),
        },
        risk_distribution={k.value: v for k, v in report.risk_distribution.items()},
        category_distribution={k.value: v for k, v in report.category_distribution.items()},
        top_concerns=report.top_concerns,
        terms=[t.to_dict() for t in report.terms],
        analyzed_at=report.analyzed_at.isoformat(),
    )


@router.post("/analyze/term", response_model=SingleTermResponse)
async def analyze_single_term(request: SingleTermRequest) -> SingleTermResponse:
    """
    Analyze a single term.

    Args:
        request: Term and optional context

    Returns:
        Term analysis with risk assessment
    """
    analyzer = get_term_analyzer()

    analysis = analyzer.analyze_term(
        term=request.term,
        context=request.context,
    )

    return SingleTermResponse(
        term=analysis.term,
        normalized_form=analysis.normalized_form,
        category=analysis.category.value,
        risk_level=analysis.risk_level.value,
        entropy_score=round(analysis.entropy_score, 4),
        dispute_rate=round(analysis.dispute_rate, 4),
        alternatives=analysis.alternatives,
        explanation=analysis.explanation,
    )


@router.post("/high-entropy")
async def find_high_entropy_terms(request: HighEntropyRequest) -> Dict[str, Any]:
    """
    Find high-entropy terms above a threshold.

    Args:
        request: Clauses and threshold

    Returns:
        List of high-entropy terms
    """
    analyzer = get_term_analyzer()

    terms = analyzer.get_high_entropy_terms(
        clauses=request.clauses,
        threshold=request.threshold,
    )

    return {
        "threshold": request.threshold,
        "count": len(terms),
        "terms": [t.to_dict() for t in terms],
        "total_entropy": sum(t.entropy_score for t in terms),
    }


@router.post("/acknowledge")
async def acknowledge_warning(request: WarningAcknowledgeRequest) -> Dict[str, Any]:
    """
    Acknowledge a warning.

    Marks the warning as seen but not yet resolved.

    Args:
        request: Warning ID

    Returns:
        Acknowledgment status
    """
    generator = get_warning_generator()

    success = generator.acknowledge_warning(request.warning_id)

    if not success:
        raise HTTPException(404, f"Warning {request.warning_id} not found")

    return {
        "status": "acknowledged",
        "warning_id": request.warning_id,
    }


@router.post("/resolve")
async def resolve_warning(request: WarningResolveRequest) -> Dict[str, Any]:
    """
    Mark a warning as resolved.

    Indicates the issue has been addressed.

    Args:
        request: Warning ID and optional notes

    Returns:
        Resolution status
    """
    generator = get_warning_generator()

    success = generator.resolve_warning(request.warning_id)

    if not success:
        raise HTTPException(404, f"Warning {request.warning_id} not found")

    return {
        "status": "resolved",
        "warning_id": request.warning_id,
        "notes": request.resolution_notes,
    }


@router.get("/warning/{warning_id}")
async def get_warning(warning_id: str) -> Dict[str, Any]:
    """
    Get a warning by ID.

    Args:
        warning_id: Warning identifier

    Returns:
        Warning details
    """
    generator = get_warning_generator()

    warning = generator.get_warning(warning_id)

    if not warning:
        raise HTTPException(404, f"Warning {warning_id} not found")

    return warning.to_dict()


@router.get("/alternatives/{term}")
async def get_alternatives(term: str) -> Dict[str, Any]:
    """
    Get suggested alternatives for a term.

    Args:
        term: Term to find alternatives for

    Returns:
        List of alternative phrasings
    """
    analyzer = get_term_analyzer()

    alternatives = analyzer.suggest_alternatives(term)

    return {
        "term": term,
        "alternatives": alternatives,
        "count": len(alternatives),
    }


@router.get("/categories")
async def list_categories() -> Dict[str, List[str]]:
    """
    List available warning and term categories.

    Returns:
        Lists of category enums
    """
    return {
        "warning_severities": [s.value for s in WarningSeverity],
        "warning_categories": [c.value for c in WarningCategory],
        "term_risk_levels": [r.value for r in TermRiskLevel],
        "term_categories": [c.value for c in TermCategory],
    }


@router.get("/stats")
async def get_statistics() -> Dict[str, Any]:
    """
    Get aggregate statistics from warning generation.

    Returns:
        Statistical summary
    """
    generator = get_warning_generator()
    analyzer = get_term_analyzer()

    # Count warnings by severity
    severity_counts = {}
    for severity in WarningSeverity:
        severity_counts[severity.value] = sum(
            1 for w in generator._warning_history.values()
            if w.severity == severity
        )

    # Count by category
    category_counts = {}
    for category in WarningCategory:
        category_counts[category.value] = sum(
            1 for w in generator._warning_history.values()
            if w.category == category
        )

    return {
        "total_warnings_generated": len(generator._warning_history),
        "acknowledged_count": sum(
            1 for w in generator._warning_history.values()
            if w.acknowledged
        ),
        "resolved_count": sum(
            1 for w in generator._warning_history.values()
            if w.resolved
        ),
        "severity_distribution": severity_counts,
        "category_distribution": category_counts,
        "known_terms": len(analyzer.TERM_DATABASE),
        "custom_terms": len(analyzer._custom_terms),
    }


@router.post("/batch/analyze")
async def batch_analyze_contracts(
    contracts: List[List[str]] = Query(..., max_length=10),
) -> Dict[str, Any]:
    """
    Analyze multiple contracts in batch.

    Args:
        contracts: List of contracts (each a list of clauses)

    Returns:
        Analysis for all contracts
    """
    generator = get_warning_generator()

    results = []
    for i, clauses in enumerate(contracts):
        report = generator.generate_warnings(clauses)
        results.append({
            "contract_index": i,
            "overall_risk": round(report.overall_risk_score, 4),
            "dispute_probability": round(report.dispute_probability, 4),
            "warning_count": report.total_count,
            "critical_count": report.critical_count,
        })

    avg_risk = sum(r["overall_risk"] for r in results) / len(results)
    avg_prob = sum(r["dispute_probability"] for r in results) / len(results)

    return {
        "count": len(results),
        "avg_risk_score": round(avg_risk, 4),
        "avg_dispute_probability": round(avg_prob, 4),
        "results": results,
    }
