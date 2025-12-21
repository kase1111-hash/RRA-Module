# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Off-Chain Event Bridging and Oracles for RRA.

Provides event bridging and validation for dispute evidence:
- Bridge real-world events to on-chain disputes
- Chainlink Functions integration for external data
- Dispute evidence from off-chain sources
- Validated event attestations
- RWA valuation oracles
"""

from .event_bridge import (
    EventSource,
    EventStatus,
    AttestationChoice,
    EventData,
    Attestation,
    BridgedEvent,
    EventFetcher,
    APIEventFetcher,
    IPFSEventFetcher,
    GitHubEventFetcher,
    EventBridge,
    create_event_bridge,
)
from .validators import (
    ValidationResult,
    ValidationReport,
    EventValidator,
    SchemaValidator,
    HashValidator,
    TimestampValidator,
    SignatureValidator,
    CompositeValidator,
    GitHubEventValidator,
    FinancialEventValidator,
    create_schema_validator,
    create_github_validator,
    create_financial_validator,
    create_composite_validator,
)
from .rwa_valuations import (
    ValuationMethod,
    AssetCategory,
    ValuationInput,
    ValuationResult,
    ConsensusValuation,
    OracleReputation,
    ValuationOracle,
    ValuationOracleAggregator,
    create_valuation_oracle,
    create_valuation_aggregator,
)

__all__ = [
    # Event Bridge
    "EventSource",
    "EventStatus",
    "AttestationChoice",
    "EventData",
    "Attestation",
    "BridgedEvent",
    "EventFetcher",
    "APIEventFetcher",
    "IPFSEventFetcher",
    "GitHubEventFetcher",
    "EventBridge",
    "create_event_bridge",
    # Validators
    "ValidationResult",
    "ValidationReport",
    "EventValidator",
    "SchemaValidator",
    "HashValidator",
    "TimestampValidator",
    "SignatureValidator",
    "CompositeValidator",
    "GitHubEventValidator",
    "FinancialEventValidator",
    "create_schema_validator",
    "create_github_validator",
    "create_financial_validator",
    "create_composite_validator",
    # RWA Valuations
    "ValuationMethod",
    "AssetCategory",
    "ValuationInput",
    "ValuationResult",
    "ConsensusValuation",
    "OracleReputation",
    "ValuationOracle",
    "ValuationOracleAggregator",
    "create_valuation_oracle",
    "create_valuation_aggregator",
]
