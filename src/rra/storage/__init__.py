# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Storage module for encrypted evidence on decentralized storage.

Includes compression utilities for reducing storage and bandwidth costs.
"""

from .encrypted_ipfs import (
    EncryptedIPFSStorage,
    StorageResult,
    StorageProvider,
    create_storage,
)

from .compression import (
    compress,
    decompress,
    compress_json,
    decompress_json,
    CompressionConfig,
    CompressionAlgorithm,
    CompressionResult,
    StreamingCompressor,
    is_gzip_compressed,
)

__all__ = [
    # Storage
    "EncryptedIPFSStorage",
    "StorageResult",
    "StorageProvider",
    "create_storage",
    # Compression
    "compress",
    "decompress",
    "compress_json",
    "decompress_json",
    "CompressionConfig",
    "CompressionAlgorithm",
    "CompressionResult",
    "StreamingCompressor",
    "is_gzip_compressed",
]
