"""
Buyer Agent for interacting with Negotiator Agents.

This is a lightweight agent that represents the buyer's side
of the negotiation.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class BuyerAgent:
    """
    Buyer-side agent for license negotiations.

    This agent helps buyers interact with Negotiator Agents to
    explore licensing options and reach agreements.
    """

    def __init__(self, name: str = "Buyer"):
        """
        Initialize the BuyerAgent.

        Args:
            name: Identifier for this buyer
        """
        self.name = name
        self.interaction_history: List[Dict[str, Any]] = []
        self.budget: Optional[str] = None
        self.requirements: List[str] = []

    def set_budget(self, budget: str) -> None:
        """
        Set the buyer's budget.

        Args:
            budget: Budget string (e.g., "0.1 ETH")
        """
        self.budget = budget

    def add_requirement(self, requirement: str) -> None:
        """
        Add a requirement for the license.

        Args:
            requirement: Description of a requirement
        """
        self.requirements.append(requirement)

    def compose_message(
        self,
        intent: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compose a message to send to the Negotiator Agent.

        Args:
            intent: Type of message (e.g., "inquire", "offer", "accept")
            details: Additional details for the message

        Returns:
            Formatted message string
        """
        details = details or {}

        if intent == "inquire_price":
            return self._compose_price_inquiry()

        elif intent == "inquire_features":
            return self._compose_feature_inquiry()

        elif intent == "inquire_terms":
            return "Can you provide details about the licensing terms and conditions?"

        elif intent == "make_offer":
            offer = details.get("offer", self.budget)
            reason = details.get("reason", "")
            return self._compose_offer(offer, reason)

        elif intent == "accept":
            return "I accept these terms. How do we proceed with the purchase?"

        elif intent == "reject":
            reason = details.get("reason", "doesn't meet our requirements")
            return f"Thank you for your time, but this {reason}. I'll need to pass."

        elif intent == "custom":
            return details.get("message", "I have a question about the repository.")

        else:
            return f"I'm interested in learning more about licensing this repository."

    def _compose_price_inquiry(self) -> str:
        """Compose a price inquiry message."""
        if self.budget:
            return f"What's your pricing? I have a budget of around {self.budget}."
        return "What's your pricing for this license?"

    def _compose_feature_inquiry(self) -> str:
        """Compose a feature inquiry message."""
        if self.requirements:
            req_str = ", ".join(self.requirements[:3])
            return f"What features are included? I specifically need: {req_str}."
        return "What features and capabilities are included in the license?"

    def _compose_offer(self, offer: str, reason: str = "") -> str:
        """Compose a price offer message."""
        base = f"I'd like to offer {offer} for this license."

        if reason:
            base += f" {reason}"

        if self.requirements:
            base += f" This would need to include {', '.join(self.requirements[:2])}."

        return base

    def send_message(
        self,
        negotiator,
        intent: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send a message to a Negotiator Agent and get response.

        Args:
            negotiator: NegotiatorAgent instance
            intent: Message intent
            details: Additional message details

        Returns:
            Response from the negotiator
        """
        message = self.compose_message(intent, details)

        # Log outgoing message
        self._log_interaction("sent", message)

        # Get response
        response = negotiator.respond(message)

        # Log response
        self._log_interaction("received", response)

        return response

    def _log_interaction(self, direction: str, content: str) -> None:
        """
        Log an interaction.

        Args:
            direction: "sent" or "received"
            content: Message content
        """
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "direction": direction,
            "content": content,
        })

    def get_interaction_history(self) -> List[Dict[str, Any]]:
        """
        Get the full interaction history.

        Returns:
            List of interaction records
        """
        return self.interaction_history

    def simulate_negotiation(
        self,
        negotiator,
        strategy: str = "direct"
    ) -> Dict[str, Any]:
        """
        Simulate a full negotiation with a Negotiator Agent.

        Args:
            negotiator: NegotiatorAgent instance
            strategy: Negotiation strategy ("direct", "haggle", "explore")

        Returns:
            Summary of the negotiation
        """
        # Start negotiation
        intro = negotiator.start_negotiation()
        self._log_interaction("received", intro)

        if strategy == "direct":
            # Direct approach: Ask about terms and accept if reasonable
            self.send_message(negotiator, "inquire_price")
            self.send_message(negotiator, "inquire_features")
            response = self.send_message(negotiator, "accept")

        elif strategy == "haggle":
            # Haggling approach: Make lower offer first
            self.send_message(negotiator, "inquire_price")

            # Counter with lower offer if budget is set
            if self.budget:
                import re
                match = re.search(r'(\d+\.?\d*)', self.budget)
                if match:
                    amount = float(match.group(1))
                    lower_amount = amount * 0.7  # Offer 70% of budget
                    currency = self.budget.split()[-1]

                    self.send_message(
                        negotiator,
                        "make_offer",
                        {"offer": f"{lower_amount} {currency}"}
                    )

            # Then accept or continue
            response = self.send_message(negotiator, "accept")

        else:  # explore
            # Exploratory approach: Ask many questions
            self.send_message(negotiator, "inquire_features")
            self.send_message(negotiator, "inquire_terms")
            self.send_message(negotiator, "inquire_price")
            response = self.send_message(negotiator, "accept")

        return {
            "buyer": self.name,
            "strategy": strategy,
            "messages_exchanged": len(self.interaction_history),
            "final_response": response,
            "negotiation_summary": negotiator.get_negotiation_summary(),
        }
