#!/usr/bin/env python3
"""
Simple negotiation example for RRA Module.

This script demonstrates how to:
1. Ingest a repository
2. Create a negotiation agent
3. Simulate a buyer-seller interaction
"""

from pathlib import Path
from rra.ingestion.repo_ingester import RepoIngester
from rra.agents.negotiator import NegotiatorAgent
from rra.agents.buyer import BuyerAgent


def main():
    """Run a simple negotiation simulation."""

    print("=" * 60)
    print("RRA Module - Simple Negotiation Example")
    print("=" * 60)

    # Step 1: Ingest a repository
    print("\n[1] Ingesting repository...")
    repo_url = "https://github.com/example/sample-repo.git"

    ingester = RepoIngester()

    # For this example, we'll simulate with a local repo
    # In production, would use actual GitHub URL
    print(f"Repository: {repo_url}")
    print("(Using simulated ingestion for demo)")

    # Create a mock knowledge base
    from rra.ingestion.knowledge_base import KnowledgeBase
    from rra.config.market_config import MarketConfig, LicenseModel, NegotiationStyle

    kb = KnowledgeBase(
        repo_path=Path("."),
        repo_url=repo_url,
    )

    kb.market_config = MarketConfig(
        target_price="0.05 ETH",
        floor_price="0.02 ETH",
        license_model=LicenseModel.PER_SEAT,
        negotiation_style=NegotiationStyle.PERSUASIVE,
        features=["Full source code", "Updates included", "Developer support"]
    )

    kb.statistics = {
        "total_files": 150,
        "code_files": 120,
        "total_lines": 5000,
        "languages": ["Python", "JavaScript"],
    }

    kb.tests = {
        "test_files": 25,
        "test_functions": 150,
    }

    print("✓ Knowledge base created")

    # Step 2: Create negotiation agent
    print("\n[2] Creating negotiation agent...")
    negotiator = NegotiatorAgent(kb)
    print("✓ Negotiator agent ready")

    # Step 3: Create buyer agent
    print("\n[3] Creating buyer agent...")
    buyer = BuyerAgent(name="TechStartup Inc.")
    buyer.set_budget("0.04 ETH")
    buyer.add_requirement("API access")
    buyer.add_requirement("Commercial use")
    print("✓ Buyer agent ready")

    # Step 4: Run negotiation simulation
    print("\n[4] Running negotiation simulation...")
    print("-" * 60)

    result = buyer.simulate_negotiation(negotiator, strategy="haggle")

    print("-" * 60)
    print(f"\n[5] Negotiation complete!")
    print(f"    Messages exchanged: {result['messages_exchanged']}")
    print(f"    Strategy used: {result['strategy']}")

    # Show summary
    summary = result['negotiation_summary']
    print(f"\n[6] Summary:")
    print(f"    Phase: {summary['phase']}")
    print(f"    Repository: {summary['repo']}")
    print(f"    Total messages: {summary['message_count']}")

    # Show last few messages
    print(f"\n[7] Conversation highlights:")
    history = buyer.get_interaction_history()
    for i, interaction in enumerate(history[-4:], 1):
        direction = "Buyer →" if interaction["direction"] == "sent" else "Seller ←"
        content_preview = interaction["content"][:80] + "..." if len(interaction["content"]) > 80 else interaction["content"]
        print(f"    {direction} {content_preview}")

    print("\n" + "=" * 60)
    print("Simulation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
