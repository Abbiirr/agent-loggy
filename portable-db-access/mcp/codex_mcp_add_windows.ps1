param(
  [string]$Name = "db",
  [string]$Dsn = $env:DB_READONLY_DSN,
  [int]$MaxRows = 1000,
  [switch]$PersistDsn
)

if (-not $Dsn) {
  $envPath = Join-Path $PSScriptRoot "..\\.env"
  if (Test-Path $envPath) {
    $dsnLine = Get-Content $envPath | Where-Object { $_ -match '^\s*DB_READONLY_DSN\s*=' } | Select-Object -First 1
    if ($dsnLine) {
      $Dsn = $dsnLine.Split("=", 2)[1].Trim().Trim('"')
      $env:DB_READONLY_DSN = $Dsn
    }
  }
}

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
