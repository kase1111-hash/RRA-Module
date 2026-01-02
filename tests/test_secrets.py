# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for Secrets Management.

Tests cover:
- Environment variable backend
- File-based secrets backend
- Multi-backend fallback
- Vault backend (mocked)
- AWS Secrets Manager backend (mocked)
- Secrets manager with caching and audit logging
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.rra.security.secrets import (
    EnvironmentSecretsBackend,
    FileSecretsBackend,
    VaultSecretsBackend,
    AWSSecretsBackend,
    MultiBackendSecrets,
    SecretsManager,
    get_secret,
)


# =============================================================================
# Environment Secrets Backend Tests
# =============================================================================


class TestEnvironmentSecretsBackend:
    """Tests for environment variable secrets backend."""

    def test_get_existing_secret(self):
        """Test getting an existing environment variable."""
        with patch.dict(os.environ, {"TEST_SECRET": "test_value"}):
            backend = EnvironmentSecretsBackend()
            assert backend.get("TEST_SECRET") == "test_value"

    def test_get_missing_secret(self):
        """Test getting a missing environment variable."""
        backend = EnvironmentSecretsBackend()
        # Make sure the key doesn't exist
        with patch.dict(os.environ, {}, clear=True):
            assert backend.get("NONEXISTENT_SECRET") is None

    def test_has_existing_secret(self):
        """Test checking for existing secret."""
        with patch.dict(os.environ, {"TEST_SECRET": "value"}):
            backend = EnvironmentSecretsBackend()
            assert backend.has("TEST_SECRET") is True

    def test_has_missing_secret(self):
        """Test checking for missing secret."""
        backend = EnvironmentSecretsBackend()
        with patch.dict(os.environ, {}, clear=True):
            assert backend.has("NONEXISTENT") is False

    def test_prefix_support(self):
        """Test prefix filtering."""
        with patch.dict(os.environ, {
            "RRA_API_KEY": "key1",
            "RRA_SECRET": "secret1",
            "OTHER_VAR": "other"
        }):
            backend = EnvironmentSecretsBackend(prefix="RRA_")
            assert backend.get("API_KEY") == "key1"
            assert backend.get("SECRET") == "secret1"
            assert backend.get("OTHER_VAR") is None

    def test_get_all_with_prefix(self):
        """Test getting all secrets with prefix."""
        with patch.dict(os.environ, {
            "RRA_API_KEY": "key1",
            "RRA_SECRET": "secret1",
            "OTHER_VAR": "other"
        }, clear=True):
            backend = EnvironmentSecretsBackend(prefix="RRA_")
            all_secrets = backend.get_all("")
            assert "API_KEY" in all_secrets
            assert "SECRET" in all_secrets
            assert "OTHER_VAR" not in all_secrets


# =============================================================================
# File Secrets Backend Tests
# =============================================================================


class TestFileSecretsBackend:
    """Tests for file-based secrets backend."""

    def test_get_secret_from_file(self):
        """Test reading secret from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a secret file
            secret_file = Path(tmpdir) / "MY_SECRET"
            secret_file.write_text("secret_value_123")

            backend = FileSecretsBackend(secrets_path=tmpdir)
            assert backend.get("MY_SECRET") == "secret_value_123"

    def test_strips_whitespace(self):
        """Test that secret values have whitespace stripped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_file = Path(tmpdir) / "MY_SECRET"
            secret_file.write_text("  secret_value  \n")

            backend = FileSecretsBackend(secrets_path=tmpdir)
            assert backend.get("MY_SECRET") == "secret_value"

    def test_missing_secret_file(self):
        """Test getting a non-existent secret file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileSecretsBackend(secrets_path=tmpdir)
            assert backend.get("NONEXISTENT") is None

    def test_has_secret_file(self):
        """Test checking for existing secret file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_file = Path(tmpdir) / "MY_SECRET"
            secret_file.write_text("value")

            backend = FileSecretsBackend(secrets_path=tmpdir)
            assert backend.has("MY_SECRET") is True
            assert backend.has("OTHER_SECRET") is False

    def test_get_all_files(self):
        """Test getting all secret files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "SECRET_A").write_text("a")
            (Path(tmpdir) / "SECRET_B").write_text("b")
            (Path(tmpdir) / "OTHER_C").write_text("c")

            backend = FileSecretsBackend(secrets_path=tmpdir)
            all_secrets = backend.get_all("SECRET_")
            assert len(all_secrets) == 2
            assert all_secrets.get("SECRET_A") == "a"
            assert all_secrets.get("SECRET_B") == "b"

    def test_nonexistent_directory(self):
        """Test with non-existent secrets directory."""
        backend = FileSecretsBackend(secrets_path="/nonexistent/path")
        assert backend.get("ANY_SECRET") is None

    def test_caching(self):
        """Test that secrets are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            secret_file = Path(tmpdir) / "MY_SECRET"
            secret_file.write_text("original_value")

            backend = FileSecretsBackend(secrets_path=tmpdir)

            # First read
            assert backend.get("MY_SECRET") == "original_value"

            # Modify file
            secret_file.write_text("new_value")

            # Should still return cached value
            assert backend.get("MY_SECRET") == "original_value"

            # Clear cache
            backend._cache.clear()
            backend._cache_time = None

            # Now should return new value
            assert backend.get("MY_SECRET") == "new_value"


