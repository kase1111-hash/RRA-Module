# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Boundary Daemon Integration for NatLangChain.

Provides permission management and access control for RRA agents,
integrating with the NatLangChain boundary-daemon system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, Flag, auto
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import json
import secrets
import hashlib


class Permission(Flag):
    """Permission flags for agent capabilities."""
    NONE = 0
    READ = auto()          # Read repository content
    NEGOTIATE = auto()     # Conduct license negotiations
    QUOTE = auto()         # Provide price quotes
    ACCEPT = auto()        # Accept license offers
    TRANSFER = auto()      # Transfer license ownership
    MINT = auto()          # Mint new license NFTs
    BURN = auto()          # Revoke/burn licenses
    ADMIN = auto()         # Administrative operations
    WEBHOOK = auto()       # Receive webhook callbacks
    STREAM = auto()        # Manage payment streams
    ANALYTICS = auto()     # Access analytics data

    # Common permission sets
    BASIC = READ | QUOTE
    STANDARD = READ | NEGOTIATE | QUOTE | ACCEPT
    FULL = READ | NEGOTIATE | QUOTE | ACCEPT | TRANSFER | MINT
    ALL = READ | NEGOTIATE | QUOTE | ACCEPT | TRANSFER | MINT | BURN | ADMIN | WEBHOOK | STREAM | ANALYTICS


class ResourceType(Enum):
    """Types of protected resources."""
    REPOSITORY = "repository"
    LICENSE = "license"
    AGENT = "agent"
    POOL = "pool"
    DAO = "dao"
    STREAM = "stream"
    WEBHOOK = "webhook"
    API = "api"


