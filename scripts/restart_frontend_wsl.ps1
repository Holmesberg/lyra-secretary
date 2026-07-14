param(
    [switch]$NoBuild,
    [switch]$SkipPublicCheck
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$wslRepoRoot = (& wsl.exe wslpath -a $repoRoot.Path).Trim()
if (-not $wslRepoRoot) {
    throw "Could not resolve repo root inside WSL."
}

$noBuildValue = if ($NoBuild) { "1" } else { "0" }
$skipPublicValue = if ($SkipPublicCheck) { "1" } else { "0" }
$safeWslRepoRoot = $wslRepoRoot.Replace("'", "'\''")

$bashScript = @"
set -euo pipefail

FRONTEND_DIR='$safeWslRepoRoot/frontend'
NO_BUILD='$noBuildValue'
SKIP_PUBLIC_CHECK='$skipPublicValue'
SESSION='lyra-frontend'
START_SCRIPT='/tmp/start_lyra_frontend.sh'
FRONTEND_LOG='/tmp/frontend.log'
PUBLIC_NEXT_DIR='.next-public'
STAGING_NEXT_DIR=".next-public.staging.`$`$"
PREVIOUS_NEXT_DIR='.next-public.previous'
FAILED_NEXT_DIR=".next-public.failed.`$`$"

source ~/.nvm/nvm.sh

cd "`$FRONTEND_DIR"
export NEXT_TELEMETRY_DISABLED=1

SOURCE_STATUS="`$(git -C "`$FRONTEND_DIR/.." status --porcelain --untracked-files=all)"
if [ -n "`$SOURCE_STATUS" ]; then
  echo 'ERROR: refusing to deploy from a dirty tracked or untracked tree.' >&2
  printf '%s\n' "`$SOURCE_STATUS" >&2
  exit 48
fi

echo '== Lyra frontend WSL restart =='
echo "frontend_dir=`$FRONTEND_DIR"
echo "node=`$(which node) `$(`$(which node) -v)"
echo "npm=`$(which npm) `$(`$(which npm) -v)"

echo '== stopping stale frontend sessions/processes =='
tmux kill-session -t "`$SESSION" 2>/dev/null || true

mapfile -t pids < <(
  ps -eo pid=,args= |
    grep -E 'next-server|next build|next start|npm run build|npm run start' |
    grep -v grep |
    awk '{print `$1}'
)

if [ "`${#pids[@]}" -gt 0 ]; then
  echo "terminating: `${pids[*]}"
  kill -TERM "`${pids[@]}" 2>/dev/null || true
  sleep 2
  kill -KILL "`${pids[@]}" 2>/dev/null || true
else
  echo 'no stale next/npm frontend processes found'
fi

if [ "`$NO_BUILD" != '1' ]; then
  echo "== building public topology into staging artifact `$STAGING_NEXT_DIR =="
  rm -rf "`$STAGING_NEXT_DIR"
  NEXT_DIST_DIR="`$STAGING_NEXT_DIR" npm run build:public
  POST_BUILD_SOURCE_STATUS="`$(git -C "`$FRONTEND_DIR/.." status --porcelain --untracked-files=all)"
  if [ -n "`$POST_BUILD_SOURCE_STATUS" ]; then
    echo 'ERROR: public build mutated tracked or untracked source files. Refusing to swap.' >&2
    printf '%s\n' "`$POST_BUILD_SOURCE_STATUS" >&2
    rm -rf "`$STAGING_NEXT_DIR"
    exit 49
  fi
  if [ ! -s "`$STAGING_NEXT_DIR/BUILD_ID" ]; then
    echo "ERROR: staged `$STAGING_NEXT_DIR/BUILD_ID is missing. Refusing to swap incomplete production artifact." >&2
    rm -rf "`$STAGING_NEXT_DIR"
    exit 42
  fi

  echo "== atomically swapping staged artifact into `$PUBLIC_NEXT_DIR =="
  rm -rf "`$PREVIOUS_NEXT_DIR"
  if [ -d "`$PUBLIC_NEXT_DIR" ]; then
    mv "`$PUBLIC_NEXT_DIR" "`$PREVIOUS_NEXT_DIR"
  fi
  if mv "`$STAGING_NEXT_DIR" "`$PUBLIC_NEXT_DIR"; then
    rm -rf "`$PREVIOUS_NEXT_DIR"
  else
    echo "ERROR: staged artifact swap failed; restoring previous public artifact." >&2
    if [ -e "`$PUBLIC_NEXT_DIR" ]; then
      mv "`$PUBLIC_NEXT_DIR" "`$FAILED_NEXT_DIR" || true
    fi
    if [ -d "`$PREVIOUS_NEXT_DIR" ]; then
      mv "`$PREVIOUS_NEXT_DIR" "`$PUBLIC_NEXT_DIR"
    fi
    rm -rf "`$FAILED_NEXT_DIR"
    exit 45
  fi
else
  echo "== skipping build; validating existing `$PUBLIC_NEXT_DIR =="
fi

if [ ! -s "`$PUBLIC_NEXT_DIR/BUILD_ID" ]; then
  echo "ERROR: `$PUBLIC_NEXT_DIR/BUILD_ID is missing. Refusing to start incomplete production artifact." >&2
  exit 42
fi
if [ ! -s "`$PUBLIC_NEXT_DIR/LYRA_PUBLIC_BUILD_ID" ]; then
  echo "ERROR: `$PUBLIC_NEXT_DIR/LYRA_PUBLIC_BUILD_ID is missing. Refusing to start unverifiable production artifact." >&2
  exit 46
fi

echo "build_id=`$(cat "`$PUBLIC_NEXT_DIR/BUILD_ID")"
EXPECTED_PUBLIC_BUILD_ID="`$(cat "`$PUBLIC_NEXT_DIR/LYRA_PUBLIC_BUILD_ID")"
echo "public_build_id=`$EXPECTED_PUBLIC_BUILD_ID"

cat > "`$START_SCRIPT" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
source ~/.nvm/nvm.sh
cd "__FRONTEND_DIR__"
export NEXT_TELEMETRY_DISABLED=1
exec npm run start:public > /tmp/frontend.log 2>&1
EOS

python3 - <<PY
from pathlib import Path
path = Path("`$START_SCRIPT")
text = path.read_text()
text = text.replace("__FRONTEND_DIR__", "$safeWslRepoRoot/frontend")
path.write_text(text)
PY

chmod +x "`$START_SCRIPT"
: > "`$FRONTEND_LOG"

echo '== starting next start in tmux =='
tmux new-session -d -s "`$SESSION" "`$START_SCRIPT"

echo '== waiting for local frontend readiness =='
ready=0
for second in `$(seq 1 45); do
  if curl -fsS -o /dev/null --max-time 2 http://localhost:3000/; then
    echo "frontend ready after `${second}s"
    ready=1
    break
  fi
  sleep 1
done

if [ "`$ready" != '1' ]; then
  echo 'ERROR: frontend did not become ready within 45s.' >&2
  tail -80 "`$FRONTEND_LOG" >&2 || true
  exit 44
fi

echo '== frontend log tail =='
tail -30 "`$FRONTEND_LOG"

echo '== local health =='
tmux has-session -t "`$SESSION"
pgrep -af 'next-server' >/dev/null
curl -s -o /dev/null -w 'wsl_localhost:%{http_code},time=%{time_total}\n' --max-time 10 http://localhost:3000/

if [ "`$SKIP_PUBLIC_CHECK" != '1' ]; then
  echo '== public health =='
  curl -s -o /dev/null -w 'lyraos_org:%{http_code},time=%{time_total}\n' --max-time 20 https://lyraos.org/
  echo '== public topology =='
  EXPECTED_PUBLIC_BUILD_ID="`$EXPECTED_PUBLIC_BUILD_ID" python3 - <<'PY'
import json
import os
import sys
import urllib.request

request = urllib.request.Request(
    "https://lyraos.org/api/topology",
    headers={"User-Agent": "LyraTopologyVerifier/1.0"},
)
with urllib.request.urlopen(request, timeout=20) as response:
    topology = json.load(response)

print(json.dumps(topology, indent=2))
expected = {
    "topology_class": "public",
    "compiled_api_origin": "https://api.lyraos.org",
    "nextauth_url": "https://lyraos.org",
    "verified_topology": True,
}
for key, value in expected.items():
    if topology.get(key) != value:
        print(f"ERROR: public topology mismatch for {key}: {topology.get(key)!r}", file=sys.stderr)
        sys.exit(43)

expected_build_id = os.environ["EXPECTED_PUBLIC_BUILD_ID"]
if topology.get("build_id") != expected_build_id:
    print(
        "ERROR: public topology build_id mismatch: "
        f"{topology.get('build_id')!r} != {expected_build_id!r}",
        file=sys.stderr,
    )
    sys.exit(47)
PY
fi
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bashScript))
& wsl.exe -e bash -lc "echo $encoded | base64 -d | bash"
if ($LASTEXITCODE -ne 0) {
    throw "WSL frontend restart failed with exit code $LASTEXITCODE."
}
