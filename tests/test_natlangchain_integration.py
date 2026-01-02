# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Integration tests for RRA Module posting to NatLangChain.

These tests verify the full integration between RRA and NatLangChain,
including posting transactions, intents, and entries to the blockchain.

To run these tests:
1. Start NatLangChain server: cd /path/to/NatLangChain && python run_server.py
2. Run tests: pytest tests/test_natlangchain_integration.py -v
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from rra.integration.natlangchain_client import (
    NatLangChainClient,
    AsyncNatLangChainClient,
    get_chain_client,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for unit testing."""
    with patch('rra.integration.natlangchain_client.httpx') as mock_httpx:
        mock_client = MagicMock()
        mock_httpx.Client.return_value = mock_client
        yield mock_client


@pytest.fixture
def chain_client(mock_httpx_client):
    """Create a chain client with mocked HTTP."""
    client = NatLangChainClient(
        base_url="http://localhost:5000",
        agent_id="test-agent"
    )
    client._client = mock_httpx_client
    return client


# =============================================================================
# Unit Tests (with mocks)
# =============================================================================


class TestNatLangChainClient:
    """Unit tests for NatLangChainClient."""

    def test_client_initialization(self):
        """Test client initializes with correct parameters."""
        with patch('rra.integration.natlangchain_client.httpx'):
            client = NatLangChainClient(
                base_url="http://test:5000",
                agent_id="my-agent"
            )
            assert client.base_url == "http://test:5000"
            assert client.agent_id == "my-agent"

    def test_health_check_success(self, chain_client, mock_httpx_client):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "NatLangChain API",
            "blocks": 5,
            "pending_entries": 2,
            "llm_validation_available": True
        }
        mock_httpx_client.get.return_value = mock_response

        success, health = chain_client.health_check()

        assert success is True
        assert health.status == "healthy"
        assert health.blocks == 5
        assert health.pending_entries == 2

    def test_health_check_failure(self, chain_client, mock_httpx_client):
        """Test health check failure."""
        mock_httpx_client.get.side_effect = Exception("Connection refused")

        success, health = chain_client.health_check()

        assert success is False
        assert health is None

    def test_post_entry_success(self, chain_client, mock_httpx_client):
        """Test successful entry posting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "entry": {
                "content": "Test entry",
                "author": "test-author",
                "status": "pending"
            }
        }
        mock_httpx_client.post.return_value = mock_response

        success, result = chain_client.post_entry(
            content="Test entry content",
            author="test-author",
            intent="Test intent"
        )

        assert success is True
        assert result["status"] == "success"
        mock_httpx_client.post.assert_called_once()

    def test_post_entry_with_metadata(self, chain_client, mock_httpx_client):
        """Test entry posting with metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_httpx_client.post.return_value = mock_response

        metadata = {"key": "value", "type": "test"}
        success, _ = chain_client.post_entry(
            content="Test",
            author="author",
            intent="intent",
            metadata=metadata
        )

        assert success is True
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["metadata"] == metadata

    def test_post_rra_transaction(self, chain_client, mock_httpx_client):
        """Test posting RRA transaction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "entry": {"id": "entry-123"}
        }
        mock_httpx_client.post.return_value = mock_response

        success, result = chain_client.post_rra_transaction(
            repo_url="https://github.com/test/repo",
            buyer_id="buyer-123",
            license_model="MIT",
            price="0.5 ETH",
            terms={"duration": "perpetual", "scope": "worldwide"}
        )

        assert success is True
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert "rra_transaction" in payload["metadata"]["type"]
        assert payload["metadata"]["price"] == "0.5 ETH"

    def test_post_negotiation_intent(self, chain_client, mock_httpx_client):
        """Test posting negotiation intent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_httpx_client.post.return_value = mock_response

        success, _ = chain_client.post_negotiation_intent(
            repo_url="https://github.com/test/repo",
            intent_type="quote_requested",
            details={"budget": "1 ETH", "license_preference": "MIT"}
        )

        assert success is True
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert "rra_negotiation_intent" in payload["metadata"]["type"]

    def test_mine_block_success(self, chain_client, mock_httpx_client):
        """Test successful block mining."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "block": {"hash": "000abc123", "index": 5}
        }
        mock_httpx_client.post.return_value = mock_response

        success, result = chain_client.mine_block()

        assert success is True
        assert "block" in result

    def test_get_chain_narrative(self, chain_client, mock_httpx_client):
        """Test getting chain narrative."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "narrative": "Block 1: Genesis...\nBlock 2: Test entry..."
        }
        mock_httpx_client.get.return_value = mock_response

        success, narrative = chain_client.get_chain_narrative()

        assert success is True
        assert "Genesis" in narrative

    def test_search_entries(self, chain_client, mock_httpx_client):
        """Test searching entries."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entries": [
                {"content": "Entry 1", "author": "alice"},
                {"content": "Entry 2", "author": "bob"}
            ]
        }
        mock_httpx_client.get.return_value = mock_response

        success, entries = chain_client.search_entries(author="alice")

        assert success is True
        assert len(entries) == 2

    def test_get_stats(self, chain_client, mock_httpx_client):
        """Test getting chain stats."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_blocks": 10,
            "total_entries": 50,
            "pending_entries": 3
        }
        mock_httpx_client.get.return_value = mock_response

        success, stats = chain_client.get_stats()

        assert success is True
        assert stats["total_blocks"] == 10


class TestGetChainClient:
    """Test the get_chain_client factory function."""

    def test_get_sync_client(self):
        """Test getting sync client."""
        with patch('rra.integration.natlangchain_client.httpx'):
            client = get_chain_client(
                base_url="http://test:5000",
                agent_id="test-agent",
                async_mode=False
            )
            assert isinstance(client, NatLangChainClient)

    def test_get_async_client(self):
        """Test getting async client."""
        with patch('rra.integration.natlangchain_client.httpx'):
            client = get_chain_client(
                base_url="http://test:5000",
                agent_id="test-agent",
                async_mode=True
            )
            assert isinstance(client, AsyncNatLangChainClient)


# =============================================================================
# Integration Tests (require running NatLangChain server)
# =============================================================================


@pytest.mark.integration
class TestNatLangChainIntegration:
    """
    Integration tests that require a running NatLangChain server.

    Run with: pytest tests/test_natlangchain_integration.py -v -m integration

    Before running, start NatLangChain:
        cd /path/to/NatLangChain
        python run_server.py
    """

    @pytest.fixture
    def live_client(self):
        """Create a client connected to live NatLangChain server."""
        try:
            client = NatLangChainClient(
                base_url="http://localhost:5000",
                agent_id="rra-integration-test"
            )
            return client
        except ImportError:
            pytest.skip("httpx not available")

    def test_live_health_check(self, live_client):
        """Test health check against live server."""
        success, health = live_client.health_check()

        if not success:
            pytest.skip("NatLangChain server not running")

        assert health.status == "healthy"
        assert health.service == "NatLangChain API"

    def test_live_post_entry(self, live_client):
        """Test posting entry to live server."""
        success, health = live_client.health_check()
        if not success:
            pytest.skip("NatLangChain server not running")

        success, result = live_client.post_entry(
            content="RRA Integration Test: Verifying chain posting capability",
            author="rra-integration-test",
            intent="Test RRA-NatLangChain integration",
            metadata={"test": True, "timestamp": datetime.now().isoformat()},
            auto_mine=True
        )

        assert success is True
        assert result.get("status") == "success"

    def test_live_post_rra_transaction(self, live_client):
        """Test posting RRA transaction to live server."""
        success, health = live_client.health_check()
        if not success:
            pytest.skip("NatLangChain server not running")

        success, result = live_client.post_rra_transaction(
            repo_url="https://github.com/test/integration-test",
            buyer_id="test-buyer-001",
            license_model="MIT",
            price="0.1 ETH",
            terms={
                "duration": "perpetual",
                "scope": "worldwide",
                "modifications_allowed": True
            }
        )

        assert success is True

    def test_live_get_narrative(self, live_client):
        """Test getting narrative from live server."""
        success, health = live_client.health_check()
        if not success:
            pytest.skip("NatLangChain server not running")

        success, narrative = live_client.get_chain_narrative()

        assert success is True
        assert isinstance(narrative, str)

    def test_live_search_entries(self, live_client):
        """Test searching entries on live server."""
        success, health = live_client.health_check()
        if not success:
            pytest.skip("NatLangChain server not running")

        # First post an entry
        live_client.post_entry(
            content="Searchable test entry for RRA integration",
            author="rra-search-test",
            intent="Search test",
            auto_mine=True
        )

        # Then search for it
        success, entries = live_client.search_entries(
            author="rra-search-test",
            limit=5
        )

        assert success is True

    def test_live_full_negotiation_flow(self, live_client):
        """Test full negotiation flow posting to chain."""
        success, health = live_client.health_check()
        if not success:
            pytest.skip("NatLangChain server not running")

        repo_url = "https://github.com/test/negotiation-flow-test"

        # Step 1: Post quote request intent
        success, _ = live_client.post_negotiation_intent(
            repo_url=repo_url,
            intent_type="quote_requested",
            details={
                "buyer_id": "buyer-flow-test",
                "budget": "1 ETH",
                "license_preference": "commercial"
            }
        )
        assert success is True

        # Step 2: Post offer made intent
        success, _ = live_client.post_negotiation_intent(
            repo_url=repo_url,
            intent_type="offer_made",
            details={
                "price": "0.8 ETH",
                "license_model": "commercial",
                "terms": {"duration": "1 year"}
            }
        )
        assert success is True

        # Step 3: Post transaction completion
        success, result = live_client.post_rra_transaction(
            repo_url=repo_url,
            buyer_id="buyer-flow-test",
            license_model="commercial",
            price="0.75 ETH",
            terms={
                "duration": "1 year",
                "scope": "worldwide",
                "exclusive": False
            }
        )
        assert success is True

        # Verify the transaction is on chain
        success, stats = live_client.get_stats()
        assert success is True
        assert stats.get("total_entries", 0) > 0


# =============================================================================
# Async Tests
# =============================================================================


class TestAsyncNatLangChainClient:
    """Tests for AsyncNatLangChainClient."""

    @pytest.fixture
    def mock_async_client(self):
        """Mock async httpx client."""
        with patch('rra.integration.natlangchain_client.httpx') as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.AsyncClient.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_async_health_check(self, mock_async_client):
        """Test async health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "NatLangChain API",
            "blocks": 5,
            "pending_entries": 0,
            "llm_validation_available": True
        }
        mock_async_client.get = AsyncMock(return_value=mock_response)

        async with AsyncNatLangChainClient() as client:
            client._client = mock_async_client
            success, health = await client.health_check()

            assert success is True
            assert health.status == "healthy"

    @pytest.mark.asyncio
    async def test_async_post_entry(self, mock_async_client):
        """Test async entry posting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_async_client.post = AsyncMock(return_value=mock_response)

        async with AsyncNatLangChainClient() as client:
            client._client = mock_async_client
            success, result = await client.post_entry(
                content="Async test",
                author="async-author",
                intent="Async test intent"
            )

            assert success is True

    @pytest.mark.asyncio
    async def test_async_post_rra_transaction(self, mock_async_client):
        """Test async RRA transaction posting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_async_client.post = AsyncMock(return_value=mock_response)

        async with AsyncNatLangChainClient(agent_id="async-rra-agent") as client:
            client._client = mock_async_client
            success, result = await client.post_rra_transaction(
                repo_url="https://github.com/async/test",
                buyer_id="async-buyer",
                license_model="MIT",
                price="0.3 ETH",
                terms={"scope": "global"}
            )

            assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
