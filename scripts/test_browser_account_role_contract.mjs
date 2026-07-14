#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const insightsDogfood = read("scripts/browser_insights_states_dogfood.mjs");
const operatorReadonly = read("scripts/browser_stress_operator_readonly.mjs");
const multiAccountSmoke = read("scripts/browser_smoke_two_users.mjs");
const runbook = read("docs/runbooks/post_wave_dogfood_loop.md");
const authority = read("docs/AUTHORITY.md");

assert(
  !insightsDogfood.includes("LYRA_COOKIE_ALINASSERSABRY"),
  "Insights forced-state dogfood must not fall back to the operator cookie"
);
assert(
  insightsDogfood.includes("LYRA_COOKIE_HOLMESBERG"),
  "Insights forced-state dogfood must use the Holmesberg dogfood cookie"
);
assert(
  operatorReadonly.includes("LYRA_COOKIE_ALINASSERSABRY"),
  "Operator read-only stress must use the operator cookie"
);
assert(
  !operatorReadonly.includes("LYRA_COOKIE_HOLMESBERG"),
  "Operator read-only stress must not use the mutable dogfood cookie"
);
assert(
  /if \(!me\.is_operator\) \{[\s\S]*academic\/pressure-map[\s\S]*suppressApiOnlyPressureProbe/.test(multiAccountSmoke),
  "Multi-account smoke must keep Pressure Map writes off the operator account and suppress non-rendered probes"
);
assert(
  runbook.includes("Never use the operator account for mutable dogfood"),
  "Post-wave runbook must state the operator read-only account rule"
);
assert(
  authority.includes("must remain read-only"),
  "Authority map must state the operator account remains read-only"
);

console.log(JSON.stringify({ ok: true, checked: "browser_account_role_contract" }));
