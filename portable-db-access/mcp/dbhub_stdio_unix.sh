#!/usr/bin/env bash
set -euo pipefail

MAX_ROWS="${MAX_ROWS:-1000}"
DSN="${DB_READONLY_DSN:-}"

# Fallback: try to read from .env file if DSN not set
if [[ -z "${DSN}" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ENV_FILE="${SCRIPT_DIR}/../.env"
  if [[ -f "${ENV_FILE}" ]]; then
    DSN="$(grep -E '^\s*DB_READONLY_DSN\s*=' "${ENV_FILE}" | head -1 | cut -d'=' -f2- | tr -d '"' | xargs)"
  fi
fi

if [[ -z "${DSN}" ]]; then
  echo "Missing DB_READONLY_DSN (export it, or create portable-db-access/.env)" >&2
  exit 1
fi

CONFIG_PATH="$(mktemp -t dbhub.XXXXXX.toml)"
cleanup() { rm -f "${CONFIG_PATH}"; }
trap cleanup EXIT

cat >"${CONFIG_PATH}" <<EOF
[[sources]]
id = "default"
dsn = "${DSN}"

[[tools]]
name = "execute_sql"
source = "default"
readonly = true
max_rows = ${MAX_ROWS}
EOF

export npm_config_yes=true
npx -- @bytebase/dbhub --config "${CONFIG_PATH}"

