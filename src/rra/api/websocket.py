# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
WebSocket handler for real-time negotiation chat.

Provides bidirectional communication for:
- Real-time message exchange
- Typing indicators
- Phase change notifications
- Offer updates
"""

import json
import asyncio
import logging
import os
import hmac
from typing import Dict, Set, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

from rra.ingestion.knowledge_base import KnowledgeBase
from rra.agents.negotiator import NegotiatorAgent
from rra.exceptions import IntegrationError, ValidationError, ErrorCode
from rra.status.websocket_integration import get_dreaming_ws_manager
from rra.status.dreaming import get_dreaming_status

logger = logging.getLogger(__name__)


router = APIRouter(tags=["websocket"])


# Message types
class WSMessage(BaseModel):
    type: str  # message, typing, phase_change, offer, error
    payload: dict
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)


# Connection manager
class ConnectionManager:
    """Manage WebSocket connections for negotiation sessions."""

    def __init__(self):
        # repo_id -> set of connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # session_id -> NegotiatorAgent
        self.agents: Dict[str, NegotiatorAgent] = {}
        # websocket -> session_id
        self.sessions: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, repo_id: str, session_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if repo_id not in self.active_connections:
            self.active_connections[repo_id] = set()

        self.active_connections[repo_id].add(websocket)
        self.sessions[websocket] = session_id

    def disconnect(self, websocket: WebSocket, repo_id: str):
        """Remove a WebSocket connection."""
        if repo_id in self.active_connections:
            self.active_connections[repo_id].discard(websocket)

        if websocket in self.sessions:
            del self.sessions[websocket]

    async def send_message(self, websocket: WebSocket, message: WSMessage):
        """Send a message to a specific connection."""
        await websocket.send_json(message.model_dump())

    async def broadcast(self, repo_id: str, message: WSMessage):
        """Broadcast a message to all connections for a repo."""
        if repo_id in self.active_connections:
            for connection in self.active_connections[repo_id]:
                try:
                    await connection.send_json(message.model_dump())
                except Exception as e:
                    logger.warning(f"Failed to broadcast message to connection: {e}")

    def get_or_create_agent(self, session_id: str, kb: KnowledgeBase) -> NegotiatorAgent:
        """Get existing agent or create new one for session."""
        if session_id not in self.agents:
            self.agents[session_id] = NegotiatorAgent(kb)
        return self.agents[session_id]


manager = ConnectionManager()


def _validate_ws_api_key(api_key: Optional[str]) -> bool:
    """
    Validate API key for WebSocket connections.

    Args:
        api_key: API key from query parameter

    Returns:
        True if valid, False otherwise
    """
    if api_key is None:
        return False

    # Get valid API keys from environment
    api_keys_env = os.environ.get("RRA_API_KEYS", "")
    if not api_keys_env:
        api_keys_env = os.environ.get("RRA_API_KEY", "")

    if not api_keys_env:
        # Development mode - accept any non-empty key
        if os.environ.get("RRA_DEV_MODE", "").lower() == "true":
            return True
        return False

    valid_keys = [k.strip() for k in api_keys_env.split(",") if k.strip()]

    # Constant-time comparison
    for valid_key in valid_keys:
        if hmac.compare_digest(api_key, valid_key):
            return True

    return False


@router.websocket("/ws/negotiate/{repo_id}")
async def websocket_negotiate(
    websocket: WebSocket,
    repo_id: str,
    api_key: Optional[str] = Query(None, alias="api_key"),
):
    """
    WebSocket endpoint for real-time negotiation.

    Message Protocol:
    - Client sends: {"type": "message", "payload": {"content": "..."}}
    - Server sends: {"type": "message", "payload": {"role": "agent", "content": "..."}}
    - Server sends: {"type": "typing", "payload": {"is_typing": true/false}}
    - Server sends: {"type": "phase_change", "payload": {"phase": "..."}}

    Args:
        websocket: WebSocket connection
        repo_id: Repository ID to negotiate for
        api_key: API key for authentication (query parameter)
    """
    # Validate API key before accepting connection
    if not _validate_ws_api_key(api_key):
        await websocket.accept()
        await websocket.send_json(
            WSMessage(
                type="error", payload={"message": "Unauthorized: Invalid or missing API key"}
            ).model_dump()
        )
        await websocket.close(code=4001)  # Custom close code for auth failure
        return

    session_id = str(uuid.uuid4())

    # Try to load knowledge base
    kb = await load_knowledge_base(repo_id)
    if not kb:
        await websocket.accept()
        await websocket.send_json(
            WSMessage(type="error", payload={"message": "Repository not found"}).model_dump()
        )
        await websocket.close()
        return

    await manager.connect(websocket, repo_id, session_id)

    try:
        # Get or create agent
        agent = manager.get_or_create_agent(session_id, kb)

        # Send initial greeting
        intro = agent.start_negotiation()
        await manager.send_message(
            websocket,
            WSMessage(
                type="message",
                payload={
                    "id": str(uuid.uuid4()),
                    "role": "agent",
                    "content": intro,
                },
            ),
        )

        # Send initial phase
        await manager.send_message(
            websocket, WSMessage(type="phase_change", payload={"phase": agent.current_phase.value})
        )

        # Listen for messages
        while True:
            try:
                data = await websocket.receive_json()

                if data.get("type") == "message":
                    content = data.get("payload", {}).get("content", "")

                    if content:
                        dreaming = get_dreaming_status()

                        # Send typing indicator
                        await manager.send_message(
                            websocket, WSMessage(type="typing", payload={"is_typing": True})
                        )

                        # Small delay to simulate thinking
                        await asyncio.sleep(0.5)

                        # Get agent response
                        dreaming.start("Processing negotiation message")
                        response = agent.respond(content)
                        dreaming.complete("Processing negotiation message")

                        # Send typing done
                        await manager.send_message(
                            websocket, WSMessage(type="typing", payload={"is_typing": False})
                        )

                        # Send response
                        await manager.send_message(
                            websocket,
                            WSMessage(
                                type="message",
                                payload={
                                    "id": str(uuid.uuid4()),
                                    "role": "agent",
                                    "content": response,
                                },
                            ),
                        )

                        # Send phase update if changed
                        await manager.send_message(
                            websocket,
                            WSMessage(
                                type="phase_change", payload={"phase": agent.current_phase.value}
                            ),
                        )

                elif data.get("type") == "accept_offer":
                    # Handle offer acceptance
                    summary = agent.get_negotiation_summary()
                    await manager.send_message(
                        websocket,
                        WSMessage(
                            type="offer",
                            payload={
                                "accepted": True,
                                "summary": summary,
                                "transaction_data": {
                                    "amount": (
                                        kb.market_config.target_price
                                        if kb.market_config
                                        else "0.05 ETH"
                                    ),
                                    "recipient": (
                                        kb.market_config.developer_wallet
                                        if kb.market_config
                                        and hasattr(kb.market_config, "developer_wallet")
                                        else None
                                    ),
                                },
                            },
                        ),
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: session={session_id}")
                break
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received in WebSocket: {e}")
                await manager.send_message(
                    websocket,
                    WSMessage(
                        type="error",
                        payload={
                            "message": "Invalid JSON",
                            "code": ErrorCode.VALIDATION_ERROR.value,
                        },
                    ),
                )
            except Exception as e:
                logger.error(f"WebSocket error in session {session_id}: {e}")
                await manager.send_message(
                    websocket,
                    WSMessage(
                        type="error",
                        payload={"message": str(e), "code": ErrorCode.UNKNOWN_ERROR.value},
                    ),
                )

    finally:
        manager.disconnect(websocket, repo_id)


async def load_knowledge_base(repo_id: str) -> Optional[KnowledgeBase]:
    """Load knowledge base by repo ID."""
    from pathlib import Path
    import hashlib

    kb_dir = Path("agent_knowledge_bases")
    if not kb_dir.exists():
        return None

    for kb_file in kb_dir.glob("*_kb.json"):
        try:
            kb = KnowledgeBase.load(kb_file)
            # Generate ID from URL and compare
            normalized = kb.repo_url.lower().strip().rstrip(".git")
            generated_id = hashlib.sha256(normalized.encode()).hexdigest()[:12]
            if generated_id == repo_id:
                return kb
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.debug(f"Could not load knowledge base {kb_file}: {e}")
            continue

    return None


@router.websocket("/ws/dreaming")
async def websocket_dreaming(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None, alias="api_key"),
):
    """
    WebSocket endpoint for dreaming status updates.

    Provides real-time visibility into what the system is doing.
    Updates are throttled to every 5 seconds to minimize overhead.

    Message Protocol:
    - Server sends: {"type": "dreaming", "payload": {"status": "...", "operation": "..."}}

    Args:
        websocket: WebSocket connection
        api_key: API key for authentication (query parameter)
    """
    # Validate API key
    if not _validate_ws_api_key(api_key):
        await websocket.accept()
        await websocket.send_json(
            {"type": "error", "payload": {"message": "Unauthorized: Invalid or missing API key"}}
        )
        await websocket.close(code=4001)
        return

    dreaming_manager = get_dreaming_ws_manager()
    await dreaming_manager.connect(websocket)

    try:
        # Keep connection alive and listen for messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle ping/pong for keepalive
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                # Handle status request
                elif data.get("type") == "get_status":
                    dreaming = get_dreaming_status()
                    await websocket.send_json(
                        {
                            "type": "dreaming",
                            "payload": {
                                "status": dreaming.current_status or "Idle",
                                "operation": dreaming.current_operation,
                                "active_operations": dreaming.get_active_operations(),
                                "history": [e.to_dict() for e in dreaming.get_history(10)],
                            },
                        }
                    )

                # Handle history request
                elif data.get("type") == "get_history":
                    limit = data.get("payload", {}).get("limit", 10)
                    dreaming = get_dreaming_status()
                    await websocket.send_json(
                        {
                            "type": "dreaming_history",
                            "payload": {
                                "entries": [e.to_dict() for e in dreaming.get_history(limit)],
                            },
                        }
                    )

            except WebSocketDisconnect:
                logger.info("Dreaming WebSocket disconnected")
                break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "payload": {"message": "Invalid JSON"}})
            except Exception as e:
                logger.error(f"Dreaming WebSocket error: {e}")
                await websocket.send_json({"type": "error", "payload": {"message": str(e)}})

    finally:
        dreaming_manager.disconnect(websocket)
