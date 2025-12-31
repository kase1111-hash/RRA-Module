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

import re
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class SafeguardLevel(str, Enum):
    """Transaction safeguard levels based on risk."""
    LOW = "low"           # Small transactions, quick confirm
    MEDIUM = "medium"     # Standard transactions, single confirm
    HIGH = "high"         # Large transactions, double confirm
    CRITICAL = "critical" # Very large, requires explicit amount typing


@dataclass
class PriceValidation:
    """
    Price validation result with warnings and display formatting.
    """
    is_valid: bool
    normalized_price: float
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
    """

    # Price thresholds for safeguard levels (in USD equivalent)
    LOW_THRESHOLD = 50
    MEDIUM_THRESHOLD = 500
    HIGH_THRESHOLD = 5000

    # Supported currencies and their approximate USD rates
    CURRENCY_RATES = {
        "ETH": 2000,   # Approximate ETH/USD
        "USDC": 1,
        "USDT": 1,
        "DAI": 1,
        "USD": 1,
    }

    # Minimum and maximum sane prices
    MIN_SANE_PRICE = 0.0001
    MAX_SANE_PRICE = 1000000

    # Rate limiting: max transactions per hour
    MAX_TRANSACTIONS_PER_HOUR = 10

    def __init__(
        self,
        custom_rates: Optional[Dict[str, float]] = None,
        enable_rate_limiting: bool = True
    ):
        """
        Initialize safeguards.

        Args:
            custom_rates: Custom currency exchange rates
            enable_rate_limiting: Enable transaction rate limiting
        """
        self.currency_rates = {**self.CURRENCY_RATES}
        if custom_rates:
            self.currency_rates.update(custom_rates)

        self.enable_rate_limiting = enable_rate_limiting
        self.transaction_timestamps: List[datetime] = []

    def validate_price(
        self,
        price_str: str,
        floor_price: Optional[str] = None,
        target_price: Optional[str] = None,
        context: Optional[str] = None
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
                safeguard_level=SafeguardLevel.CRITICAL
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

        # Check currency is supported
        if currency not in self.currency_rates:
            warnings.append(f"Unknown currency '{currency}'. Proceed with caution.")

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
                        f"Price is more than 2x the target price. Verify this is correct."
                    )

        # Determine safeguard level
        usd_value = self._to_usd(amount, currency)
        safeguard_level = self._determine_safeguard_level(usd_value)

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
            confirmation_prompt=confirmation_prompt
        )

    def check_rate_limit(self, buyer_id: str) -> Tuple[bool, str]:
        """
        Check if transaction rate limit is exceeded.

        Args:
            buyer_id: Buyer identifier

        Returns:
            Tuple of (allowed, message)
        """
        if not self.enable_rate_limiting:
            return True, ""

        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        # Cleanup old timestamps
        self.transaction_timestamps = [
            ts for ts in self.transaction_timestamps
            if ts > hour_ago
        ]

        if len(self.transaction_timestamps) >= self.MAX_TRANSACTIONS_PER_HOUR:
            oldest = min(self.transaction_timestamps)
            wait_time = (oldest + timedelta(hours=1)) - now
            return False, (
                f"Rate limit exceeded. Maximum {self.MAX_TRANSACTIONS_PER_HOUR} "
                f"transactions per hour. Try again in {int(wait_time.total_seconds())} seconds."
            )

        return True, ""

    def record_transaction(self) -> None:
        """Record a transaction for rate limiting."""
        self.transaction_timestamps.append(datetime.utcnow())

    def format_confirmation_screen(
        self,
        transaction_data: Dict[str, Any],
        time_remaining: int
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

        lines.extend([
            f"  Time remaining: {time_str}",
            "",
            "  This transaction is FINAL and cannot be undone.",
            "",
            "=" * 50,
            "  Type 'CONFIRM' to proceed",
            "  Type 'CANCEL' to abort",
            "=" * 50,
        ])

        return "\n".join(lines)

    def _parse_price(self, price_str: str) -> Optional[Tuple[float, str]]:
        """Parse a price string into (amount, currency)."""
        if not price_str:
            return None

        price_str = price_str.strip()

        # Handle formats: "0.5 ETH", "$100", "100 USD", "0.5ETH"
        patterns = [
            r'^([\d,]+\.?\d*)\s*([A-Za-z$]+)$',  # 0.5 ETH, 100USD
            r'^([A-Za-z$]+)\s*([\d,]+\.?\d*)$',   # $100, ETH 0.5
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
                    amount = float(amount_str)
                    return (amount, currency)
                except ValueError:
                    continue

        return None

    def _to_usd(self, amount: float, currency: str) -> float:
        """Convert amount to USD equivalent."""
        currency = currency.upper()
        rate = self.currency_rates.get(currency, 1)
        return amount * rate

    def _determine_safeguard_level(self, usd_value: float) -> SafeguardLevel:
        """Determine safeguard level based on USD value."""
        if usd_value < self.LOW_THRESHOLD:
            return SafeguardLevel.LOW
        elif usd_value < self.MEDIUM_THRESHOLD:
            return SafeguardLevel.MEDIUM
        elif usd_value < self.HIGH_THRESHOLD:
            return SafeguardLevel.HIGH
        else:
            return SafeguardLevel.CRITICAL

    def _format_display(
        self,
        amount: float,
        currency: str,
        usd_value: float
    ) -> str:
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
        amount: float,
        currency: str,
        level: SafeguardLevel,
        warnings: List[str],
        context: Optional[str]
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
            base += (
                f"\n\nThis is a HIGH VALUE transaction."
                f"\n\nType 'CONFIRM' to proceed."
            )
        else:  # CRITICAL
            base += (
                f"\n\nThis is a VERY HIGH VALUE transaction."
                f"\n\nTo proceed, type the exact amount: '{amount} {currency}'"
            )

        return base

    def verify_explicit_confirmation(
        self,
        user_input: str,
        expected_amount: float,
        expected_currency: str,
        level: SafeguardLevel
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
                return False, f"Please type the exact amount '{expected_amount} {expected_currency}' to confirm"
