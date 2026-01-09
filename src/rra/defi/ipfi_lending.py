# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
IPFi (Intellectual Property Finance) Lending Integration.

Enables license NFT holders to use their licenses as collateral
for loans, similar to NFTfi but specialized for IP assets.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import secrets


class LoanStatus(Enum):
    """Status of a loan."""

    PENDING = "pending"
    ACTIVE = "active"
    REPAID = "repaid"
    DEFAULTED = "defaulted"
    LIQUIDATED = "liquidated"
    CANCELLED = "cancelled"


class CollateralType(Enum):
    """Types of collateral accepted."""

    LICENSE_NFT = "license_nft"
    IP_ASSET = "ip_asset"
    REVENUE_STREAM = "revenue_stream"


@dataclass
class LoanTerms:
    """Terms for a loan offer."""

    principal: float  # Loan amount in ETH
    interest_rate: float  # Annual interest rate (0.05 = 5%)
    duration_days: int  # Loan duration
    collateral_value: float  # Required collateral value
    ltv_ratio: float = 0.5  # Loan-to-value ratio (50% default)
    liquidation_threshold: float = 0.8  # Liquidate if LTV exceeds this

    @property
    def total_repayment(self) -> float:
        """Calculate total repayment amount."""
        interest = self.principal * self.interest_rate * (self.duration_days / 365)
        return self.principal + interest

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principal": self.principal,
            "interest_rate": self.interest_rate,
            "duration_days": self.duration_days,
            "collateral_value": self.collateral_value,
            "ltv_ratio": self.ltv_ratio,
            "liquidation_threshold": self.liquidation_threshold,
            "total_repayment": self.total_repayment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoanTerms":
        return cls(
            principal=data["principal"],
            interest_rate=data["interest_rate"],
            duration_days=data["duration_days"],
            collateral_value=data["collateral_value"],
            ltv_ratio=data.get("ltv_ratio", 0.5),
            liquidation_threshold=data.get("liquidation_threshold", 0.8),
        )


@dataclass
class Collateral:
    """Collateral for a loan."""

    collateral_id: str
    collateral_type: CollateralType
    asset_id: str  # License ID or IP Asset ID
    owner_address: str
    estimated_value: float
    locked: bool = False
    locked_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collateral_id": self.collateral_id,
            "collateral_type": self.collateral_type.value,
            "asset_id": self.asset_id,
            "owner_address": self.owner_address,
            "estimated_value": self.estimated_value,
            "locked": self.locked,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Collateral":
        return cls(
            collateral_id=data["collateral_id"],
            collateral_type=CollateralType(data["collateral_type"]),
            asset_id=data["asset_id"],
            owner_address=data["owner_address"],
            estimated_value=data["estimated_value"],
            locked=data.get("locked", False),
            locked_at=datetime.fromisoformat(data["locked_at"]) if data.get("locked_at") else None,
        )


@dataclass
class Loan:
    """Represents an active or historical loan."""

    loan_id: str
    borrower_address: str
    lender_address: str
    collateral: Collateral
    terms: LoanTerms
    status: LoanStatus
    created_at: datetime
    funded_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    repaid_at: Optional[datetime] = None
    amount_repaid: float = 0.0

    @property
    def is_overdue(self) -> bool:
        """Check if loan is past due date."""
        if self.status != LoanStatus.ACTIVE or not self.due_date:
            return False
        return datetime.now() > self.due_date

    @property
    def days_until_due(self) -> Optional[int]:
        """Days remaining until due date."""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.now()
        return max(0, delta.days)

    @property
    def current_ltv(self) -> float:
        """Current loan-to-value ratio."""
        if self.collateral.estimated_value == 0:
            return float("inf")
        outstanding = self.terms.total_repayment - self.amount_repaid
        return outstanding / self.collateral.estimated_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "borrower_address": self.borrower_address,
            "lender_address": self.lender_address,
            "collateral": self.collateral.to_dict(),
            "terms": self.terms.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "funded_at": self.funded_at.isoformat() if self.funded_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "repaid_at": self.repaid_at.isoformat() if self.repaid_at else None,
            "amount_repaid": self.amount_repaid,
            "is_overdue": self.is_overdue,
            "days_until_due": self.days_until_due,
            "current_ltv": self.current_ltv,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Loan":
        return cls(
            loan_id=data["loan_id"],
            borrower_address=data["borrower_address"],
            lender_address=data["lender_address"],
            collateral=Collateral.from_dict(data["collateral"]),
            terms=LoanTerms.from_dict(data["terms"]),
            status=LoanStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            funded_at=datetime.fromisoformat(data["funded_at"]) if data.get("funded_at") else None,
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            repaid_at=datetime.fromisoformat(data["repaid_at"]) if data.get("repaid_at") else None,
            amount_repaid=data.get("amount_repaid", 0.0),
        )


