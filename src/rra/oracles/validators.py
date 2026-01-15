# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Event Validators for Off-Chain Event Bridging.

Provides validation logic for different event types:
- Schema validation
- Data integrity checks
- Source-specific validation rules
- Cryptographic signature verification
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from abc import ABC, abstractmethod
import hashlib
import json
import re


class ValidationResult(Enum):
    """Result of event validation."""

    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"
    ERROR = "error"


@dataclass
class ValidationReport:
    """Detailed validation report."""

    result: ValidationResult
    confidence: float  # 0.0 to 1.0
    checks_passed: List[str]
    checks_failed: List[str]
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.result == ValidationResult.VALID

    @property
    def pass_rate(self) -> float:
        total = len(self.checks_passed) + len(self.checks_failed)
        return len(self.checks_passed) / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "confidence": self.confidence,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "warnings": self.warnings,
            "errors": self.errors,
            "metadata": self.metadata,
            "pass_rate": self.pass_rate,
        }


class EventValidator(ABC):
    """Abstract base class for event validators."""

    @abstractmethod
    def validate(self, event_data: Dict[str, Any], **kwargs) -> ValidationReport:
        """Validate event data."""

    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Get list of required fields."""


class SchemaValidator(EventValidator):
    """
    JSON Schema-based event validator.

    Validates event data against expected schema.
    """

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.required_fields = schema.get("required", [])
        self.field_types = schema.get("properties", {})

    def validate(self, event_data: Dict[str, Any], **kwargs) -> ValidationReport:
        """Validate against schema."""
        passed = []
        failed = []
        warnings = []
        errors = []

        # Check required fields
        for field_name in self.required_fields:
            if field_name in event_data and event_data[field_name] is not None:
                passed.append(f"required_field:{field_name}")
            else:
                failed.append(f"required_field:{field_name}")

        # Check field types
        for field_name, type_spec in self.field_types.items():
            if field_name in event_data:
                expected_type = type_spec.get("type")
                value = event_data[field_name]

                if self._check_type(value, expected_type):
                    passed.append(f"type_check:{field_name}")
                else:
                    failed.append(f"type_check:{field_name}")

                # Check additional constraints
                if "minLength" in type_spec and isinstance(value, str):
                    if len(value) >= type_spec["minLength"]:
                        passed.append(f"min_length:{field_name}")
                    else:
                        failed.append(f"min_length:{field_name}")

                if "maxLength" in type_spec and isinstance(value, str):
                    if len(value) <= type_spec["maxLength"]:
                        passed.append(f"max_length:{field_name}")
                    else:
                        failed.append(f"max_length:{field_name}")

                if "pattern" in type_spec and isinstance(value, str):
                    if re.match(type_spec["pattern"], value):
                        passed.append(f"pattern:{field_name}")
                    else:
                        failed.append(f"pattern:{field_name}")

        # Calculate confidence
        total = len(passed) + len(failed)
        confidence = len(passed) / total if total > 0 else 0.0

        # Determine result
        if len(failed) == 0 and len(errors) == 0:
            result = ValidationResult.VALID
        elif confidence > 0.8:
            result = ValidationResult.UNCERTAIN
            warnings.append("Some checks failed but high pass rate")
        else:
            result = ValidationResult.INVALID

        return ValidationReport(
            result=result,
            confidence=confidence,
            checks_passed=passed,
            checks_failed=failed,
            warnings=warnings,
            errors=errors,
        )

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, skip check
        return isinstance(value, expected)

    def get_required_fields(self) -> List[str]:
        return self.required_fields


class HashValidator(EventValidator):
    """
    Validate event data integrity using hash verification.
    """

    def __init__(self, algorithm: str = "sha256"):
        self.algorithm = algorithm

    def validate(
        self, event_data: Dict[str, Any], expected_hash: Optional[str] = None, **kwargs
    ) -> ValidationReport:
        """Validate data hash."""
        passed = []
        failed = []
        warnings = []
        errors = []

        # Calculate hash
        try:
            data_str = json.dumps(event_data, sort_keys=True)
            calculated_hash = hashlib.new(self.algorithm, data_str.encode()).hexdigest()
            passed.append("hash_calculation")
        except Exception as e:
            errors.append(f"Hash calculation failed: {e}")
            return ValidationReport(
                result=ValidationResult.ERROR,
                confidence=0.0,
                checks_passed=passed,
                checks_failed=failed,
                warnings=warnings,
                errors=errors,
                metadata={"error": str(e)},
            )

        # Compare with expected hash if provided using constant-time comparison
        # SECURITY FIX: Prevents timing attacks on hash verification
        if expected_hash:
            import hmac

            calculated_bytes = (
                calculated_hash.encode() if isinstance(calculated_hash, str) else calculated_hash
            )
            expected_bytes = (
                expected_hash.lower().encode() if isinstance(expected_hash, str) else expected_hash
            )
            if hmac.compare_digest(calculated_bytes, expected_bytes):
                passed.append("hash_match")
            else:
                failed.append("hash_match")
                warnings.append(f"Hash mismatch: expected {expected_hash[:16]}...")

        # Check for empty data
        if not event_data:
            failed.append("non_empty_data")
            warnings.append("Event data is empty")
        else:
            passed.append("non_empty_data")

        confidence = len(passed) / (len(passed) + len(failed)) if passed or failed else 0.0

        result = ValidationResult.VALID if len(failed) == 0 else ValidationResult.INVALID

        return ValidationReport(
            result=result,
            confidence=confidence,
            checks_passed=passed,
            checks_failed=failed,
            warnings=warnings,
            errors=errors,
            metadata={"calculated_hash": calculated_hash, "algorithm": self.algorithm},
        )

    def get_required_fields(self) -> List[str]:
        return []


class TimestampValidator(EventValidator):
    """
    Validate event timestamps.
    """

    def __init__(
        self,
        max_age_days: int = 30,
        allow_future: bool = False,
        future_tolerance_minutes: int = 5,
    ):
        self.max_age = timedelta(days=max_age_days)
        self.allow_future = allow_future
        self.future_tolerance = timedelta(minutes=future_tolerance_minutes)

    def validate(
        self, event_data: Dict[str, Any], timestamp_field: str = "timestamp", **kwargs
    ) -> ValidationReport:
        """Validate timestamp."""
        passed = []
        failed = []
        warnings = []
        errors = []

        # Extract timestamp
        timestamp_str = event_data.get(timestamp_field)
        if not timestamp_str:
            failed.append("timestamp_present")
            return ValidationReport(
                result=ValidationResult.INVALID,
                confidence=0.0,
                checks_passed=passed,
                checks_failed=failed,
                warnings=["Timestamp field missing"],
                errors=errors,
            )

        passed.append("timestamp_present")

        # Parse timestamp
        try:
            if isinstance(timestamp_str, (int, float)):
                timestamp = datetime.fromtimestamp(timestamp_str)
            else:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            passed.append("timestamp_parseable")
        except Exception as e:
            failed.append("timestamp_parseable")
            errors.append(f"Failed to parse timestamp: {e}")
            return ValidationReport(
                result=ValidationResult.ERROR,
                confidence=0.0,
                checks_passed=passed,
                checks_failed=failed,
                warnings=warnings,
                errors=errors,
            )

        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()

        # Check if too old
        age = now - timestamp
        if age <= self.max_age:
            passed.append("timestamp_not_stale")
        else:
            failed.append("timestamp_not_stale")
            warnings.append(f"Event is {age.days} days old, max allowed is {self.max_age.days}")

        # Check if in future
        if timestamp > now + self.future_tolerance:
            if self.allow_future:
                warnings.append("Timestamp is in the future")
                passed.append("timestamp_not_future")
            else:
                failed.append("timestamp_not_future")
        else:
            passed.append("timestamp_not_future")

        confidence = len(passed) / (len(passed) + len(failed))
        result = ValidationResult.VALID if len(failed) == 0 else ValidationResult.INVALID

        return ValidationReport(
            result=result,
            confidence=confidence,
            checks_passed=passed,
            checks_failed=failed,
            warnings=warnings,
            errors=errors,
            metadata={"timestamp": timestamp.isoformat(), "age_days": age.days},
        )

    def get_required_fields(self) -> List[str]:
        return ["timestamp"]


class SignatureValidator(EventValidator):
    """
    Validate cryptographic signatures on event data.
    """

    def __init__(self, trusted_signers: Optional[Set[str]] = None):
        self.trusted_signers = trusted_signers or set()

    def validate(
        self,
        event_data: Dict[str, Any],
        signature: Optional[str] = None,
        signer: Optional[str] = None,
        **kwargs,
    ) -> ValidationReport:
        """Validate signature."""
        passed = []
        failed = []
        warnings = []
        errors = []

        # Get signature from data if not provided
        if signature is None:
            signature = event_data.get("signature")
        if signer is None:
            signer = event_data.get("signer")

        if not signature:
            failed.append("signature_present")
            return ValidationReport(
                result=ValidationResult.INVALID,
                confidence=0.0,
                checks_passed=passed,
                checks_failed=failed,
                warnings=["No signature provided"],
                errors=errors,
            )

        passed.append("signature_present")

        # Check signature format (basic hex check)
        if self._is_valid_signature_format(signature):
            passed.append("signature_format")
        else:
            failed.append("signature_format")

        # Check if signer is trusted
        if signer:
            passed.append("signer_present")
            if signer.lower() in [s.lower() for s in self.trusted_signers]:
                passed.append("signer_trusted")
            else:
                if self.trusted_signers:
                    failed.append("signer_trusted")
                    warnings.append(f"Signer {signer[:10]}... not in trusted list")
                else:
                    warnings.append("No trusted signers configured")
        else:
            warnings.append("Signer address not provided")

        confidence = len(passed) / (len(passed) + len(failed)) if passed or failed else 0.0

        # Signature verification would require actual crypto library
        # This is a placeholder for structure
        warnings.append("Full signature verification requires web3/crypto integration")

        result = ValidationResult.VALID if len(failed) == 0 else ValidationResult.UNCERTAIN

        return ValidationReport(
            result=result,
            confidence=confidence,
            checks_passed=passed,
            checks_failed=failed,
            warnings=warnings,
            errors=errors,
            metadata={"signer": signer, "signature_length": len(signature) if signature else 0},
        )

    def _is_valid_signature_format(self, signature: str) -> bool:
        """Check if signature looks like valid hex."""
        if signature.startswith("0x"):
            signature = signature[2:]
        return bool(re.match(r"^[0-9a-fA-F]+$", signature)) and len(signature) >= 64

    def add_trusted_signer(self, signer: str) -> None:
        """Add a trusted signer."""
        self.trusted_signers.add(signer.lower())

    def remove_trusted_signer(self, signer: str) -> None:
        """Remove a trusted signer."""
        self.trusted_signers.discard(signer.lower())

    def get_required_fields(self) -> List[str]:
        return ["signature"]


class CompositeValidator(EventValidator):
    """
    Combine multiple validators with configurable logic.
    """

    def __init__(
        self,
        validators: List[EventValidator],
        require_all: bool = True,
        min_pass_ratio: float = 0.7,
    ):
        self.validators = validators
        self.require_all = require_all
        self.min_pass_ratio = min_pass_ratio

    def validate(self, event_data: Dict[str, Any], **kwargs) -> ValidationReport:
        """Run all validators and combine results."""
        all_passed = []
        all_failed = []
        all_warnings = []
        all_errors = []
        sub_reports = []

        for validator in self.validators:
            try:
                report = validator.validate(event_data, **kwargs)
                sub_reports.append(report)

                all_passed.extend(report.checks_passed)
                all_failed.extend(report.checks_failed)
                all_warnings.extend(report.warnings)
                all_errors.extend(report.errors)
            except Exception as e:
                all_errors.append(f"Validator {type(validator).__name__} failed: {e}")

        # Calculate overall result
        valid_count = sum(1 for r in sub_reports if r.is_valid)
        total_count = len(sub_reports)
        pass_ratio = valid_count / total_count if total_count > 0 else 0.0

        if self.require_all:
            result = (
                ValidationResult.VALID if valid_count == total_count else ValidationResult.INVALID
            )
        else:
            if pass_ratio >= self.min_pass_ratio:
                result = ValidationResult.VALID
            elif pass_ratio >= 0.5:
                result = ValidationResult.UNCERTAIN
            else:
                result = ValidationResult.INVALID

        # Calculate confidence as weighted average
        if sub_reports:
            confidence = sum(r.confidence for r in sub_reports) / len(sub_reports)
        else:
            confidence = 0.0

        return ValidationReport(
            result=result,
            confidence=confidence,
            checks_passed=all_passed,
            checks_failed=all_failed,
            warnings=all_warnings,
            errors=all_errors,
            metadata={
                "validators_run": total_count,
                "validators_passed": valid_count,
                "pass_ratio": pass_ratio,
            },
        )

    def get_required_fields(self) -> List[str]:
        fields = []
        for validator in self.validators:
            fields.extend(validator.get_required_fields())
        return list(set(fields))


class GitHubEventValidator(EventValidator):
    """
    Validate GitHub-specific event data.
    """

    VALID_EVENT_TYPES = {
        "push",
        "pull_request",
        "issues",
        "issue_comment",
        "release",
        "create",
        "delete",
        "fork",
        "star",
        "commit_comment",
        "pull_request_review",
        "workflow_run",
    }

    def validate(self, event_data: Dict[str, Any], **kwargs) -> ValidationReport:
        """Validate GitHub event."""
        passed = []
        failed = []
        warnings = []
        errors = []

        # Check for repository info
        repo = event_data.get("repository") or event_data.get("repo")
        if repo:
            passed.append("repository_present")
            if isinstance(repo, dict):
                if repo.get("full_name"):
                    passed.append("repository_name")
                else:
                    failed.append("repository_name")
        else:
            failed.append("repository_present")

        # Check for sender/actor
        sender = event_data.get("sender") or event_data.get("actor")
        if sender:
            passed.append("sender_present")
            if isinstance(sender, dict) and sender.get("login"):
                passed.append("sender_login")
            elif isinstance(sender, str):
                passed.append("sender_login")
            else:
                warnings.append("Sender login not found")
        else:
            warnings.append("No sender information")

        # Check event type if present
        event_type = event_data.get("type") or event_data.get("action")
        if event_type:
            if event_type.lower() in self.VALID_EVENT_TYPES:
                passed.append("valid_event_type")
            else:
                warnings.append(f"Unknown event type: {event_type}")

        # Check for commit SHA if applicable
        if "commits" in event_data or "head_commit" in event_data:
            commits = event_data.get("commits", [])
            head = event_data.get("head_commit", {})
            if commits or head:
                passed.append("commit_data_present")
                if head.get("id") or (commits and commits[0].get("id")):
                    passed.append("commit_sha")
                else:
                    warnings.append("Commit SHA not found")

        confidence = len(passed) / (len(passed) + len(failed)) if passed or failed else 0.5

        if len(failed) == 0 and len(errors) == 0:
            result = ValidationResult.VALID
        elif confidence >= 0.7:
            result = ValidationResult.UNCERTAIN
        else:
            result = ValidationResult.INVALID

        return ValidationReport(
            result=result,
            confidence=confidence,
            checks_passed=passed,
            checks_failed=failed,
            warnings=warnings,
            errors=errors,
            metadata={"event_type": event_type},
        )

    def get_required_fields(self) -> List[str]:
        return ["repository"]


class FinancialEventValidator(EventValidator):
    """
    Validate financial/payment event data.
    """

    def __init__(self, min_amount: float = 0.0, max_amount: Optional[float] = None):
        self.min_amount = min_amount
        self.max_amount = max_amount

    def validate(self, event_data: Dict[str, Any], **kwargs) -> ValidationReport:
        """Validate financial event."""
        passed = []
        failed = []
        warnings = []
        errors = []

        # Check amount
        amount = event_data.get("amount") or event_data.get("value")
        if amount is not None:
            passed.append("amount_present")
            try:
                amount_val = float(amount)
                if amount_val >= self.min_amount:
                    passed.append("amount_min")
                else:
                    failed.append("amount_min")
                    warnings.append(f"Amount {amount_val} below minimum {self.min_amount}")

                if self.max_amount is not None:
                    if amount_val <= self.max_amount:
                        passed.append("amount_max")
                    else:
                        failed.append("amount_max")
                        warnings.append(f"Amount {amount_val} above maximum {self.max_amount}")
            except (ValueError, TypeError):
                failed.append("amount_numeric")
                errors.append(f"Amount '{amount}' is not numeric")
        else:
            failed.append("amount_present")

        # Check currency
        currency = event_data.get("currency") or event_data.get("token")
        if currency:
            passed.append("currency_present")
        else:
            warnings.append("No currency specified")

        # Check transaction ID
        tx_id = (
            event_data.get("transaction_id") or event_data.get("tx_hash") or event_data.get("id")
        )
        if tx_id:
            passed.append("transaction_id")
        else:
            warnings.append("No transaction ID")

        # Check sender/recipient
        sender = event_data.get("sender") or event_data.get("from")
        recipient = event_data.get("recipient") or event_data.get("to")
        if sender:
            passed.append("sender_present")
        if recipient:
            passed.append("recipient_present")

        confidence = len(passed) / (len(passed) + len(failed)) if passed or failed else 0.0

        if len(failed) == 0:
            result = ValidationResult.VALID
        elif confidence >= 0.7:
            result = ValidationResult.UNCERTAIN
        else:
            result = ValidationResult.INVALID

        return ValidationReport(
            result=result,
            confidence=confidence,
            checks_passed=passed,
            checks_failed=failed,
            warnings=warnings,
            errors=errors,
            metadata={"amount": amount, "currency": currency},
        )

    def get_required_fields(self) -> List[str]:
        return ["amount"]


# =============================================================================
# Validator Factory
# =============================================================================


def create_schema_validator(schema: Dict[str, Any]) -> SchemaValidator:
    """Create a schema validator."""
    return SchemaValidator(schema)


def create_github_validator() -> GitHubEventValidator:
    """Create a GitHub event validator."""
    return GitHubEventValidator()


def create_financial_validator(
    min_amount: float = 0.0,
    max_amount: Optional[float] = None,
) -> FinancialEventValidator:
    """Create a financial event validator."""
    return FinancialEventValidator(min_amount, max_amount)


def create_composite_validator(
    include_hash: bool = True,
    include_timestamp: bool = True,
    custom_validators: Optional[List[EventValidator]] = None,
    require_all: bool = False,
) -> CompositeValidator:
    """Create a composite validator with common checks."""
    validators = []

    if include_hash:
        validators.append(HashValidator())
    if include_timestamp:
        validators.append(TimestampValidator())
    if custom_validators:
        validators.extend(custom_validators)

    return CompositeValidator(validators, require_all=require_all)
