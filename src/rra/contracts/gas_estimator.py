# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Dynamic Gas Estimation for Smart Contract Transactions.

Provides intelligent gas estimation with:
- Dynamic estimation based on actual transaction simulation
- Safety buffers for complex transactions
- Historical gas usage tracking
- Fallback values when estimation fails
- Gas price optimization (EIP-1559 support)

Addresses M-003: Fixed gas limits - consider dynamic estimation.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)


class GasEstimationStrategy(str, Enum):
    """Gas estimation strategies."""

    DYNAMIC = "dynamic"  # Estimate from node
    HISTORICAL = "historical"  # Use historical averages
    FIXED = "fixed"  # Use fixed fallback values
    AGGRESSIVE = "aggressive"  # Minimal buffer (risky)
    CONSERVATIVE = "conservative"  # Large buffer (safe but expensive)


class TransactionType(str, Enum):
    """Types of contract transactions with different gas profiles."""

    DEPLOY = "deploy"
    REGISTER_REPOSITORY = "register_repository"
    ISSUE_LICENSE = "issue_license"
    TRANSFER_LICENSE = "transfer_license"
    REVOKE_LICENSE = "revoke_license"
    UPDATE_METADATA = "update_metadata"
    BATCH_OPERATION = "batch_operation"
    GENERIC = "generic"


@dataclass
class GasEstimate:
    """
    Gas estimation result with metadata.

    Includes the estimate, buffer applied, and confidence level.
    """

    gas_limit: int
    estimated_gas: int
    buffer_applied: float  # Multiplier (e.g., 1.2 = 20% buffer)
    strategy_used: GasEstimationStrategy
    confidence: float  # 0-1, lower for fallback estimates
    gas_price_wei: Optional[int] = None
    max_fee_per_gas: Optional[int] = None  # EIP-1559
    max_priority_fee: Optional[int] = None  # EIP-1559
    estimated_cost_wei: Optional[int] = None

    @property
    def estimated_cost_eth(self) -> Optional[Decimal]:
        """Get estimated cost in ETH."""
        if self.estimated_cost_wei is None:
            return None
        return Decimal(self.estimated_cost_wei) / Decimal(10**18)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gas_limit": self.gas_limit,
            "estimated_gas": self.estimated_gas,
            "buffer_applied": self.buffer_applied,
            "strategy": self.strategy_used.value,
            "confidence": self.confidence,
            "gas_price_wei": self.gas_price_wei,
            "max_fee_per_gas": self.max_fee_per_gas,
            "max_priority_fee": self.max_priority_fee,
            "estimated_cost_wei": self.estimated_cost_wei,
            "estimated_cost_eth": str(self.estimated_cost_eth) if self.estimated_cost_eth else None,
        }


@dataclass
class GasHistoryEntry:
    """Historical gas usage entry."""

    transaction_type: TransactionType
    gas_used: int
    gas_limit: int
    timestamp: float
    success: bool


