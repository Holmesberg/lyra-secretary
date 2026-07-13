param(
  [ValidateSet("public", "local", "local-current")]
  [string]$Topology = "public",

  [ValidateSet("both", "operator", "holmesberg")]
  [string]$Account = "both",

  [ValidateSet("readonly", "mutable")]
  [string]$Intent = "readonly",

  [string]$FrontendOrigin = "",
  [string]$ApiOrigin = "",
  [string]$ExpectedFrontendBuildId = "",
  [string]$TargetPath = "",
  [string]$ReadySelector = "",
  [string]$SelectedDate = "",
  [string]$SelectedWeek = "",
  [string]$SyntheticPrefix = "",
  [int]$TimeoutMs = 30000,
  [int]$MaxExportBytes = 20000000,
  [int]$MaxPendingNotifications = 0,
  [switch]$ProxyApi,
  [switch]$FixtureAccountReady,
  [switch]$RequireAccountReady,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "local_frontend_topology.ps1")

function Import-UserCookieEnv {
  param([Parameter(Mandatory = $true)][string]$Name)
  $value = [Environment]::GetEnvironmentVariable($Name, "User")
  if ([string]::IsNullOrWhiteSpace($value)) {
    $value = (Get-ItemProperty -Path "HKCU:\Environment" -Name $Name -ErrorAction SilentlyContinue).$Name
  }
  if ([string]::IsNullOrWhiteSpace($value)) { throw "$Name is missing from User env/registry." }
  Set-Item -Path "Env:\$Name" -Value $value
}

function Get-CheckoutOwnerProcessId {
  param([Parameter(Mandatory = $true)][int]$ProcessId)
  $seen = @{}
  $currentId = $ProcessId
  for ($depth = 0; $depth -lt 8 -and $currentId -gt 0; $depth++) {
    if ($seen.ContainsKey($currentId)) { break }
    $seen[$currentId] = $true
    $current = Get-CimInstance Win32_Process -Filter "ProcessId = $currentId" -ErrorAction SilentlyContinue
    if (-not $current) { break }
    $commandLine = [string]$current.CommandLine
    if (
      $commandLine -and
      $commandLine.IndexOf($repoRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0
    ) {
      return [int]$current.ProcessId
    }
    $currentId = [int]$current.ParentProcessId
  }
  return $null
}

function Get-LocalPortProof {
  param([Parameter(Mandatory = $true)][string]$Label, [Parameter(Mandatory = $true)][uri]$Origin)
  if ($Origin.Host -notin @("localhost", "127.0.0.1")) { return $null }
  $listeners = @(Get-NetTCPConnection -LocalPort $Origin.Port -State Listen -ErrorAction SilentlyContinue)
  if ($listeners.Count -ne 1) { throw "$Label expected one listener on port $($Origin.Port); found $($listeners.Count)." }
  $pidValue = $listeners[0].OwningProcess
  $process = Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue" -ErrorAction SilentlyContinue
  $checkoutOwnerPid = Get-CheckoutOwnerProcessId -ProcessId $pidValue
  $checkoutOwned = $null -ne $checkoutOwnerPid
  if ($Topology -eq "local-current" -and -not $checkoutOwned) {
    throw "$Label listener $pidValue is not owned by this checkout."
  }
  return [ordered]@{
    label = $Label
    port = $Origin.Port
    pid = $pidValue
    process = $process.Name
    checkout_owned = $checkoutOwned
    checkout_owner_pid = $checkoutOwnerPid
  }
}

if ($Intent -eq "mutable" -and $Account -ne "holmesberg") {
  throw "Mutable proof is restricted to -Account holmesberg."
}
if ($SyntheticPrefix -and $SyntheticPrefix -notmatch '^DOGFOOD(?:\s|[-_])') {
  throw "SyntheticPrefix must begin with DOGFOOD."
}
if ($FixtureAccountReady -and $Topology -ne "local-current") {
  throw "FixtureAccountReady is restricted to local-current."
}

$contract = Get-Content -Raw (Join-Path $repoRoot "runtime_topology.json") | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($FrontendOrigin)) {
  $FrontendOrigin = if ($Topology -eq "local-current") { "http://localhost:3013" } else { $contract.topologies.$Topology.frontend_origin }
}
if ([string]::IsNullOrWhiteSpace($ApiOrigin)) {
  $ApiOrigin = if ($Topology -eq "local-current") { "http://localhost:8000" } else { $contract.topologies.$Topology.api_origin }
}
if ($Topology -eq "local-current" -and [string]::IsNullOrWhiteSpace($ExpectedFrontendBuildId)) {
  $ExpectedFrontendBuildId = (git -C $repoRoot rev-parse HEAD).Trim()
}