# =============================================================================
# Multi-Backend Tests
# =============================================================================


class TestMultiBackendSecrets:
    """Tests for multi-backend fallback."""

    def test_first_backend_wins(self):
        """Test that first backend with value wins."""
        backend1 = Mock()
        backend1.get.return_value = "value_from_1"

        backend2 = Mock()
        backend2.get.return_value = "value_from_2"

        multi = MultiBackendSecrets([backend1, backend2])
        assert multi.get("KEY") == "value_from_1"

    def test_fallback_to_second(self):
        """Test fallback when first backend returns None."""
        backend1 = Mock()
        backend1.get.return_value = None

        backend2 = Mock()
        backend2.get.return_value = "value_from_2"

        multi = MultiBackendSecrets([backend1, backend2])
        assert multi.get("KEY") == "value_from_2"

    def test_has_checks_all(self):
        """Test has() checks all backends."""
        backend1 = Mock()
        backend1.has.return_value = False

        backend2 = Mock()
        backend2.has.return_value = True

        multi = MultiBackendSecrets([backend1, backend2])
        assert multi.has("KEY") is True

    def test_get_all_merges(self):
        """Test get_all merges from all backends."""
        backend1 = Mock()
        backend1.get_all.return_value = {"A": "1", "B": "2"}

        backend2 = Mock()
        backend2.get_all.return_value = {"B": "override", "C": "3"}

        multi = MultiBackendSecrets([backend1, backend2])
        all_secrets = multi.get_all("")

        # Later backends override earlier
        assert all_secrets == {"A": "1", "B": "override", "C": "3"}


# =============================================================================
# Vault Backend Tests (Mocked)
# =============================================================================


class TestVaultSecretsBackend:
    """Tests for HashiCorp Vault backend."""

    def test_disabled_without_addr(self):
        """Test that backend is disabled without VAULT_ADDR."""
        with patch.dict(os.environ, {}, clear=True):
            backend = VaultSecretsBackend()
            assert backend.get("ANY_KEY") is None
            assert backend.has("ANY_KEY") is False

    @patch("src.rra.security.secrets.VaultSecretsBackend._get_client")
    def test_get_from_vault(self, mock_get_client):
        """Test getting secret from Vault."""
        mock_client = Mock()
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "API_KEY": "vault_secret"
                }
            }
        }
        mock_get_client.return_value = mock_client

        backend = VaultSecretsBackend(vault_addr="http://vault:8200")
        backend._cache.clear()
        backend._cache_time = None

        # Force cache refresh
        backend._refresh_cache()

        assert backend.get("API_KEY") == "vault_secret"

    @patch("src.rra.security.secrets.VaultSecretsBackend._get_client")
    def test_vault_error_handling(self, mock_get_client):
        """Test error handling when Vault is unavailable."""
        mock_get_client.return_value = None

        backend = VaultSecretsBackend(vault_addr="http://vault:8200")
        assert backend.get("ANY_KEY") is None


# =============================================================================
# AWS Secrets Manager Backend Tests (Mocked)
# =============================================================================


class TestAWSSecretsBackend:
    """Tests for AWS Secrets Manager backend."""

    @patch("src.rra.security.secrets.AWSSecretsBackend._get_client")
    def test_get_from_aws(self, mock_get_client):
        """Test getting secret from AWS."""
        mock_client = Mock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps({
                "API_KEY": "aws_secret",
                "DB_PASSWORD": "db_pass"
            })
        }
        mock_get_client.return_value = mock_client

        backend = AWSSecretsBackend(secret_name="test-secrets")
        backend._cache.clear()
        backend._cache_time = None

        assert backend.get("API_KEY") == "aws_secret"
        assert backend.get("DB_PASSWORD") == "db_pass"

    @patch("src.rra.security.secrets.AWSSecretsBackend._get_client")
    def test_aws_secret_not_found(self, mock_get_client):
        """Test handling of missing AWS secret."""
        mock_client = Mock()
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = Exception
        mock_client.get_secret_value.side_effect = mock_client.exceptions.ResourceNotFoundException()
        mock_get_client.return_value = mock_client

        backend = AWSSecretsBackend()
        assert backend.get("ANY_KEY") is None


# =============================================================================
# Secrets Manager Tests
# =============================================================================


