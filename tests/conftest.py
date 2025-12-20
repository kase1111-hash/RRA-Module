# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Pytest configuration and shared fixtures for RRA tests.
"""

import os
import pytest


def pytest_configure(config):
    """
    Configure pytest environment before tests run.

    Sets up development mode for API authentication.
    """
    # Enable development mode for API tests
    # This allows any non-empty API key to pass authentication
    os.environ["RRA_DEV_MODE"] = "true"

    # Set a default API key for tests
    os.environ["RRA_API_KEY"] = "test-api-key-for-testing"


@pytest.fixture(scope="session")
def api_headers():
    """Provide standard API headers for authenticated requests."""
    return {"X-API-Key": os.environ.get("RRA_API_KEY", "test-api-key-for-testing")}


@pytest.fixture
def authenticated_client():
    """
    Create an authenticated test client wrapper.

    Returns a TestClient that automatically includes the X-API-Key header.
    """
    from fastapi.testclient import TestClient
    from rra.api.server import app

    class AuthenticatedTestClient(TestClient):
        """TestClient wrapper that adds authentication headers."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._auth_headers = {
                "X-API-Key": os.environ.get("RRA_API_KEY", "test-api-key-for-testing")
            }

        def request(self, method, url, **kwargs):
            headers = kwargs.pop("headers", {})
            headers.update(self._auth_headers)
            return super().request(method, url, headers=headers, **kwargs)

    return AuthenticatedTestClient(app)
