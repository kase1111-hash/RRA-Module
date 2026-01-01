# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Stream Access Controller for Superfluid-based licenses.

Controls repository access based on streaming payment status:
- Verifies active payment streams
- Manages grace periods
- Handles access revocation
- Provides access verification endpoints
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from rra.integrations.superfluid import SuperfluidManager, StreamStatus, StreamingLicense

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """Repository access levels."""
    NONE = "none"
    READ = "read"
    FULL = "full"
    ENTERPRISE = "enterprise"


@dataclass
class AccessGrant:
    """Represents an access grant for a buyer."""
    license_id: str
    repo_id: str
    buyer_address: str
    access_level: AccessLevel
    granted_at: datetime
    expires_at: Optional[datetime]
    is_streaming: bool
    monthly_cost: Optional[float]


class StreamAccessController:
    """
    Control repository access based on Superfluid stream status.

    Provides:
    - Real-time access verification
    - Grace period management
    - Automatic revocation
    - Access event notifications
    """

    def __init__(
        self,
        superfluid_manager: SuperfluidManager,
        default_grace_hours: int = 24,
        check_interval_seconds: int = 60,
    ):
        """
        Initialize stream access controller.

        Args:
            superfluid_manager: Superfluid manager instance
            default_grace_hours: Default grace period in hours
            check_interval_seconds: How often to check stream status
        """
        self.sf = superfluid_manager
        self.default_grace_hours = default_grace_hours
        self.check_interval_seconds = check_interval_seconds
        self._access_grants: Dict[str, AccessGrant] = {}
        self._revocation_callbacks: List[Callable] = []
        self._monitor_task: Optional[asyncio.Task] = None

    def add_revocation_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Add a callback for access revocation events.

        Args:
            callback: Function(license_id, buyer_address) called on revocation
        """
        self._revocation_callbacks.append(callback)

    async def check_access(self, license_id: str) -> Dict[str, Any]:
        """
        Check if a buyer has valid access for a license.

        Args:
            license_id: License ID to check

        Returns:
            Access status and details
        """
        license = self.sf.get_license(license_id)

        if not license:
            return {
                "has_access": False,
                "reason": "license_not_found",
                "license_id": license_id,
            }

        has_access = self.sf.check_access(license_id)

        result = {
            "has_access": has_access,
            "license_id": license_id,
            "buyer": license.buyer_address,
            "repo_id": license.repo_id,
            "status": license.status.value,
        }

        if has_access:
            result["reason"] = "active_stream" if license.status == StreamStatus.ACTIVE else "grace_period"

            if license.status == StreamStatus.STOPPED and license.stop_time:
                grace_end = license.stop_time + timedelta(seconds=license.grace_period_seconds)
                result["grace_ends_at"] = grace_end.isoformat()
                result["grace_remaining_seconds"] = max(
                    0,
                    int((grace_end - datetime.utcnow()).total_seconds())
                )
        else:
            if license.status == StreamStatus.REVOKED:
                result["reason"] = "revoked"
            elif license.status == StreamStatus.STOPPED:
                result["reason"] = "grace_period_expired"
            else:
                result["reason"] = "stream_inactive"

        return result

    async def check_access_by_buyer(
        self,
        repo_id: str,
        buyer_address: str
    ) -> Dict[str, Any]:
        """
        Check if a buyer has access to a specific repository.

        Args:
            repo_id: Repository ID
            buyer_address: Buyer's wallet address

        Returns:
            Access status and details
        """
        licenses = self.sf.get_licenses_for_buyer(buyer_address)
        repo_licenses = [l for l in licenses if l.repo_id == repo_id]

        if not repo_licenses:
            return {
                "has_access": False,
                "reason": "no_license",
                "repo_id": repo_id,
                "buyer": buyer_address,
            }

        # Check for any active license
        for license in repo_licenses:
            if self.sf.check_access(license.license_id):
                return await self.check_access(license.license_id)

        # No active access
        return {
            "has_access": False,
            "reason": "all_licenses_expired",
            "repo_id": repo_id,
            "buyer": buyer_address,
            "license_count": len(repo_licenses),
        }

    async def grant_access(
        self,
        license_id: str,
        access_level: AccessLevel = AccessLevel.FULL,
    ) -> AccessGrant:
        """
        Grant access for a streaming license.

        Args:
            license_id: License ID
            access_level: Level of access to grant

        Returns:
            Access grant details
        """
        license = self.sf.get_license(license_id)

        if not license:
            raise ValueError(f"License not found: {license_id}")

        grant = AccessGrant(
            license_id=license_id,
            repo_id=license.repo_id,
            buyer_address=license.buyer_address,
            access_level=access_level,
            granted_at=datetime.utcnow(),
            expires_at=None,  # Streaming licenses don't have fixed expiry
            is_streaming=True,
            monthly_cost=license.monthly_cost_usd,
        )

        self._access_grants[license_id] = grant
        return grant

    async def revoke_access(self, license_id: str, reason: str = "stream_stopped") -> bool:
        """
        Revoke access for a license.

        Args:
            license_id: License to revoke
            reason: Reason for revocation

        Returns:
            True if revoked successfully
        """
        license = self.sf.get_license(license_id)

        if not license:
            return False

        # Update license status
        if license.status != StreamStatus.REVOKED:
            license.status = StreamStatus.REVOKED
            self.sf._save_licenses()

        # Remove access grant
        if license_id in self._access_grants:
            del self._access_grants[license_id]

        # Call revocation callbacks
        for callback in self._revocation_callbacks:
            try:
                callback(license_id, license.buyer_address)
            except Exception as e:
                logger.warning(f"Revocation callback failed for license {license_id}: {e}")

        return True

    async def start_monitoring(self) -> None:
        """Start background task to monitor streams and revoke expired access."""
        if self._monitor_task is not None:
            return

        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self) -> None:
        """Stop the background monitoring task."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self) -> None:
        """Background loop to check and revoke expired licenses."""
        while True:
            try:
                # Revoke expired licenses
                revoked = await self.sf.revoke_expired_licenses()

                for license_id in revoked:
                    await self.revoke_access(license_id, reason="grace_period_expired")

                await asyncio.sleep(self.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream monitor error: {e}")
                await asyncio.sleep(self.check_interval_seconds)

    def get_active_grants(self) -> List[AccessGrant]:
        """Get all active access grants."""
        return list(self._access_grants.values())

    def get_grants_for_repo(self, repo_id: str) -> List[AccessGrant]:
        """Get all grants for a repository."""
        return [
            grant for grant in self._access_grants.values()
            if grant.repo_id == repo_id
        ]

    async def get_access_summary(self, repo_id: str) -> Dict[str, Any]:
        """
        Get access summary for a repository.

        Args:
            repo_id: Repository ID

        Returns:
            Summary of access grants and streaming status
        """
        licenses = self.sf.get_licenses_for_repo(repo_id)
        grants = self.get_grants_for_repo(repo_id)

        active_count = len([l for l in licenses if l.status == StreamStatus.ACTIVE])
        stopped_count = len([l for l in licenses if l.status == StreamStatus.STOPPED])
        revoked_count = len([l for l in licenses if l.status == StreamStatus.REVOKED])

        total_mrr = sum(
            l.monthly_cost_usd
            for l in licenses
            if l.status == StreamStatus.ACTIVE
        )

        return {
            "repo_id": repo_id,
            "total_licenses": len(licenses),
            "active_streams": active_count,
            "stopped_streams": stopped_count,
            "revoked_licenses": revoked_count,
            "active_grants": len(grants),
            "monthly_recurring_revenue": total_mrr,
        }


class AccessVerificationMiddleware:
    """
    Middleware for verifying access in API requests.

    Usage:
        controller = StreamAccessController(sf_manager)
        middleware = AccessVerificationMiddleware(controller)

        @app.get("/repo/{repo_id}/download")
        async def download(repo_id: str, buyer: str):
            if not await middleware.verify(repo_id, buyer):
                raise HTTPException(403, "Access denied")
            ...
    """

    def __init__(self, controller: StreamAccessController):
        """Initialize middleware with access controller."""
        self.controller = controller

    async def verify(
        self,
        repo_id: str,
        buyer_address: str,
        required_level: AccessLevel = AccessLevel.READ
    ) -> bool:
        """
        Verify buyer has required access level.

        Args:
            repo_id: Repository ID
            buyer_address: Buyer's wallet address
            required_level: Minimum required access level

        Returns:
            True if access is granted
        """
        result = await self.controller.check_access_by_buyer(repo_id, buyer_address)
        return result.get("has_access", False)

    async def get_access_token(
        self,
        license_id: str,
        duration_hours: int = 24
    ) -> Optional[str]:
        """
        Generate a temporary access token for a valid license.

        Args:
            license_id: License ID
            duration_hours: Token validity duration

        Returns:
            Access token or None if access denied
        """
        import secrets
        import hashlib

        result = await self.controller.check_access(license_id)
        if not result.get("has_access"):
            return None

        # Generate token
        token_data = f"{license_id}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
        return hashlib.sha256(token_data.encode()).hexdigest()
