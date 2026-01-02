# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Scoped Delegation for RRA Agent Authorization.

Enables secure agent delegation with hardware-backed limits:
- Users sign delegation scope with YubiKey/hardware authenticator
- Agents can only operate within authorized limits
- Hierarchical permissions (per-action, per-token, per-amount)
- Automatic expiration and revocation

This prevents "Agent Hijacking" where an autonomous agent
performs unauthorized market-matches or stake-transfers.

Example:
    "I authorize this RRA Agent to spend up to 100 USDC
     for market matching, but any transaction over that
     threshold requires a fresh YubiKey touch."
"""

from enum import Enum, auto
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from eth_utils import keccak


class ActionType(Enum):
    """Types of delegatable actions."""

    MARKET_MATCH = auto()  # License marketplace matching
    DISPUTE_STAKE = auto()  # ILRM dispute staking
    LICENSE_TRANSFER = auto()  # License NFT transfers
    METADATA_UPDATE = auto()  # Metadata/URI updates
    WITHDRAW = auto()  # Fund withdrawals
    NEGOTIATE = auto()  # Negotiation actions
    CUSTOM = auto()  # Custom action type


@dataclass
class TokenLimit:
    """Spending limit for a specific token."""

    token_address: str
    max_amount: int
    spent_amount: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_amount - self.spent_amount)

    def can_spend(self, amount: int) -> bool:
        return amount <= self.remaining

    def spend(self, amount: int) -> bool:
        if not self.can_spend(amount):
            return False
        self.spent_amount += amount
        return True


@dataclass
class DelegationScope:
    """
    Defines the scope of a delegation.

    Specifies what actions an agent can perform and with what limits.
    """

    delegation_id: str
    delegator: str  # User's address
    agent: str  # Agent's address
    credential_id_hash: bytes  # Hardware credential used to create
    allowed_actions: Set[ActionType]  # Permitted action types
    token_limits: Dict[str, TokenLimit]  # Token address => limit
    eth_limit: int  # Max ETH spending (in wei)
    eth_spent: int = 0  # ETH spent so far
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    active: bool = True
    requires_fresh_signature: bool = False  # Require new FIDO2 sig per action
    description: str = ""  # Human-readable scope
    custom_actions: Set[str] = field(default_factory=set)  # Custom action hashes

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.active and not self.is_expired

    @property
    def eth_remaining(self) -> int:
        return max(0, self.eth_limit - self.eth_spent)

    def can_perform_action(self, action: ActionType) -> bool:
        """Check if action type is allowed."""
        return action in self.allowed_actions

    def can_spend_eth(self, amount: int) -> bool:
        """Check if ETH amount is within limit."""
        return amount <= self.eth_remaining

    def can_spend_token(self, token_address: str, amount: int) -> bool:
        """Check if token amount is within limit."""
        limit = self.token_limits.get(token_address.lower())
        if not limit:
            return False
        return limit.can_spend(amount)

    def use(self, action: ActionType, token_address: Optional[str] = None, amount: int = 0) -> bool:
        """
        Use delegation for an action.

        Args:
            action: Action type being performed
            token_address: Token address (None for ETH)
            amount: Amount to spend

        Returns:
            True if successful, False if limit exceeded
        """
        if not self.is_valid:
            return False

        if not self.can_perform_action(action):
            return False

        if amount > 0:
            if token_address is None:
                # ETH spending
                if not self.can_spend_eth(amount):
                    return False
                self.eth_spent += amount
            else:
                # Token spending
                if not self.can_spend_token(token_address, amount):
                    return False
                self.token_limits[token_address.lower()].spend(amount)

        return True

    def revoke(self, reason: str = "") -> None:
        """Revoke this delegation."""
        self.active = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "delegation_id": self.delegation_id,
            "delegator": self.delegator,
            "agent": self.agent,
            "credential_id_hash": self.credential_id_hash.hex(),
            "allowed_actions": [a.name for a in self.allowed_actions],
            "token_limits": {
                addr: {"max_amount": limit.max_amount, "spent_amount": limit.spent_amount}
                for addr, limit in self.token_limits.items()
            },
            "eth_limit": self.eth_limit,
            "eth_spent": self.eth_spent,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "active": self.active,
            "requires_fresh_signature": self.requires_fresh_signature,
            "description": self.description,
        }


class ScopedDelegation:
    """
    Manager for scoped agent delegations.

    Enables hardware-backed delegation with spending limits:
    - Creates delegations signed by hardware authenticator
    - Enforces per-action and per-token limits
    - Tracks usage and prevents over-spending
    - Supports delegation revocation
    """

    def __init__(self):
        self.delegations: Dict[str, DelegationScope] = {}
        self.agent_delegations: Dict[str, List[str]] = {}  # agent => delegation_ids
        self.delegator_delegations: Dict[str, List[str]] = {}  # delegator => delegation_ids

    def create_delegation(
        self,
        delegator: str,
        agent: str,
        credential_id_hash: bytes,
        allowed_actions: List[ActionType],
        token_limits: Dict[str, int],  # token_address => max_amount
        eth_limit: int,
        duration_seconds: int,
        requires_fresh_signature: bool = False,
        description: str = "",
    ) -> DelegationScope:
        """
        Create a new scoped delegation.

        Args:
            delegator: User's address creating the delegation
            agent: Agent's address receiving the delegation
            credential_id_hash: Hash of FIDO2 credential used
            allowed_actions: List of permitted action types
            token_limits: Token address to max amount mapping
            eth_limit: Maximum ETH spending in wei
            duration_seconds: Delegation validity duration
            requires_fresh_signature: Require new FIDO2 sig per action
            description: Human-readable description

        Returns:
            Created DelegationScope
        """
        delegation_id = keccak(
            delegator.encode()
            + agent.encode()
            + credential_id_hash
            + str(datetime.utcnow().timestamp()).encode()
        ).hex()[:16]

        scope = DelegationScope(
            delegation_id=delegation_id,
            delegator=delegator.lower(),
            agent=agent.lower(),
            credential_id_hash=credential_id_hash,
            allowed_actions=set(allowed_actions),
            token_limits={
                addr.lower(): TokenLimit(addr.lower(), limit)
                for addr, limit in token_limits.items()
            },
            eth_limit=eth_limit,
            expires_at=datetime.utcnow() + timedelta(seconds=duration_seconds),
            requires_fresh_signature=requires_fresh_signature,
            description=description,
        )

        self.delegations[delegation_id] = scope

        # Update index mappings
        if agent.lower() not in self.agent_delegations:
            self.agent_delegations[agent.lower()] = []
        self.agent_delegations[agent.lower()].append(delegation_id)

        if delegator.lower() not in self.delegator_delegations:
            self.delegator_delegations[delegator.lower()] = []
        self.delegator_delegations[delegator.lower()].append(delegation_id)

        return scope

    def get_delegation(self, delegation_id: str) -> Optional[DelegationScope]:
        """Get delegation by ID."""
        return self.delegations.get(delegation_id)

    def get_agent_delegations(self, agent: str, active_only: bool = True) -> List[DelegationScope]:
        """Get all delegations for an agent."""
        delegation_ids = self.agent_delegations.get(agent.lower(), [])
        delegations = [self.delegations[did] for did in delegation_ids if did in self.delegations]

        if active_only:
            delegations = [d for d in delegations if d.is_valid]

        return delegations

    def get_delegator_delegations(
        self, delegator: str, active_only: bool = True
    ) -> List[DelegationScope]:
        """Get all delegations created by a delegator."""
        delegation_ids = self.delegator_delegations.get(delegator.lower(), [])
        delegations = [self.delegations[did] for did in delegation_ids if did in self.delegations]

        if active_only:
            delegations = [d for d in delegations if d.is_valid]

        return delegations

    def use_delegation(
        self,
        delegation_id: str,
        action: ActionType,
        token_address: Optional[str] = None,
        amount: int = 0,
    ) -> bool:
        """
        Use a delegation for an action.

        Args:
            delegation_id: Delegation to use
            action: Action type being performed
            token_address: Token address (None for ETH)
            amount: Amount to spend

        Returns:
            True if successful
        """
        delegation = self.get_delegation(delegation_id)
        if not delegation:
            return False

        return delegation.use(action, token_address, amount)

    def check_delegation(
        self,
        delegation_id: str,
        action: ActionType,
        token_address: Optional[str] = None,
        amount: int = 0,
    ) -> Dict[str, Any]:
        """
        Check if a delegation allows an action (without consuming).

        Returns detailed status information.
        """
        delegation = self.get_delegation(delegation_id)

        if not delegation:
            return {"allowed": False, "reason": "Delegation not found"}

        if not delegation.is_valid:
            return {
                "allowed": False,
                "reason": "Delegation expired" if delegation.is_expired else "Delegation revoked",
            }

        if not delegation.can_perform_action(action):
            return {"allowed": False, "reason": f"Action {action.name} not allowed"}

        if amount > 0:
            if token_address is None:
                remaining = delegation.eth_remaining
                if amount > remaining:
                    return {
                        "allowed": False,
                        "reason": "ETH limit exceeded",
                        "requested": amount,
                        "remaining": remaining,
                    }
            else:
                limit = delegation.token_limits.get(token_address.lower())
                if not limit:
                    return {"allowed": False, "reason": "Token not authorized"}
                if amount > limit.remaining:
                    return {
                        "allowed": False,
                        "reason": "Token limit exceeded",
                        "requested": amount,
                        "remaining": limit.remaining,
                    }

        return {
            "allowed": True,
            "delegation_id": delegation_id,
            "requires_fresh_signature": delegation.requires_fresh_signature,
        }

    def revoke_delegation(self, delegation_id: str, delegator: str, reason: str = "") -> bool:
        """
        Revoke a delegation.

        Only the delegator can revoke their delegations.
        """
        delegation = self.get_delegation(delegation_id)
        if not delegation:
            return False

        if delegation.delegator != delegator.lower():
            return False

        delegation.revoke(reason)
        return True

    def revoke_all_for_agent(self, delegator: str, agent: str, reason: str = "") -> int:
        """
        Revoke all delegations from a delegator to an agent.

        Returns count of revoked delegations.
        """
        count = 0
        for delegation in self.get_delegator_delegations(delegator, active_only=True):
            if delegation.agent == agent.lower():
                delegation.revoke(reason)
                count += 1
        return count

    def prepare_for_contract(
        self, delegation: DelegationScope, tokens: List[str]
    ) -> Dict[str, Any]:
        """
        Prepare delegation data for smart contract creation.

        Args:
            delegation: The delegation scope
            tokens: List of token addresses to include

        Returns:
            Data formatted for ScopedDelegation.sol
        """
        return {
            "agent": delegation.agent,
            "credentialIdHash": "0x" + delegation.credential_id_hash.hex(),
            "allowedActions": [a.value - 1 for a in delegation.allowed_actions],  # 0-indexed
            "tokens": tokens,
            "tokenLimits": [
                delegation.token_limits.get(t.lower(), TokenLimit(t, 0)).max_amount for t in tokens
            ],
            "ethLimit": delegation.eth_limit,
            "duration": (
                int((delegation.expires_at - delegation.created_at).total_seconds())
                if delegation.expires_at
                else 0
            ),
            "requiresFreshSignature": delegation.requires_fresh_signature,
            "scopeDescription": delegation.description,
        }
