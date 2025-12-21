# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Off-Chain Event Bridge for Dispute Evidence.

Bridges real-world events to on-chain disputes:
- Fetches data from external APIs
- Validates event data integrity
- Submits attestations to EventOracle contract
- Integrates with Chainlink Functions for external data
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable
from pathlib import Path
import json
import hashlib
import secrets
import asyncio
import aiohttp
from abc import ABC, abstractmethod


class EventSource(Enum):
    """Types of event sources."""
    API = "api"
    IPFS = "ipfs"
    GITHUB = "github"
    LEGAL = "legal"
    FINANCIAL = "financial"
    IOT = "iot"
    SOCIAL = "social"
    CUSTOM = "custom"


class EventStatus(Enum):
    """Event verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AttestationChoice(Enum):
    """Attestation validity choice."""
    VALID = "valid"
    INVALID = "invalid"


@dataclass
class EventData:
    """Raw event data from source."""
    source: EventSource
    source_uri: str
    raw_data: Dict[str, Any]
    data_hash: str
    fetched_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.value,
            "source_uri": self.source_uri,
            "raw_data": self.raw_data,
            "data_hash": self.data_hash,
            "fetched_at": self.fetched_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Attestation:
    """Validator attestation for an event."""
    validator_address: str
    event_id: str
    is_valid: bool
    data_hash: str
    evidence_uri: str
    timestamp: datetime
    signature: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_address": self.validator_address,
            "event_id": self.event_id,
            "is_valid": self.is_valid,
            "data_hash": self.data_hash,
            "evidence_uri": self.evidence_uri,
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature,
            "reason": self.reason,
        }


@dataclass
class BridgedEvent:
    """Event bridged from off-chain source."""
    event_id: str
    source: EventSource
    status: EventStatus
    data: Optional[EventData] = None
    dispute_id: Optional[str] = None
    requester: Optional[str] = None
    requested_at: datetime = field(default_factory=datetime.now)
    validated_at: Optional[datetime] = None
    consensus_threshold: int = 2
    attestations: Dict[str, Attestation] = field(default_factory=dict)
    valid_count: int = 0
    invalid_count: int = 0

    @property
    def total_attestations(self) -> int:
        return len(self.attestations)

    @property
    def has_consensus(self) -> bool:
        return (
            self.valid_count >= self.consensus_threshold or
            self.invalid_count >= self.consensus_threshold
        )

    def add_attestation(self, attestation: Attestation) -> bool:
        """Add attestation and check consensus."""
        if attestation.validator_address in self.attestations:
            return False  # Already attested

        self.attestations[attestation.validator_address] = attestation

        if attestation.is_valid:
            self.valid_count += 1
        else:
            self.invalid_count += 1

        # Check consensus
        if self.valid_count >= self.consensus_threshold:
            self.status = EventStatus.VERIFIED
            self.validated_at = datetime.now()
        elif self.invalid_count >= self.consensus_threshold:
            self.status = EventStatus.REJECTED
            self.validated_at = datetime.now()
        elif (
            self.valid_count > 0 and
            self.invalid_count > 0 and
            self.total_attestations >= self.consensus_threshold * 2
        ):
            self.status = EventStatus.DISPUTED
            self.validated_at = datetime.now()

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source.value,
            "status": self.status.value,
            "data": self.data.to_dict() if self.data else None,
            "dispute_id": self.dispute_id,
            "requester": self.requester,
            "requested_at": self.requested_at.isoformat(),
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "consensus_threshold": self.consensus_threshold,
            "attestations": {k: v.to_dict() for k, v in self.attestations.items()},
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
        }


class EventFetcher(ABC):
    """Abstract base class for event fetchers."""

    @abstractmethod
    async def fetch(self, uri: str, **kwargs) -> EventData:
        """Fetch event data from source."""
        pass

    @abstractmethod
    def validate_uri(self, uri: str) -> bool:
        """Validate the source URI format."""
        pass


class APIEventFetcher(EventFetcher):
    """Fetch events from REST APIs."""

    def __init__(
        self,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.timeout = timeout
        self.headers = headers or {}

    async def fetch(self, uri: str, json_path: Optional[str] = None, **kwargs) -> EventData:
        """Fetch data from API endpoint."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                uri,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Extract specific path if provided
                if json_path:
                    data = self._extract_json_path(data, json_path)

                # Calculate hash
                data_hash = hashlib.sha256(
                    json.dumps(data, sort_keys=True).encode()
                ).hexdigest()

                return EventData(
                    source=EventSource.API,
                    source_uri=uri,
                    raw_data=data,
                    data_hash=data_hash,
                    fetched_at=datetime.now(),
                    metadata={"json_path": json_path} if json_path else {},
                )

    def _extract_json_path(self, data: Any, path: str) -> Any:
        """Extract data using simple dot notation path."""
        parts = path.split(".")
        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            elif isinstance(data, list) and part.isdigit():
                data = data[int(part)]
            else:
                return None
        return data

    def validate_uri(self, uri: str) -> bool:
        return uri.startswith("http://") or uri.startswith("https://")


