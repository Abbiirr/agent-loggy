#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-db}"
MAX_ROWS="${MAX_ROWS:-1000}"
DSN="${DB_READONLY_DSN:-}"

if [[ -z "${DSN}" ]]; then
  echo "Missing DB_READONLY_DSN (export it, or set it in your shell)" >&2
  exit 1
fi

RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER="${RUNNER_DIR}/dbhub_stdio_unix.sh"

codex mcp add "${NAME}" -- \
  env MAX_ROWS="${MAX_ROWS}" bash "${RUNNER}"
