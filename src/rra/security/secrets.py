# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Secrets Management for RRA Module.

Provides a unified interface for retrieving secrets from multiple backends:
- Environment variables (default, for development/simple deployments)
- File-based secrets (Docker/Kubernetes secrets mounted as files)
- HashiCorp Vault (enterprise deployments)
- AWS Secrets Manager (AWS deployments)

Usage:
    from rra.security.secrets import secrets

    # Get a secret (checks all configured backends)
    api_key = secrets.get("WORLDCOIN_APP_ID")

    # Get with a default value
    rpc_url = secrets.get("ETH_RPC_URL", default="https://eth.llamarpc.com")

    # Check if a secret exists
    if secrets.has("GITHUB_WEBHOOK_SECRET"):
        ...

Configuration:
    Set RRA_SECRETS_BACKEND to configure the primary backend:
    - "env" (default): Environment variables only
    - "file": File-based secrets (set RRA_SECRETS_PATH for directory)
    - "vault": HashiCorp Vault (set VAULT_ADDR, VAULT_TOKEN)
    - "aws": AWS Secrets Manager (uses boto3 credentials)
    - "multi": Try multiple backends in order (env -> file -> vault)
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import lru_cache
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a secret value by key."""
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a secret exists."""
        pass

    def get_all(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with an optional prefix filter."""
        return {}


class EnvironmentSecretsBackend(SecretsBackend):
    """
    Secrets backend using environment variables.

    This is the simplest backend, suitable for development and
    simple deployments. Secrets are read directly from os.environ.
    """

    def __init__(self, prefix: str = ""):
        """
        Initialize the environment backend.

        Args:
            prefix: Optional prefix for all keys (e.g., "RRA_")
        """
        self.prefix = prefix

    def get(self, key: str) -> Optional[str]:
        """Get a secret from environment variables."""
        full_key = f"{self.prefix}{key}" if self.prefix else key
        return os.environ.get(full_key)

    def has(self, key: str) -> bool:
        """Check if an environment variable exists."""
        full_key = f"{self.prefix}{key}" if self.prefix else key
        return full_key in os.environ

    def get_all(self, prefix: str = "") -> Dict[str, str]:
        """Get all environment variables with prefix."""
        full_prefix = f"{self.prefix}{prefix}"
        return {
            k[len(self.prefix):] if self.prefix else k: v
            for k, v in os.environ.items()
            if k.startswith(full_prefix)
        }


class FileSecretsBackend(SecretsBackend):
    """
    Secrets backend using files.

    Designed for Docker/Kubernetes secrets mounted as files.
    Each secret is a separate file in the secrets directory.

    Structure:
        /run/secrets/
            GITHUB_WEBHOOK_SECRET
            WORLDCOIN_APP_ID
            ETH_RPC_URL
    """

    def __init__(self, secrets_path: Optional[str] = None):
        """
        Initialize the file backend.

        Args:
            secrets_path: Path to secrets directory. Defaults to
                         RRA_SECRETS_PATH env var or /run/secrets/
        """
        default_path = os.environ.get("RRA_SECRETS_PATH", "/run/secrets")
        self.secrets_path = Path(secrets_path or default_path)
        self._cache: Dict[str, str] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)

    def _refresh_cache(self) -> None:
        """Refresh the secrets cache if needed."""
        now = datetime.utcnow()
        if self._cache_time and now - self._cache_time < self._cache_ttl:
            return

        self._cache.clear()
        if self.secrets_path.exists() and self.secrets_path.is_dir():
            for secret_file in self.secrets_path.iterdir():
                if secret_file.is_file():
                    try:
                        self._cache[secret_file.name] = secret_file.read_text().strip()
                    except Exception as e:
                        logger.warning(f"Failed to read secret file {secret_file}: {e}")

        self._cache_time = now

    def get(self, key: str) -> Optional[str]:
        """Get a secret from a file."""
        self._refresh_cache()
        return self._cache.get(key)

    def has(self, key: str) -> bool:
        """Check if a secret file exists."""
        self._refresh_cache()
        return key in self._cache

    def get_all(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with prefix."""
        self._refresh_cache()
        return {k: v for k, v in self._cache.items() if k.startswith(prefix)}


class VaultSecretsBackend(SecretsBackend):
    """
    Secrets backend using HashiCorp Vault.

    Requires:
        - VAULT_ADDR: Vault server address
        - VAULT_TOKEN or VAULT_ROLE_ID + VAULT_SECRET_ID for auth
        - Optional: VAULT_SECRETS_PATH for the secrets mount path

    Supports:
        - KV v2 secrets engine
        - Token and AppRole authentication
        - Automatic token renewal
    """

    def __init__(
        self,
        vault_addr: Optional[str] = None,
        vault_token: Optional[str] = None,
        secrets_path: str = "secret/data/rra"
    ):
        """
        Initialize the Vault backend.

        Args:
            vault_addr: Vault server address
            vault_token: Vault authentication token
            secrets_path: Path to secrets in Vault
        """
        self.vault_addr = vault_addr or os.environ.get("VAULT_ADDR", "")
        self.vault_token = vault_token or os.environ.get("VAULT_TOKEN", "")
        self.secrets_path = os.environ.get("VAULT_SECRETS_PATH", secrets_path)

        self._cache: Dict[str, str] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        self._client = None

    def _get_client(self):
        """Get or create Vault client."""
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(
                    url=self.vault_addr,
                    token=self.vault_token
                )

                # Try AppRole auth if token not provided
                if not self.vault_token:
                    role_id = os.environ.get("VAULT_ROLE_ID")
                    secret_id = os.environ.get("VAULT_SECRET_ID")
                    if role_id and secret_id:
                        self._client.auth.approle.login(
                            role_id=role_id,
                            secret_id=secret_id
                        )

                if not self._client.is_authenticated():
                    logger.error("Vault authentication failed")
                    self._client = None

            except ImportError:
                logger.error("hvac package not installed. Install with: pip install hvac")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize Vault client: {e}")
                return None

        return self._client

    def _refresh_cache(self) -> None:
        """Refresh secrets from Vault."""
        now = datetime.utcnow()
        if self._cache_time and now - self._cache_time < self._cache_ttl:
            return

        client = self._get_client()
        if not client:
            return

        try:
            # Read from KV v2 secrets engine
            response = client.secrets.kv.v2.read_secret_version(
                path=self.secrets_path.replace("secret/data/", ""),
                mount_point="secret"
            )

            if response and response.get("data", {}).get("data"):
                self._cache = response["data"]["data"]
                self._cache_time = now

        except Exception as e:
            logger.error(f"Failed to read secrets from Vault: {e}")

    def get(self, key: str) -> Optional[str]:
        """Get a secret from Vault."""
        if not self.vault_addr:
            return None

        self._refresh_cache()
        return self._cache.get(key)

    def has(self, key: str) -> bool:
        """Check if a secret exists in Vault."""
        if not self.vault_addr:
            return False

        self._refresh_cache()
        return key in self._cache

    def get_all(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with prefix from Vault."""
        if not self.vault_addr:
            return {}

        self._refresh_cache()
        return {k: v for k, v in self._cache.items() if k.startswith(prefix)}


class AWSSecretsBackend(SecretsBackend):
    """
    Secrets backend using AWS Secrets Manager.

    Requires:
        - AWS credentials configured (env vars, ~/.aws/credentials, or IAM role)
        - Optional: AWS_REGION or AWS_DEFAULT_REGION
        - Optional: RRA_AWS_SECRET_NAME for the secret name

    Stores all secrets as a single JSON document in AWS Secrets Manager.
    """

    def __init__(
        self,
        secret_name: Optional[str] = None,
        region_name: Optional[str] = None
    ):
        """
        Initialize the AWS Secrets Manager backend.

        Args:
            secret_name: Name of the secret in AWS
            region_name: AWS region
        """
        self.secret_name = secret_name or os.environ.get(
            "RRA_AWS_SECRET_NAME", "rra-module/secrets"
        )
        self.region_name = region_name or os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )

        self._cache: Dict[str, str] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        self._client = None

    def _get_client(self):
        """Get or create AWS Secrets Manager client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "secretsmanager",
                    region_name=self.region_name
                )
            except ImportError:
                logger.error("boto3 package not installed. Install with: pip install boto3")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize AWS Secrets Manager client: {e}")
                return None

        return self._client

    def _refresh_cache(self) -> None:
        """Refresh secrets from AWS Secrets Manager."""
        now = datetime.utcnow()
        if self._cache_time and now - self._cache_time < self._cache_ttl:
            return

        client = self._get_client()
        if not client:
            return

        try:
            response = client.get_secret_value(SecretId=self.secret_name)
            secret_string = response.get("SecretString", "{}")
            self._cache = json.loads(secret_string)
            self._cache_time = now

        except client.exceptions.ResourceNotFoundException:
            logger.warning(f"AWS secret '{self.secret_name}' not found")
        except Exception as e:
            logger.error(f"Failed to read secrets from AWS: {e}")

    def get(self, key: str) -> Optional[str]:
        """Get a secret from AWS Secrets Manager."""
        self._refresh_cache()
        return self._cache.get(key)

    def has(self, key: str) -> bool:
        """Check if a secret exists in AWS."""
        self._refresh_cache()
        return key in self._cache

    def get_all(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with prefix from AWS."""
        self._refresh_cache()
        return {k: v for k, v in self._cache.items() if k.startswith(prefix)}


class MultiBackendSecrets(SecretsBackend):
    """
    Secrets backend that tries multiple backends in order.

    Useful for fallback scenarios where you want to check
    environment variables first, then file secrets, then Vault.
    """

    def __init__(self, backends: List[SecretsBackend]):
        """
        Initialize with a list of backends.

        Args:
            backends: List of backends to try in order
        """
        self.backends = backends

    def get(self, key: str) -> Optional[str]:
        """Get a secret from the first backend that has it."""
        for backend in self.backends:
            value = backend.get(key)
            if value is not None:
                return value
        return None

    def has(self, key: str) -> bool:
        """Check if any backend has the secret."""
        return any(backend.has(key) for backend in self.backends)

    def get_all(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with prefix, merging from all backends."""
        result = {}
        # Later backends override earlier ones
        for backend in self.backends:
            result.update(backend.get_all(prefix))
        return result


@dataclass
class SecretValue:
    """Wrapper for secret values with metadata."""
    value: str
    source: str  # Which backend provided this secret
    cached_at: datetime

    def __str__(self) -> str:
        """Don't accidentally log secret values."""
        return f"SecretValue(source={self.source}, cached_at={self.cached_at})"

    def __repr__(self) -> str:
        return self.__str__()


class SecretsManager:
    """
    Main secrets manager with caching and audit logging.

    Provides a high-level interface for secrets management with:
    - Automatic backend selection based on configuration
    - Caching with configurable TTL
    - Audit logging for secret access
    - Default values support
    """

    # Known secrets with descriptions (for documentation/validation)
    KNOWN_SECRETS = {
        # API Keys
        "WORLDCOIN_APP_ID": "Worldcoin World ID application ID",
        "GITHUB_WEBHOOK_SECRET": "GitHub webhook signing secret",
        "GITHUB_API_TOKEN": "GitHub API token for repository access",

        # RPC URLs
        "ETH_RPC_URL": "Ethereum mainnet RPC endpoint",
        "SEPOLIA_RPC_URL": "Sepolia testnet RPC endpoint",
        "ARBITRUM_RPC_URL": "Arbitrum One RPC endpoint",
        "OPTIMISM_RPC_URL": "Optimism mainnet RPC endpoint",
        "BASE_RPC_URL": "Base mainnet RPC endpoint",
        "POLYGON_RPC_URL": "Polygon mainnet RPC endpoint",

        # Story Protocol
        "STORY_PRIVATE_KEY": "Private key for Story Protocol transactions",
        "STORY_RPC_URL": "Story Protocol RPC endpoint",

        # DID Registry
        "NLC_DID_REGISTRY_ADDRESS": "NatLangChain DID Registry contract address",

        # Security
        "RRA_ENCRYPTION_KEY": "Encryption key for webhook secrets",
        "RRA_ADMIN_API_KEY": "Admin API key for management endpoints",
        "RRA_API_KEYS": "Comma-separated list of valid API keys",

        # Vault (when using Vault backend)
        "VAULT_ADDR": "HashiCorp Vault server address",
        "VAULT_TOKEN": "Vault authentication token",
        "VAULT_ROLE_ID": "Vault AppRole role ID",
        "VAULT_SECRET_ID": "Vault AppRole secret ID",
    }

    def __init__(self, backend: Optional[SecretsBackend] = None):
        """
        Initialize the secrets manager.

        Args:
            backend: Secrets backend to use. If None, auto-configured
                    based on RRA_SECRETS_BACKEND environment variable.
        """
        self._backend = backend or self._create_default_backend()
        self._access_log: List[Dict[str, Any]] = []
        self._audit_enabled = os.environ.get("RRA_SECRETS_AUDIT", "false").lower() == "true"

    def _create_default_backend(self) -> SecretsBackend:
        """Create the default backend based on configuration."""
        backend_type = os.environ.get("RRA_SECRETS_BACKEND", "env").lower()

        if backend_type == "file":
            return FileSecretsBackend()

        elif backend_type == "vault":
            return VaultSecretsBackend()

        elif backend_type == "aws":
            return AWSSecretsBackend()

        elif backend_type == "multi":
            # Try env -> file -> vault in order
            backends = [EnvironmentSecretsBackend()]

            # Add file backend if secrets path exists
            secrets_path = Path(os.environ.get("RRA_SECRETS_PATH", "/run/secrets"))
            if secrets_path.exists():
                backends.append(FileSecretsBackend())

            # Add Vault if configured
            if os.environ.get("VAULT_ADDR"):
                backends.append(VaultSecretsBackend())

            return MultiBackendSecrets(backends)

        else:  # Default to environment variables
            return EnvironmentSecretsBackend()

    def _log_access(self, key: str, found: bool) -> None:
        """Log secret access for auditing."""
        if not self._audit_enabled:
            return

        self._access_log.append({
            "key": key,
            "found": found,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Keep only last 1000 entries
        if len(self._access_log) > 1000:
            self._access_log = self._access_log[-1000:]

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value.

        Args:
            key: The secret key
            default: Default value if secret not found

        Returns:
            The secret value, or default if not found
        """
        value = self._backend.get(key)
        self._log_access(key, value is not None)

        if value is None:
            return default
        return value

    def get_required(self, key: str) -> str:
        """
        Get a required secret value.

        Args:
            key: The secret key

        Returns:
            The secret value

        Raises:
            ValueError: If the secret is not found
        """
        value = self.get(key)
        if value is None:
            description = self.KNOWN_SECRETS.get(key, "Unknown secret")
            raise ValueError(
                f"Required secret '{key}' not found. "
                f"Description: {description}"
            )
        return value

    def has(self, key: str) -> bool:
        """Check if a secret exists."""
        return self._backend.has(key)

    def get_all(self, prefix: str = "") -> Dict[str, str]:
        """Get all secrets with optional prefix filter."""
        return self._backend.get_all(prefix)

    def get_access_log(self) -> List[Dict[str, Any]]:
        """Get the audit log of secret accesses."""
        return self._access_log.copy()

    def validate_required_secrets(self, keys: List[str]) -> Dict[str, bool]:
        """
        Validate that all required secrets are present.

        Args:
            keys: List of secret keys to check

        Returns:
            Dict mapping key to whether it's present
        """
        return {key: self.has(key) for key in keys}

    def list_known_secrets(self) -> Dict[str, str]:
        """Get list of known secrets with descriptions."""
        return self.KNOWN_SECRETS.copy()


# Global singleton instance
_secrets_instance: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    global _secrets_instance
    if _secrets_instance is None:
        _secrets_instance = SecretsManager()
    return _secrets_instance


# Convenience alias for the global instance
secrets = get_secrets_manager()


# Utility function for backward compatibility with direct os.environ.get calls
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a secret value using the configured backend.

    This is a convenience function that uses the global secrets manager.

    Args:
        key: The secret key
        default: Default value if not found

    Returns:
        The secret value or default
    """
    return get_secrets_manager().get(key, default)
