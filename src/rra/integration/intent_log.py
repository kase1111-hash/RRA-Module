# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Integration with IntentLog for agent intent and decision auditing.

Provides audit trails for agent negotiations and decisions when
running in integrated mode.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

from rra.integration.base import IntentLoggerProtocol
from rra.integration.config import get_integration_config


class LocalIntentLogger:
    """
    Local file-based intent logger (standalone fallback).

    Logs intents and decisions to local JSON files for auditing.
    """

    def __init__(self, agent_id: str, log_dir: Optional[Path] = None):
        """
        Initialize local intent logger.

        Args:
            agent_id: Unique agent identifier
            log_dir: Directory for log files (default: ./intent_logs)
        """
        self.agent_id = agent_id
        self.log_dir = log_dir or Path("./intent_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file for this agent
        timestamp = datetime.now().strftime("%Y%m%d")
        self.log_file = self.log_dir / f"{agent_id}_{timestamp}.jsonl"

    def log_intent(self, intent: str, context: Dict[str, Any]) -> None:
        """Log an agent intent to file."""
        entry = {
            "type": "intent",
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
            "context": context,
        }

        self._append_log(entry)

    def log_decision(self, decision: str, rationale: Dict[str, Any]) -> None:
        """Log an agent decision to file."""
        entry = {
            "type": "decision",
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "rationale": rationale,
        }

        self._append_log(entry)

    def _append_log(self, entry: Dict[str, Any]) -> None:
        """Append entry to log file (JSONL format)."""
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent log entries."""
        if not self.log_file.exists():
            return []

        logs = []
        with open(self.log_file, "r") as f:
            for line in f:
                logs.append(json.loads(line.strip()))

        return logs[-limit:]


class IntentLogService:
    """
    Integration with IntentLog service for distributed audit trails.

    Uses IntentLog when available for cross-agent auditing and analytics.
    """

    def __init__(self, agent_id: str, service_url: Optional[str] = None):
        """
        Initialize IntentLog service integration.

        Args:
            agent_id: Unique agent identifier
            service_url: URL of IntentLog service
        """
        self.agent_id = agent_id
        self.service_url = service_url or get_integration_config().intent_log_url

        # Try to import IntentLog client
        try:
            from intent_log import IntentLogClient  # type: ignore

            self.client = IntentLogClient(url=self.service_url, agent_id=agent_id)
            self.available = True
        except ImportError:
            self.available = False
            self._fallback = LocalIntentLogger(agent_id)

    def log_intent(self, intent: str, context: Dict[str, Any]) -> None:
        """Log intent to IntentLog service."""
        if not self.available:
            self._fallback.log_intent(intent, context)
            return

        try:
            self.client.record_intent(intent=intent, context=context, timestamp=datetime.now())
        except Exception as e:
            logger.warning(f"Failed to log intent to IntentLog: {e}")
            if not hasattr(self, "_fallback"):
                self._fallback = LocalIntentLogger(self.agent_id)
            self._fallback.log_intent(intent, context)

    def log_decision(self, decision: str, rationale: Dict[str, Any]) -> None:
        """Log decision to IntentLog service."""
        if not self.available:
            self._fallback.log_decision(decision, rationale)
            return

        try:
            self.client.record_decision(
                decision=decision, rationale=rationale, timestamp=datetime.now()
            )
        except Exception as e:
            logger.warning(f"Failed to log decision to IntentLog: {e}")
            if not hasattr(self, "_fallback"):
                self._fallback = LocalIntentLogger(self.agent_id)
            self._fallback.log_decision(decision, rationale)


def get_intent_logger(agent_id: str, prefer_service: bool = True) -> IntentLoggerProtocol:
    """
    Get appropriate intent logger based on configuration.

    Args:
        agent_id: Unique agent identifier
        prefer_service: Prefer IntentLog service if available

    Returns:
        Intent logger instance (IntentLog or Local)
    """
    config = get_integration_config()

    if config.enable_intent_log and prefer_service:
        logger = IntentLogService(agent_id, config.intent_log_url)
        if logger.available:
            return logger

    return LocalIntentLogger(agent_id)
