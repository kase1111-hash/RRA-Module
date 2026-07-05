# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for Deep Links service."""

from pathlib import Path
from tempfile import TemporaryDirectory

from rra.services.deep_links import DeepLinkService


class TestDeepLinkService:
    """Test cases for DeepLinkService."""

    def test_generate_repo_id(self):
        """Test repo ID generation is stable and consistent."""
        service = DeepLinkService()

        # Same URL should always produce same ID
        url1 = "https://github.com/user/repo"
        id1 = service.generate_repo_id(url1)
        id2 = service.generate_repo_id(url1)
        assert id1 == id2

        # ID should be 12 characters
        assert len(id1) == 12

        # Normalized URLs should produce same ID
        url_variations = [
            "https://github.com/user/repo",
            "https://github.com/user/repo.git",
            "https://github.com/USER/REPO",
            "https://github.com/user/repo/",
        ]
        ids = [service.generate_repo_id(url) for url in url_variations]
        assert len(set(ids)) == 1

    def test_different_repos_different_ids(self):
        """Test different repos get different IDs."""
        service = DeepLinkService()

        id1 = service.generate_repo_id("https://github.com/user/repo1")
        id2 = service.generate_repo_id("https://github.com/user/repo2")

        assert id1 != id2

    def test_get_purchase_url(self):
        """Test purchase URL generation."""
        service = DeepLinkService(base_url="https://test.io/buy.html")
        url = service.get_purchase_url("https://github.com/user/repo")

        assert url.startswith("https://test.io/buy.html?")
        repo_id = service.generate_repo_id("https://github.com/user/repo")
        assert f"repo={repo_id}" in url
        assert "network=mainnet" in url

    def test_get_purchase_url_with_registered_ip_asset(self):
        """Registered on-chain details should be embedded in purchase links."""
        with TemporaryDirectory() as tmpdir:
            mappings_path = Path(tmpdir) / "mappings.json"
            service = DeepLinkService(
                base_url="https://test.io/buy.html", mappings_path=mappings_path
            )

            service.register_repo(
                "https://github.com/user/repo",
                metadata={
                    "ip_asset_id": "0x" + "f" * 40,
                    "license_terms_id": 28437,
                    "network": "mainnet",
                },
            )

            url = service.get_purchase_url("https://github.com/user/repo")
            assert "ipAsset=0x" in url
            assert "terms=28437" in url
            assert "network=mainnet" in url

    def test_get_license_url(self):
        """Test license tier URL generation."""
        service = DeepLinkService(base_url="https://test.io/buy.html")
        url = service.get_license_url("https://github.com/user/repo", "enterprise")

        assert "tier=enterprise" in url
        assert url.startswith("https://test.io/buy.html?")

    def test_get_explorer_url(self):
        """Explorer URL requires a registered IP asset."""
        with TemporaryDirectory() as tmpdir:
            mappings_path = Path(tmpdir) / "mappings.json"
            service = DeepLinkService(mappings_path=mappings_path)

            # Unregistered repo has no explorer URL
            assert service.get_explorer_url("https://github.com/user/repo") is None

            ip_asset = "0x" + "a" * 40
            service.register_repo(
                "https://github.com/user/repo",
                metadata={"ip_asset_id": ip_asset, "network": "mainnet"},
            )

            url = service.get_explorer_url("https://github.com/user/repo")
            assert url == f"https://explorer.story.foundation/ipa/{ip_asset}"

    def test_generate_badge_markdown(self):
        """Test markdown badge generation."""
        service = DeepLinkService(base_url="https://test.io/buy.html")
        badge = service.generate_badge_markdown(
            "https://github.com/user/repo", style="flat", label="License This"
        )

        assert "[![License This]" in badge
        assert "shields.io" in badge
        assert "test.io/buy.html?" in badge

    def test_generate_badge_html(self):
        """Test HTML badge generation."""
        service = DeepLinkService(base_url="https://test.io/buy.html")
        badge = service.generate_badge_html(
            "https://github.com/user/repo", style="flat", label="License This"
        )

        assert "<a href=" in badge
        assert "<img src=" in badge
        assert "test.io/buy.html?" in badge

    def test_generate_embed_button(self):
        """Test embeddable buy-button generation."""
        service = DeepLinkService(base_url="https://test.io/buy.html")
        embed = service.generate_embed_button("https://github.com/user/repo")

        assert "<a href=" in embed
        assert "test.io/buy.html?" in embed
        assert "Buy License" in embed

    def test_generate_qr_code_url(self):
        """Test QR code URL generation."""
        service = DeepLinkService(base_url="https://test.io/buy.html")
        qr_url = service.generate_qr_code_url("https://github.com/user/repo", size=300)

        assert "qrserver.com" in qr_url
        assert "300x300" in qr_url

    def test_get_all_links(self):
        """Test getting all links for a repo."""
        service = DeepLinkService(base_url="https://test.io/buy.html")
        links = service.get_all_links("https://github.com/user/repo")

        assert "repo_id" in links
        assert "purchase_page" in links
        assert "explorer_url" in links
        assert "license_standard" in links
        assert "license_premium" in links
        assert "license_enterprise" in links
        assert "qr_code" in links
        assert "badge_markdown" in links
        assert "embed_button" in links


