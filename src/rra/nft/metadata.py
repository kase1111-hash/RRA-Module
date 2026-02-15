# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
NFT metadata assembly and IPFS upload for license NFTs.

Builds ERC-721 compatible metadata JSON with dynamic SVG images
and uploads both image and metadata to IPFS.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from rra.nft.image_generator import (
    generate_license_svg,
    LICENSE_TYPE_NAMES,
    _format_address,
)
from rra.storage.encrypted_ipfs import (
    EncryptedIPFSStorage,
    StorageConfig,
    StorageProvider,
)

logger = logging.getLogger(__name__)


@dataclass
class LicenseMetadataInput:
    """Input data for building license NFT metadata."""

    repo_name: str
    repo_url: str
    license_type: int  # 0=PER_SEAT, 1=SUBSCRIPTION, 2=PERPETUAL, 3=TRIAL
    licensee_address: str
    price_wei: int = 0
    token_id: Optional[int] = None
    max_seats: int = 0
    allow_forks: bool = True
    royalty_basis_points: int = 0
    duration_seconds: int = 0
    issued_at: Optional[str] = None

    @property
    def license_type_name(self) -> str:
        return LICENSE_TYPE_NAMES.get(self.license_type, f"Type {self.license_type}")

    @property
    def price_display(self) -> str:
        if self.price_wei == 0:
            return "Free"
        eth = self.price_wei / 1e18
        if eth == int(eth):
            return f"{int(eth)} ETH"
        return f"{eth:.6g} ETH"

    @property
    def royalty_display(self) -> str:
        pct = self.royalty_basis_points / 100
        if pct == int(pct):
            return f"{int(pct)}%"
        return f"{pct:.2g}%"

    @property
    def duration_display(self) -> str:
        if self.duration_seconds == 0:
            return "Perpetual"
        days = self.duration_seconds // 86400
        if days >= 365:
            years = days // 365
            return f"{years} year{'s' if years != 1 else ''}"
        if days >= 30:
            months = days // 30
            return f"{months} month{'s' if months != 1 else ''}"
        return f"{days} day{'s' if days != 1 else ''}"


class NFTMetadataBuilder:
    """
    Builds ERC-721 metadata and uploads to IPFS for license NFTs.

    Generates a dynamic SVG image per license, uploads the image to IPFS,
    assembles a standards-compliant metadata JSON, and uploads that too.
    Returns the final metadata URI for use as the token's tokenURI.
    """

    def __init__(
        self,
        storage: Optional[EncryptedIPFSStorage] = None,
    ):
        """
        Initialize metadata builder.

        Args:
            storage: IPFS storage instance. Defaults to mock provider.
        """
        self.storage = storage or EncryptedIPFSStorage(
            config=StorageConfig(
                provider=StorageProvider.MOCK,
                api_url="",
            )
        )

    def build(
        self,
        license_info: LicenseMetadataInput,
        custom_image: Optional[bytes] = None,
    ) -> str:
        """
        Build metadata and upload to IPFS.

        Args:
            license_info: License data for metadata generation
            custom_image: Optional custom image bytes (PNG/SVG).
                If not provided, a branded SVG is generated.

        Returns:
            IPFS URI for the metadata JSON (e.g. "ipfs://Qm...")

        Raises:
            StorageUploadError: If IPFS upload fails
        """
        # 1. Generate or use custom image
        if custom_image:
            image_bytes = custom_image
            image_filename = "license-image.png"
        else:
            svg = generate_license_svg(
                repo_name=license_info.repo_name,
                license_type=license_info.license_type_name,
                price=license_info.price_display,
                licensee_short=_format_address(license_info.licensee_address),
                token_id=f"#{license_info.token_id}" if license_info.token_id is not None else "",
                issued_date=license_info.issued_at or "",
            )
            image_bytes = svg.encode("utf-8")
            image_filename = "license-image.svg"

        # 2. Upload image to IPFS
        logger.info("Uploading license NFT image to IPFS")
        image_result = self.storage.upload_raw(image_bytes, filename=image_filename)
        if not image_result.success:
            raise RuntimeError(f"Image upload failed: {image_result.error}")
        image_uri = image_result.uri
        logger.info(f"Image uploaded: {image_uri}")

        # 3. Build metadata JSON
        metadata = self.build_metadata_dict(license_info, image_uri)
        metadata_bytes = json.dumps(metadata, indent=2).encode("utf-8")

        # 4. Upload metadata to IPFS
        logger.info("Uploading license NFT metadata to IPFS")
        metadata_result = self.storage.upload_raw(metadata_bytes, filename="metadata.json")
        if not metadata_result.success:
            raise RuntimeError(f"Metadata upload failed: {metadata_result.error}")
        logger.info(f"Metadata uploaded: {metadata_result.uri}")

        return metadata_result.uri

    def build_metadata_dict(
        self,
        license_info: LicenseMetadataInput,
        image_uri: str,
    ) -> dict:
        """
        Assemble ERC-721 / OpenSea compatible metadata dict.

        Args:
            license_info: License data
            image_uri: IPFS URI of the license image

        Returns:
            Metadata dict ready for JSON serialization
        """
        issued_at = license_info.issued_at or datetime.utcnow().isoformat()

        attributes = [
            {"trait_type": "License Type", "value": license_info.license_type_name},
            {"trait_type": "Duration", "value": license_info.duration_display},
            {"trait_type": "Max Seats", "value": license_info.max_seats if license_info.max_seats > 0 else "Unlimited"},
            {"trait_type": "Allow Forks", "value": "Yes" if license_info.allow_forks else "No"},
            {"trait_type": "Royalty", "value": license_info.royalty_display, "display_type": "string"},
            {"trait_type": "Price", "value": license_info.price_display},
            {"trait_type": "Software", "value": license_info.repo_name},
            {"trait_type": "Issued At", "value": issued_at, "display_type": "date"},
        ]

        if license_info.token_id is not None:
            attributes.append(
                {"trait_type": "Token ID", "value": license_info.token_id, "display_type": "number"}
            )

        metadata = {
            "name": f"{license_info.repo_name} License",
            "description": (
                f"License NFT for {license_info.repo_name}. "
                f"{license_info.license_type_name} license "
                f"issued to {_format_address(license_info.licensee_address)}. "
                f"Powered by Story Protocol."
            ),
            "image": image_uri,
            "external_url": license_info.repo_url,
            "attributes": attributes,
            "background_color": "1a1a2e",
        }

        return metadata
