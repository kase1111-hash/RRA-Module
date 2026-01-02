# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Environment Configuration for RRA Module.

Provides separation between development, staging, and production environments
with appropriate defaults and validation for each.

Usage:
    from rra.config.environment import get_config, Environment

    # Get current environment config
    config = get_config()

    # Access settings
    api_url = config.api_base_url
    is_debug = config.debug

    # Check environment
    if config.environment == Environment.PRODUCTION:
        ...

Environment Selection:
    Set RRA_ENV environment variable:
    - "development" or "dev" (default)
    - "staging" or "stage"
    - "production" or "prod"

Override Settings:
    Individual settings can be overridden via environment variables.
    See EnvironmentConfig for available settings.
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, value: str) -> "Environment":
        """Parse environment from string."""
        value = value.lower().strip()
        mapping = {
            "development": cls.DEVELOPMENT,
            "dev": cls.DEVELOPMENT,
            "local": cls.DEVELOPMENT,
            "staging": cls.STAGING,
            "stage": cls.STAGING,
            "test": cls.STAGING,
            "production": cls.PRODUCTION,
            "prod": cls.PRODUCTION,
            "live": cls.PRODUCTION,
        }
        return mapping.get(value, cls.DEVELOPMENT)


class LogLevel(Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """Database configuration."""

    driver: str = "sqlite"
    host: str = "localhost"
    port: int = 5432
    name: str = "rra"
    user: str = "rra"
    password: str = ""
    ssl_mode: str = "prefer"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    @property
    def connection_string(self) -> str:
        """Get database connection string."""
        if self.driver == "sqlite":
            return f"sqlite:///{self.name}.db"
        elif self.driver == "postgresql":
            auth = f"{self.user}:{self.password}@" if self.password else f"{self.user}@"
            return f"postgresql://{auth}{self.host}:{self.port}/{self.name}?sslmode={self.ssl_mode}"
        else:
            return f"{self.driver}://{self.user}@{self.host}:{self.port}/{self.name}"


@dataclass
class CacheConfig:
    """Cache configuration."""

    backend: str = "memory"  # memory, redis, memcached
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0
    default_ttl: int = 300  # 5 minutes
    max_entries: int = 10000

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class BlockchainConfig:
    """Blockchain configuration."""

    default_chain: str = "sepolia"  # Default chain for development
    rpc_timeout: int = 30
    max_retries: int = 3
    confirmation_blocks: int = 1
    gas_price_multiplier: float = 1.1
    max_gas_price_gwei: float = 100.0

    # Story Protocol
    story_network: str = "testnet"  # testnet or mainnet

    # DID Registry
    did_registry_address: str = ""


@dataclass
class SecurityConfig:
    """Security configuration."""

    # API Authentication
    auth_enabled: bool = True
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    api_key_header: str = "X-API-Key"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # CORS
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])

    # Secrets
    secrets_backend: str = "env"  # env, file, vault, aws

    # Encryption
    encryption_key: str = ""


@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout."""

    # Core features
    enable_story_protocol: bool = True
    enable_superfluid_streaming: bool = False
    enable_l3_rollups: bool = False
    enable_zk_proofs: bool = False

    # Identity features
    enable_worldcoin_verification: bool = True
    enable_brightid_verification: bool = True
    enable_hardware_auth: bool = True
    enable_ens_verification: bool = True

    # Experimental
    enable_ai_negotiation: bool = True
    enable_auto_pricing: bool = False
    enable_reputation_decay: bool = False

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled."""
        return getattr(self, flag_name, False)


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""

    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090
    metrics_path: str = "/metrics"

    # Tracing
    tracing_enabled: bool = False
    tracing_endpoint: str = ""
    tracing_sample_rate: float = 0.1

    # Health checks
    health_check_path: str = "/health"
    readiness_path: str = "/ready"
    liveness_path: str = "/live"


