# Portable DB Read-Only Access Kit

This folder is a copy/paste-able kit for granting **read-only** database access to AI tools (Claude Code / Codex) without giving write privileges.

## Prereqs

- PostgreSQL client: `psql`
- Node.js (for `npx`)
- Either `claude` (Claude Code) and/or `codex` (Codex CLI)

## 0) Pick the right target

- For sensitive production data, prefer a **read replica** or a **sanitized analytics DB**.
- If you must limit what can be read, use **views** and/or **row-level security (RLS)** in addition to read-only grants.

## 1) Create a read-only DB user (PostgreSQL)

1. Edit `portable-db-access/sql/postgres_readonly_user.sql` and replace placeholders (DB name, schema, password).
2. Run it as a DB admin / owner:

PowerShell example:

```powershell
psql -h HOST -U ADMIN_USER -d postgres -f portable-db-access/sql/postgres_readonly_user.sql
```

Quick smoke test (as the new user):

```powershell
$env:DB_READONLY_DSN="postgresql://readonly:REPLACE_ME@HOST:5432/your_db"
psql "$env:DB_READONLY_DSN" -c "select now();"
```

Note: PostgreSQL’s default `public` schema privileges often allow `CREATE` to `PUBLIC`. If that’s true in your DB, “read-only” roles can still create objects unless you revoke `CREATE` from `PUBLIC` or use a dedicated schema.

## 2) Recommended: MCP via DBHub (read-only)

1. Put your DSN in an env var (don’t commit it):

```powershell
Copy-Item portable-db-access/.env.example portable-db-access/.env
# then edit portable-db-access/.env
```

2. Add the MCP server:

- Claude Code (Windows): `portable-db-access/mcp/claude_mcp_add_windows.ps1`
- Claude Code (macOS/Linux/WSL): `portable-db-access/mcp/claude_mcp_add_unix.sh`
- Codex CLI (Windows): `portable-db-access/mcp/codex_mcp_add_windows.ps1`
- Codex CLI (macOS/Linux/WSL): `portable-db-access/mcp/codex_mcp_add_unix.sh`

These scripts expect `DB_READONLY_DSN` to be set (you can `dotenv`-load it, or set it manually).
If you see `unknown option '-y'`, your `npx` is older; the Windows scripts auto-fallback (or update Node.js/npm).

## 3) Reduce accidental secret exposure (Codex)

Codex can restrict which environment variables get forwarded to spawned commands.

Example snippet (copy into your `~/.codex/config.toml`):

```toml
[shell_environment_policy]
include_only = ["PATH", "HOME", "USERPROFILE", "DB_READONLY_DSN", "DSN"]
```

## 4) SSH tunnel pattern (optional)

If your DB is private, tunnel it instead of exposing it publicly.

Example:

```bash
ssh -L 5432:db.internal:5432 user@bastion.example.com
```

Then use `HOST=localhost` in your DSN.
