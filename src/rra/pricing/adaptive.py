# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Adaptive Pricing System for RRA Module.

Implements dynamic pricing based on:
- Market demand (views, negotiations)
- Conversion rates
- Competitor pricing
- Time-based patterns
- Buyer behavior signals
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from collections import deque


class PricingStrategy(Enum):
    """Available pricing strategies."""

    FIXED = "fixed"  # No adaptation
    DEMAND_BASED = "demand_based"  # Adjust based on demand
    CONVERSION_OPTIMIZED = "conversion_optimized"  # Optimize for conversions
    REVENUE_MAXIMIZED = "revenue_maximized"  # Maximize revenue
    COMPETITIVE = "competitive"  # Match market prices
    TIME_DECAY = "time_decay"  # Price decreases over time
    SURGE = "surge"  # Increase during high demand


@dataclass
class PriceSignal:
    """A signal that influences pricing."""

    signal_type: str
    value: float
    weight: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PricingMetrics:
    """Metrics used for pricing decisions."""

    views_24h: int = 0
    views_7d: int = 0
    negotiations_24h: int = 0
    negotiations_7d: int = 0
    conversions_24h: int = 0
    conversions_7d: int = 0
    avg_negotiation_rounds: float = 0.0
    avg_final_discount: float = 0.0
    competitor_avg_price: Optional[float] = None
    market_position: str = "average"  # low, average, premium
    last_sale_price: Optional[float] = None
    last_sale_at: Optional[str] = None


@dataclass
class PriceRecommendation:
    """A pricing recommendation from the adaptive system."""

    recommended_price: float
    confidence: float  # 0-1
    reasoning: str
    factors: List[str]
    price_range: Tuple[float, float]  # (min, max)
    strategy_used: PricingStrategy


