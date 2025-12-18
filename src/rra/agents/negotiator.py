"""
Negotiator Agent for automated licensing negotiations.

The Negotiator Agent represents the repository owner and conducts
autonomous negotiations with potential buyers based on the .market.yaml
configuration.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from rra.ingestion.knowledge_base import KnowledgeBase
from rra.config.market_config import NegotiationStyle


class NegotiationPhase(str, Enum):
    """Phases of a negotiation."""
    INTRODUCTION = "introduction"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    AGREEMENT = "agreement"
    REJECTED = "rejected"


class NegotiatorAgent:
    """
    Autonomous negotiation agent for repository licensing.

    This agent uses the repository's knowledge base and market configuration
    to conduct intelligent, multi-turn negotiations with buyers.
    """

    def __init__(self, knowledge_base: KnowledgeBase):
        """
        Initialize the NegotiatorAgent.

        Args:
            knowledge_base: KnowledgeBase containing repository information
        """
        self.kb = knowledge_base
        self.config = knowledge_base.market_config

        if not self.config:
            raise ValueError("Knowledge base must have market_config to negotiate")

        self.negotiation_history: List[Dict[str, Any]] = []
        self.current_phase = NegotiationPhase.INTRODUCTION
        self.current_offer: Optional[Dict[str, Any]] = None

    def start_negotiation(self) -> str:
        """
        Start a new negotiation session with an introduction.

        Returns:
            Opening message from the negotiator
        """
        self.negotiation_history = []
        self.current_phase = NegotiationPhase.INTRODUCTION

        context = self.kb.get_negotiation_context()

        # Generate introduction based on negotiation style
        if self.config.negotiation_style == NegotiationStyle.CONCISE:
            intro = self._generate_concise_intro(context)
        elif self.config.negotiation_style == NegotiationStyle.PERSUASIVE:
            intro = self._generate_persuasive_intro(context)
        elif self.config.negotiation_style == NegotiationStyle.STRICT:
            intro = self._generate_strict_intro(context)
        else:  # ADAPTIVE
            intro = self._generate_adaptive_intro(context)

        self._log_message("negotiator", intro)
        return intro

    def respond(self, buyer_message: str) -> str:
        """
        Respond to a buyer's message.

        Args:
            buyer_message: Message from the buyer

        Returns:
            Response from the negotiator
        """
        self._log_message("buyer", buyer_message)

        # Parse buyer intent
        intent = self._parse_buyer_intent(buyer_message)

        # Generate appropriate response
        response = self._generate_response(intent, buyer_message)

        self._log_message("negotiator", response)
        return response

    def _generate_concise_intro(self, context: Dict[str, Any]) -> str:
        """Generate a concise introduction."""
        features = context["pricing"].get("features", [])
        features_str = ", ".join(features[:3]) if features else "full access"

        return f"""Hello! I represent the {self.kb.repo_url} repository.

License Model: {context['pricing']['model']}
Price: {context['pricing']['target_price']}
Includes: {features_str}

What are your licensing needs?"""

    def _generate_persuasive_intro(self, context: Dict[str, Any]) -> str:
        """Generate a persuasive introduction highlighting value."""
        strengths = []

        if context.get("value_propositions"):
            strengths.extend(context["value_propositions"][:2])

        if context.get("strengths"):
            strengths.extend(context["strengths"][:2])

        strengths_str = "\n".join(f"  - {s}" for s in strengths) if strengths else "  - Production-ready code"

        return f"""Welcome! I'm excited to discuss licensing for {self.kb.repo_url}.

This is a proven, high-quality codebase with:
{strengths_str}

Our {context['pricing']['model']} licensing starts at {context['pricing']['target_price']},
offering exceptional value for your project.

May I learn more about your use case to tailor the perfect licensing arrangement?"""

    def _generate_strict_intro(self, context: Dict[str, Any]) -> str:
        """Generate a strict, no-nonsense introduction."""
        return f"""Repository Licensing Terms

Repository: {self.kb.repo_url}
License Model: {context['pricing']['model']}
Price: {context['pricing']['target_price']} (non-negotiable)
Floor Price: {context['pricing']['floor_price']}

Terms are as specified. Please confirm if you wish to proceed."""

    def _generate_adaptive_intro(self, context: Dict[str, Any]) -> str:
        """Generate an adaptive introduction."""
        return f"""Hello! I'm the licensing agent for {self.kb.repo_url}.

