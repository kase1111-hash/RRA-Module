# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Fractional IP Ownership Module.

Enables fractionalizing IP assets (license NFTs) into tradeable shares,
allowing multiple parties to own portions of valuable IP assets.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import secrets


class FractionStatus(Enum):
    """Status of a fractionalized asset."""

    PENDING = "pending"
    ACTIVE = "active"
    BUYOUT_INITIATED = "buyout_initiated"
    BOUGHT_OUT = "bought_out"
    DISSOLVED = "dissolved"


class ShareTransferType(Enum):
    """Types of share transfers."""

    INITIAL_DISTRIBUTION = "initial_distribution"
    SALE = "sale"
    TRANSFER = "transfer"
    BUYOUT = "buyout"
    DIVIDEND = "dividend"


@dataclass
class ShareHolder:
    """Represents a holder of fractional shares."""

    address: str
    shares: int
    acquired_at: datetime
    total_dividends_claimed: float = 0.0

    @property
    def share_percentage(self) -> float:
        """Placeholder - actual percentage calculated by FractionalAsset."""
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "shares": self.shares,
            "acquired_at": self.acquired_at.isoformat(),
            "total_dividends_claimed": self.total_dividends_claimed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShareHolder":
        return cls(
            address=data["address"],
            shares=data["shares"],
            acquired_at=datetime.fromisoformat(data["acquired_at"]),
            total_dividends_claimed=data.get("total_dividends_claimed", 0.0),
        )


