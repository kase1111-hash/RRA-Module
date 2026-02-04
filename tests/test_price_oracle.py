# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for price oracle module."""

import time
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from rra.oracles.price_oracle import (
    PriceSource,
    PriceData,
    PriceCache,
    ChainlinkOracle,
    CoinGeckoOracle,
    FallbackPriceOracle,
    AggregatedPriceOracle,
    get_price_oracle,
    get_eth_usd_price,
    convert_to_usd,
)


class TestPriceData:
    """Tests for PriceData class."""

    def test_price_data_creation(self):
        """Test creating price data."""
        price_data = PriceData(
            price=Decimal("2500.50"),
            currency_pair="ETH/USD",
            source=PriceSource.CHAINLINK,
            timestamp=datetime.utcnow(),
        )

        assert price_data.price == Decimal("2500.50")
        assert price_data.currency_pair == "ETH/USD"
        assert price_data.source == PriceSource.CHAINLINK
        assert price_data.confidence == 1.0

    def test_price_data_staleness(self):
        """Test staleness detection."""
        # Fresh price
        fresh = PriceData(
            price=Decimal("2500"),
            currency_pair="ETH/USD",
            source=PriceSource.CHAINLINK,
            timestamp=datetime.utcnow(),
        )
        assert not fresh.is_stale

        # Stale price (> 1 hour old)
        stale = PriceData(
            price=Decimal("2500"),
            currency_pair="ETH/USD",
            source=PriceSource.CHAINLINK,
            timestamp=datetime.utcnow() - timedelta(hours=2),
        )
        assert stale.is_stale

    def test_price_data_age(self):
        """Test age calculation."""
        old_time = datetime.utcnow() - timedelta(minutes=30)
        price_data = PriceData(
            price=Decimal("2500"),
            currency_pair="ETH/USD",
            source=PriceSource.COINGECKO,
            timestamp=old_time,
        )

        # Age should be approximately 30 minutes (1800 seconds)
        assert 1790 < price_data.age_seconds < 1810

    def test_price_data_to_dict(self):
        """Test serialization."""
        price_data = PriceData(
            price=Decimal("2500.50"),
            currency_pair="ETH/USD",
            source=PriceSource.CHAINLINK,
            timestamp=datetime.utcnow(),
            block_number=12345678,
            confidence=0.95,
        )

        data = price_data.to_dict()

        assert data["price"] == "2500.50"
        assert data["currency_pair"] == "ETH/USD"
        assert data["source"] == "chainlink"
        assert data["block_number"] == 12345678
        assert data["confidence"] == 0.95
        assert "timestamp" in data
        assert "age_seconds" in data
        assert "is_stale" in data


