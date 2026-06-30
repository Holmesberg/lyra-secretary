param(
  [ValidateSet("public", "local")]
  [string]$Topology = "public"
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

if ($Topology -eq "public") {
  $env:LYRA_FRONTEND_ORIGIN = "https://lyraos.org"
  $env:LYRA_API_ORIGIN = "https://api.lyraos.org"
} else {
  $env:LYRA_FRONTEND_ORIGIN = "http://localhost:3000"
  $env:LYRA_API_ORIGIN = "http://localhost:8000"
}

$env:LYRA_COOKIE_HOLMESBERG = Read-UserCookie "LYRA_COOKIE_HOLMESBERG"

Write-Host "Holmesberg mutable browser smoke"
Write-Host "Topology: $Topology"
Write-Host "Frontend: $env:LYRA_FRONTEND_ORIGIN"
Write-Host "API: $env:LYRA_API_ORIGIN"
Write-Host "Holmesberg cookie length: $($env:LYRA_COOKIE_HOLMESBERG.Length)"
Write-Host ""

node scripts/test_browser_auth_helpers.mjs
node scripts/verify_runtime_topology.mjs --topology $Topology
node scripts/browser_mutable_holmesberg_smoke.mjs
