#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const contract = JSON.parse(
  fs.readFileSync(path.join(repoRoot, "runtime_topology.json"), "utf8")
);
const read = (relativePath) => fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
const multiAccountWrapper = read("scripts/run_multi_account_browser_smoke.ps1");
const operatorWrapper = read("scripts/run_operator_readonly_browser_stress.ps1");
const calendarTableWrapper = read("scripts/run_calendar_table_mutation_dogfood.ps1");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const local = contract.topologies.local;
const pub = contract.topologies.public;

assert(contract.version === "runtime_topology_v1", "contract version mismatch");
assert(local.frontend_origin === "http://localhost:3000", "local frontend origin changed");
assert(local.api_origin === "http://localhost:8000", "local API origin changed");
assert(local.nextauth_url === "http://localhost:3000", "local NextAuth origin changed");
assert(!local.api_origin.includes("api.lyraos.org"), "local API points at public");
assert(!local.frontend_origin.includes("lyraos.org"), "local frontend points at public");

assert(pub.frontend_origin === "https://lyraos.org", "public frontend origin changed");
assert(pub.api_origin === "https://api.lyraos.org", "public API origin changed");
assert(pub.nextauth_url === "https://lyraos.org", "public NextAuth origin changed");
assert(!pub.frontend_origin.includes("localhost"), "public frontend points at localhost");
assert(!pub.api_origin.includes("localhost"), "public API points at localhost");
assert(!pub.nextauth_url.includes("localhost"), "public NextAuth points at localhost");

for (const origin of contract.declared_browser_origins) {
  assert(
    [local.frontend_origin, "http://127.0.0.1:3000", pub.frontend_origin].includes(origin),
    `unexpected declared browser origin: ${origin}`
  );
}

for (const [name, wrapper] of [
  ["multi-account", multiAccountWrapper],
  ["operator read-only", operatorWrapper],
  ["Calendar/Table mutation", calendarTableWrapper],
]) {
  assert(
    wrapper.includes("[int]$LocalCurrentApiPort = 8000"),
    `${name} wrapper must expose an explicit local-current API port`,
  );
  assert(
    wrapper.includes('$env:LYRA_API_ORIGIN = "http://localhost:$LocalCurrentApiPort"'),
    `${name} wrapper must route local-current proof to the selected API port`,
  );
  assert(
    wrapper.includes('"--api", $env:LYRA_API_ORIGIN'),
    `${name} wrapper must pass the selected API origin into topology verification`,
  );
}

assert(
  calendarTableWrapper.includes("[switch]$FixtureAccountReady")
    && calendarTableWrapper.includes('$args += "--fixture-account-ready"'),
  "Calendar/Table wrapper must carry explicit local account-readiness fixture state into browser proof",
);
assert(
  calendarTableWrapper.includes("[switch]$CalendarOnly")
    && calendarTableWrapper.includes('$args += @("--calendar-only")'),
  "Calendar/Table wrapper must expose a focused Calendar-only debugging tier",
);
assert(
  calendarTableWrapper.includes('if ($Topology -ne "local-current")'),
  "Calendar/Table account-readiness fixture must remain local-current only",
);

console.log(JSON.stringify({ ok: true, checked: "runtime_topology_contract" }));
