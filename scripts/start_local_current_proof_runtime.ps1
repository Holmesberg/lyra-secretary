param(
  [int]$FrontendPort = 3018,
  [int]$BackendPort = 8001,
  [string]$DistDir = ".next-local-current",
  [string]$ExpectedBuildId = "",
  [string]$OutFile = "tmp/local-current-runtime/active.json",
  [string]$PythonPath = "",
  [switch]$DisposableData,
  [ValidateRange(8, 15)]
  [int]$DisposableRedisDatabase = 15
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $repoRoot "frontend"
$backendDir = Join-Path $repoRoot "backend"
. (Join-Path $PSScriptRoot "local_frontend_topology.ps1")

function Resolve-RepoPath {
  param([Parameter(Mandatory = $true)][string]$PathValue)
  if ([IO.Path]::IsPathRooted($PathValue)) { return [IO.Path]::GetFullPath($PathValue) }
  return [IO.Path]::GetFullPath((Join-Path $repoRoot $PathValue))
}

function Assert-SafeDistDirectory {
  param([Parameter(Mandatory = $true)][string]$Name)
  if ($Name -notmatch '^\.next-local-current(?:-[A-Za-z0-9._-]+)?$') {
    throw "DistDir must be .next-local-current or a suffixed local-current artifact name."
  }
  $resolved = [IO.Path]::GetFullPath((Join-Path $frontendDir $Name))
  $frontendPrefix = $frontendDir.TrimEnd('\') + '\'
  if (-not $resolved.StartsWith($frontendPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "DistDir resolved outside frontend/."
  }
  return $resolved
}

function Assert-PortFree {
  param([Parameter(Mandatory = $true)][string]$Label, [Parameter(Mandatory = $true)][int]$Port)
  $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  if ($listeners.Count -gt 0) {
    $owners = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ","
    throw "$Label port $Port is already listening (pid=$owners). Refusing to kill or reuse it."
  }
}

function Resolve-ProjectPython {
  param([string]$ExplicitPath)
  $candidate = if ([string]::IsNullOrWhiteSpace($ExplicitPath)) {
    Join-Path $repoRoot ".venv311\Scripts\python.exe"
  } else {
    Resolve-RepoPath $ExplicitPath
  }
  if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
    throw "Project Python is missing at $candidate. Plain python fallback is forbidden."
  }
  & $candidate -c "import uvicorn" 2>$null
  if ($LASTEXITCODE -ne 0) {
    throw "Project Python cannot import uvicorn: $candidate"
  }
  return (Resolve-Path -LiteralPath $candidate).Path
}

function Get-RedisDatabaseSize {
  param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$RedisUrl
  )
  $size = & $Python -c "import redis,sys; print(redis.from_url(sys.argv[1], socket_connect_timeout=3, socket_timeout=3).dbsize())" $RedisUrl
  if ($LASTEXITCODE -ne 0 -or "$size" -notmatch '^\d+$') {
    throw "Could not inspect disposable Redis database at $RedisUrl."
  }
  return [int]$size
}

function Reset-DisposableRedisDatabase {
  param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$RedisUrl
  )
  & $Python -c "import redis,sys; r=redis.from_url(sys.argv[1], socket_connect_timeout=3, socket_timeout=3); r.flushdb(); print(r.dbsize())" $RedisUrl | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Could not reset disposable Redis database at $RedisUrl."
  }
}

function Wait-JsonEndpoint {
  param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][scriptblock]$Accept,
    [int]$Attempts = 90
  )
  $lastError = $null
  for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
    Start-Sleep -Seconds 1
    try {
      $body = Invoke-RestMethod -Uri $Url -TimeoutSec 4
      if (& $Accept $body) { return $body }
      $lastError = "endpoint returned unexpected topology"
    } catch {
      $lastError = $_.Exception.Message
    }
  }
  throw "$Label did not become ready at $Url. Last error: $lastError"
}

function Get-ListenerRecord {
  param([Parameter(Mandatory = $true)][int]$Port)
  $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
    Select-Object -First 1
  $process = Get-Process -Id $listener.OwningProcess -ErrorAction Stop
  return [ordered]@{
    pid = [int]$listener.OwningProcess
    started_at = $process.StartTime.ToUniversalTime().ToString("o")
  }
}

function Stop-StartedProcesses {
  param([System.Collections.Generic.List[int]]$ProcessIds)
  foreach ($processId in @($ProcessIds | Select-Object -Unique | Sort-Object -Descending)) {
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
  }
}

function Test-DescendsFromStartedProcess {
  param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][System.Collections.Generic.List[int]]$StartedProcessIds
  )
  $seen = @{}
  $currentId = $ProcessId
  for ($depth = 0; $depth -lt 8 -and $currentId -gt 0; $depth++) {
    if ($StartedProcessIds.Contains($currentId)) { return $true }
    if ($seen.ContainsKey($currentId)) { break }
    $seen[$currentId] = $true
    $current = Get-CimInstance Win32_Process -Filter "ProcessId = $currentId" -ErrorAction SilentlyContinue
    if (-not $current) { break }
    $currentId = [int]$current.ParentProcessId
  }
  return $false
}

