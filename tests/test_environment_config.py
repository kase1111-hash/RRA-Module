# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for Environment Configuration.

Tests cover:
- Environment detection and parsing
- Configuration loading for each environment
- Environment variable overrides
- Configuration validation
- Feature flags
"""

import os
from unittest.mock import patch

from src.rra.config.environment import (
    Environment,
    LogLevel,
    EnvironmentConfig,
    DatabaseConfig,
    CacheConfig,
    FeatureFlags,
    get_config,
    reload_config,
    validate_config,
    is_development,
    is_staging,
    is_production,
    is_feature_enabled,
    _get_development_config,
    _get_staging_config,
    _get_production_config,
    _apply_env_overrides,
)


# =============================================================================
# Environment Enum Tests
# =============================================================================


class TestEnvironment:
    """Tests for Environment enum."""

    def test_from_string_development(self):
        """Test parsing development environment."""
        assert Environment.from_string("development") == Environment.DEVELOPMENT
        assert Environment.from_string("dev") == Environment.DEVELOPMENT
        assert Environment.from_string("local") == Environment.DEVELOPMENT
        assert Environment.from_string("DEV") == Environment.DEVELOPMENT

    def test_from_string_staging(self):
        """Test parsing staging environment."""
        assert Environment.from_string("staging") == Environment.STAGING
        assert Environment.from_string("stage") == Environment.STAGING
        assert Environment.from_string("test") == Environment.STAGING

    def test_from_string_production(self):
        """Test parsing production environment."""
        assert Environment.from_string("production") == Environment.PRODUCTION
        assert Environment.from_string("prod") == Environment.PRODUCTION
        assert Environment.from_string("live") == Environment.PRODUCTION

    def test_from_string_default(self):
        """Test default to development for unknown values."""
        assert Environment.from_string("unknown") == Environment.DEVELOPMENT
        assert Environment.from_string("") == Environment.DEVELOPMENT


# =============================================================================
# Database Config Tests
# =============================================================================


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_sqlite_connection_string(self):
        """Test SQLite connection string."""
        config = DatabaseConfig(driver="sqlite", name="test_db")
        assert config.connection_string == "sqlite:///test_db.db"

    def test_postgresql_connection_string(self):
        """Test PostgreSQL connection string."""
        config = DatabaseConfig(
            driver="postgresql",
            host="localhost",
            port=5432,
            name="mydb",
            user="user",
            password="pass",
            ssl_mode="require",
        )
        assert "postgresql://user:pass@localhost:5432/mydb" in config.connection_string
        assert "sslmode=require" in config.connection_string

    def test_postgresql_without_password(self):
        """Test PostgreSQL connection string without password."""
        config = DatabaseConfig(
            driver="postgresql", host="localhost", port=5432, name="mydb", user="user"
        )
        assert "user@localhost:5432/mydb" in config.connection_string


# =============================================================================
# Cache Config Tests
# =============================================================================


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_redis_url(self):
        """Test Redis URL generation."""
        config = CacheConfig(host="redis.example.com", port=6380, password="secret", db=2)
        assert config.redis_url == "redis://:secret@redis.example.com:6380/2"

    def test_redis_url_without_password(self):
        """Test Redis URL without password."""
        config = CacheConfig(host="localhost", port=6379, db=0)
        assert config.redis_url == "redis://localhost:6379/0"


# =============================================================================
# Feature Flags Tests
# =============================================================================


class TestFeatureFlags:
    """Tests for FeatureFlags."""

    def test_default_flags(self):
        """Test default feature flag values."""
        flags = FeatureFlags()
        assert flags.enable_story_protocol is True
        assert flags.enable_superfluid_streaming is False
        assert flags.enable_l3_rollups is False

    def test_is_enabled(self):
        """Test is_enabled helper method."""
        flags = FeatureFlags(enable_story_protocol=True, enable_zk_proofs=False)
        assert flags.is_enabled("enable_story_protocol") is True
        assert flags.is_enabled("enable_zk_proofs") is False
        assert flags.is_enabled("nonexistent_flag") is False


# =============================================================================
# Environment Config Tests
# =============================================================================


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig."""

    def test_is_environment_helpers(self):
        """Test environment helper properties."""
        dev_config = EnvironmentConfig(environment=Environment.DEVELOPMENT)
        assert dev_config.is_development is True
        assert dev_config.is_staging is False
        assert dev_config.is_production is False

        prod_config = EnvironmentConfig(environment=Environment.PRODUCTION)
        assert prod_config.is_development is False
        assert prod_config.is_production is True


# =============================================================================
# Environment-Specific Config Tests
# =============================================================================


class TestDevelopmentConfig:
    """Tests for development configuration."""

    def test_development_defaults(self):
        """Test development environment defaults."""
        config = _get_development_config()

        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is True
        assert config.api_docs_enabled is True
        assert config.security.auth_enabled is False
        assert config.security.rate_limit_enabled is False
        assert config.database.driver == "sqlite"
        assert config.cache.backend == "memory"
        assert config.blockchain.story_network == "testnet"


class TestStagingConfig:
    """Tests for staging configuration."""

    def test_staging_defaults(self):
        """Test staging environment defaults."""
        config = _get_staging_config()

        assert config.environment == Environment.STAGING
        assert config.debug is True
        assert config.api_docs_enabled is True
        assert config.security.auth_enabled is True
        assert config.security.rate_limit_enabled is True
        assert config.database.driver == "postgresql"
        assert config.cache.backend == "redis"
        assert config.blockchain.story_network == "testnet"


