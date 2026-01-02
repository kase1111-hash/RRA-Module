# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Two-Step Transaction Confirmation with Timeout.

Prevents accidental transactions and price manipulation by:
1. Locking in agreed price with cryptographic commitment
2. Requiring explicit confirmation before execution
3. Auto-canceling transactions that exceed timeout
4. Validating price bounds before commitment

This addresses:
- Accidental click-to-buy scenarios
- Bait-and-switch price manipulation
- State machine soft locks (via timeout)
- TOCTOU race conditions (via commitment)

Example Flow:
    1. User agrees to price -> create_pending_transaction()
    2. System shows confirmation UI with locked price
    3. User confirms within timeout -> confirm_transaction()
    4. Transaction executes at committed price
    OR
    4. Timeout expires -> auto-cancel
"""

import os
import re
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from eth_utils import keccak


class TransactionStatus(str, Enum):
    """Transaction lifecycle states."""

    PENDING_CONFIRMATION = "pending_confirmation"  # Awaiting user confirmation
    CONFIRMED = "confirmed"  # User confirmed, ready to execute
    EXECUTED = "executed"  # Transaction completed
    CANCELLED = "cancelled"  # User cancelled
    EXPIRED = "expired"  # Auto-cancelled due to timeout
    FAILED = "failed"  # Execution failed


class CancellationReason(str, Enum):
    """Reasons for transaction cancellation."""

    USER_CANCELLED = "user_cancelled"
    TIMEOUT_EXPIRED = "timeout_expired"
    PRICE_CHANGED = "price_changed"
    VALIDATION_FAILED = "validation_failed"
    SYSTEM_ERROR = "system_error"


@dataclass
class PriceCommitment:
    """
    Cryptographic commitment to a specific price.

    Prevents price manipulation between agreement and execution.
    """

    amount: float
    currency: str
    commitment_hash: bytes
    created_at: datetime

    @classmethod
    def create(cls, price_str: str) -> "PriceCommitment":
        """
        Create a price commitment from price string.

        Args:
            price_str: Price in format "X.XX CURRENCY"

        Returns:
            PriceCommitment with hash binding
        """
        # Parse price string
        match = re.match(r"([\d.]+)\s*(\w+)", price_str.strip())
        if not match:
            raise ValueError(f"Invalid price format: {price_str}")

        amount = float(match.group(1))
        currency = match.group(2).upper()

        # Validate amount
        if amount <= 0:
            raise ValueError("Price must be positive")
        if amount > 1e18:  # Reasonable upper bound
            raise ValueError("Price exceeds maximum allowed")

        # Create commitment hash
        timestamp = datetime.utcnow()
        nonce = os.urandom(16)
        commitment_data = f"{amount}:{currency}:{timestamp.isoformat()}:{nonce.hex()}"
        commitment_hash = keccak(commitment_data.encode())

        return cls(
            amount=amount, currency=currency, commitment_hash=commitment_hash, created_at=timestamp
        )

    def verify(self, price_str: str) -> bool:
        """Verify a price matches this commitment."""
        match = re.match(r"([\d.]+)\s*(\w+)", price_str.strip())
        if not match:
            return False

        amount = float(match.group(1))
        currency = match.group(2).upper()

        # Allow small floating point tolerance
        return abs(amount - self.amount) < 0.0001 and currency == self.currency

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"


@dataclass
class PendingTransaction:
    """
    Transaction awaiting confirmation.

    Holds all details in a locked state until user confirms or timeout expires.
    """

    transaction_id: str
    buyer_id: str
    seller_id: str
    repo_url: str
    license_model: str
    price_commitment: PriceCommitment
    floor_price: float
    target_price: float
    created_at: datetime
    expires_at: datetime
    status: TransactionStatus = TransactionStatus.PENDING_CONFIRMATION
    confirmation_count: int = 0  # For multi-step confirmation
    required_confirmations: int = 1
    cancellation_reason: Optional[CancellationReason] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if transaction has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if still awaiting confirmation."""
        return self.status == TransactionStatus.PENDING_CONFIRMATION

    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining before expiry."""
        remaining = self.expires_at - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    @property
    def is_fully_confirmed(self) -> bool:
        """Check if all required confirmations received."""
        return self.confirmation_count >= self.required_confirmations

    def validate_price(self) -> Dict[str, Any]:
        """
        Validate price is within acceptable bounds.

        Returns:
            Dict with 'valid' bool and 'warnings' list
        """
        warnings = []
        valid = True

        price = self.price_commitment.amount

        # Check floor price
        if price < self.floor_price:
            valid = False
            warnings.append(f"Price {price} below floor {self.floor_price}")

        # Check target price (warning only)
        if price < self.target_price:
            warnings.append(f"Price {price} below target {self.target_price}")

        # Check for suspiciously high price
        if price > self.target_price * 10:
            warnings.append(f"Price {price} is 10x above target - verify intent")

        return {"valid": valid, "warnings": warnings}

    def to_confirmation_display(self) -> Dict[str, Any]:
        """
        Generate data for confirmation UI display.

        Returns user-friendly summary for confirmation step.
        """
        validation = self.validate_price()

        return {
            "transaction_id": self.transaction_id,
            "summary": {
                "repository": self.repo_url,
                "license_type": self.license_model,
                "agreed_price": str(self.price_commitment),
                "floor_price": f"{self.floor_price} {self.price_commitment.currency}",
                "target_price": f"{self.target_price} {self.price_commitment.currency}",
            },
            "time_remaining_seconds": int(self.time_remaining.total_seconds()),
            "time_remaining_display": self._format_time_remaining(),
            "warnings": validation["warnings"],
            "requires_attention": len(validation["warnings"]) > 0,
            "confirmation_message": self._generate_confirmation_message(),
        }

    def _format_time_remaining(self) -> str:
        """Format time remaining in human-readable format."""
        remaining = self.time_remaining
        minutes = int(remaining.total_seconds() // 60)
        seconds = int(remaining.total_seconds() % 60)

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def _generate_confirmation_message(self) -> str:
        """Generate confirmation prompt message."""
        return f"""Please confirm this transaction:

