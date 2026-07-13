param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "local",

  [string]$RunId = "",

  [string]$OutDir = "",

  [string]$Prefix = "",

  [switch]$CleanupOnly,

  [switch]$CalendarOnly,

  [switch]$AssumeLocalFrontendReady,

  [switch]$AllowPublicFrontendArtifactMutation,

  [int]$LocalCurrentPort = 3013,

  [int]$LocalCurrentApiPort = 8000,

  [switch]$ProxyApi,

  [switch]$FixtureAccountReady
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

  $useProxyApi = [bool]$ProxyApi -or $Topology -eq "local-current"

  if ($Topology -eq "public") {
    $env:LYRA_FRONTEND_ORIGIN = "https://lyraos.org"
    $env:LYRA_API_ORIGIN = "https://api.lyraos.org"
  } elseif ($Topology -eq "local-current") {
    $env:LYRA_FRONTEND_ORIGIN = "http://localhost:$LocalCurrentPort"
    $env:LYRA_API_ORIGIN = "http://localhost:$LocalCurrentApiPort"
    $env:NEXTAUTH_URL = $env:LYRA_FRONTEND_ORIGIN
  } else {
    $env:LYRA_FRONTEND_ORIGIN = "http://localhost:3000"
    $env:LYRA_API_ORIGIN = "http://localhost:8000"
  }

  Write-Host "Calendar/table mutation dogfood"
  Write-Host "Topology: $Topology"
  Write-Host "Frontend: $env:LYRA_FRONTEND_ORIGIN"
  Write-Host "API: $env:LYRA_API_ORIGIN"
  Write-Host "Proxy API: $useProxyApi"
  Write-Host ""

  if (($Topology -eq "local" -or $Topology -eq "local-current") -and -not $AssumeLocalFrontendReady) {
    $port = if ($Topology -eq "local-current") { $LocalCurrentPort } else { 3000 }
    Ensure-LocalFrontendDev `
      -Reason "calendar/table mutation local topology proof" `
      -Port $port `
      -AllowPublicFrontendArtifactMutation:$AllowPublicFrontendArtifactMutation
  }

  & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_browser_cookie_env.ps1 -Account holmesberg
  if ($LASTEXITCODE -ne 0) {
    throw "Holmesberg cookie check failed."
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
    "scripts\browser_calendar_table_mutation_dogfood.mjs",
    "--topology", $Topology,
    "--frontend", $env:LYRA_FRONTEND_ORIGIN,
    "--api", $env:LYRA_API_ORIGIN
  )
  if ($useProxyApi) {
    $args += "--proxy-api"
  }
  if ([bool]$FixtureAccountReady) {
    if ($Topology -ne "local-current") {
      throw "FixtureAccountReady is restricted to local-current."
    }
    $args += "--fixture-account-ready"
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
  if ([bool]$CalendarOnly) {
    $args += @("--calendar-only")
  }

  node @args
  if ($LASTEXITCODE -ne 0) {
    throw "Calendar/table mutation dogfood failed with exit code $LASTEXITCODE."
  }
} finally {
  Pop-Location
}
