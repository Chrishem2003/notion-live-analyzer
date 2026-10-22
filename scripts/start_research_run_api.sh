#!/bin/sh
# Persistent-ledger preflight is mandatory when write-back is enabled.
# On free hosting, keep the API available but disable Notion run writes explicitly.
set -eu
if [ "${RESEARCH_RUN_WRITEBACK_ENABLED:-true}" = "true" ]; then
  python scripts/research_run_preflight.py
else
  echo "Research-run write-back disabled: durable idempotency storage is not configured."
fi
exec uvicorn api_server:app --host 0.0.0.0 --port "${PORT:-8000}"
