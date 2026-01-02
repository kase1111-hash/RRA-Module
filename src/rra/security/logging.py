# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Structured security logging for RRA Module.

Provides consistent, machine-readable security event logging for:
- Authentication events (success/failure)
- Authorization events (access granted/denied)
- Rate limiting events
- Suspicious activity detection
- Webhook operations
- Contract interactions

All logs are JSON-formatted for easy parsing by monitoring tools.
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pathlib import Path


class SecurityEventType(Enum):
    """Types of security events for structured logging."""

    # Authentication
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_TOKEN_EXPIRED = "auth.token_expired"
    AUTH_TOKEN_REVOKED = "auth.token_revoked"

    # Authorization
    AUTHZ_GRANTED = "authz.granted"
    AUTHZ_DENIED = "authz.denied"
    AUTHZ_SCOPE_INSUFFICIENT = "authz.scope_insufficient"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    RATE_LIMIT_WARNING = "rate_limit.warning"

    # Webhook security
    WEBHOOK_SIGNATURE_VALID = "webhook.signature_valid"
    WEBHOOK_SIGNATURE_INVALID = "webhook.signature_invalid"
    WEBHOOK_IP_BLOCKED = "webhook.ip_blocked"
    WEBHOOK_CREDENTIALS_ROTATED = "webhook.credentials_rotated"
    WEBHOOK_CREDENTIALS_REVOKED = "webhook.credentials_revoked"

    # SSRF protection
    SSRF_BLOCKED = "ssrf.blocked"
    SSRF_PRIVATE_IP = "ssrf.private_ip"
    SSRF_LOCALHOST = "ssrf.localhost"

    # Injection prevention
    INJECTION_BLOCKED = "injection.blocked"
    PATH_TRAVERSAL_BLOCKED = "path_traversal.blocked"
    COMMAND_INJECTION_BLOCKED = "command_injection.blocked"

    # Replay attacks
    REPLAY_ATTACK_DETECTED = "replay.detected"
    NONCE_REUSED = "replay.nonce_reused"

    # Contract operations
    CONTRACT_LICENSE_ISSUED = "contract.license_issued"
    CONTRACT_LICENSE_REVOKED = "contract.license_revoked"
    CONTRACT_PAYMENT_RECEIVED = "contract.payment_received"

    # Suspicious activity
    SUSPICIOUS_PATTERN = "suspicious.pattern"
    BRUTE_FORCE_DETECTED = "suspicious.brute_force"
    UNUSUAL_VOLUME = "suspicious.volume"

    # General
    SECURITY_CONFIG_CHANGED = "config.changed"
    ENCRYPTION_KEY_ROTATED = "encryption.key_rotated"


