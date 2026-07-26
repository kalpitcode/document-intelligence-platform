#!/usr/bin/env bash
# ==============================================================================
# Development Start Script
# ==============================================================================
# Starts the application with Uvicorn hot-reload for development.
#
# Usage: bash scripts/start-dev.sh
# ==============================================================================

set -euo pipefail

echo "========================================"
echo " Document Intelligence Platform"
echo " Starting in DEVELOPMENT mode"
echo "========================================"

# Set development defaults
export APP_ENV="${APP_ENV:-development}"
export APP_DEBUG="${APP_DEBUG:-true}"
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
export LOG_FORMAT="${LOG_FORMAT:-console}"

HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-8000}"

echo "Host:        ${HOST}"
echo "Port:        ${PORT}"
echo "Environment: ${APP_ENV}"
echo "Debug:       ${APP_DEBUG}"
echo "Log Level:   ${LOG_LEVEL}"
echo "========================================"

exec uvicorn app.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --reload \
  --reload-dir app \
  --log-level debug
