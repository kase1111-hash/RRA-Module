# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Centralized Exception Hierarchy for RRA Module.

This module provides a comprehensive exception hierarchy with:
- Domain-specific exception types
- Verbose error messages with context
- Error codes for programmatic handling
- Chained exception support for debugging
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """
    Standardized error codes for programmatic error handling.

    Format: DOMAIN_SPECIFIC_ERROR (e.g., CONTRACT_NOT_FOUND)
    """
    # General errors (1xxx)
    UNKNOWN_ERROR = 1000
    VALIDATION_ERROR = 1001
    CONFIGURATION_ERROR = 1002
    INITIALIZATION_ERROR = 1003
    TIMEOUT_ERROR = 1004
    RESOURCE_NOT_FOUND = 1005
    PERMISSION_DENIED = 1006
    RATE_LIMITED = 1007

    # Contract errors (2xxx)
    CONTRACT_NOT_FOUND = 2000
    CONTRACT_DEPLOYMENT_FAILED = 2001
    CONTRACT_CALL_FAILED = 2002
    CONTRACT_ABI_INVALID = 2003
    CONTRACT_BYTECODE_MISSING = 2004
    CONTRACT_COMPILATION_FAILED = 2005
    CONTRACT_VERIFICATION_FAILED = 2006

    # Transaction errors (3xxx)
    TRANSACTION_FAILED = 3000
    TRANSACTION_REVERTED = 3001
    TRANSACTION_TIMEOUT = 3002
    INSUFFICIENT_FUNDS = 3003
    GAS_ESTIMATION_FAILED = 3004
    NONCE_TOO_LOW = 3005
    NONCE_TOO_HIGH = 3006

    # Storage errors (4xxx)
    STORAGE_UPLOAD_FAILED = 4000
    STORAGE_DOWNLOAD_FAILED = 4001
    STORAGE_NOT_FOUND = 4002
    STORAGE_ENCRYPTION_FAILED = 4003
    STORAGE_DECRYPTION_FAILED = 4004
    STORAGE_HASH_MISMATCH = 4005

    # Authentication errors (5xxx)
    AUTH_FAILED = 5000
    AUTH_EXPIRED = 5001
    AUTH_INVALID_SIGNATURE = 5002
    AUTH_INVALID_TOKEN = 5003
    AUTH_INSUFFICIENT_PERMISSIONS = 5004
    AUTH_DID_RESOLUTION_FAILED = 5005

    # Dispute errors (6xxx)
    DISPUTE_NOT_FOUND = 6000
    DISPUTE_ALREADY_RESOLVED = 6001
    DISPUTE_INVALID_STATE = 6002
    DISPUTE_STAKE_INSUFFICIENT = 6003
    DISPUTE_VOTING_CLOSED = 6004
    DISPUTE_QUORUM_NOT_MET = 6005

    # Integration errors (7xxx)
    INTEGRATION_CONNECTION_FAILED = 7000
    INTEGRATION_API_ERROR = 7001
    INTEGRATION_TIMEOUT = 7002
    INTEGRATION_RATE_LIMITED = 7003
    INTEGRATION_INVALID_RESPONSE = 7004

    # L3/Batch processing errors (8xxx)
    BATCH_NOT_FOUND = 8000
    BATCH_PROCESSING_FAILED = 8001
    BATCH_INVALID_STATE = 8002
    SEQUENCER_NOT_RUNNING = 8003
    SEQUENCER_OVERLOADED = 8004

    # Negotiation errors (9xxx)
    NEGOTIATION_NOT_FOUND = 9000
    NEGOTIATION_EXPIRED = 9001
    NEGOTIATION_INVALID_STATE = 9002
    NEGOTIATION_STAKE_INSUFFICIENT = 9003

    # Oracle/Bridge errors (10xxx)
    ORACLE_UNAVAILABLE = 10000
    ORACLE_DATA_STALE = 10001
    BRIDGE_EVENT_NOT_FOUND = 10002
    BRIDGE_ATTESTATION_FAILED = 10003
    BRIDGE_CONSENSUS_FAILED = 10004


