import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const defaultSkillPath = path.join(repoRoot, "openclaw", "skills", "lyra-secretary", "SKILL.md");
const skillPath = process.argv[2] || defaultSkillPath;

function fail(message) {
  console.error(`openclaw delete-confirmation contract failed: ${message}`);
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
      "NEVER bulk delete without confirmation",
      "Bulk delete conflicts automatically",
    )
    .replace(
      "NEVER DELETE EXECUTED TASKS",
      "DELETE EXECUTED TASKS when asked",
    )
    .replace(
      "NEVER pick a reason yourself, NEVER default to system_error",
      "Pick system_error when unsure",
    );
  if (broken === original) {
    fail("negative fixture did not alter the skill contract");
  }
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-delete-contract-"));
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
  console.log("openclaw delete-confirmation contract negative fixture failed as expected");
  process.exit(0);
}

const skill = fs.readFileSync(skillPath, "utf8");

assertIncludes(
  skill,
  "This skill is retained as compatibility/reference material",
  "skill must remain historical/compatibility material, not live mutation authority",
);
assertIncludes(
  skill,
  "**NEVER bulk delete without confirmation.**",
  "hard rule must forbid bulk delete without confirmation",
);
assertIncludes(
  skill,
  "Call query",
  "delete workflow must query before acting",
);
assertIncludes(
  skill,
  "show list",
  "delete workflow must show the target list before acting",
);
assertIncludes(
  skill,
  "wait for explicit \"yes\"",
  "delete workflow must wait for explicit yes before deletion",
);
assertIncludes(
  skill,
  "**VERIFY BEFORE ACTING**",
  "hard rule must require backend verification before destructive action",
);
assertIncludes(
  skill,
  "Before timer start, delete, or reschedule",
  "verification rule must cover delete and reschedule",
);
assertIncludes(
  skill,
  "NEVER use a task_id from memory",
  "destructive task identity must not come from memory",
);
assertIncludes(
  skill,
  "**NEVER DELETE EXECUTED TASKS**",
  "hard rule must forbid deleting executed tasks",
);
assertIncludes(
  skill,
  "DELETE is for PLANNED tasks only",
  "delete endpoint must remain planned-only in the skill contract",
);
assertIncludes(
  skill,
  "EXECUTED = void",
  "executed task handling must be void, not delete",
);
assertIncludes(
  skill,
  "ALWAYS ASK REASON",
  "void workflow must ask for a reason",
);
assertIncludes(
  skill,
  "NEVER pick a reason yourself, NEVER default to system_error",
  "void workflow must not silently default the reason",
);
assertIncludes(
  skill,
  "NEVER delete EXECUTED tasks",
  "void workflow must restate the executed-task deletion ban",
);
assertNotIncludes(
  skill,
  "Bulk delete conflicts automatically",
  "skill must not allow automatic bulk delete",
);
assertNotIncludes(
  skill,
  "DELETE EXECUTED TASKS when asked",
  "skill must not allow deleting executed tasks",
);
assertNotIncludes(
  skill,
  "Pick system_error when unsure",
  "skill must not default void reason",
);

console.log("openclaw delete-confirmation contract passed");
