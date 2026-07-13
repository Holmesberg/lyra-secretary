$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$startPath = Join-Path $PSScriptRoot "start_local_current_proof_runtime.ps1"
$stopPath = Join-Path $PSScriptRoot "stop_local_current_proof_runtime.ps1"
$startSource = Get-Content -Raw -LiteralPath $startPath
$stopSource = Get-Content -Raw -LiteralPath $stopPath

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
