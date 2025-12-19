# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Webhook API endpoints for RRA Module.

Provides REST API endpoints for:
- Triggering agent negotiations from external systems
- Managing webhook credentials
- Session tracking and callbacks

Supports use cases:
- Company websites ("License Our SDK" buttons)
- Developer portfolios ("Hire/License" links)
- CRM integrations (lead qualification)
- Landing pages (embedded forms)
"""

import uuid
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel, EmailStr

from rra.security.webhook_auth import (
    WebhookSecurity,
    RateLimiter,
    validate_callback_url,
    webhook_security,
    rate_limiter,
)
from rra.services.deep_links import DeepLinkService
from rra.ingestion.knowledge_base import KnowledgeBase
from rra.agents.negotiator import NegotiatorAgent


# =============================================================================
# Security Constants
# =============================================================================

MAX_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1MB max payload size


router = APIRouter(prefix="/webhook", tags=["webhooks"])

# Session storage (in production, use Redis or database)
_webhook_sessions: Dict[str, Dict[str, Any]] = {}
_session_messages: Dict[str, List[Dict[str, Any]]] = {}


# Request/Response models
class WebhookTriggerRequest(BaseModel):
    """Incoming webhook trigger payload."""
    message: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    company: Optional[str] = None
    budget: Optional[str] = None
    use_case: Optional[str] = None
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WebhookTriggerResponse(BaseModel):
    """Response from webhook trigger."""
    status: str
    session_id: str
    chat_url: str
    message: Optional[str] = None


class WebhookCredentialsRequest(BaseModel):
    """Request to generate webhook credentials."""
    agent_id: str
    allowed_ips: Optional[List[str]] = None


class WebhookCredentialsResponse(BaseModel):
    """Webhook credentials response."""
    agent_id: str
    webhook_url: str
    secret_key: str
    rate_limit: str
    created_at: str


class SessionStatusResponse(BaseModel):
    """Webhook session status."""
    session_id: str
    agent_id: str
    status: str
    phase: Optional[str] = None
    messages_count: int
    created_at: str
    last_activity: str


class SessionMessageRequest(BaseModel):
    """Message to send to a webhook session."""
    content: str


class SessionMessageResponse(BaseModel):
    """Response from session message."""
    session_id: str
    response: str
    phase: str


# Helper functions
def generate_session_id() -> str:
    """
    Generate a cryptographically secure session ID.

    Uses 256 bits of entropy for security against brute-force attacks.
    """
    import secrets
    return f"wh_{secrets.token_urlsafe(32)}"


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.

    Args:
        session_id: Session ID to validate

    Returns:
        True if valid format
    """
    import re
    if not session_id:
        return False

    # Must start with wh_ prefix and have sufficient length
    if not session_id.startswith("wh_"):
        return False

    token_part = session_id[3:]
    if len(token_part) < 20:  # Minimum reasonable length
        return False

    # Must be URL-safe characters only
    if not re.match(r'^[\w\-]+$', token_part):
        return False

    return True


async def load_knowledge_base(agent_id: str) -> Optional[KnowledgeBase]:
    """Load knowledge base by agent/repo ID."""
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
            if generated_id == agent_id:
                return kb
        except Exception:
            continue

    return None


