# ==============================================================================
# Ultra-Fast Production Dockerfile for Enterprise AI Document Intelligence Platform
# ==============================================================================

FROM python:3.12-slim AS runner

LABEL maintainer="BlackRock Engineering <engineering@blackrock.com>"
LABEL version="0.1.0"
LABEL description="Enterprise AI Document Intelligence Platform Runtime Container"

# Install system dependencies required for runtime (OCR engine, Poppler, libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq5 \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Environment variables for Python & memory optimization in 512MB containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2

WORKDIR /app

# Copy requirements and install via pip with no cache for maximum speed
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and group for container security isolation
RUN groupadd -g 10001 dipgroup && \
    useradd -u 10001 -g dipgroup -s /bin/bash -m dipuser

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
    CMD sh -c "curl -f http://localhost:\${PORT:-8000}/api/v1/health/live || exit 1"

# Default execution command dynamically binding to cloud PORT env (defaults to 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
