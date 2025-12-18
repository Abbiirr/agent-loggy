param(
  [string]$Dsn = $env:DB_READONLY_DSN,
  [int]$MaxRows = 1000
)

if (-not $Dsn) {
  Write-Error "Missing DB_READONLY_DSN (or pass -Dsn)."
  exit 1
}

$npx = Get-Command npx -ErrorAction SilentlyContinue
if (-not $npx) {
  Write-Error "Missing 'npx' (install Node.js / npm)."
  exit 1
}

$configPath = Join-Path $env:TEMP ("dbhub_{0}.toml" -f [System.Guid]::NewGuid().ToString("n"))

try {
  # ASCII avoids BOM issues with DBHub's TOML loader on Windows PowerShell.
  @"
[[sources]]
id = "default"
dsn = "$Dsn"

[[tools]]
name = "execute_sql"
source = "default"
readonly = true
max_rows = $MaxRows
"@ | Set-Content -Encoding ASCII $configPath

  $env:npm_config_yes = "true"
  npx -- @bytebase/dbhub --config "$configPath"
} finally {
  Remove-Item -Force -ErrorAction SilentlyContinue $configPath
}

