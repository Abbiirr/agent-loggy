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

$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) {
  Write-Error "Missing 'codex' CLI in PATH."
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
    codex mcp add $Name --env "DSN=$Dsn" -- npx $npxYesArg @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "$Dsn"
  } else {
    codex mcp add $Name --env "DSN=$Dsn" -- npx @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "$Dsn"
  }
} else {
  if ($npxYesArg) {
    codex mcp add $Name --env "DSN=$Dsn" -- cmd /c npx $npxYesArg @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "%DSN%"
  } else {
    codex mcp add $Name --env "DSN=$Dsn" -- cmd /c npx @bytebase/dbhub --readonly --max-rows $MaxRows --dsn "%DSN%"
  }
}

