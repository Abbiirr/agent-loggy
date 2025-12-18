#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-db}"
MAX_ROWS="${MAX_ROWS:-1000}"
DSN="${DB_READONLY_DSN:-}"

if [[ -z "${DSN}" ]]; then
  echo "Missing DB_READONLY_DSN (export it, or set it in your shell)" >&2
  exit 1
fi

claude mcp add --transport stdio "${NAME}" -- \
  npx -y @bytebase/dbhub --readonly --max-rows "${MAX_ROWS}" --dsn "${DSN}"