class RRAError(Exception):
    """
    Base exception for all RRA module errors.

    Provides:
    - Error code for programmatic handling
    - Verbose message with context
    - Original exception chaining
    - Structured context dictionary

    Example:
        raise RRAError(
            message="Operation failed",
            error_code=ErrorCode.UNKNOWN_ERROR,
            context={"operation": "deploy", "contract": "License"},
            cause=original_exception
        )
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.cause = cause

        # Build verbose message
        verbose_message = self._build_verbose_message()
        super().__init__(verbose_message)

        # Chain the cause if provided
        if cause:
            self.__cause__ = cause

    def _build_verbose_message(self) -> str:
        """Build a verbose error message with all context."""
        parts = [f"[{self.error_code.name}] {self.message}"]

        if self.context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        if self.cause:
            parts.append(f"Caused by: {type(self.cause).__name__}: {self.cause}")

        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error": self.error_code.name,
            "error_code": self.error_code.value,
            "message": self.message,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(RRAError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        constraint: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = repr(value)[:100]  # Truncate long values
        if constraint:
            context["constraint"] = constraint

        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            context=context,
            cause=cause,
        )


class ConfigurationError(RRAError):
    """Raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {}
        if config_key:
            context["config_key"] = config_key
        if expected:
            context["expected"] = expected
        if actual:
            context["actual"] = actual

        super().__init__(
            message=message,
            error_code=ErrorCode.CONFIGURATION_ERROR,
            context=context,
            cause=cause,
        )


# =============================================================================
# Contract Errors
# =============================================================================

