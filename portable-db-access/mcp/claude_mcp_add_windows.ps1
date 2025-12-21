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
  Write-Error "Missing DB_READONLY_DSN. Set it (or pass -Dsn), or create portable-db-access/.env"
  exit 1
}

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
  Write-Error "Missing 'claude' CLI in PATH."
  exit 1
}

$runnerPath = Join-Path $PSScriptRoot "dbhub_stdio_windows.ps1"
$runnerPath = (Resolve-Path $runnerPath).Path
$cmd = "powershell -ExecutionPolicy Bypass -File `"$runnerPath`" -MaxRows $MaxRows"

if ($PersistDsn) {
  # WARNING: this stores the DSN value in Claude's MCP config on disk.
  claude mcp add --transport stdio $Name --env "DB_READONLY_DSN=$Dsn" -- powershell -ExecutionPolicy Bypass -File $runnerPath -MaxRows $MaxRows
} else {
  # Recommended: keep DSN in your environment, not in MCP config files.
  # The runner script will read from DB_READONLY_DSN env var or fall back to .env file.
  claude mcp add --transport stdio $Name -- powershell -ExecutionPolicy Bypass -File $runnerPath -MaxRows $MaxRows
}
