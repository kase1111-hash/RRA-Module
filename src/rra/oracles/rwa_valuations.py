# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
RWA Valuation Oracles module.

Provides valuation services for real-world assets:
- Multiple valuation methodologies
- Oracle aggregation and consensus
- Historical valuation tracking
- Confidence scoring
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import statistics


class ValuationMethod(Enum):
    """Asset valuation methodologies."""

    MARKET_COMPARABLE = "market_comparable"  # Comparable sales analysis
    INCOME_APPROACH = "income_approach"  # DCF / income capitalization
    COST_APPROACH = "cost_approach"  # Replacement/reproduction cost
    ROYALTY_RELIEF = "royalty_relief"  # Relief from royalty method
    EXCESS_EARNINGS = "excess_earnings"  # Multi-period excess earnings
    OPTION_PRICING = "option_pricing"  # Real options valuation
    AUCTION_BASED = "auction_based"  # Recent auction/sale data
    EXPERT_OPINION = "expert_opinion"  # Qualified appraiser opinion
    ALGORITHMIC = "algorithmic"  # AI/ML based valuation


class AssetCategory(Enum):
    """Categories for valuation purposes."""

    PATENT = "patent"
    TRADEMARK = "trademark"
    COPYRIGHT = "copyright"
    TRADE_SECRET = "trade_secret"
    PHYSICAL_IP = "physical_ip"
    HYBRID = "hybrid"


@dataclass
class ValuationInput:
    """Input data for valuation calculation."""

    # Basic info
    asset_category: AssetCategory
    asset_type: str
    registration_number: Optional[str] = None

    # Income metrics
    annual_revenue: Optional[Decimal] = None
    royalty_rate: Optional[Decimal] = None  # As decimal, e.g., 0.05 for 5%
    license_fees: Optional[Decimal] = None
    remaining_life_years: Optional[int] = None

    # Cost metrics
    development_cost: Optional[Decimal] = None
    replacement_cost: Optional[Decimal] = None
    maintenance_cost_annual: Optional[Decimal] = None

    # Market metrics
    comparable_sales: List[Decimal] = field(default_factory=list)
    market_multiples: Optional[Dict[str, Decimal]] = None

    # Risk factors
    technology_obsolescence_risk: Optional[Decimal] = None  # 0-1
    legal_risk: Optional[Decimal] = None  # 0-1
    market_risk: Optional[Decimal] = None  # 0-1

    # Additional context
    industry_sector: Optional[str] = None
    geographic_scope: Optional[str] = None
    exclusivity: bool = True


@dataclass
class ValuationResult:
    """Result of a valuation calculation."""

    valuation_id: str
    asset_id: str
    method: ValuationMethod

    estimated_value: Decimal
    low_estimate: Decimal
    high_estimate: Decimal
    confidence_score: int  # 0-10000 basis points

    methodology_hash: str  # Hash of methodology document
    oracle_address: str
    calculation_details: Dict = field(default_factory=dict)

    calculated_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=90))


@dataclass
class ConsensusValuation:
    """Aggregated valuation from multiple oracles."""

    consensus_id: str
    asset_id: str

    # Aggregated values
    consensus_value: Decimal
    weighted_average: Decimal
    median_value: Decimal
    low_estimate: Decimal
    high_estimate: Decimal

    # Confidence
    confidence_score: int  # 0-10000
    agreement_score: int  # How well oracles agree (0-10000)

    # Source data
    individual_valuations: List[ValuationResult] = field(default_factory=list)
    oracle_count: int = 0

    calculated_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))


@dataclass
class OracleReputation:
    """Reputation metrics for a valuation oracle."""

    oracle_address: str
    accuracy_score: int = 5000  # 0-10000, starts at 50%
    total_valuations: int = 0
    successful_valuations: int = 0
    average_deviation: Decimal = Decimal("0")
    specializations: List[AssetCategory] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_active: Optional[datetime] = None
    is_active: bool = True


