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

console.log(JSON.stringify({ ok: true, checked: "public_runtime_watchdog_contract" }));
