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

from rra.security.logging import (
    SecurityLogger,
    SecurityEventType,
    SecurityEventSeverity,
    security_logger,
    log_auth_success,
    log_auth_failure,
    log_rate_limit_exceeded,
    log_webhook_signature_invalid,
    log_ssrf_blocked,
    log_injection_blocked,
    log_suspicious_activity,
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
    # Security logging
    'SecurityLogger',
    'SecurityEventType',
    'SecurityEventSeverity',
    'security_logger',
    'log_auth_success',
    'log_auth_failure',
    'log_rate_limit_exceeded',
    'log_webhook_signature_invalid',
    'log_ssrf_blocked',
    'log_injection_blocked',
    'log_suspicious_activity',
]