class TestProductionConfig:
    """Tests for production configuration."""

    def test_production_defaults(self):
        """Test production environment defaults."""
        config = _get_production_config()

        assert config.environment == Environment.PRODUCTION
        assert config.debug is False
        assert config.api_docs_enabled is False
        assert config.security.auth_enabled is True
        assert config.security.rate_limit_enabled is True
        assert config.database.driver == "postgresql"
        assert config.cache.backend == "redis"
        assert config.blockchain.story_network == "mainnet"


# =============================================================================
# Environment Override Tests
# =============================================================================


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_debug_override(self):
        """Test debug mode override."""
        config = _get_development_config()
        config.debug = True

        with patch.dict(os.environ, {"RRA_DEBUG": "false"}):
            config = _apply_env_overrides(config)

        assert config.debug is False

    def test_api_settings_override(self):
        """Test API settings override."""
        config = _get_development_config()

        with patch.dict(
            os.environ,
            {
                "RRA_API_HOST": "0.0.0.0",
                "RRA_API_PORT": "9000",
                "RRA_API_URL": "https://custom.api.com",
            },
        ):
            config = _apply_env_overrides(config)

        assert config.api_host == "0.0.0.0"
        assert config.api_port == 9000
        assert config.api_base_url == "https://custom.api.com"

    def test_log_level_override(self):
        """Test log level override."""
        config = _get_development_config()

        with patch.dict(os.environ, {"RRA_LOG_LEVEL": "WARNING"}):
            config = _apply_env_overrides(config)

        assert config.log_level == LogLevel.WARNING

    def test_security_overrides(self):
        """Test security settings override."""
        config = _get_development_config()

        with patch.dict(
            os.environ,
            {
                "RRA_AUTH_ENABLED": "true",
                "RRA_JWT_SECRET": "my-secret",
                "RRA_CORS_ORIGINS": "https://a.com,https://b.com",
            },
        ):
            config = _apply_env_overrides(config)

        assert config.security.auth_enabled is True
        assert config.security.jwt_secret_key == "my-secret"
        assert config.security.cors_origins == ["https://a.com", "https://b.com"]

    def test_feature_flag_override(self):
        """Test feature flag override via environment."""
        config = _get_development_config()

        with patch.dict(
            os.environ,
            {"RRA_FEATURE_enable_zk_proofs": "true", "RRA_FEATURE_enable_story_protocol": "false"},
        ):
            config = _apply_env_overrides(config)

        assert config.features.enable_zk_proofs is True
        assert config.features.enable_story_protocol is False


# =============================================================================
# Config Validation Tests
# =============================================================================


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_valid_development_config(self):
        """Test that development config is valid."""
        config = _get_development_config()
        issues = validate_config(config)
        assert len(issues) == 0

    def test_production_with_debug(self):
        """Test production validation catches debug mode."""
        config = _get_production_config()
        config.debug = True

        issues = validate_config(config)
        assert any("Debug mode" in issue for issue in issues)

    def test_production_with_wildcard_cors(self):
        """Test production validation catches wildcard CORS."""
        config = _get_production_config()
        config.security.cors_origins = ["*"]

        issues = validate_config(config)
        assert any("CORS" in issue for issue in issues)

    def test_production_with_sqlite(self):
        """Test production validation catches SQLite."""
        config = _get_production_config()
        config.database.driver = "sqlite"

        issues = validate_config(config)
        assert any("SQLite" in issue for issue in issues)

    def test_production_without_jwt_secret(self):
        """Test production validation catches missing JWT secret."""
        config = _get_production_config()
        config.security.jwt_secret_key = ""

        issues = validate_config(config)
        assert any("JWT" in issue for issue in issues)


# =============================================================================
# Config Loading Tests
# =============================================================================


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_get_config_development(self):
        """Test loading development config."""
        with patch.dict(os.environ, {"RRA_ENV": "development"}, clear=True):
            reload_config()
            config = get_config()
            assert config.environment == Environment.DEVELOPMENT

    def test_get_config_staging(self):
        """Test loading staging config."""
        with patch.dict(os.environ, {"RRA_ENV": "staging"}, clear=True):
            reload_config()
            config = get_config()
            assert config.environment == Environment.STAGING

    def test_get_config_production(self):
        """Test loading production config."""
        with patch.dict(os.environ, {"RRA_ENV": "production"}, clear=True):
            reload_config()
            config = get_config()
            assert config.environment == Environment.PRODUCTION

    def test_config_caching(self):
        """Test that config is cached."""
        with patch.dict(os.environ, {"RRA_ENV": "development"}, clear=True):
            reload_config()
            config1 = get_config()
            config2 = get_config()
            assert config1 is config2

    def test_reload_clears_cache(self):
        """Test that reload_config clears cache."""
        with patch.dict(os.environ, {"RRA_ENV": "development"}, clear=True):
            config1 = get_config()
            reload_config()
            config2 = get_config()
            # After reload, should be new object
            assert config1 is not config2


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_is_development_function(self):
        """Test is_development function."""
        with patch.dict(os.environ, {"RRA_ENV": "development"}, clear=True):
            reload_config()
            assert is_development() is True
            assert is_staging() is False
            assert is_production() is False

    def test_is_feature_enabled_function(self):
        """Test is_feature_enabled function."""
        with patch.dict(os.environ, {"RRA_ENV": "development"}, clear=True):
            reload_config()
            # Development has Story Protocol enabled by default
            assert is_feature_enabled("enable_story_protocol") is True
