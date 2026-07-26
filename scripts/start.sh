#!/usr/bin/env bash
# ==============================================================================
# Production Start Script
# ==============================================================================
# Starts the application with Uvicorn using production settings.
#
# Usage: bash scripts/start.sh
# ==============================================================================

set -euo pipefail

echo "========================================"
echo " Document Intelligence Platform"
echo " Starting in PRODUCTION mode"
echo "========================================"

# Default values
HOST="${APP_HOST:-0.0.0.0}"
PORT="${APP_PORT:-8000}"
WORKERS="${APP_WORKERS:-4}"
LOG_LEVEL="${LOG_LEVEL:-warning}"

echo "Host:     ${HOST}"
echo "Port:     ${PORT}"
echo "Workers:  ${WORKERS}"
echo "Log Level: ${LOG_LEVEL}"
echo "========================================"

exec uvicorn app.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --workers "${WORKERS}" \
  --log-level "${LOG_LEVEL}" \
  --no-access-log \
  --proxy-headers \
  --forwarded-allow-ips="*"
