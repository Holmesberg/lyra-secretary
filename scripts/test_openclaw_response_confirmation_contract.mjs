import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const defaultSkillPath = path.join(repoRoot, "openclaw", "skills", "lyra-secretary", "SKILL.md");
const skillPath = process.argv[2] || defaultSkillPath;

function fail(message) {
  console.error(`openclaw response-confirmation contract failed: ${message}`);
  process.exit(1);
}

function assertIncludes(haystack, needle, message) {
  if (!haystack.includes(needle)) fail(message);
}

function assertNotIncludes(haystack, needle, message) {
  if (haystack.includes(needle)) fail(message);
}

function sectionBetween(haystack, start, end) {
  const startIndex = haystack.indexOf(start);
  if (startIndex === -1) fail(`missing section start: ${start}`);
  const endIndex = haystack.indexOf(end, startIndex + start.length);
  if (endIndex === -1) fail(`missing section end after ${start}: ${end}`);
  return haystack.slice(startIndex, endIndex);
}

if (process.argv.includes("--self-test-negative")) {
  const original = fs.readFileSync(defaultSkillPath, "utf8");
  const broken = original
    .replace(
      "NEVER CONFIRM WITHOUT A BACKEND RESPONSE (task_id or session_id required)",
      "Confirm from plan text when the backend is slow",
    )
    .replace(
      "Any \"schedule\"/\"add task\"/\"remind me\" request MUST call POST /v1/create and receive `task_id` before confirming.",
      "Any schedule request may be confirmed after parsing the time.",
    )
    .replace(
      '"start timer"/"start stopwatch" â†’ POST /v1/stopwatch/start (ask readiness first)',
      '"start timer"/"start stopwatch" â†’ POST /v1/reschedule (ask readiness first)',
    );
  if (broken === original) {
    fail("negative fixture did not alter the skill contract");
  }
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-response-contract-"));
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
  console.log("openclaw response-confirmation contract negative fixture failed as expected");
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
  "NEVER CONFIRM WITHOUT A BACKEND RESPONSE (task_id or session_id required)",
  "hard rule must forbid success confirmation without backend evidence",
);
assertIncludes(
  skill,
  "**ALWAYS USE LYRA FOR SCHEDULING**",
  "hard rule must preserve canonical scheduling authority",
);
assertIncludes(
  skill,
  "Any \"schedule\"/\"add task\"/\"remind me\" request MUST call POST /v1/create and receive `task_id` before confirming.",
  "schedule confirmation must require POST /v1/create plus task_id",
);
assertIncludes(
  skill,
  "**POST /v1/create**",
  "endpoint reference must keep create as the scheduling command",
);
assertIncludes(
  skill,
  "returns: `task_id`, `created`, `conflicts[]`, `notion_synced`",
  "create endpoint must expose backend task_id evidence",
);
assertIncludes(
  skill,
  '"start timer"/"start stopwatch"',
  "intent router must map start timer requests",
);
assertIncludes(
  skill,
  "POST /v1/stopwatch/start (ask readiness first)",
  "intent router must map start timer to stopwatch/start",
);
assertIncludes(
  skill,
  "**POST /v1/stopwatch/start**",
  "endpoint table must document stopwatch start",
);
assertIncludes(
  skill,
  "returns: `session_id`, `task_id`, `is_future_task`",
  "start endpoint must return backend session/task evidence",
);

const startTimerSection = sectionBetween(
  skill,
  "**Start timer:**",
  "**Starting while another task is PAUSED",
);
const scheduleSection = sectionBetween(
  skill,
  "**Schedule request:**",
  "**Start timer:**",
);
assertIncludes(
  scheduleSection,
  "POST /v1/create",
  "schedule workflow must call create",
);
assertIncludes(
  scheduleSection,
  "get `task_id`",
  "schedule workflow must receive task_id before confirmation",
);
assertIncludes(
  scheduleSection,
  "confirm to user",
  "schedule workflow must only confirm after backend evidence",
);
assertIncludes(
  startTimerSection,
  "POST /v1/stopwatch/start with `task_id` + `pre_task_readiness`",
  "start workflow must call stopwatch/start with task_id",
);
assertNotIncludes(
  startTimerSection,
  "POST /v1/reschedule",
  "start workflow must not use reschedule as a stopwatch/start proxy",
);
assertNotIncludes(
  skill,
  "Confirm from plan text when the backend is slow",
  "skill must not permit confirmation from model text",
);
assertNotIncludes(
  skill,
  "Any schedule request may be confirmed after parsing the time.",
  "skill must not permit schedule confirmation without task_id",
);

console.log("openclaw response-confirmation contract passed");
