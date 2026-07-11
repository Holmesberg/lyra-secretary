#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assertIncludes(haystack, needle, label) {
  if (!haystack.includes(needle)) {
    throw new Error(`${label} must include: ${needle}`);
  }
}

function assertAllIncludes(haystack, needles, label) {
  for (const needle of needles) {
    assertIncludes(haystack, needle, label);
  }
}

const instructions = read(".github/instructions.md");
const authority = read("docs/AUTHORITY.md");

assertAllIncludes(
  instructions,
  [
    "reduce uncertainty before reducing",
    "Refactor without losing a single documented feature",
    "name the document or test that proves it exists",
    "runtime AI synthesis",
    "ReasoningRuntimeContract/OpenClawAdapter product wiring",
    "passive tracking",
    "provider adapters",
    "schema migrations",
    "brand/domain/runtime-host migration",
    "queue insertion is not exposure",
    "browser render creates render truth",
    "Pending disappearance is not render proof",
    "LYRA_COOKIE_ALINASSERSABRY",
    "LYRA_COOKIE_HOLMESBERG",
    "Stop and ask before",
    "public deploy, or public restart",
    "production data repair, purge",
    "weakening operator/readiness/exposure denominators",
    "deleting or disabling a documented or user-facing feature",
    "mixed seams exceeding 8 files",
    "more than 2 CI fix/retry cycles",
    "three consecutive cosmetic-only seams",
    "Adjacent fixes are allowed only when they block proof",
    "Before editing, declare",
    "Evidence beats screenshots",
    "Public Artifact Safety",
    "Local verification must not mutate hosted-public frontend artifacts",
  ],
  ".github/instructions.md"
);

assertAllIncludes(
  authority,
  [
    "Standing Freeze Doctrine",
    "Freeze remains active",
    "runtime AI synthesis",
    "ReasoningRuntimeContract/OpenClawAdapter product wiring",
    "passive tracking",
    "provider adapters",
    "schema migrations",
    "Queue insertion is not exposure",
    "Browser render creates render truth",
    "No seam may treat queued, delivered, or pending",
    "LYRA_COOKIE_ALINASSERSABRY",
    "must remain read-only",
    "LYRA_COOKIE_HOLMESBERG",
    "cleanup/void proof",
    "Browser verification must use real account cookies",
    "Cleanup is part of verification",
  ],
  "docs/AUTHORITY.md"
);

console.log(JSON.stringify({ ok: true, checked: "repository_instructions_contract" }));
