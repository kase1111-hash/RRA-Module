# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""RRA Security module."""

from rra.security.webhook_auth import (
    WebhookSecurity,
    RateLimiter,
    NonceTracker,
    CredentialEncryption,
    validate_callback_url,
    verify_webhook_signature,
    webhook_security,
    rate_limiter,
)

from rra.security.api_auth import (
    APIKeyManager,
    api_key_manager,
    get_api_key,
    require_auth,
    require_admin,
    require_scope,
    optional_auth,
)

__all__ = [
    # Webhook security
    'WebhookSecurity',
    'RateLimiter',
    'NonceTracker',
    'CredentialEncryption',
    'validate_callback_url',
    'verify_webhook_signature',
    'webhook_security',
    'rate_limiter',
    # API authentication
    'APIKeyManager',
    'api_key_manager',
    'get_api_key',
    'require_auth',
    'require_admin',
    'require_scope',
    'optional_auth',
]