class SecurityEventSeverity(Enum):
    """Severity levels for security events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SecurityLogger:
    """
    Structured security event logger.

    Outputs JSON-formatted logs suitable for:
    - SIEM ingestion (Splunk, ELK, etc.)
    - Cloud logging (CloudWatch, Stackdriver)
    - Alert systems (PagerDuty, OpsGenie)
    """

    def __init__(
        self,
        logger_name: str = "rra.security",
        log_file: Optional[Path] = None,
        console_output: bool = True,
        min_level: SecurityEventSeverity = SecurityEventSeverity.INFO,
    ):
        """
        Initialize security logger.

        Args:
            logger_name: Name for the logger
            log_file: Optional path to log file
            console_output: Whether to also output to console
            min_level: Minimum severity level to log
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        self.min_level = min_level
        self._service_name = os.environ.get("RRA_SERVICE_NAME", "rra-module")
        self._environment = os.environ.get("RRA_ENVIRONMENT", "development")

        # Clear existing handlers
        self.logger.handlers.clear()

        # JSON formatter
        formatter = logging.Formatter("%(message)s")

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def _get_log_level(self, severity: SecurityEventSeverity) -> int:
        """Convert severity to logging level."""
        mapping = {
            SecurityEventSeverity.DEBUG: logging.DEBUG,
            SecurityEventSeverity.INFO: logging.INFO,
            SecurityEventSeverity.WARNING: logging.WARNING,
            SecurityEventSeverity.ERROR: logging.ERROR,
            SecurityEventSeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.INFO)

    def _should_log(self, severity: SecurityEventSeverity) -> bool:
        """Check if event should be logged based on minimum level."""
        level_order = [
            SecurityEventSeverity.DEBUG,
            SecurityEventSeverity.INFO,
            SecurityEventSeverity.WARNING,
            SecurityEventSeverity.ERROR,
            SecurityEventSeverity.CRITICAL,
        ]
        return level_order.index(severity) >= level_order.index(self.min_level)

    def log_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        message: str,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Log a structured security event.

        Args:
            event_type: Type of security event
            severity: Severity level
            message: Human-readable message
            source_ip: Source IP address if applicable
            user_id: User identifier if applicable
            agent_id: Agent/repo ID if applicable
            request_id: Request ID for correlation
            details: Additional event-specific details
            tags: Optional list of tags for filtering

        Returns:
            The logged event dictionary
        """
        if not self._should_log(severity):
            return {}

        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self._service_name,
            "environment": self._environment,
            "event_type": event_type.value,
            "severity": severity.value,
            "message": message,
        }

        # Add optional fields
        if source_ip:
            event["source_ip"] = source_ip
        if user_id:
            event["user_id"] = user_id
        if agent_id:
            event["agent_id"] = agent_id
        if request_id:
            event["request_id"] = request_id
        if details:
            event["details"] = details
        if tags:
            event["tags"] = tags

        # Log as JSON
        log_level = self._get_log_level(severity)
        self.logger.log(log_level, json.dumps(event))

        return event

    # Convenience methods for common events

    def auth_success(
        self, user_id: str, source_ip: Optional[str] = None, method: str = "api_key", **kwargs
    ) -> Dict[str, Any]:
        """Log successful authentication."""
        return self.log_event(
            event_type=SecurityEventType.AUTH_SUCCESS,
            severity=SecurityEventSeverity.INFO,
            message=f"Authentication successful for user {user_id}",
            user_id=user_id,
            source_ip=source_ip,
            details={"method": method},
            **kwargs,
        )

    def auth_failure(
        self, reason: str, source_ip: Optional[str] = None, user_id: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Log failed authentication."""
        return self.log_event(
            event_type=SecurityEventType.AUTH_FAILURE,
            severity=SecurityEventSeverity.WARNING,
            message=f"Authentication failed: {reason}",
            source_ip=source_ip,
            user_id=user_id,
            details={"reason": reason},
            **kwargs,
        )

    def rate_limit_exceeded(
        self,
        agent_id: str,
        source_ip: Optional[str] = None,
        limit: int = 100,
        window_minutes: int = 60,
        **kwargs,
    ) -> Dict[str, Any]:
        """Log rate limit exceeded."""
        return self.log_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SecurityEventSeverity.WARNING,
            message=f"Rate limit exceeded for agent {agent_id}",
            agent_id=agent_id,
            source_ip=source_ip,
            details={"limit": limit, "window_minutes": window_minutes},
            **kwargs,
        )

    def webhook_signature_invalid(
        self, agent_id: str, source_ip: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Log invalid webhook signature."""
        return self.log_event(
            event_type=SecurityEventType.WEBHOOK_SIGNATURE_INVALID,
            severity=SecurityEventSeverity.WARNING,
            message=f"Invalid webhook signature for agent {agent_id}",
            agent_id=agent_id,
            source_ip=source_ip,
            tags=["webhook", "security"],
            **kwargs,
        )

    def ssrf_blocked(
        self, url: str, reason: str, source_ip: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Log blocked SSRF attempt."""
        return self.log_event(
            event_type=SecurityEventType.SSRF_BLOCKED,
            severity=SecurityEventSeverity.WARNING,
            message=f"SSRF attempt blocked: {reason}",
            source_ip=source_ip,
            details={"blocked_url": url, "reason": reason},
            tags=["ssrf", "security"],
            **kwargs,
        )

    def injection_blocked(
        self, attack_type: str, input_value: str, source_ip: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Log blocked injection attempt."""
        # Truncate potentially malicious input
        safe_input = input_value[:100] + "..." if len(input_value) > 100 else input_value

        return self.log_event(
            event_type=SecurityEventType.INJECTION_BLOCKED,
            severity=SecurityEventSeverity.WARNING,
            message=f"Injection attempt blocked: {attack_type}",
            source_ip=source_ip,
            details={"attack_type": attack_type, "input_preview": safe_input},
            tags=["injection", "security"],
            **kwargs,
        )

    def suspicious_activity(
        self, pattern: str, source_ip: Optional[str] = None, user_id: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Log suspicious activity detection."""
        return self.log_event(
            event_type=SecurityEventType.SUSPICIOUS_PATTERN,
            severity=SecurityEventSeverity.WARNING,
            message=f"Suspicious activity detected: {pattern}",
            source_ip=source_ip,
            user_id=user_id,
            details={"pattern": pattern},
            tags=["suspicious", "security", "alert"],
            **kwargs,
        )

    def contract_event(
        self,
        event_type: SecurityEventType,
        token_id: Optional[str] = None,
        transaction_hash: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Log blockchain contract event."""
        return self.log_event(
            event_type=event_type,
            severity=SecurityEventSeverity.INFO,
            message=f"Contract event: {event_type.value}",
            details={
                "token_id": token_id,
                "transaction_hash": transaction_hash,
            },
            tags=["blockchain", "contract"],
            **kwargs,
        )


# Global security logger instance
security_logger = SecurityLogger(
    log_file=Path("logs/security.log") if os.environ.get("RRA_SECURITY_LOG_FILE") else None
)


# Convenience functions
def log_auth_success(user_id: str, **kwargs):
    """Log successful authentication."""
    return security_logger.auth_success(user_id, **kwargs)


def log_auth_failure(reason: str, **kwargs):
    """Log failed authentication."""
    return security_logger.auth_failure(reason, **kwargs)


def log_rate_limit_exceeded(agent_id: str, **kwargs):
    """Log rate limit exceeded."""
    return security_logger.rate_limit_exceeded(agent_id, **kwargs)


def log_webhook_signature_invalid(agent_id: str, **kwargs):
    """Log invalid webhook signature."""
    return security_logger.webhook_signature_invalid(agent_id, **kwargs)


def log_ssrf_blocked(url: str, reason: str, **kwargs):
    """Log blocked SSRF attempt."""
    return security_logger.ssrf_blocked(url, reason, **kwargs)


def log_injection_blocked(attack_type: str, input_value: str, **kwargs):
    """Log blocked injection attempt."""
    return security_logger.injection_blocked(attack_type, input_value, **kwargs)


def log_suspicious_activity(pattern: str, **kwargs):
    """Log suspicious activity."""
    return security_logger.suspicious_activity(pattern, **kwargs)
