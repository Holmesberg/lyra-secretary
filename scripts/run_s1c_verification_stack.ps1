param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "public",

  [switch]$SkipBackendFull,
  [switch]$SkipFrontendBuild,
  [switch]$SkipBrowser,
  [switch]$IncludeMutable,
  [switch]$AllowPublicFrontendArtifactMutation,
  [int]$LocalCurrentPort = 3013
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
. (Join-Path $PSScriptRoot "local_frontend_topology.ps1")

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
  $global:LASTEXITCODE = 0
  & $Body
  $stepSucceeded = $?
  $stepExitCode = $global:LASTEXITCODE
  if (-not $stepSucceeded) {
    throw "$Name failed with exit code $stepExitCode"
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

  Invoke-Step "backend layer import gate" {
    & $python -m py_compile scripts\scan_backend_layer_imports.py
    & $python scripts\scan_backend_layer_imports.py --self-test
    & $python scripts\scan_backend_layer_imports.py --fail-on-errors
  }

  Invoke-Step "Cortex read-only gate" {
    & $python -m py_compile scripts\scan_cortex_readonly.py
    & $python scripts\scan_cortex_readonly.py --self-test
    & $python scripts\scan_cortex_readonly.py --fail-on-errors
  }

  Invoke-Step "shipped feature preservation registry gate" {
    & $python -m py_compile scripts\scan_feature_preservation_registry.py
    & $python scripts\scan_feature_preservation_registry.py --self-test
    & $python scripts\scan_feature_preservation_registry.py --fail-on-errors
  }

  Invoke-Step "onboarding Brain Dump recovery contract gate" {
    node scripts\test_onboarding_brain_dump_recovery_contract.mjs
  }

  Invoke-Step "OpenClaw operator relay hermetic test" {
    node scripts\test_openclaw_operator_relay.mjs
  }

  Invoke-Step "public backend isolation contract gate" {
    node scripts\test_public_backend_isolation_contract.mjs
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
    Assert-LocalNextArtifactIsolation `
      -Reason "frontend production build in local topology" `
      -Topology $Topology `
      -AllowPublicFrontendArtifactMutation:$AllowPublicFrontendArtifactMutation

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
        Ensure-LocalFrontendDev `
          -Reason "local frontend dev restart after build" `
          -Port 3000 `
          -AllowPublicFrontendArtifactMutation:$AllowPublicFrontendArtifactMutation
      }
    } elseif ($Topology -eq "local-current") {
      Invoke-Step "local-current frontend dev restart after build" {
        Ensure-LocalFrontendDev `
          -Reason "local-current frontend dev restart after build" `
          -Port $LocalCurrentPort `
          -AllowPublicFrontendArtifactMutation:$AllowPublicFrontendArtifactMutation
      }
    }

    Invoke-Step "multi-account browser smoke" {
      if ($Topology -eq "local-current") {
        powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_multi_account_browser_smoke.ps1 -Topology $Topology -LocalCurrentPort $LocalCurrentPort
      } else {
        powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_multi_account_browser_smoke.ps1 -Topology $Topology
      }
    }

    Invoke-Step "operator read-only browser stress" {
      if ($Topology -eq "local-current") {
        powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology $Topology -LocalCurrentPort $LocalCurrentPort -AssumeLocalFrontendReady
      } else {
        powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_operator_readonly_browser_stress.ps1 -Topology $Topology
      }
    }

    if ($IncludeMutable) {
      Invoke-Step "Holmesberg mutable browser smoke" {
        if ($Topology -eq "local-current") {
          powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology $Topology -LocalCurrentPort $LocalCurrentPort -ProxyApi
        } else {
          powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_holmesberg_mutable_browser_smoke.ps1 -Topology $Topology
        }
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
