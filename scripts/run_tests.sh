#!/usr/bin/env bash
set -euo pipefail

echo "Building API and worker images..."
docker compose build api worker

echo "Running test suite with coverage..."
docker compose run --rm api python -m pytest \
  --cov=app \
  --cov=scripts \
  --cov-report=term-missing \
  "$@"
