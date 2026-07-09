param(
    [switch]$ForceRestart
)

$ErrorActionPreference = "Stop"
$forceValue = if ($ForceRestart) { "1" } else { "0" }

function ConvertTo-Lf([string]$Text) {
    return ($Text -replace "`r`n", "`n" -replace "`r", "`n")
}

$dnsRepairScript = @'
set -euo pipefail

# WSL can regenerate /etc/resolv.conf after laptop restarts with the Windows
# DNS proxy. That proxy has failed SRV lookups for Cloudflare tunnel edges, so
# repair it before cloudflared starts.
cat > /etc/resolv.conf <<'EOF'
nameserver 1.1.1.1
nameserver 8.8.8.8
EOF

getent hosts region1.v2.argotunnel.com >/dev/null
'@

$dnsEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Lf $dnsRepairScript)))
& wsl.exe -u root -e bash -lc "echo $dnsEncoded | base64 -d | bash"

if ($LASTEXITCODE -ne 0) {
    throw "WSL DNS repair failed with exit code $LASTEXITCODE."
}

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

if pgrep -f "cloudflared tunnel .*lyra-prod" >/dev/null; then
  if [ "$FORCE_RESTART" = "1" ]; then
    echo "Stopping existing cloudflared connector(s)..."
    pkill -f "cloudflared tunnel .*lyra-prod" || true
    sleep 3
  else
    echo "cloudflared already appears to be running for lyra-prod."
    "$CLOUDFLARED" tunnel info "$TUNNEL_NAME" || true
    exit 0
  fi
fi

echo "Starting cloudflared tunnel for $TUNNEL_NAME..."
echo "Log: $LOG_FILE"
nohup "$CLOUDFLARED" tunnel \
  --protocol http2 \
  --edge-ip-version 4 \
  run \
  "$TUNNEL_NAME" > "$LOG_FILE" 2>&1 &
disown

sleep 10

if ! pgrep -f "cloudflared tunnel .*lyra-prod" >/dev/null; then
  echo "ERROR: cloudflared did not remain running." >&2
  tail -120 "$LOG_FILE" >&2 || true
  exit 42
fi

tail -80 "$LOG_FILE"
echo "== tunnel info =="
"$CLOUDFLARED" tunnel info "$TUNNEL_NAME"
'@

$bashScript = $bashScript.Replace("__FORCE_RESTART__", $forceValue)

$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Lf $bashScript)))
& wsl.exe -e bash -lc "echo $encoded | base64 -d | bash"

if ($LASTEXITCODE -ne 0) {
    throw "WSL cloudflared restart failed with exit code $LASTEXITCODE."
}
