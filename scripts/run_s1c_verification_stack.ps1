param(
  [ValidateSet("public", "local")]
  [string]$Topology = "public",

  [switch]$SkipBackendFull,
  [switch]$SkipFrontendBuild,
  [switch]$SkipBrowser,
  [switch]$IncludeMutable,
  [switch]$AllowPublicFrontendArtifactMutation
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

function Test-WslPublicFrontendSession {
  if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    return $false
  }

  & wsl.exe -e bash -lc "tmux has-session -t lyra-frontend 2>/dev/null" 2>$null
  return $LASTEXITCODE -eq 0
}

function Assert-LocalNextArtifactIsolation {
  param([Parameter(Mandatory = $true)][string]$Reason)

  if ($Topology -ne "local") {
    return
  }

  if (-not (Test-WslPublicFrontendSession)) {
    return
  }

  $envOverride = [Environment]::GetEnvironmentVariable("LYRA_ALLOW_LOCAL_FRONTEND_WHILE_PUBLIC")
  if ([bool]$AllowPublicFrontendArtifactMutation -or $envOverride -eq "1") {
    Write-Warning (
      "Continuing despite active public frontend artifact risk for '$Reason'. " +
      "Restart hosted public frontend with scripts\restart_frontend_wsl.ps1 after this run."
    )
    return
  }

  throw @"
Refusing local frontend artifact mutation while WSL public frontend session 'lyra-frontend' is running.

Reason: $Reason

Local Next build/dev writes frontend\.next, the same artifact directory used by
the hosted public WSL frontend. This previously caused hosted-public _next chunk
400s and ChunkLoadError in the browser.

Use one of these explicit paths:
- run the verifier with -Topology public when local frontend proof is not needed;
- stop the public frontend before local artifact mutation, then restart it with scripts\restart_frontend_wsl.ps1;
- pass -AllowPublicFrontendArtifactMutation only for an intentional local proof and restart public immediately after.
"@
}

function Ensure-LocalFrontendDev {
  Assert-LocalNextArtifactIsolation -Reason "local frontend dev restart after build"

  $outDir = Join-Path $repoRoot "tmp\local-frontend-dev"
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $stdout = Join-Path $outDir "frontend-dev-$stamp.out.log"
  $stderr = Join-Path $outDir "frontend-dev-$stamp.err.log"

  $existing = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($existing) {
    Stop-Process -Id $existing.OwningProcess -Force
    Start-Sleep -Seconds 2
  }

  $env:NEXTAUTH_URL = "http://localhost:3000"
  $env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
  $env:NEXT_PUBLIC_BUILD_ID = "local-current"

  $process = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "-p", "3000") `
    -WorkingDirectory $frontendDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

  $ready = $false
  $lastError = $null
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 1
    try {
      $response = Invoke-WebRequest -UseBasicParsing "http://localhost:3000/api/topology" -TimeoutSec 3
      if ($response.StatusCode -eq 200) {
        $topology = $response.Content | ConvertFrom-Json
        if ($topology.verified_topology -eq $true -and
            $topology.topology_class -eq "local" -and
            $topology.compiled_api_origin -eq "http://localhost:8000") {
          $ready = $true
          break
        }
        $lastError = "unexpected topology response: $($response.Content)"
      }
    } catch {
      $lastError = $_.Exception.Message
    }
  }

  if (-not $ready) {
    Write-Host "Local frontend dev stdout: $stdout"
    Write-Host "Local frontend dev stderr: $stderr"
    Get-Content $stdout -ErrorAction SilentlyContinue | Select-Object -Last 80
    Get-Content $stderr -ErrorAction SilentlyContinue | Select-Object -Last 80
    throw "local frontend dev server did not become topology-ready on localhost:3000. Last error: $lastError"
  }

  Write-Host "Local frontend dev topology-ready on localhost:3000 (pid=$($process.Id))"
  Write-Host "stdout=$stdout"
  Write-Host "stderr=$stderr"
}

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
    Assert-LocalNextArtifactIsolation -Reason "frontend production build in local topology"

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
    if ($Topology -eq "local") {
      Invoke-Step "local frontend dev restart after build" {
        Ensure-LocalFrontendDev
      }
    }

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