class ContractError(RRAError):
    """Base exception for contract-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.CONTRACT_CALL_FAILED,
        contract_name: Optional[str] = None,
        contract_address: Optional[str] = None,
        function_name: Optional[str] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if contract_name:
            context["contract_name"] = contract_name
        if contract_address:
            context["contract_address"] = contract_address
        if function_name:
            context["function_name"] = function_name

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class ContractNotFoundError(ContractError):
    """Raised when a contract cannot be found."""

    def __init__(
        self,
        contract_name: str,
        search_paths: Optional[list] = None,
        cause: Optional[Exception] = None,
    ):
        context = {"search_paths": search_paths} if search_paths else {}
        super().__init__(
            message=f"Contract '{contract_name}' not found",
            error_code=ErrorCode.CONTRACT_NOT_FOUND,
            contract_name=contract_name,
            cause=cause,
            **context,
        )


class ContractDeploymentError(ContractError):
    """Raised when contract deployment fails."""

    def __init__(
        self,
        contract_name: str,
        reason: str,
        gas_used: Optional[int] = None,
        tx_hash: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {"reason": reason}
        if gas_used:
            context["gas_used"] = gas_used
        if tx_hash:
            context["tx_hash"] = tx_hash

        super().__init__(
            message=f"Failed to deploy contract '{contract_name}': {reason}",
            error_code=ErrorCode.CONTRACT_DEPLOYMENT_FAILED,
            contract_name=contract_name,
            cause=cause,
            **context,
        )


class ContractCompilationError(ContractError):
    """Raised when contract compilation fails."""

    def __init__(
        self,
        contract_name: str,
        compiler_output: Optional[str] = None,
        source_file: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {}
        if compiler_output:
            context["compiler_output"] = compiler_output[:500]  # Truncate
        if source_file:
            context["source_file"] = source_file

        super().__init__(
            message=f"Failed to compile contract '{contract_name}'",
            error_code=ErrorCode.CONTRACT_COMPILATION_FAILED,
            contract_name=contract_name,
            cause=cause,
            **context,
        )


class ContractCallError(ContractError):
    """Raised when a contract call fails."""

    def __init__(
        self,
        contract_name: str,
        function_name: str,
        reason: str,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        cause: Optional[Exception] = None,
    ):
        context = {"reason": reason}
        if args:
            context["args"] = repr(args)[:200]
        if kwargs:
            context["kwargs"] = repr(kwargs)[:200]

        super().__init__(
            message=f"Contract call '{contract_name}.{function_name}()' failed: {reason}",
            error_code=ErrorCode.CONTRACT_CALL_FAILED,
            contract_name=contract_name,
            function_name=function_name,
            cause=cause,
            **context,
        )


# =============================================================================
# Transaction Errors
# =============================================================================

class TransactionError(RRAError):
    """Base exception for transaction-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.TRANSACTION_FAILED,
        tx_hash: Optional[str] = None,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        value: Optional[int] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if tx_hash:
            context["tx_hash"] = tx_hash
        if from_address:
            context["from"] = from_address
        if to_address:
            context["to"] = to_address
        if value is not None:
            context["value"] = value

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class TransactionRevertedError(TransactionError):
    """Raised when a transaction is reverted."""

    def __init__(
        self,
        tx_hash: str,
        revert_reason: Optional[str] = None,
        gas_used: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        context = {}
        if revert_reason:
            context["revert_reason"] = revert_reason
        if gas_used:
            context["gas_used"] = gas_used

        super().__init__(
            message=f"Transaction reverted: {revert_reason or 'unknown reason'}",
            error_code=ErrorCode.TRANSACTION_REVERTED,
            tx_hash=tx_hash,
            cause=cause,
            **context,
        )


class InsufficientFundsError(TransactionError):
    """Raised when account has insufficient funds."""

    def __init__(
        self,
        address: str,
        required: int,
        available: int,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"Insufficient funds: required {required} wei, available {available} wei",
            error_code=ErrorCode.INSUFFICIENT_FUNDS,
            from_address=address,
            cause=cause,
            required=required,
            available=available,
        )


# =============================================================================
# Storage Errors
# =============================================================================

class StorageError(RRAError):
    """Base exception for storage-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.STORAGE_UPLOAD_FAILED,
        provider: Optional[str] = None,
        uri: Optional[str] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if provider:
            context["provider"] = provider
        if uri:
            context["uri"] = uri

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class StorageUploadError(StorageError):
    """Raised when storage upload fails."""

    def __init__(
        self,
        provider: str,
        reason: str,
        content_size: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        context = {"reason": reason}
        if content_size:
            context["content_size"] = content_size

        super().__init__(
            message=f"Failed to upload to {provider}: {reason}",
            error_code=ErrorCode.STORAGE_UPLOAD_FAILED,
            provider=provider,
            cause=cause,
            **context,
        )


class StorageDownloadError(StorageError):
    """Raised when storage download fails."""

    def __init__(
        self,
        uri: str,
        reason: str,
        status_code: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        context = {"reason": reason}
        if status_code:
            context["status_code"] = status_code

        super().__init__(
            message=f"Failed to download from '{uri}': {reason}",
            error_code=ErrorCode.STORAGE_DOWNLOAD_FAILED,
            uri=uri,
            cause=cause,
            **context,
        )


class EncryptionError(StorageError):
    """Raised when encryption/decryption fails."""

    def __init__(
        self,
        operation: str,  # "encrypt" or "decrypt"
        reason: str,
        cause: Optional[Exception] = None,
    ):
        error_code = (
            ErrorCode.STORAGE_ENCRYPTION_FAILED if operation == "encrypt"
            else ErrorCode.STORAGE_DECRYPTION_FAILED
        )

        super().__init__(
            message=f"Failed to {operation}: {reason}",
            error_code=error_code,
            cause=cause,
            operation=operation,
            reason=reason,
        )


# =============================================================================
# Dispute Errors
# =============================================================================

class DisputeError(RRAError):
    """Base exception for dispute-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DISPUTE_INVALID_STATE,
        dispute_id: Optional[int] = None,
        current_status: Optional[str] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if dispute_id is not None:
            context["dispute_id"] = dispute_id
        if current_status:
            context["current_status"] = current_status

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class DisputeNotFoundError(DisputeError):
    """Raised when a dispute cannot be found."""

    def __init__(self, dispute_id: int, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Dispute with ID {dispute_id} not found",
            error_code=ErrorCode.DISPUTE_NOT_FOUND,
            dispute_id=dispute_id,
            cause=cause,
        )


class DisputeStateError(DisputeError):
    """Raised when dispute is in an invalid state for the operation."""

    def __init__(
        self,
        dispute_id: int,
        operation: str,
        current_status: str,
        required_status: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {"operation": operation}
        if required_status:
            context["required_status"] = required_status

        super().__init__(
            message=f"Cannot {operation} dispute {dispute_id}: "
                    f"current status is '{current_status}'"
                    f"{f', required: {required_status}' if required_status else ''}",
            error_code=ErrorCode.DISPUTE_INVALID_STATE,
            dispute_id=dispute_id,
            current_status=current_status,
            cause=cause,
            **context,
        )


class InsufficientStakeError(DisputeError):
    """Raised when stake amount is insufficient."""

    def __init__(
        self,
        dispute_id: int,
        required: int,
        provided: int,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"Insufficient stake for dispute {dispute_id}: "
                    f"required {required} wei, provided {provided} wei",
            error_code=ErrorCode.DISPUTE_STAKE_INSUFFICIENT,
            dispute_id=dispute_id,
            cause=cause,
            required=required,
            provided=provided,
        )


# =============================================================================
# Integration Errors
# =============================================================================

class IntegrationError(RRAError):
    """Base exception for external integration errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTEGRATION_API_ERROR,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if service:
            context["service"] = service
        if endpoint:
            context["endpoint"] = endpoint
        if status_code:
            context["status_code"] = status_code

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class ConnectionError(IntegrationError):
    """Raised when connection to external service fails."""

    def __init__(
        self,
        service: str,
        endpoint: str,
        reason: str,
        retry_count: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        context = {"reason": reason}
        if retry_count is not None:
            context["retry_count"] = retry_count

        super().__init__(
            message=f"Failed to connect to {service} at {endpoint}: {reason}",
            error_code=ErrorCode.INTEGRATION_CONNECTION_FAILED,
            service=service,
            endpoint=endpoint,
            cause=cause,
            **context,
        )


class APIError(IntegrationError):
    """Raised when an API call fails."""

    def __init__(
        self,
        service: str,
        endpoint: str,
        status_code: int,
        response_body: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {}
        if response_body:
            context["response_body"] = response_body[:500]  # Truncate

        super().__init__(
            message=f"API error from {service} ({endpoint}): HTTP {status_code}",
            error_code=ErrorCode.INTEGRATION_API_ERROR,
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            cause=cause,
            **context,
        )


class TimeoutError(IntegrationError):
    """Raised when an operation times out."""

    def __init__(
        self,
        service: str,
        operation: str,
        timeout_seconds: float,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"Operation '{operation}' on {service} timed out after {timeout_seconds}s",
            error_code=ErrorCode.INTEGRATION_TIMEOUT,
            service=service,
            cause=cause,
            operation=operation,
            timeout_seconds=timeout_seconds,
        )


# =============================================================================
# L3/Batch Processing Errors
# =============================================================================

class BatchProcessingError(RRAError):
    """Base exception for batch processing errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.BATCH_PROCESSING_FAILED,
        batch_id: Optional[int] = None,
        dispute_count: Optional[int] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if batch_id is not None:
            context["batch_id"] = batch_id
        if dispute_count is not None:
            context["dispute_count"] = dispute_count

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class BatchNotFoundError(BatchProcessingError):
    """Raised when a batch cannot be found."""

    def __init__(self, batch_id: int, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Batch with ID {batch_id} not found",
            error_code=ErrorCode.BATCH_NOT_FOUND,
            batch_id=batch_id,
            cause=cause,
        )


class SequencerError(BatchProcessingError):
    """Raised when sequencer operations fail."""

    def __init__(
        self,
        message: str,
        sequencer_status: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {}
        if sequencer_status:
            context["sequencer_status"] = sequencer_status

        super().__init__(
            message=message,
            error_code=ErrorCode.SEQUENCER_NOT_RUNNING,
            cause=cause,
            **context,
        )


# =============================================================================
# Oracle/Bridge Errors
# =============================================================================

class OracleError(RRAError):
    """Base exception for oracle-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.ORACLE_UNAVAILABLE,
        source: Optional[str] = None,
        event_id: Optional[str] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if source:
            context["source"] = source
        if event_id:
            context["event_id"] = event_id

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class BridgeEventError(OracleError):
    """Raised when bridge event processing fails."""

    def __init__(
        self,
        event_id: str,
        source: str,
        reason: str,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"Bridge event '{event_id}' from {source} failed: {reason}",
            error_code=ErrorCode.BRIDGE_EVENT_NOT_FOUND,
            source=source,
            event_id=event_id,
            cause=cause,
            reason=reason,
        )


class ConsensusError(OracleError):
    """Raised when consensus cannot be reached."""

    def __init__(
        self,
        event_id: str,
        valid_count: int,
        invalid_count: int,
        threshold: int,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=f"Consensus failed for event '{event_id}': "
                    f"{valid_count} valid, {invalid_count} invalid, threshold {threshold}",
            error_code=ErrorCode.BRIDGE_CONSENSUS_FAILED,
            event_id=event_id,
            cause=cause,
            valid_count=valid_count,
            invalid_count=invalid_count,
            threshold=threshold,
        )


# =============================================================================
# Negotiation Errors
# =============================================================================

class NegotiationError(RRAError):
    """Base exception for negotiation-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.NEGOTIATION_INVALID_STATE,
        negotiation_id: Optional[str] = None,
        cause: Optional[Exception] = None,
        **extra_context,
    ):
        context = {**extra_context}
        if negotiation_id:
            context["negotiation_id"] = negotiation_id

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            cause=cause,
        )


class NegotiationNotFoundError(NegotiationError):
    """Raised when a negotiation cannot be found."""

    def __init__(self, negotiation_id: str, cause: Optional[Exception] = None):
        super().__init__(
            message=f"Negotiation '{negotiation_id}' not found",
            error_code=ErrorCode.NEGOTIATION_NOT_FOUND,
            negotiation_id=negotiation_id,
            cause=cause,
        )


class NegotiationExpiredError(NegotiationError):
    """Raised when a negotiation has expired."""

    def __init__(
        self,
        negotiation_id: str,
        expired_at: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        context = {}
        if expired_at:
            context["expired_at"] = expired_at

        super().__init__(
            message=f"Negotiation '{negotiation_id}' has expired",
            error_code=ErrorCode.NEGOTIATION_EXPIRED,
            negotiation_id=negotiation_id,
            cause=cause,
            **context,
        )


# =============================================================================
# Helper Functions
# =============================================================================

def wrap_exception(
    exception: Exception,
    error_class: type = RRAError,
    message: Optional[str] = None,
    **kwargs,
) -> RRAError:
    """
    Wrap an exception in an RRAError with additional context.

    Args:
        exception: The original exception to wrap
        error_class: The RRAError subclass to use
        message: Optional message (defaults to str(exception))
        **kwargs: Additional context to pass to the error class

    Returns:
        An instance of error_class wrapping the original exception
    """
    if isinstance(exception, RRAError):
        return exception  # Already an RRAError, don't double-wrap

    return error_class(
        message=message or str(exception),
        cause=exception,
        **kwargs,
    )
