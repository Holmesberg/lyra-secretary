param(
  [string]$DatabasePath = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"
$python = Join-Path $repoRoot ".venv311\Scripts\python.exe"

if (-not (Test-Path $python)) {
  throw "Python venv not found at $python"
}

$tmpDir = Join-Path $repoRoot "tmp\alembic"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

$ownsDatabase = $false
if ([string]::IsNullOrWhiteSpace($DatabasePath)) {
  $DatabasePath = Join-Path $tmpDir ("fresh-smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss-fff") + ".sqlite")
  $ownsDatabase = $true
}

if (Test-Path $DatabasePath) {
  throw "Refusing to run fresh migration smoke against existing database: $DatabasePath"
}

$oldDatabaseUrl = $env:DATABASE_URL
$sqlitePath = ($DatabasePath -replace "\\", "/")
$env:DATABASE_URL = "sqlite:///$sqlitePath"

try {
  Push-Location $backendDir
  try {
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
      throw "alembic upgrade head failed with exit code $LASTEXITCODE"
    }

    $current = & $python -m alembic current
    if ($LASTEXITCODE -ne 0) {
      throw "alembic current failed with exit code $LASTEXITCODE"
    }
  } finally {
    Pop-Location
  }

  [pscustomobject]@{
    ok = $true
    database_path = $DatabasePath
    database_url = $env:DATABASE_URL
    alembic_current = ($current -join "`n").Trim()
  } | ConvertTo-Json
} finally {
  $env:DATABASE_URL = $oldDatabaseUrl
  if ($ownsDatabase -and (Test-Path $DatabasePath)) {
    Remove-Item -LiteralPath $DatabasePath -Force
  }
}
