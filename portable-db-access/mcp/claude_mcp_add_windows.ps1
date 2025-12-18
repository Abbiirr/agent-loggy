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

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
  Write-Error "Missing 'claude' CLI in PATH."
  exit 1
}

$runnerPath = Join-Path $PSScriptRoot "dbhub_stdio_windows.ps1"
$runnerPath = (Resolve-Path $runnerPath).Path

if ($PersistDsn) {
  # WARNING: this stores the DSN value in Claude's MCP config on disk.
  claude mcp add --transport stdio $Name --env "DB_READONLY_DSN=$Dsn" -- powershell -NoProfile -ExecutionPolicy Bypass -File "$runnerPath" -MaxRows $MaxRows
} else {
  # Recommended: keep DSN in your environment, not in MCP config files.
  claude mcp add --transport stdio $Name -- powershell -NoProfile -ExecutionPolicy Bypass -File "$runnerPath" -MaxRows $MaxRows
}
