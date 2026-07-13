$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$startPath = Join-Path $PSScriptRoot "start_local_current_proof_runtime.ps1"
$stopPath = Join-Path $PSScriptRoot "stop_local_current_proof_runtime.ps1"
$startSource = Get-Content -Raw -LiteralPath $startPath
$stopSource = Get-Content -Raw -LiteralPath $stopPath
$preflightSource = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "proof_preflight.ps1")
$pytestSource = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot "run_backend_pytest.ps1")

$requiredStartFragments = @(
  '.venv311\Scripts\python.exe',
  'Plain python fallback is forbidden',
  'Assert-LocalNextArtifactIsolation',
  '/v1/health/topology',
  'NEXT_DIST_DIR',
  '.next-local-current',
  'Refusing to kill or reuse it',
  'Test-DescendsFromStartedProcess',
  'tsconfig.original.json',
  'Restore the exact pre-build bytes',
  '[switch]$DisposableData',
  'target_account_state = "unprovisioned"',
  'Refusing to erase unknown state',
  'ConvertTo-Json -Depth 8'
)
foreach ($fragment in $requiredStartFragments) {
  if (-not $startSource.Contains($fragment)) { throw "Launcher contract missing: $fragment" }
}
if ($startSource -match 'Get-Command\s+python') { throw "Launcher restored a plain-python fallback." }
if (-not $stopSource.Contains('PID $ProcessId was reused; refusing to stop it.')) {
  throw "Teardown does not fail closed on PID reuse."
}
if (-not $stopSource.Contains('Refusing to remove unsafe artifact path')) {
  throw "Teardown does not bound artifact deletion."
}
if (-not $stopSource.Contains('Refusing to remove unsafe disposable database path')) {
  throw "Teardown does not bound disposable database deletion."
}
if (-not $stopSource.Contains('Refusing to trust unsafe disposable run directory')) {
  throw "Teardown does not bind disposable deletion to the recorded run directory."
}
if (-not $stopSource.Contains("Refusing to invoke Python outside this checkout's .venv311.")) {
  throw "Teardown does not bind Redis cleanup to the project interpreter."
}
if (-not $stopSource.Contains('Refusing to reset unsafe disposable Redis target.')) {
  throw "Teardown does not bound disposable Redis reset."
}
if (-not $preflightSource.Contains('[string]$RuntimeManifest')) {
  throw "Proof preflight cannot consume the runtime ownership manifest."
}
if (-not $preflightSource.Contains('RuntimeManifest build ID does not match')) {
  throw "Proof preflight does not bind runtime ownership to the expected build."
}
if (-not $preflightSource.Contains('Disposable local-current data supports Holmesberg proof only')) {
  throw "Proof preflight does not reject operator proof against disposable account state."
}
if ($pytestSource -match 'Get-Command\s+python') {
  throw "Backend pytest restored a system-Python fallback."
}
if (-not $pytestSource.Contains('Plain python fallback is forbidden')) {
  throw "Backend pytest does not fail closed when project Python is missing."
}

$frontendPort = 39118
$backendPort = 39801
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $frontendPort)
$listener.Start()
try {
  $blocked = $false
  try {
    & $startPath -FrontendPort $frontendPort -BackendPort $backendPort `
      -ExpectedBuildId ((& git -C $repoRoot rev-parse HEAD).Trim()) `
      -OutFile "tmp/local-current-runtime/contract-should-not-exist.json"
  } catch {
    if ($_.Exception.Message -match 'already listening') { $blocked = $true }
    else { throw }
  }
  if (-not $blocked) { throw "Occupied-port negative proof did not fail closed." }
} finally {
  $listener.Stop()
}

$missingPythonBlocked = $false
try {
  & $startPath -FrontendPort $frontendPort -BackendPort $backendPort `
    -PythonPath ".venv-does-not-exist\Scripts\python.exe" `
    -ExpectedBuildId ((& git -C $repoRoot rev-parse HEAD).Trim()) `
    -OutFile "tmp/local-current-runtime/contract-should-not-exist.json"
} catch {
  if ($_.Exception.Message -match 'Project Python is missing') { $missingPythonBlocked = $true }
  else { throw }
}
if (-not $missingPythonBlocked) { throw "Missing-project-Python negative proof did not fail closed." }

if (Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue) {
  throw "Negative proof unexpectedly started the backend."
}
if (Test-Path -LiteralPath (Join-Path $repoRoot "tmp/local-current-runtime/contract-should-not-exist.json")) {
  throw "Negative proof unexpectedly wrote a ready manifest."
}

Write-Host "local-current proof runtime contract: ok"
