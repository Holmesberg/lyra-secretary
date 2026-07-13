param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "public",

  [string]$RunId = "",

  [string]$OutDir = "",

  [string]$Prefix = "",

  [switch]$CleanupOnly,

  [switch]$AssumeLocalFrontendReady,

  [switch]$AllowPublicFrontendArtifactMutation,

  [int]$LocalCurrentPort = 3013,

  [switch]$ProxyApi,

  [switch]$ForcePressureRecovery,

  [switch]$PressureProofOnly,

  [switch]$PulseStopwatchOutputProofOnly
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local_frontend_topology.ps1")

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $repoRoot
try {
  function Import-UserCookieEnv {
    param(
      [Parameter(Mandatory = $true)]
      [string]$Name
    )
    $value = [Environment]::GetEnvironmentVariable($Name, "User")
    if ([string]::IsNullOrWhiteSpace($value)) {
      $value = (Get-ItemProperty -Path "HKCU:\Environment" -Name $Name -ErrorAction SilentlyContinue).$Name
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
      throw "$Name is missing from User env/registry."
    }
    Set-Item -Path "Env:\$Name" -Value $value
  }

  Import-UserCookieEnv -Name "LYRA_COOKIE_HOLMESBERG"
  Import-UserCookieEnv -Name "LYRA_COOKIE_ALINASSERSABRY"

  $useProxyApi = [bool]$ProxyApi -or $Topology -eq "local-current"

  if ($Topology -eq "public") {
    $env:LYRA_FRONTEND_ORIGIN = "https://lyraos.org"
    $env:LYRA_API_ORIGIN = "https://api.lyraos.org"
  } elseif ($Topology -eq "local-current") {
    $env:LYRA_FRONTEND_ORIGIN = "http://localhost:$LocalCurrentPort"
    $env:LYRA_API_ORIGIN = "http://localhost:8000"
    $env:NEXTAUTH_URL = $env:LYRA_FRONTEND_ORIGIN
  } else {
    $env:LYRA_FRONTEND_ORIGIN = "http://localhost:3000"
    $env:LYRA_API_ORIGIN = "http://localhost:8000"
  }

  Write-Host "Holmesberg product-loop dogfood"
  Write-Host "Topology: $Topology"
  Write-Host "Frontend: $env:LYRA_FRONTEND_ORIGIN"
  Write-Host "API: $env:LYRA_API_ORIGIN"
  Write-Host "Proxy API: $useProxyApi"
  Write-Host ""

  if (($Topology -eq "local" -or $Topology -eq "local-current") -and -not $AssumeLocalFrontendReady) {
    $port = if ($Topology -eq "local-current") { $LocalCurrentPort } else { 3000 }
    Ensure-LocalFrontendDev `
      -Reason "Holmesberg product-loop local topology proof" `
      -Port $port `
      -AllowPublicFrontendArtifactMutation:$AllowPublicFrontendArtifactMutation
  }

  & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_browser_cookie_env.ps1 -Account holmesberg
  if ($LASTEXITCODE -ne 0) {
    throw "Holmesberg cookie check failed."
  }
  & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_browser_cookie_env.ps1 -Account alinassersabry
  if ($LASTEXITCODE -ne 0) {
    throw "Operator cookie check failed."
  }

  node scripts\test_browser_auth_helpers.mjs
  if ($LASTEXITCODE -ne 0) {
    throw "browser auth helper self-test failed with exit code $LASTEXITCODE."
  }

  $topologyArgs = @("scripts\verify_runtime_topology.mjs", "--topology", $Topology)
  if ($Topology -eq "local-current") {
    $topologyArgs += @(
      "--frontend", $env:LYRA_FRONTEND_ORIGIN,
      "--api", $env:LYRA_API_ORIGIN,
      "--nextauth", $env:LYRA_FRONTEND_ORIGIN
    )
    if ($useProxyApi) {
      $topologyArgs += "--proxy-api"
    }
  }
  node @topologyArgs
  if ($LASTEXITCODE -ne 0) {
    throw "runtime topology verifier failed with exit code $LASTEXITCODE."
  }

  $args = @(
    "scripts\browser_holmesberg_product_loop_dogfood.mjs",
    "--topology", $Topology,
    "--frontend", $env:LYRA_FRONTEND_ORIGIN,
    "--api", $env:LYRA_API_ORIGIN
  )
  if ($useProxyApi) {
    $args += "--proxy-api"
  }
  if (-not [string]::IsNullOrWhiteSpace($RunId)) {
    $args += @("--run-id", $RunId)
  }
  if (-not [string]::IsNullOrWhiteSpace($OutDir)) {
    $args += @("--out-dir", $OutDir)
  }
  if (-not [string]::IsNullOrWhiteSpace($Prefix)) {
    $args += @("--prefix", $Prefix)
  }
  if ([bool]$CleanupOnly) {
    $args += @("--cleanup-only")
  }
  if ([bool]$ForcePressureRecovery) {
    $args += @("--force-pressure-recovery", "true")
  }
  if ([bool]$PressureProofOnly) {
    $args += "--pressure-proof-only"
  }
  if ([bool]$PulseStopwatchOutputProofOnly) {
    $args += "--pulse-stopwatch-output-proof-only"
  }

  node @args
  if ($LASTEXITCODE -ne 0) {
    throw "Holmesberg product-loop dogfood failed with exit code $LASTEXITCODE."
  }
} finally {
  Pop-Location
}
