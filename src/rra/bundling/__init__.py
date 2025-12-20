# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Multi-repo bundling for RRA Module.

Package multiple repositories into licensable bundles with discounts.
"""

from .repo_bundle import (
    BundleType,
    DiscountType,
    BundleDiscount,
    BundledRepo,
    RepoBundle,
    BundleManager,
    bundle_manager,
    get_bundle_manager,
)

__all__ = [
    "BundleType",
    "DiscountType",
    "BundleDiscount",
    "BundledRepo",
    "RepoBundle",
    "BundleManager",
    "bundle_manager",
    "get_bundle_manager",
]
