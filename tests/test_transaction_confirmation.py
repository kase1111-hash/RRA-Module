# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Tests for Two-Step Transaction Confirmation with Timeout.

Validates:
- Price commitment and locking
- Timeout auto-cancellation
- Multi-step confirmation
- Price validation and bounds checking
- Safeguard levels
- Audit logging
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from rra.transaction.confirmation import (
    TransactionConfirmation,
    PendingTransaction,
    PriceCommitment,
    TransactionStatus,
    CancellationReason,
)
from rra.transaction.safeguards import (
    TransactionSafeguards,
    PriceValidation,
    SafeguardLevel,
)


# ============================================================================
# Price Commitment Tests
# ============================================================================

class TestPriceCommitment:
    """Tests for PriceCommitment class."""

    def test_create_valid_price(self):
        """Test creating commitment with valid price."""
        commitment = PriceCommitment.create("0.5 ETH")

        assert commitment.amount == 0.5
        assert commitment.currency == "ETH"
        assert commitment.commitment_hash is not None
        assert len(commitment.commitment_hash) == 32

    def test_create_various_formats(self):
        """Test price parsing with various formats."""
        test_cases = [
            ("0.5 ETH", 0.5, "ETH"),
            ("100 USDC", 100, "USDC"),
            ("1.234567 eth", 1.234567, "ETH"),
            ("50.00 USD", 50.00, "USD"),
            ("0.001ETH", 0.001, "ETH"),
        ]

        for price_str, expected_amount, expected_currency in test_cases:
            commitment = PriceCommitment.create(price_str)
            assert abs(commitment.amount - expected_amount) < 0.0001
            assert commitment.currency == expected_currency

    def test_reject_negative_price(self):
        """Test that negative prices are rejected."""
        with pytest.raises(ValueError, match="Invalid price format"):
            PriceCommitment.create("-1 ETH")

    def test_reject_zero_price(self):
        """Test that zero prices are rejected."""
        with pytest.raises(ValueError, match="positive"):
            PriceCommitment.create("0 ETH")

    def test_reject_overflow_price(self):
        """Test that extremely large prices are rejected."""
        with pytest.raises(ValueError, match="maximum"):
            PriceCommitment.create("999999999999999999999 ETH")

    def test_verify_matching_price(self):
        """Test verification of matching price."""
        commitment = PriceCommitment.create("0.5 ETH")
        assert commitment.verify("0.5 ETH") is True
        assert commitment.verify("0.5000 ETH") is True

    def test_verify_non_matching_price(self):
        """Test verification of non-matching price."""
        commitment = PriceCommitment.create("0.5 ETH")
        assert commitment.verify("0.6 ETH") is False
        assert commitment.verify("0.5 USDC") is False

    def test_commitment_uniqueness(self):
        """Test that commitments are unique even for same price."""
        c1 = PriceCommitment.create("0.5 ETH")
        c2 = PriceCommitment.create("0.5 ETH")

        # Hash should be different due to nonce
        assert c1.commitment_hash != c2.commitment_hash


# ============================================================================
# Transaction Confirmation Tests
# ============================================================================

