param(
    [switch]$NoBuild,
    [switch]$SkipFrontendBuild,
    [switch]$SkipPublicCheck,
    [switch]$SkipRelay,
    [int]$DockerWaitSeconds = 240,
    [int]$DockerPollSeconds = 5
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "== $Message =="
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Step "Starting backend and Redis"
$backendArgs = @{
    ApprovedPublicRestart = $true
    SkipHostedCheck = $true
    DockerWaitSeconds = $DockerWaitSeconds
    DockerPollSeconds = $DockerPollSeconds
}
if ($NoBuild) {
    $backendArgs.NoBuild = $true
}
& (Join-Path $repoRoot "scripts\restart_backend_public.ps1") @backendArgs

if (-not $SkipRelay) {
    Write-Step "Starting OpenClaw operator relay"
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\start_openclaw_operator_relay.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "OpenClaw operator relay start failed."
    }
}

Write-Step "Starting public frontend in WSL"
$frontendArgs = @{
    SkipPublicCheck = $true
}
if ($NoBuild -or $SkipFrontendBuild) {
    $frontendArgs.NoBuild = $true
}
& (Join-Path $repoRoot "scripts\restart_frontend_wsl.ps1") @frontendArgs

Write-Step "Starting Cloudflare tunnel"
powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\restart_cloudflared_wsl.ps1") -ForceRestart
if ($LASTEXITCODE -ne 0) {
    throw "cloudflared restart failed."
}

if (-not $SkipPublicCheck) {
    Write-Step "Verifying public runtime"
    node (Join-Path $repoRoot "scripts\verify_runtime_topology.mjs") --topology public --skip-browser
    if ($LASTEXITCODE -ne 0) {
        throw "public topology verification failed."
    }

    $front = Invoke-WebRequest -Uri "https://lyraos.org/" -UseBasicParsing -TimeoutSec 20
    $api = Invoke-WebRequest -Uri "https://api.lyraos.org/v1/health" -UseBasicParsing -TimeoutSec 20
    Write-Host "lyraos.org: $($front.StatusCode)"
    Write-Host "api.lyraos.org/v1/health: $($api.StatusCode) $($api.Content)"
}

Write-Host ""
Write-Host "LyraOS public stack is up."
