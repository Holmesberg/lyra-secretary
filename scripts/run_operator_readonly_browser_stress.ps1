param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "public",

  [switch]$AssumeLocalFrontendReady,
  [switch]$AllowPublicFrontendArtifactMutation,
  [int]$LocalCurrentPort = 3013,
  [switch]$ProxyApi
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "local_frontend_topology.ps1")

$cookie = [Environment]::GetEnvironmentVariable("LYRA_COOKIE_ALINASSERSABRY", "User")
if ([string]::IsNullOrWhiteSpace($cookie) -or $cookie.Length -lt 300) {
  throw "LYRA_COOKIE_ALINASSERSABRY is missing or looks truncated."
}

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

$env:LYRA_COOKIE_ALINASSERSABRY = $cookie

Write-Host "Operator read-only browser stress"
Write-Host "Topology: $Topology"
Write-Host "Frontend: $env:LYRA_FRONTEND_ORIGIN"
Write-Host "API: $env:LYRA_API_ORIGIN"
Write-Host "Proxy API: $useProxyApi"
Write-Host "Operator cookie length: $($cookie.Length)"
Write-Host ""

if (($Topology -eq "local" -or $Topology -eq "local-current") -and -not $AssumeLocalFrontendReady) {
  $port = if ($Topology -eq "local-current") { $LocalCurrentPort } else { 3000 }
  Ensure-LocalFrontendDev `
    -Reason "operator read-only local topology proof" `
    -Port $port `
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

$topologyArgs = @("scripts/verify_runtime_topology.mjs", "--topology", $Topology)
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

Invoke-NodeChecked `
  -Name "runtime topology verifier" `
  -NodeArgs $topologyArgs

$browserArgs = @("scripts/browser_stress_operator_readonly.mjs")
if ($useProxyApi) {
  $browserArgs += @("--proxy-api", "true")
}

Invoke-NodeChecked `
  -Name "operator read-only browser stress" `
  -NodeArgs $browserArgs