class TestPriceCache:
    """Tests for price cache."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        cache = PriceCache(ttl_seconds=10)
        price_data = PriceData(
            price=Decimal("2500"),
            currency_pair="ETH/USD",
            source=PriceSource.COINGECKO,
            timestamp=datetime.utcnow(),
        )

        cache.set("ETH/USD", price_data)
        cached = cache.get("ETH/USD")

        assert cached is not None
        assert cached.price == Decimal("2500")

    def test_cache_expiry(self):
        """Test cache TTL expiry."""
        cache = PriceCache(ttl_seconds=0.1)  # 100ms TTL
        price_data = PriceData(
            price=Decimal("2500"),
            currency_pair="ETH/USD",
            source=PriceSource.COINGECKO,
            timestamp=datetime.utcnow(),
        )

        cache.set("ETH/USD", price_data)
        assert cache.get("ETH/USD") is not None

        time.sleep(0.2)
        assert cache.get("ETH/USD") is None

    def test_cache_miss(self):
        """Test cache miss."""
        cache = PriceCache()
        assert cache.get("BTC/USD") is None

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = PriceCache()
        cache.set("ETH/USD", PriceData(
            price=Decimal("2500"),
            currency_pair="ETH/USD",
            source=PriceSource.FALLBACK,
            timestamp=datetime.utcnow(),
        ))
        cache.set("BTC/USD", PriceData(
            price=Decimal("40000"),
            currency_pair="BTC/USD",
            source=PriceSource.FALLBACK,
            timestamp=datetime.utcnow(),
        ))

        cache.clear()

        assert cache.get("ETH/USD") is None
        assert cache.get("BTC/USD") is None


class TestFallbackPriceOracle:
    """Tests for fallback price oracle."""

    def test_fallback_eth_price(self):
        """Test ETH fallback price."""
        oracle = FallbackPriceOracle()
        price_data = oracle.get_price("ETH", "USD")

        assert price_data is not None
        assert price_data.price == Decimal("2000")
        assert price_data.source == PriceSource.FALLBACK
        assert price_data.confidence == 0.5

    def test_fallback_btc_price(self):
        """Test BTC fallback price."""
        oracle = FallbackPriceOracle()
        price_data = oracle.get_price("BTC", "USD")

        assert price_data is not None
        assert price_data.price == Decimal("40000")

    def test_fallback_stablecoin(self):
        """Test stablecoin fallback prices."""
        oracle = FallbackPriceOracle()

        usdc = oracle.get_price("USDC", "USD")
        usdt = oracle.get_price("USDT", "USD")
        dai = oracle.get_price("DAI", "USD")

        assert usdc.price == Decimal("1")
        assert usdt.price == Decimal("1")
        assert dai.price == Decimal("1")

    def test_fallback_unknown_currency(self):
        """Test unknown currency returns None."""
        oracle = FallbackPriceOracle()
        price_data = oracle.get_price("UNKNOWN", "USD")

        assert price_data is None

    def test_fallback_always_available(self):
        """Test fallback is always available."""
        oracle = FallbackPriceOracle()
        assert oracle.is_available() is True


class TestCoinGeckoOracle:
    """Tests for CoinGecko oracle (with mocking)."""

    @patch("rra.oracles.price_oracle.requests.get")
    def test_coingecko_eth_price(self, mock_get):
        """Test fetching ETH price from CoinGecko."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ethereum": {
                "usd": 2500.50,
                "last_updated_at": int(time.time()),
            }
        }
        mock_get.return_value = mock_response

        oracle = CoinGeckoOracle(timeout=5)
        price_data = oracle.get_price("ETH", "USD")

        assert price_data is not None
        assert price_data.price == Decimal("2500.50")
        assert price_data.source == PriceSource.COINGECKO
        assert price_data.confidence == 0.95

    @patch("rra.oracles.price_oracle.requests.get")
    def test_coingecko_api_error(self, mock_get):
        """Test handling API errors."""
        mock_get.side_effect = Exception("API Error")

        oracle = CoinGeckoOracle()
        price_data = oracle.get_price("ETH", "USD")

        assert price_data is None

    @patch("rra.oracles.price_oracle.requests.get")
    def test_coingecko_unknown_coin(self, mock_get):
        """Test unknown coin handling."""
        oracle = CoinGeckoOracle()
        price_data = oracle.get_price("UNKNOWN_COIN", "USD")

        assert price_data is None
        mock_get.assert_not_called()  # Should fail before API call


class TestChainlinkOracle:
    """Tests for Chainlink oracle (with mocking)."""

    def test_chainlink_no_provider(self):
        """Test Chainlink without web3 provider."""
        oracle = ChainlinkOracle(web3_provider_url=None)

        assert oracle.is_available() is False
        assert oracle.get_price("ETH", "USD") is None

    @patch("rra.oracles.price_oracle.Web3")
    def test_chainlink_connection_failure(self, mock_web3_class):
        """Test Chainlink connection failure."""
        mock_web3 = MagicMock()
        mock_web3.is_connected.return_value = False
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider = MagicMock()

        oracle = ChainlinkOracle(web3_provider_url="http://localhost:8545")

        assert oracle.is_available() is False