class TestTransactionConfirmation:
    """Tests for TransactionConfirmation manager."""

    @pytest.fixture
    def confirmation_manager(self):
        """Create a confirmation manager with short timeout for testing."""
        return TransactionConfirmation(
            default_timeout=5,  # 5 seconds for testing
            min_timeout=1,  # Allow 1 second minimum for testing
        )

    def test_create_pending_transaction(self, confirmation_manager):
        """Test creating a pending transaction."""
        pending = confirmation_manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        assert pending.transaction_id is not None
        assert pending.status == TransactionStatus.PENDING_CONFIRMATION
        assert pending.price_commitment.amount == 0.5
        assert pending.buyer_id == "buyer123"
        assert pending.seller_id == "seller456"
        assert pending.is_pending is True
        assert pending.is_expired is False

    def test_reject_below_floor_price(self, confirmation_manager):
        """Test that prices below floor are rejected."""
        with pytest.raises(ValueError, match="below floor"):
            confirmation_manager.create_pending_transaction(
                buyer_id="buyer123",
                seller_id="seller456",
                repo_url="https://github.com/test/repo",
                license_model="perpetual",
                agreed_price="0.2 ETH",
                floor_price="0.3 ETH",
                target_price="0.6 ETH",
            )

    def test_confirm_transaction(self, confirmation_manager):
        """Test confirming a transaction (Step 2)."""
        pending = confirmation_manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        result = confirmation_manager.confirm_transaction(pending.transaction_id)

        assert result["success"] is True
        assert result["transaction"].status == TransactionStatus.CONFIRMED
        assert result["next_step"] == "execute"

    def test_double_confirmation_mode(self):
        """Test requiring double confirmation."""
        manager = TransactionConfirmation(
            default_timeout=60,
            require_double_confirmation=True,
            min_timeout=1,
        )

        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        # First confirmation
        result1 = manager.confirm_transaction(pending.transaction_id)
        assert result1["success"] is True
        assert result1["next_step"] == "confirm_again"

        # Second confirmation
        result2 = manager.confirm_transaction(pending.transaction_id)
        assert result2["success"] is True
        assert result2["next_step"] == "execute"

    def test_cancel_transaction(self, confirmation_manager):
        """Test cancelling a transaction."""
        pending = confirmation_manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        result = confirmation_manager.cancel_transaction(pending.transaction_id)

        assert result["success"] is True

        # Verify transaction is no longer pending
        retrieved = confirmation_manager.get_pending_transaction(pending.transaction_id)
        assert retrieved is None

    def test_timeout_expiration(self, confirmation_manager):
        """Test that transactions expire after timeout."""
        pending = confirmation_manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
            timeout_seconds=1,  # 1 second timeout
        )

        # Wait for expiration
        time.sleep(1.5)

        # Try to confirm
        result = confirmation_manager.confirm_transaction(pending.transaction_id)
        assert result["success"] is False
        assert result["error_code"] == "EXPIRED"

    def test_cleanup_expired(self, confirmation_manager):
        """Test cleanup of expired transactions."""
        # Create multiple transactions with short timeout
        for i in range(3):
            confirmation_manager.create_pending_transaction(
                buyer_id=f"buyer{i}",
                seller_id="seller456",
                repo_url="https://github.com/test/repo",
                license_model="perpetual",
                agreed_price="0.5 ETH",
                floor_price="0.3 ETH",
                target_price="0.6 ETH",
                timeout_seconds=1,
            )

        assert len(confirmation_manager.pending_transactions) == 3

        # Wait for expiration
        time.sleep(1.5)

        # Cleanup
        expired_count = confirmation_manager.cleanup_expired()
        assert expired_count == 3
        assert len(confirmation_manager.pending_transactions) == 0

    def test_audit_logging(self, confirmation_manager):
        """Test that actions are logged."""
        pending = confirmation_manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        confirmation_manager.confirm_transaction(pending.transaction_id)

        logs = confirmation_manager.get_audit_log(pending.transaction_id)

        # Should have created and confirmed entries
        actions = [log["action"] for log in logs]
        assert "created" in actions
        assert "confirmed" in actions

    def test_confirm_callback(self):
        """Test that confirm callback is called."""
        callback_called = []

        def on_confirmed(tx):
            callback_called.append(tx.transaction_id)

        manager = TransactionConfirmation(
            default_timeout=60,
            on_confirmed=on_confirmed,
            min_timeout=1,
        )

        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        manager.confirm_transaction(pending.transaction_id)

        assert pending.transaction_id in callback_called

    def test_expired_callback(self):
        """Test that expired callback is called."""
        callback_called = []

        def on_expired(tx):
            callback_called.append(tx.transaction_id)

        manager = TransactionConfirmation(
            default_timeout=1,
            on_expired=on_expired,
            min_timeout=1,
        )

        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
            timeout_seconds=1,
        )

        time.sleep(1.5)
        manager.cleanup_expired()

        assert pending.transaction_id in callback_called

    def test_confirmation_display(self, confirmation_manager):
        """Test confirmation display generation."""
        pending = confirmation_manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.4 ETH",  # Below target, should warn
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        display = pending.to_confirmation_display()

        assert display["transaction_id"] == pending.transaction_id
        assert "0.4 ETH" in display["summary"]["agreed_price"]
        assert display["time_remaining_seconds"] > 0
        assert "CONFIRM" in display["confirmation_message"]

    def test_get_stats(self, confirmation_manager):
        """Test statistics gathering."""
        # Create and confirm some transactions
        for i in range(3):
            pending = confirmation_manager.create_pending_transaction(
                buyer_id=f"buyer{i}",
                seller_id="seller456",
                repo_url="https://github.com/test/repo",
                license_model="perpetual",
                agreed_price="0.5 ETH",
                floor_price="0.3 ETH",
                target_price="0.6 ETH",
            )
            if i < 2:
                confirmation_manager.confirm_transaction(pending.transaction_id)
            else:
                confirmation_manager.cancel_transaction(pending.transaction_id)

        stats = confirmation_manager.get_stats()
        assert stats["confirmed"] == 2
        assert stats["cancelled"] == 1
        assert stats["total_completed"] == 3