I offer flexible {context['pricing']['model']} licensing starting at {context['pricing']['target_price']}.

I can adapt our agreement to your specific needs - whether you're a solo developer,
startup, or enterprise.

What's your intended use case?"""

    def _parse_buyer_intent(self, message: str) -> Dict[str, Any]:
        """
        Parse buyer's message to understand intent.

        This is a simplified implementation. In production, would use
        NLP/LLM for more sophisticated intent recognition.
        """
        message_lower = message.lower()

        intent = {
            "type": "general",
            "asks_about_price": False,
            "proposes_price": False,
            "asks_about_features": False,
            "asks_about_terms": False,
            "ready_to_purchase": False,
            "proposed_amount": None,
        }

        # Price-related
        if any(word in message_lower for word in ["price", "cost", "how much", "expensive", "cheap"]):
            intent["asks_about_price"] = True

        if any(word in message_lower for word in ["offer", "would pay", "can do", "counter"]):
            intent["proposes_price"] = True
            # Try to extract amount (simplified)
            import re
            price_match = re.search(r'(\d+\.?\d*)\s*(eth|usdc|usd|\$)', message_lower)
            if price_match:
                intent["proposed_amount"] = f"{price_match.group(1)} {price_match.group(2).upper()}"

        # Feature-related
        if any(word in message_lower for word in ["feature", "include", "what do", "capability"]):
            intent["asks_about_features"] = True

        # Terms-related
        if any(word in message_lower for word in ["term", "condition", "duration", "license"]):
            intent["asks_about_terms"] = True

        # Ready to purchase
        if any(word in message_lower for word in ["accept", "agree", "purchase", "buy", "deal"]):
            intent["ready_to_purchase"] = True
            intent["type"] = "purchase"

        return intent

    def _generate_response(self, intent: Dict[str, Any], message: str) -> str:
        """
        Generate appropriate response based on buyer intent.

        Args:
            intent: Parsed buyer intent
            message: Original buyer message

        Returns:
            Response string
        """
        context = self.kb.get_negotiation_context()

        # Handle purchase intent
        if intent["ready_to_purchase"]:
            self.current_phase = NegotiationPhase.AGREEMENT
            return self._generate_agreement_response(context)

        # Handle price inquiry
        if intent["asks_about_price"]:
            return self._generate_price_response(context)

        # Handle price proposal
        if intent["proposes_price"] and intent["proposed_amount"]:
            return self._handle_price_negotiation(intent["proposed_amount"], context)

        # Handle feature inquiry
        if intent["asks_about_features"]:
            return self._generate_feature_response(context)

        # Handle terms inquiry
        if intent["asks_about_terms"]:
            return self._generate_terms_response(context)

        # Default response
        return self._generate_default_response(context)

    def _generate_price_response(self, context: Dict[str, Any]) -> str:
        """Generate response to price inquiry."""
        if self.config.negotiation_style == NegotiationStyle.STRICT:
            return f"""The price is fixed at {context['pricing']['target_price']}.
Minimum acceptable price is {context['pricing']['floor_price']}.
No further negotiation available."""

        return f"""Our target price is {context['pricing']['target_price']}, with a floor of {context['pricing']['floor_price']}.

Given the repository's value - {len(context.get('value_propositions', []))} key strengths -
this represents fair market value.

I'm open to discussing terms that work for both of us. What's your budget?"""

    def _handle_price_negotiation(self, proposed_amount: str, context: Dict[str, Any]) -> str:
        """
        Handle a price negotiation.

        Args:
            proposed_amount: Buyer's proposed price
            context: Negotiation context

        Returns:
            Response to the proposal
        """
        self.current_phase = NegotiationPhase.NEGOTIATION

        # Extract numeric value (simplified)
        try:
            import re
            match = re.search(r'(\d+\.?\d*)', proposed_amount)
            if match:
                proposed_value = float(match.group(1))

                # Compare with floor price (simplified - assumes ETH)
                floor_match = re.search(r'(\d+\.?\d*)', context['pricing']['floor_price'])
                floor_value = float(floor_match.group(1)) if floor_match else 0

                if proposed_value >= floor_value:
                    # Acceptable offer
                    return f"""Your offer of {proposed_amount} is within acceptable range.

I can agree to {proposed_amount} for a {context['pricing']['model']} license
including all standard features.

Shall we proceed with the transaction?"""
                else:
                    # Below floor
                    if self.config.negotiation_style == NegotiationStyle.STRICT:
                        return f"""Your offer of {proposed_amount} is below our floor price of {context['pricing']['floor_price']}.
I cannot accept offers below this threshold. Final offer: {context['pricing']['floor_price']}."""

                    return f"""I appreciate your offer of {proposed_amount}, but that's below our floor price of {context['pricing']['floor_price']}.

Given the repository's proven value - including {', '.join(context.get('value_propositions', [])[:2])} -
I can meet you at {context['pricing']['floor_price']}.

This is the best I can offer while maintaining the quality and support you deserve."""

        except:
            pass

        # Fallback if parsing fails
        return f"""I'd like to consider your offer, but I need clarification on the amount.

Our pricing range is {context['pricing']['floor_price']} to {context['pricing']['target_price']}.
Can you provide a specific offer within this range?"""

    def _generate_feature_response(self, context: Dict[str, Any]) -> str:
        """Generate response about features."""
        features = context["pricing"].get("features", [])

        if not features:
            features = [
                "Full source code access",
                "Regular updates",
                "Documentation",
                "Basic support"
            ]

        features_str = "\n".join(f"  - {f}" for f in features)

        tech_details = context.get("technical_details", {})
        languages = tech_details.get("languages", [])
        lang_str = f" Written in {', '.join(languages)}." if languages else ""

        return f"""This license includes:
{features_str}

{lang_str}
{tech_details.get('lines_of_code', 0):,} lines of production-ready code.

What specific capabilities are you looking for?"""

    def _generate_terms_response(self, context: Dict[str, Any]) -> str:
        """Generate response about licensing terms."""
        terms = [
            f"License Type: {context['pricing']['model']}",
            f"Price: {context['pricing']['target_price']}",
        ]

        if self.config.min_license_duration:
            terms.append(f"Minimum Duration: {self.config.min_license_duration}")

        if self.config.auto_renewal:
            terms.append("Auto-renewal: Enabled")

        if self.config.allow_custom_fork_rights:
            terms.append("Fork Rights: Negotiable")

        if self.config.royalty_on_derivatives:
            royalty_pct = self.config.royalty_on_derivatives * 100
            terms.append(f"Derivative Royalty: {royalty_pct}%")

        terms_str = "\n".join(f"  - {t}" for t in terms)

        return f"""Licensing Terms:
{terms_str}

All licenses are enforced via smart contracts on Ethereum, ensuring
transparent and automatic rights management.

Any questions about specific terms?"""

    def _generate_agreement_response(self, context: Dict[str, Any]) -> str:
        """Generate response when buyer agrees to purchase."""
        price = self.current_offer["price"] if self.current_offer else context['pricing']['target_price']

        return f"""Excellent! I'm pleased we've reached an agreement.

Final Terms:
  - License: {context['pricing']['model']}
  - Price: {price}
  - Repository: {self.kb.repo_url}

Next Steps:
  1. Smart contract will be deployed with these terms
  2. You'll receive payment instructions (Ethereum address)
  3. Upon payment confirmation, a Cryptographic Grant Token (NFT) will be minted
  4. Token grants automatic access to the repository

Transaction ID will be provided for your records.

Proceed with payment?"""

    def _generate_default_response(self, context: Dict[str, Any]) -> str:
        """Generate default response for unclear intents."""
        return f"""I'm here to help you find the right licensing arrangement for {self.kb.repo_url}.

You can ask me about:
  - Pricing and payment options
  - Features and capabilities
  - License terms and conditions
  - Technical specifications

Or we can proceed directly if you're ready. What would you like to know?"""

    def _log_message(self, sender: str, content: str) -> None:
        """Log a message in the negotiation history."""
        self.negotiation_history.append({
            "timestamp": datetime.now().isoformat(),
            "sender": sender,
            "content": content,
            "phase": self.current_phase.value,
        })

    def get_negotiation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current negotiation state.

        Returns:
            Dictionary containing negotiation status and history
        """
        return {
            "repo": self.kb.repo_url,
            "phase": self.current_phase.value,
            "message_count": len(self.negotiation_history),
            "history": self.negotiation_history,
            "current_offer": self.current_offer,
        }