@dataclass
class LoanOffer:
    """A loan offer from a lender."""

    offer_id: str
    lender_address: str
    terms: LoanTerms
    accepted_collateral_types: List[CollateralType]
    min_collateral_value: float
    max_collateral_value: float
    created_at: datetime
    expires_at: datetime
    active: bool = True

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "lender_address": self.lender_address,
            "terms": self.terms.to_dict(),
            "accepted_collateral_types": [t.value for t in self.accepted_collateral_types],
            "min_collateral_value": self.min_collateral_value,
            "max_collateral_value": self.max_collateral_value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "active": self.active,
            "is_expired": self.is_expired,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoanOffer":
        return cls(
            offer_id=data["offer_id"],
            lender_address=data["lender_address"],
            terms=LoanTerms.from_dict(data["terms"]),
            accepted_collateral_types=[
                CollateralType(t) for t in data["accepted_collateral_types"]
            ],
            min_collateral_value=data["min_collateral_value"],
            max_collateral_value=data["max_collateral_value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            active=data.get("active", True),
        )


class CollateralValuator:
    """Estimates value of IP collateral."""

    def __init__(self):
        self.value_cache: Dict[str, tuple[float, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)

    def estimate_license_value(
        self,
        license_id: str,
        original_price: float,
        license_age_days: int,
        revenue_generated: float = 0.0,
        reputation_score: float = 0.5,
    ) -> float:
        """
        Estimate the current value of a license.

        Factors:
        - Original purchase price
        - Age (depreciation)
        - Revenue generated (appreciation)
        - Reputation score
        """
        # Check cache
        if license_id in self.value_cache:
            value, cached_at = self.value_cache[license_id]
            if datetime.now() - cached_at < self.cache_ttl:
                return value

        # Base value is original price
        base_value = original_price

        # Age depreciation (lose 10% per year, min 50%)
        depreciation = max(0.5, 1.0 - (license_age_days / 365) * 0.1)
        value = base_value * depreciation

        # Revenue appreciation (each ETH of revenue adds 10% value)
        revenue_bonus = 1.0 + (revenue_generated * 0.1)
        value *= revenue_bonus

        # Reputation multiplier (0.5-1.0 score maps to 0.8-1.2 multiplier)
        reputation_multiplier = 0.8 + (reputation_score * 0.4)
        value *= reputation_multiplier

        # Cache result
        self.value_cache[license_id] = (value, datetime.now())

        return value

    def estimate_ip_asset_value(
        self,
        ip_asset_id: str,
        total_licenses_sold: int,
        total_revenue: float,
        fork_count: int = 0,
        star_count: int = 0,
    ) -> float:
        """
        Estimate value of an IP asset (repository).

        Factors:
        - Total licenses sold
        - Total revenue generated
        - Fork/star counts (popularity)
        """
        # Base value from revenue
        base_value = total_revenue * 2  # 2x revenue multiple

        # License volume bonus
        license_bonus = 1.0 + (total_licenses_sold * 0.05)
        value = base_value * min(2.0, license_bonus)

        # Popularity bonus
        popularity_score = (fork_count * 0.01) + (star_count * 0.001)
        popularity_multiplier = 1.0 + min(0.5, popularity_score)
        value *= popularity_multiplier

        return max(0.01, value)  # Minimum 0.01 ETH


class IPFiLendingManager:
    """Manages IP-backed lending operations."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/lending")
        self.loans: Dict[str, Loan] = {}
        self.offers: Dict[str, LoanOffer] = {}
        self.collaterals: Dict[str, Collateral] = {}
        self.valuator = CollateralValuator()

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    # =========================================================================
    # Collateral Management
    # =========================================================================

    def register_collateral(
        self,
        collateral_type: CollateralType,
        asset_id: str,
        owner_address: str,
        estimated_value: float,
    ) -> Collateral:
        """Register an asset as potential collateral."""
        collateral = Collateral(
            collateral_id=self._generate_id("col_"),
            collateral_type=collateral_type,
            asset_id=asset_id,
            owner_address=owner_address,
            estimated_value=estimated_value,
        )

        self.collaterals[collateral.collateral_id] = collateral
        self._save_state()

        return collateral

    def update_collateral_value(self, collateral_id: str, new_value: float) -> Collateral:
        """Update the estimated value of collateral."""
        collateral = self.collaterals.get(collateral_id)
        if not collateral:
            raise ValueError(f"Collateral not found: {collateral_id}")

        collateral.estimated_value = new_value
        self._save_state()

        return collateral

    def lock_collateral(self, collateral_id: str) -> Collateral:
        """Lock collateral for a loan."""
        collateral = self.collaterals.get(collateral_id)
        if not collateral:
            raise ValueError(f"Collateral not found: {collateral_id}")

        if collateral.locked:
            raise ValueError(f"Collateral already locked: {collateral_id}")

        collateral.locked = True
        collateral.locked_at = datetime.now()
        self._save_state()

        return collateral

    def unlock_collateral(self, collateral_id: str) -> Collateral:
        """Unlock collateral after loan completion."""
        collateral = self.collaterals.get(collateral_id)
        if not collateral:
            raise ValueError(f"Collateral not found: {collateral_id}")

        collateral.locked = False
        collateral.locked_at = None
        self._save_state()

        return collateral

    # =========================================================================
    # Loan Offers
    # =========================================================================

    def create_loan_offer(
        self,
        lender_address: str,
        principal: float,
        interest_rate: float,
        duration_days: int,
        accepted_collateral_types: List[CollateralType],
        min_collateral_value: float,
        max_collateral_value: float,
        ltv_ratio: float = 0.5,
        expires_in_days: int = 7,
    ) -> LoanOffer:
        """Create a new loan offer."""
        terms = LoanTerms(
            principal=principal,
            interest_rate=interest_rate,
            duration_days=duration_days,
            collateral_value=min_collateral_value,
            ltv_ratio=ltv_ratio,
        )

        offer = LoanOffer(
            offer_id=self._generate_id("offer_"),
            lender_address=lender_address,
            terms=terms,
            accepted_collateral_types=accepted_collateral_types,
            min_collateral_value=min_collateral_value,
            max_collateral_value=max_collateral_value,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=expires_in_days),
        )

        self.offers[offer.offer_id] = offer
        self._save_state()

        return offer

    def list_offers(
        self,
        active_only: bool = True,
        collateral_type: Optional[CollateralType] = None,
        min_principal: Optional[float] = None,
        max_principal: Optional[float] = None,
    ) -> List[LoanOffer]:
        """List available loan offers."""
        offers = list(self.offers.values())

        if active_only:
            offers = [o for o in offers if o.active and not o.is_expired]

        if collateral_type:
            offers = [o for o in offers if collateral_type in o.accepted_collateral_types]

        if min_principal is not None:
            offers = [o for o in offers if o.terms.principal >= min_principal]

        if max_principal is not None:
            offers = [o for o in offers if o.terms.principal <= max_principal]

        return offers

    def cancel_offer(self, offer_id: str) -> LoanOffer:
        """Cancel a loan offer."""
        offer = self.offers.get(offer_id)
        if not offer:
            raise ValueError(f"Offer not found: {offer_id}")

        offer.active = False
        self._save_state()

        return offer

    # =========================================================================
    # Loan Operations
    # =========================================================================

    def request_loan(self, offer_id: str, borrower_address: str, collateral_id: str) -> Loan:
        """Request a loan by accepting an offer."""
        offer = self.offers.get(offer_id)
        if not offer:
            raise ValueError(f"Offer not found: {offer_id}")

        if not offer.active or offer.is_expired:
            raise ValueError("Offer is no longer active")

        collateral = self.collaterals.get(collateral_id)
        if not collateral:
            raise ValueError(f"Collateral not found: {collateral_id}")

        if collateral.locked:
            raise ValueError("Collateral is already locked")

        if collateral.owner_address.lower() != borrower_address.lower():
            raise ValueError("Collateral owner mismatch")

        if collateral.collateral_type not in offer.accepted_collateral_types:
            raise ValueError("Collateral type not accepted by this offer")

        if not (
            offer.min_collateral_value <= collateral.estimated_value <= offer.max_collateral_value
        ):
            raise ValueError("Collateral value out of accepted range")

        # Create loan
        loan = Loan(
            loan_id=self._generate_id("loan_"),
            borrower_address=borrower_address,
            lender_address=offer.lender_address,
            collateral=collateral,
            terms=offer.terms,
            status=LoanStatus.PENDING,
            created_at=datetime.now(),
        )

        self.loans[loan.loan_id] = loan
        self._save_state()

        return loan

    def fund_loan(self, loan_id: str) -> Loan:
        """Fund a pending loan (lender action)."""
        loan = self.loans.get(loan_id)
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")

        if loan.status != LoanStatus.PENDING:
            raise ValueError(f"Loan is not pending: {loan.status.value}")

        # Lock collateral
        self.lock_collateral(loan.collateral.collateral_id)

        # Update loan status
        loan.status = LoanStatus.ACTIVE
        loan.funded_at = datetime.now()
        loan.due_date = datetime.now() + timedelta(days=loan.terms.duration_days)

        self._save_state()

        return loan

    def repay_loan(self, loan_id: str, amount: float) -> Loan:
        """Make a payment on a loan."""
        loan = self.loans.get(loan_id)
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")

        if loan.status != LoanStatus.ACTIVE:
            raise ValueError(f"Loan is not active: {loan.status.value}")

        loan.amount_repaid += amount

        # Check if fully repaid
        if loan.amount_repaid >= loan.terms.total_repayment:
            loan.status = LoanStatus.REPAID
            loan.repaid_at = datetime.now()
            # Unlock collateral
            self.unlock_collateral(loan.collateral.collateral_id)

        self._save_state()

        return loan

    def liquidate_loan(self, loan_id: str) -> Loan:
        """Liquidate a defaulted loan."""
        loan = self.loans.get(loan_id)
        if not loan:
            raise ValueError(f"Loan not found: {loan_id}")

        if loan.status != LoanStatus.ACTIVE:
            raise ValueError(f"Loan is not active: {loan.status.value}")

        # Check if eligible for liquidation
        if not loan.is_overdue and loan.current_ltv < loan.terms.liquidation_threshold:
            raise ValueError("Loan is not eligible for liquidation")

        loan.status = LoanStatus.LIQUIDATED
        # Collateral transfers to lender (remains locked but ownership changes)

        self._save_state()

        return loan

    def get_loan(self, loan_id: str) -> Optional[Loan]:
        """Get a loan by ID."""
        return self.loans.get(loan_id)

    def list_loans(
        self,
        borrower_address: Optional[str] = None,
        lender_address: Optional[str] = None,
        status: Optional[LoanStatus] = None,
    ) -> List[Loan]:
        """List loans with optional filters."""
        loans = list(self.loans.values())

        if borrower_address:
            loans = [ln for ln in loans if ln.borrower_address.lower() == borrower_address.lower()]

        if lender_address:
            loans = [ln for ln in loans if ln.lender_address.lower() == lender_address.lower()]

        if status:
            loans = [ln for ln in loans if ln.status == status]

        return loans

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_market_stats(self) -> Dict[str, Any]:
        """Get overall lending market statistics."""
        active_loans = [ln for ln in self.loans.values() if ln.status == LoanStatus.ACTIVE]
        all_loans = list(self.loans.values())

        total_value_locked = sum(ln.collateral.estimated_value for ln in active_loans)
        total_borrowed = sum(ln.terms.principal for ln in active_loans)
        total_repaid = sum(ln.amount_repaid for ln in all_loans)

        return {
            "total_loans": len(all_loans),
            "active_loans": len(active_loans),
            "pending_loans": len([ln for ln in all_loans if ln.status == LoanStatus.PENDING]),
            "repaid_loans": len([ln for ln in all_loans if ln.status == LoanStatus.REPAID]),
            "defaulted_loans": len([ln for ln in all_loans if ln.status == LoanStatus.DEFAULTED]),
            "liquidated_loans": len([ln for ln in all_loans if ln.status == LoanStatus.LIQUIDATED]),
            "total_value_locked": total_value_locked,
            "total_borrowed": total_borrowed,
            "total_repaid": total_repaid,
            "active_offers": len(
                [o for o in self.offers.values() if o.active and not o.is_expired]
            ),
            "registered_collaterals": len(self.collaterals),
            "locked_collaterals": len([c for c in self.collaterals.values() if c.locked]),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "loans": {lid: loan.to_dict() for lid, loan in self.loans.items()},
            "offers": {oid: offer.to_dict() for oid, offer in self.offers.items()},
            "collaterals": {cid: coll.to_dict() for cid, coll in self.collaterals.items()},
        }

        with open(self.data_dir / "lending_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        state_file = self.data_dir / "lending_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.loans = {lid: Loan.from_dict(loan) for lid, loan in state.get("loans", {}).items()}
            self.offers = {
                oid: LoanOffer.from_dict(offer) for oid, offer in state.get("offers", {}).items()
            }
            self.collaterals = {
                cid: Collateral.from_dict(coll)
                for cid, coll in state.get("collaterals", {}).items()
            }
        except (json.JSONDecodeError, KeyError):
            pass


def create_lending_manager(data_dir: Optional[str] = None) -> IPFiLendingManager:
    """Factory function to create a lending manager."""
    path = Path(data_dir) if data_dir else None
    return IPFiLendingManager(data_dir=path)