class IPFSEventFetcher(EventFetcher):
    """Fetch events from IPFS."""

    def __init__(self, gateway: str = "https://ipfs.io/ipfs/"):
        self.gateway = gateway

    async def fetch(self, uri: str, **kwargs) -> EventData:
        """Fetch data from IPFS."""
        # Extract CID from various IPFS URI formats
        cid = self._extract_cid(uri)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.gateway}{cid}",
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "json" in content_type:
                    data = await response.json()
                else:
                    data = {"content": await response.text()}

                data_hash = hashlib.sha256(
                    json.dumps(data, sort_keys=True).encode()
                ).hexdigest()

                return EventData(
                    source=EventSource.IPFS,
                    source_uri=uri,
                    raw_data=data,
                    data_hash=data_hash,
                    fetched_at=datetime.now(),
                    metadata={"cid": cid},
                )

    def _extract_cid(self, uri: str) -> str:
        """Extract CID from IPFS URI."""
        if uri.startswith("ipfs://"):
            return uri[7:]
        elif uri.startswith("/ipfs/"):
            return uri[6:]
        elif uri.startswith("Qm") or uri.startswith("bafy"):
            return uri
        return uri

    def validate_uri(self, uri: str) -> bool:
        return (
            uri.startswith("ipfs://") or
            uri.startswith("/ipfs/") or
            uri.startswith("Qm") or
            uri.startswith("bafy")
        )


