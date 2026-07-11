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
const s1cStack = read("scripts/run_s1c_verification_stack.ps1");
const ciProof = read("scripts/collect_github_ci_cd_proof.ps1");
const ciWorkflow = read(".github/workflows/ci.yml");
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

for (const [name, source] of [
  ["post-wave wrapper", wrapper],
  ["S1c stack", s1cStack],
]) {
  const resetIndex = source.indexOf("$global:LASTEXITCODE = 0");
  const bodyIndex = source.indexOf("& $Body", resetIndex);
  assert(
    resetIndex >= 0 && bodyIndex > resetIndex,
    `${name} must reset stale native LASTEXITCODE before each step body`
  );
  assert(
    source.includes("$stepExitCode = $global:LASTEXITCODE"),
    `${name} must retain native exit code for failure diagnostics`
  );
  assert(
    source.includes("$stepSucceeded = $?") &&
      source.includes("if (-not $stepSucceeded)"),
    `${name} must classify the scriptblock result instead of handled probe exits`
  );
}

const localGateSource = s1cStack.replaceAll("\\", "/");
const ciGateSource = ciWorkflow.replaceAll("\\", "/");
for (const gate of [
  "scripts/scan_backend_layer_imports.py",
  "scripts/scan_cortex_readonly.py",
  "scripts/scan_feature_preservation_registry.py",
]) {
  for (const [name, source] of [
    ["local S1c", localGateSource],
    ["CI", ciGateSource],
  ]) {
    assert(source.includes(`${gate} --self-test`), `${name} is missing ${gate} self-test`);
    assert(
      source.includes(`${gate} --fail-on-errors`),
      `${name} is missing ${gate} hard-fail execution`
    );
  }
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
