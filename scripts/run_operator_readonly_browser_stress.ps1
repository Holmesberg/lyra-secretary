param(
  [ValidateSet("public", "local")]
  [string]$Topology = "public"
)

$ErrorActionPreference = "Stop"

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

node scripts/verify_runtime_topology.mjs --topology $Topology
node scripts/browser_stress_operator_readonly.mjs