class GasEstimator:
    """
    Dynamic gas estimator for smart contract transactions.

    Features:
    - Estimates gas using node simulation
    - Applies configurable safety buffers
    - Tracks historical gas usage
    - Provides fallback values when estimation fails
    - Supports EIP-1559 gas pricing
    """

    # Default fallback gas limits by transaction type
    DEFAULT_GAS_LIMITS: Dict[TransactionType, int] = {
        TransactionType.DEPLOY: 5_000_000,
        TransactionType.REGISTER_REPOSITORY: 300_000,
        TransactionType.ISSUE_LICENSE: 500_000,
        TransactionType.TRANSFER_LICENSE: 150_000,
        TransactionType.REVOKE_LICENSE: 100_000,
        TransactionType.UPDATE_METADATA: 200_000,
        TransactionType.BATCH_OPERATION: 1_000_000,
        TransactionType.GENERIC: 300_000,
    }

    # Buffer multipliers by strategy
    BUFFER_MULTIPLIERS: Dict[GasEstimationStrategy, float] = {
        GasEstimationStrategy.DYNAMIC: 1.2,  # 20% buffer
        GasEstimationStrategy.HISTORICAL: 1.3,  # 30% buffer
        GasEstimationStrategy.FIXED: 1.5,  # 50% buffer
        GasEstimationStrategy.AGGRESSIVE: 1.05,  # 5% buffer
        GasEstimationStrategy.CONSERVATIVE: 2.0,  # 100% buffer
    }

    # Maximum gas limit (block limit safety)
    MAX_GAS_LIMIT = 30_000_000

    def __init__(
        self,
        web3: Optional[Any] = None,
        default_strategy: GasEstimationStrategy = GasEstimationStrategy.DYNAMIC,
        custom_buffers: Optional[Dict[TransactionType, float]] = None,
        track_history: bool = True,
        max_history_size: int = 1000,
    ):
        """
        Initialize the gas estimator.

        Args:
            web3: Web3 instance for dynamic estimation
            default_strategy: Default estimation strategy
            custom_buffers: Custom buffer multipliers by transaction type
            track_history: Whether to track historical gas usage
            max_history_size: Maximum history entries to keep
        """
        self.web3 = web3
        self.default_strategy = default_strategy
        self.custom_buffers = custom_buffers or {}
        self.track_history = track_history
        self.max_history_size = max_history_size

        self._history: List[GasHistoryEntry] = []
        self._average_gas: Dict[TransactionType, int] = {}

    def estimate(
        self,
        transaction_type: TransactionType,
        transaction: Optional[Dict[str, Any]] = None,
        from_address: Optional[str] = None,
        strategy: Optional[GasEstimationStrategy] = None,
    ) -> GasEstimate:
        """
        Estimate gas for a transaction.

        Args:
            transaction_type: Type of transaction
            transaction: Transaction dict for dynamic estimation
            from_address: Sender address for estimation
            strategy: Override default strategy

        Returns:
            GasEstimate with recommended gas limit
        """
        strategy = strategy or self.default_strategy

        # Try dynamic estimation first if web3 available and transaction provided
        if (
            strategy == GasEstimationStrategy.DYNAMIC
            and self.web3
            and transaction
        ):
            try:
                estimate = self._estimate_dynamic(transaction, from_address)
                if estimate is not None:
                    return self._apply_buffer(
                        estimate,
                        transaction_type,
                        strategy,
                        confidence=0.9,
                    )
            except Exception as e:
                logger.warning(f"Dynamic gas estimation failed: {e}")

        # Try historical estimation
        if strategy in [GasEstimationStrategy.DYNAMIC, GasEstimationStrategy.HISTORICAL]:
            historical = self._get_historical_average(transaction_type)
            if historical is not None:
                return self._apply_buffer(
                    historical,
                    transaction_type,
                    GasEstimationStrategy.HISTORICAL,
                    confidence=0.7,
                )

        # Fall back to fixed values
        return self._get_fallback_estimate(transaction_type, strategy)

    def estimate_with_gas_price(
        self,
        transaction_type: TransactionType,
        transaction: Optional[Dict[str, Any]] = None,
        from_address: Optional[str] = None,
        strategy: Optional[GasEstimationStrategy] = None,
        use_eip1559: bool = True,
    ) -> GasEstimate:
        """
        Estimate gas and gas price for a transaction.

        Args:
            transaction_type: Type of transaction
            transaction: Transaction dict for dynamic estimation
            from_address: Sender address for estimation
            strategy: Override default strategy
            use_eip1559: Use EIP-1559 pricing if available

        Returns:
            GasEstimate with gas limit and price
        """
        estimate = self.estimate(transaction_type, transaction, from_address, strategy)

        if not self.web3:
            return estimate

        try:
            if use_eip1559 and self._supports_eip1559():
                # Get EIP-1559 gas prices
                base_fee = self.web3.eth.get_block("latest").get("baseFeePerGas", 0)
                max_priority_fee = self._get_priority_fee()
                max_fee = base_fee * 2 + max_priority_fee

                estimate.max_fee_per_gas = max_fee
                estimate.max_priority_fee = max_priority_fee
                estimate.estimated_cost_wei = estimate.gas_limit * max_fee
            else:
                # Legacy gas price
                gas_price = self.web3.eth.gas_price
                estimate.gas_price_wei = gas_price
                estimate.estimated_cost_wei = estimate.gas_limit * gas_price

        except Exception as e:
            logger.warning(f"Failed to get gas price: {e}")

        return estimate

    def record_gas_used(
        self,
        transaction_type: TransactionType,
        gas_used: int,
        gas_limit: int,
        success: bool = True,
    ) -> None:
        """
        Record actual gas used for a transaction.

        Updates historical averages for future estimates.

        Args:
            transaction_type: Type of transaction
            gas_used: Actual gas used
            gas_limit: Gas limit that was set
            success: Whether transaction succeeded
        """
        if not self.track_history:
            return

        import time

        entry = GasHistoryEntry(
            transaction_type=transaction_type,
            gas_used=gas_used,
            gas_limit=gas_limit,
            timestamp=time.time(),
            success=success,
        )

        self._history.append(entry)

        # Trim history if needed
        if len(self._history) > self.max_history_size:
            self._history = self._history[-self.max_history_size:]

        # Update average
        self._update_average(transaction_type)

    def get_transaction_params(
        self,
        transaction_type: TransactionType,
        base_params: Dict[str, Any],
        from_address: str,
        use_eip1559: bool = True,
    ) -> Dict[str, Any]:
        """
        Get complete transaction parameters with gas estimation.

        Convenience method that returns ready-to-use transaction params.

        Args:
            transaction_type: Type of transaction
            base_params: Base transaction parameters
            from_address: Sender address
            use_eip1559: Use EIP-1559 pricing

        Returns:
            Complete transaction parameters dict
        """
        estimate = self.estimate_with_gas_price(
            transaction_type=transaction_type,
            transaction=base_params,
            from_address=from_address,
            use_eip1559=use_eip1559,
        )

        params = {**base_params}
        params["gas"] = estimate.gas_limit

        if estimate.max_fee_per_gas is not None:
            params["maxFeePerGas"] = estimate.max_fee_per_gas
            params["maxPriorityFeePerGas"] = estimate.max_priority_fee
        elif estimate.gas_price_wei is not None:
            params["gasPrice"] = estimate.gas_price_wei

        return params

    def _estimate_dynamic(
        self,
        transaction: Dict[str, Any],
        from_address: Optional[str],
    ) -> Optional[int]:
        """Estimate gas using node simulation."""
        if not self.web3:
            return None

        try:
            tx = {**transaction}
            if from_address:
                tx["from"] = from_address

            # Remove gas-related fields for estimation
            tx.pop("gas", None)
            tx.pop("gasPrice", None)
            tx.pop("maxFeePerGas", None)
            tx.pop("maxPriorityFeePerGas", None)

            estimated = self.web3.eth.estimate_gas(tx)
            return estimated

        except Exception as e:
            logger.debug(f"Dynamic estimation failed: {e}")
            return None

    def _get_historical_average(self, transaction_type: TransactionType) -> Optional[int]:
        """Get historical average gas for transaction type."""
        if transaction_type in self._average_gas:
            return self._average_gas[transaction_type]
        return None

    def _update_average(self, transaction_type: TransactionType) -> None:
        """Update historical average for transaction type."""
        relevant = [
            e.gas_used
            for e in self._history
            if e.transaction_type == transaction_type and e.success
        ]

        if relevant:
            # Use weighted average favoring recent transactions
            if len(relevant) >= 5:
                # Weight recent more heavily
                weights = [1 + (i / len(relevant)) for i in range(len(relevant))]
                weighted_sum = sum(g * w for g, w in zip(relevant, weights))
                self._average_gas[transaction_type] = int(weighted_sum / sum(weights))
            else:
                self._average_gas[transaction_type] = int(sum(relevant) / len(relevant))

    def _get_fallback_estimate(
        self,
        transaction_type: TransactionType,
        strategy: GasEstimationStrategy,
    ) -> GasEstimate:
        """Get fallback gas estimate."""
        fallback = self.DEFAULT_GAS_LIMITS.get(
            transaction_type,
            self.DEFAULT_GAS_LIMITS[TransactionType.GENERIC],
        )

        return self._apply_buffer(
            fallback,
            transaction_type,
            GasEstimationStrategy.FIXED,
            confidence=0.5,
        )

    def _apply_buffer(
        self,
        estimated_gas: int,
        transaction_type: TransactionType,
        strategy: GasEstimationStrategy,
        confidence: float,
    ) -> GasEstimate:
        """Apply buffer to gas estimate."""
        # Get buffer multiplier
        buffer = self.custom_buffers.get(
            transaction_type,
            self.BUFFER_MULTIPLIERS.get(strategy, 1.2),
        )

        # Calculate buffered gas limit
        gas_limit = int(estimated_gas * buffer)

        # Enforce maximum
        gas_limit = min(gas_limit, self.MAX_GAS_LIMIT)

        return GasEstimate(
            gas_limit=gas_limit,
            estimated_gas=estimated_gas,
            buffer_applied=buffer,
            strategy_used=strategy,
            confidence=confidence,
        )

    def _supports_eip1559(self) -> bool:
        """Check if network supports EIP-1559."""
        if not self.web3:
            return False

        try:
            block = self.web3.eth.get_block("latest")
            return "baseFeePerGas" in block
        except Exception:
            return False

    def _get_priority_fee(self) -> int:
        """Get recommended priority fee."""
        if not self.web3:
            return 1_500_000_000  # 1.5 Gwei default

        try:
            # Try to get from fee history
            fee_history = self.web3.eth.fee_history(5, "latest", [50])
            rewards = fee_history.get("reward", [])
            if rewards:
                # Use median of recent priority fees
                fees = [r[0] for r in rewards if r]
                if fees:
                    return sorted(fees)[len(fees) // 2]
        except Exception:
            pass

        return 1_500_000_000  # 1.5 Gwei fallback

    def get_statistics(self) -> Dict[str, Any]:
        """Get gas estimation statistics."""
        return {
            "history_size": len(self._history),
            "averages": {
                t.value: g for t, g in self._average_gas.items()
            },
            "default_strategy": self.default_strategy.value,
            "has_web3": self.web3 is not None,
        }


# Global estimator instance
_gas_estimator: Optional[GasEstimator] = None


def get_gas_estimator(web3: Optional[Any] = None) -> GasEstimator:
    """
    Get the global gas estimator instance.

    Args:
        web3: Web3 instance (used only on first call)

    Returns:
        Configured GasEstimator
    """
    global _gas_estimator
    if _gas_estimator is None:
        _gas_estimator = GasEstimator(web3=web3)
    elif web3 is not None and _gas_estimator.web3 is None:
        _gas_estimator.web3 = web3
    return _gas_estimator


def estimate_gas(
    transaction_type: TransactionType,
    transaction: Optional[Dict[str, Any]] = None,
    web3: Optional[Any] = None,
) -> int:
    """
    Convenience function to estimate gas for a transaction.

    Args:
        transaction_type: Type of transaction
        transaction: Transaction dict for estimation
        web3: Web3 instance

    Returns:
        Recommended gas limit
    """
    estimator = get_gas_estimator(web3)
    estimate = estimator.estimate(transaction_type, transaction)
    return estimate.gas_limit