class TestSecretsManager:
    """Tests for the main SecretsManager class."""

    def test_get_with_default(self):
        """Test getting secret with default value."""
        with patch.dict(os.environ, {"REAL_SECRET": "value"}, clear=True):
            manager = SecretsManager(EnvironmentSecretsBackend())

            assert manager.get("REAL_SECRET") == "value"
            assert manager.get("MISSING", default="default") == "default"

    def test_get_required_success(self):
        """Test get_required with existing secret."""
        with patch.dict(os.environ, {"MY_SECRET": "value"}):
            manager = SecretsManager(EnvironmentSecretsBackend())
            assert manager.get_required("MY_SECRET") == "value"

    def test_get_required_raises(self):
        """Test get_required raises for missing secret."""
        with patch.dict(os.environ, {}, clear=True):
            manager = SecretsManager(EnvironmentSecretsBackend())
            with pytest.raises(ValueError, match="Required secret"):
                manager.get_required("MISSING_SECRET")

    def test_validate_required_secrets(self):
        """Test validating multiple required secrets."""
        with patch.dict(os.environ, {
            "SECRET_A": "a",
            "SECRET_B": "b"
        }, clear=True):
            manager = SecretsManager(EnvironmentSecretsBackend())
            result = manager.validate_required_secrets([
                "SECRET_A",
                "SECRET_B",
                "SECRET_C"
            ])

            assert result["SECRET_A"] is True
            assert result["SECRET_B"] is True
            assert result["SECRET_C"] is False

    def test_audit_logging(self):
        """Test audit logging of secret access."""
        with patch.dict(os.environ, {
            "RRA_SECRETS_AUDIT": "true",
            "MY_SECRET": "value"
        }):
            manager = SecretsManager(EnvironmentSecretsBackend())

            manager.get("MY_SECRET")
            manager.get("MISSING_SECRET")

            log = manager.get_access_log()
            assert len(log) == 2
            assert log[0]["key"] == "MY_SECRET"
            assert log[0]["found"] is True
            assert log[1]["key"] == "MISSING_SECRET"
            assert log[1]["found"] is False

    def test_list_known_secrets(self):
        """Test listing known secrets."""
        manager = SecretsManager()
        known = manager.list_known_secrets()

        assert "WORLDCOIN_APP_ID" in known
        assert "ETH_RPC_URL" in known
        assert isinstance(known["WORLDCOIN_APP_ID"], str)

    def test_auto_backend_selection_env(self):
        """Test auto-selecting env backend."""
        with patch.dict(os.environ, {"RRA_SECRETS_BACKEND": "env"}):
            manager = SecretsManager()
            assert isinstance(manager._backend, EnvironmentSecretsBackend)

    def test_auto_backend_selection_file(self):
        """Test auto-selecting file backend."""
        with patch.dict(os.environ, {"RRA_SECRETS_BACKEND": "file"}):
            manager = SecretsManager()
            assert isinstance(manager._backend, FileSecretsBackend)

    def test_auto_backend_selection_multi(self):
        """Test auto-selecting multi backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {
                "RRA_SECRETS_BACKEND": "multi",
                "RRA_SECRETS_PATH": tmpdir
            }):
                manager = SecretsManager()
                assert isinstance(manager._backend, MultiBackendSecrets)


# =============================================================================
# Global Function Tests
# =============================================================================


class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_secret_function(self):
        """Test get_secret convenience function."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            # Reset global instance
            import src.rra.security.secrets as secrets_module
            secrets_module._secrets_instance = None

            value = get_secret("TEST_KEY")
            assert value == "test_value"

            value = get_secret("MISSING", default="fallback")
            assert value == "fallback"


# =============================================================================
# Integration Tests
# =============================================================================


class TestSecretsIntegration:
    """Integration tests for secrets management."""

    def test_env_to_file_fallback(self):
        """Test fallback from env to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file secret
            (Path(tmpdir) / "FILE_SECRET").write_text("from_file")

            with patch.dict(os.environ, {
                "ENV_SECRET": "from_env"
            }, clear=True):
                backends = [
                    EnvironmentSecretsBackend(),
                    FileSecretsBackend(secrets_path=tmpdir)
                ]
                multi = MultiBackendSecrets(backends)
                manager = SecretsManager(backend=multi)

                # Should get from env
                assert manager.get("ENV_SECRET") == "from_env"

                # Should fallback to file
                assert manager.get("FILE_SECRET") == "from_file"

                # Missing in both
                assert manager.get("MISSING") is None

    def test_complete_workflow(self):
        """Test complete secrets workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up file secrets
            (Path(tmpdir) / "API_KEY").write_text("secret_api_key")
            (Path(tmpdir) / "DB_PASSWORD").write_text("db_secret")

            with patch.dict(os.environ, {
                "RRA_SECRETS_BACKEND": "file",
                "RRA_SECRETS_PATH": tmpdir,
                "RRA_SECRETS_AUDIT": "true"
            }):
                # Reset global
                import src.rra.security.secrets as secrets_module
                secrets_module._secrets_instance = None

                from src.rra.security.secrets import get_secrets_manager
                manager = get_secrets_manager()

                # Validate secrets
                validation = manager.validate_required_secrets([
                    "API_KEY",
                    "DB_PASSWORD",
                    "MISSING_SECRET"
                ])
                assert validation["API_KEY"] is True
                assert validation["DB_PASSWORD"] is True
                assert validation["MISSING_SECRET"] is False

                # Get required secrets
                api_key = manager.get_required("API_KEY")
                assert api_key == "secret_api_key"

                # Check audit log
                log = manager.get_access_log()
                assert len(log) > 0
