param(
    [switch]$ForceRestart
)

$ErrorActionPreference = "Stop"
$forceValue = if ($ForceRestart) { "1" } else { "0" }

$bashScript = @'
set -euo pipefail

FORCE_RESTART='__FORCE_RESTART__'
CLOUDFLARED="${HOME}/.local/bin/cloudflared"
LOG_DIR="${HOME}/.lyra-logs"
LOG_FILE="${LOG_DIR}/cloudflared-lyra-prod.log"
TUNNEL_NAME='lyra-prod'

mkdir -p "$LOG_DIR"

if [ ! -x "$CLOUDFLARED" ]; then
  echo "ERROR: cloudflared not found at $CLOUDFLARED" >&2
  exit 41
fi

if pgrep -f "cloudflared tunnel run .*lyra-prod" >/dev/null; then
  if [ "$FORCE_RESTART" = "1" ]; then
    echo "Stopping existing cloudflared connector(s)..."
    pkill -f "cloudflared tunnel run .*lyra-prod" || true
    sleep 3
  else
    echo "cloudflared already appears to be running for lyra-prod."
    "$CLOUDFLARED" tunnel info "$TUNNEL_NAME" || true
    exit 0
  fi
fi

echo "Starting cloudflared tunnel for $TUNNEL_NAME..."
echo "Log: $LOG_FILE"
nohup "$CLOUDFLARED" tunnel run \
  --dns-resolver-addrs 1.1.1.1:53 \
  --dns-resolver-addrs 8.8.8.8:53 \
  "$TUNNEL_NAME" > "$LOG_FILE" 2>&1 &
disown

sleep 10

if ! pgrep -f "cloudflared tunnel run .*lyra-prod" >/dev/null; then
  echo "ERROR: cloudflared did not remain running." >&2
  tail -120 "$LOG_FILE" >&2 || true
  exit 42
fi

tail -80 "$LOG_FILE"
echo "== tunnel info =="
"$CLOUDFLARED" tunnel info "$TUNNEL_NAME"
'@

$bashScript = $bashScript.Replace("__FORCE_RESTART__", $forceValue)

$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bashScript))
& wsl.exe -e bash -lc "echo $encoded | base64 -d | bash"

if ($LASTEXITCODE -ne 0) {
    throw "WSL cloudflared restart failed with exit code $LASTEXITCODE."
}
