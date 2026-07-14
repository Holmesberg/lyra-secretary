param(
  [string]$Manifest = "tmp/local-current-runtime/active.json",
  [switch]$RemoveArtifact,
  [switch]$RemoveDisposableData
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = if ([IO.Path]::IsPathRooted($Manifest)) {
  [IO.Path]::GetFullPath($Manifest)
} else {
  [IO.Path]::GetFullPath((Join-Path $repoRoot $Manifest))
}
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
  throw "Local-current runtime manifest does not exist: $manifestPath"
}

$runtime = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ($runtime.topology -ne "local-current") { throw "Manifest is not local-current." }
if (-not ([string]$runtime.repo_root).Equals($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
  throw "Manifest belongs to a different checkout: $($runtime.repo_root)"
}

function Stop-RecordedProcess {
  param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [string]$ExpectedStartedAt = ""
  )
  $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
  if (-not $process) { return }
  if ($ExpectedStartedAt) {
    $actual = $process.StartTime.ToUniversalTime()
    $expected = [DateTime]::Parse($ExpectedStartedAt).ToUniversalTime()
    if ([Math]::Abs(($actual - $expected).TotalSeconds) -gt 2) {
      throw "PID $ProcessId was reused; refusing to stop it."
    }
  }
  Stop-Process -Id $ProcessId -Force
}

foreach ($service in @($runtime.frontend, $runtime.backend)) {
  $listeners = @(Get-NetTCPConnection -LocalPort ([int]$service.port) -State Listen -ErrorAction SilentlyContinue)
  foreach ($listener in $listeners) {
    if ([int]$listener.OwningProcess -ne [int]$service.listener_pid) {
      throw "Port $($service.port) is now owned by unexpected PID $($listener.OwningProcess); refusing teardown."
    }
  }
}

Stop-RecordedProcess -ProcessId ([int]$runtime.frontend.listener_pid) -ExpectedStartedAt ([string]$runtime.frontend.listener_started_at)
if ([int]$runtime.frontend.launch_pid -ne [int]$runtime.frontend.listener_pid) {
  Stop-RecordedProcess -ProcessId ([int]$runtime.frontend.launch_pid)
}
Stop-RecordedProcess -ProcessId ([int]$runtime.backend.listener_pid) -ExpectedStartedAt ([string]$runtime.backend.listener_started_at)
if ([int]$runtime.backend.launch_pid -ne [int]$runtime.backend.listener_pid) {
  Stop-RecordedProcess -ProcessId ([int]$runtime.backend.launch_pid)
}

Start-Sleep -Seconds 1
foreach ($service in @($runtime.frontend, $runtime.backend)) {
  if (Get-NetTCPConnection -LocalPort ([int]$service.port) -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $($service.port) is still listening after teardown."
  }
}

if ($RemoveArtifact) {
  $frontendDir = [IO.Path]::GetFullPath((Join-Path $repoRoot "frontend"))
  $distPath = [IO.Path]::GetFullPath([string]$runtime.frontend.dist_path)
  $frontendPrefix = $frontendDir.TrimEnd('\') + '\'
  $leaf = Split-Path -Leaf $distPath
  if (
    -not $distPath.StartsWith($frontendPrefix, [StringComparison]::OrdinalIgnoreCase) -or
    $leaf -notmatch '^\.next-local-current(?:-[A-Za-z0-9._-]+)?$'
  ) {
    throw "Refusing to remove unsafe artifact path: $distPath"
  }
  if (Test-Path -LiteralPath $distPath) {
    Remove-Item -LiteralPath $distPath -Recurse -Force
  }
}

$disposableDataRemoved = $false
if ($RemoveDisposableData) {
  if ([string]$runtime.data.mode -ne "disposable") {
    throw "Manifest does not own disposable runtime data."
  }
  $runtimePrefix = [IO.Path]::GetFullPath((Join-Path $repoRoot "tmp\local-current-runtime")).TrimEnd('\') + '\'
  $runDir = [IO.Path]::GetFullPath([string]$runtime.run_dir).TrimEnd('\')
  if (-not ($runDir + '\').StartsWith($runtimePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to trust unsafe disposable run directory: $runDir"
  }
  $databasePath = [IO.Path]::GetFullPath([string]$runtime.data.database_path)
  if (
    -not $databasePath.StartsWith(($runDir + '\'), [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $databasePath) -ne "disposable.sqlite"
  ) {
    throw "Refusing to remove unsafe disposable database path: $databasePath"
  }
  $redisDatabase = [int]$runtime.data.redis_database
  $expectedRedisUrl = "redis://localhost:6379/$redisDatabase"
  if ($redisDatabase -lt 8 -or $redisDatabase -gt 15 -or [string]$runtime.data.redis_url -ne $expectedRedisUrl) {
    throw "Refusing to reset unsafe disposable Redis target."
  }
  $python = [IO.Path]::GetFullPath([string]$runtime.backend.python)
  $expectedPython = [IO.Path]::GetFullPath((Join-Path $repoRoot ".venv311\Scripts\python.exe"))
  if (-not $python.Equals($expectedPython, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to invoke Python outside this checkout's .venv311."
  }
  & $python -c "import redis,sys; r=redis.from_url(sys.argv[1], socket_connect_timeout=3, socket_timeout=3); r.flushdb(); print(r.dbsize())" $expectedRedisUrl | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Disposable Redis reset failed." }
  foreach ($path in @($databasePath, "$databasePath-wal", "$databasePath-shm")) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
  }
  $disposableDataRemoved = $true
}

[ordered]@{
  ok = $true
  classification = "local_current_runtime_stopped"
  manifest = $manifestPath
  artifact_removed = [bool]$RemoveArtifact
  disposable_data_removed = $disposableDataRemoved
} | ConvertTo-Json
