#!/bin/sh
# Run a read-only preflight for the optional Notion research-run integration.
# A failed preflight must not prevent unrelated API routes from starting.
# Research write-back remains fail-closed in api_server.py until its own
# required configuration and relation checks pass.
set -eu
if python scripts/research_run_preflight.py; then
  echo "Research-run preflight passed."
else
  status=$?
  echo "WARNING: research-run integration is not ready (preflight exit ${status}); API will start with protected write-back unavailable until configuration is fixed." >&2
fi
exec uvicorn api_server:app --host 0.0.0.0 --port "${PORT:-8000}"