$distPath = Assert-SafeDistDirectory -Name $DistDir
$manifestPath = Resolve-RepoPath $OutFile
if ([string]::IsNullOrWhiteSpace($ExpectedBuildId)) {
  $ExpectedBuildId = (& git -C $repoRoot rev-parse HEAD).Trim()
}
if ($ExpectedBuildId -notmatch '^[0-9a-f]{40}$') {
  throw "ExpectedBuildId must be the full 40-character commit SHA."
}

Assert-LocalNextArtifactIsolation -Reason "local-current proof runtime" -Topology local-current
Assert-PortFree -Label "frontend" -Port $FrontendPort
Assert-PortFree -Label "backend" -Port $BackendPort
$python = Resolve-ProjectPython -ExplicitPath $PythonPath

$runId = "{0}-{1}" -f (Get-Date -Format "yyyyMMdd-HHmmss"), $ExpectedBuildId.Substring(0, 7)
$runDir = Join-Path $repoRoot "tmp\local-current-runtime\$runId"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$backendOut = Join-Path $runDir "backend.out.log"
$backendErr = Join-Path $runDir "backend.err.log"
$buildOut = Join-Path $runDir "frontend-build.out.log"
$buildErr = Join-Path $runDir "frontend-build.err.log"
$frontendOut = Join-Path $runDir "frontend.out.log"
$frontendErr = Join-Path $runDir "frontend.err.log"
$startedPids = [System.Collections.Generic.List[int]]::new()
$frontendOrigin = "http://localhost:$FrontendPort"
$apiOrigin = "http://localhost:$BackendPort"
$disposableDatabasePath = Join-Path $runDir "disposable.sqlite"
$disposableDatabaseUrl = "sqlite:///$(($disposableDatabasePath -replace '\\', '/'))"
$disposableRedisUrl = "redis://localhost:6379/$DisposableRedisDatabase"
$migrationOut = Join-Path $runDir "alembic.out.log"
$migrationErr = Join-Path $runDir "alembic.err.log"
$disposableRedisOwned = $false

