param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "public",
  [int]$LocalCurrentPort = 3013,
  [switch]$ProxyApi
)

$ErrorActionPreference = "Stop"

function Read-UserCookie {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name
  )
  $value = [Environment]::GetEnvironmentVariable($Name, "User")
  if ([string]::IsNullOrWhiteSpace($value)) {
    $item = Get-ItemProperty -Path "HKCU:\Environment" -Name $Name -ErrorAction SilentlyContinue
    if ($null -ne $item) {
      $value = $item.$Name
    }
  }
  if ([string]::IsNullOrWhiteSpace($value)) {
    throw "$Name is missing. Save it with scripts\save_browser_cookie_from_clipboard.ps1 first."
  }
  return $value
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

$env:LYRA_COOKIE_ALINASSERSABRY = Read-UserCookie "LYRA_COOKIE_ALINASSERSABRY"
$env:LYRA_COOKIE_HOLMESBERG = Read-UserCookie "LYRA_COOKIE_HOLMESBERG"

Write-Host "Multi-account browser smoke"
Write-Host "Topology: $Topology"
Write-Host "Frontend: $env:LYRA_FRONTEND_ORIGIN"
Write-Host "API: $env:LYRA_API_ORIGIN"
Write-Host "Proxy API: $useProxyApi"
Write-Host "Operator cookie length: $($env:LYRA_COOKIE_ALINASSERSABRY.Length)"
Write-Host "Holmesberg cookie length: $($env:LYRA_COOKIE_HOLMESBERG.Length)"
Write-Host ""

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

Invoke-NodeChecked `
  -Name "multi-account browser smoke" `
  -NodeArgs @("scripts/browser_smoke_two_users.mjs")
