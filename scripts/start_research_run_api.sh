#!/bin/sh
# Start the research-run API only after a read-only Notion schema preflight.
# The preflight performs no research-record writes.
set -eu
python scripts/research_run_preflight.py
exec uvicorn api_server:app --host 0.0.0.0 --port "${PORT:-8000}"
