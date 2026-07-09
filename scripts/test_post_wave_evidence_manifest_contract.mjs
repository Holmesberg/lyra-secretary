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

const wrapper = read("scripts/run_post_wave_dogfood_loop.ps1");
const ciProof = read("scripts/collect_github_ci_cd_proof.ps1");
const runbook = read("docs/runbooks/post_wave_dogfood_loop.md");

const requiredManifestFields = [
  "topology_class",
  "frontend_build_id",
  "backend_build_id",
  "frontend_origin",
  "api_origin",
  "browser_issues",
  "browser_warnings",
  "count_diffs",
  "count_diff_count",
  "cleanup",
  "readiness",
  "implementation_green",
  "implementation_status",
  "cohort_green",
  "cohort_status",
  "safe_to_invite_more_users",
  "controlled_evidence_collection_allowed",
  "exposure_without_render_count",
  "gated_paths",
  "ci_cd_proof",
  "selected_run_id",
  "selected_run_url",
];

for (const field of requiredManifestFields) {
  assert(
    wrapper.includes(field),
    `post-wave wrapper evidence manifest is missing ${field}`
  );
}

const requiredClassifications = [
  "standard_wave_proof_passed",
  "product_or_verifier_failure",
  "measurement_cleanup_failure",
];

for (const classification of requiredClassifications) {
  assert(
    wrapper.includes(classification),
    `post-wave wrapper is missing classification ${classification}`
  );
}

const runbookRequiredPhrases = [
  "summary.json.evidence_manifest",
  "topology class",
  "frontend/backend build IDs",
  "implementation/cohort readiness split",
  "`exposure_without_render_count`",
  "CI/CD proof",
];

for (const phrase of runbookRequiredPhrases) {
  assert(
    runbook.includes(phrase),
    `post-wave runbook is missing evidence manifest phrase: ${phrase}`
  );
}

assert(
  ciProof.includes("[System.IO.Path]::IsPathRooted($OutFile)"),
  "CI/CD proof collector must handle rooted OutFile paths explicitly"
);

console.log(JSON.stringify({ ok: true, checked: "post_wave_evidence_manifest_contract" }));