if ($Topology -ne "public") {
  Assert-LocalNextArtifactIsolation -Reason "proof preflight" -Topology $Topology
}
$portProof = @(
  Get-LocalPortProof -Label "frontend" -Origin ([uri]$FrontendOrigin)
  Get-LocalPortProof -Label "backend" -Origin ([uri]$ApiOrigin)
) | Where-Object { $null -ne $_ }

if ($Account -in @("both", "operator")) { Import-UserCookieEnv -Name "LYRA_COOKIE_ALINASSERSABRY" }
if ($Account -in @("both", "holmesberg")) { Import-UserCookieEnv -Name "LYRA_COOKIE_HOLMESBERG" }

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $OutFile = "tmp/proof-preflight/$stamp-$Topology-$Account.json"
}

$topologyArgs = @("scripts/verify_runtime_topology.mjs", "--topology", $Topology, "--skip-browser")
if ($Topology -eq "local-current") {
  $topologyArgs += @("--frontend", $FrontendOrigin, "--api", $ApiOrigin, "--nextauth", $FrontendOrigin)
  if ($ProxyApi) { $topologyArgs += "--proxy-api" }
}
Push-Location $repoRoot
try {
  node @topologyArgs
  if ($LASTEXITCODE -ne 0) { throw "runtime topology preflight failed with exit code $LASTEXITCODE" }

  $args = @(
    "scripts/proof_preflight.mjs",
    "--topology", $Topology,
    "--frontend", $FrontendOrigin,
    "--api", $ApiOrigin,
    "--account", $Account,
    "--intent", $Intent,
    "--timeout-ms", [string]$TimeoutMs,
    "--max-export-bytes", [string]$MaxExportBytes,
    "--max-pending-notifications", [string]$MaxPendingNotifications,
    "--out-file", $OutFile
  )
  if ($ExpectedFrontendBuildId) { $args += @("--expected-frontend-build", $ExpectedFrontendBuildId) }
  if ($TargetPath) { $args += @("--target-path", $TargetPath) }
  if ($ReadySelector) { $args += @("--ready-selector", $ReadySelector) }
  if ($SelectedDate) { $args += @("--selected-date", $SelectedDate) }
  if ($SelectedWeek) { $args += @("--selected-week", $SelectedWeek) }
  if ($SyntheticPrefix) { $args += @("--synthetic-prefix", $SyntheticPrefix) }
  if ($ProxyApi) { $args += "--proxy-api" }
  if ($FixtureAccountReady) { $args += "--fixture-account-ready" }
  if ($RequireAccountReady) { $args += "--require-account-ready" }

  node @args
  if ($LASTEXITCODE -ne 0) { throw "proof preflight blocked the run with exit code $LASTEXITCODE" }
} finally {
  Pop-Location
}

[ordered]@{
  ok = $true
  classification = "proof_preflight_passed"
  topology = $Topology
  frontend_origin = $FrontendOrigin
  api_origin = $ApiOrigin
  port_ownership = $portProof
  account = $Account
  intent = $Intent
  artifact = $OutFile
  backend_test_entrypoint = "scripts/run_backend_pytest.ps1"
} | ConvertTo-Json -Depth 6