try {
  $savedEnvironment = @{
    BUILD_ID = $env:BUILD_ID
    FRONTEND_URL = $env:FRONTEND_URL
    CORS_ALLOWED_ORIGINS = $env:CORS_ALLOWED_ORIGINS
    DATABASE_URL = $env:DATABASE_URL
    REDIS_URL = $env:REDIS_URL
    USER_EMAIL_ENABLED = $env:USER_EMAIL_ENABLED
    OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED = $env:OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED
    OPENCLAW_MIRROR_USER_NOTIFICATIONS = $env:OPENCLAW_MIRROR_USER_NOTIFICATIONS
  }
  try {
    $env:BUILD_ID = $ExpectedBuildId
    $env:FRONTEND_URL = $frontendOrigin
    $env:CORS_ALLOWED_ORIGINS = $frontendOrigin
    if ($DisposableData) {
      $existingRedisKeys = Get-RedisDatabaseSize -Python $python -RedisUrl $disposableRedisUrl
      if ($existingRedisKeys -ne 0) {
        throw "Disposable Redis database $DisposableRedisDatabase is not empty ($existingRedisKeys keys). Refusing to erase unknown state."
      }
      $disposableRedisOwned = $true
      $env:DATABASE_URL = $disposableDatabaseUrl
      $env:REDIS_URL = $disposableRedisUrl
      $env:USER_EMAIL_ENABLED = "false"
      $env:OPENCLAW_OPERATOR_NOTIFICATIONS_ENABLED = "false"
      $env:OPENCLAW_MIRROR_USER_NOTIFICATIONS = "false"
      $migration = Start-Process -FilePath $python `
        -ArgumentList @("-m", "alembic", "upgrade", "head") `
        -WorkingDirectory $backendDir -WindowStyle Hidden `
        -RedirectStandardOutput $migrationOut -RedirectStandardError $migrationErr -PassThru -Wait
      if ($migration.ExitCode -ne 0) {
        throw "Disposable database migration failed with exit code $($migration.ExitCode). Logs: $migrationOut ; $migrationErr"
      }
    }
    $backend = Start-Process -FilePath $python `
      -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort", "--lifespan", "off") `
      -WorkingDirectory $backendDir -WindowStyle Hidden `
      -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
    $startedPids.Add([int]$backend.Id)
  } finally {
    foreach ($name in $savedEnvironment.Keys) {
      $value = $savedEnvironment[$name]
      if ($null -eq $value) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
      else { Set-Item "Env:$name" $value }
    }
  }

  $backendTopology = Wait-JsonEndpoint -Label "backend" -Url "$apiOrigin/v1/health/topology" -Accept {
    param($body)
    $body.build_id -eq $ExpectedBuildId -and $body.api_origin -eq $apiOrigin
  }

  if (Test-Path -LiteralPath $distPath) {
    Remove-Item -LiteralPath $distPath -Recurse -Force
  }

  $savedFrontendEnvironment = @{
    NEXT_DIST_DIR = $env:NEXT_DIST_DIR
    NEXT_PUBLIC_API_URL = $env:NEXT_PUBLIC_API_URL
    NEXT_PUBLIC_BUILD_ID = $env:NEXT_PUBLIC_BUILD_ID
    NEXTAUTH_URL = $env:NEXTAUTH_URL
  }
  $tsconfigPath = Join-Path $frontendDir "tsconfig.json"
  $tsconfigSnapshot = Join-Path $runDir "tsconfig.original.json"
  Copy-Item -LiteralPath $tsconfigPath -Destination $tsconfigSnapshot
  try {
    $env:NEXT_DIST_DIR = $DistDir
    $env:NEXT_PUBLIC_API_URL = $apiOrigin
    $env:NEXT_PUBLIC_BUILD_ID = $ExpectedBuildId
    $env:NEXTAUTH_URL = $frontendOrigin

    $build = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "build") `
      -WorkingDirectory $frontendDir -WindowStyle Hidden `
      -RedirectStandardOutput $buildOut -RedirectStandardError $buildErr -PassThru -Wait
    if ($build.ExitCode -ne 0) {
      throw "Frontend build failed with exit code $($build.ExitCode). Logs: $buildOut ; $buildErr"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $distPath "BUILD_ID") -PathType Leaf)) {
      throw "Frontend build completed without $DistDir/BUILD_ID."
    }

    $frontend = Start-Process -FilePath "npm.cmd" `
      -ArgumentList @("run", "start", "--", "-p", "$FrontendPort") `
      -WorkingDirectory $frontendDir -WindowStyle Hidden `
      -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru
    $startedPids.Add([int]$frontend.Id)
  } finally {
    # Next adds custom dist type paths and reformats tsconfig.json during a
    # build. Restore the exact pre-build bytes so proof cannot dirty source.
    Copy-Item -LiteralPath $tsconfigSnapshot -Destination $tsconfigPath -Force
    foreach ($name in $savedFrontendEnvironment.Keys) {
      $value = $savedFrontendEnvironment[$name]
      if ($null -eq $value) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
      else { Set-Item "Env:$name" $value }
    }
  }

  $frontendTopology = Wait-JsonEndpoint -Label "frontend" -Url "$frontendOrigin/api/topology" -Accept {
    param($body)
    $body.frontend_origin -eq $frontendOrigin -and
      $body.compiled_api_origin -eq $apiOrigin -and
      $body.nextauth_url -eq $frontendOrigin -and
      $body.build_id -eq $ExpectedBuildId
  }

  $backendListener = Get-ListenerRecord -Port $BackendPort
  $frontendListener = Get-ListenerRecord -Port $FrontendPort
  foreach ($record in @($backendListener, $frontendListener)) {
    if (-not $startedPids.Contains([int]$record.pid)) { $startedPids.Add([int]$record.pid) }
  }

  $manifest = [ordered]@{
    ok = $true
    classification = "local_current_runtime_ready"
    topology = "local-current"
    repo_root = $repoRoot
    run_dir = $runDir
    expected_build_id = $ExpectedBuildId
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    frontend = [ordered]@{
      origin = $frontendOrigin
      port = $FrontendPort
      launch_pid = [int]$frontend.Id
      listener_pid = [int]$frontendListener.pid
      listener_started_at = $frontendListener.started_at
      dist_dir = $DistDir
      dist_path = $distPath
      topology = $frontendTopology
      stdout = $frontendOut
      stderr = $frontendErr
      build_stdout = $buildOut
      build_stderr = $buildErr
    }
    backend = [ordered]@{
      origin = $apiOrigin
      port = $BackendPort
      launch_pid = [int]$backend.Id
      listener_pid = [int]$backendListener.pid
      listener_started_at = $backendListener.started_at
      python = $python
      topology = $backendTopology
      stdout = $backendOut
      stderr = $backendErr
    }
    data = if ($DisposableData) {
      [ordered]@{
        mode = "disposable"
        target_account_state = "unprovisioned"
        database_path = $disposableDatabasePath
        redis_url = $disposableRedisUrl
        redis_database = $DisposableRedisDatabase
        migration_stdout = $migrationOut
        migration_stderr = $migrationErr
      }
    } else {
      [ordered]@{ mode = "shared" }
    }
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $manifestPath) | Out-Null
  $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
  $manifest | ConvertTo-Json -Depth 8
} catch {
  foreach ($port in @($FrontendPort, $BackendPort)) {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -First 1
    if (
      $listener -and
      (Test-DescendsFromStartedProcess -ProcessId ([int]$listener.OwningProcess) -StartedProcessIds $startedPids)
    ) {
      $startedPids.Add([int]$listener.OwningProcess)
    }
  }
  Stop-StartedProcesses -ProcessIds $startedPids
  if ($DisposableData -and $disposableRedisOwned) {
    Reset-DisposableRedisDatabase -Python $python -RedisUrl $disposableRedisUrl
    foreach ($path in @($disposableDatabasePath, "$disposableDatabasePath-wal", "$disposableDatabasePath-shm")) {
      if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
  }
  Write-Host "Local-current startup failed. Backend logs: $backendOut ; $backendErr"
  Write-Host "Frontend logs: $frontendOut ; $frontendErr"
  throw
}
