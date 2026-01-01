# =============================================================================
# RRA-Module Dockerfile
# Multi-stage build for production deployment
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# Install dependencies and build the package
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /build

# Copy dependency files first for better caching
COPY pyproject.toml requirements.txt ./

# Install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY README.md LICENSE* ./

# Install the package
RUN pip install --no-deps .

# -----------------------------------------------------------------------------
# Stage 2: Production
# Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.11-slim as production

# Labels
LABEL org.opencontainers.image.title="RRA-Module" \
      org.opencontainers.image.description="Revenant Repo Agent Module - Transform dormant repos into autonomous licensing agents" \
      org.opencontainers.image.version="0.1.0-alpha" \
      org.opencontainers.image.vendor="RRA Contributors" \
      org.opencontainers.image.source="https://github.com/kase1111-hash/RRA-Module"

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # Application settings
    RRA_HOST=0.0.0.0 \
    RRA_PORT=8000 \
    RRA_DEV_MODE=false \
    # Python path
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Git for repository operations
    git \
    # CA certificates for HTTPS
    ca-certificates \
    # Curl for health checks
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 rra && \
    useradd --uid 1000 --gid rra --shell /bin/bash --create-home rra

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directories
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R rra:rra /app

# Set working directory
WORKDIR /app

# Copy any additional configuration files
COPY --chown=rra:rra contracts/abi/ ./contracts/abi/

# Switch to non-root user
USER rra

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run the API server
CMD ["python", "-m", "uvicorn", "rra.api.server:app", "--host", "0.0.0.0", "--port", "8000"]

# -----------------------------------------------------------------------------
# Stage 3: Development
# Full development environment with testing tools
# -----------------------------------------------------------------------------
FROM production as development

# Switch back to root for installations
USER root

# Install development dependencies
RUN pip install pytest pytest-asyncio black flake8 mypy types-PyYAML types-requests

# Copy test files
COPY --chown=rra:rra tests/ ./tests/

# Switch back to non-root user
USER rra

# Override command for development
CMD ["python", "-m", "uvicorn", "rra.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
