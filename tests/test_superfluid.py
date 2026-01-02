# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for Superfluid streaming payments integration."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta

from rra.integrations.superfluid import (
    SuperfluidManager,
    StreamStatus,
    SupportedNetwork,
    StreamingLicense,
)
from rra.access.stream_controller import (
    StreamAccessController,
    AccessLevel,
)


class TestSuperfluidManager:
    """Test cases for SuperfluidManager."""

    def test_initialization(self):
        """Test manager initialization."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(
                network=SupportedNetwork.POLYGON,
                storage_path=storage_path,
            )

            assert manager.network == SupportedNetwork.POLYGON
            assert len(manager._licenses) == 0

    def test_calculate_flow_rate(self):
        """Test flow rate calculation."""
        manager = SuperfluidManager()

        # $100/month should be ~$0.0000385/second
        monthly = 100.0
        flow_rate = manager.calculate_flow_rate(monthly)

        # Convert back
        monthly_back = manager.calculate_monthly_from_flow_rate(flow_rate)

        # Should be approximately equal (some rounding)
        assert abs(monthly - monthly_back) < 0.01

    def test_calculate_flow_rate_precision(self):
        """Test flow rate calculation precision."""
        manager = SuperfluidManager()

        # Various price points
        prices = [1.0, 10.0, 100.0, 1000.0, 0.5, 0.01]

        for price in prices:
            flow_rate = manager.calculate_flow_rate(price)
            monthly_back = manager.calculate_monthly_from_flow_rate(flow_rate)
            # Should be within 1% due to integer conversion
            assert abs(price - monthly_back) / price < 0.01

    def test_create_streaming_license(self):
        """Test creating a streaming license."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            license = manager.create_streaming_license(
                repo_id="test_repo_123",
                buyer_address="0xBuyer123",
                seller_address="0xSeller456",
                monthly_price_usd=50.0,
                token="USDCx",
                grace_period_hours=48,
            )

            assert license.license_id.startswith("sl_")
            assert license.repo_id == "test_repo_123"
            assert license.buyer_address == "0xbuyer123"  # lowercase
            assert license.seller_address == "0xseller456"
            assert license.monthly_cost_usd == 50.0
            assert license.token == "USDCx"
            assert license.status == StreamStatus.PENDING
            assert license.grace_period_seconds == 48 * 3600

    def test_license_persistence(self):
        """Test that licenses persist across instances."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"

            # Create license
            manager1 = SuperfluidManager(storage_path=storage_path)
            license = manager1.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=25.0,
            )
            license_id = license.license_id

            # Load in new instance
            manager2 = SuperfluidManager(storage_path=storage_path)
            loaded = manager2.get_license(license_id)

            assert loaded is not None
            assert loaded.repo_id == "test_repo"
            assert loaded.monthly_cost_usd == 25.0

    @pytest.mark.asyncio
    async def test_activate_stream(self):
        """Test activating a stream."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
            )

            result = await manager.activate_stream(license.license_id)

            assert result["status"] == "active"
            assert license.status == StreamStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_stop_stream(self):
        """Test stopping a stream."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
            )
            await manager.activate_stream(license.license_id)

            result = await manager.stop_stream(license.license_id)

            assert result["status"] == "stopped"
            assert license.status == StreamStatus.STOPPED
            assert license.stop_time is not None

    def test_check_access_active(self):
        """Test access check for active stream."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
            )

            # Should have no access when pending
            assert manager.check_access(license.license_id) is False

            # Activate
            license.status = StreamStatus.ACTIVE
            manager._save_licenses()

            # Should have access when active
            assert manager.check_access(license.license_id) is True

    def test_check_access_grace_period(self):
        """Test access check during grace period."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
                grace_period_hours=24,
            )

            # Activate then stop
            license.status = StreamStatus.STOPPED
            license.stop_time = datetime.utcnow()
            manager._save_licenses()

            # Should have access during grace period
            assert manager.check_access(license.license_id) is True

    def test_check_access_grace_expired(self):
        """Test access check after grace period expires."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
                grace_period_hours=1,
            )

            # Stop with past time (grace expired)
            license.status = StreamStatus.STOPPED
            license.stop_time = datetime.utcnow() - timedelta(hours=2)
            manager._save_licenses()

            # Should NOT have access
            assert manager.check_access(license.license_id) is False

    def test_get_licenses_for_repo(self):
        """Test getting licenses by repo."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            # Create multiple licenses
            manager.create_streaming_license("repo1", "0xA", "0xS", 10.0)
            manager.create_streaming_license("repo1", "0xB", "0xS", 20.0)
            manager.create_streaming_license("repo2", "0xC", "0xS", 30.0)

            repo1_licenses = manager.get_licenses_for_repo("repo1")
            repo2_licenses = manager.get_licenses_for_repo("repo2")

            assert len(repo1_licenses) == 2
            assert len(repo2_licenses) == 1

    def test_get_licenses_for_buyer(self):
        """Test getting licenses by buyer."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            # Create multiple licenses
            manager.create_streaming_license("repo1", "0xBuyer1", "0xS", 10.0)
            manager.create_streaming_license("repo2", "0xBuyer1", "0xS", 20.0)
            manager.create_streaming_license("repo3", "0xBuyer2", "0xS", 30.0)

            buyer1_licenses = manager.get_licenses_for_buyer("0xBuyer1")
            buyer2_licenses = manager.get_licenses_for_buyer("0xBuyer2")

            assert len(buyer1_licenses) == 2
            assert len(buyer2_licenses) == 1

    def test_get_stats(self):
        """Test getting statistics."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)

            # Create licenses with different statuses
            l1 = manager.create_streaming_license("repo1", "0xA", "0xS", 10.0)
            l2 = manager.create_streaming_license("repo2", "0xB", "0xS", 20.0)
            l3 = manager.create_streaming_license("repo3", "0xC", "0xS", 30.0)

            l1.status = StreamStatus.ACTIVE
            l2.status = StreamStatus.ACTIVE
            l3.status = StreamStatus.STOPPED
            manager._save_licenses()

            stats = manager.get_stats()

            assert stats["total_licenses"] == 3
            assert stats["active_streams"] == 2
            assert stats["stopped_streams"] == 1
            assert stats["total_monthly_revenue_usd"] == 30.0  # 10 + 20

    def test_generate_stream_proposal(self):
        """Test proposal generation."""
        manager = SuperfluidManager()

        proposal = manager.generate_stream_proposal(
            repo_name="MyRepo",
            monthly_price=50.0,
            token="USDCx",
        )

        assert "MyRepo" in proposal
        assert "$50.00" in proposal
        assert "USDCx" in proposal
        assert "streaming" in proposal.lower()


class TestStreamAccessController:
    """Test cases for StreamAccessController."""

    @pytest.mark.asyncio
    async def test_check_access(self):
        """Test access check through controller."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)
            controller = StreamAccessController(manager)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
            )

            # Activate
            license.status = StreamStatus.ACTIVE
            manager._save_licenses()

            result = await controller.check_access(license.license_id)

            assert result["has_access"] is True
            assert result["reason"] == "active_stream"

    @pytest.mark.asyncio
    async def test_check_access_by_buyer(self):
        """Test access check by buyer address."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)
            controller = StreamAccessController(manager)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
            )
            license.status = StreamStatus.ACTIVE
            manager._save_licenses()

            # Check by buyer
            result = await controller.check_access_by_buyer("test_repo", "0xBuyer")

            assert result["has_access"] is True

            # Check non-existent buyer
            result2 = await controller.check_access_by_buyer("test_repo", "0xOther")

            assert result2["has_access"] is False
            assert result2["reason"] == "no_license"

    @pytest.mark.asyncio
    async def test_grant_access(self):
        """Test granting access."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)
            controller = StreamAccessController(manager)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
            )

            grant = await controller.grant_access(license.license_id, AccessLevel.FULL)

            assert grant.license_id == license.license_id
            assert grant.access_level == AccessLevel.FULL
            assert grant.is_streaming is True

    @pytest.mark.asyncio
    async def test_revoke_access(self):
        """Test revoking access."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)
            controller = StreamAccessController(manager)

            license = manager.create_streaming_license(
                repo_id="test_repo",
                buyer_address="0xBuyer",
                seller_address="0xSeller",
                monthly_price_usd=100.0,
            )
            license.status = StreamStatus.ACTIVE
            manager._save_licenses()

            await controller.grant_access(license.license_id)

            # Revoke
            result = await controller.revoke_access(license.license_id)

            assert result is True
            assert license.status == StreamStatus.REVOKED

    @pytest.mark.asyncio
    async def test_get_access_summary(self):
        """Test getting access summary."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "licenses.json"
            manager = SuperfluidManager(storage_path=storage_path)
            controller = StreamAccessController(manager)

            # Create licenses
            l1 = manager.create_streaming_license("repo1", "0xA", "0xS", 10.0)
            l2 = manager.create_streaming_license("repo1", "0xB", "0xS", 20.0)
            l1.status = StreamStatus.ACTIVE
            l2.status = StreamStatus.STOPPED
            manager._save_licenses()

            summary = await controller.get_access_summary("repo1")

            assert summary["total_licenses"] == 2
            assert summary["active_streams"] == 1
            assert summary["stopped_streams"] == 1
            assert summary["monthly_recurring_revenue"] == 10.0


class TestStreamingLicense:
    """Test cases for StreamingLicense dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        license = StreamingLicense(
            license_id="sl_test123",
            repo_id="repo_abc",
            buyer_address="0xbuyer",
            seller_address="0xseller",
            flow_rate=1000000,
            token="USDCx",
            monthly_cost_usd=50.0,
            start_time=datetime.utcnow(),
            grace_period_seconds=86400,
            status=StreamStatus.ACTIVE,
        )

        data = license.to_dict()

        assert data["license_id"] == "sl_test123"
        assert data["status"] == "active"
        assert "start_time" in data

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "license_id": "sl_test123",
            "repo_id": "repo_abc",
            "buyer_address": "0xbuyer",
            "seller_address": "0xseller",
            "flow_rate": 1000000,
            "token": "USDCx",
            "monthly_cost_usd": 50.0,
            "start_time": datetime.utcnow().isoformat(),
            "grace_period_seconds": 86400,
            "status": "active",
            "tx_hash": None,
            "stop_time": None,
            "metadata": None,
        }

        license = StreamingLicense.from_dict(data)

        assert license.license_id == "sl_test123"
        assert license.status == StreamStatus.ACTIVE
        assert isinstance(license.start_time, datetime)
