# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Smart contract templates and blockchain integration."""

from rra.contracts.license_nft import LicenseNFTContract
from rra.contracts.manager import ContractManager
from rra.contracts.artifacts import (
    ArtifactLoader,
    ContractArtifact,
    load_contract,
    get_abi,
    get_bytecode,
    is_compiled,
    available_contracts,
)
from rra.contracts.story_protocol import StoryProtocolClient, IPAssetMetadata, PILTerms

__all__ = [
    # Core contract interfaces
    "LicenseNFTContract",
    "ContractManager",
    # Artifact loading
    "ArtifactLoader",
    "ContractArtifact",
    "load_contract",
    "get_abi",
    "get_bytecode",
    "is_compiled",
    "available_contracts",
    # Story Protocol
    "StoryProtocolClient",
    "IPAssetMetadata",
    "PILTerms",
]
