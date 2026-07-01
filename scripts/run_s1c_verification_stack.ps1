param(
  [ValidateSet("public", "local")]
  [string]$Topology = "public",

  [switch]$SkipBackendFull,
  [switch]$SkipFrontendBuild,
  [switch]$SkipBrowser,
  [switch]$IncludeMutable
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$python = Join-Path $repoRoot ".venv311\Scripts\python.exe"

if (-not (Test-Path $python)) {
  throw "Python venv not found at $python"
}

$summary = [System.Collections.Generic.List[object]]::new()

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Body
  )

  Write-Host ""
  Write-Host "==> $Name"
  $started = Get-Date
  & $Body
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
  $durationMs = [int]((Get-Date) - $started).TotalMilliseconds
  $summary.Add([pscustomobject]@{
    step = $Name
    duration_ms = $durationMs
  }) | Out-Null
}

Push-Location $repoRoot
try {
  Invoke-Step "git diff check" {
    git diff --check
  }

  Invoke-Step "authority surface scan" {
    & $python scripts\scan_authority_surfaces.py --fail-on-missing --fail-on-worker-write-drift
  }

  Invoke-Step "static refactor contract scan" {
    & $python -m py_compile scripts\scan_refactor_contracts.py
    & $python scripts\scan_refactor_contracts.py --fail-on-errors
  }

  Invoke-Step "OpenClaw operator relay hermetic test" {
    node scripts\test_openclaw_operator_relay.mjs
  }

  Invoke-Step "alembic fresh database smoke" {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_alembic_fresh_smoke.ps1
  }

  if (-not $SkipBackendFull) {
    Invoke-Step "backend full pytest suite" {
      Push-Location $backendDir
      try {
        & $python -m pytest -q
      } finally {
        Pop-Location
      }
    }
  }

  if (-not $SkipFrontendBuild) {
    Invoke-Step "frontend production build" {
      Push-Location $frontendDir
      try {
        npm run build
      } finally {
        Pop-Location
      }
    }
  }

  if (-not $SkipBrowser) {
    Invoke-Step "multi-account browser smoke" {
      powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_multi_account_browser_smoke.ps1 -Topology $Topology
    }

    Invoke-Step "operator read-only browser stress" {
      powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology $Topology
    }

    if ($IncludeMutable) {
      Invoke-Step "Holmesberg mutable browser smoke" {
        powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology $Topology
      }
    }
  }

  Write-Host ""
  [pscustomobject]@{
    ok = $true
    topology = $Topology
    skipped = @{
      backend_full = [bool]$SkipBackendFull
      frontend_build = [bool]$SkipFrontendBuild
      browser = [bool]$SkipBrowser
      mutable = -not [bool]$IncludeMutable
    }
    steps = $summary
  } | ConvertTo-Json -Depth 5
} finally {
  Pop-Location
}
