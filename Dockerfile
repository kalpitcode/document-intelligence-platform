# ==============================================================================
# Enterprise AI Document Intelligence Platform — Dockerfile
# ==============================================================================
# Multi-stage build for minimal production image size and security.
#
# Stage 1 (builder): Install dependencies with Poetry
# Stage 2 (production): Slim Python image with only runtime dependencies
#
# Build:  docker build -t document-intelligence:latest .
# Run:    docker run -p 8000:8000 --env-file .env document-intelligence:latest
# ==============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — Install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install system dependencies for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copy dependency files first (cache layer)
COPY pyproject.toml poetry.lock* ./

# Install dependencies (no dev dependencies for production)
RUN poetry install --no-root --only main --no-interaction --no-ansi

# ---------------------------------------------------------------------------
# Stage 2: Production — Slim runtime image
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS production

# Prevent Python from writing .pyc files and enable unbuffered stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime-only system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create log directory
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
