param(
  [ValidateSet("public", "local")]
  [string]$Topology = "public",

  [ValidateSet("quick", "standard", "full", "chaos")]
  [string]$Mode = "standard",

  [string]$WaveName = "unnamed-wave",

  [switch]$IncludeMutable,

  [switch]$NoMutable
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $repoRoot ".venv311\Scripts\python.exe"
$runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runStartedAt = Get-Date
$safeWaveName = ($WaveName -replace "[^A-Za-z0-9_.-]", "-").Trim("-")
if ([string]::IsNullOrWhiteSpace($safeWaveName)) {
  $safeWaveName = "unnamed-wave"
}
$runId = "$runStamp-$safeWaveName-$Mode-$Topology"
$outDir = Join-Path $repoRoot "tmp\post-wave-dogfood\$runId"

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$mutableRequested = [bool]$IncludeMutable -and -not [bool]$NoMutable -and $Mode -ne "quick"
if ([bool]$IncludeMutable -and [bool]$NoMutable) {
  throw "Use either -IncludeMutable or -NoMutable, not both."
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

function Invoke-CheckedScript {
  param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,
    [string[]]$ScriptArgs = @()
  )
  & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @ScriptArgs
  if ($LASTEXITCODE -ne 0) {
    throw "$ScriptPath failed with exit code $LASTEXITCODE"
  }
}

function Assert-Cookie {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Account
  )
  $cookieJson = Invoke-CheckedScript `
    -ScriptPath ".\scripts\check_browser_cookie_env.ps1" `
    -ScriptArgs @("-Account", $Account)
  $cookieText = ($cookieJson -join "`n")
  $cookie = $cookieText | ConvertFrom-Json
  if (-not $cookie.consistent) {
    throw "$($cookie.env_name) is inconsistent across user/registry/process env."
  }
  if ([int]$cookie.user_env_length -lt 100 -or [int]$cookie.registry_length -lt 100) {
    throw "$($cookie.env_name) is missing or too short. Run save_browser_cookie_from_clipboard.ps1 for $Account."
  }
  Write-Host $cookieText
}

$transcriptPath = Join-Path $outDir "transcript.txt"
Start-Transcript -Path $transcriptPath -Force | Out-Null

Push-Location $repoRoot
try {
  Write-Host "Post-wave dogfood loop"
  Write-Host "Wave: $WaveName"
  Write-Host "Mode: $Mode"
  Write-Host "Topology: $Topology"
  Write-Host "Mutable: $mutableRequested"
  Write-Host "Out: $outDir"

  $commitSha = (git rev-parse --short HEAD).Trim()

  Invoke-Step "cookie check: operator" {
    Assert-Cookie -Account "alinassersabry"
  }

  Invoke-Step "cookie check: Holmesberg non-operator account" {
    Assert-Cookie -Account "holmesberg"
  }

  if ($Mode -eq "quick") {
    Invoke-Step "git diff check" {
      git diff --check
    }

    Invoke-Step "runtime topology verifier" {
      if ($Topology -eq "public") {
        $env:LYRA_FRONTEND_ORIGIN = "https://lyraos.org"
        $env:LYRA_API_ORIGIN = "https://api.lyraos.org"
      } else {
        $env:LYRA_FRONTEND_ORIGIN = "http://localhost:3000"
        $env:LYRA_API_ORIGIN = "http://localhost:8000"
      }
      node scripts\verify_runtime_topology.mjs --topology $Topology
    }

    Invoke-Step "multi-account browser smoke" {
      Invoke-CheckedScript `
        -ScriptPath ".\scripts\run_multi_account_browser_smoke.ps1" `
        -ScriptArgs @("-Topology", $Topology)
    }

    Invoke-Step "operator read-only browser stress" {
      Invoke-CheckedScript `
        -ScriptPath ".\scripts\run_operator_readonly_browser_stress.ps1" `
        -ScriptArgs @("-Topology", $Topology)
    }
  } else {
    $stackArgs = @("-Topology", $Topology)
    if ($mutableRequested) {
      $stackArgs += "-IncludeMutable"
    }
    if ($Mode -eq "standard") {
      $stackArgs += "-SkipBackendFull"
    }

    Invoke-Step "S1C verification stack" {
      Invoke-CheckedScript `
        -ScriptPath ".\scripts\run_s1c_verification_stack.ps1" `
        -ScriptArgs $stackArgs
    }

    if ($mutableRequested) {
      Invoke-Step "operator read-only browser stress after mutable pass" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_operator_readonly_browser_stress.ps1" `
          -ScriptArgs @("-Topology", $Topology)
      }
    }

    if ($Mode -eq "chaos" -and $mutableRequested) {
      Invoke-Step "Holmesberg mutable browser smoke repeat" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_holmesberg_mutable_browser_smoke.ps1" `
          -ScriptArgs @("-Topology", $Topology)
      }

      Invoke-Step "operator read-only browser stress after chaos repeat" {
        Invoke-CheckedScript `
          -ScriptPath ".\scripts\run_operator_readonly_browser_stress.ps1" `
          -ScriptArgs @("-Topology", $Topology)
      }
    }
  }

  $result = [pscustomobject]@{
    ok = $true
    commit = $commitSha
    wave = $WaveName
    mode = $Mode
    topology = $Topology
    mutable_enabled = $mutableRequested
    output_dir = $outDir
    transcript = $transcriptPath
    artifacts = @{
      operator_readonly_stress = @(
        Get-ChildItem -Path (Join-Path $repoRoot "tmp") -Directory -Filter "operator-readonly-stress-*" -ErrorAction SilentlyContinue |
          Where-Object { $_.LastWriteTime -ge $runStartedAt } |
          Sort-Object LastWriteTime |
          ForEach-Object { $_.FullName }
      )
      browser_smoke = @(
        Get-ChildItem -Path (Join-Path $repoRoot "tmp\browser-smoke") -Directory -ErrorAction SilentlyContinue |
          Where-Object { $_.LastWriteTime -ge $runStartedAt } |
          Sort-Object LastWriteTime |
          ForEach-Object { $_.FullName }
      )
    }
    steps = $summary
  }
  $result | ConvertTo-Json -Depth 6 | Tee-Object -FilePath (Join-Path $outDir "summary.json")
} finally {
  Pop-Location
  Stop-Transcript | Out-Null
}
