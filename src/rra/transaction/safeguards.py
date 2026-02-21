# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Transaction Safeguards for UI/UX Protection.

Prevents accidental transactions through:
- Multiple confirmation levels based on transaction value
- Price sanity checks and warnings
- Clear display formatting
- Undo/cooling-off periods
- Rate limiting

Addresses:
- Confusing menu navigation
- Accidental clicks
- Price display ambiguity
- Currency confusion
"""

import logging
import re
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SafeguardLevel(str, Enum):
    """Transaction safeguard levels based on risk."""

    LOW = "low"  # Small transactions, quick confirm
    MEDIUM = "medium"  # Standard transactions, single confirm
    HIGH = "high"  # Large transactions, double confirm
    CRITICAL = "critical"  # Very large, requires explicit amount typing


@dataclass
class PriceValidation:
    """
    Price validation result with warnings and display formatting.
    """

    is_valid: bool
    normalized_price: Decimal
    currency: str
    display_string: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    safeguard_level: SafeguardLevel = SafeguardLevel.MEDIUM
    requires_explicit_confirmation: bool = False
    confirmation_prompt: str = ""

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


class TransactionSafeguards:
    """
    Manager for transaction UI/UX safeguards.

    Provides:
    - Price normalization and display
    - Sanity checking with warnings
    - Safeguard level determination
    - Confirmation prompt generation
    - Rate limiting
    - Live price feeds via oracle integration (H-002 fix)
    """

    # Price thresholds for safeguard levels (in USD equivalent)
    LOW_THRESHOLD = Decimal("50")
    MEDIUM_THRESHOLD = Decimal("500")
    HIGH_THRESHOLD = Decimal("5000")

    # Stablecoin rates (always 1:1 with USD)
    STABLECOIN_RATES = {
        "USDC": 1,
        "USDT": 1,
        "DAI": 1,
        "USD": 1,
    }

    # Minimum and maximum sane prices
    MIN_SANE_PRICE = Decimal("0.0001")
    MAX_SANE_PRICE = Decimal("1000000")

    # Rate limiting: max transactions per hour
    MAX_TRANSACTIONS_PER_HOUR = 10

    def __init__(
        self,
        custom_rates: Optional[Dict[str, float]] = None,
        enable_rate_limiting: bool = True,
        enable_live_prices: bool = True,
    ):
        """
        Initialize safeguards.

        Args:
            custom_rates: Custom currency exchange rates (override oracle)
            enable_rate_limiting: Enable transaction rate limiting
            enable_live_prices: Use live price oracle (set False for testing)
        """
        self.custom_rates = custom_rates or {}
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_live_prices = enable_live_prices
        self.transaction_timestamps: Dict[str, List[datetime]] = {}

        # Lazy-loaded price oracle
        self._price_oracle = None

    @property
    def price_oracle(self):
        """Lazy-load price oracle to avoid import issues."""
        if self._price_oracle is None and self.enable_live_prices:
            try:
                from rra.oracles.price_oracle import get_price_oracle

                self._price_oracle = get_price_oracle()
                logger.info("Price oracle initialized for transaction safeguards")
            except ImportError:
                logger.warning(
                    "Price oracle module not available. Using fallback rates."
                )
            except Exception as e:
                logger.warning(f"Failed to initialize price oracle: {e}")
        return self._price_oracle

    def get_currency_rate(self, currency: str) -> Tuple[float, str]:
        """
        Get USD exchange rate for a currency.

        Uses oracle for live prices, falls back to stablecoins/custom rates.

        Args:
            currency: Currency code (e.g., "ETH")

        Returns:
            Tuple of (rate, source description)
        """
        currency = currency.upper()

        # Check custom rates first (user overrides)
        if currency in self.custom_rates:
            return self.custom_rates[currency], "custom"

        # Stablecoins are always 1:1
        if currency in self.STABLECOIN_RATES:
            return self.STABLECOIN_RATES[currency], "stablecoin"

        # Try live oracle
        if self.price_oracle is not None:
            try:
                price_data = self.price_oracle.get_price(currency, "USD")
                if price_data is not None:
                    rate = float(price_data.price)
                    source = f"{price_data.source.value}"
                    if price_data.is_stale:
                        source += " (stale)"
                    logger.debug(
                        f"Got {currency}/USD rate {rate} from {source}"
                    )
                    return rate, source
            except Exception as e:
                logger.warning(f"Oracle price fetch failed for {currency}: {e}")

        # Final fallback: conservative estimate with warning
        fallback_rates = {
            "ETH": 2000,
            "BTC": 40000,
            "LINK": 15,
            "MATIC": 1,
        }

        if currency in fallback_rates:
            logger.warning(
                f"Using hardcoded fallback rate for {currency}. "
                "Configure RRA_WEB3_PROVIDER_URL for live prices."
            )
            return fallback_rates[currency], "fallback (hardcoded)"

        # Unknown currency
        logger.warning(f"Unknown currency {currency}, assuming rate of 1")
        return 1.0, "unknown"

    def validate_price(
        self,
        price_str: str,
        floor_price: Optional[str] = None,
        target_price: Optional[str] = None,
        context: Optional[str] = None,
    ) -> PriceValidation:
        """
        Validate and analyze a price string.

        Args:
            price_str: Price to validate (e.g., "0.5 ETH")
            floor_price: Optional floor price for bounds check
            target_price: Optional target price for comparison
            context: Optional context for better error messages

        Returns:
            PriceValidation with warnings, errors, and safeguard level
        """
        warnings = []
        errors = []

        # Parse price
        parsed = self._parse_price(price_str)
        if not parsed:
            return PriceValidation(
                is_valid=False,
                normalized_price=0,
                currency="UNKNOWN",
                display_string="Invalid price",
                errors=[f"Cannot parse price: '{price_str}'"],
                safeguard_level=SafeguardLevel.CRITICAL,
            )

        amount, currency = parsed
        currency = currency.upper()

        # Normalize currency
        if currency == "$":
            currency = "USD"
        elif currency in ["ETHER", "WEI"]:
            if currency == "WEI":
                amount = amount / 1e18
            currency = "ETH"

        # Check currency rate and source
        rate, rate_source = self.get_currency_rate(currency)
        if rate_source == "unknown":
            warnings.append(f"Unknown currency '{currency}'. Proceed with caution.")
        elif rate_source.startswith("fallback"):
            warnings.append(
                f"Using fallback price for {currency}. "
                "Live price data unavailable."
            )
        elif "stale" in rate_source:
            warnings.append(f"Price data for {currency} may be outdated.")

        # Sanity checks
        if amount <= 0:
            errors.append("Price must be positive")
        elif amount < self.MIN_SANE_PRICE:
            warnings.append(f"Price {amount} is unusually low. Verify intent.")
        elif amount > self.MAX_SANE_PRICE:
            errors.append(f"Price {amount} exceeds maximum allowed ({self.MAX_SANE_PRICE})")

        # Check against floor price
        if floor_price:
            floor_parsed = self._parse_price(floor_price)
            if floor_parsed:
                floor_amount, floor_currency = floor_parsed
                floor_usd = self._to_usd(floor_amount, floor_currency)
                price_usd = self._to_usd(amount, currency)

                if price_usd < floor_usd:
                    errors.append(
                        f"Price ({amount} {currency}) is below floor price "
                        f"({floor_amount} {floor_currency})"
                    )

        # Check against target price
        if target_price:
            target_parsed = self._parse_price(target_price)
            if target_parsed:
                target_amount, _ = target_parsed
                if amount < target_amount:
                    warnings.append(
                        f"Price is {((target_amount - amount) / target_amount * 100):.1f}% "
                        f"below target price"
                    )
                elif amount > target_amount * 2:
                    warnings.append(
                        "Price is more than 2x the target price. Verify this is correct."
                    )

        # Determine safeguard level
        usd_value = self._to_usd(amount, currency)
        safeguard_level = self._determine_safeguard_level(usd_value)

        # Force at minimum MEDIUM safeguard level when using fallback rates
        if "fallback" in rate_source and safeguard_level == SafeguardLevel.LOW:
            safeguard_level = SafeguardLevel.MEDIUM

        # Generate display string
        display_string = self._format_display(amount, currency, usd_value)

        # Determine if explicit confirmation needed
        requires_explicit = safeguard_level in [SafeguardLevel.HIGH, SafeguardLevel.CRITICAL]
        if errors:
            requires_explicit = True

        # Generate confirmation prompt
        confirmation_prompt = self._generate_confirmation_prompt(
            amount, currency, safeguard_level, warnings, context
        )

        return PriceValidation(
            is_valid=len(errors) == 0,
            normalized_price=amount,
            currency=currency,
            display_string=display_string,
            warnings=warnings,
            errors=errors,
            safeguard_level=safeguard_level,
            requires_explicit_confirmation=requires_explicit,
            confirmation_prompt=confirmation_prompt,
        )

    def check_rate_limit(self, buyer_id: str) -> Tuple[bool, str]:
        """
        Check if transaction rate limit is exceeded for a specific buyer.

        Args:
            buyer_id: Buyer identifier

        Returns:
            Tuple of (allowed, message)
        """
        if not self.enable_rate_limiting:
            return True, ""

        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        # Get or create per-buyer timestamp list
        if buyer_id not in self.transaction_timestamps:
            self.transaction_timestamps[buyer_id] = []

        # Cleanup old timestamps for this buyer
        self.transaction_timestamps[buyer_id] = [
            ts for ts in self.transaction_timestamps[buyer_id] if ts > hour_ago
        ]

        if len(self.transaction_timestamps[buyer_id]) >= self.MAX_TRANSACTIONS_PER_HOUR:
            oldest = min(self.transaction_timestamps[buyer_id])
            wait_time = (oldest + timedelta(hours=1)) - now
            return False, (
                f"Rate limit exceeded. Maximum {self.MAX_TRANSACTIONS_PER_HOUR} "
                f"transactions per hour. Try again in {int(wait_time.total_seconds())} seconds."
            )

        return True, ""

    def record_transaction(self, buyer_id: str) -> None:
        """Record a transaction for rate limiting.

        Args:
            buyer_id: Buyer identifier
        """
        if buyer_id not in self.transaction_timestamps:
            self.transaction_timestamps[buyer_id] = []
        self.transaction_timestamps[buyer_id].append(datetime.utcnow())

    def format_confirmation_screen(
        self, transaction_data: Dict[str, Any], time_remaining: int
    ) -> str:
        """
        Generate a formatted confirmation screen.

        Args:
            transaction_data: Transaction details
            time_remaining: Seconds remaining before timeout

        Returns:
            Formatted confirmation screen string
        """
        repo = transaction_data.get("repo_url", "Unknown")
        license_model = transaction_data.get("license_model", "Unknown")
        price = transaction_data.get("price", "Unknown")
        warnings = transaction_data.get("warnings", [])

        # Format time
        minutes = time_remaining // 60
        seconds = time_remaining % 60
        time_str = f"{minutes}:{seconds:02d}"

        lines = [
            "=" * 50,
            "           TRANSACTION CONFIRMATION",
            "=" * 50,
            "",
            f"  Repository: {repo}",
            f"  License:    {license_model}",
            "",
            "-" * 50,
            f"  TOTAL PRICE: {price}",
            "-" * 50,
            "",
        ]

        if warnings:
            lines.append("  WARNINGS:")
            for w in warnings:
                lines.append(f"    ! {w}")
            lines.append("")

        lines.extend(
            [
                f"  Time remaining: {time_str}",
                "",
                "  This transaction is FINAL and cannot be undone.",
                "",
                "=" * 50,
                "  Type 'CONFIRM' to proceed",
                "  Type 'CANCEL' to abort",
                "=" * 50,
            ]
        )

        return "\n".join(lines)

    def _parse_price(self, price_str: str) -> Optional[Tuple[Decimal, str]]:
        """Parse a price string into (amount, currency) using Decimal for precision."""
        if not price_str:
            return None

        price_str = price_str.strip()

        # Handle formats: "0.5 ETH", "$100", "100 USD", "0.5ETH"
        patterns = [
            r"^([\d,]+\.?\d*)\s*([A-Za-z$]+)$",  # 0.5 ETH, 100USD
            r"^([A-Za-z$]+)\s*([\d,]+\.?\d*)$",  # $100, ETH 0.5
        ]

        for pattern in patterns:
            match = re.match(pattern, price_str)
            if match:
                groups = match.groups()
                # Determine which group is the number
                if groups[0].replace(",", "").replace(".", "").isdigit():
                    amount_str = groups[0].replace(",", "")
                    currency = groups[1]
                else:
                    amount_str = groups[1].replace(",", "")
                    currency = groups[0]

                try:
                    amount = Decimal(str(amount_str))
                    return (amount, currency)
                except Exception:
                    continue

        return None

    def _to_usd(self, amount, currency: str) -> Decimal:
        """
        Convert amount to USD equivalent using live oracle prices.

        Args:
            amount: Amount in source currency (Decimal or float)
            currency: Source currency code

        Returns:
            USD equivalent value as Decimal
        """
        currency = currency.upper()
        rate, source = self.get_currency_rate(currency)
        return Decimal(str(amount)) * Decimal(str(rate))

    def _determine_safeguard_level(self, usd_value: Decimal) -> SafeguardLevel:
        """Determine safeguard level based on USD value."""
        if usd_value < self.LOW_THRESHOLD:
            return SafeguardLevel.LOW
        elif usd_value < self.MEDIUM_THRESHOLD:
            return SafeguardLevel.MEDIUM
        elif usd_value < self.HIGH_THRESHOLD:
            return SafeguardLevel.HIGH
        else:
            return SafeguardLevel.CRITICAL

    def _format_display(self, amount: Decimal, currency: str, usd_value: Decimal) -> str:
        """Format price for clear display."""
        # Format amount based on currency
        if currency in ["ETH"]:
            formatted = f"{amount:.4f} {currency}"
        elif currency in ["USD", "USDC", "USDT", "DAI"]:
            formatted = f"${amount:,.2f}"
            if currency != "USD":
                formatted += f" ({currency})"
        else:
            formatted = f"{amount} {currency}"

        # Add USD equivalent for non-USD currencies
        if currency not in ["USD", "USDC", "USDT", "DAI"]:
            formatted += f" (~${usd_value:,.2f} USD)"

        return formatted

    def _generate_confirmation_prompt(
        self,
        amount: Decimal,
        currency: str,
        level: SafeguardLevel,
        warnings: List[str],
        context: Optional[str],
    ) -> str:
        """Generate appropriate confirmation prompt."""
        base = f"You are about to pay {amount} {currency}"

        if context:
            base += f" for {context}"

        base += "."

        if warnings:
            base += "\n\nWarnings:\n" + "\n".join(f"  - {w}" for w in warnings)

        if level == SafeguardLevel.LOW:
            base += "\n\nClick CONFIRM to proceed."
        elif level == SafeguardLevel.MEDIUM:
            base += "\n\nPlease review and click CONFIRM to proceed."
        elif level == SafeguardLevel.HIGH:
            base += "\n\nThis is a HIGH VALUE transaction." "\n\nType 'CONFIRM' to proceed."
        else:  # CRITICAL
            base += (
                f"\n\nThis is a VERY HIGH VALUE transaction."
                f"\n\nTo proceed, type the exact amount: '{amount} {currency}'"
            )

        return base

    def verify_explicit_confirmation(
        self, user_input: str, expected_amount: Decimal, expected_currency: str, level: SafeguardLevel
    ) -> Tuple[bool, str]:
        """
        Verify user's explicit confirmation input.

        Args:
            user_input: What the user typed
            expected_amount: Expected amount
            expected_currency: Expected currency
            level: Safeguard level

        Returns:
            Tuple of (valid, error_message)
        """
        user_input = user_input.strip().upper()

        if level in [SafeguardLevel.LOW, SafeguardLevel.MEDIUM]:
            # Simple CONFIRM check
            if user_input == "CONFIRM":
                return True, ""
            elif user_input == "CANCEL":
                return False, "Transaction cancelled by user"
            else:
                return False, "Please type 'CONFIRM' to proceed or 'CANCEL' to abort"

        elif level == SafeguardLevel.HIGH:
            # Require CONFIRM
            if user_input == "CONFIRM":
                return True, ""
            elif user_input == "CANCEL":
                return False, "Transaction cancelled by user"
            else:
                return False, "Please type 'CONFIRM' exactly to proceed"

        else:  # CRITICAL
            # Require typing the exact amount
            expected = f"{expected_amount} {expected_currency}".upper()
            if user_input == expected:
                return True, ""
            elif user_input == "CANCEL":
                return False, "Transaction cancelled by user"
            else:
                return (
                    False,
                    f"Please type the exact amount '{expected_amount} {expected_currency}' to confirm",
                )
