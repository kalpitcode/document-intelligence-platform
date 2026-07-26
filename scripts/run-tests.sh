#!/usr/bin/env bash
# ==============================================================================
# Test Runner Script
# ==============================================================================
# Runs the test suite with coverage reporting.
#
# Usage:
#   bash scripts/run-tests.sh           # Run all tests
#   bash scripts/run-tests.sh unit      # Run unit tests only
#   bash scripts/run-tests.sh integration # Run integration tests only
# ==============================================================================

set -euo pipefail

echo "========================================"
echo " Document Intelligence Platform"
echo " Running Tests"
echo "========================================"

# Set test environment
export APP_ENV=testing
export POSTGRES_DB=document_intelligence_test

TEST_TYPE="${1:-all}"

case "${TEST_TYPE}" in
  unit)
    echo "Running UNIT tests..."
    python -m pytest tests/unit -v --tb=short -m "unit"
    ;;
  integration)
    echo "Running INTEGRATION tests..."
    python -m pytest tests/integration -v --tb=short -m "integration"
    ;;
  api)
    echo "Running API tests..."
    python -m pytest tests/api -v --tb=short
    ;;
  all)
    echo "Running ALL tests..."
    python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-report=html:reports/coverage
    ;;
  *)
    echo "Unknown test type: ${TEST_TYPE}"
    echo "Usage: $0 [unit|integration|api|all]"
    exit 1
    ;;
esac

echo ""
echo "========================================"
echo " Tests Complete"
echo "========================================"