# ============================================================================
# Transaction Safeguards Tests
# ============================================================================

class TestTransactionSafeguards:
    """Tests for TransactionSafeguards class."""

    @pytest.fixture
    def safeguards(self):
        """Create a safeguards instance."""
        return TransactionSafeguards(enable_rate_limiting=False)

    def test_validate_valid_price(self, safeguards):
        """Test validating a valid price."""
        result = safeguards.validate_price("0.5 ETH")

        assert result.is_valid is True
        assert result.normalized_price == 0.5
        assert result.currency == "ETH"
        assert len(result.errors) == 0

    def test_validate_price_with_floor_check(self, safeguards):
        """Test price validation against floor."""
        # Price above floor - valid
        result = safeguards.validate_price(
            "0.5 ETH",
            floor_price="0.3 ETH"
        )
        assert result.is_valid is True

        # Price below floor - invalid
        result = safeguards.validate_price(
            "0.2 ETH",
            floor_price="0.3 ETH"
        )
        assert result.is_valid is False
        assert any("below floor" in e for e in result.errors)

    def test_validate_price_with_target_warning(self, safeguards):
        """Test warning when price is below target."""
        result = safeguards.validate_price(
            "0.4 ETH",
            target_price="0.6 ETH"
        )

        assert result.is_valid is True
        assert result.has_warnings is True
        assert any("below target" in w for w in result.warnings)

    def test_safeguard_levels(self, safeguards):
        """Test safeguard level determination."""
        # Low value
        result = safeguards.validate_price("0.01 ETH")  # ~$20
        assert result.safeguard_level == SafeguardLevel.LOW

        # Medium value
        result = safeguards.validate_price("0.1 ETH")  # ~$200
        assert result.safeguard_level == SafeguardLevel.MEDIUM

        # High value
        result = safeguards.validate_price("1 ETH")  # ~$2000
        assert result.safeguard_level == SafeguardLevel.HIGH

        # Critical value
        result = safeguards.validate_price("10 ETH")  # ~$20000
        assert result.safeguard_level == SafeguardLevel.CRITICAL

    def test_display_formatting(self, safeguards):
        """Test price display formatting."""
        result = safeguards.validate_price("0.5 ETH")
        assert "0.5" in result.display_string
        assert "ETH" in result.display_string
        assert "USD" in result.display_string  # Should show USD equivalent

        result = safeguards.validate_price("100 USDC")
        assert "$100" in result.display_string

    def test_rate_limiting(self):
        """Test transaction rate limiting."""
        safeguards = TransactionSafeguards(enable_rate_limiting=True)
        safeguards.MAX_TRANSACTIONS_PER_HOUR = 3

        # First 3 should be allowed
        for i in range(3):
            allowed, _ = safeguards.check_rate_limit("buyer123")
            assert allowed is True
            safeguards.record_transaction()

        # 4th should be blocked
        allowed, message = safeguards.check_rate_limit("buyer123")
        assert allowed is False
        assert "Rate limit" in message

    def test_explicit_confirmation_low_level(self, safeguards):
        """Test explicit confirmation for low safeguard level."""
        valid, msg = safeguards.verify_explicit_confirmation(
            "CONFIRM", 0.01, "ETH", SafeguardLevel.LOW
        )
        assert valid is True

        valid, msg = safeguards.verify_explicit_confirmation(
            "CANCEL", 0.01, "ETH", SafeguardLevel.LOW
        )
        assert valid is False
        assert "cancelled" in msg

    def test_explicit_confirmation_critical_level(self, safeguards):
        """Test explicit confirmation for critical safeguard level."""
        # Must type exact amount
        valid, msg = safeguards.verify_explicit_confirmation(
            "CONFIRM", 10, "ETH", SafeguardLevel.CRITICAL
        )
        assert valid is False

        valid, msg = safeguards.verify_explicit_confirmation(
            "10 ETH", 10, "ETH", SafeguardLevel.CRITICAL
        )
        assert valid is True

    def test_confirmation_screen_format(self, safeguards):
        """Test confirmation screen formatting."""
        screen = safeguards.format_confirmation_screen(
            {
                "repo_url": "https://github.com/test/repo",
                "license_model": "perpetual",
                "price": "0.5 ETH",
                "warnings": ["Price is below target"]
            },
            time_remaining=120
        )

        assert "TRANSACTION CONFIRMATION" in screen
        assert "test/repo" in screen
        assert "0.5 ETH" in screen
        assert "2:00" in screen  # 120 seconds = 2:00
        assert "CONFIRM" in screen
        assert "CANCEL" in screen
        assert "below target" in screen


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for confirmation and safeguards together."""

    def test_full_transaction_flow(self):
        """Test complete transaction flow from creation to confirmation."""
        # Setup
        safeguards = TransactionSafeguards(enable_rate_limiting=False)
        confirmed_txs = []

        def on_confirmed(tx):
            confirmed_txs.append(tx)

        manager = TransactionConfirmation(
            default_timeout=60,
            on_confirmed=on_confirmed,
            min_timeout=1,
        )

        # Step 1: Validate price
        validation = safeguards.validate_price(
            "0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH"
        )
        assert validation.is_valid

        # Step 2: Create pending transaction
        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        # Step 3: Show confirmation screen
        display = pending.to_confirmation_display()
        assert display["time_remaining_seconds"] > 0

        # Step 4: User confirms
        user_input = "CONFIRM"
        valid, _ = safeguards.verify_explicit_confirmation(
            user_input,
            pending.price_commitment.amount,
            pending.price_commitment.currency,
            validation.safeguard_level
        )
        assert valid

        # Step 5: Execute confirmation
        result = manager.confirm_transaction(pending.transaction_id)
        assert result["success"]
        assert len(confirmed_txs) == 1

    def test_timeout_prevents_stale_confirmation(self):
        """Test that timeout prevents confirming stale transactions."""
        manager = TransactionConfirmation(default_timeout=1, min_timeout=1)

        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
            timeout_seconds=1,
        )

        # Simulate delay (user takes too long)
        time.sleep(1.5)

        # Try to confirm - should fail
        result = manager.confirm_transaction(pending.transaction_id)
        assert result["success"] is False
        assert result["error_code"] == "EXPIRED"

    def test_price_manipulation_prevented(self):
        """Test that price cannot be changed after commitment."""
        manager = TransactionConfirmation(default_timeout=60, min_timeout=1)

        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        # Price is locked in commitment
        original_price = pending.price_commitment.amount

        # Even if someone tries to modify, the commitment hash would be invalid
        # (In a real system, the smart contract would verify the commitment)
        assert pending.price_commitment.verify("0.5 ETH") is True
        assert pending.price_commitment.verify("0.6 ETH") is False

        # Original price remains locked
        result = manager.confirm_transaction(pending.transaction_id)
        assert result["transaction"].price_commitment.amount == original_price


# ============================================================================
# Edge Cases and Security Tests
# ============================================================================

class TestSecurityEdgeCases:
    """Security-focused edge case tests."""

    def test_concurrent_confirmations(self):
        """Test handling of concurrent confirmation attempts."""
        import threading

        manager = TransactionConfirmation(default_timeout=60, min_timeout=1)

        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        results = []

        def confirm():
            result = manager.confirm_transaction(pending.transaction_id)
            results.append(result)

        # Start multiple confirmation threads
        threads = [threading.Thread(target=confirm) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Only one should succeed
        successes = sum(1 for r in results if r.get("success") and r.get("next_step") == "execute")
        assert successes == 1

    def test_negative_timeout_normalization(self):
        """Test that negative timeout is normalized."""
        manager = TransactionConfirmation(default_timeout=-10, min_timeout=30)

        # Should use minimum timeout (30 seconds default)
        pending = manager.create_pending_transaction(
            buyer_id="buyer123",
            seller_id="seller456",
            repo_url="https://github.com/test/repo",
            license_model="perpetual",
            agreed_price="0.5 ETH",
            floor_price="0.3 ETH",
            target_price="0.6 ETH",
        )

        # Should have minimum timeout (30 seconds)
        assert pending.time_remaining.total_seconds() >= 25  # Some tolerance

    def test_invalid_transaction_id_handling(self):
        """Test handling of invalid transaction IDs."""
        manager = TransactionConfirmation(default_timeout=60, min_timeout=1)

        result = manager.confirm_transaction("nonexistent_id")
        assert result["success"] is False
        assert result["error_code"] == "NOT_FOUND"

        result = manager.cancel_transaction("nonexistent_id")
        assert result["success"] is False

    def test_special_characters_in_price(self):
        """Test handling of special characters in price strings."""
        safeguards = TransactionSafeguards()

        # Should handle commas
        result = safeguards.validate_price("1,000 ETH")
        assert result.is_valid is True
        assert result.normalized_price == 1000

        # Should reject injection attempts
        result = safeguards.validate_price("0.5 ETH; DROP TABLE")
        assert result.is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
