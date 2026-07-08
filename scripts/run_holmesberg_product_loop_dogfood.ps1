param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "public",

  [string]$RunId = "",

  [string]$OutDir = "",

  [string]$Prefix = "",

  [switch]$CleanupOnly,

  [int]$LocalCurrentPort = 3013,

  [switch]$ProxyApi
)

$ErrorActionPreference = "Stop"

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

  & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_browser_cookie_env.ps1 -Account holmesberg
  if ($LASTEXITCODE -ne 0) {
    throw "Holmesberg cookie check failed."
  }
  & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_browser_cookie_env.ps1 -Account alinassersabry
  if ($LASTEXITCODE -ne 0) {
    throw "Operator cookie check failed."
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

  node @args
  if ($LASTEXITCODE -ne 0) {
    throw "Holmesberg product-loop dogfood failed with exit code $LASTEXITCODE."
  }
} finally {
  Pop-Location
}
