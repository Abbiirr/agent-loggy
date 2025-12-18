param(
  [string]$Name = "db",
  [string]$Dsn = $env:DB_READONLY_DSN,
  [int]$MaxRows = 1000,
  [switch]$NoCmd
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

$npx = Get-Command npx -ErrorAction SilentlyContinue
if (-not $npx) {
  Write-Error "Missing 'npx' (install Node.js / npm)."
  exit 1
}

$npxYesArg = $null
try {
  $help = & npx --help 2>&1 | Out-String
  if ($help -match "(?m)^\s*--yes\b") { $npxYesArg = "--yes" }
  elseif ($help -match "(?m)^\s*-y\b") { $npxYesArg = "-y" }
} catch {
  $npxYesArg = $null
}

if (-not $npxYesArg) {
  $env:npm_config_yes = "true"
}

if ($NoCmd) {
  if ($npxYesArg) {
    claude mcp add --transport stdio $Name -- npx $npxYesArg @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "$Dsn"
  } else {
    claude mcp add --transport stdio $Name -- npx @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "$Dsn"
  }
} else {
  if ($npxYesArg) {
    claude mcp add --transport stdio $Name -- cmd /c npx $npxYesArg @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "$Dsn"
  } else {
    claude mcp add --transport stdio $Name -- cmd /c npx @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "$Dsn"
  }
}