@dataclass
class AccessPolicy:
    """Defines access rules for a resource."""
    policy_id: str
    name: str
    description: str
    resource_type: ResourceType
    resource_id: str  # "*" for wildcard
    permissions: Permission
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    active: bool = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.active and not self.is_expired

    def matches_resource(self, resource_type: ResourceType, resource_id: str) -> bool:
        """Check if policy applies to a resource."""
        if self.resource_type != resource_type:
            return False
        if self.resource_id == "*":
            return True
        return self.resource_id == resource_id

    def check_conditions(self, context: Dict[str, Any]) -> bool:
        """Evaluate policy conditions against context."""
        for key, expected in self.conditions.items():
            if key not in context:
                return False

            actual = context[key]

            # Handle different condition types
            if isinstance(expected, dict):
                if "min" in expected and actual < expected["min"]:
                    return False
                if "max" in expected and actual > expected["max"]:
                    return False
                if "in" in expected and actual not in expected["in"]:
                    return False
                if "not_in" in expected and actual in expected["not_in"]:
                    return False
            elif actual != expected:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "permissions": self.permissions.value,
            "conditions": self.conditions,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessPolicy":
        return cls(
            policy_id=data["policy_id"],
            name=data["name"],
            description=data["description"],
            resource_type=ResourceType(data["resource_type"]),
            resource_id=data["resource_id"],
            permissions=Permission(data["permissions"]),
            conditions=data.get("conditions", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            active=data.get("active", True),
        )


@dataclass
class Principal:
    """An entity that can be granted permissions."""
    principal_id: str
    principal_type: str  # "user", "agent", "service", "contract"
    address: Optional[str] = None  # Ethereum address if applicable
    name: str = ""
    policies: List[str] = field(default_factory=list)  # Policy IDs
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "address": self.address,
            "name": self.name,
            "policies": self.policies,
            "created_at": self.created_at.isoformat(),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Principal":
        return cls(
            principal_id=data["principal_id"],
            principal_type=data["principal_type"],
            address=data.get("address"),
            name=data.get("name", ""),
            policies=data.get("policies", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            active=data.get("active", True),
        )


@dataclass
class AccessToken:
    """A temporary access token for authentication."""
    token_id: str
    token_hash: str  # Hashed token value
    principal_id: str
    scopes: List[str]
    issued_at: datetime
    expires_at: datetime
    revoked: bool = False

    @property
    def is_valid(self) -> bool:
        return not self.revoked and datetime.now() < self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "token_hash": self.token_hash,
            "principal_id": self.principal_id,
            "scopes": self.scopes,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "revoked": self.revoked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessToken":
        return cls(
            token_id=data["token_id"],
            token_hash=data["token_hash"],
            principal_id=data["principal_id"],
            scopes=data["scopes"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            revoked=data.get("revoked", False),
        )


@dataclass
class AccessLog:
    """Log entry for access attempts."""
    log_id: str
    timestamp: datetime
    principal_id: str
    resource_type: ResourceType
    resource_id: str
    permission: Permission
    granted: bool
    reason: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "principal_id": self.principal_id,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "permission": self.permission.value,
            "granted": self.granted,
            "reason": self.reason,
            "context": self.context,
        }


class BoundaryDaemon:
    """
    Boundary Daemon for permission management.

    Integrates with NatLangChain's access control system to manage
    permissions for RRA agents and resources.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/permissions")
        self.policies: Dict[str, AccessPolicy] = {}
        self.principals: Dict[str, Principal] = {}
        self.tokens: Dict[str, AccessToken] = {}
        self.access_logs: List[AccessLog] = []

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    # =========================================================================
    # Policy Management
    # =========================================================================

    def create_policy(
        self,
        name: str,
        description: str,
        resource_type: ResourceType,
        resource_id: str,
        permissions: Permission,
        conditions: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None
    ) -> AccessPolicy:
        """Create a new access policy."""
        policy = AccessPolicy(
            policy_id=self._generate_id("policy_"),
            name=name,
            description=description,
            resource_type=resource_type,
            resource_id=resource_id,
            permissions=permissions,
            conditions=conditions or {},
            expires_at=datetime.now() + timedelta(days=expires_in_days) if expires_in_days else None,
        )

        self.policies[policy.policy_id] = policy
        self._save_state()

        return policy

    def get_policy(self, policy_id: str) -> Optional[AccessPolicy]:
        return self.policies.get(policy_id)

    def revoke_policy(self, policy_id: str) -> AccessPolicy:
        """Revoke an access policy."""
        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")

        policy.active = False
        self._save_state()

        return policy

    def list_policies(
        self,
        resource_type: Optional[ResourceType] = None,
        active_only: bool = True
    ) -> List[AccessPolicy]:
        """List policies with optional filters."""
        policies = list(self.policies.values())

        if resource_type:
            policies = [p for p in policies if p.resource_type == resource_type]

        if active_only:
            policies = [p for p in policies if p.is_valid]

        return policies

    # =========================================================================
    # Principal Management
    # =========================================================================

    def register_principal(
        self,
        principal_type: str,
        name: str,
        address: Optional[str] = None
    ) -> Principal:
        """Register a new principal (user, agent, service)."""
        principal = Principal(
            principal_id=self._generate_id("principal_"),
            principal_type=principal_type,
            address=address,
            name=name,
        )

        self.principals[principal.principal_id] = principal
        self._save_state()

        return principal

    def get_principal(self, principal_id: str) -> Optional[Principal]:
        return self.principals.get(principal_id)

    def get_principal_by_address(self, address: str) -> Optional[Principal]:
        """Find principal by Ethereum address."""
        address = address.lower()
        for principal in self.principals.values():
            if principal.address and principal.address.lower() == address:
                return principal
        return None

    def assign_policy(self, principal_id: str, policy_id: str) -> Principal:
        """Assign a policy to a principal."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        policy = self.policies.get(policy_id)
        if not policy:
            raise ValueError(f"Policy not found: {policy_id}")

        if policy_id not in principal.policies:
            principal.policies.append(policy_id)
            self._save_state()

        return principal

    def remove_policy(self, principal_id: str, policy_id: str) -> Principal:
        """Remove a policy from a principal."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        if policy_id in principal.policies:
            principal.policies.remove(policy_id)
            self._save_state()

        return principal

    # =========================================================================
    # Token Management
    # =========================================================================

    def issue_token(
        self,
        principal_id: str,
        scopes: List[str],
        expires_in_hours: int = 24
    ) -> tuple[str, AccessToken]:
        """Issue an access token for a principal."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        if not principal.active:
            raise ValueError("Principal is not active")

        # Generate token
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)

        token = AccessToken(
            token_id=self._generate_id("token_"),
            token_hash=token_hash,
            principal_id=principal_id,
            scopes=scopes,
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=expires_in_hours),
        )

        self.tokens[token.token_id] = token
        self._save_state()

        return raw_token, token

    def validate_token(self, raw_token: str) -> Optional[AccessToken]:
        """Validate an access token."""
        token_hash = self._hash_token(raw_token)

        for token in self.tokens.values():
            if token.token_hash == token_hash:
                if token.is_valid:
                    return token
                break

        return None

    def revoke_token(self, token_id: str) -> AccessToken:
        """Revoke an access token."""
        token = self.tokens.get(token_id)
        if not token:
            raise ValueError(f"Token not found: {token_id}")

        token.revoked = True
        self._save_state()

        return token

    # =========================================================================
    # Access Control
    # =========================================================================

    def check_access(
        self,
        principal_id: str,
        resource_type: ResourceType,
        resource_id: str,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str]:
        """
        Check if a principal has access to a resource.

        Returns:
            Tuple of (granted, reason)
        """
        context = context or {}

        principal = self.principals.get(principal_id)
        if not principal:
            reason = "Principal not found"
            self._log_access(principal_id, resource_type, resource_id, permission, False, reason, context)
            return False, reason

        if not principal.active:
            reason = "Principal is not active"
            self._log_access(principal_id, resource_type, resource_id, permission, False, reason, context)
            return False, reason

        # Check each policy assigned to the principal
        for policy_id in principal.policies:
            policy = self.policies.get(policy_id)
            if not policy or not policy.is_valid:
                continue

            # Check if policy applies to this resource
            if not policy.matches_resource(resource_type, resource_id):
                continue

            # Check if policy grants the required permission
            if not (policy.permissions & permission):
                continue

            # Check conditions
            if not policy.check_conditions(context):
                continue

            # Access granted
            reason = f"Granted by policy: {policy.name}"
            self._log_access(principal_id, resource_type, resource_id, permission, True, reason, context)
            return True, reason

        reason = "No matching policy found"
        self._log_access(principal_id, resource_type, resource_id, permission, False, reason, context)
        return False, reason

    def check_token_access(
        self,
        raw_token: str,
        resource_type: ResourceType,
        resource_id: str,
        permission: Permission,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str]:
        """Check access using a token."""
        token = self.validate_token(raw_token)
        if not token:
            return False, "Invalid or expired token"

        # Check if token scope allows this resource type
        scope_name = resource_type.value
        if scope_name not in token.scopes and "*" not in token.scopes:
            return False, f"Token scope does not include: {scope_name}"

        return self.check_access(
            token.principal_id,
            resource_type,
            resource_id,
            permission,
            context
        )

    def _log_access(
        self,
        principal_id: str,
        resource_type: ResourceType,
        resource_id: str,
        permission: Permission,
        granted: bool,
        reason: str,
        context: Dict[str, Any]
    ) -> None:
        """Log an access attempt."""
        log = AccessLog(
            log_id=self._generate_id("log_"),
            timestamp=datetime.now(),
            principal_id=principal_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
            granted=granted,
            reason=reason,
            context=context,
        )
        self.access_logs.append(log)

        # Keep only last 1000 logs in memory
        if len(self.access_logs) > 1000:
            self.access_logs = self.access_logs[-1000:]

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def grant_repository_access(
        self,
        principal_id: str,
        repo_id: str,
        permissions: Permission = Permission.STANDARD
    ) -> AccessPolicy:
        """Grant access to a repository."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        policy = self.create_policy(
            name=f"Repo access: {repo_id}",
            description=f"Access policy for repository {repo_id}",
            resource_type=ResourceType.REPOSITORY,
            resource_id=repo_id,
            permissions=permissions,
        )

        self.assign_policy(principal_id, policy.policy_id)

        return policy

    def grant_agent_access(
        self,
        principal_id: str,
        agent_id: str,
        permissions: Permission = Permission.NEGOTIATE | Permission.QUOTE
    ) -> AccessPolicy:
        """Grant access to an agent."""
        principal = self.principals.get(principal_id)
        if not principal:
            raise ValueError(f"Principal not found: {principal_id}")

        policy = self.create_policy(
            name=f"Agent access: {agent_id}",
            description=f"Access policy for agent {agent_id}",
            resource_type=ResourceType.AGENT,
            resource_id=agent_id,
            permissions=permissions,
        )

        self.assign_policy(principal_id, policy.policy_id)

        return policy

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_access_stats(self) -> Dict[str, Any]:
        """Get access control statistics."""
        recent_logs = [l for l in self.access_logs if l.timestamp > datetime.now() - timedelta(hours=24)]

        return {
            "total_policies": len(self.policies),
            "active_policies": len([p for p in self.policies.values() if p.is_valid]),
            "total_principals": len(self.principals),
            "active_principals": len([p for p in self.principals.values() if p.active]),
            "total_tokens": len(self.tokens),
            "valid_tokens": len([t for t in self.tokens.values() if t.is_valid]),
            "access_logs_24h": len(recent_logs),
            "granted_24h": len([l for l in recent_logs if l.granted]),
            "denied_24h": len([l for l in recent_logs if not l.granted]),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "policies": {pid: p.to_dict() for pid, p in self.policies.items()},
            "principals": {pid: p.to_dict() for pid, p in self.principals.items()},
            "tokens": {tid: t.to_dict() for tid, t in self.tokens.items()},
        }

        with open(self.data_dir / "permissions_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        state_file = self.data_dir / "permissions_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.policies = {pid: AccessPolicy.from_dict(p) for pid, p in state.get("policies", {}).items()}
            self.principals = {pid: Principal.from_dict(p) for pid, p in state.get("principals", {}).items()}
            self.tokens = {tid: AccessToken.from_dict(t) for tid, t in state.get("tokens", {}).items()}
        except (json.JSONDecodeError, KeyError):
            pass


def create_boundary_daemon(data_dir: Optional[str] = None) -> BoundaryDaemon:
    """Factory function to create a boundary daemon."""
    path = Path(data_dir) if data_dir else None
    return BoundaryDaemon(data_dir=path)
