# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for NFT metadata generation and image creation.

Covers SVG generation, metadata assembly, and IPFS upload integration.
"""

import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rra.nft.image_generator import (
    generate_license_svg,
    generate_text_logo,
    _format_address,
    _truncate,
    LICENSE_TYPE_NAMES,
)
from rra.nft.metadata import (
    NFTMetadataBuilder,
    LicenseMetadataInput,
)
from rra.storage.encrypted_ipfs import (
    EncryptedIPFSStorage,
    StorageConfig,
    StorageProvider,
)


class TestImageGenerator(unittest.TestCase):
    """Tests for SVG image generation."""

    def test_generate_license_svg_basic(self):
        """Test that SVG is generated with required structure."""
        svg = generate_license_svg(
            repo_name="RRA-Module",
            license_type="Perpetual",
        )
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)
        self.assertIn("RRA-Module", svg)
        self.assertIn("Perpetual", svg)
        self.assertIn("LICENSE NFT", svg)

    def test_generate_license_svg_all_fields(self):
        """Test SVG with all dynamic fields populated."""
        svg = generate_license_svg(
            repo_name="MyProject",
            license_type="Subscription",
            price="0.1 ETH",
            licensee_short="0x1234...abcd",
            token_id="#42",
            issued_date="2025-06-15",
        )
        self.assertIn("MyProject", svg)
        self.assertIn("Subscription", svg)
        self.assertIn("0.1 ETH", svg)
        self.assertIn("0x1234...abcd", svg)
        self.assertIn("#42", svg)
        self.assertIn("2025-06-15", svg)

    def test_generate_license_svg_escapes_special_chars(self):
        """Test that special XML characters are escaped."""
        svg = generate_license_svg(
            repo_name="Foo<Bar>&Baz",
            license_type='Type"One',
        )
        self.assertNotIn("<Bar>", svg)
        self.assertIn("&amp;", svg)
        self.assertIn("&lt;", svg)

    def test_generate_license_svg_truncates_long_names(self):
        """Test that excessively long names are truncated."""
        svg = generate_license_svg(
            repo_name="A" * 50,
            license_type="Perpetual",
        )
        # Should be truncated to 20 chars + "..."
        self.assertNotIn("A" * 50, svg)
        self.assertIn("...", svg)

    def test_generate_license_svg_valid_xml(self):
        """Test that generated SVG is valid XML."""
        import xml.etree.ElementTree as ET

        svg = generate_license_svg(
            repo_name="TestRepo",
            license_type="Per-Seat",
            price="1 ETH",
        )
        # Should parse without error
        ET.fromstring(svg)

    def test_generate_text_logo(self):
        """Test fallback text logo generation."""
        svg = generate_text_logo("MyApp")
        self.assertIn("<svg", svg)
        self.assertIn("MyApp", svg)
        self.assertIn("LICENSE NFT", svg)

    def test_generate_text_logo_custom_dimensions(self):
        """Test text logo with custom dimensions."""
        svg = generate_text_logo("Test", width=200, height=200)
        self.assertIn('viewBox="0 0 200 200"', svg)

    def test_generate_text_logo_valid_xml(self):
        """Test that text logo is valid XML."""
        import xml.etree.ElementTree as ET

        svg = generate_text_logo("Hello")
        ET.fromstring(svg)


class TestHelpers(unittest.TestCase):
    """Tests for helper functions."""

    def test_format_address_full(self):
        """Test address formatting with full address."""
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        self.assertEqual(_format_address(addr), "0x1234...5678")

    def test_format_address_short(self):
        """Test address formatting with short string."""
        self.assertEqual(_format_address("0x12"), "0x12")

    def test_truncate_short(self):
        """Test truncate with short text."""
        self.assertEqual(_truncate("hello", 10), "hello")

    def test_truncate_long(self):
        """Test truncate with long text."""
        result = _truncate("a" * 30, 10)
        self.assertEqual(len(result), 10)
        self.assertTrue(result.endswith("..."))

    def test_license_type_names(self):
        """Test license type name mapping."""
        self.assertEqual(LICENSE_TYPE_NAMES[0], "Per-Seat")
        self.assertEqual(LICENSE_TYPE_NAMES[1], "Subscription")
        self.assertEqual(LICENSE_TYPE_NAMES[2], "Perpetual")
        self.assertEqual(LICENSE_TYPE_NAMES[3], "Trial")


class TestLicenseMetadataInput(unittest.TestCase):
    """Tests for LicenseMetadataInput dataclass."""

    def _make_input(self, **kwargs):
        defaults = {
            "repo_name": "RRA-Module",
            "repo_url": "https://github.com/kase1111-hash/RRA-Module",
            "license_type": 2,
            "licensee_address": "0x1234567890abcdef1234567890abcdef12345678",
        }
        defaults.update(kwargs)
        return LicenseMetadataInput(**defaults)

    def test_license_type_name(self):
        """Test license type name property."""
        inp = self._make_input(license_type=0)
        self.assertEqual(inp.license_type_name, "Per-Seat")

        inp = self._make_input(license_type=2)
        self.assertEqual(inp.license_type_name, "Perpetual")

    def test_license_type_name_unknown(self):
        """Test unknown license type fallback."""
        inp = self._make_input(license_type=99)
        self.assertEqual(inp.license_type_name, "Type 99")

    def test_price_display_free(self):
        """Test price display for free license."""
        inp = self._make_input(price_wei=0)
        self.assertEqual(inp.price_display, "Free")

    def test_price_display_eth(self):
        """Test price display for ETH amount."""
        inp = self._make_input(price_wei=50000000000000000)  # 0.05 ETH
        self.assertEqual(inp.price_display, "0.05 ETH")

    def test_price_display_whole_eth(self):
        """Test price display for whole ETH."""
        inp = self._make_input(price_wei=1000000000000000000)  # 1 ETH
        self.assertEqual(inp.price_display, "1 ETH")

    def test_royalty_display(self):
        """Test royalty display."""
        inp = self._make_input(royalty_basis_points=900)
        self.assertEqual(inp.royalty_display, "9%")

    def test_royalty_display_fractional(self):
        """Test fractional royalty display."""
        inp = self._make_input(royalty_basis_points=250)
        self.assertEqual(inp.royalty_display, "2.5%")

    def test_duration_display_perpetual(self):
        """Test perpetual duration."""
        inp = self._make_input(duration_seconds=0)
        self.assertEqual(inp.duration_display, "Perpetual")

    def test_duration_display_years(self):
        """Test year-based duration."""
        inp = self._make_input(duration_seconds=365 * 86400)
        self.assertEqual(inp.duration_display, "1 year")

    def test_duration_display_months(self):
        """Test month-based duration."""
        inp = self._make_input(duration_seconds=90 * 86400)
        self.assertEqual(inp.duration_display, "3 months")

    def test_duration_display_days(self):
        """Test day-based duration."""
        inp = self._make_input(duration_seconds=7 * 86400)
        self.assertEqual(inp.duration_display, "7 days")


class TestNFTMetadataBuilder(unittest.TestCase):
    """Tests for the NFTMetadataBuilder."""

    def setUp(self):
        """Set up mock storage and builder."""
        self.storage = EncryptedIPFSStorage(
            config=StorageConfig(
                provider=StorageProvider.MOCK,
                api_url="",
            )
        )
        self.builder = NFTMetadataBuilder(storage=self.storage)

    def _make_input(self, **kwargs):
        defaults = {
            "repo_name": "RRA-Module",
            "repo_url": "https://github.com/kase1111-hash/RRA-Module",
            "license_type": 2,
            "licensee_address": "0x1234567890abcdef1234567890abcdef12345678",
            "price_wei": 50000000000000000,
            "token_id": 1,
            "max_seats": 5,
            "allow_forks": True,
            "royalty_basis_points": 900,
            "duration_seconds": 0,
            "issued_at": "2025-06-15T00:00:00",
        }
        defaults.update(kwargs)
        return LicenseMetadataInput(**defaults)

    def test_build_metadata_dict_structure(self):
        """Test that metadata dict has all required ERC-721 fields."""
        license_info = self._make_input()
        metadata = self.builder.build_metadata_dict(license_info, "ipfs://QmFakeImage")

        self.assertIn("name", metadata)
        self.assertIn("description", metadata)
        self.assertIn("image", metadata)
        self.assertIn("external_url", metadata)
        self.assertIn("attributes", metadata)
        self.assertIn("background_color", metadata)

    def test_build_metadata_dict_values(self):
        """Test metadata field values."""
        license_info = self._make_input()
        metadata = self.builder.build_metadata_dict(license_info, "ipfs://QmFakeImage")

        self.assertEqual(metadata["name"], "RRA-Module License")
        self.assertEqual(metadata["image"], "ipfs://QmFakeImage")
        self.assertEqual(metadata["external_url"], "https://github.com/kase1111-hash/RRA-Module")
        self.assertEqual(metadata["background_color"], "1a1a2e")
        self.assertIn("Story Protocol", metadata["description"])

    def test_build_metadata_attributes_complete(self):
        """Test that all license attributes are present."""
        license_info = self._make_input()
        metadata = self.builder.build_metadata_dict(license_info, "ipfs://QmFakeImage")

        attr_types = {a["trait_type"] for a in metadata["attributes"]}
        expected = {
            "License Type",
            "Duration",
            "Max Seats",
            "Allow Forks",
            "Royalty",
            "Price",
            "Software",
            "Issued At",
            "Token ID",
        }
        self.assertEqual(attr_types, expected)

    def test_build_metadata_attribute_values(self):
        """Test specific attribute values."""
        license_info = self._make_input()
        metadata = self.builder.build_metadata_dict(license_info, "ipfs://QmFakeImage")

        attrs = {a["trait_type"]: a["value"] for a in metadata["attributes"]}
        self.assertEqual(attrs["License Type"], "Perpetual")
        self.assertEqual(attrs["Duration"], "Perpetual")
        self.assertEqual(attrs["Max Seats"], 5)
        self.assertEqual(attrs["Allow Forks"], "Yes")
        self.assertEqual(attrs["Royalty"], "9%")
        self.assertEqual(attrs["Software"], "RRA-Module")
        self.assertEqual(attrs["Token ID"], 1)

    def test_build_metadata_no_token_id(self):
        """Test metadata without token_id omits that attribute."""
        license_info = self._make_input(token_id=None)
        metadata = self.builder.build_metadata_dict(license_info, "ipfs://QmFakeImage")

        attr_types = {a["trait_type"] for a in metadata["attributes"]}
        self.assertNotIn("Token ID", attr_types)

    def test_build_metadata_unlimited_seats(self):
        """Test metadata with unlimited seats."""
        license_info = self._make_input(max_seats=0)
        metadata = self.builder.build_metadata_dict(license_info, "ipfs://QmFakeImage")

        attrs = {a["trait_type"]: a["value"] for a in metadata["attributes"]}
        self.assertEqual(attrs["Max Seats"], "Unlimited")

    def test_build_full_integration(self):
        """Test full build pipeline: SVG gen -> IPFS upload -> metadata upload -> URI."""
        license_info = self._make_input()
        uri = self.builder.build(license_info)

        # Should return a mock:// URI
        self.assertTrue(uri.startswith("mock://"))

        # The metadata should be retrievable from mock storage
        # Parse the CID from the URI
        cid = uri.replace("mock://", "")
        self.assertIn(cid, self.storage._mock_storage)

        # Parse the stored metadata
        stored = json.loads(self.storage._mock_storage[cid])
        self.assertEqual(stored["name"], "RRA-Module License")
        self.assertIn("attributes", stored)

        # The image URI should also be a mock:// URI pointing to stored SVG
        image_uri = stored["image"]
        self.assertTrue(image_uri.startswith("mock://"))
        image_cid = image_uri.replace("mock://", "")
        self.assertIn(image_cid, self.storage._mock_storage)

        # Verify the image is valid SVG
        image_data = self.storage._mock_storage[image_cid]
        self.assertIn(b"<svg", image_data)

    def test_build_with_custom_image(self):
        """Test build with custom image bytes."""
        license_info = self._make_input()
        custom_png = b"\x89PNG\r\n\x1a\nfake-image-data"

        uri = self.builder.build(license_info, custom_image=custom_png)

        # Should still produce a valid metadata URI
        self.assertTrue(uri.startswith("mock://"))

        # Verify the custom image was uploaded (not generated SVG)
        cid = uri.replace("mock://", "")
        stored = json.loads(self.storage._mock_storage[cid])
        image_cid = stored["image"].replace("mock://", "")
        self.assertEqual(self.storage._mock_storage[image_cid], custom_png)


class TestUploadRaw(unittest.TestCase):
    """Tests for the upload_raw method on EncryptedIPFSStorage."""

    def setUp(self):
        self.storage = EncryptedIPFSStorage(
            config=StorageConfig(
                provider=StorageProvider.MOCK,
                api_url="",
            )
        )

    def test_upload_raw_success(self):
        """Test successful raw upload to mock storage."""
        data = b"hello world"
        result = self.storage.upload_raw(data, filename="test.txt")

        self.assertTrue(result.success)
        self.assertTrue(result.uri.startswith("mock://"))
        self.assertEqual(result.size_bytes, len(data))
        self.assertEqual(result.provider, StorageProvider.MOCK)

    def test_upload_raw_retrievable(self):
        """Test that uploaded data is retrievable."""
        data = b'{"test": true}'
        result = self.storage.upload_raw(data)
        cid = result.uri.replace("mock://", "")
        self.assertEqual(self.storage._mock_storage[cid], data)

    def test_upload_raw_empty_data_raises(self):
        """Test that empty data raises ValidationError."""
        from rra.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.storage.upload_raw(b"")

    def test_upload_raw_metadata_contains_filename(self):
        """Test that result metadata includes filename."""
        result = self.storage.upload_raw(b"data", filename="image.svg")
        self.assertEqual(result.metadata.get("filename"), "image.svg")


if __name__ == "__main__":
    unittest.main()
