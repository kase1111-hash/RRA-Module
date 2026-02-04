# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Price Oracle Integration for RRA Module.

Provides real-time price feeds from multiple sources:
- Chainlink (primary, on-chain)
- CoinGecko (fallback, off-chain API)
- Pyth Network (alternative on-chain)

Addresses H-002: Hardcoded ETH/USD rate needs oracle integration.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class PriceSource(str, Enum):
    """Available price data sources."""

    CHAINLINK = "chainlink"
    COINGECKO = "coingecko"
    PYTH = "pyth"
    CACHE = "cache"
    FALLBACK = "fallback"


@dataclass
class PriceData:
    """
    Price data from oracle with metadata.

    Includes staleness tracking and confidence indicators.
    """

    price: Decimal
    currency_pair: str  # e.g., "ETH/USD"
    source: PriceSource
    timestamp: datetime
    block_number: Optional[int] = None  # For on-chain sources
    confidence: float = 1.0  # 0-1, lower if using fallback
    round_id: Optional[int] = None  # Chainlink round ID

    @property
    def age_seconds(self) -> float:
        """Get age of price data in seconds."""
        return (datetime.utcnow() - self.timestamp).total_seconds()

    @property
    def is_stale(self) -> bool:
        """Check if price data is stale (> 1 hour old)."""
        return self.age_seconds > 3600

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "price": str(self.price),
            "currency_pair": self.currency_pair,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "block_number": self.block_number,
            "confidence": self.confidence,
            "age_seconds": self.age_seconds,
            "is_stale": self.is_stale,
        }


@dataclass
class PriceCache:
    """
    Simple in-memory price cache with TTL.

    Thread-safe for read operations; write conflicts are acceptable
    as they just result in redundant fetches.
    """

    cache: Dict[str, PriceData] = field(default_factory=dict)
    ttl_seconds: int = 60  # 1 minute default TTL

    def get(self, currency_pair: str) -> Optional[PriceData]:
        """Get cached price if not expired."""
        data = self.cache.get(currency_pair)
        if data is None:
            return None
        if data.age_seconds > self.ttl_seconds:
            del self.cache[currency_pair]
            return None
        return data

    def set(self, currency_pair: str, data: PriceData) -> None:
        """Cache price data."""
        self.cache[currency_pair] = data

    def clear(self) -> None:
        """Clear all cached prices."""
        self.cache.clear()


class PriceOracle(ABC):
    """Abstract base class for price oracles."""

    @abstractmethod
    def get_price(self, base: str, quote: str = "USD") -> Optional[PriceData]:
        """
        Get current price for a currency pair.

        Args:
            base: Base currency (e.g., "ETH")
            quote: Quote currency (e.g., "USD")

        Returns:
            PriceData if available, None otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if oracle is currently available."""
        pass


