param(
    [string]$ContainerName = "openclaw-openclaw-gateway-1",
    [int]$QueueUserId = 1,
    [switch]$StatusOnly
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "== $Message =="
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$relaySource = Join-Path $repoRoot "scripts\openclaw_operator_relay.mjs"
$relayTarget = "/tmp/lyra_openclaw_operator_relay.mjs"
$logTarget = "/tmp/lyra-openclaw-operator-relay.log"

if (-not (Test-Path $relaySource)) {
    throw "Relay source not found: $relaySource"
}

$running = docker inspect -f "{{.State.Running}}" $ContainerName 2>$null
if ($LASTEXITCODE -ne 0 -or $running -ne "true") {
    throw "OpenClaw gateway container is not running: $ContainerName"
}

if ($StatusOnly) {
    docker exec $ContainerName sh -lc "pgrep -af '[l]yra_openclaw_operator_relay.mjs' || true"
    exit $LASTEXITCODE
}

Write-Step "Installing OpenClaw operator relay"
docker cp $relaySource "${ContainerName}:$relayTarget"
if ($LASTEXITCODE -ne 0) {
    throw "docker cp failed."
}

Write-Step "Restarting OpenClaw operator relay"
docker exec $ContainerName sh -lc "if pgrep -f '[l]yra_openclaw_operator_relay.mjs' >/dev/null; then pkill -f '[l]yra_openclaw_operator_relay.mjs' || true; fi; true"
if ($LASTEXITCODE -ne 0) {
    throw "failed to stop existing relay."
}

docker exec -d $ContainerName sh -lc "LYRA_OPERATOR_QUEUE_USER_ID='$QueueUserId' LYRA_OPERATOR_REDIS_HOST='redis' LYRA_OPERATOR_REDIS_PORT='6379' nohup node '$relayTarget' >> '$logTarget' 2>&1 &"
if ($LASTEXITCODE -ne 0) {
    throw "failed to start relay."
}

Start-Sleep -Seconds 2
$process = docker exec $ContainerName sh -lc "pgrep -af '[l]yra_openclaw_operator_relay.mjs' || true"
if (-not $process) {
    docker exec $ContainerName sh -lc "tail -80 '$logTarget' || true"
    throw "OpenClaw operator relay did not stay running."
}

Write-Host $process
Write-Step "Relay log tail"
docker exec $ContainerName sh -lc "tail -20 '$logTarget' || true"