class ValuationOracle:
    """
    Individual valuation oracle implementation.

    Provides valuation calculations using various methodologies.
    """

    def __init__(self, oracle_address: str, specializations: Optional[List[AssetCategory]] = None):
        self.oracle_address = oracle_address
        self.specializations = specializations or list(AssetCategory)
        self._valuation_counter = 0

        # Default parameters
        self._discount_rates: Dict[AssetCategory, Decimal] = {
            AssetCategory.PATENT: Decimal("0.15"),  # 15% for patents
            AssetCategory.TRADEMARK: Decimal("0.12"),  # 12% for trademarks
            AssetCategory.COPYRIGHT: Decimal("0.10"),  # 10% for copyrights
            AssetCategory.TRADE_SECRET: Decimal("0.20"),  # 20% for trade secrets
            AssetCategory.PHYSICAL_IP: Decimal("0.08"),  # 8% for physical IP
            AssetCategory.HYBRID: Decimal("0.14"),  # 14% for hybrid
        }

    def calculate_valuation(
        self, asset_id: str, inputs: ValuationInput, method: ValuationMethod
    ) -> ValuationResult:
        """Calculate valuation using specified method."""
        self._valuation_counter += 1
        valuation_id = f"val_{self.oracle_address[:8]}_{self._valuation_counter}"

        if method == ValuationMethod.INCOME_APPROACH:
            result = self._income_valuation(inputs)
        elif method == ValuationMethod.MARKET_COMPARABLE:
            result = self._market_comparable_valuation(inputs)
        elif method == ValuationMethod.COST_APPROACH:
            result = self._cost_valuation(inputs)
        elif method == ValuationMethod.ROYALTY_RELIEF:
            result = self._royalty_relief_valuation(inputs)
        elif method == ValuationMethod.EXCESS_EARNINGS:
            result = self._excess_earnings_valuation(inputs)
        else:
            # Default to hybrid approach
            result = self._hybrid_valuation(inputs)

        estimated_value, low_estimate, high_estimate, confidence, details = result

        # Generate methodology hash
        methodology_hash = self._generate_methodology_hash(method, inputs.asset_category)

        return ValuationResult(
            valuation_id=valuation_id,
            asset_id=asset_id,
            method=method,
            estimated_value=estimated_value,
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            confidence_score=confidence,
            methodology_hash=methodology_hash,
            calculation_details=details,
            oracle_address=self.oracle_address,
        )

    def _income_valuation(
        self, inputs: ValuationInput
    ) -> Tuple[Decimal, Decimal, Decimal, int, Dict]:
        """Income approach / DCF valuation."""
        if not inputs.annual_revenue or not inputs.remaining_life_years:
            return Decimal("0"), Decimal("0"), Decimal("0"), 0, {"error": "Missing income data"}

        discount_rate = self._discount_rates.get(inputs.asset_category, Decimal("0.12"))

        # Apply risk adjustments
        if inputs.technology_obsolescence_risk:
            discount_rate += inputs.technology_obsolescence_risk * Decimal("0.05")
        if inputs.legal_risk:
            discount_rate += inputs.legal_risk * Decimal("0.03")
        if inputs.market_risk:
            discount_rate += inputs.market_risk * Decimal("0.04")

        # Calculate NPV of future cash flows
        npv = Decimal("0")
        for year in range(1, inputs.remaining_life_years + 1):
            # Assume declining revenue over time
            decay_factor = Decimal(str(0.95 ** (year - 1)))
            annual_cf = inputs.annual_revenue * decay_factor
            if inputs.royalty_rate:
                annual_cf = annual_cf * inputs.royalty_rate

            discount_factor = Decimal(str((1 + float(discount_rate)) ** year))
            npv += annual_cf / discount_factor

        # Calculate range
        estimated_value = npv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        low_estimate = (estimated_value * Decimal("0.7")).quantize(Decimal("0.01"))
        high_estimate = (estimated_value * Decimal("1.3")).quantize(Decimal("0.01"))

        # Confidence based on data quality
        confidence = 7500  # Base 75%
        if inputs.royalty_rate:
            confidence += 500
        if inputs.remaining_life_years > 5:
            confidence += 500

        details = {
            "method": "income_approach",
            "discount_rate": str(discount_rate),
            "remaining_years": inputs.remaining_life_years,
            "annual_revenue": str(inputs.annual_revenue),
        }

        return estimated_value, low_estimate, high_estimate, min(confidence, 9500), details

    def _market_comparable_valuation(
        self, inputs: ValuationInput
    ) -> Tuple[Decimal, Decimal, Decimal, int, Dict]:
        """Market comparable valuation."""
        if not inputs.comparable_sales or len(inputs.comparable_sales) < 2:
            return (
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                0,
                {"error": "Insufficient comparables"},
            )

        # Calculate statistics
        sales = [float(s) for s in inputs.comparable_sales]
        mean_value = Decimal(str(statistics.mean(sales)))
        median_value = Decimal(str(statistics.median(sales)))
        stdev = Decimal(str(statistics.stdev(sales))) if len(sales) > 1 else Decimal("0")

        # Use median as primary estimate (more robust to outliers)
        estimated_value = median_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        low_estimate = (estimated_value - stdev).quantize(Decimal("0.01"))
        high_estimate = (estimated_value + stdev).quantize(Decimal("0.01"))

        # Ensure positive values
        low_estimate = max(low_estimate, Decimal("0"))

        # Confidence based on number of comparables and variance
        confidence = min(5000 + len(inputs.comparable_sales) * 500, 8500)

        # Reduce confidence if high variance
        if stdev > estimated_value * Decimal("0.3"):
            confidence -= 1000

        details = {
            "method": "market_comparable",
            "comparables_count": len(inputs.comparable_sales),
            "mean_value": str(mean_value),
            "median_value": str(median_value),
            "std_deviation": str(stdev),
        }

        return estimated_value, low_estimate, high_estimate, max(confidence, 3000), details

    def _cost_valuation(
        self, inputs: ValuationInput
    ) -> Tuple[Decimal, Decimal, Decimal, int, Dict]:
        """Cost approach valuation."""
        if not inputs.development_cost and not inputs.replacement_cost:
            return Decimal("0"), Decimal("0"), Decimal("0"), 0, {"error": "Missing cost data"}

        # Use replacement cost if available, otherwise development cost
        base_cost = inputs.replacement_cost or inputs.development_cost

        # Apply depreciation based on remaining life
        if inputs.remaining_life_years:
            # Assume 20-year typical IP life
            typical_life = 20
            age = typical_life - inputs.remaining_life_years
            depreciation = Decimal(str(min(age / typical_life, 0.8)))  # Max 80% depreciation
            base_cost = base_cost * (Decimal("1") - depreciation)

        # Add maintenance value if ongoing investment
        if inputs.maintenance_cost_annual and inputs.remaining_life_years:
            # NPV of maintenance investment
            discount_rate = self._discount_rates.get(inputs.asset_category, Decimal("0.10"))
            maintenance_value = Decimal("0")
            for year in range(1, min(inputs.remaining_life_years, 10) + 1):
                discount_factor = Decimal(str((1 + float(discount_rate)) ** year))
                maintenance_value += inputs.maintenance_cost_annual / discount_factor
            base_cost += maintenance_value * Decimal("0.5")  # 50% of maintenance adds value

        estimated_value = base_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        low_estimate = (estimated_value * Decimal("0.6")).quantize(Decimal("0.01"))
        high_estimate = (estimated_value * Decimal("1.4")).quantize(Decimal("0.01"))

        confidence = 6000  # Cost approach typically less reliable
        if inputs.replacement_cost:
            confidence += 1000  # Replacement cost more reliable

        details = {
            "method": "cost_approach",
            "base_cost": str(inputs.development_cost or inputs.replacement_cost),
            "depreciation_applied": inputs.remaining_life_years is not None,
        }

        return estimated_value, low_estimate, high_estimate, confidence, details

    def _royalty_relief_valuation(
        self, inputs: ValuationInput
    ) -> Tuple[Decimal, Decimal, Decimal, int, Dict]:
        """Relief from royalty valuation method."""
        if not inputs.annual_revenue or not inputs.royalty_rate:
            return Decimal("0"), Decimal("0"), Decimal("0"), 0, {"error": "Missing royalty data"}

        discount_rate = self._discount_rates.get(inputs.asset_category, Decimal("0.12"))
        remaining_years = inputs.remaining_life_years or 10

        # Calculate royalty savings
        npv = Decimal("0")
        for year in range(1, remaining_years + 1):
            royalty_savings = inputs.annual_revenue * inputs.royalty_rate
            discount_factor = Decimal(str((1 + float(discount_rate)) ** year))
            npv += royalty_savings / discount_factor

        estimated_value = npv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        low_estimate = (estimated_value * Decimal("0.75")).quantize(Decimal("0.01"))
        high_estimate = (estimated_value * Decimal("1.25")).quantize(Decimal("0.01"))

        confidence = 8000  # Royalty relief is well-established method

        details = {
            "method": "royalty_relief",
            "royalty_rate": str(inputs.royalty_rate),
            "discount_rate": str(discount_rate),
            "remaining_years": remaining_years,
        }

        return estimated_value, low_estimate, high_estimate, confidence, details

    def _excess_earnings_valuation(
        self, inputs: ValuationInput
    ) -> Tuple[Decimal, Decimal, Decimal, int, Dict]:
        """Multi-period excess earnings method."""
        if not inputs.annual_revenue:
            return Decimal("0"), Decimal("0"), Decimal("0"), 0, {"error": "Missing revenue data"}

        # Assume a portion of revenue is excess earnings attributable to IP
        excess_rate = Decimal("0.15")  # 15% of revenue as excess
        discount_rate = self._discount_rates.get(inputs.asset_category, Decimal("0.15"))
        remaining_years = inputs.remaining_life_years or 10

        npv = Decimal("0")
        for year in range(1, remaining_years + 1):
            excess_earnings = inputs.annual_revenue * excess_rate
            discount_factor = Decimal(str((1 + float(discount_rate)) ** year))
            npv += excess_earnings / discount_factor

        estimated_value = npv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        low_estimate = (estimated_value * Decimal("0.6")).quantize(Decimal("0.01"))
        high_estimate = (estimated_value * Decimal("1.5")).quantize(Decimal("0.01"))

        confidence = 6500  # More speculative method

        details = {
            "method": "excess_earnings",
            "excess_rate": str(excess_rate),
            "discount_rate": str(discount_rate),
        }

        return estimated_value, low_estimate, high_estimate, confidence, details

    def _hybrid_valuation(
        self, inputs: ValuationInput
    ) -> Tuple[Decimal, Decimal, Decimal, int, Dict]:
        """Hybrid valuation combining multiple methods."""
        results = []
        weights = []

        # Try each applicable method
        if inputs.annual_revenue and inputs.remaining_life_years:
            income_result = self._income_valuation(inputs)
            if income_result[0] > 0:
                results.append(income_result)
                weights.append(Decimal("0.35"))

        if inputs.comparable_sales and len(inputs.comparable_sales) >= 2:
            market_result = self._market_comparable_valuation(inputs)
            if market_result[0] > 0:
                results.append(market_result)
                weights.append(Decimal("0.30"))

        if inputs.development_cost or inputs.replacement_cost:
            cost_result = self._cost_valuation(inputs)
            if cost_result[0] > 0:
                results.append(cost_result)
                weights.append(Decimal("0.20"))

        if inputs.annual_revenue and inputs.royalty_rate:
            royalty_result = self._royalty_relief_valuation(inputs)
            if royalty_result[0] > 0:
                results.append(royalty_result)
                weights.append(Decimal("0.15"))

        if not results:
            return (
                Decimal("0"),
                Decimal("0"),
                Decimal("0"),
                0,
                {"error": "Insufficient data for any method"},
            )

        # Normalize weights
        total_weight = sum(weights[: len(results)])
        weights = [w / total_weight for w in weights[: len(results)]]

        # Weighted average
        estimated_value = sum(r[0] * w for r, w in zip(results, weights))
        low_estimate = sum(r[1] * w for r, w in zip(results, weights))
        high_estimate = sum(r[2] * w for r, w in zip(results, weights))
        weighted_confidence = sum(r[3] * float(w) for r, w in zip(results, weights))

        estimated_value = estimated_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        low_estimate = low_estimate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        high_estimate = high_estimate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        details = {
            "method": "hybrid",
            "methods_used": len(results),
            "weights": [str(w) for w in weights],
        }

        return estimated_value, low_estimate, high_estimate, int(weighted_confidence), details

    def _generate_methodology_hash(self, method: ValuationMethod, category: AssetCategory) -> str:
        """Generate hash representing the methodology used."""
        methodology_string = f"{method.value}:{category.value}:v1.0"
        return hashlib.sha256(methodology_string.encode()).hexdigest()[:16]


