param(
  [Parameter(Mandatory = $true)]
  [string]$OutFile,

  [string]$FrontendOrigin = "https://lyraos.org",
  [string]$ApiOrigin = "https://api.lyraos.org"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repoRoot ".venv311\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
  throw "Project Python is missing at $python. Plain python fallback is forbidden."
}

$cookie = [Environment]::GetEnvironmentVariable("LYRA_COOKIE_ALINASSERSABRY", "User")
if ([string]::IsNullOrWhiteSpace($cookie)) {
  $cookie = (Get-ItemProperty -Path "HKCU:\Environment" -Name "LYRA_COOKIE_ALINASSERSABRY" -ErrorAction SilentlyContinue).LYRA_COOKIE_ALINASSERSABRY
}
if ([string]::IsNullOrWhiteSpace($cookie) -or $cookie.Length -lt 300) {
  throw "LYRA_COOKIE_ALINASSERSABRY is missing or looks truncated."
}
$env:LYRA_COOKIE_ALINASSERSABRY = $cookie

$methodFiles = @(
  "backend/app/services/pause_policy_replay.py",
  "backend/app/services/pause_policy_replay_baselines.py",
  "backend/scripts/run_founder_pause_replay.py",
  "scripts/browser_founder_pause_replay.mjs",
  "scripts/run_founder_pause_replay.ps1"
)
$dirty = @(git status --porcelain=v1 -- @methodFiles)
if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) {
  throw "Founder pause replay method files must be committed and clean before holdout evaluation."
}
$methodCommit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $methodCommit -notmatch '^[0-9a-f]{40}$') {
  throw "Could not resolve exact method commit."
}

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "proof_preflight.ps1") `
  -Topology public `
  -Account operator `
  -Intent readonly `
  -FrontendOrigin $FrontendOrigin `
  -ApiOrigin $ApiOrigin `
  -MaxPendingNotifications 100000
if ($LASTEXITCODE -ne 0) { throw "Founder replay preflight failed." }

& node (Join-Path $PSScriptRoot "browser_founder_pause_replay.mjs") `
  --frontend $FrontendOrigin `
  --api $ApiOrigin `
  --python $python `
  --out-file $OutFile `
  --method-commit $methodCommit
if ($LASTEXITCODE -ne 0) { throw "Founder pause replay failed." }