Repository: {self.repo_url}
License: {self.license_model}
Price: {self.price_commitment}

This price is LOCKED and cannot be changed.
Transaction expires in: {self._format_time_remaining()}

Type 'CONFIRM' to proceed or 'CANCEL' to abort."""


class TransactionConfirmation:
    """
    Manager for two-step transaction verification.

    Provides:
    - Pending transaction creation with price locking
    - Timeout-based auto-cancellation
    - Explicit confirmation requirement
    - Price validation and bounds checking
    - Audit trail for all actions
    """

    # Default timeout: 5 minutes
    DEFAULT_TIMEOUT_SECONDS = 300

    # Maximum timeout: 1 hour
    MAX_TIMEOUT_SECONDS = 3600

    # Minimum timeout: 30 seconds (can be overridden for testing)
    MIN_TIMEOUT_SECONDS = 30

    def __init__(
        self,
        default_timeout: int = DEFAULT_TIMEOUT_SECONDS,
        on_expired: Optional[Callable[[PendingTransaction], None]] = None,
        on_confirmed: Optional[Callable[[PendingTransaction], None]] = None,
        require_double_confirmation: bool = False,
        min_timeout: Optional[int] = None,  # Override for testing
    ):
        """
        Initialize transaction confirmation manager.

        Args:
            default_timeout: Default timeout in seconds
            on_expired: Callback when transaction expires
            on_confirmed: Callback when transaction is confirmed
            require_double_confirmation: Require 2 confirmations for execution
            min_timeout: Override minimum timeout (for testing)
        """
        self._min_timeout = min_timeout if min_timeout is not None else self.MIN_TIMEOUT_SECONDS
        self.default_timeout = min(
            max(default_timeout, self._min_timeout), self.MAX_TIMEOUT_SECONDS
        )
        self.on_expired = on_expired
        self.on_confirmed = on_confirmed
        self.require_double_confirmation = require_double_confirmation

        self.pending_transactions: Dict[str, PendingTransaction] = {}
        self.completed_transactions: Dict[str, PendingTransaction] = {}
        self.audit_log: List[Dict[str, Any]] = []

        self._lock = threading.Lock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

    def start_cleanup_daemon(self, interval_seconds: int = 10) -> None:
        """Start background thread to cleanup expired transactions."""
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, args=(interval_seconds,), daemon=True
        )
        self._cleanup_thread.start()

    def stop_cleanup_daemon(self) -> None:
        """Stop the cleanup daemon."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2)

    def _cleanup_loop(self, interval: int) -> None:
        """Background loop to cleanup expired transactions."""
        import time

        while self._running:
            self.cleanup_expired()
            time.sleep(interval)

    def create_pending_transaction(
        self,
        buyer_id: str,
        seller_id: str,
        repo_url: str,
        license_model: str,
        agreed_price: str,
        floor_price: str,
        target_price: str,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PendingTransaction:
        """
        Create a new pending transaction (Step 1).

        Locks in the agreed price and starts timeout countdown.

        Args:
            buyer_id: Buyer's identifier
            seller_id: Seller's identifier
            repo_url: Repository URL
            license_model: License type
            agreed_price: Agreed price string (e.g., "0.5 ETH")
            floor_price: Minimum acceptable price
            target_price: Target/asking price
            timeout_seconds: Custom timeout (uses default if None)
            metadata: Additional transaction metadata

        Returns:
            PendingTransaction awaiting confirmation

        Raises:
            ValueError: If price validation fails
        """
        # Parse prices
        price_commitment = PriceCommitment.create(agreed_price)

        floor_match = re.match(r"([\d.]+)", floor_price)
        target_match = re.match(r"([\d.]+)", target_price)

        floor_value = float(floor_match.group(1)) if floor_match else 0
        target_value = float(target_match.group(1)) if target_match else price_commitment.amount

        # Validate floor <= agreed price
        if price_commitment.amount < floor_value:
            raise ValueError(
                f"Agreed price {price_commitment.amount} is below floor price {floor_value}. "
                "Transaction rejected for seller protection."
            )

        # Generate transaction ID
        tx_id = keccak(
            f"{buyer_id}:{seller_id}:{repo_url}:{datetime.utcnow().isoformat()}".encode()
            + os.urandom(8)
        ).hex()[:16]

        # Calculate expiry
        timeout = timeout_seconds or self.default_timeout
        timeout = min(max(timeout, self._min_timeout), self.MAX_TIMEOUT_SECONDS)
        expires_at = datetime.utcnow() + timedelta(seconds=timeout)

        # Create pending transaction
        pending = PendingTransaction(
            transaction_id=tx_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            repo_url=repo_url,
            license_model=license_model,
            price_commitment=price_commitment,
            floor_price=floor_value,
            target_price=target_value,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            required_confirmations=2 if self.require_double_confirmation else 1,
            metadata=metadata or {},
        )

        # Validate and add warnings
        validation = pending.validate_price()
        if validation["warnings"]:
            pending.metadata["price_warnings"] = validation["warnings"]

        with self._lock:
            self.pending_transactions[tx_id] = pending

        self._log_action(
            "created",
            pending,
            {"timeout_seconds": timeout, "price_warnings": validation["warnings"]},
        )

        return pending

    def confirm_transaction(
        self, transaction_id: str, confirmation_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirm a pending transaction (Step 2).

        Args:
            transaction_id: Transaction to confirm
            confirmation_code: Optional confirmation code (for extra security)

        Returns:
            Dict with 'success', 'transaction', and optional 'message'
        """
        with self._lock:
            pending = self.pending_transactions.get(transaction_id)

            if not pending:
                return {
                    "success": False,
                    "error": "Transaction not found",
                    "error_code": "NOT_FOUND",
                }

            # Check expiry
            if pending.is_expired:
                self._expire_transaction(pending)
                return {
                    "success": False,
                    "error": "Transaction has expired",
                    "error_code": "EXPIRED",
                }

            # Check status
            if pending.status != TransactionStatus.PENDING_CONFIRMATION:
                return {
                    "success": False,
                    "error": f"Transaction is {pending.status.value}",
                    "error_code": "INVALID_STATUS",
                }

            # Increment confirmation count
            pending.confirmation_count += 1

            if pending.is_fully_confirmed:
                pending.status = TransactionStatus.CONFIRMED

                # Move to completed
                self.completed_transactions[transaction_id] = pending
                del self.pending_transactions[transaction_id]

                self._log_action("confirmed", pending)

                # Trigger callback
                if self.on_confirmed:
                    try:
                        self.on_confirmed(pending)
                    except Exception as e:
                        self._log_action("callback_error", pending, {"error": str(e)})

                return {
                    "success": True,
                    "transaction": pending,
                    "message": "Transaction confirmed and ready for execution",
                    "next_step": "execute",
                }
            else:
                # Need more confirmations
                remaining = pending.required_confirmations - pending.confirmation_count
                self._log_action("partial_confirm", pending, {"remaining": remaining})

                return {
                    "success": True,
                    "transaction": pending,
                    "message": f"Confirmation received. {remaining} more confirmation(s) required.",
                    "next_step": "confirm_again",
                }

    def cancel_transaction(
        self, transaction_id: str, reason: CancellationReason = CancellationReason.USER_CANCELLED
    ) -> Dict[str, Any]:
        """
        Cancel a pending transaction.

        Args:
            transaction_id: Transaction to cancel
            reason: Reason for cancellation

        Returns:
            Dict with 'success' and optional 'error'
        """
        with self._lock:
            pending = self.pending_transactions.get(transaction_id)

            if not pending:
                return {"success": False, "error": "Transaction not found"}

            pending.status = TransactionStatus.CANCELLED
            pending.cancellation_reason = reason

            self.completed_transactions[transaction_id] = pending
            del self.pending_transactions[transaction_id]

        self._log_action("cancelled", pending, {"reason": reason.value})

        return {"success": True, "message": "Transaction cancelled successfully"}

    def get_pending_transaction(self, transaction_id: str) -> Optional[PendingTransaction]:
        """Get a pending transaction by ID."""
        with self._lock:
            pending = self.pending_transactions.get(transaction_id)

            # Check for expiry
            if pending and pending.is_expired:
                self._expire_transaction(pending)
                return None

            return pending

    def get_all_pending(
        self, buyer_id: Optional[str] = None, seller_id: Optional[str] = None
    ) -> List[PendingTransaction]:
        """Get all pending transactions, optionally filtered."""
        with self._lock:
            # First cleanup expired
            self._cleanup_expired_internal()

            pending = list(self.pending_transactions.values())

        if buyer_id:
            pending = [p for p in pending if p.buyer_id == buyer_id]
        if seller_id:
            pending = [p for p in pending if p.seller_id == seller_id]

        return pending

    def cleanup_expired(self) -> int:
        """
        Cleanup all expired transactions.

        Returns:
            Number of transactions expired
        """
        with self._lock:
            return self._cleanup_expired_internal()

    def _cleanup_expired_internal(self) -> int:
        """Internal cleanup (must hold lock)."""
        expired_ids = [tx_id for tx_id, tx in self.pending_transactions.items() if tx.is_expired]

        for tx_id in expired_ids:
            self._expire_transaction(self.pending_transactions[tx_id])

        return len(expired_ids)

    def _expire_transaction(self, pending: PendingTransaction) -> None:
        """Mark transaction as expired (must hold lock)."""
        pending.status = TransactionStatus.EXPIRED
        pending.cancellation_reason = CancellationReason.TIMEOUT_EXPIRED

        tx_id = pending.transaction_id
        self.completed_transactions[tx_id] = pending

        if tx_id in self.pending_transactions:
            del self.pending_transactions[tx_id]

        self._log_action("expired", pending)

        # Trigger callback
        if self.on_expired:
            try:
                self.on_expired(pending)
            except Exception as e:
                self._log_action("callback_error", pending, {"error": str(e)})

    def _log_action(
        self, action: str, transaction: PendingTransaction, extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an action to the audit trail."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "transaction_id": transaction.transaction_id,
            "buyer_id": transaction.buyer_id,
            "seller_id": transaction.seller_id,
            "price": str(transaction.price_commitment),
            "status": transaction.status.value,
        }

        if extra:
            entry.update(extra)

        self.audit_log.append(entry)

    def get_audit_log(
        self, transaction_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        logs = self.audit_log

        if transaction_id:
            logs = [log for log in logs if log.get("transaction_id") == transaction_id]

        return logs[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get confirmation system statistics."""
        with self._lock:
            pending_count = len(self.pending_transactions)
            completed = list(self.completed_transactions.values())

        confirmed = sum(1 for t in completed if t.status == TransactionStatus.CONFIRMED)
        cancelled = sum(1 for t in completed if t.status == TransactionStatus.CANCELLED)
        expired = sum(1 for t in completed if t.status == TransactionStatus.EXPIRED)

        return {
            "pending": pending_count,
            "confirmed": confirmed,
            "cancelled": cancelled,
            "expired": expired,
            "total_completed": len(completed),
            "confirmation_rate": confirmed / len(completed) if completed else 0,
            "expiry_rate": expired / len(completed) if completed else 0,
        }
