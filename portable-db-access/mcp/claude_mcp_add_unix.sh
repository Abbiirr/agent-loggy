#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-db}"
MAX_ROWS="${MAX_ROWS:-1000}"
DSN="${DB_READONLY_DSN:-}"

# Fallback: try to read from .env file if DSN not set
if [[ -z "${DSN}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ENV_FILE="${SCRIPT_DIR}/../.env"
  if [[ -f "${ENV_FILE}" ]]; then
    DSN="$(grep -E '^\s*DB_READONLY_DSN\s*=' "${ENV_FILE}" | head -1 | cut -d'=' -f2- | tr -d '"' | xargs)"
    export DB_READONLY_DSN="${DSN}"
  fi
fi

if [[ -z "${DSN}" ]]; then
  echo "Missing DB_READONLY_DSN (export it, or create portable-db-access/.env)" >&2
  exit 1
fi

RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${RUNNER_DIR}/dbhub_stdio_unix.sh"

claude mcp add --transport stdio "${NAME}" -- \
  env MAX_ROWS="${MAX_ROWS}" bash "${RUNNER}"