@dataclass
class FractionalAsset:
    """A fractionalized IP asset."""

    asset_id: str
    name: str
    description: str
    original_owner: str
    underlying_asset_id: str  # Original license/IP asset ID
    underlying_asset_type: str  # "license_nft" or "ip_asset"

    # Tokenomics
    total_shares: int
    share_price: float  # Price per share in ETH
    min_shares_per_holder: int = 1
    max_shares_per_holder: int = 0  # 0 = no limit

    # State
    status: FractionStatus = FractionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None

    # Revenue distribution
    total_revenue: float = 0.0
    distributed_revenue: float = 0.0
    pending_revenue: float = 0.0

    # Buyout settings
    buyout_price: Optional[float] = None
    buyout_initiator: Optional[str] = None
    buyout_deadline: Optional[datetime] = None

    # Shareholders stored separately
    _shareholders: Dict[str, ShareHolder] = field(default_factory=dict)

    @property
    def total_value(self) -> float:
        """Total value of the fractionalized asset."""
        return self.total_shares * self.share_price

    @property
    def shares_outstanding(self) -> int:
        """Total shares held by shareholders."""
        return sum(h.shares for h in self._shareholders.values())

    @property
    def shares_available(self) -> int:
        """Shares available for purchase."""
        return self.total_shares - self.shares_outstanding

    def get_holder_percentage(self, address: str) -> float:
        """Get ownership percentage for an address."""
        holder = self._shareholders.get(address.lower())
        if not holder:
            return 0.0
        return (holder.shares / self.total_shares) * 100

    def add_shareholder(self, address: str, shares: int) -> ShareHolder:
        """Add or update a shareholder."""
        address = address.lower()

        if shares > self.shares_available:
            raise ValueError(f"Not enough shares available. Available: {self.shares_available}")

        if self.max_shares_per_holder > 0:
            current = self._shareholders.get(address)
            current_shares = current.shares if current else 0
            if current_shares + shares > self.max_shares_per_holder:
                raise ValueError(
                    f"Would exceed max shares per holder: {self.max_shares_per_holder}"
                )

        if address in self._shareholders:
            self._shareholders[address].shares += shares
        else:
            self._shareholders[address] = ShareHolder(
                address=address,
                shares=shares,
                acquired_at=datetime.now(),
            )

        return self._shareholders[address]

    def transfer_shares(
        self, from_address: str, to_address: str, shares: int
    ) -> tuple[ShareHolder, ShareHolder]:
        """Transfer shares between addresses."""
        from_address = from_address.lower()
        to_address = to_address.lower()

        from_holder = self._shareholders.get(from_address)
        if not from_holder or from_holder.shares < shares:
            raise ValueError("Insufficient shares to transfer")

        # Deduct from sender
        from_holder.shares -= shares

        # Add to recipient
        if to_address in self._shareholders:
            self._shareholders[to_address].shares += shares
        else:
            self._shareholders[to_address] = ShareHolder(
                address=to_address,
                shares=shares,
                acquired_at=datetime.now(),
            )

        # Clean up empty holdings
        if from_holder.shares == 0:
            del self._shareholders[from_address]
            from_holder = ShareHolder(address=from_address, shares=0, acquired_at=datetime.now())

        return from_holder, self._shareholders[to_address]

    def distribute_revenue(self, amount: float) -> Dict[str, float]:
        """Distribute revenue to shareholders proportionally."""
        self.total_revenue += amount
        distributions: Dict[str, float] = {}

        if self.shares_outstanding == 0:
            self.pending_revenue += amount
            return distributions

        for address, holder in self._shareholders.items():
            share_ratio = holder.shares / self.shares_outstanding
            holder_amount = amount * share_ratio
            distributions[address] = holder_amount
            holder.total_dividends_claimed += holder_amount

        self.distributed_revenue += amount
        return distributions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "description": self.description,
            "original_owner": self.original_owner,
            "underlying_asset_id": self.underlying_asset_id,
            "underlying_asset_type": self.underlying_asset_type,
            "total_shares": self.total_shares,
            "share_price": self.share_price,
            "min_shares_per_holder": self.min_shares_per_holder,
            "max_shares_per_holder": self.max_shares_per_holder,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "total_revenue": self.total_revenue,
            "distributed_revenue": self.distributed_revenue,
            "pending_revenue": self.pending_revenue,
            "buyout_price": self.buyout_price,
            "buyout_initiator": self.buyout_initiator,
            "buyout_deadline": self.buyout_deadline.isoformat() if self.buyout_deadline else None,
            "shareholders": {addr: h.to_dict() for addr, h in self._shareholders.items()},
            "total_value": self.total_value,
            "shares_outstanding": self.shares_outstanding,
            "shares_available": self.shares_available,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FractionalAsset":
        asset = cls(
            asset_id=data["asset_id"],
            name=data["name"],
            description=data["description"],
            original_owner=data["original_owner"],
            underlying_asset_id=data["underlying_asset_id"],
            underlying_asset_type=data["underlying_asset_type"],
            total_shares=data["total_shares"],
            share_price=data["share_price"],
            min_shares_per_holder=data.get("min_shares_per_holder", 1),
            max_shares_per_holder=data.get("max_shares_per_holder", 0),
            status=FractionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            total_revenue=data.get("total_revenue", 0.0),
            distributed_revenue=data.get("distributed_revenue", 0.0),
            pending_revenue=data.get("pending_revenue", 0.0),
            buyout_price=data.get("buyout_price"),
            buyout_initiator=data.get("buyout_initiator"),
        )
        if data.get("activated_at"):
            asset.activated_at = datetime.fromisoformat(data["activated_at"])
        if data.get("buyout_deadline"):
            asset.buyout_deadline = datetime.fromisoformat(data["buyout_deadline"])

        # Load shareholders
        for addr, holder_data in data.get("shareholders", {}).items():
            asset._shareholders[addr] = ShareHolder.from_dict(holder_data)

        return asset


@dataclass
class ShareOrder:
    """An order to buy or sell shares."""

    order_id: str
    asset_id: str
    order_type: str  # "buy" or "sell"
    address: str
    shares: int
    price_per_share: float
    created_at: datetime
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    filled_shares: int = 0

    @property
    def is_active(self) -> bool:
        return self.filled_at is None and self.cancelled_at is None

    @property
    def remaining_shares(self) -> int:
        return self.shares - self.filled_shares

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "asset_id": self.asset_id,
            "order_type": self.order_type,
            "address": self.address,
            "shares": self.shares,
            "price_per_share": self.price_per_share,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "filled_shares": self.filled_shares,
            "is_active": self.is_active,
            "remaining_shares": self.remaining_shares,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShareOrder":
        return cls(
            order_id=data["order_id"],
            asset_id=data["asset_id"],
            order_type=data["order_type"],
            address=data["address"],
            shares=data["shares"],
            price_per_share=data["price_per_share"],
            created_at=datetime.fromisoformat(data["created_at"]),
            filled_at=datetime.fromisoformat(data["filled_at"]) if data.get("filled_at") else None,
            cancelled_at=(
                datetime.fromisoformat(data["cancelled_at"]) if data.get("cancelled_at") else None
            ),
            filled_shares=data.get("filled_shares", 0),
        )