class ValuationOracleAggregator:
    """
    Aggregates valuations from multiple oracles.

    Provides consensus valuations with confidence scoring.
    """

    def __init__(self, min_oracles: int = 3):
        self.min_oracles = min_oracles
        self._oracles: Dict[str, ValuationOracle] = {}
        self._oracle_reputations: Dict[str, OracleReputation] = {}
        self._consensus_counter = 0
        self._valuation_history: Dict[str, List[ConsensusValuation]] = {}

    def register_oracle(self, oracle: ValuationOracle) -> OracleReputation:
        """Register a valuation oracle."""
        self._oracles[oracle.oracle_address] = oracle

        reputation = OracleReputation(
            oracle_address=oracle.oracle_address,
            specializations=oracle.specializations,
        )
        self._oracle_reputations[oracle.oracle_address] = reputation

        return reputation

    def get_oracle(self, oracle_address: str) -> Optional[ValuationOracle]:
        """Get a registered oracle."""
        return self._oracles.get(oracle_address)

    def get_oracle_reputation(self, oracle_address: str) -> Optional[OracleReputation]:
        """Get oracle reputation."""
        return self._oracle_reputations.get(oracle_address)

    def request_valuation(
        self, asset_id: str, inputs: ValuationInput, methods: Optional[List[ValuationMethod]] = None
    ) -> ConsensusValuation:
        """Request valuations from multiple oracles and aggregate."""
        if len(self._oracles) < self.min_oracles:
            raise ValueError(f"Need at least {self.min_oracles} oracles, have {len(self._oracles)}")

        methods = methods or [ValuationMethod.INCOME_APPROACH, ValuationMethod.ROYALTY_RELIEF]

        individual_valuations = []

        # Collect valuations from each oracle
        for oracle_address, oracle in self._oracles.items():
            reputation = self._oracle_reputations.get(oracle_address)
            if not reputation or not reputation.is_active:
                continue

            # Check specialization
            if inputs.asset_category not in oracle.specializations:
                continue

            for method in methods:
                try:
                    result = oracle.calculate_valuation(asset_id, inputs, method)
                    if result.estimated_value > 0:
                        individual_valuations.append(result)

                        # Update oracle reputation
                        reputation.total_valuations += 1
                        reputation.last_active = datetime.utcnow()
                except Exception:
                    pass  # Skip failed valuations

        if not individual_valuations:
            raise ValueError("No valid valuations received")

        # Calculate consensus
        consensus = self._calculate_consensus(asset_id, individual_valuations)

        # Store history
        if asset_id not in self._valuation_history:
            self._valuation_history[asset_id] = []
        self._valuation_history[asset_id].append(consensus)

        return consensus

    def get_valuation_history(self, asset_id: str) -> List[ConsensusValuation]:
        """Get historical valuations for an asset."""
        return self._valuation_history.get(asset_id, [])

    def update_oracle_accuracy(
        self, oracle_address: str, actual_value: Decimal, predicted_value: Decimal
    ):
        """Update oracle accuracy based on actual vs predicted value."""
        reputation = self._oracle_reputations.get(oracle_address)
        if not reputation:
            return

        # Calculate deviation
        if actual_value > 0:
            deviation = abs(predicted_value - actual_value) / actual_value

            # Update average deviation (rolling average)
            reputation.average_deviation = reputation.average_deviation * Decimal(
                "0.9"
            ) + deviation * Decimal("0.1")

            # Update accuracy score
            if deviation < Decimal("0.1"):  # Within 10%
                reputation.successful_valuations += 1
                reputation.accuracy_score = min(reputation.accuracy_score + 100, 10000)
            elif deviation < Decimal("0.25"):  # Within 25%
                reputation.successful_valuations += 1
                reputation.accuracy_score = min(reputation.accuracy_score + 50, 10000)
            else:
                reputation.accuracy_score = max(reputation.accuracy_score - 100, 0)

    def _calculate_consensus(
        self, asset_id: str, valuations: List[ValuationResult]
    ) -> ConsensusValuation:
        """Calculate consensus from multiple valuations."""
        self._consensus_counter += 1
        consensus_id = f"consensus_{self._consensus_counter}"

        # Extract values and weights
        values = []
        weights = []

        for val in valuations:
            # Weight by confidence and oracle reputation
            reputation = self._oracle_reputations.get(val.oracle_address)
            oracle_weight = reputation.accuracy_score / 10000 if reputation else 0.5

            total_weight = (val.confidence_score / 10000) * oracle_weight
            values.append(float(val.estimated_value))
            weights.append(total_weight)

        # Calculate weighted average
        total_weight = sum(weights)
        if total_weight == 0:
            weighted_avg = Decimal(str(statistics.mean(values)))
        else:
            weighted_avg = Decimal(str(sum(v * w for v, w in zip(values, weights)) / total_weight))

        # Calculate median and range
        median_val = Decimal(str(statistics.median(values)))
        low_estimates = [float(v.low_estimate) for v in valuations]
        high_estimates = [float(v.high_estimate) for v in valuations]

        low_estimate = Decimal(str(min(low_estimates)))
        high_estimate = Decimal(str(max(high_estimates)))

        # Calculate agreement score (how close valuations are)
        if len(values) > 1:
            stdev = statistics.stdev(values)
            mean_val = statistics.mean(values)
            cv = stdev / mean_val if mean_val > 0 else 1  # Coefficient of variation
            agreement_score = int(max(0, min(10000, 10000 * (1 - cv))))
        else:
            agreement_score = 5000  # Neutral for single valuation

        # Confidence is average of individual confidences, adjusted by agreement
        avg_confidence = sum(v.confidence_score for v in valuations) / len(valuations)
        confidence_score = int(avg_confidence * (agreement_score / 10000))

        return ConsensusValuation(
            consensus_id=consensus_id,
            asset_id=asset_id,
            consensus_value=weighted_avg.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            weighted_average=weighted_avg.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            median_value=median_val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            low_estimate=low_estimate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            high_estimate=high_estimate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            confidence_score=confidence_score,
            agreement_score=agreement_score,
            individual_valuations=valuations,
            oracle_count=len(set(v.oracle_address for v in valuations)),
        )


def create_valuation_oracle(
    oracle_address: str, specializations: Optional[List[AssetCategory]] = None
) -> ValuationOracle:
    """Factory function to create a ValuationOracle."""
    return ValuationOracle(oracle_address, specializations)


def create_valuation_aggregator(min_oracles: int = 3) -> ValuationOracleAggregator:
    """Factory function to create a ValuationOracleAggregator."""
    return ValuationOracleAggregator(min_oracles)
