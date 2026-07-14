#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const read = (relativePath) => fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
const browser = read("scripts/browser_holmesberg_product_loop_dogfood.mjs");
const wrapper = read("scripts/run_holmesberg_product_loop_dogfood.ps1");

for (const blocker of [
  "terms_not_accepted",
  "archetype_survey_pending",
  "onboarding_not_completed",
  "no_active_task_history",
]) {
  assert(
    browser.includes(`"${blocker}"`),
    `full-loop account preflight must classify ${blocker}`,
  );
}
assert(
  browser.includes('"Holmesberg account preflight admits the full product loop"')
    && browser.includes("if (!fixtureAccountReady)"),
  "full product loop must fail before route traversal when the real account is ineligible",
);
assert(
  wrapper.includes("[switch]$FixtureAccountReady")
    && wrapper.includes('$args += "--fixture-account-ready"'),
  "wrapper must expose the existing browser-response-only account readiness fixture",
);

console.log("product loop account preflight contract: ok");
