#!/bin/sh
# Dedicated worker for the durable platform ledger. Invoke with: sh scripts/start_platform_ledger_worker.sh
set -eu

: "${REDIS_URL:?REDIS_URL is required; do not rely on localhost in hosted environments}"
case "$REDIS_URL" in
  redis://*|rediss://*) ;;
  *) echo "REDIS_URL must use redis:// or rediss://" >&2; exit 1 ;;
esac

if [ "${PLATFORM_JOB_LEDGER_ENABLED:-false}" = "true" ]; then
  case "${SUPABASE_URL:-}" in
    https://*) ;;
    *) echo "PLATFORM_JOB_LEDGER_ENABLED=true requires an HTTPS SUPABASE_URL" >&2; exit 1 ;;
  esac
  : "${SUPABASE_SERVICE_ROLE_KEY:?Ledger enabled but SUPABASE_SERVICE_ROLE_KEY is missing}"
fi

exec celery -A celery_app.celery_app worker \
  --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
  --queues=platform_ledger \
  --concurrency="${CELERY_LEDGER_CONCURRENCY:-2}"
