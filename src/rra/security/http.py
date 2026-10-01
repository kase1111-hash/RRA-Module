# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Scheme-checked wrapper around ``urllib.request.urlopen``.

``urlopen`` also accepts ``file://`` and other custom schemes, so a
misconfigured or attacker-influenced endpoint URL could read local files.
Outbound HTTP calls go through :func:`safe_urlopen`, which only allows
http and https.
"""

import urllib.error
import urllib.request
from typing import Any, Union

ALLOWED_SCHEMES = frozenset({"http", "https"})


def safe_urlopen(request: Union[str, urllib.request.Request], timeout: float) -> Any:
    """
    Open an http(s) URL, refusing any other scheme.

    Raises ``urllib.error.URLError`` for a disallowed scheme so callers'
    existing URLError handling covers it.
    """
    if isinstance(request, str):
        request = urllib.request.Request(request)
    if request.type not in ALLOWED_SCHEMES:
        raise urllib.error.URLError(
            f"Refusing URL with scheme '{request.type}': only http and https are allowed"
        )
    return urllib.request.urlopen(request, timeout=timeout)  # nosec B310 - scheme checked above
