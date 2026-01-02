# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham

"""
Compression utilities for RRA storage and upload pipeline.

Provides gzip compression for:
1. IPFS/Arweave uploads - reduce storage costs
2. Knowledge base files - reduce disk space
3. API responses - reduce bandwidth

Compression is optional and configurable per operation.
"""

import gzip
import io
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class CompressionAlgorithm(str, Enum):
    """Supported compression algorithms."""

    NONE = "none"
    GZIP = "gzip"
    # Future: ZSTD, LZ4, BROTLI


@dataclass
class CompressionConfig:
    """Configuration for compression operations."""

    algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    level: int = 6  # gzip level 1-9 (6 is default, good balance)
    min_size: int = 1024  # Minimum bytes to compress (skip small data)
    enabled: bool = True

    def __post_init__(self):
        """Validate compression level."""
        if not 1 <= self.level <= 9:
            raise ValueError(f"Compression level must be 1-9, got {self.level}")


@dataclass
class CompressionResult:
    """Result of a compression operation."""

    original_size: int
    compressed_size: int
    algorithm: CompressionAlgorithm
    was_compressed: bool
    compression_ratio: float = field(init=False)

    def __post_init__(self):
        """Calculate compression ratio."""
        if self.original_size > 0 and self.was_compressed:
            self.compression_ratio = 1 - (self.compressed_size / self.original_size)
        else:
            self.compression_ratio = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "algorithm": self.algorithm.value,
            "was_compressed": self.was_compressed,
            "compression_ratio": round(self.compression_ratio, 4),
            "savings_bytes": (
                self.original_size - self.compressed_size if self.was_compressed else 0
            ),
        }


# Magic bytes for detecting compression
GZIP_MAGIC = b"\x1f\x8b"


def is_gzip_compressed(data: bytes) -> bool:
    """
    Check if data is gzip compressed by examining magic bytes.

    Args:
        data: Bytes to check

    Returns:
        True if data appears to be gzip compressed
    """
    return len(data) >= 2 and data[:2] == GZIP_MAGIC


def compress(
    data: bytes,
    config: Optional[CompressionConfig] = None,
) -> Tuple[bytes, CompressionResult]:
    """
    Compress data using the configured algorithm.

    Args:
        data: Raw bytes to compress
        config: Compression configuration (defaults to gzip level 6)

    Returns:
        Tuple of (compressed_data, compression_result)

    Example:
        >>> data = b"Hello World" * 1000
        >>> compressed, result = compress(data)
        >>> print(f"Saved {result.compression_ratio:.1%}")
        Saved 99.2%
    """
    config = config or CompressionConfig()
    original_size = len(data)

    # Skip compression if disabled or data is too small
    if not config.enabled or original_size < config.min_size:
        logger.debug(
            f"Skipping compression: enabled={config.enabled}, "
            f"size={original_size}, min={config.min_size}"
        )
        return data, CompressionResult(
            original_size=original_size,
            compressed_size=original_size,
            algorithm=CompressionAlgorithm.NONE,
            was_compressed=False,
        )

    # Skip if already compressed
    if is_gzip_compressed(data):
        logger.debug("Data already compressed, skipping")
        return data, CompressionResult(
            original_size=original_size,
            compressed_size=original_size,
            algorithm=CompressionAlgorithm.GZIP,
            was_compressed=False,
        )

    if config.algorithm == CompressionAlgorithm.NONE:
        return data, CompressionResult(
            original_size=original_size,
            compressed_size=original_size,
            algorithm=CompressionAlgorithm.NONE,
            was_compressed=False,
        )

    if config.algorithm == CompressionAlgorithm.GZIP:
        compressed = gzip.compress(data, compresslevel=config.level)
        compressed_size = len(compressed)

        # Only use compressed version if it's actually smaller
        if compressed_size >= original_size:
            logger.debug(f"Compression not beneficial: {original_size} -> {compressed_size}")
            return data, CompressionResult(
                original_size=original_size,
                compressed_size=original_size,
                algorithm=CompressionAlgorithm.NONE,
                was_compressed=False,
            )

        logger.debug(
            f"Compressed {original_size} -> {compressed_size} "
            f"({(1 - compressed_size / original_size):.1%} reduction)"
        )
        return compressed, CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            algorithm=CompressionAlgorithm.GZIP,
            was_compressed=True,
        )

    raise ValueError(f"Unsupported compression algorithm: {config.algorithm}")


