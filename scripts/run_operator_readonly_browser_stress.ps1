param(
  [ValidateSet("public", "local")]
  [string]$Topology = "public",

  [switch]$AssumeLocalFrontendReady,
  [switch]$AllowPublicFrontendArtifactMutation
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local_frontend_topology.ps1")

$cookie = [Environment]::GetEnvironmentVariable("LYRA_COOKIE_ALINASSERSABRY", "User")
if ([string]::IsNullOrWhiteSpace($cookie) -or $cookie.Length -lt 300) {
  throw "LYRA_COOKIE_ALINASSERSABRY is missing or looks truncated."
}

if ($Topology -eq "public") {
  $env:LYRA_FRONTEND_ORIGIN = "https://lyraos.org"
  $env:LYRA_API_ORIGIN = "https://api.lyraos.org"
} else {
  $env:LYRA_FRONTEND_ORIGIN = "http://localhost:3000"
  $env:LYRA_API_ORIGIN = "http://localhost:8000"
}

$env:LYRA_COOKIE_ALINASSERSABRY = $cookie

Write-Host "Operator read-only browser stress"
Write-Host "Topology: $Topology"
Write-Host "Frontend: $env:LYRA_FRONTEND_ORIGIN"
Write-Host "API: $env:LYRA_API_ORIGIN"
Write-Host "Operator cookie length: $($cookie.Length)"
Write-Host ""

if ($Topology -eq "local" -and -not $AssumeLocalFrontendReady) {
  Ensure-LocalFrontendDev `
    -Reason "operator read-only local topology proof" `
    -AllowPublicFrontendArtifactMutation:$AllowPublicFrontendArtifactMutation
}

function Invoke-NodeChecked {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$NodeArgs,
    [Parameter(Mandatory = $true)]
    [string]$Name
  )

  & node @NodeArgs
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE."
  }
}

Invoke-NodeChecked `
  -Name "browser auth helper self-test" `
  -NodeArgs @("scripts/test_browser_auth_helpers.mjs")

Invoke-NodeChecked `
  -Name "runtime topology verifier" `
  -NodeArgs @("scripts/verify_runtime_topology.mjs", "--topology", $Topology)

Invoke-NodeChecked `
  -Name "operator read-only browser stress" `
  -NodeArgs @("scripts/browser_stress_operator_readonly.mjs")