@dataclass
class EnvironmentConfig:
    """
    Complete environment configuration.

    This class aggregates all configuration for a specific environment.
    """

    # Core settings
    environment: Environment = Environment.DEVELOPMENT
    app_name: str = "rra-module"
    app_version: str = "1.0.0"
    debug: bool = True
    testing: bool = False

    # API settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    api_docs_enabled: bool = True

    # Logging
    log_level: LogLevel = LogLevel.DEBUG
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_json: bool = False
    log_file: Optional[str] = None

    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    blockchain: BlockchainConfig = field(default_factory=BlockchainConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("data"))
    logs_dir: Path = field(default_factory=lambda: Path("logs"))
    temp_dir: Path = field(default_factory=lambda: Path("/tmp/rra"))

    def __post_init__(self):
        """Initialize directories and validate config."""
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode."""
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == Environment.PRODUCTION


# =============================================================================
# Environment-Specific Defaults
# =============================================================================


def _get_development_config() -> EnvironmentConfig:
    """Get development environment configuration."""
    return EnvironmentConfig(
        environment=Environment.DEVELOPMENT,
        debug=True,
        testing=False,
        api_host="127.0.0.1",
        api_port=8000,
        api_base_url="http://localhost:8000",
        api_docs_enabled=True,
        log_level=LogLevel.DEBUG,
        log_json=False,
        database=DatabaseConfig(
            driver="sqlite",
            name="rra_dev",
        ),
        cache=CacheConfig(
            backend="memory",
            default_ttl=60,
        ),
        blockchain=BlockchainConfig(
            default_chain="sepolia",
            story_network="testnet",
            confirmation_blocks=1,
        ),
        security=SecurityConfig(
            auth_enabled=False,  # Disabled for easy development
            rate_limit_enabled=False,
            cors_origins=["*"],
            secrets_backend="env",
        ),
        features=FeatureFlags(
            enable_story_protocol=True,
            enable_ai_negotiation=True,
            enable_auto_pricing=False,
        ),
        monitoring=MonitoringConfig(
            metrics_enabled=False,
            tracing_enabled=False,
        ),
    )


def _get_staging_config() -> EnvironmentConfig:
    """Get staging environment configuration."""
    return EnvironmentConfig(
        environment=Environment.STAGING,
        debug=True,
        testing=False,
        api_host="0.0.0.0",
        api_port=8000,
        api_base_url=os.environ.get("RRA_API_URL", "https://staging-api.rra.dev"),
        api_docs_enabled=True,
        log_level=LogLevel.INFO,
        log_json=True,
        database=DatabaseConfig(
            driver="postgresql",
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "5432")),
            name=os.environ.get("DB_NAME", "rra_staging"),
            user=os.environ.get("DB_USER", "rra"),
            password=os.environ.get("DB_PASSWORD", ""),
            ssl_mode="require",
            pool_size=10,
        ),
        cache=CacheConfig(
            backend="redis",
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            default_ttl=300,
        ),
        blockchain=BlockchainConfig(
            default_chain="sepolia",
            story_network="testnet",
            confirmation_blocks=2,
            max_gas_price_gwei=50.0,
        ),
        security=SecurityConfig(
            auth_enabled=True,
            rate_limit_enabled=True,
            rate_limit_requests=200,
            cors_origins=["https://staging.rra.dev", "https://staging-app.rra.dev"],
            secrets_backend="file",
        ),
        features=FeatureFlags(
            enable_story_protocol=True,
            enable_superfluid_streaming=True,
            enable_ai_negotiation=True,
            enable_auto_pricing=True,
        ),
        monitoring=MonitoringConfig(
            metrics_enabled=True,
            tracing_enabled=True,
            tracing_sample_rate=0.5,
        ),
        data_dir=Path("/var/lib/rra/data"),
        logs_dir=Path("/var/log/rra"),
    )


def _get_production_config() -> EnvironmentConfig:
    """Get production environment configuration."""
    return EnvironmentConfig(
        environment=Environment.PRODUCTION,
        debug=False,
        testing=False,
        api_host="0.0.0.0",
        api_port=8000,
        api_base_url=os.environ.get("RRA_API_URL", "https://api.rra.io"),
        api_docs_enabled=False,  # Disabled in production
        log_level=LogLevel.WARNING,
        log_json=True,
        log_file="/var/log/rra/app.log",
        database=DatabaseConfig(
            driver="postgresql",
            host=os.environ.get("DB_HOST", ""),
            port=int(os.environ.get("DB_PORT", "5432")),
            name=os.environ.get("DB_NAME", "rra"),
            user=os.environ.get("DB_USER", "rra"),
            password=os.environ.get("DB_PASSWORD", ""),
            ssl_mode="require",
            pool_size=20,
            max_overflow=30,
        ),
        cache=CacheConfig(
            backend="redis",
            host=os.environ.get("REDIS_HOST", ""),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            password=os.environ.get("REDIS_PASSWORD", ""),
            default_ttl=600,
            max_entries=100000,
        ),
        blockchain=BlockchainConfig(
            default_chain="ethereum",
            story_network="mainnet",
            confirmation_blocks=3,
            max_gas_price_gwei=150.0,
            gas_price_multiplier=1.2,
        ),
        security=SecurityConfig(
            auth_enabled=True,
            rate_limit_enabled=True,
            rate_limit_requests=100,
            rate_limit_window=60,
            cors_origins=["https://app.rra.io", "https://www.rra.io"],
            secrets_backend="vault",
        ),
        features=FeatureFlags(
            enable_story_protocol=True,
            enable_superfluid_streaming=True,
            enable_worldcoin_verification=True,
            enable_brightid_verification=True,
            enable_ai_negotiation=True,
            # Experimental features disabled in prod
            enable_auto_pricing=False,
            enable_reputation_decay=False,
            enable_l3_rollups=False,
            enable_zk_proofs=False,
        ),
        monitoring=MonitoringConfig(
            metrics_enabled=True,
            tracing_enabled=True,
            tracing_sample_rate=0.1,
        ),
        data_dir=Path("/var/lib/rra/data"),
        logs_dir=Path("/var/log/rra"),
    )


# =============================================================================
# Configuration Loading
# =============================================================================


def _apply_env_overrides(config: EnvironmentConfig) -> EnvironmentConfig:
    """Apply environment variable overrides to configuration."""
    # Core overrides
    if os.environ.get("RRA_DEBUG"):
        config.debug = os.environ.get("RRA_DEBUG", "").lower() == "true"

    if os.environ.get("RRA_API_HOST"):
        config.api_host = os.environ["RRA_API_HOST"]

    if os.environ.get("RRA_API_PORT"):
        config.api_port = int(os.environ["RRA_API_PORT"])

    if os.environ.get("RRA_API_URL"):
        config.api_base_url = os.environ["RRA_API_URL"]

    if os.environ.get("RRA_LOG_LEVEL"):
        try:
            config.log_level = LogLevel(os.environ["RRA_LOG_LEVEL"].upper())
        except ValueError:
            pass

    # Security overrides
    if os.environ.get("RRA_AUTH_ENABLED"):
        config.security.auth_enabled = os.environ["RRA_AUTH_ENABLED"].lower() == "true"

    if os.environ.get("RRA_JWT_SECRET"):
        config.security.jwt_secret_key = os.environ["RRA_JWT_SECRET"]

    if os.environ.get("RRA_CORS_ORIGINS"):
        config.security.cors_origins = os.environ["RRA_CORS_ORIGINS"].split(",")

    if os.environ.get("RRA_SECRETS_BACKEND"):
        config.security.secrets_backend = os.environ["RRA_SECRETS_BACKEND"]

    # Blockchain overrides
    if os.environ.get("RRA_DEFAULT_CHAIN"):
        config.blockchain.default_chain = os.environ["RRA_DEFAULT_CHAIN"]

    if os.environ.get("STORY_NETWORK"):
        config.blockchain.story_network = os.environ["STORY_NETWORK"]

    if os.environ.get("NLC_DID_REGISTRY_ADDRESS"):
        config.blockchain.did_registry_address = os.environ["NLC_DID_REGISTRY_ADDRESS"]

    # Feature flag overrides (RRA_FEATURE_<FLAG_NAME>=true/false)
    for key, value in os.environ.items():
        if key.startswith("RRA_FEATURE_"):
            flag_name = key.replace("RRA_FEATURE_", "").lower()
            if hasattr(config.features, flag_name):
                setattr(config.features, flag_name, value.lower() == "true")

    return config


@lru_cache(maxsize=1)
def get_config() -> EnvironmentConfig:
    """
    Get the current environment configuration.

    The environment is determined by the RRA_ENV environment variable.
    Configuration is cached after first load.

    Returns:
        EnvironmentConfig for the current environment
    """
    env_str = os.environ.get("RRA_ENV", "development")
    environment = Environment.from_string(env_str)

    logger.info(f"Loading configuration for environment: {environment.value}")

    # Get base config for environment
    if environment == Environment.DEVELOPMENT:
        config = _get_development_config()
    elif environment == Environment.STAGING:
        config = _get_staging_config()
    else:
        config = _get_production_config()

    # Apply any environment variable overrides
    config = _apply_env_overrides(config)

    return config


def reload_config() -> EnvironmentConfig:
    """
    Force reload of configuration.

    Clears the cache and reloads configuration from environment.
    Use sparingly - configuration should be loaded once at startup.

    Returns:
        Freshly loaded EnvironmentConfig
    """
    get_config.cache_clear()
    return get_config()


def validate_config(config: EnvironmentConfig) -> List[str]:
    """
    Validate configuration and return list of issues.

    Args:
        config: Configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    issues = []

    # Production-specific validations
    if config.is_production:
        if config.debug:
            issues.append("Debug mode should not be enabled in production")

        if config.api_docs_enabled:
            issues.append("API docs should be disabled in production")

        if not config.security.auth_enabled:
            issues.append("Authentication must be enabled in production")

        if not config.security.jwt_secret_key:
            issues.append("JWT secret key must be set in production")

        if "*" in config.security.cors_origins:
            issues.append("Wildcard CORS origins not allowed in production")

        if config.database.driver == "sqlite":
            issues.append("SQLite should not be used in production")

        if config.cache.backend == "memory":
            issues.append("In-memory cache should not be used in production")

    # General validations
    if config.security.auth_enabled and not config.security.jwt_secret_key:
        if config.environment != Environment.DEVELOPMENT:
            issues.append("JWT secret key required when auth is enabled")

    return issues


# =============================================================================
# Convenience Functions
# =============================================================================


def is_development() -> bool:
    """Check if running in development environment."""
    return get_config().is_development


def is_staging() -> bool:
    """Check if running in staging environment."""
    return get_config().is_staging


def is_production() -> bool:
    """Check if running in production environment."""
    return get_config().is_production


def is_feature_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return get_config().features.is_enabled(flag_name)
