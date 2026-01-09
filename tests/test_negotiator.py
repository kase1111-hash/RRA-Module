# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for negotiation agent."""

import pytest
from pathlib import Path

from rra.agents.negotiator import NegotiatorAgent, NegotiationPhase
from rra.agents.buyer import BuyerAgent
from rra.ingestion.knowledge_base import KnowledgeBase
from rra.config.market_config import MarketConfig, LicenseModel, NegotiationStyle
from rra.exceptions import ConfigurationError


@pytest.fixture
def sample_kb():
    """Create a sample knowledge base for testing."""
    kb = KnowledgeBase(repo_path=Path("."), repo_url="https://github.com/test/repo.git")

    kb.market_config = MarketConfig(
        target_price="0.05 ETH",
        floor_price="0.02 ETH",
        license_model=LicenseModel.PER_SEAT,
        negotiation_style=NegotiationStyle.CONCISE,
        features=["Full access", "Updates", "Support"],
    )

    kb.statistics = {
        "total_files": 100,
        "code_files": 80,
        "total_lines": 3000,
        "languages": ["Python"],
    }

    return kb


def test_negotiator_creation(sample_kb):
    """Test creating a negotiator agent."""
    negotiator = NegotiatorAgent(sample_kb)

    assert negotiator.kb == sample_kb
    assert negotiator.config == sample_kb.market_config
    assert negotiator.current_phase == NegotiationPhase.INTRODUCTION


def test_negotiator_without_config():
    """Test that negotiator requires market config."""
    kb = KnowledgeBase(repo_path=Path("."), repo_url="https://github.com/test/repo.git")

    with pytest.raises(ConfigurationError):
        NegotiatorAgent(kb)


def test_start_negotiation(sample_kb):
    """Test starting a negotiation."""
    negotiator = NegotiatorAgent(sample_kb)
    intro = negotiator.start_negotiation()

    assert isinstance(intro, str)
    assert len(intro) > 0
    assert "0.05 ETH" in intro  # Should mention price
    assert len(negotiator.negotiation_history) == 1


def test_respond_to_message(sample_kb):
    """Test responding to buyer messages."""
    negotiator = NegotiatorAgent(sample_kb)
    negotiator.start_negotiation()

    response = negotiator.respond("What features are included?")

    assert isinstance(response, str)
    assert len(response) > 0
    # Should log: intro + buyer message + negotiator response = 3 messages
    assert len(negotiator.negotiation_history) == 3


def test_price_negotiation(sample_kb):
    """Test price negotiation."""
    negotiator = NegotiatorAgent(sample_kb)
    negotiator.start_negotiation()

    # Offer below floor
    response = negotiator.respond("I can offer 0.01 ETH")
    assert "floor" in response.lower() or "minimum" in response.lower()

    # Offer above floor
    response = negotiator.respond("I can offer 0.03 ETH")
    assert "accept" in response.lower() or "agree" in response.lower()


def test_negotiation_styles(sample_kb):
    """Test different negotiation styles."""
    # Concise
    sample_kb.market_config.negotiation_style = NegotiationStyle.CONCISE
    negotiator = NegotiatorAgent(sample_kb)
    intro_concise = negotiator.start_negotiation()

    # Persuasive
    sample_kb.market_config.negotiation_style = NegotiationStyle.PERSUASIVE
    negotiator = NegotiatorAgent(sample_kb)
    intro_persuasive = negotiator.start_negotiation()

    # Strict
    sample_kb.market_config.negotiation_style = NegotiationStyle.STRICT
    negotiator = NegotiatorAgent(sample_kb)
    intro_strict = negotiator.start_negotiation()

    # Each should be different
    assert intro_concise != intro_persuasive
    assert intro_persuasive != intro_strict
    assert intro_strict != intro_concise


def test_buyer_agent():
    """Test buyer agent functionality."""
    buyer = BuyerAgent(name="TestBuyer")

    buyer.set_budget("0.05 ETH")
    buyer.add_requirement("API access")

    assert buyer.budget == "0.05 ETH"
    assert "API access" in buyer.requirements


def test_full_negotiation_simulation(sample_kb):
    """Test a complete negotiation simulation."""
    negotiator = NegotiatorAgent(sample_kb)
    buyer = BuyerAgent(name="TestBuyer")

    buyer.set_budget("0.04 ETH")

    result = buyer.simulate_negotiation(negotiator, strategy="direct")

    assert result["buyer"] == "TestBuyer"
    assert result["strategy"] == "direct"
    assert result["messages_exchanged"] > 0
    assert "negotiation_summary" in result


def test_negotiation_summary(sample_kb):
    """Test getting negotiation summary."""
    negotiator = NegotiatorAgent(sample_kb)
    negotiator.start_negotiation()
    negotiator.respond("What's the price?")

    summary = negotiator.get_negotiation_summary()

    assert summary["repo"] == sample_kb.repo_url
    # Should have: intro + buyer message + negotiator response = 3 messages
    assert summary["message_count"] == 3
    assert "history" in summary
    assert len(summary["history"]) == 3