class ChainlinkOracle(PriceOracle):
    """
    Chainlink price feed oracle.

    Uses Chainlink's decentralized oracle network for
    reliable, manipulation-resistant price data.

    Requires web3 connection to Ethereum mainnet or L2.
    """

    # Chainlink price feed addresses (Ethereum mainnet)
    FEED_ADDRESSES = {
        "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
        "LINK/USD": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",
        "USDC/USD": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
        "DAI/USD": "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9",
    }

    # Chainlink AggregatorV3 ABI (minimal for price feeds)
    AGGREGATOR_ABI = [
        {
            "inputs": [],
            "name": "latestRoundData",
            "outputs": [
                {"name": "roundId", "type": "uint80"},
                {"name": "answer", "type": "int256"},
                {"name": "startedAt", "type": "uint256"},
                {"name": "updatedAt", "type": "uint256"},
                {"name": "answeredInRound", "type": "uint80"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    def __init__(
        self,
        web3_provider_url: Optional[str] = None,
        custom_feeds: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize Chainlink oracle.

        Args:
            web3_provider_url: Ethereum RPC URL (default from RRA_WEB3_PROVIDER_URL)
            custom_feeds: Additional feed addresses to use
        """
        self.provider_url = web3_provider_url or os.environ.get(
            "RRA_WEB3_PROVIDER_URL"
        )
        self.feeds = {**self.FEED_ADDRESSES}
        if custom_feeds:
            self.feeds.update(custom_feeds)

        self._web3 = None
        self._contracts: Dict[str, Any] = {}

    def _get_web3(self):
        """Lazy-load web3 connection."""
        if self._web3 is None:
            if not self.provider_url:
                return None
            try:
                from web3 import Web3

                self._web3 = Web3(Web3.HTTPProvider(self.provider_url))
                if not self._web3.is_connected():
                    logger.warning("Web3 provider not connected")
                    self._web3 = None
            except ImportError:
                logger.warning("web3 package not installed for Chainlink oracle")
            except Exception as e:
                logger.warning(f"Failed to connect to web3 provider: {e}")

        return self._web3

    def _get_contract(self, pair: str):
        """Get or create contract instance for feed."""
        if pair not in self._contracts:
            web3 = self._get_web3()
            if web3 is None or pair not in self.feeds:
                return None

            from web3 import Web3

            address = Web3.to_checksum_address(self.feeds[pair])
            self._contracts[pair] = web3.eth.contract(
                address=address, abi=self.AGGREGATOR_ABI
            )

        return self._contracts[pair]

    def get_price(self, base: str, quote: str = "USD") -> Optional[PriceData]:
        """Get price from Chainlink feed."""
        pair = f"{base.upper()}/{quote.upper()}"

        contract = self._get_contract(pair)
        if contract is None:
            return None

        try:
            # Get latest round data
            round_id, answer, started_at, updated_at, answered_in_round = (
                contract.functions.latestRoundData().call()
            )

            # Get decimals
            decimals = contract.functions.decimals().call()

            # Convert to Decimal with proper precision
            price = Decimal(answer) / Decimal(10**decimals)

            # Get current block for reference
            web3 = self._get_web3()
            block_number = web3.eth.block_number if web3 else None

            return PriceData(
                price=price,
                currency_pair=pair,
                source=PriceSource.CHAINLINK,
                timestamp=datetime.utcfromtimestamp(updated_at),
                block_number=block_number,
                confidence=1.0,  # Chainlink is highly reliable
                round_id=round_id,
            )

        except Exception as e:
            logger.warning(f"Chainlink price fetch failed for {pair}: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Chainlink oracle is available."""
        web3 = self._get_web3()
        return web3 is not None and web3.is_connected()


class CoinGeckoOracle(PriceOracle):
    """
    CoinGecko API price oracle.

    Free API with reasonable rate limits.
    Used as fallback when on-chain oracles unavailable.
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    # CoinGecko ID mapping
    COIN_IDS = {
        "ETH": "ethereum",
        "BTC": "bitcoin",
        "LINK": "chainlink",
        "USDC": "usd-coin",
        "USDT": "tether",
        "DAI": "dai",
        "MATIC": "matic-network",
        "ARB": "arbitrum",
        "OP": "optimism",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10,
    ):
        """
        Initialize CoinGecko oracle.

        Args:
            api_key: Optional CoinGecko Pro API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.environ.get("COINGECKO_API_KEY")
        self.timeout = timeout
        self._last_request_time = 0
        self._min_request_interval = 1.5  # Rate limit: ~30 req/min for free tier

    def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def get_price(self, base: str, quote: str = "USD") -> Optional[PriceData]:
        """Get price from CoinGecko API."""
        base = base.upper()
        quote = quote.lower()

        coin_id = self.COIN_IDS.get(base)
        if coin_id is None:
            logger.warning(f"Unknown coin for CoinGecko: {base}")
            return None

        self._rate_limit()

        try:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": quote,
                "include_last_updated_at": "true",
            }

            headers = {}
            if self.api_key:
                headers["x-cg-pro-api-key"] = self.api_key

            response = requests.get(
                url, params=params, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            if coin_id not in data:
                return None

            coin_data = data[coin_id]
            price = Decimal(str(coin_data[quote]))
            updated_at = coin_data.get("last_updated_at", int(time.time()))

            return PriceData(
                price=price,
                currency_pair=f"{base}/{quote.upper()}",
                source=PriceSource.COINGECKO,
                timestamp=datetime.utcfromtimestamp(updated_at),
                confidence=0.95,  # Slightly lower than on-chain
            )

        except requests.RequestException as e:
            logger.warning(f"CoinGecko API error for {base}/{quote}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.warning(f"CoinGecko response parsing error: {e}")
            return None

    def is_available(self) -> bool:
        """Check if CoinGecko API is reachable."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/ping", timeout=self.timeout
            )
            return response.status_code == 200
        except requests.RequestException:
            return False


class FallbackPriceOracle(PriceOracle):
    """
    Fallback oracle with hardcoded prices.

    Used only when all other oracles fail.
    Prices are conservative estimates with low confidence.
    """

    # Conservative fallback prices (updated periodically)
    FALLBACK_PRICES = {
        "ETH/USD": Decimal("2000"),
        "BTC/USD": Decimal("40000"),
        "LINK/USD": Decimal("15"),
        "USDC/USD": Decimal("1"),
        "USDT/USD": Decimal("1"),
        "DAI/USD": Decimal("1"),
    }

    # Last manual update date for fallback prices
    LAST_UPDATE = datetime(2025, 1, 1)

    def get_price(self, base: str, quote: str = "USD") -> Optional[PriceData]:
        """Get hardcoded fallback price."""
        pair = f"{base.upper()}/{quote.upper()}"

        price = self.FALLBACK_PRICES.get(pair)
        if price is None:
            return None

        logger.warning(
            f"Using FALLBACK price for {pair}. "
            f"Last updated: {self.LAST_UPDATE.date()}. "
            "Configure RRA_WEB3_PROVIDER_URL for live prices."
        )

        return PriceData(
            price=price,
            currency_pair=pair,
            source=PriceSource.FALLBACK,
            timestamp=self.LAST_UPDATE,
            confidence=0.5,  # Low confidence for hardcoded values
        )

    def is_available(self) -> bool:
        """Fallback is always available."""
        return True


class AggregatedPriceOracle:
    """
    Aggregated price oracle with fallback chain.

    Attempts oracles in order of preference:
    1. Chainlink (most reliable, on-chain)
    2. CoinGecko (API fallback)
    3. Hardcoded fallback (last resort)

    Includes caching to reduce API calls.
    """

    def __init__(
        self,
        cache_ttl_seconds: int = 60,
        enable_chainlink: bool = True,
        enable_coingecko: bool = True,
    ):
        """
        Initialize aggregated oracle.

        Args:
            cache_ttl_seconds: Cache TTL for prices
            enable_chainlink: Enable Chainlink oracle
            enable_coingecko: Enable CoinGecko oracle
        """
        self.cache = PriceCache(ttl_seconds=cache_ttl_seconds)

        # Build oracle chain
        self.oracles: List[PriceOracle] = []

        if enable_chainlink:
            self.oracles.append(ChainlinkOracle())

        if enable_coingecko:
            self.oracles.append(CoinGeckoOracle())

        # Fallback is always included
        self.oracles.append(FallbackPriceOracle())

    def get_price(
        self, base: str, quote: str = "USD", skip_cache: bool = False
    ) -> PriceData:
        """
        Get price from best available oracle.

        Args:
            base: Base currency
            quote: Quote currency
            skip_cache: Bypass cache for fresh price

        Returns:
            PriceData from best available source

        Raises:
            ValueError: If no oracle can provide a price (shouldn't happen with fallback)
        """
        pair = f"{base.upper()}/{quote.upper()}"

        # Check cache first
        if not skip_cache:
            cached = self.cache.get(pair)
            if cached is not None:
                # Return cached with updated source indicator
                return PriceData(
                    price=cached.price,
                    currency_pair=cached.currency_pair,
                    source=PriceSource.CACHE,
                    timestamp=cached.timestamp,
                    block_number=cached.block_number,
                    confidence=cached.confidence,
                    round_id=cached.round_id,
                )

        # Try each oracle in order
        for oracle in self.oracles:
            if not oracle.is_available():
                continue

            price_data = oracle.get_price(base, quote)
            if price_data is not None:
                # Cache successful result
                self.cache.set(pair, price_data)
                return price_data

        # This shouldn't happen with fallback oracle
        raise ValueError(f"No oracle could provide price for {pair}")

    def get_usd_value(self, amount: Decimal, currency: str) -> Tuple[Decimal, PriceData]:
        """
        Convert amount to USD value.

        Args:
            amount: Amount in the currency
            currency: Currency code

        Returns:
            Tuple of (USD value, price data used)
        """
        currency = currency.upper()

        # Stablecoins are 1:1 with USD
        if currency in ["USD", "USDC", "USDT", "DAI"]:
            price_data = PriceData(
                price=Decimal("1"),
                currency_pair=f"{currency}/USD",
                source=PriceSource.FALLBACK,
                timestamp=datetime.utcnow(),
                confidence=1.0,
            )
            return amount, price_data

        price_data = self.get_price(currency, "USD")
        usd_value = amount * price_data.price

        return usd_value, price_data

    def get_available_sources(self) -> List[Dict[str, Any]]:
        """
        Get status of all oracle sources.

        Returns:
            List of oracle status dictionaries
        """
        return [
            {
                "name": type(oracle).__name__,
                "available": oracle.is_available(),
            }
            for oracle in self.oracles
        ]


# Global oracle instance
_price_oracle: Optional[AggregatedPriceOracle] = None


def get_price_oracle() -> AggregatedPriceOracle:
    """
    Get the global price oracle instance.

    Returns:
        Configured AggregatedPriceOracle
    """
    global _price_oracle
    if _price_oracle is None:
        _price_oracle = AggregatedPriceOracle()
    return _price_oracle


def get_eth_usd_price() -> Decimal:
    """
    Convenience function to get current ETH/USD price.

    Returns:
        Current ETH price in USD
    """
    oracle = get_price_oracle()
    price_data = oracle.get_price("ETH", "USD")
    return price_data.price


def convert_to_usd(amount: Decimal, currency: str) -> Decimal:
    """
    Convenience function to convert amount to USD.

    Args:
        amount: Amount to convert
        currency: Source currency

    Returns:
        USD equivalent
    """
    oracle = get_price_oracle()
    usd_value, _ = oracle.get_usd_value(amount, currency)
    return usd_value
