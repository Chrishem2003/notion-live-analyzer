#!/bin/sh
# Persistent-ledger preflight is mandatory whenever the API will accept run writes.
# Normalize exactly as api_server.py does so mixed-case/space-padded "true" cannot
# enable writes while skipping the startup preflight.
set -eu
writeback_flag="$(printf '%s' "${RESEARCH_RUN_WRITEBACK_ENABLED:-false}" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
if [ "$writeback_flag" = "true" ]; then
  python scripts/research_run_preflight.py
else
  echo "Research-run write-back disabled: durable idempotency storage is not configured."
fi
exec uvicorn api_server:app --host 0.0.0.0 --port "${PORT:-8000}"