class GitHubEventFetcher(EventFetcher):
    """Fetch events from GitHub API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"

    async def fetch(self, uri: str, **kwargs) -> EventData:
        """Fetch data from GitHub API."""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        # Parse GitHub URI
        endpoint = self._parse_github_uri(uri)

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                data = await response.json()

                data_hash = hashlib.sha256(
                    json.dumps(data, sort_keys=True).encode()
                ).hexdigest()

                return EventData(
                    source=EventSource.GITHUB,
                    source_uri=uri,
                    raw_data=data,
                    data_hash=data_hash,
                    fetched_at=datetime.now(),
                    metadata={"endpoint": endpoint},
                )

    def _parse_github_uri(self, uri: str) -> str:
        """Parse GitHub URI to API endpoint."""
        if uri.startswith("github://"):
            return uri[9:]
        if uri.startswith("https://github.com/"):
            # Convert web URL to API endpoint
            path = uri[19:]
            parts = path.split("/")
            if len(parts) >= 2:
                return f"repos/{parts[0]}/{parts[1]}"
        return uri

    def validate_uri(self, uri: str) -> bool:
        return (
            uri.startswith("github://") or
            uri.startswith("https://github.com/") or
            uri.startswith("repos/")
        )


class EventBridge:
    """
    Bridge for off-chain events to on-chain disputes.

    Manages event fetching, validation, and attestation submission.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        consensus_threshold: int = 2,
        attestation_window_hours: int = 24,
    ):
        self.data_dir = data_dir
        self.consensus_threshold = consensus_threshold
        self.attestation_window = timedelta(hours=attestation_window_hours)

        # Event storage
        self.events: Dict[str, BridgedEvent] = {}
        self.dispute_events: Dict[str, List[str]] = {}

        # Fetchers by source type
        self.fetchers: Dict[EventSource, EventFetcher] = {
            EventSource.API: APIEventFetcher(),
            EventSource.IPFS: IPFSEventFetcher(),
            EventSource.GITHUB: GitHubEventFetcher(),
        }

        # Validators
        self.registered_validators: Dict[str, Dict[str, Any]] = {}

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(12)}"

    # =========================================================================
    # Fetcher Management
    # =========================================================================

    def register_fetcher(self, source: EventSource, fetcher: EventFetcher) -> None:
        """Register a custom fetcher for a source type."""
        self.fetchers[source] = fetcher

    def get_fetcher(self, source: EventSource) -> Optional[EventFetcher]:
        """Get fetcher for source type."""
        return self.fetchers.get(source)

    # =========================================================================
    # Event Requests
    # =========================================================================

    async def request_event(
        self,
        source: EventSource,
        source_uri: str,
        dispute_id: Optional[str] = None,
        requester: Optional[str] = None,
        consensus_threshold: Optional[int] = None,
        fetch_immediately: bool = True,
    ) -> BridgedEvent:
        """
        Request verification of an off-chain event.

        Args:
            source: Type of event source
            source_uri: URI to event data
            dispute_id: Associated dispute ID (optional)
            requester: Address requesting the event
            consensus_threshold: Override default consensus threshold
            fetch_immediately: Whether to fetch data immediately

        Returns:
            Created BridgedEvent
        """
        event = BridgedEvent(
            event_id=self._generate_id("evt_"),
            source=source,
            status=EventStatus.PENDING,
            dispute_id=dispute_id,
            requester=requester,
            requested_at=datetime.now(),
            consensus_threshold=consensus_threshold or self.consensus_threshold,
        )

        # Fetch data if requested
        if fetch_immediately:
            fetcher = self.fetchers.get(source)
            if fetcher and fetcher.validate_uri(source_uri):
                try:
                    event.data = await fetcher.fetch(source_uri)
                except Exception as e:
                    event.data = EventData(
                        source=source,
                        source_uri=source_uri,
                        raw_data={"error": str(e)},
                        data_hash="",
                        fetched_at=datetime.now(),
                        metadata={"fetch_error": True},
                    )

        self.events[event.event_id] = event

        # Link to dispute
        if dispute_id:
            if dispute_id not in self.dispute_events:
                self.dispute_events[dispute_id] = []
            self.dispute_events[dispute_id].append(event.event_id)

        self._save_state()
        return event

    async def fetch_event_data(
        self,
        event_id: str,
        json_path: Optional[str] = None,
    ) -> Optional[EventData]:
        """
        Fetch or refresh data for an existing event.

        Args:
            event_id: Event ID
            json_path: Optional JSON path to extract specific data

        Returns:
            Fetched EventData or None
        """
        event = self.events.get(event_id)
        if not event:
            return None

        fetcher = self.fetchers.get(event.source)
        if not fetcher:
            return None

        source_uri = event.data.source_uri if event.data else ""
        if not source_uri:
            return None

        try:
            event.data = await fetcher.fetch(source_uri, json_path=json_path)
            self._save_state()
            return event.data
        except Exception:
            return None

    # =========================================================================
    # Attestations
    # =========================================================================

    def submit_attestation(
        self,
        event_id: str,
        validator_address: str,
        is_valid: bool,
        evidence_uri: str,
        signature: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[Attestation]:
        """
        Submit attestation for an event.

        Args:
            event_id: Event to attest
            validator_address: Validator's address
            is_valid: Whether validator confirms event validity
            evidence_uri: URI to attestation evidence
            signature: Optional cryptographic signature
            reason: Optional reason for attestation

        Returns:
            Created Attestation or None if failed
        """
        event = self.events.get(event_id)
        if not event:
            return None

        # Check event is still pending
        if event.status != EventStatus.PENDING:
            return None

        # Check attestation window
        if datetime.now() > event.requested_at + self.attestation_window:
            event.status = EventStatus.EXPIRED
            event.validated_at = datetime.now()
            self._save_state()
            return None

        # Calculate data hash
        data_hash = event.data.data_hash if event.data else ""

        attestation = Attestation(
            validator_address=validator_address,
            event_id=event_id,
            is_valid=is_valid,
            data_hash=data_hash,
            evidence_uri=evidence_uri,
            timestamp=datetime.now(),
            signature=signature,
            reason=reason,
        )

        if event.add_attestation(attestation):
            self._save_state()
            return attestation

        return None

    def get_attestations(self, event_id: str) -> List[Attestation]:
        """Get all attestations for an event."""
        event = self.events.get(event_id)
        if not event:
            return []
        return list(event.attestations.values())

    # =========================================================================
    # Validator Management
    # =========================================================================

    def register_validator(
        self,
        address: str,
        stake: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a validator."""
        self.registered_validators[address.lower()] = {
            "address": address.lower(),
            "stake": stake,
            "registered_at": datetime.now().isoformat(),
            "attestation_count": 0,
            "correct_count": 0,
            "metadata": metadata or {},
        }
        self._save_state()

    def is_registered_validator(self, address: str) -> bool:
        """Check if address is a registered validator."""
        return address.lower() in self.registered_validators

    def get_validator_stats(self, address: str) -> Optional[Dict[str, Any]]:
        """Get validator statistics."""
        return self.registered_validators.get(address.lower())

    def update_validator_accuracy(self, event_id: str) -> None:
        """Update validator accuracy after consensus."""
        event = self.events.get(event_id)
        if not event or event.status not in [EventStatus.VERIFIED, EventStatus.REJECTED]:
            return

        consensus_valid = event.status == EventStatus.VERIFIED

        for address, attestation in event.attestations.items():
            validator = self.registered_validators.get(address.lower())
            if validator:
                validator["attestation_count"] = validator.get("attestation_count", 0) + 1
                if attestation.is_valid == consensus_valid:
                    validator["correct_count"] = validator.get("correct_count", 0) + 1

        self._save_state()

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_event(self, event_id: str) -> Optional[BridgedEvent]:
        """Get event by ID."""
        return self.events.get(event_id)

    def get_dispute_events(self, dispute_id: str) -> List[BridgedEvent]:
        """Get all events linked to a dispute."""
        event_ids = self.dispute_events.get(dispute_id, [])
        return [self.events[eid] for eid in event_ids if eid in self.events]

    def list_events(
        self,
        status: Optional[EventStatus] = None,
        source: Optional[EventSource] = None,
        limit: int = 50,
    ) -> List[BridgedEvent]:
        """List events with optional filters."""
        events = list(self.events.values())

        if status:
            events = [e for e in events if e.status == status]
        if source:
            events = [e for e in events if e.source == source]

        events.sort(key=lambda e: e.requested_at, reverse=True)
        return events[:limit]

    def get_pending_events(self) -> List[BridgedEvent]:
        """Get all pending events."""
        return self.list_events(status=EventStatus.PENDING)

    def finalize_expired_events(self) -> List[str]:
        """Finalize events that have passed attestation window."""
        expired = []
        now = datetime.now()

        for event in self.events.values():
            if event.status != EventStatus.PENDING:
                continue
            if now > event.requested_at + self.attestation_window:
                event.status = EventStatus.EXPIRED
                event.validated_at = now
                expired.append(event.event_id)

        if expired:
            self._save_state()

        return expired

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        events = list(self.events.values())

        return {
            "total_events": len(events),
            "pending": len([e for e in events if e.status == EventStatus.PENDING]),
            "verified": len([e for e in events if e.status == EventStatus.VERIFIED]),
            "rejected": len([e for e in events if e.status == EventStatus.REJECTED]),
            "disputed": len([e for e in events if e.status == EventStatus.DISPUTED]),
            "expired": len([e for e in events if e.status == EventStatus.EXPIRED]),
            "by_source": {
                source.value: len([e for e in events if e.source == source])
                for source in EventSource
            },
            "total_validators": len(self.registered_validators),
            "total_attestations": sum(len(e.attestations) for e in events),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "events": {eid: e.to_dict() for eid, e in self.events.items()},
            "dispute_events": self.dispute_events,
            "validators": self.registered_validators,
            "config": {
                "consensus_threshold": self.consensus_threshold,
                "attestation_window_hours": self.attestation_window.total_seconds() / 3600,
            },
        }

        state_file = self.data_dir / "event_bridge_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        if not self.data_dir:
            return

        state_file = self.data_dir / "event_bridge_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            # Restore events
            for eid, edata in state.get("events", {}).items():
                event = BridgedEvent(
                    event_id=edata["event_id"],
                    source=EventSource(edata["source"]),
                    status=EventStatus(edata["status"]),
                    dispute_id=edata.get("dispute_id"),
                    requester=edata.get("requester"),
                    requested_at=datetime.fromisoformat(edata["requested_at"]),
                    consensus_threshold=edata.get("consensus_threshold", 2),
                    valid_count=edata.get("valid_count", 0),
                    invalid_count=edata.get("invalid_count", 0),
                )
                if edata.get("validated_at"):
                    event.validated_at = datetime.fromisoformat(edata["validated_at"])

                # Restore attestations
                for vaddr, att_data in edata.get("attestations", {}).items():
                    event.attestations[vaddr] = Attestation(
                        validator_address=att_data["validator_address"],
                        event_id=att_data["event_id"],
                        is_valid=att_data["is_valid"],
                        data_hash=att_data["data_hash"],
                        evidence_uri=att_data["evidence_uri"],
                        timestamp=datetime.fromisoformat(att_data["timestamp"]),
                        signature=att_data.get("signature"),
                        reason=att_data.get("reason"),
                    )

                self.events[eid] = event

            self.dispute_events = state.get("dispute_events", {})
            self.registered_validators = state.get("validators", {})

            config = state.get("config", {})
            self.consensus_threshold = config.get("consensus_threshold", 2)
            self.attestation_window = timedelta(
                hours=config.get("attestation_window_hours", 24)
            )

        except (json.JSONDecodeError, KeyError):
            pass


def create_event_bridge(
    data_dir: Optional[str] = None,
    consensus_threshold: int = 2,
    attestation_window_hours: int = 24,
) -> EventBridge:
    """Factory function to create an event bridge."""
    path = Path(data_dir) if data_dir else None
    return EventBridge(
        data_dir=path,
        consensus_threshold=consensus_threshold,
        attestation_window_hours=attestation_window_hours,
    )
