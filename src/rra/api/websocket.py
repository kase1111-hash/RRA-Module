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
from typing import Dict, Set, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from rra.ingestion.knowledge_base import KnowledgeBase
from rra.agents.negotiator import NegotiatorAgent


router = APIRouter(tags=["websocket"])


# Message types
class WSMessage(BaseModel):
    type: str  # message, typing, phase_change, offer, error
    payload: dict
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get('timestamp'):
            data['timestamp'] = datetime.utcnow().isoformat()
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
                except Exception:
                    pass

    def get_or_create_agent(
        self,
        session_id: str,
        kb: KnowledgeBase
    ) -> NegotiatorAgent:
        """Get existing agent or create new one for session."""
        if session_id not in self.agents:
            self.agents[session_id] = NegotiatorAgent(kb)
        return self.agents[session_id]


manager = ConnectionManager()


@router.websocket("/ws/negotiate/{repo_id}")
async def websocket_negotiate(websocket: WebSocket, repo_id: str):
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
    """
    session_id = str(uuid.uuid4())

    # Try to load knowledge base
    kb = await load_knowledge_base(repo_id)
    if not kb:
        await websocket.accept()
        await websocket.send_json(WSMessage(
            type="error",
            payload={"message": "Repository not found"}
        ).model_dump())
        await websocket.close()
        return

    await manager.connect(websocket, repo_id, session_id)

    try:
        # Get or create agent
        agent = manager.get_or_create_agent(session_id, kb)

        # Send initial greeting
        intro = agent.start_negotiation()
        await manager.send_message(websocket, WSMessage(
            type="message",
            payload={
                "id": str(uuid.uuid4()),
                "role": "agent",
                "content": intro,
            }
        ))

        # Send initial phase
        await manager.send_message(websocket, WSMessage(
            type="phase_change",
            payload={"phase": agent.current_phase.value}
        ))

        # Listen for messages
        while True:
            try:
                data = await websocket.receive_json()

                if data.get("type") == "message":
                    content = data.get("payload", {}).get("content", "")

                    if content:
                        # Send typing indicator
                        await manager.send_message(websocket, WSMessage(
                            type="typing",
                            payload={"is_typing": True}
                        ))

                        # Small delay to simulate thinking
                        await asyncio.sleep(0.5)

                        # Get agent response
                        response = agent.respond(content)

                        # Send typing done
                        await manager.send_message(websocket, WSMessage(
                            type="typing",
                            payload={"is_typing": False}
                        ))

                        # Send response
                        await manager.send_message(websocket, WSMessage(
                            type="message",
                            payload={
                                "id": str(uuid.uuid4()),
                                "role": "agent",
                                "content": response,
                            }
                        ))

                        # Send phase update if changed
                        await manager.send_message(websocket, WSMessage(
                            type="phase_change",
                            payload={"phase": agent.current_phase.value}
                        ))

                elif data.get("type") == "accept_offer":
                    # Handle offer acceptance
                    summary = agent.get_negotiation_summary()
                    await manager.send_message(websocket, WSMessage(
                        type="offer",
                        payload={
                            "accepted": True,
                            "summary": summary,
                            "transaction_data": {
                                "amount": kb.market_config.target_price if kb.market_config else "0.05 ETH",
                                "recipient": kb.market_config.developer_wallet if kb.market_config and hasattr(kb.market_config, 'developer_wallet') else None,
                            }
                        }
                    ))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_message(websocket, WSMessage(
                    type="error",
                    payload={"message": "Invalid JSON"}
                ))
            except Exception as e:
                await manager.send_message(websocket, WSMessage(
                    type="error",
                    payload={"message": str(e)}
                ))

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
            normalized = kb.repo_url.lower().strip().rstrip('.git')
            generated_id = hashlib.sha256(normalized.encode()).hexdigest()[:12]
            if generated_id == repo_id:
                return kb
        except Exception:
            continue

    return None
