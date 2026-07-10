import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const defaultSkillPath = path.join(repoRoot, "openclaw", "skills", "lyra-secretary", "SKILL.md");
const doNotAddPath = path.join(repoRoot, "docs", "do_not_add.md");
const skillPath = process.argv[2] || defaultSkillPath;

function fail(message) {
  console.error(`openclaw measurement-field contract failed: ${message}`);
  process.exit(1);
}

function assertIncludes(haystack, needle, message) {
  if (!haystack.includes(needle)) fail(message);
}

if (process.argv.includes("--self-test-negative")) {
  const original = fs.readFileSync(defaultSkillPath, "utf8");
  const broken = original
    .replace(
      "NEVER ASSUME USER INPUT — never default readiness or reflection to any value",
      "Use readiness 5 when the user sounds confident."
    )
    .replace(
      "Send \"Rate your readiness (1=exhausted, 3=neutral, 5=sharp):\" — WAIT for number",
      "Use readiness 5 when starting quickly"
    );
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-measurement-contract-"));
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
  console.log("openclaw measurement-field contract negative fixture failed as expected");
  process.exit(0);
}

const skill = fs.readFileSync(skillPath, "utf8");
const doNotAdd = fs.readFileSync(doNotAddPath, "utf8");

assertIncludes(
  skill,
  "This skill is retained as compatibility/reference material",
  "skill must remain historical/compatibility material, not live mutation authority"
);
assertIncludes(
  skill,
  "ALWAYS ASK READINESS BEFORE START",
  "hard rule must require readiness capture before timer start"
);
assertIncludes(
  skill,
  "ALWAYS ASK REFLECTION AFTER STOP",
  "hard rule must require reflection capture after stop"
);
assertIncludes(
  skill,
  "NEVER ASSUME USER INPUT",
  "hard rule must forbid inferred measurement fields"
);
assertIncludes(
  skill,
  "never default readiness or reflection to any value",
  "hard rule must forbid readiness/reflection defaults"
);
assertIncludes(
  skill,
  "ask readiness first",
  "intent router must remind the agent to ask readiness before start"
);
assertIncludes(
  skill,
  "ask reflection after",
  "intent router must remind the agent to ask reflection after stop"
);
assertIncludes(
  skill,
  "Send \"Rate your readiness (1=exhausted, 3=neutral, 5=sharp):\" — WAIT for number",
  "start workflow must wait for an explicit readiness answer"
);
assertIncludes(
  skill,
  "POST /v1/stopwatch/start with `task_id` + `pre_task_readiness`",
  "start workflow must pass the explicit readiness value"
);
assertIncludes(
  skill,
  "send \"Rate focus (1=very poor, 3=average, 5=excellent):\" — WAIT for number",
  "confirmed early-stop workflow must wait for explicit reflection"
);
assertIncludes(
  skill,
  "If no confirmation required: send focus question — WAIT → POST /v1/stopwatch/stop with `post_task_reflection`",
  "normal stop workflow must wait for explicit reflection"
);
assertIncludes(
  skill,
  "NEVER infer or fabricate a completion percentage yourself",
  "completion percentage must not be inferred"
);
assertIncludes(
  doNotAdd,
  "Hardcoded default values for any research-relevant field",
  "active doctrine must preserve the no-default measurement field rule"
);
assertIncludes(
  doNotAdd,
  "Every research-relevant field must be explicitly provided or explicitly null",
  "active doctrine must require explicit or null measurement fields"
);

console.log("openclaw measurement-field contract passed");
