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

import logging
import re
import os
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from pydantic import BaseModel

from rra.ingestion.repo_ingester import RepoIngester
from rra.storage.session_store import (
    SessionData,
    get_session_store,
    SessionStore,
)
from rra.api.auth import (
    verify_api_key,
    generate_session_id,
    SESSION_EXPIRY_HOURS,
)


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
    if not re.match(r"^[\w\-\.]+$", repo_name):
        return False

    # Reject path traversal attempts
    if ".." in repo_name or repo_name.startswith("."):
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

        # Check file extension (support both .json and .json.gz)
        path_str = str(resolved)
        if not (path_str.endswith("_kb.json") or path_str.endswith("_kb.json.gz")):
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
        r"/home/[\w/]+",  # File paths
        r"/usr/[\w/]+",
        r"postgresql://[^\s]+",  # Database URLs
        r"mongodb://[^\s]+",
        r"redis://[^\s]+",
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP addresses
    ]

    for pattern in sensitive_patterns:
        error_str = re.sub(pattern, "[REDACTED]", error_str)

    # Truncate long messages
    if len(error_str) > 200:
        error_str = error_str[:200] + "..."

    return error_str


from rra.ingestion.knowledge_base import KnowledgeBase
from rra.agents.negotiator import NegotiatorAgent


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


class NegotiationMessageRequest(BaseModel):
    session_id: str
    message: str


class NegotiationResponse(BaseModel):
    message: str
    phase: str
    session_id: str


class LicenseVerifyRequest(BaseModel):
    token_id: int


# =============================================================================
# Session Storage (Redis-backed in production, in-memory fallback)
# =============================================================================
# Session store is lazily initialized via get_session_store()
# Configure RRA_REDIS_URL environment variable for production Redis backend
# Example: RRA_REDIS_URL=redis://localhost:6379/0


def get_session(session_id: str) -> Optional[SessionData]:
    """
    Retrieve a session from the store.

    Args:
        session_id: Session identifier

    Returns:
        SessionData if found and valid, None otherwise
    """
    store = get_session_store()
    return store.get(session_id)