def decompress(data: bytes, expected_algorithm: Optional[CompressionAlgorithm] = None) -> bytes:
    """
    Decompress data, auto-detecting algorithm if not specified.

    Args:
        data: Compressed bytes
        expected_algorithm: Expected compression algorithm (auto-detect if None)

    Returns:
        Decompressed bytes

    Raises:
        ValueError: If data format is invalid or algorithm unsupported
    """
    # Auto-detect compression
    if expected_algorithm is None:
        if is_gzip_compressed(data):
            expected_algorithm = CompressionAlgorithm.GZIP
        else:
            # Data is not compressed
            return data

    if expected_algorithm == CompressionAlgorithm.NONE:
        return data

    if expected_algorithm == CompressionAlgorithm.GZIP:
        try:
            return gzip.decompress(data)
        except gzip.BadGzipFile as e:
            raise ValueError(f"Invalid gzip data: {e}") from e

    raise ValueError(f"Unsupported compression algorithm: {expected_algorithm}")


def compress_json(
    json_bytes: bytes, config: Optional[CompressionConfig] = None
) -> Tuple[bytes, CompressionResult]:
    """
    Compress JSON data with optimized settings.

    JSON typically compresses very well (80-95% reduction).
    Uses slightly higher compression level for better ratio.

    Args:
        json_bytes: JSON string encoded as bytes
        config: Optional compression config (uses level 7 by default)

    Returns:
        Tuple of (compressed_data, compression_result)
    """
    if config is None:
        config = CompressionConfig(level=7)  # Slightly higher for JSON
    return compress(json_bytes, config)


def decompress_json(data: bytes) -> bytes:
    """
    Decompress JSON data, handling both compressed and uncompressed input.

    Args:
        data: Potentially compressed JSON bytes

    Returns:
        Decompressed JSON bytes
    """
    return decompress(data)


class StreamingCompressor:
    """
    Streaming compressor for large files.

    Use when data is too large to fit in memory at once.
    """

    def __init__(self, config: Optional[CompressionConfig] = None):
        """
        Initialize streaming compressor.

        Args:
            config: Compression configuration
        """
        self.config = config or CompressionConfig()
        self._buffer = io.BytesIO()
        self._compressor: Optional[gzip.GzipFile] = None
        self._total_input = 0
        self._finalized = False

    def write(self, data: bytes) -> None:
        """
        Write data to the compressor.

        Args:
            data: Bytes to compress
        """
        if self._finalized:
            raise RuntimeError("Compressor has been finalized")

        if self._compressor is None:
            self._compressor = gzip.GzipFile(
                mode="wb",
                fileobj=self._buffer,
                compresslevel=self.config.level,
            )

        self._compressor.write(data)
        self._total_input += len(data)

    def finalize(self) -> Tuple[bytes, CompressionResult]:
        """
        Finalize compression and return result.

        Returns:
            Tuple of (compressed_data, compression_result)
        """
        if self._finalized:
            raise RuntimeError("Compressor already finalized")

        self._finalized = True

        if self._compressor:
            self._compressor.close()

        compressed_data = self._buffer.getvalue()

        return compressed_data, CompressionResult(
            original_size=self._total_input,
            compressed_size=len(compressed_data),
            algorithm=self.config.algorithm,
            was_compressed=True,
        )


def get_content_type_for_compression(
    original_content_type: str,
    algorithm: CompressionAlgorithm,
) -> Tuple[str, Optional[str]]:
    """
    Get appropriate content-type and content-encoding for compressed data.

    Args:
        original_content_type: Original MIME type
        algorithm: Compression algorithm used

    Returns:
        Tuple of (content_type, content_encoding)
    """
    if algorithm == CompressionAlgorithm.GZIP:
        return original_content_type, "gzip"
    return original_content_type, None
