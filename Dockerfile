# ==============================================================================
# Multi-Stage Production Dockerfile for Enterprise AI Document Intelligence Platform
# ==============================================================================

# --- Stage 1: Build Environment ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies required for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copy dependency specifications
COPY pyproject.toml poetry.lock* ./

# Install production dependencies only
RUN poetry install --only main --no-root


# --- Stage 2: Production Minimal Runtime ---
FROM python:3.12-slim AS runner

LABEL maintainer="BlackRock Engineering <engineering@blackrock.com>"
LABEL version="0.1.0"
LABEL description="Enterprise AI Document Intelligence Platform Runtime Container"

# Install runtime system libraries (OCR engine, Poppler for PDF rendering, libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    poppler-utils \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user and group for container security isolation
RUN groupadd -g 10001 dipgroup && \
    useradd -u 10001 -g dipgroup -s /bin/bash -m dipuser

# Copy virtual environment from builder stage
COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# Copy application source code and entrypoint
COPY --chown=dipuser:dipgroup app /app/app
COPY --chown=dipuser:dipgroup migrations /app/migrations
COPY --chown=dipuser:dipgroup alembic.ini /app/alembic.ini

# Create logs directory with proper non-root permissions
RUN mkdir -p /app/logs && chown -R dipuser:dipgroup /app

# Switch to non-root user
USER dipuser:dipgroup

# Expose HTTP port
EXPOSE 8000

# Container Healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# Default execution command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
