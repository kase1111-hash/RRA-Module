# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
FastAPI server for RRA Module.

Provides REST API endpoints for:
- Repository ingestion
- Agent management
- Negotiation sessions
- License verification
- Marketplace discovery (NEW)
- WebSocket real-time chat (NEW)
"""

import re
import os
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rra.ingestion.repo_ingester import RepoIngester


# =============================================================================
# Security Utilities
# =============================================================================

# Allowed directory for knowledge bases
KB_BASE_DIR = Path("agent_knowledge_bases").resolve()


def validate_repo_name(repo_name: str) -> bool:
    """
    Validate repository name to prevent path traversal.

    Args:
        repo_name: Repository name to validate

    Returns:
        True if valid, False otherwise
    """
    if not repo_name:
        return False

    # Only allow alphanumeric, underscore, hyphen, and dot
    if not re.match(r'^[\w\-\.]+$', repo_name):
        return False

    # Reject path traversal attempts
    if '..' in repo_name or repo_name.startswith('.'):
        return False

    return True


def validate_kb_path(kb_path: str, allowed_dir: Path = KB_BASE_DIR) -> bool:
    """
    Validate knowledge base path to prevent path traversal.

    Args:
        kb_path: Path to validate
        allowed_dir: Directory that paths must be within

    Returns:
        True if path is valid and within allowed directory
    """
    try:
        # Resolve to absolute path
        resolved = Path(kb_path).resolve()

        # Ensure it's within the allowed directory
        resolved.relative_to(allowed_dir)

        # Check file extension
        if not str(resolved).endswith('_kb.json'):
            return False

        return True
    except (ValueError, RuntimeError):
        return False


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error message to prevent information disclosure.

    Args:
        error: Exception to sanitize

    Returns:
        Safe error message
    """
    error_str = str(error)

    # List of patterns to redact
    sensitive_patterns = [
        r'/home/[\w/]+',  # File paths
        r'/usr/[\w/]+',
        r'postgresql://[^\s]+',  # Database URLs
        r'mongodb://[^\s]+',
        r'redis://[^\s]+',
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
    ]

    for pattern in sensitive_patterns:
        error_str = re.sub(pattern, '[REDACTED]', error_str)

    # Truncate long messages
    if len(error_str) > 200:
        error_str = error_str[:200] + '...'

    return error_str


from rra.ingestion.knowledge_base import KnowledgeBase
from rra.agents.negotiator import NegotiatorAgent
from rra.config.market_config import MarketConfig


# Request/Response models
class IngestRequest(BaseModel):
    repo_url: str
    force_refresh: bool = False


class IngestResponse(BaseModel):
    status: str
    repo_url: str
    kb_path: str
    summary: Dict[str, Any]


class NegotiationRequest(BaseModel):
    kb_path: str
    message: Optional[str] = None


class NegotiationResponse(BaseModel):
    message: str
    phase: str
    session_id: str


class LicenseVerifyRequest(BaseModel):
    token_id: int


