#!/usr/bin/env bash
set -euo pipefail

MAX_ROWS="${MAX_ROWS:-1000}"
DSN="${DB_READONLY_DSN:-}"

if [[ -z "${DSN}" ]]; then
  echo "Missing DB_READONLY_DSN" >&2
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

