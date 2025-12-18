param(
  [string]$Name = "db",
  [string]$Dsn = $env:DB_READONLY_DSN,
  [int]$MaxRows = 1000,
  [switch]$PersistDsn
)

if (-not $Dsn) {
  Write-Error "Missing DB_READONLY_DSN. Set it (or pass -Dsn)."
  exit 1
}

$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) {
  Write-Error "Missing 'codex' CLI in PATH."
  exit 1
}

$runnerPath = Join-Path $PSScriptRoot "dbhub_stdio_windows.ps1"
$runnerPath = (Resolve-Path $runnerPath).Path

if ($PersistDsn) {
  # WARNING: this stores the DSN value in Codex MCP config on disk.
  codex mcp add $Name --env "DB_READONLY_DSN=$Dsn" -- powershell -NoProfile -ExecutionPolicy Bypass -File "$runnerPath" -MaxRows $MaxRows
} else {
  codex mcp add $Name -- powershell -NoProfile -ExecutionPolicy Bypass -File "$runnerPath" -MaxRows $MaxRows
}
