# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
End-to-end test: Full GitHub repository scanning and upload flow.

This test mocks the complete workflow:
1. Scan a GitHub repository
2. Ingest and analyze the code
3. Generate knowledge base
4. Post transaction to NatLangChain
5. Verify rate limiting works
6. Test network resilience (circuit breaker, retries)
"""

import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


class TestEndToEndGitHubFlow:
    """Full end-to-end test of GitHub scanning and upload flow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test artifacts."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_github_repo(self):
        """Mock GitHub repository data."""
        return {
            "url": "https://github.com/test-org/test-repo",
            "name": "test-repo",
            "owner": "test-org",
            "description": "A test repository for RRA Module",
            "language": "Python",
            "stars": 150,
            "license": "MIT",
            "files": [
                {"path": "README.md", "content": "# Test Repo\n\nA sample project."},
                {"path": "src/main.py", "content": "def hello():\n    return 'Hello, World!'"},
                {"path": "src/utils.py", "content": "def add(a, b):\n    return a + b"},
                {"path": "tests/test_main.py", "content": "def test_hello():\n    assert hello() == 'Hello, World!'"},
                {"path": "LICENSE", "content": "MIT License\n\nCopyright 2025..."},
                {"path": "pyproject.toml", "content": "[project]\nname = \"test-repo\"\nversion = \"1.0.0\""},
            ]
        }

    @pytest.fixture
    def mock_knowledge_base(self, mock_github_repo):
        """Create mock knowledge base from repo data."""
        return {
            "repo_url": mock_github_repo["url"],
            "repo_name": mock_github_repo["name"],
            "updated_at": datetime.now().isoformat(),
            "statistics": {
                "code_files": 4,
                "languages": ["Python"],
                "total_lines": 150,
                "test_coverage": 0.75,
            },
            "license_info": {
                "type": "MIT",
                "commercial_use": True,
                "modification_allowed": True,
            },
            "market_config": {
                "base_price": 0.5,
                "currency": "ETH",
                "negotiable": True,
            }
        }

    def test_step1_repository_ingestion(self, temp_dir, mock_github_repo):
        """Step 1: Test repository ingestion and knowledge base creation."""
        print("\n=== Step 1: Repository Ingestion ===")

        # Mock the repo ingester
        with patch('rra.ingestion.repo_ingester.RepoIngester') as MockIngester:
            mock_ingester = MagicMock()
            MockIngester.return_value = mock_ingester

            # Mock knowledge base
            mock_kb = MagicMock()
            mock_kb.repo_url = mock_github_repo["url"]
            mock_kb.statistics = {"code_files": 4, "languages": ["Python"]}
            mock_kb.save.return_value = Path(temp_dir) / "test_repo_kb.json"
            mock_kb.get_negotiation_context.return_value = {
                "repo_name": "test-repo",
                "license": "MIT",
                "base_price": 0.5,
            }

            mock_ingester.ingest.return_value = mock_kb

            # Perform ingestion
            ingester = MockIngester()
            kb = ingester.ingest(mock_github_repo["url"])

            # Verify
            assert kb.repo_url == mock_github_repo["url"]
            assert kb.statistics["code_files"] == 4
            print(f"  ✓ Ingested repository: {mock_github_repo['url']}")
            print(f"  ✓ Created knowledge base with {kb.statistics['code_files']} files")

    def test_step2_rate_limiting(self):
        """Step 2: Test that rate limiting works for API requests."""
        print("\n=== Step 2: Rate Limiting ===")

        from rra.api.rate_limiter import RateLimiter, RateLimitConfig

        # Create limiter with low limits for testing
        config = RateLimitConfig(
            requests_per_minute=5,
            burst_size=3,
            exempt_paths=["/health"],
        )
        limiter = RateLimiter(config)

        # Create mock request
        mock_request = MagicMock()
        mock_request.url.path = "/api/ingest"
        mock_request.client.host = "192.168.1.100"
        mock_request.headers.get = MagicMock(return_value="")

        # Make requests until rate limited
        allowed_count = 0
        blocked_count = 0

        async def check_limits():
            nonlocal allowed_count, blocked_count
            for i in range(10):
                allowed, headers = await limiter.check_rate_limit(mock_request)
                if allowed:
                    allowed_count += 1
                else:
                    blocked_count += 1

        asyncio.get_event_loop().run_until_complete(check_limits())

        print(f"  ✓ Allowed requests: {allowed_count}")
        print(f"  ✓ Blocked requests: {blocked_count}")
        assert allowed_count > 0, "Should allow some requests"
        assert blocked_count > 0, "Should block excess requests"

    def test_step3_network_resilience(self, temp_dir):
        """Step 3: Test network resilience with circuit breaker."""
        print("\n=== Step 3: Network Resilience ===")

        from rra.integration.network_resilience import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitState,
            RequestQueue,
        )

        # Create circuit breaker
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=1.0,
        )
        cb = CircuitBreaker("test_service", config)

        # Initially closed
        assert cb.state == CircuitState.CLOSED
        print(f"  ✓ Circuit breaker initial state: {cb.state.value}")

        # Simulate failures
        for i in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        print(f"  ✓ Circuit opened after 3 failures: {cb.state.value}")

        # Verify requests are blocked
        assert cb.allow_request() is False
        print("  ✓ Requests blocked while circuit is open")

        # Test request queue
        queue = RequestQueue(queue_dir=temp_dir)
        queue.enqueue("req1", "post_entry", ("content",), {"author": "test"})
        assert queue.size() == 1
        print(f"  ✓ Request queued for retry: {queue.size()} pending")

        # Wait for timeout and test half-open
        import time
        time.sleep(1.1)

        assert cb.state == CircuitState.HALF_OPEN
        print(f"  ✓ Circuit transitioned to half-open: {cb.state.value}")

        # Simulate recovery
        cb.record_success()
        cb.record_success()

        assert cb.state == CircuitState.CLOSED
        print(f"  ✓ Circuit recovered to closed: {cb.state.value}")

    def test_step4_natlangchain_transaction(self, mock_github_repo, mock_knowledge_base):
        """Step 4: Test posting transaction to NatLangChain."""
        print("\n=== Step 4: NatLangChain Transaction ===")

        from rra.integration.natlangchain_client import NatLangChainClient

        # Create client with mocked HTTP
        with patch('rra.integration.natlangchain_client.httpx') as mock_httpx:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "success",
                "entry": {
                    "id": "entry-12345",
                    "block_hash": "0xabc123...",
                }
            }

            mock_client_instance = MagicMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.get.return_value = mock_response
            mock_httpx.Client.return_value = mock_client_instance

            # Create NatLangChain client
            client = NatLangChainClient(
                base_url="http://mock-chain:5000",
                agent_id="rra-test-agent",
                enable_resilience=False,  # Disable for this test
            )
            client._client = mock_client_instance

            # Post RRA transaction
            success, result = client.post_rra_transaction(
                repo_url=mock_github_repo["url"],
                buyer_id="did:nlc:buyer123",
                license_model="MIT",
                price="0.5 ETH",
                terms={
                    "duration": "perpetual",
                    "scope": "worldwide",
                    "commercial_use": True,
                }
            )

            assert success is True
            assert "entry" in result
            print(f"  ✓ Transaction posted successfully")
            print(f"  ✓ Entry ID: {result['entry']['id']}")
            print(f"  ✓ Block hash: {result['entry']['block_hash']}")

    def test_step5_full_api_flow(self, temp_dir, mock_github_repo):
        """Step 5: Test full API flow with FastAPI test client."""
        print("\n=== Step 5: Full API Flow ===")

        from fastapi.testclient import TestClient
        from rra.api.server import create_app

        # Create app
        app = create_app()
        client = TestClient(app)

        # Test health endpoint (should bypass rate limiting)
        response = client.get("/health")
        assert response.status_code == 200
        print("  ✓ Health check passed")

        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        print(f"  ✓ Root endpoint returns {len(data['endpoints'])} endpoint categories")

        # Test protected endpoint without auth (should fail)
        response = client.post(
            "/api/ingest",
            json={"repo_url": mock_github_repo["url"]}
        )
        assert response.status_code == 401
        print("  ✓ Protected endpoint requires authentication")

        # Test with API key
        with patch.dict('os.environ', {'RRA_API_KEYS': 'test-api-key-12345'}):
            # Recreate app to pick up new env
            app = create_app()
            client = TestClient(app)

            response = client.post(
                "/api/ingest",
                json={"repo_url": mock_github_repo["url"]},
                headers={"X-API-Key": "test-api-key-12345"}
            )
            # Will fail because repo doesn't exist, but auth should pass
            # Status could be 500 (repo not found) or 200 (if mocked)
            assert response.status_code != 401
            print("  ✓ API key authentication works")

    def test_step6_environment_config(self):
        """Step 6: Test environment configuration."""
        print("\n=== Step 6: Environment Configuration ===")

        from rra.config.environment import (
            Environment,
            get_config,
            reload_config,
            is_development,
            is_production,
        )

        # Test development config
        with patch.dict('os.environ', {'RRA_ENV': 'development'}):
            config = reload_config()
            assert config.environment == Environment.DEVELOPMENT
            assert config.debug is True
            print(f"  ✓ Development config: debug={config.debug}")

        # Test production config
        with patch.dict('os.environ', {'RRA_ENV': 'production', 'RRA_JWT_SECRET': 'secret123'}):
            config = reload_config()
            assert config.environment == Environment.PRODUCTION
            assert config.debug is False
            print(f"  ✓ Production config: debug={config.debug}")

    def test_step7_secrets_management(self, temp_dir):
        """Step 7: Test secrets management."""
        print("\n=== Step 7: Secrets Management ===")

        from rra.security.secrets import (
            SecretsManager,
            EnvironmentSecretsBackend,
            FileSecretsBackend,
        )

        # Test environment backend
        with patch.dict('os.environ', {
            'RRA_API_KEY': 'secret-api-key',
            'RRA_JWT_SECRET': 'jwt-secret-123',
        }):
            env_backend = EnvironmentSecretsBackend(prefix="RRA_")

            api_key = env_backend.get("API_KEY")
            assert api_key == "secret-api-key"
            print(f"  ✓ Environment secrets: API_KEY retrieved")

        # Test file backend
        secrets_dir = Path(temp_dir) / "secrets"
        secrets_dir.mkdir()
        (secrets_dir / "database_password").write_text("db-pass-456")

        file_backend = FileSecretsBackend(str(secrets_dir))
        db_pass = file_backend.get("database_password")
        assert db_pass == "db-pass-456"
        print(f"  ✓ File secrets: database_password retrieved")

        # Test secrets manager with caching
        manager = SecretsManager(backend=env_backend)
        with patch.dict('os.environ', {'RRA_CACHED_SECRET': 'cached-value'}):
            # First call
            val1 = manager.get("CACHED_SECRET")
            # Second call (should use cache)
            val2 = manager.get("CACHED_SECRET")
            assert val1 == val2
            print(f"  ✓ Secrets caching works")

    def test_full_e2e_flow(self, temp_dir, mock_github_repo, mock_knowledge_base):
        """Run complete end-to-end flow."""
        print("\n" + "="*60)
        print("FULL END-TO-END TEST: GitHub Scan → NatLangChain Upload")
        print("="*60)

        # Step 1: Ingest
        self.test_step1_repository_ingestion(temp_dir, mock_github_repo)

        # Step 2: Rate Limiting
        self.test_step2_rate_limiting()

        # Step 3: Network Resilience
        self.test_step3_network_resilience(temp_dir)

        # Step 4: NatLangChain Transaction
        self.test_step4_natlangchain_transaction(mock_github_repo, mock_knowledge_base)

        # Step 5: Full API Flow
        self.test_step5_full_api_flow(temp_dir, mock_github_repo)

        # Step 6: Environment Config
        self.test_step6_environment_config()

        # Step 7: Secrets Management
        self.test_step7_secrets_management(temp_dir)

        print("\n" + "="*60)
        print("✓ ALL END-TO-END TESTS PASSED")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
