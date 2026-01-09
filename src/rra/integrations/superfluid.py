# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Superfluid Protocol integration for streaming payments.

Enables real-time money streams for subscription-based licensing:
- Per-second payment flows
- Automatic access revocation when streams stop
- Grace period support
- Multi-token support (USDCx, DAIx, etc.)

Superfluid is best deployed on Polygon for low gas costs.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from web3 import Web3
    from web3.contract import Contract

    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    Web3 = None
    Contract = None


class StreamStatus(Enum):
    """Status of a Superfluid stream."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    REVOKED = "revoked"


class SupportedNetwork(Enum):
    """Networks with Superfluid support."""

    POLYGON = "polygon"
    POLYGON_MUMBAI = "polygon-mumbai"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    GNOSIS = "gnosis"
    ETHEREUM = "ethereum"


@dataclass
class StreamingLicense:
    """Represents a streaming license subscription."""

    license_id: str
    repo_id: str
    buyer_address: str
    seller_address: str
    flow_rate: int  # tokens per second (in wei)
    token: str  # e.g., "USDCx"
    monthly_cost_usd: float
    start_time: datetime
    grace_period_seconds: int
    status: StreamStatus
    tx_hash: Optional[str] = None
    stop_time: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["start_time"] = self.start_time.isoformat()
        if self.stop_time:
            data["stop_time"] = self.stop_time.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamingLicense":
        """Create from dictionary."""
        data["status"] = StreamStatus(data["status"])
        data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data.get("stop_time"):
            data["stop_time"] = datetime.fromisoformat(data["stop_time"])
        return cls(**data)


# Superfluid contract addresses by network
SUPERFLUID_ADDRESSES = {
    SupportedNetwork.POLYGON: {
        "host": "0x3E14dC1b13c488a8d5D310918780c983bD5982E7",
        "cfa": "0x6EeE6060f715257b970700bc2656De21dEdF074C",
        "tokens": {
            "USDCx": "0xCAa7349CEA390F89641fe306D93591f87595dc1F",
            "DAIx": "0x1305F6B6Df9Dc47159D12Eb7aC2804d4A33173c2",
            "WETHx": "0x27e1e4E6BC79D93032abef01025811B7E4727e85",
        },
    },
    SupportedNetwork.POLYGON_MUMBAI: {
        "host": "0xEB796bdb90fFA0f28255275e16936D25d3418603",
        "cfa": "0x49e565Ed1bdc17F3d220f72DF0857C26FA83F873",
        "tokens": {
            "fUSDCx": "0x42bb40bF79730451B11f6De1CbA222F17b87Afd7",
            "fDAIx": "0x5D8B4C2554aeB7e86F387B4d6c00Ac33499Ed01f",
        },
    },
    SupportedNetwork.ARBITRUM: {
        "host": "0xCf8Acb4eF033efF16E8080aed4c7D5B9285D2192",
        "cfa": "0x731FdBB12944973B500518aea61942381d7e240D",
        "tokens": {
            "USDCx": "0x7BE4c6B5C8C77c13EBEB10DAFC46c0c7Dc11D54b",
        },
    },
}


class SuperfluidManager:
    """
    Manage Superfluid streaming payments for RRA licenses.

    Provides:
    - Stream creation and management
    - Flow rate calculations
    - License status monitoring
    - Access revocation on stream stop
    """

    # Seconds per month (30 days)
    SECONDS_PER_MONTH = 30 * 24 * 60 * 60

    def __init__(
        self,
        w3: Optional["Web3"] = None,
        network: SupportedNetwork = SupportedNetwork.POLYGON,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize Superfluid manager.

        Args:
            w3: Web3 instance (optional for offline mode)
            network: Target network
            storage_path: Path to store license data
        """
        self.w3 = w3
        self.network = network
        self.storage_path = storage_path or Path("agent_knowledge_bases/streaming_licenses.json")
        self._licenses: Dict[str, StreamingLicense] = {}
        self._load_licenses()

        # Get contract addresses
        if network in SUPERFLUID_ADDRESSES:
            self.addresses = SUPERFLUID_ADDRESSES[network]
        else:
            self.addresses = {}

    def _load_licenses(self) -> None:
        """Load licenses from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for license_id, license_data in data.items():
                        self._licenses[license_id] = StreamingLicense.from_dict(license_data)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_licenses(self) -> None:
        """Save licenses to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {license_id: license.to_dict() for license_id, license in self._licenses.items()}
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def calculate_flow_rate(self, monthly_usd: float, decimals: int = 18) -> int:
        """
        Convert monthly price to tokens per second (in wei).

        Args:
            monthly_usd: Monthly cost in USD
            decimals: Token decimals (default 18)

        Returns:
            Flow rate in wei per second
        """
        per_second = monthly_usd / self.SECONDS_PER_MONTH
        return int(per_second * (10**decimals))

    def calculate_monthly_from_flow_rate(self, flow_rate: int, decimals: int = 18) -> float:
        """
        Convert flow rate to monthly cost.

        Args:
            flow_rate: Tokens per second in wei
            decimals: Token decimals

        Returns:
            Monthly cost in token units
        """
        per_second = flow_rate / (10**decimals)
        return per_second * self.SECONDS_PER_MONTH

    def get_supported_tokens(self) -> List[str]:
        """Get list of supported super tokens on current network."""
        return list(self.addresses.get("tokens", {}).keys())

    def get_token_address(self, token: str) -> Optional[str]:
        """Get super token contract address."""
        return self.addresses.get("tokens", {}).get(token)

    def create_streaming_license(
        self,
        repo_id: str,
        buyer_address: str,
        seller_address: str,
        monthly_price_usd: float,
        token: str = "USDCx",
        grace_period_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StreamingLicense:
        """
        Create a new streaming license subscription.

        Args:
            repo_id: Repository/agent ID
            buyer_address: Buyer's wallet address
            seller_address: Seller's wallet address
            monthly_price_usd: Monthly subscription cost
            token: Super token to use (USDCx, DAIx, etc.)
            grace_period_hours: Hours after stream stops before revocation
            metadata: Additional license metadata

        Returns:
            Created StreamingLicense
        """
        import uuid

        license_id = f"sl_{uuid.uuid4().hex[:12]}"
        flow_rate = self.calculate_flow_rate(monthly_price_usd)

        license = StreamingLicense(
            license_id=license_id,
            repo_id=repo_id,
            buyer_address=buyer_address.lower(),
            seller_address=seller_address.lower(),
            flow_rate=flow_rate,
            token=token,
            monthly_cost_usd=monthly_price_usd,
            start_time=datetime.utcnow(),
            grace_period_seconds=grace_period_hours * 3600,
            status=StreamStatus.PENDING,
            metadata=metadata,
        )

        self._licenses[license_id] = license
        self._save_licenses()

        return license

    async def activate_stream(self, license_id: str) -> Dict[str, Any]:
        """
        Activate a streaming license (create on-chain stream).

        In production, this would create the actual Superfluid stream.

        Args:
            license_id: License to activate

        Returns:
            Transaction details
        """
        if license_id not in self._licenses:
            raise ValueError(f"License not found: {license_id}")

        license = self._licenses[license_id]

        if self.w3 and HAS_WEB3:
            # Production: Create actual Superfluid stream
            # This would call the Superfluid contracts
            tx_hash = await self._create_stream_on_chain(license)
            license.tx_hash = tx_hash
        else:
            # Offline mode: Just update status
            license.tx_hash = f"0x{'0' * 64}"

        license.status = StreamStatus.ACTIVE
        license.start_time = datetime.utcnow()
        self._save_licenses()

        return {
            "license_id": license_id,
            "status": "active",
            "tx_hash": license.tx_hash,
            "flow_rate": license.flow_rate,
            "monthly_cost": license.monthly_cost_usd,
        }

    async def _create_stream_on_chain(self, license: StreamingLicense) -> str:
        """Create actual Superfluid stream on-chain."""
        # This would use the Superfluid SDK to create a CFA stream
        # For now, return placeholder
        return f"0x{'0' * 64}"

    async def stop_stream(self, license_id: str) -> Dict[str, Any]:
        """
        Stop a streaming license.

        Args:
            license_id: License to stop

        Returns:
            Transaction details
        """
        if license_id not in self._licenses:
            raise ValueError(f"License not found: {license_id}")

        license = self._licenses[license_id]
        license.status = StreamStatus.STOPPED
        license.stop_time = datetime.utcnow()
        self._save_licenses()

        return {
            "license_id": license_id,
            "status": "stopped",
            "stop_time": license.stop_time.isoformat(),
        }

    async def check_stream_status(self, license_id: str) -> Dict[str, Any]:
        """
        Check the current status of a streaming license.

        Args:
            license_id: License to check

        Returns:
            Current status and stream details
        """
        if license_id not in self._licenses:
            raise ValueError(f"License not found: {license_id}")

        license = self._licenses[license_id]

        # Calculate time since start
        elapsed = (datetime.utcnow() - license.start_time).total_seconds()
        total_paid = (license.flow_rate * elapsed) / (10**18)

        result = {
            "license_id": license_id,
            "status": license.status.value,
            "flow_rate": license.flow_rate,
            "monthly_cost": license.monthly_cost_usd,
            "elapsed_seconds": int(elapsed),
            "total_paid": total_paid,
            "buyer": license.buyer_address,
            "seller": license.seller_address,
        }

        if license.status == StreamStatus.STOPPED and license.stop_time:
            grace_remaining = (
                license.grace_period_seconds
                - (datetime.utcnow() - license.stop_time).total_seconds()
            )
            result["grace_period_remaining"] = max(0, int(grace_remaining))
            result["will_revoke_at"] = (
                license.stop_time + timedelta(seconds=license.grace_period_seconds)
            ).isoformat()

        return result

    def check_access(self, license_id: str) -> bool:
        """
        Check if a license has valid access (stream active or in grace period).

        Args:
            license_id: License to check

        Returns:
            True if access is valid
        """
        if license_id not in self._licenses:
            return False

        license = self._licenses[license_id]

        if license.status == StreamStatus.ACTIVE:
            return True

        if license.status == StreamStatus.STOPPED and license.stop_time:
            # Check if within grace period
            grace_end = license.stop_time + timedelta(seconds=license.grace_period_seconds)
            if datetime.utcnow() < grace_end:
                return True

        return False

    async def revoke_expired_licenses(self) -> List[str]:
        """
        Revoke all licenses that have exceeded their grace period.

        Returns:
            List of revoked license IDs
        """
        revoked = []

        for license_id, license in self._licenses.items():
            if license.status == StreamStatus.STOPPED and license.stop_time:
                grace_end = license.stop_time + timedelta(seconds=license.grace_period_seconds)
                if datetime.utcnow() >= grace_end:
                    license.status = StreamStatus.REVOKED
                    revoked.append(license_id)

        if revoked:
            self._save_licenses()

        return revoked

    def get_license(self, license_id: str) -> Optional[StreamingLicense]:
        """Get a specific license."""
        return self._licenses.get(license_id)

    def get_licenses_for_repo(self, repo_id: str) -> List[StreamingLicense]:
        """Get all licenses for a repository."""
        return [license for license in self._licenses.values() if license.repo_id == repo_id]

    def get_licenses_for_buyer(self, buyer_address: str) -> List[StreamingLicense]:
        """Get all licenses for a buyer."""
        buyer = buyer_address.lower()
        return [license for license in self._licenses.values() if license.buyer_address == buyer]

    def get_active_licenses(self) -> List[StreamingLicense]:
        """Get all active streaming licenses."""
        return [
            license for license in self._licenses.values() if license.status == StreamStatus.ACTIVE
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get streaming payment statistics."""
        active = len([lic for lic in self._licenses.values() if lic.status == StreamStatus.ACTIVE])
        stopped = len(
            [lic for lic in self._licenses.values() if lic.status == StreamStatus.STOPPED]
        )
        revoked = len(
            [lic for lic in self._licenses.values() if lic.status == StreamStatus.REVOKED]
        )

        total_monthly_revenue = sum(
            lic.monthly_cost_usd
            for lic in self._licenses.values()
            if lic.status == StreamStatus.ACTIVE
        )

        return {
            "total_licenses": len(self._licenses),
            "active_streams": active,
            "stopped_streams": stopped,
            "revoked_licenses": revoked,
            "total_monthly_revenue_usd": total_monthly_revenue,
            "network": self.network.value,
        }

    def generate_stream_proposal(
        self, repo_name: str, monthly_price: float, token: str = "USDCx"
    ) -> str:
        """
        Generate a negotiation proposal for streaming subscription.

        Args:
            repo_name: Repository name
            monthly_price: Monthly price in USD
            token: Super token for payments

        Returns:
            Proposal text for negotiation agent
        """
        self.calculate_flow_rate(monthly_price)
        per_second = monthly_price / self.SECONDS_PER_MONTH

        return f"""I can offer a streaming subscription model using Superfluid for {repo_name}:

**Subscription Terms:**
- Monthly Rate: ${monthly_price:.2f}/month
- Per-Second Rate: ${per_second:.8f}/second
- Payment Token: {token}
- Network: {self.network.value.title()}

**Benefits:**
- Pay only for what you use (per-second billing)
- Cancel anytime - no lock-in period
- 24-hour grace period after cancellation
- Automatic license NFT minting
- On-chain verification of subscription status

With streaming payments, you only pay for actual usage time. Would you like to proceed with this streaming subscription?"""
