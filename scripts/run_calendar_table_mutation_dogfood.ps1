param(
  [ValidateSet("public", "local")]
  [string]$Topology = "local",

  [string]$RunId = "",

  [string]$OutDir = "",

  [string]$Prefix = "",

  [switch]$CleanupOnly
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

  if ($Topology -eq "public") {
    $env:LYRA_FRONTEND_ORIGIN = "https://lyraos.org"
    $env:LYRA_API_ORIGIN = "https://api.lyraos.org"
  } else {
    $env:LYRA_FRONTEND_ORIGIN = "http://localhost:3000"
    $env:LYRA_API_ORIGIN = "http://localhost:8000"
  }

  & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_browser_cookie_env.ps1 -Account holmesberg
  if ($LASTEXITCODE -ne 0) {
    throw "Holmesberg cookie check failed."
  }

  $args = @("scripts\browser_calendar_table_mutation_dogfood.mjs", "--topology", $Topology)
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
    throw "Calendar/table mutation dogfood failed with exit code $LASTEXITCODE."
  }
} finally {
  Pop-Location
}