class FractionalIPManager:
    """Manages fractional IP ownership."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/fractional")
        self.assets: Dict[str, FractionalAsset] = {}
        self.orders: Dict[str, ShareOrder] = {}

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    # =========================================================================
    # Asset Management
    # =========================================================================

    def fractionalize_asset(
        self,
        name: str,
        description: str,
        owner_address: str,
        underlying_asset_id: str,
        underlying_asset_type: str,
        total_shares: int,
        share_price: float,
        min_shares_per_holder: int = 1,
        max_shares_per_holder: int = 0,
    ) -> FractionalAsset:
        """Create a new fractionalized asset."""
        asset = FractionalAsset(
            asset_id=self._generate_id("frac_"),
            name=name,
            description=description,
            original_owner=owner_address,
            underlying_asset_id=underlying_asset_id,
            underlying_asset_type=underlying_asset_type,
            total_shares=total_shares,
            share_price=share_price,
            min_shares_per_holder=min_shares_per_holder,
            max_shares_per_holder=max_shares_per_holder,
        )

        self.assets[asset.asset_id] = asset
        self._save_state()

        return asset

    def activate_asset(self, asset_id: str) -> FractionalAsset:
        """Activate a fractionalized asset for trading."""
        asset = self.assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        if asset.status != FractionStatus.PENDING:
            raise ValueError(f"Asset is not pending: {asset.status.value}")

        asset.status = FractionStatus.ACTIVE
        asset.activated_at = datetime.now()
        self._save_state()

        return asset

    def get_asset(self, asset_id: str) -> Optional[FractionalAsset]:
        """Get a fractionalized asset by ID."""
        return self.assets.get(asset_id)

    def list_assets(
        self, status: Optional[FractionStatus] = None, owner: Optional[str] = None
    ) -> List[FractionalAsset]:
        """List fractionalized assets."""
        assets = list(self.assets.values())

        if status:
            assets = [a for a in assets if a.status == status]

        if owner:
            assets = [a for a in assets if a.original_owner.lower() == owner.lower()]

        return assets

    # =========================================================================
    # Share Trading
    # =========================================================================

    def buy_shares(self, asset_id: str, buyer_address: str, shares: int) -> ShareHolder:
        """Buy shares directly from the asset (primary market)."""
        asset = self.assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        if asset.status != FractionStatus.ACTIVE:
            raise ValueError(f"Asset is not active: {asset.status.value}")

        holder = asset.add_shareholder(buyer_address, shares)
        self._save_state()

        return holder

    def create_sell_order(
        self, asset_id: str, seller_address: str, shares: int, price_per_share: float
    ) -> ShareOrder:
        """Create a sell order (secondary market)."""
        asset = self.assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        holder = asset._shareholders.get(seller_address.lower())
        if not holder or holder.shares < shares:
            raise ValueError("Insufficient shares to sell")

        order = ShareOrder(
            order_id=self._generate_id("order_"),
            asset_id=asset_id,
            order_type="sell",
            address=seller_address,
            shares=shares,
            price_per_share=price_per_share,
            created_at=datetime.now(),
        )

        self.orders[order.order_id] = order
        self._save_state()

        return order

    def fill_order(
        self, order_id: str, buyer_address: str, shares: Optional[int] = None
    ) -> tuple[ShareOrder, ShareHolder]:
        """Fill a sell order (buy from secondary market)."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if not order.is_active:
            raise ValueError("Order is no longer active")

        if order.order_type != "sell":
            raise ValueError("Can only fill sell orders")

        asset = self.assets.get(order.asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {order.asset_id}")

        shares_to_fill = shares or order.remaining_shares
        if shares_to_fill > order.remaining_shares:
            raise ValueError(f"Not enough shares in order. Available: {order.remaining_shares}")

        # Transfer shares
        _, buyer_holder = asset.transfer_shares(order.address, buyer_address, shares_to_fill)

        # Update order
        order.filled_shares += shares_to_fill
        if order.filled_shares >= order.shares:
            order.filled_at = datetime.now()

        self._save_state()

        return order, buyer_holder

    def cancel_order(self, order_id: str) -> ShareOrder:
        """Cancel an active order."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")

        if not order.is_active:
            raise ValueError("Order is already closed")

        order.cancelled_at = datetime.now()
        self._save_state()

        return order

    def list_orders(
        self, asset_id: Optional[str] = None, active_only: bool = True
    ) -> List[ShareOrder]:
        """List share orders."""
        orders = list(self.orders.values())

        if asset_id:
            orders = [o for o in orders if o.asset_id == asset_id]

        if active_only:
            orders = [o for o in orders if o.is_active]

        return orders

    # =========================================================================
    # Revenue Distribution
    # =========================================================================

    def distribute_asset_revenue(self, asset_id: str, amount: float) -> Dict[str, float]:
        """Distribute revenue to shareholders."""
        asset = self.assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        distributions = asset.distribute_revenue(amount)
        self._save_state()

        return distributions

    # =========================================================================
    # Buyout
    # =========================================================================

    def initiate_buyout(
        self, asset_id: str, initiator_address: str, buyout_price: float, deadline_days: int = 14
    ) -> FractionalAsset:
        """Initiate a buyout offer for all shares."""
        asset = self.assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        if asset.status != FractionStatus.ACTIVE:
            raise ValueError("Asset must be active for buyout")

        # Initiator must own some shares
        holder = asset._shareholders.get(initiator_address.lower())
        if not holder or holder.shares == 0:
            raise ValueError("Initiator must be a shareholder")

        asset.status = FractionStatus.BUYOUT_INITIATED
        asset.buyout_price = buyout_price
        asset.buyout_initiator = initiator_address
        asset.buyout_deadline = datetime.now() + __import__("datetime").timedelta(
            days=deadline_days
        )

        self._save_state()

        return asset

    def complete_buyout(self, asset_id: str) -> FractionalAsset:
        """Complete a buyout (transfer all shares to initiator)."""
        asset = self.assets.get(asset_id)
        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        if asset.status != FractionStatus.BUYOUT_INITIATED:
            raise ValueError("No buyout in progress")

        # Transfer all shares to buyout initiator
        initiator = asset.buyout_initiator.lower()
        for address in list(asset._shareholders.keys()):
            if address != initiator:
                holder = asset._shareholders[address]
                asset.transfer_shares(address, initiator, holder.shares)

        asset.status = FractionStatus.BOUGHT_OUT
        self._save_state()

        return asset

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_holder_portfolio(self, address: str) -> Dict[str, Any]:
        """Get all holdings for an address."""
        holdings = []
        total_value = 0.0

        for asset in self.assets.values():
            holder = asset._shareholders.get(address.lower())
            if holder and holder.shares > 0:
                value = holder.shares * asset.share_price
                holdings.append(
                    {
                        "asset_id": asset.asset_id,
                        "asset_name": asset.name,
                        "shares": holder.shares,
                        "share_price": asset.share_price,
                        "value": value,
                        "percentage": asset.get_holder_percentage(address),
                        "dividends_claimed": holder.total_dividends_claimed,
                    }
                )
                total_value += value

        return {
            "address": address,
            "total_holdings": len(holdings),
            "total_value": total_value,
            "holdings": holdings,
        }

    def get_market_stats(self) -> Dict[str, Any]:
        """Get overall market statistics."""
        active_assets = [a for a in self.assets.values() if a.status == FractionStatus.ACTIVE]

        total_market_cap = sum(a.total_value for a in active_assets)
        total_revenue = sum(a.total_revenue for a in self.assets.values())
        total_holders = len(
            set(addr for a in self.assets.values() for addr in a._shareholders.keys())
        )

        return {
            "total_assets": len(self.assets),
            "active_assets": len(active_assets),
            "total_market_cap": total_market_cap,
            "total_revenue_distributed": total_revenue,
            "unique_holders": total_holders,
            "active_orders": len([o for o in self.orders.values() if o.is_active]),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "assets": {aid: a.to_dict() for aid, a in self.assets.items()},
            "orders": {oid: o.to_dict() for oid, o in self.orders.items()},
        }

        with open(self.data_dir / "fractional_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        state_file = self.data_dir / "fractional_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.assets = {
                aid: FractionalAsset.from_dict(a) for aid, a in state.get("assets", {}).items()
            }
            self.orders = {
                oid: ShareOrder.from_dict(o) for oid, o in state.get("orders", {}).items()
            }
        except (json.JSONDecodeError, KeyError):
            pass


def create_fractional_manager(data_dir: Optional[str] = None) -> FractionalIPManager:
    """Factory function to create a fractional IP manager."""
    path = Path(data_dir) if data_dir else None
    return FractionalIPManager(data_dir=path)
