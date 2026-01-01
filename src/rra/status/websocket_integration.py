# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
WebSocket Integration for Dreaming Status.

Provides WebSocket broadcasting for dreaming status updates,
allowing web GUI clients to receive real-time status updates.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set, Dict, Any, Optional
from dataclasses import dataclass

from fastapi import WebSocket

from rra.status.dreaming import get_dreaming_status, StatusEntry, StatusType

logger = logging.getLogger(__name__)


@dataclass
class DreamingMessage:
    """Message format for dreaming WebSocket updates."""
    type: str = "dreaming"
    payload: Dict[str, Any] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if self.payload is None:
            self.payload = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class DreamingWebSocketManager:
    """
    Manages WebSocket connections for dreaming status updates.

    Broadcasts status updates to all connected clients.
    """

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._dreaming = get_dreaming_status()
        self._callback_registered = False

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection for dreaming updates."""
        await websocket.accept()
        self._connections.add(websocket)
        logger.debug(f"Dreaming WebSocket connected. Total: {len(self._connections)}")

        # Register callback if not already done
        if not self._callback_registered:
            self._dreaming.add_async_callback(self._broadcast_status)
            self._callback_registered = True

        # Send current status on connect
        current = self._dreaming.current_status
        if current:
            await self._send_to_client(websocket, DreamingMessage(
                payload={
                    "status": current,
                    "operation": self._dreaming.current_operation,
                }
            ))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections.discard(websocket)
        logger.debug(f"Dreaming WebSocket disconnected. Total: {len(self._connections)}")

    async def _send_to_client(self, websocket: WebSocket, message: DreamingMessage) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message.to_dict())
        except Exception as e:
            logger.warning(f"Failed to send dreaming update: {e}")
            self._connections.discard(websocket)

    async def _broadcast_status(self, entry: StatusEntry) -> None:
        """Broadcast a status update to all connected clients."""
        if not self._connections:
            return

        message = DreamingMessage(
            payload={
                "operation": entry.operation,
                "type": entry.status_type.value,
                "status": entry.format_message(),
                "duration_ms": entry.duration_ms,
                "details": entry.details,
            }
        )

        # Create tasks for all connections
        tasks = [
            self._send_to_client(ws, message)
            for ws in list(self._connections)
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_current_status(self) -> None:
        """Broadcast the current status to all clients."""
        if not self._connections:
            return

        current = self._dreaming.current_status
        message = DreamingMessage(
            payload={
                "status": current or "Idle",
                "operation": self._dreaming.current_operation,
                "active_operations": self._dreaming.get_active_operations(),
            }
        )

        tasks = [
            self._send_to_client(ws, message)
            for ws in list(self._connections)
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_connection_count(self) -> int:
        """Get the number of connected clients."""
        return len(self._connections)


# Global manager instance
_dreaming_ws_manager: Optional[DreamingWebSocketManager] = None


def get_dreaming_ws_manager() -> DreamingWebSocketManager:
    """Get the global dreaming WebSocket manager."""
    global _dreaming_ws_manager
    if _dreaming_ws_manager is None:
        _dreaming_ws_manager = DreamingWebSocketManager()
    return _dreaming_ws_manager