class AdaptivePricingEngine:
    """
    Adaptive pricing engine that learns from market signals.

    Uses multiple strategies to recommend optimal prices based on:
    - Historical data
    - Market conditions
    - Buyer behavior
    - Competitor analysis
    """

    # Price adjustment bounds
    MIN_ADJUSTMENT = 0.7  # Max 30% decrease
    MAX_ADJUSTMENT = 1.5  # Max 50% increase

    # Strategy weights
    DEFAULT_WEIGHTS = {
        "demand": 0.3,
        "conversion": 0.25,
        "competition": 0.2,
        "recency": 0.15,
        "seasonality": 0.1,
    }

    def __init__(
        self,
        base_price: float,
        strategy: PricingStrategy = PricingStrategy.DEMAND_BASED,
        storage_path: Path = None,
    ):
        """
        Initialize the adaptive pricing engine.

        Args:
            base_price: Base price for the repository
            strategy: Pricing strategy to use
            storage_path: Path for signal storage
        """
        self.base_price = base_price
        self.strategy = strategy
        self.storage_path = storage_path or Path("data/pricing")
        self._signals: deque = deque(maxlen=1000)
        self._price_history: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self) -> None:
        """Load historical data."""
        if self.storage_path.exists():
            try:
                signals_file = self.storage_path / "signals.json"
                if signals_file.exists():
                    with open(signals_file, "r") as f:
                        data = json.load(f)
                        for s in data:
                            self._signals.append(PriceSignal(**s))

                history_file = self.storage_path / "history.json"
                if history_file.exists():
                    with open(history_file, "r") as f:
                        self._price_history = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_data(self) -> None:
        """Save data to storage."""
        self.storage_path.mkdir(parents=True, exist_ok=True)

        signals_file = self.storage_path / "signals.json"
        with open(signals_file, "w") as f:
            json.dump([s.__dict__ for s in self._signals], f, indent=2, default=str)

        history_file = self.storage_path / "history.json"
        with open(history_file, "w") as f:
            json.dump(self._price_history, f, indent=2, default=str)

    def record_signal(self, signal: PriceSignal) -> None:
        """
        Record a pricing signal.

        Args:
            signal: The signal to record
        """
        self._signals.append(signal)
        self._save_data()

    def record_view(self) -> None:
        """Record a page view signal."""
        self.record_signal(
            PriceSignal(
                signal_type="view",
                value=1.0,
                weight=0.1,
            )
        )

    def record_negotiation_start(self) -> None:
        """Record a negotiation start signal."""
        self.record_signal(
            PriceSignal(
                signal_type="negotiation_start",
                value=1.0,
                weight=0.5,
            )
        )

    def record_negotiation_complete(
        self, final_price: float, rounds: int, discount_percent: float
    ) -> None:
        """Record a completed negotiation."""
        self.record_signal(
            PriceSignal(
                signal_type="negotiation_complete",
                value=final_price,
                weight=1.0,
                metadata={
                    "rounds": rounds,
                    "discount_percent": discount_percent,
                },
            )
        )

    def record_sale(self, sale_price: float) -> None:
        """Record a sale signal."""
        self.record_signal(
            PriceSignal(
                signal_type="sale",
                value=sale_price,
                weight=2.0,
            )
        )

        self._price_history.append(
            {
                "price": sale_price,
                "timestamp": datetime.utcnow().isoformat(),
                "base_price": self.base_price,
            }
        )
        self._save_data()

    def get_metrics(self) -> PricingMetrics:
        """
        Calculate current pricing metrics from signals.

        Returns:
            Aggregated pricing metrics
        """
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        metrics = PricingMetrics()

        for signal in self._signals:
            signal_time = datetime.fromisoformat(signal.timestamp)

            if signal.signal_type == "view":
                if signal_time >= day_ago:
                    metrics.views_24h += 1
                if signal_time >= week_ago:
                    metrics.views_7d += 1

            elif signal.signal_type == "negotiation_start":
                if signal_time >= day_ago:
                    metrics.negotiations_24h += 1
                if signal_time >= week_ago:
                    metrics.negotiations_7d += 1

            elif signal.signal_type == "sale":
                if signal_time >= day_ago:
                    metrics.conversions_24h += 1
                if signal_time >= week_ago:
                    metrics.conversions_7d += 1
                metrics.last_sale_price = signal.value
                metrics.last_sale_at = signal.timestamp

            elif signal.signal_type == "negotiation_complete":
                meta = signal.metadata
                if meta.get("rounds"):
                    # Running average
                    if metrics.avg_negotiation_rounds == 0:
                        metrics.avg_negotiation_rounds = meta["rounds"]
                    else:
                        metrics.avg_negotiation_rounds = (
                            metrics.avg_negotiation_rounds * 0.9 + meta["rounds"] * 0.1
                        )
                if meta.get("discount_percent"):
                    if metrics.avg_final_discount == 0:
                        metrics.avg_final_discount = meta["discount_percent"]
                    else:
                        metrics.avg_final_discount = (
                            metrics.avg_final_discount * 0.9 + meta["discount_percent"] * 0.1
                        )

        return metrics

    def _calculate_demand_factor(self, metrics: PricingMetrics) -> float:
        """
        Calculate demand-based price adjustment factor.

        Returns:
            Adjustment factor (e.g., 1.1 = 10% increase)
        """
        # Views to negotiation conversion
        view_to_neg = metrics.negotiations_7d / metrics.views_7d if metrics.views_7d > 0 else 0

        # High demand indicators
        if metrics.views_24h > 50 and view_to_neg > 0.1:
            return 1.2  # 20% increase
        elif metrics.views_24h > 20 and view_to_neg > 0.05:
            return 1.1  # 10% increase
        elif metrics.views_7d < 5:
            return 0.9  # 10% decrease (low demand)
        else:
            return 1.0

    def _calculate_conversion_factor(self, metrics: PricingMetrics) -> float:
        """
        Calculate conversion-optimized price adjustment.

        Returns:
            Adjustment factor
        """
        # If negotiations happen but few convert, price might be too high
        if metrics.negotiations_7d > 5 and metrics.conversions_7d == 0:
            return 0.85  # 15% decrease

        # If high discount needed to close, base price too high
        if metrics.avg_final_discount > 30:
            return 0.9  # 10% decrease

        # If conversions are high with low discount, room to increase
        if metrics.conversions_7d > 3 and metrics.avg_final_discount < 10:
            return 1.15  # 15% increase

        return 1.0

    def _calculate_recency_factor(self, metrics: PricingMetrics) -> float:
        """
        Calculate time-based adjustment.

        Returns:
            Adjustment factor
        """
        if not metrics.last_sale_at:
            return 1.0

        last_sale = datetime.fromisoformat(metrics.last_sale_at)
        days_since = (datetime.utcnow() - last_sale).days

        if days_since > 90:
            return 0.85  # 15% decrease if no sales in 90 days
        elif days_since > 30:
            return 0.95  # 5% decrease if no sales in 30 days
        elif days_since < 7 and metrics.conversions_7d > 2:
            return 1.1  # 10% increase if selling well recently

        return 1.0

    def _calculate_seasonality_factor(self) -> float:
        """
        Calculate seasonal adjustment.

        Returns:
            Adjustment factor
        """
        now = datetime.utcnow()

        # Q4 typically higher demand (budget season)
        if now.month in [10, 11, 12]:
            return 1.05

        # Summer typically lower
        if now.month in [6, 7, 8]:
            return 0.95

        return 1.0

    def get_recommendation(
        self,
        competitor_price: float = None,
    ) -> PriceRecommendation:
        """
        Get a price recommendation based on current signals.

        Args:
            competitor_price: Optional competitor's price for comparison

        Returns:
            Price recommendation with reasoning
        """
        metrics = self.get_metrics()
        if competitor_price:
            metrics.competitor_avg_price = competitor_price

        factors = []
        adjustments = []

        # Apply strategy-specific logic
        if self.strategy == PricingStrategy.FIXED:
            return PriceRecommendation(
                recommended_price=self.base_price,
                confidence=1.0,
                reasoning="Fixed pricing strategy - no adjustments",
                factors=["fixed_strategy"],
                price_range=(self.base_price, self.base_price),
                strategy_used=self.strategy,
            )

        # Demand factor
        demand_factor = self._calculate_demand_factor(metrics)
        if demand_factor != 1.0:
            factors.append(f"demand_adjustment: {demand_factor:.2f}x")
            adjustments.append(demand_factor * self.DEFAULT_WEIGHTS["demand"])

        # Conversion factor
        if self.strategy in [
            PricingStrategy.CONVERSION_OPTIMIZED,
            PricingStrategy.REVENUE_MAXIMIZED,
        ]:
            conv_factor = self._calculate_conversion_factor(metrics)
            if conv_factor != 1.0:
                factors.append(f"conversion_adjustment: {conv_factor:.2f}x")
                adjustments.append(conv_factor * self.DEFAULT_WEIGHTS["conversion"])

        # Competition factor
        if self.strategy == PricingStrategy.COMPETITIVE and competitor_price:
            comp_ratio = competitor_price / self.base_price
            if comp_ratio < 0.8:
                factors.append("competitor_undercutting")
                adjustments.append(0.85)
            elif comp_ratio > 1.2:
                factors.append("premium_positioning_available")
                adjustments.append(1.1)

        # Recency factor
        recency_factor = self._calculate_recency_factor(metrics)
        if recency_factor != 1.0:
            factors.append(f"recency_adjustment: {recency_factor:.2f}x")
            adjustments.append(recency_factor * self.DEFAULT_WEIGHTS["recency"])

        # Seasonality
        season_factor = self._calculate_seasonality_factor()
        if season_factor != 1.0:
            factors.append(f"seasonal_adjustment: {season_factor:.2f}x")
            adjustments.append(season_factor * self.DEFAULT_WEIGHTS["seasonality"])

        # Calculate final adjustment
        if adjustments:
            # Weighted geometric mean of adjustments
            final_adjustment = 1.0
            for adj in adjustments:
                final_adjustment *= adj
            final_adjustment = final_adjustment ** (1 / len(adjustments))
        else:
            final_adjustment = 1.0

        # Apply bounds
        final_adjustment = max(self.MIN_ADJUSTMENT, min(self.MAX_ADJUSTMENT, final_adjustment))

        recommended = self.base_price * final_adjustment

        # Calculate confidence based on data quality
        data_points = len(self._signals)
        confidence = min(0.9, 0.3 + (data_points / 100) * 0.6)

        # Calculate price range
        min_price = self.base_price * self.MIN_ADJUSTMENT
        max_price = self.base_price * self.MAX_ADJUSTMENT

        # Build reasoning
        if final_adjustment > 1.0:
            reasoning = f"Recommend increasing price by {(final_adjustment - 1) * 100:.1f}% based on positive signals"
        elif final_adjustment < 1.0:
            reasoning = f"Recommend decreasing price by {(1 - final_adjustment) * 100:.1f}% to improve conversions"
        else:
            reasoning = "Current price appears optimal based on available data"

        return PriceRecommendation(
            recommended_price=round(recommended, 2),
            confidence=round(confidence, 2),
            reasoning=reasoning,
            factors=factors if factors else ["no_significant_factors"],
            price_range=(round(min_price, 2), round(max_price, 2)),
            strategy_used=self.strategy,
        )

    def get_price_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get price history for the specified period.

        Args:
            days: Number of days to look back

        Returns:
            List of historical prices
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [p for p in self._price_history if datetime.fromisoformat(p["timestamp"]) >= cutoff]

    def simulate_price(
        self,
        test_price: float,
        expected_views: int = 100,
    ) -> Dict[str, Any]:
        """
        Simulate expected outcomes at a given price point.

        Args:
            test_price: Price to simulate
            expected_views: Expected number of views

        Returns:
            Simulation results
        """
        metrics = self.get_metrics()

        # Price elasticity estimate
        price_ratio = test_price / self.base_price
        elasticity = -1.5  # Typical for software

        # Estimated conversion change
        conv_rate_base = metrics.conversions_7d / metrics.views_7d if metrics.views_7d > 0 else 0.02
        conv_rate_new = conv_rate_base * (price_ratio**elasticity)
        conv_rate_new = max(0.001, min(0.5, conv_rate_new))

        expected_conversions = expected_views * conv_rate_new
        expected_revenue = expected_conversions * test_price

        return {
            "test_price": test_price,
            "price_change_percent": (price_ratio - 1) * 100,
            "expected_conversion_rate": round(conv_rate_new * 100, 2),
            "expected_conversions": round(expected_conversions, 1),
            "expected_revenue": round(expected_revenue, 2),
            "revenue_vs_base": (
                round(expected_revenue / (expected_views * conv_rate_base * self.base_price) - 1, 2)
                if conv_rate_base > 0
                else 0
            ),
        }


# =============================================================================
# Factory Function
# =============================================================================


def create_pricing_engine(
    base_price: float,
    strategy: str = "demand_based",
    repo_id: str = None,
) -> AdaptivePricingEngine:
    """
    Create an adaptive pricing engine.

    Args:
        base_price: Base price for the item
        strategy: Pricing strategy name
        repo_id: Optional repo ID for storage isolation

    Returns:
        Configured pricing engine
    """
    strategy_enum = PricingStrategy(strategy)
    storage_path = Path(f"data/pricing/{repo_id}") if repo_id else None

    return AdaptivePricingEngine(
        base_price=base_price,
        strategy=strategy_enum,
        storage_path=storage_path,
    )
