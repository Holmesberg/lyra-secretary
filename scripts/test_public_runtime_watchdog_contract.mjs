#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const watchdog = fs.readFileSync(
  path.join(repoRoot, "scripts", "watch_public_runtime.ps1"),
  "utf8"
);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function section(startMarker, endMarker) {
  const start = watchdog.indexOf(startMarker);
  const end = watchdog.indexOf(endMarker, start + startMarker.length);
  assert(start >= 0, `missing watchdog section: ${startMarker}`);
  assert(end > start, `missing watchdog section terminator: ${endMarker}`);
  return watchdog.slice(start, end);
}

assert(
  /\[switch\]\$ReadOnly/.test(watchdog),
  "watch_public_runtime.ps1 must expose an explicit -ReadOnly mode"
);

assert(
  /\[switch\]\$SkipRelay/.test(watchdog),
  "watch_public_runtime.ps1 must expose -SkipRelay for proof-only checks"
);

assert(
  /\$ReadOnly[\s\S]*?\$NoRepair\s*=\s*\$true[\s\S]*?\$SkipRelay\s*=\s*\$true/.test(watchdog),
  "-ReadOnly must imply both -NoRepair and -SkipRelay"
);

assert(
  watchdog.includes("Ensure-OpenClawOperatorRelay"),
  "watch_public_runtime.ps1 must route relay starts through an explicit guard"
);

assert(
  /Relay start skipped by -ReadOnly\/-SkipRelay/.test(watchdog),
  "watch_public_runtime.ps1 must make skipped relay starts explicit in logs"
);

const directRuntimeStartCalls = [...watchdog.matchAll(/Start-OpenClawOperatorRelay\s+\$repoRoot/g)];
assert(
  directRuntimeStartCalls.length === 0,
  "runtime paths must not call Start-OpenClawOperatorRelay directly; use the guarded helper"
);

assert(
  watchdog.includes("Invoke-PublicFrontendRepair") &&
    watchdog.includes("Invoke-PublicBackendRepair") &&
    watchdog.includes("Invoke-PublicTunnelRepair") &&
    watchdog.includes("Invoke-FullPublicStackRepair"),
  "watchdog must expose separate repair paths for each runtime layer"
);

assert(
  /\$reuseExistingArtifacts\s*=\s*-not\s+\$AllowFullBuild/.test(watchdog),
  "watchdog must reuse deployed artifacts unless a full build is explicitly allowed"
);

const tunnelOnly = section(
  "} elseif ($localOk) {",
  "} elseif (-not $localFrontend.Ok -and $localApi.Ok) {"
);
assert(
  tunnelOnly.includes("Invoke-PublicTunnelRepair") &&
    !tunnelOnly.includes("Invoke-PublicFrontendRepair") &&
    !tunnelOnly.includes("Invoke-PublicBackendRepair") &&
    !tunnelOnly.includes("Invoke-FullPublicStackRepair"),
  "healthy local services with failed public health must restart only the tunnel"
);

const frontendOnly = section(
  "} elseif (-not $localFrontend.Ok -and $localApi.Ok) {",
  "} elseif ($localFrontend.Ok -and -not $localApi.Ok) {"
);
assert(
  frontendOnly.includes("Invoke-PublicFrontendRepair") &&
    !frontendOnly.includes("Invoke-PublicBackendRepair") &&
    !frontendOnly.includes("Invoke-FullPublicStackRepair"),
  "frontend-only failure must not restart the backend or full stack"
);

const backendOnly = section(
  "} elseif ($localFrontend.Ok -and -not $localApi.Ok) {",
  "} else {"
);
assert(
  backendOnly.includes("Invoke-PublicBackendRepair") &&
    !backendOnly.includes("Invoke-PublicFrontendRepair") &&
    !backendOnly.includes("Invoke-FullPublicStackRepair"),
  "backend-only failure must not restart the frontend or full stack"
);

assert(
  /Repairing full local stack and Cloudflare tunnel[\s\S]*?Invoke-FullPublicStackRepair/.test(
    watchdog
  ),
  "both local services being down must use the full-stack reboot path"
);

assert(
  /Invoke-FullPublicStackRepair[\s\S]*?"-SkipPublicCheck"[\s\S]*?"-SkipRelay"/.test(
    watchdog
  ),
  "full-stack repair must defer final public proof and relay startup to the watchdog"
);

assert(
  /Rerun with -AllowFullBuild only if the existing artifact is invalid/.test(
    watchdog
  ),
  "failed no-build asset repair must explain the explicit full-build escalation"
);

console.log(JSON.stringify({ ok: true, checked: "public_runtime_watchdog_contract" }));