def create_session(agent: NegotiatorAgent, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a new session with the given agent.

    Args:
        agent: NegotiatorAgent instance
        metadata: Optional session metadata

    Returns:
        Generated session ID
    """
    store = get_session_store()
    session_id = generate_session_id()
    session = SessionData(
        payload=agent,
        expiry_hours=SESSION_EXPIRY_HOURS,
        metadata=metadata or {},
    )
    store.set(session_id, session)
    return session_id


def cleanup_expired_sessions() -> None:
    """Remove expired sessions from the store."""
    store = get_session_store()
    count = store.cleanup_expired()
    if count > 0:
        logger.info(f"Cleaned up {count} expired sessions")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="RRA Module API",
        description="REST API for Revenant Repo Agent Module",
        version="1.0.1-beta",
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
        allowed_origins.extend(
            [
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ]
        )

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
            "Accept-Encoding",
        ],
        expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Reset", "Content-Encoding"],
    )

    # ==========================================================================
    # GZip Response Compression Middleware
    # ==========================================================================
    # Compress responses larger than 500 bytes
    # This reduces bandwidth for API responses, especially JSON payloads
    app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)
    logger.info("GZip response compression enabled (min_size=500, level=6)")

    # ==========================================================================
    # Security Headers Middleware
    # ==========================================================================
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        """Add security headers to all responses."""

        async def dispatch(self, request: Request, call_next) -> Response:
            response = await call_next(request)

            # Prevent MIME type sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"

            # Prevent clickjacking (except for widget endpoints that need embedding)
            if not request.url.path.startswith("/api/widget"):
                response.headers["X-Frame-Options"] = "DENY"

            # Enable XSS protection in older browsers
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Referrer policy for privacy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Permissions policy (formerly Feature-Policy)
            response.headers["Permissions-Policy"] = (
                "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
                "magnetometer=(), microphone=(), payment=(), usb=()"
            )

            # HSTS - only in production (when not localhost)
            if os.environ.get("RRA_ENV", "production") == "production":
                # max-age=1 year, include subdomains, allow preload
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )

            # Content Security Policy
            # Build connect-src from allowed CORS origins + self + ws/wss
            connect_sources = "'self'"
            cors_env = os.environ.get("RRA_CORS_ORIGINS", "")
            if cors_env:
                connect_sources += " " + " ".join(
                    o.strip() for o in cors_env.split(",") if o.strip()
                )

            # Allow frame-ancestors for widget embed paths
            if request.url.path.startswith("/api/widget"):
                frame_ancestors = "'self' *"
            else:
                frame_ancestors = "'none'"

            csp_directives = [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self' 'unsafe-inline'",  # inline styles often needed
                "img-src 'self' data: https:",
                "font-src 'self'",
                f"connect-src {connect_sources}",
                f"frame-ancestors {frame_ancestors}",
                "base-uri 'self'",
                "form-action 'self'",
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

            return response

    app.add_middleware(SecurityHeadersMiddleware)

    # ==========================================================================
    # Rate Limiting Middleware
    # ==========================================================================
    if os.environ.get("RRA_RATE_LIMIT_ENABLED", "true").lower() == "true":
        try:
            from rra.api.rate_limiter import setup_rate_limiting

            setup_rate_limiting(app)
            logger.info("Rate limiting enabled")
        except ImportError:
            logger.warning("Rate limiter module not available, running without rate limiting")

    @app.get("/")
    def root():
        """Root endpoint."""
        return {
            "name": "RRA Module API",
            "version": "1.0.1-beta",
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
            },
        }

    @app.post("/api/ingest", response_model=IngestResponse)
    async def ingest_repository(
        request: IngestRequest,
        background_tasks: BackgroundTasks,
        authenticated: bool = Depends(verify_api_key),
    ):
        """
        Ingest a repository and generate knowledge base.

        This endpoint clones the repository, parses its contents,
        and creates a knowledge base for agent operations.

        Requires API key authentication.
        """
        logger.info(f"Ingesting repository: {request.repo_url}")
        try:
            ingester = RepoIngester()
            kb = ingester.ingest(request.repo_url, force_refresh=request.force_refresh)

            # Save knowledge base
            kb_path = kb.save()

            # Get summary
            context = kb.get_negotiation_context()

            logger.info(f"Repository ingested successfully: {request.repo_url} -> {kb_path}")
            return IngestResponse(
                status="success", repo_url=request.repo_url, kb_path=str(kb_path), summary=context
            )

        except Exception as e:
            # Sanitize error message to prevent information disclosure
            logger.error(f"Repository ingestion failed for {request.repo_url}: {e}")
            raise HTTPException(status_code=500, detail=sanitize_error_message(e))

    @app.post("/api/negotiate/start", response_model=NegotiationResponse)
    async def start_negotiation(
        request: NegotiationRequest,
        authenticated: bool = Depends(verify_api_key),
    ):
        """
        Start a new negotiation session.

        Creates a negotiation agent and returns its introduction.
        Requires API key authentication.
        """
        logger.info(f"Starting negotiation for KB: {request.kb_path}")
        try:
            # Cleanup expired sessions periodically
            cleanup_expired_sessions()

            # Security: Validate kb_path to prevent path traversal
            if not validate_kb_path(request.kb_path):
                logger.warning(f"Invalid knowledge base path rejected: {request.kb_path}")
                raise HTTPException(status_code=400, detail="Invalid knowledge base path")

            # Load knowledge base
            kb = KnowledgeBase.load(Path(request.kb_path))

            # Create negotiator
            negotiator = NegotiatorAgent(kb)

            # Start negotiation
            intro = negotiator.start_negotiation()

            # Create session with Redis-backed storage (or in-memory fallback)
            session_id = create_session(
                agent=negotiator,
                metadata={"repo_url": kb.repo_url, "kb_path": str(request.kb_path)},
            )

            logger.info(f"Negotiation session started: {session_id} for {kb.repo_url}")
            return NegotiationResponse(
                message=intro, phase=negotiator.current_phase.value, session_id=session_id
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to start negotiation for {request.kb_path}: {e}")
            raise HTTPException(status_code=500, detail=sanitize_error_message(e))

    @app.post("/api/negotiate/message", response_model=NegotiationResponse)
    async def send_message(
        request: NegotiationMessageRequest,
        authenticated: bool = Depends(verify_api_key),
    ):
        """
        Send a message in an active negotiation.

        Requires API key authentication.
        """
        store = get_session_store()
        session = store.get(request.session_id)

        if session is None:
            logger.warning(f"Message sent to unknown/expired session: {request.session_id[:8]}...")
            raise HTTPException(status_code=404, detail="Session not found or expired")

        try:
            # Update last activity
            store.touch(request.session_id)

            negotiator = session.payload
            response = negotiator.respond(request.message)

            logger.debug(
                f"Message processed for session {request.session_id[:8]}..., phase: {negotiator.current_phase.value}"
            )
            return NegotiationResponse(
                message=response, phase=negotiator.current_phase.value, session_id=request.session_id
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Message processing failed for session {request.session_id[:8]}...: {e}")
            raise HTTPException(status_code=500, detail=sanitize_error_message(e))

    @app.get("/api/negotiate/summary/{session_id}")
    async def get_negotiation_summary(
        session_id: str,
        authenticated: bool = Depends(verify_api_key),
    ):
        """
        Get summary of a negotiation session.

        Args:
            session_id: Negotiation session ID

        Returns:
            Summary including history and current state

        Requires API key authentication.
        """
        store = get_session_store()
        session = store.get(session_id)

        if session is None:
            raise HTTPException(status_code=404, detail="Session not found or expired")

        store.touch(session_id)
        return session.payload.get_negotiation_summary()

    @app.get("/api/repositories")
    async def list_repositories(
        authenticated: bool = Depends(verify_api_key),
    ):
        """
        List all ingested repositories.

        Returns:
            List of knowledge bases (supports both .json and .json.gz)

        Requires API key authentication.
        """
        kb_dir = Path("agent_knowledge_bases")

        if not kb_dir.exists():
            return {"repositories": []}

        repositories = []
        seen_repos = set()  # Track seen repos to avoid duplicates

        # Find both compressed and uncompressed knowledge bases
        for pattern in ["*_kb.json", "*_kb.json.gz"]:
            for kb_file in kb_dir.glob(pattern):
                try:
                    kb = KnowledgeBase.load(kb_file)

                    # Avoid duplicates if both .json and .json.gz exist
                    if kb.repo_url in seen_repos:
                        continue
                    seen_repos.add(kb.repo_url)

                    repositories.append(
                        {
                            "url": kb.repo_url,
                            "kb_path": str(kb_file),
                            "updated_at": kb.updated_at.isoformat(),
                            "languages": kb.statistics.get("languages", []),
                            "files": kb.statistics.get("code_files", 0),
                            "compressed": str(kb_file).endswith(".gz"),
                        }
                    )
                except Exception as e:
                    # Skip corrupted knowledge bases but log the issue
                    logger.warning(f"Skipping corrupted knowledge base {kb_file}: {e}")
                    continue

        return {"repositories": repositories}

    @app.get("/api/repository/{repo_name}")
    async def get_repository_info(
        repo_name: str,
        authenticated: bool = Depends(verify_api_key),
    ):
        """
        Get detailed information about a repository.

        Args:
            repo_name: Repository name

        Returns:
            Repository details and configuration

        Requires API key authentication.
        """
        # Validate repo_name to prevent path traversal
        if not validate_repo_name(repo_name):
            logger.warning(f"Invalid repository name rejected: {repo_name}")
            raise HTTPException(status_code=400, detail="Invalid repository name")

        kb_dir = Path("agent_knowledge_bases")

        # Check for both compressed and uncompressed versions
        kb_file = kb_dir / f"{repo_name}_kb.json.gz"
        if not kb_file.exists():
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

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get repository info for {repo_name}: {e}")
            raise HTTPException(status_code=500, detail=sanitize_error_message(e))

    @app.post("/api/verify")
    async def verify_license(
        request: LicenseVerifyRequest,
        authenticated: bool = Depends(verify_api_key),
    ):
        """
        Verify a license token.

        Args:
            request: Verification request with token ID

        Returns:
            Verification result

        Requires API key authentication.
        """
        # Validate token ID
        if request.token_id < 0:
            raise HTTPException(status_code=400, detail="Invalid token ID")

        # Attempt on-chain verification via LicenseNFTContract
        try:
            from rra.contracts.license_nft import LicenseNFTContract
            from rra.contracts.manager import ContractManager

            manager = ContractManager()
            contract = manager.get_license_contract()
            is_valid = contract.is_license_valid(request.token_id)
            details = contract.get_license_details(request.token_id) if is_valid else {}

            return {
                "token_id": request.token_id,
                "valid": is_valid,
                "details": details,
                "message": "Verified on-chain",
            }
        except Exception as e:
            # Blockchain not configured or unreachable — report unknown
            logger.warning(f"On-chain verification unavailable for token {request.token_id}: {e}")
            return {
                "token_id": request.token_id,
                "valid": None,
                "message": "License verification unavailable: blockchain connection not configured",
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
        from rra.api.entropy import router as entropy_router
        from rra.api.warnings import router as warnings_router
        from rra.api.verification_api import router as verification_router

        app.include_router(marketplace_router)
        app.include_router(websocket_router)
        app.include_router(deep_links_router)
        app.include_router(webhooks_router)
        app.include_router(streaming_router)
        app.include_router(widget_router)
        app.include_router(analytics_router)
        app.include_router(entropy_router)
        app.include_router(warnings_router)
        app.include_router(verification_router)
        logger.info("All API routers loaded successfully")
    except ImportError as e:
        # Routers not available in minimal install
        logger.warning(f"Some API routers not available: {e}")

    return app


# For running with uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Use environment variable for host binding; 127.0.0.1 for local dev, 0.0.0.0 for production behind reverse proxy
    host = os.environ.get("RRA_HOST", "127.0.0.1")  # nosec B104
    port = int(os.environ.get("RRA_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
