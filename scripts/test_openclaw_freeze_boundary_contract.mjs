import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const defaultSkillPath = path.join(repoRoot, "openclaw", "skills", "lyra-secretary", "SKILL.md");
const skillPath = process.argv[2] || defaultSkillPath;

function fail(message) {
  console.error(`openclaw freeze-boundary contract failed: ${message}`);
  process.exit(1);
}

function assertIncludes(haystack, needle, message) {
  if (!haystack.includes(needle)) fail(message);
}

function assertNotIncludes(haystack, needle, message) {
  if (haystack.includes(needle)) fail(message);
}

if (process.argv.includes("--self-test-negative")) {
  const original = fs.readFileSync(defaultSkillPath, "utf8");
  const broken = original
    .replace(
      "This skill is retained as compatibility/reference material",
      "This skill is retained as live mutation material",
    )
    .replace(
      "It does not authorize live task creation",
      "It authorizes live task creation",
    )
    .replace(
      "do not perform scheduling, timer,",
      "perform scheduling, timer,",
    );
  if (broken === original) {
    fail("negative fixture did not alter the skill contract");
  }
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-freeze-boundary-"));
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
  console.log("openclaw freeze-boundary contract negative fixture failed as expected");
  process.exit(0);
}

const skill = fs.readFileSync(skillPath, "utf8");

assertIncludes(
  skill,
  "## Freeze Boundary",
  "skill must keep an explicit freeze boundary",
);
assertIncludes(
  skill,
  "This skill is retained as compatibility/reference material",
  "skill must remain historical/compatibility material, not live mutation authority",
);
assertIncludes(
  skill,
  "It does not authorize live task creation",
  "skill must not authorize live task creation",
);
assertIncludes(
  skill,
  "rescheduling, deletion, timer start/stop/pause/resume",
  "skill must list timer and task mutations as not authorized",
);
assertIncludes(
  skill,
  "Direct Docker-network access to `http://backend:8000` describes reachability",
  "direct backend reachability must be framed as reachability only",
);
assertIncludes(
  skill,
  "not identity, scope, audit, or mutation authority",
  "direct backend reachability must not imply authority",
);
assertIncludes(
  skill,
  "must use a current authenticated/audited canonical command path",
  "future command paths must require current authenticated/audited authority",
);
assertIncludes(
  skill,
  "must be reauthorized before this skill can be used for live mutations",
  "future live mutation use must require reauthorization",
);
assertIncludes(
  skill,
  "The endpoint and workflow sections below are historical compatibility notes.",
  "legacy endpoint/workflow sections must be historical notes",
);
assertIncludes(
  skill,
  "they must not override the freeze",
  "legacy endpoint/workflow sections must not override the freeze boundary",
);
assertIncludes(
  skill,
  "do not perform scheduling, timer,",
  "historical runtime guard must forbid scheduling/timer mutations during freeze",
);
assertIncludes(
  skill,
  "or task mutations through this skill",
  "historical runtime guard must forbid task mutations during freeze",
);
assertNotIncludes(
  skill,
  "This skill is retained as live mutation material",
  "skill must not present itself as live mutation material",
);
assertNotIncludes(
  skill,
  "It authorizes live task creation",
  "skill must not authorize live task creation",
);

console.log("openclaw freeze-boundary contract passed");