class TestAggregatedPriceOracle:
    """Tests for aggregated price oracle."""

    def test_aggregated_fallback_only(self):
        """Test aggregated oracle with fallback only."""
        oracle = AggregatedPriceOracle(
            enable_chainlink=False,
            enable_coingecko=False,
        )

        price_data = oracle.get_price("ETH", "USD")

        assert price_data is not None
        assert price_data.price == Decimal("2000")
        assert price_data.source == PriceSource.FALLBACK

    def test_aggregated_caching(self):
        """Test that results are cached."""
        oracle = AggregatedPriceOracle(
            cache_ttl_seconds=60,
            enable_chainlink=False,
            enable_coingecko=False,
        )

        # First call
        price_data1 = oracle.get_price("ETH", "USD")
        assert price_data1.source == PriceSource.FALLBACK

        # Second call should be from cache
        price_data2 = oracle.get_price("ETH", "USD")
        assert price_data2.source == PriceSource.CACHE

    def test_aggregated_skip_cache(self):
        """Test skipping cache."""
        oracle = AggregatedPriceOracle(
            cache_ttl_seconds=60,
            enable_chainlink=False,
            enable_coingecko=False,
        )

        # Populate cache
        oracle.get_price("ETH", "USD")

        # Skip cache
        price_data = oracle.get_price("ETH", "USD", skip_cache=True)
        assert price_data.source == PriceSource.FALLBACK

    def test_aggregated_usd_value(self):
        """Test USD value conversion."""
        oracle = AggregatedPriceOracle(
            enable_chainlink=False,
            enable_coingecko=False,
        )

        usd_value, price_data = oracle.get_usd_value(Decimal("1.5"), "ETH")

        # 1.5 ETH * $2000 = $3000
        assert usd_value == Decimal("3000")

    def test_aggregated_stablecoin_conversion(self):
        """Test stablecoin 1:1 conversion."""
        oracle = AggregatedPriceOracle(
            enable_chainlink=False,
            enable_coingecko=False,
        )

        usd_value, price_data = oracle.get_usd_value(Decimal("100"), "USDC")

        assert usd_value == Decimal("100")
        assert price_data.price == Decimal("1")

    def test_get_available_sources(self):
        """Test getting source status."""
        oracle = AggregatedPriceOracle(
            enable_chainlink=False,
            enable_coingecko=True,
        )

        sources = oracle.get_available_sources()

        assert len(sources) >= 2  # CoinGecko + Fallback
        source_names = [s["name"] for s in sources]
        assert "CoinGeckoOracle" in source_names
        assert "FallbackPriceOracle" in source_names


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_eth_usd_price(self):
        """Test getting ETH/USD price."""
        with patch("rra.oracles.price_oracle._price_oracle", None):
            price = get_eth_usd_price()

            # Should get fallback price
            assert price == Decimal("2000")

    def test_convert_to_usd(self):
        """Test USD conversion."""
        with patch("rra.oracles.price_oracle._price_oracle", None):
            usd = convert_to_usd(Decimal("2"), "ETH")

            # 2 ETH * $2000 = $4000
            assert usd == Decimal("4000")


class TestTransactionSafeguardsIntegration:
    """Test integration with transaction safeguards."""

    def test_safeguards_uses_oracle(self):
        """Test that safeguards uses price oracle."""
        from rra.transaction.safeguards import TransactionSafeguards

        safeguards = TransactionSafeguards(enable_live_prices=False)
        rate, source = safeguards.get_currency_rate("ETH")

        # Without live prices, should use fallback
        assert rate == 2000
        assert "fallback" in source

    def test_safeguards_stablecoin_rate(self):
        """Test stablecoin rates in safeguards."""
        from rra.transaction.safeguards import TransactionSafeguards

        safeguards = TransactionSafeguards(enable_live_prices=False)

        usdc_rate, _ = safeguards.get_currency_rate("USDC")
        usdt_rate, _ = safeguards.get_currency_rate("USDT")

        assert usdc_rate == 1
        assert usdt_rate == 1

    def test_safeguards_custom_rate_override(self):
        """Test custom rate override."""
        from rra.transaction.safeguards import TransactionSafeguards

        safeguards = TransactionSafeguards(
            custom_rates={"ETH": 3000},
            enable_live_prices=True,
        )

        rate, source = safeguards.get_currency_rate("ETH")

        assert rate == 3000
        assert source == "custom"

    def test_safeguards_price_validation_warning(self):
        """Test price validation includes oracle warnings."""
        from rra.transaction.safeguards import TransactionSafeguards

        safeguards = TransactionSafeguards(enable_live_prices=False)
        result = safeguards.validate_price("0.5 ETH")

        # Should have warning about fallback prices
        assert result.is_valid
        assert any("fallback" in w.lower() for w in result.warnings)