class TestDeepLinkServicePersistence:
    """Test cases for DeepLinkService persistence."""

    def test_register_and_resolve(self):
        """Test registering and resolving a repo."""
        with TemporaryDirectory() as tmpdir:
            mappings_path = Path(tmpdir) / "mappings.json"
            service = DeepLinkService(mappings_path=mappings_path)

            # Register
            repo_id = service.register_repo(
                "https://github.com/user/repo", metadata={"name": "repo", "owner": "user"}
            )

            assert len(repo_id) == 12

            # Resolve
            mapping = service.resolve_repo_id(repo_id)

            assert mapping is not None
            assert mapping["repo_url"] == "https://github.com/user/repo"
            assert mapping["name"] == "repo"
            assert mapping["owner"] == "user"
            assert mapping["active"] is True

    def test_persistence_across_instances(self):
        """Test that mappings persist across service instances."""
        with TemporaryDirectory() as tmpdir:
            mappings_path = Path(tmpdir) / "mappings.json"

            # First instance - register
            service1 = DeepLinkService(mappings_path=mappings_path)
            repo_id = service1.register_repo("https://github.com/user/repo")

            # Second instance - resolve
            service2 = DeepLinkService(mappings_path=mappings_path)
            mapping = service2.resolve_repo_id(repo_id)

            assert mapping is not None
            assert mapping["repo_url"] == "https://github.com/user/repo"

    def test_resolve_unregistered(self):
        """Test resolving an unregistered repo ID returns None."""
        with TemporaryDirectory() as tmpdir:
            mappings_path = Path(tmpdir) / "mappings.json"
            service = DeepLinkService(mappings_path=mappings_path)

            mapping = service.resolve_repo_id("nonexistent1")
            assert mapping is None

    def test_get_stats(self):
        """Test getting statistics."""
        with TemporaryDirectory() as tmpdir:
            mappings_path = Path(tmpdir) / "mappings.json"
            service = DeepLinkService(mappings_path=mappings_path)

            # Register some repos
            service.register_repo("https://github.com/user/repo1")
            service.register_repo(
                "https://github.com/user/repo2",
                metadata={"ip_asset_id": "0x" + "b" * 40},
            )

            stats = service.get_stats()

            assert stats["total_registered"] == 2
            assert stats["active"] == 2
            assert stats["inactive"] == 0
            assert stats["with_ip_asset"] == 1


class TestDeepLinkServiceDefaultBaseUrl:
    """Test default base URL behavior."""

    def test_default_base_url(self):
        """Test that default base URL is the hosted purchase page."""
        service = DeepLinkService()
        url = service.get_purchase_url("https://github.com/user/repo")

        assert url.startswith("https://kase1111-hash.github.io/RRA-Module/buy-license.html?")

    def test_custom_base_url(self):
        """Test custom base URL override."""
        service = DeepLinkService(base_url="https://custom.example.com/buy.html")
        url = service.get_purchase_url("https://github.com/user/repo")

        assert url.startswith("https://custom.example.com/buy.html?")

    def test_base_url_trailing_slash_handling(self):
        """Test that trailing slashes in base URL are handled."""
        service = DeepLinkService(base_url="https://example.com/buy.html/")
        url = service.get_purchase_url("https://github.com/user/repo")

        # Should not have a slash immediately before the query string
        assert "/?" not in url
        assert url.startswith("https://example.com/buy.html?")
