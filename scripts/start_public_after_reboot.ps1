param(
    [switch]$NoBuild,
    [switch]$SkipFrontendBuild,
    [switch]$SkipPublicCheck,
    [int]$DockerWaitSeconds = 240,
    [int]$DockerPollSeconds = 5
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "== $Message =="
}

function Convert-ToWslPathLiteral($WindowsPath) {
    $resolved = (Resolve-Path $WindowsPath).Path
    if ($resolved -notmatch '^([A-Za-z]):\\(.*)$') {
        throw "Expected a drive-letter path, got: $resolved"
    }
    $drive = $matches[1].ToLowerInvariant()
    $rest = $matches[2] -replace '\\', '/'
    return "/mnt/$drive/$rest"
}

function ConvertTo-Lf([string]$Text) {
    return ($Text -replace "`r`n", "`n" -replace "`r", "`n")
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendDir = Join-Path $repoRoot "frontend"
$wslFrontendDir = Convert-ToWslPathLiteral $frontendDir
$safeWslFrontendDir = $wslFrontendDir.Replace("'", "'\''")

Write-Step "Starting Docker Desktop"
if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -WindowStyle Hidden
}

$dockerWaitStartedAt = Get-Date
$deadline = (Get-Date).AddSeconds($DockerWaitSeconds)
Write-Host "Waiting for Docker to become ready (timeout ${DockerWaitSeconds}s; typical boot is 30-40s)..."
do {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        $elapsedSeconds = [int]((Get-Date) - $dockerWaitStartedAt).TotalSeconds
        Write-Host "Docker is ready after ${elapsedSeconds}s."
        break
    }
    if ((Get-Date) -ge $deadline) {
        throw "Docker Desktop did not become ready within $DockerWaitSeconds seconds."
    }
    $elapsedSeconds = [int]((Get-Date) - $dockerWaitStartedAt).TotalSeconds
    Write-Host "Docker not ready yet (${elapsedSeconds}s elapsed); checking again in ${DockerPollSeconds}s..."
    Start-Sleep -Seconds $DockerPollSeconds
} while ($true)

Write-Step "Starting backend and Redis"
& (Join-Path $repoRoot "scripts\restart_backend_public.ps1") `
    -ApprovedPublicRestart `
    -NoBuild:$NoBuild `
    -SkipHostedCheck

Write-Step "Starting OpenClaw operator relay"
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\start_openclaw_operator_relay.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "OpenClaw operator relay start failed."
}

Write-Step "Starting public frontend in WSL"
$skipBuildValue = if ($NoBuild -or $SkipFrontendBuild) { "1" } else { "0" }
$bash = @"
set -euo pipefail
source ~/.nvm/nvm.sh
FRONTEND_DIR='$safeWslFrontendDir'
SESSION='lyra-frontend'
START_SCRIPT='/tmp/start_lyra_frontend.sh'
FRONTEND_LOG='/tmp/frontend.log'
PUBLIC_NEXT_DIR='.next-public'

cd "`$FRONTEND_DIR"
export NEXT_TELEMETRY_DISABLED=1

tmux kill-session -t "`$SESSION" 2>/dev/null || true
mapfile -t pids < <(
  ps -eo pid=,args= |
    grep -E 'next-server|next/dist/bin/next build|node scripts/public-topology|npm run start:public' |
    grep -v grep |
    awk '{print `$1}'
)
if [ "`${#pids[@]}" -gt 0 ]; then
  kill -TERM "`${pids[@]}" 2>/dev/null || true
  sleep 2
  kill -KILL "`${pids[@]}" 2>/dev/null || true
fi

if [ '$skipBuildValue' != '1' ]; then
  rm -rf "`$PUBLIC_NEXT_DIR"
  npm run build:public
fi

if [ ! -s "`$PUBLIC_NEXT_DIR/BUILD_ID" ]; then
  echo "ERROR: `$PUBLIC_NEXT_DIR/BUILD_ID is missing. Build public frontend first." >&2
  exit 42
fi

cat > "`$START_SCRIPT" <<EOS
#!/usr/bin/env bash
set -euo pipefail
source ~/.nvm/nvm.sh
cd '$safeWslFrontendDir'
export NEXT_TELEMETRY_DISABLED=1
exec npm run start:public > /tmp/frontend.log 2>&1
EOS
chmod +x "`$START_SCRIPT"
: > "`$FRONTEND_LOG"
tmux new-session -d -s "`$SESSION" "`$START_SCRIPT"
ready=0
for second in `$(seq 1 45); do
  if curl -fsS -o /dev/null --max-time 2 http://localhost:3000/; then
    echo "wsl_frontend_ready_after:`${second}s"
    ready=1
    break
  fi
  sleep 1
done
if [ "`$ready" != '1' ]; then
  echo 'ERROR: WSL frontend did not become ready within 45s.' >&2
  tail -80 "`$FRONTEND_LOG" >&2 || true
  exit 44
fi
tail -30 "`$FRONTEND_LOG"
curl -s -o /dev/null -w 'wsl_frontend:%{http_code},time=%{time_total}\n' --max-time 15 http://localhost:3000/
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Lf $bash)))
wsl.exe -d Ubuntu -e bash -lc "echo $encoded | base64 -d | bash"
if ($LASTEXITCODE -ne 0) {
    throw "WSL frontend start failed."
}

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