# Global state (in production, use proper state management)
active_agents: Dict[str, NegotiatorAgent] = {}


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="RRA Module API",
        description="REST API for Revenant Repo Agent Module",
        version="0.6.0",
    )

    # ==========================================================================
    # CORS Configuration
    # ==========================================================================
    # Get allowed origins from environment or use secure defaults
    cors_origins_env = os.environ.get("RRA_CORS_ORIGINS", "")
    if cors_origins_env:
        # Parse comma-separated origins from environment
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")]
    else:
        # Default: Only allow specific origins
        allowed_origins = [
            "https://natlangchain.io",
            "https://app.natlangchain.io",
            "https://marketplace.natlangchain.io",
        ]

    # In development, also allow localhost
    if os.environ.get("RRA_ENV", "production") == "development":
        allowed_origins.extend([
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
        ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Webhook-Signature",
            "X-Request-Timestamp",
            "X-Request-Nonce",
        ],
        expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Reset"],
    )

    @app.get("/")
    def root():
        """Root endpoint."""
        return {
            "name": "RRA Module API",
            "version": "0.5.0",
            "endpoints": {
                "ingest": "/api/ingest",
                "negotiate": "/api/negotiate",
                "verify": "/api/verify",
                "repositories": "/api/repositories",
                "marketplace": {
                    "repos": "/api/marketplace/repos",
                    "featured": "/api/marketplace/featured",
                    "categories": "/api/marketplace/categories",
                    "agent_details": "/api/marketplace/agent/{repo_id}/details",
                    "agent_stats": "/api/marketplace/agent/{repo_id}/stats",
                },
                "deep_links": {
                    "generate": "/api/links/generate",
                    "resolve": "/api/links/resolve/{repo_id}",
                    "register": "/api/links/register",
                    "badge": "/api/links/badge",
                    "qr_code": "/api/links/qr/{repo_id}",
                    "embed": "/api/links/embed/{repo_id}",
                    "stats": "/api/links/stats",
                },
                "webhooks": {
                    "trigger": "/webhook/{agent_id}",
                    "session_status": "/webhook/session/{session_id}",
                    "session_messages": "/webhook/session/{session_id}/messages",
                    "send_message": "/webhook/session/{session_id}/message",
                    "credentials": "/webhook/credentials",
                    "rate_limit": "/webhook/rate-limit/{agent_id}",
                },
                "streaming": {
                    "create": "/api/streaming/create",
                    "activate": "/api/streaming/activate/{license_id}",
                    "stop": "/api/streaming/stop/{license_id}",
                    "status": "/api/streaming/status/{license_id}",
                    "access": "/api/streaming/access/{license_id}",
                    "tokens": "/api/streaming/tokens",
                    "stats": "/api/streaming/stats",
                },
                "websocket": "/ws/negotiate/{repo_id}",
                "widget": {
                    "init": "/api/widget/init",
                    "embed_js": "/api/widget/embed.js",
                    "message": "/api/widget/message",
                    "config": "/api/widget/config/{widget_id}",
                    "event": "/api/widget/event",
                    "analytics": "/api/widget/analytics/{agent_id}",
                    "demo": "/api/widget/demo",
                },
                "analytics": {
                    "overview": "/api/analytics/overview",
                    "agent": "/api/analytics/agent/{agent_id}",
                    "funnel": "/api/analytics/funnel",
                    "revenue": "/api/analytics/revenue",
                    "timeseries": "/api/analytics/timeseries",
                    "agents": "/api/analytics/agents",
                    "export": "/api/analytics/export",
                    "dashboard": "/api/analytics/dashboard",
                    "event": "/api/analytics/event",
                },
            }
        }

    @app.post("/api/ingest", response_model=IngestResponse)
    async def ingest_repository(
        request: IngestRequest,
        background_tasks: BackgroundTasks
    ):
        """
        Ingest a repository and generate knowledge base.

        This endpoint clones the repository, parses its contents,
        and creates a knowledge base for agent operations.
        """
        try:
            ingester = RepoIngester()
            kb = ingester.ingest(request.repo_url, force_refresh=request.force_refresh)

            # Save knowledge base
            kb_path = kb.save()

            # Get summary
            context = kb.get_negotiation_context()

            return IngestResponse(
                status="success",
                repo_url=request.repo_url,
                kb_path=str(kb_path),
                summary=context
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/negotiate/start", response_model=NegotiationResponse)
    async def start_negotiation(request: NegotiationRequest):
        """
        Start a new negotiation session.

        Creates a negotiation agent and returns its introduction.
        """
        try:
            # Security: Validate kb_path to prevent path traversal
            if not validate_kb_path(request.kb_path):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid knowledge base path"
                )

            # Load knowledge base
            kb = KnowledgeBase.load(Path(request.kb_path))

            # Create negotiator
            negotiator = NegotiatorAgent(kb)

            # Start negotiation
            intro = negotiator.start_negotiation()

            # Store agent (in production, use proper session management)
            session_id = f"session_{len(active_agents)}"
            active_agents[session_id] = negotiator

            return NegotiationResponse(
                message=intro,
                phase=negotiator.current_phase.value,
                session_id=session_id
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/negotiate/message", response_model=NegotiationResponse)
    async def send_message(
        session_id: str,
        message: str
    ):
        """
        Send a message in an active negotiation.

        Args:
            session_id: Active negotiation session ID
            message: Message from buyer

        Returns:
            Response from negotiator
        """
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")

        try:
            negotiator = active_agents[session_id]
            response = negotiator.respond(message)

            return NegotiationResponse(
                message=response,
                phase=negotiator.current_phase.value,
                session_id=session_id
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/negotiate/summary/{session_id}")
    async def get_negotiation_summary(session_id: str):
        """
        Get summary of a negotiation session.

        Args:
            session_id: Negotiation session ID

        Returns:
            Summary including history and current state
        """
        if session_id not in active_agents:
            raise HTTPException(status_code=404, detail="Session not found")

        negotiator = active_agents[session_id]
        return negotiator.get_negotiation_summary()

    @app.get("/api/repositories")
    async def list_repositories():
        """
        List all ingested repositories.

        Returns:
            List of knowledge bases
        """
        kb_dir = Path("agent_knowledge_bases")

        if not kb_dir.exists():
            return {"repositories": []}

        repositories = []
        for kb_file in kb_dir.glob("*_kb.json"):
            try:
                kb = KnowledgeBase.load(kb_file)
                repositories.append({
                    "url": kb.repo_url,
                    "kb_path": str(kb_file),
                    "updated_at": kb.updated_at.isoformat(),
                    "languages": kb.statistics.get("languages", []),
                    "files": kb.statistics.get("code_files", 0),
                })
            except:
                pass

        return {"repositories": repositories}

    @app.get("/api/repository/{repo_name}")
    async def get_repository_info(repo_name: str):
        """
        Get detailed information about a repository.

        Args:
            repo_name: Repository name

        Returns:
            Repository details and configuration
        """
        kb_dir = Path("agent_knowledge_bases")
        kb_file = kb_dir / f"{repo_name}_kb.json"

        if not kb_file.exists():
            raise HTTPException(status_code=404, detail="Repository not found")

        try:
            kb = KnowledgeBase.load(kb_file)

            return {
                "url": kb.repo_url,
                "summary": kb.get_summary(),
                "context": kb.get_negotiation_context(),
                "statistics": kb.statistics,
                "market_config": kb.market_config.model_dump() if kb.market_config else None,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/verify")
    async def verify_license(request: LicenseVerifyRequest):
        """
        Verify a license token.

        Args:
            request: Verification request with token ID

        Returns:
            Verification result
        """
        # In production, would check blockchain
        # For now, return placeholder
        return {
            "token_id": request.token_id,
            "valid": True,
            "message": "License verification requires blockchain connection"
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    # Include all API routers
    try:
        from rra.api.marketplace import router as marketplace_router
        from rra.api.websocket import router as websocket_router
        from rra.api.deep_links import router as deep_links_router
        from rra.api.webhooks import router as webhooks_router
        from rra.api.streaming import router as streaming_router
        from rra.api.widget import router as widget_router
        from rra.api.analytics import router as analytics_router
        from rra.api.yield_api import router as yield_router
        app.include_router(marketplace_router)
        app.include_router(websocket_router)
        app.include_router(deep_links_router)
        app.include_router(webhooks_router)
        app.include_router(streaming_router)
        app.include_router(widget_router)
        app.include_router(analytics_router)
        app.include_router(yield_router)
    except ImportError:
        # Routers not available in minimal install
        pass

    return app


# For running with uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