async def process_webhook_negotiation(
    agent_id: str,
    session_id: str,
    payload: WebhookTriggerRequest,
) -> Optional[str]:
    """
    Process a webhook-initiated negotiation in the background.

    Args:
        agent_id: The agent/repo ID
        session_id: The webhook session ID
        payload: The webhook trigger payload

    Returns:
        Initial agent response or None on error
    """
    try:
        # Load knowledge base
        kb = await load_knowledge_base(agent_id)
        if not kb:
            _webhook_sessions[session_id]["status"] = "error"
            _webhook_sessions[session_id]["error"] = "Agent not found"
            return None

        # Create negotiator agent
        negotiator = NegotiatorAgent(kb)

        # Store agent reference (in production, use proper state management)
        _webhook_sessions[session_id]["agent"] = negotiator
        _webhook_sessions[session_id]["status"] = "active"

        # Start negotiation
        intro = negotiator.start_negotiation()
        _webhook_sessions[session_id]["phase"] = negotiator.current_phase.value

        # Record initial message
        _session_messages[session_id] = [
            {
                "id": str(uuid.uuid4()),
                "role": "agent",
                "content": intro,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ]

        # If buyer sent an initial message, respond to it
        if payload.message:
            # Record buyer message
            _session_messages[session_id].append({
                "id": str(uuid.uuid4()),
                "role": "buyer",
                "content": payload.message,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Get agent response
            response = negotiator.respond(payload.message)
            _session_messages[session_id].append({
                "id": str(uuid.uuid4()),
                "role": "agent",
                "content": response,
                "timestamp": datetime.utcnow().isoformat(),
            })
            _webhook_sessions[session_id]["phase"] = negotiator.current_phase.value

            # Send callback if provided
            if payload.callback_url:
                await send_callback(
                    payload.callback_url,
                    {
                        "session_id": session_id,
                        "agent_id": agent_id,
                        "response": response,
                        "phase": negotiator.current_phase.value,
                    }
                )

            return response

        return intro

    except Exception as e:
        _webhook_sessions[session_id]["status"] = "error"
        _webhook_sessions[session_id]["error"] = str(e)
        return None


async def send_callback(callback_url: str, data: dict) -> None:
    """
    Send a callback to the specified URL.

    Args:
        callback_url: URL to send callback to (must pass SSRF validation)
        data: JSON data to send

    Note:
        URL is validated to prevent SSRF attacks
    """
    import httpx

    # Security: Validate URL to prevent SSRF
    if not validate_callback_url(callback_url):
        # Log but don't raise - don't reveal validation failure
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                callback_url,
                json=data,
                timeout=10.0,
            )
    except Exception:
        # Log error but don't fail the webhook
        pass


# Endpoints
@router.post("/{agent_id}", response_model=WebhookTriggerResponse)
async def webhook_trigger(
    agent_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_signature: Optional[str] = Header(None),
) -> WebhookTriggerResponse:
    """
    Universal webhook endpoint for external integrations.

    Triggers a new negotiation session with an agent from external systems.

    Supported use cases:
    - Company websites ("License Our SDK" buttons)
    - Developer portfolios ("Hire/License" links)
    - CRM integrations (lead qualification)
    - Landing pages (embedded forms)

    Args:
        agent_id: The agent/repo ID (12-character hex)
        request: FastAPI request object
        x_webhook_signature: HMAC-SHA256 signature (optional for registered webhooks)

    Returns:
        Session ID and chat URL for continuing the negotiation
    """
    try:
        payload_dict = await request.json()
        payload = WebhookTriggerRequest(**payload_dict)
    except Exception:
        raise HTTPException(400, "Invalid request payload")

    # Check if agent has registered webhook credentials
    creds = webhook_security.get_credentials(agent_id)

    if creds:
        # Verify signature for registered webhooks
        if not x_webhook_signature:
            raise HTTPException(401, "Missing webhook signature")

        if not webhook_security.verify_signature(agent_id, payload_dict, x_webhook_signature):
            raise HTTPException(403, "Invalid webhook signature")

        # Check IP allowlist
        client_ip = request.client.host if request.client else "unknown"
        if not webhook_security.verify_ip(agent_id, client_ip):
            raise HTTPException(403, "IP not in allowlist")

    # Check rate limit
    if not rate_limiter.record(agent_id):
        remaining = rate_limiter.get_remaining(agent_id)
        reset_time = rate_limiter.get_reset_time(agent_id)
        raise HTTPException(
            429,
            f"Rate limit exceeded. Remaining: {remaining}. Reset: {reset_time.isoformat() if reset_time else 'N/A'}"
        )

    # Generate session
    session_id = generate_session_id()
    link_service = DeepLinkService()

    # Store session info
    _webhook_sessions[session_id] = {
        "agent_id": agent_id,
        "status": "initializing",
        "created_at": datetime.utcnow().isoformat(),
        "last_activity": datetime.utcnow().isoformat(),
        "buyer_email": payload.email,
        "buyer_name": payload.name,
        "buyer_company": payload.company,
        "metadata": payload.metadata,
    }

    # Process negotiation in background
    background_tasks.add_task(
        process_webhook_negotiation,
        agent_id=agent_id,
        session_id=session_id,
        payload=payload,
    )

    return WebhookTriggerResponse(
        status="processing",
        session_id=session_id,
        chat_url=f"{link_service.base_url}/session/{session_id}",
        message="Negotiation session initiated. Use the chat_url to continue the conversation.",
    )


@router.get("/session/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str) -> SessionStatusResponse:
    """
    Get the status of a webhook session.

    Args:
        session_id: The session ID from webhook_trigger

    Returns:
        Session status and metadata
    """
    session = _webhook_sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    messages = _session_messages.get(session_id, [])

    return SessionStatusResponse(
        session_id=session_id,
        agent_id=session["agent_id"],
        status=session["status"],
        phase=session.get("phase"),
        messages_count=len(messages),
        created_at=session["created_at"],
        last_activity=session["last_activity"],
    )


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str) -> dict:
    """
    Get all messages from a webhook session.

    Args:
        session_id: The session ID

    Returns:
        List of messages in the session
    """
    if session_id not in _webhook_sessions:
        raise HTTPException(404, "Session not found")

    return {
        "session_id": session_id,
        "messages": _session_messages.get(session_id, []),
    }


@router.post("/session/{session_id}/message", response_model=SessionMessageResponse)
async def send_session_message(
    session_id: str,
    message: SessionMessageRequest,
) -> SessionMessageResponse:
    """
    Send a message to a webhook session.

    Args:
        session_id: The session ID
        message: Message content

    Returns:
        Agent response
    """
    session = _webhook_sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    if session["status"] != "active":
        raise HTTPException(400, f"Session is not active: {session['status']}")

    agent = session.get("agent")
    if not agent:
        raise HTTPException(500, "Agent not initialized")

    # Record buyer message
    if session_id not in _session_messages:
        _session_messages[session_id] = []

    _session_messages[session_id].append({
        "id": str(uuid.uuid4()),
        "role": "buyer",
        "content": message.content,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Get response
    response = agent.respond(message.content)

    # Record agent response
    _session_messages[session_id].append({
        "id": str(uuid.uuid4()),
        "role": "agent",
        "content": response,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Update session
    session["phase"] = agent.current_phase.value
    session["last_activity"] = datetime.utcnow().isoformat()

    return SessionMessageResponse(
        session_id=session_id,
        response=response,
        phase=agent.current_phase.value,
    )


@router.post("/credentials", response_model=WebhookCredentialsResponse)
async def generate_credentials(
    request: WebhookCredentialsRequest,
) -> WebhookCredentialsResponse:
    """
    Generate webhook credentials for an agent.

    This creates a secret key for signing webhook payloads and
    configures rate limiting.

    Args:
        request: Agent ID and optional IP allowlist

    Returns:
        Webhook URL and secret key
    """
    # Verify agent exists
    kb = await load_knowledge_base(request.agent_id)
    if not kb:
        raise HTTPException(404, "Agent not found")

    creds = webhook_security.generate_credentials(
        agent_id=request.agent_id,
        allowed_ips=request.allowed_ips,
    )

    return WebhookCredentialsResponse(
        agent_id=creds["agent_id"],
        webhook_url=creds["webhook_url"],
        secret_key=creds["secret_key"],
        rate_limit=creds["rate_limit"],
        created_at=creds["created_at"],
    )


@router.get("/credentials/{agent_id}")
async def get_credentials(agent_id: str) -> dict:
    """
    Get webhook configuration for an agent (without secret key).

    Args:
        agent_id: The agent/repo ID

    Returns:
        Webhook configuration
    """
    creds = webhook_security.get_credentials(agent_id)
    if not creds:
        raise HTTPException(404, "No webhook credentials for this agent")

    return creds


@router.post("/credentials/{agent_id}/rotate")
async def rotate_credentials(agent_id: str) -> dict:
    """
    Rotate the webhook secret key for an agent.

    Args:
        agent_id: The agent/repo ID

    Returns:
        New secret key
    """
    new_secret = webhook_security.rotate_secret(agent_id)
    if not new_secret:
        raise HTTPException(404, "No webhook credentials for this agent")

    return {
        "agent_id": agent_id,
        "new_secret_key": new_secret,
        "message": "Secret key rotated. Update your integration with the new key.",
    }


@router.delete("/credentials/{agent_id}")
async def revoke_credentials(agent_id: str) -> dict:
    """
    Revoke webhook credentials for an agent.

    Args:
        agent_id: The agent/repo ID

    Returns:
        Confirmation message
    """
    if not webhook_security.revoke_credentials(agent_id):
        raise HTTPException(404, "No webhook credentials for this agent")

    return {
        "agent_id": agent_id,
        "message": "Webhook credentials revoked",
    }


@router.get("/rate-limit/{agent_id}")
async def get_rate_limit_status(agent_id: str) -> dict:
    """
    Get rate limit status for an agent.

    Args:
        agent_id: The agent/repo ID

    Returns:
        Rate limit info
    """
    remaining = rate_limiter.get_remaining(agent_id)
    reset_time = rate_limiter.get_reset_time(agent_id)

    return {
        "agent_id": agent_id,
        "remaining": remaining,
        "limit": rate_limiter.max_requests,
        "window_minutes": rate_limiter.window_minutes,
        "reset_at": reset_time.isoformat() if reset_time else None,
    }
