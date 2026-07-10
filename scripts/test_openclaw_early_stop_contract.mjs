import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const defaultSkillPath = path.join(repoRoot, "openclaw", "skills", "lyra-secretary", "SKILL.md");
const skillPath = process.argv[2] || defaultSkillPath;

function fail(message) {
  console.error(`openclaw early-stop contract failed: ${message}`);
  process.exit(1);
}

function assertIncludes(haystack, needle, message) {
  if (!haystack.includes(needle)) fail(message);
}

if (process.argv.includes("--self-test-negative")) {
  const original = fs.readFileSync(defaultSkillPath, "utf8");
  const broken = original
    .replace(
      "NEVER call `?confirmed=true` as first call.",
      "Call `?confirmed=true` when the user wants to stop."
    )
    .replace(
      "POST /v1/stopwatch/stop → if `requires_confirmation: true`",
      "POST /v1/stopwatch/stop?confirmed=true → if `requires_confirmation: true`"
    );
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-early-stop-contract-"));
  const tmpPath = path.join(tmpDir, "SKILL.md");
  fs.writeFileSync(tmpPath, broken);
  const result = spawnSync(process.execPath, [import.meta.filename, tmpPath], {
    cwd: repoRoot,
    encoding: "utf8",
  });
  fs.rmSync(tmpDir, { recursive: true, force: true });
  if (result.status === 0) {
    fail("negative fixture unexpectedly passed");
  }
  console.log("openclaw early-stop contract negative fixture failed as expected");
  process.exit(0);
}

const skill = fs.readFileSync(skillPath, "utf8");

assertIncludes(
  skill,
  "This skill is retained as compatibility/reference material",
  "skill must remain historical/compatibility material, not live mutation authority"
);
assertIncludes(
  skill,
  "**EARLY STOP GATE**",
  "hard rule must name the early-stop gate"
);
assertIncludes(
  skill,
  "POST /v1/stopwatch/stop (no params)",
  "hard rule must require the first stop call without confirmation params"
);
assertIncludes(
  skill,
  "requires_confirmation: true",
  "hard rule/workflow must branch on requires_confirmation"
);
assertIncludes(
  skill,
  "STOP → wait for \"yes\"/\"no\"",
  "hard rule must stop for explicit user yes/no before confirmed stop"
);
assertIncludes(
  skill,
  "NEVER call `?confirmed=true` as first call.",
  "hard rule must forbid first-call confirmed stop"
);
assertIncludes(
  skill,
  "POST /v1/stopwatch/stop → if `requires_confirmation: true`",
  "workflow must start with unconfirmed stop"
);
assertIncludes(
  skill,
  "POST /v1/stopwatch/stop?confirmed=true with `post_task_reflection`",
  "workflow may call confirmed stop only after yes plus reflection"
);

console.log("openclaw early-stop contract passed");
