"""
Integration with value-ledger for transaction and revenue tracking.

Tracks licensing deals, payments, and revenue metrics when running
in integrated mode.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
from dataclasses import dataclass, asdict

from rra.integration.config import get_integration_config


@dataclass
class Transaction:
    """Represents a licensing transaction."""
    transaction_id: str
    agent_id: str
    buyer_id: str
    repo_url: str
    price: str
    license_model: str
    timestamp: str
    status: str  # pending, confirmed, failed
    metadata: Dict[str, Any]


class LocalLedger:
    """
    Local file-based ledger (standalone fallback).

    Tracks transactions in local JSON files.
    """

    def __init__(self, agent_id: str, ledger_dir: Optional[Path] = None):
        """
        Initialize local ledger.

        Args:
            agent_id: Unique agent identifier
            ledger_dir: Directory for ledger files (default: ./ledgers)
        """
        self.agent_id = agent_id
        self.ledger_dir = ledger_dir or Path("./ledgers")
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.ledger_dir / f"{agent_id}_transactions.jsonl"

    def record_transaction(
        self,
        transaction_id: str,
        buyer_id: str,
        repo_url: str,
        price: str,
        license_model: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """Record a new transaction."""
        transaction = Transaction(
            transaction_id=transaction_id,
            agent_id=self.agent_id,
            buyer_id=buyer_id,
            repo_url=repo_url,
            price=price,
            license_model=license_model,
            timestamp=datetime.now().isoformat(),
            status="pending",
            metadata=metadata or {}
        )

        # Append to ledger
        with open(self.ledger_file, 'a') as f:
            f.write(json.dumps(asdict(transaction)) + '\n')

        return transaction

    def update_transaction_status(
        self,
        transaction_id: str,
        status: str
    ) -> None:
        """Update transaction status."""
        # Read all transactions
        transactions = self.get_transactions()

        # Update status
        for tx in transactions:
            if tx.get("transaction_id") == transaction_id:
                tx["status"] = status
                tx["updated_at"] = datetime.now().isoformat()

        # Rewrite file
        with open(self.ledger_file, 'w') as f:
            for tx in transactions:
                f.write(json.dumps(tx) + '\n')

    def get_transactions(
        self,
        limit: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve transactions."""
        if not self.ledger_file.exists():
            return []

        transactions = []
        with open(self.ledger_file, 'r') as f:
            for line in f:
                tx = json.loads(line.strip())
                if status is None or tx.get("status") == status:
                    transactions.append(tx)

        if limit:
            transactions = transactions[-limit:]

        return transactions

    def get_revenue_stats(self) -> Dict[str, Any]:
        """Calculate revenue statistics."""
        transactions = self.get_transactions(status="confirmed")

        total_revenue = 0.0
        by_model = {}

        for tx in transactions:
            # Parse price (assumes "X.XX ETH" format)
            try:
                price_str = tx.get("price", "0 ETH")
                amount = float(price_str.split()[0])
                total_revenue += amount

                model = tx.get("license_model", "unknown")
                by_model[model] = by_model.get(model, 0.0) + amount
            except Exception:
                pass

        return {
            "total_transactions": len(transactions),
            "total_revenue": total_revenue,
            "revenue_by_model": by_model,
            "agent_id": self.agent_id
        }


class ValueLedgerService:
    """
    Integration with value-ledger service for distributed transaction tracking.

    Uses value-ledger when available for cross-agent revenue analytics.
    """

    def __init__(self, agent_id: str, ledger_url: Optional[str] = None):
        """
        Initialize value-ledger service integration.

        Args:
            agent_id: Unique agent identifier
            ledger_url: URL of value-ledger service
        """
        self.agent_id = agent_id
        self.ledger_url = ledger_url or get_integration_config().value_ledger_url

        # Try to import value-ledger client
        try:
            from value_ledger import LedgerClient  # type: ignore
            self.client = LedgerClient(url=self.ledger_url, agent_id=agent_id)
            self.available = True
        except ImportError:
            self.available = False
            self._fallback = LocalLedger(agent_id)

    def record_transaction(
        self,
        transaction_id: str,
        buyer_id: str,
        repo_url: str,
        price: str,
        license_model: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        """Record transaction to value-ledger service."""
        if not self.available:
            return self._fallback.record_transaction(
                transaction_id, buyer_id, repo_url, price, license_model, metadata
            )

        try:
            result = self.client.record(
                transaction_id=transaction_id,
                buyer_id=buyer_id,
                repo_url=repo_url,
                price=price,
                license_model=license_model,
                metadata=metadata or {}
            )
            return Transaction(**result)
        except Exception as e:
            print(f"Warning: Failed to record to value-ledger: {e}")
            if not hasattr(self, '_fallback'):
                self._fallback = LocalLedger(self.agent_id)
            return self._fallback.record_transaction(
                transaction_id, buyer_id, repo_url, price, license_model, metadata
            )

    def update_transaction_status(
        self,
        transaction_id: str,
        status: str
    ) -> None:
        """Update transaction status in value-ledger."""
        if not self.available:
            self._fallback.update_transaction_status(transaction_id, status)
            return

        try:
            self.client.update_status(transaction_id, status)
        except Exception as e:
            print(f"Warning: Failed to update in value-ledger: {e}")
            if not hasattr(self, '_fallback'):
                self._fallback = LocalLedger(self.agent_id)
            self._fallback.update_transaction_status(transaction_id, status)

    def get_transactions(
        self,
        limit: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve transactions from value-ledger."""
        if not self.available:
            return self._fallback.get_transactions(limit, status)

        try:
            return self.client.query(limit=limit, status=status)
        except Exception:
            if not hasattr(self, '_fallback'):
                self._fallback = LocalLedger(self.agent_id)
            return self._fallback.get_transactions(limit, status)

    def get_revenue_stats(self) -> Dict[str, Any]:
        """Get revenue statistics from value-ledger."""
        if not self.available:
            return self._fallback.get_revenue_stats()

        try:
            return self.client.get_stats(self.agent_id)
        except Exception:
            if not hasattr(self, '_fallback'):
                self._fallback = LocalLedger(self.agent_id)
            return self._fallback.get_revenue_stats()


def get_ledger(
    agent_id: str,
    prefer_service: bool = True
):
    """
    Get appropriate ledger based on configuration.

    Args:
        agent_id: Unique agent identifier
        prefer_service: Prefer value-ledger service if available

    Returns:
        Ledger instance (ValueLedger or Local)
    """
    config = get_integration_config()

    if config.enable_value_ledger and prefer_service:
        ledger = ValueLedgerService(agent_id, config.value_ledger_url)
        if ledger.available:
            return ledger

    return LocalLedger(agent_id)
