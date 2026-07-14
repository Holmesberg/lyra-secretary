#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const read = (relativePath) => fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
const browser = read("scripts/browser_stress_operator_readonly.mjs");
const wrapper = read("scripts/run_operator_readonly_browser_stress.ps1");

for (const blocker of [
  "terms_not_accepted",
  "archetype_survey_pending",
  "onboarding_not_completed",
  "no_active_task_history",
]) {
  assert(
    browser.includes(`"${blocker}"`),
    `operator browser preflight must classify ${blocker}`,
  );
}
assert(
  browser.includes("if (browserRouteEligible)")
    && browser.includes("operator browser account preflight blocked route proof"),
  "ineligible operator browser proof must fail before expensive route waits",
);
assert(
  wrapper.includes("[switch]$FixtureAccountReady")
    && wrapper.includes('@("--fixture-account-ready", "true")'),
  "operator wrapper must expose the browser-response-only readiness fixture",
);

console.log("operator account preflight contract: ok");
