# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
NatLangChain API Client for direct chain interaction.

Provides HTTP client for posting entries, intents, and transactions
to the NatLangChain blockchain.
"""

from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
import json
import logging

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

logger = logging.getLogger(__name__)

# Default NatLangChain API endpoint
DEFAULT_CHAIN_URL = "http://localhost:5000"


@dataclass
class ChainEntry:
    """Represents an entry on the NatLangChain."""
    content: str
    author: str
    intent: str
    timestamp: str
    status: str
    entry_id: Optional[str] = None
    block_hash: Optional[str] = None
    validation_status: Optional[str] = None


@dataclass
class ChainHealth:
    """Chain health status."""
    status: str
    service: str
    blocks: int
    pending_entries: int
    llm_validation_available: bool


class NatLangChainClient:
    """
    HTTP client for NatLangChain API.

    Provides methods for:
    - Posting natural language entries to the chain
    - Mining blocks
    - Querying chain state
    - Getting narratives
    """

    def __init__(
        self,
        base_url: str = DEFAULT_CHAIN_URL,
        timeout: float = 30.0,
        agent_id: Optional[str] = None
    ):
        """
        Initialize NatLangChain client.

        Args:
            base_url: NatLangChain API base URL
            timeout: Request timeout in seconds
            agent_id: Optional agent identifier for attribution
        """
        if not HAS_HTTPX:
            raise ImportError("httpx is required for NatLangChainClient")

        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.agent_id = agent_id
        self._client = httpx.Client(timeout=timeout)

    def __del__(self):
        """Close HTTP client on cleanup."""
        if hasattr(self, '_client'):
            self._client.close()

    def health_check(self) -> Tuple[bool, Optional[ChainHealth]]:
        """
        Check NatLangChain API health.

        Returns:
            Tuple of (is_healthy, health_info)
        """
        try:
            response = self._client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                health = ChainHealth(
                    status=data.get("status", "unknown"),
                    service=data.get("service", "NatLangChain"),
                    blocks=data.get("blocks", 0),
                    pending_entries=data.get("pending_entries", 0),
                    llm_validation_available=data.get("llm_validation_available", False)
                )
                return True, health
            return False, None
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False, None

    def post_entry(
        self,
        content: str,
        author: str,
        intent: str,
        metadata: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        auto_mine: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Post a natural language entry to the chain.

        Args:
            content: Natural language description of the transaction/event
            author: Identifier of the entry creator
            intent: Brief summary of the entry's purpose
            metadata: Optional additional structured data
            validate: Whether to validate the entry (default True)
            auto_mine: Whether to immediately mine a block (default False)

        Returns:
            Tuple of (success, result_data)
        """
        payload = {
            "content": content,
            "author": author,
            "intent": intent,
            "validate": validate,
            "auto_mine": auto_mine
        }

        if metadata:
            payload["metadata"] = metadata

        try:
            response = self._client.post(
                f"{self.base_url}/entry",
                json=payload
            )

            result = response.json()

            if response.status_code == 200:
                logger.info(f"Entry posted successfully: {intent}")
                return True, result
            else:
                logger.warning(f"Entry post failed: {result}")
                return False, result

        except Exception as e:
            logger.error(f"Failed to post entry: {e}")
            return False, {"error": str(e)}

    def post_rra_transaction(
        self,
        repo_url: str,
        buyer_id: str,
        license_model: str,
        price: str,
        terms: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Post an RRA licensing transaction to the chain.

        Args:
            repo_url: Repository URL being licensed
            buyer_id: Identifier of the buyer
            license_model: Type of license (MIT, GPL, commercial, etc.)
            price: Transaction price (e.g., "0.5 ETH")
            terms: Negotiated license terms
            agent_id: Optional agent identifier

        Returns:
            Tuple of (success, result_data)
        """
        author = agent_id or self.agent_id or "rra-agent"

        content = (
            f"RRA License Transaction: {author} grants {buyer_id} a {license_model} "
            f"license for repository {repo_url} at price {price}. "
            f"Terms include: {json.dumps(terms)}"
        )

        intent = f"License {repo_url} to {buyer_id}"

        metadata = {
            "type": "rra_transaction",
            "repo_url": repo_url,
            "buyer_id": buyer_id,
            "license_model": license_model,
            "price": price,
            "terms": terms,
            "agent_id": author,
            "timestamp": datetime.now().isoformat()
        }

        return self.post_entry(
            content=content,
            author=author,
            intent=intent,
            metadata=metadata,
            validate=True,
            auto_mine=True
        )

    def post_negotiation_intent(
        self,
        repo_url: str,
        intent_type: str,
        details: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Post a negotiation intent to the chain.

        Args:
            repo_url: Repository being negotiated
            intent_type: Type of intent (quote_requested, offer_made, counter_offer, etc.)
            details: Intent details
            agent_id: Optional agent identifier

        Returns:
            Tuple of (success, result_data)
        """
        author = agent_id or self.agent_id or "rra-agent"

        content = (
            f"RRA Negotiation Intent: {intent_type} for {repo_url}. "
            f"Details: {json.dumps(details)}"
        )

        intent = f"Negotiation {intent_type}: {repo_url}"

        metadata = {
            "type": "rra_negotiation_intent",
            "intent_type": intent_type,
            "repo_url": repo_url,
            "details": details,
            "agent_id": author,
            "timestamp": datetime.now().isoformat()
        }

        return self.post_entry(
            content=content,
            author=author,
            intent=intent,
            metadata=metadata,
            validate=True,
            auto_mine=False
        )

    def mine_block(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Mine pending entries into a new block.

        Returns:
            Tuple of (success, result_data)
        """
        try:
            response = self._client.post(f"{self.base_url}/mine")
            result = response.json()

            if response.status_code == 200:
                logger.info("Block mined successfully")
                return True, result
            else:
                return False, result

        except Exception as e:
            logger.error(f"Failed to mine block: {e}")
            return False, {"error": str(e)}

    def get_chain_narrative(self) -> Tuple[bool, str]:
        """
        Get the human-readable narrative of the chain.

        Returns:
            Tuple of (success, narrative_text)
        """
        try:
            response = self._client.get(f"{self.base_url}/chain/narrative")

            if response.status_code == 200:
                result = response.json()
                return True, result.get("narrative", "")
            return False, ""

        except Exception as e:
            logger.error(f"Failed to get narrative: {e}")
            return False, ""

    def search_entries(
        self,
        query: Optional[str] = None,
        author: Optional[str] = None,
        intent: Optional[str] = None,
        limit: int = 10
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Search entries on the chain.

        Args:
            query: Text search query
            author: Filter by author
            intent: Filter by intent
            limit: Maximum results

        Returns:
            Tuple of (success, entries_list)
        """
        params = {"limit": limit}
        if query:
            params["q"] = query
        if author:
            params["author"] = author
        if intent:
            params["intent"] = intent

        try:
            response = self._client.get(
                f"{self.base_url}/entries/search",
                params=params
            )

            if response.status_code == 200:
                result = response.json()
                return True, result.get("entries", [])
            return False, []

        except Exception as e:
            logger.error(f"Failed to search entries: {e}")
            return False, []

    def get_stats(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Get blockchain statistics.

        Returns:
            Tuple of (success, stats_dict)
        """
        try:
            response = self._client.get(f"{self.base_url}/stats")

            if response.status_code == 200:
                return True, response.json()
            return False, {}

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return False, {}


class AsyncNatLangChainClient:
    """
    Async HTTP client for NatLangChain API.

    Same functionality as NatLangChainClient but with async/await support.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_CHAIN_URL,
        timeout: float = 30.0,
        agent_id: Optional[str] = None
    ):
        """Initialize async NatLangChain client."""
        if not HAS_HTTPX:
            raise ImportError("httpx is required for AsyncNatLangChainClient")

        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.agent_id = agent_id
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

    async def health_check(self) -> Tuple[bool, Optional[ChainHealth]]:
        """Check NatLangChain API health."""
        try:
            response = await self._client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                health = ChainHealth(
                    status=data.get("status", "unknown"),
                    service=data.get("service", "NatLangChain"),
                    blocks=data.get("blocks", 0),
                    pending_entries=data.get("pending_entries", 0),
                    llm_validation_available=data.get("llm_validation_available", False)
                )
                return True, health
            return False, None
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False, None

    async def post_entry(
        self,
        content: str,
        author: str,
        intent: str,
        metadata: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        auto_mine: bool = False
    ) -> Tuple[bool, Dict[str, Any]]:
        """Post a natural language entry to the chain."""
        payload = {
            "content": content,
            "author": author,
            "intent": intent,
            "validate": validate,
            "auto_mine": auto_mine
        }

        if metadata:
            payload["metadata"] = metadata

        try:
            response = await self._client.post(
                f"{self.base_url}/entry",
                json=payload
            )

            result = response.json()

            if response.status_code == 200:
                logger.info(f"Entry posted successfully: {intent}")
                return True, result
            else:
                logger.warning(f"Entry post failed: {result}")
                return False, result

        except Exception as e:
            logger.error(f"Failed to post entry: {e}")
            return False, {"error": str(e)}

    async def post_rra_transaction(
        self,
        repo_url: str,
        buyer_id: str,
        license_model: str,
        price: str,
        terms: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Post an RRA licensing transaction to the chain."""
        author = agent_id or self.agent_id or "rra-agent"

        content = (
            f"RRA License Transaction: {author} grants {buyer_id} a {license_model} "
            f"license for repository {repo_url} at price {price}. "
            f"Terms include: {json.dumps(terms)}"
        )

        intent = f"License {repo_url} to {buyer_id}"

        metadata = {
            "type": "rra_transaction",
            "repo_url": repo_url,
            "buyer_id": buyer_id,
            "license_model": license_model,
            "price": price,
            "terms": terms,
            "agent_id": author,
            "timestamp": datetime.now().isoformat()
        }

        return await self.post_entry(
            content=content,
            author=author,
            intent=intent,
            metadata=metadata,
            validate=True,
            auto_mine=True
        )


def get_chain_client(
    base_url: Optional[str] = None,
    agent_id: Optional[str] = None,
    async_mode: bool = False
):
    """
    Get a NatLangChain client instance.

    Args:
        base_url: Override default chain URL
        agent_id: Agent identifier for attribution
        async_mode: Return async client if True

    Returns:
        NatLangChainClient or AsyncNatLangChainClient instance
    """
    url = base_url or DEFAULT_CHAIN_URL

    if async_mode:
        return AsyncNatLangChainClient(base_url=url, agent_id=agent_id)
    return NatLangChainClient(base_url=url, agent_id=agent_id)
