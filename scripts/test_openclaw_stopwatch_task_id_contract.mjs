import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const defaultSkillPath = path.join(repoRoot, "openclaw", "skills", "lyra-secretary", "SKILL.md");
const skillPath = process.argv[2] || defaultSkillPath;

function fail(message) {
  console.error(`openclaw stopwatch task-id contract failed: ${message}`);
  process.exit(1);
}

function assertIncludes(haystack, needle, message) {
  if (!haystack.includes(needle)) fail(message);
}

function assertNotMatches(haystack, pattern, message) {
  if (pattern.test(haystack)) fail(message);
}

if (process.argv.includes("--self-test-negative")) {
  const original = fs.readFileSync(defaultSkillPath, "utf8");
  const broken = original
    .replace(
      "POST /v1/stopwatch/start with `task_id` + `pre_task_readiness`",
      "POST /v1/stopwatch/start with `pre_task_readiness`"
    )
    .replace(
      "POST /v1/stopwatch/start with `task_id` + `pre_task_readiness` + `interruption_type`",
      "POST /v1/stopwatch/start with `pre_task_readiness` + `interruption_type`"
    );
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-stopwatch-contract-"));
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
  console.log("openclaw stopwatch task-id contract negative fixture failed as expected");
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
  "STOPWATCH USES TASK_ID ONLY",
  "hard rule must say stopwatch uses task_id only"
);
assertIncludes(
  skill,
  "never title",
  "hard rule/endpoint table must forbid title-based stopwatch start"
);
assertIncludes(
  skill,
  "**POST /v1/stopwatch/start**",
  "endpoint table must document stopwatch start"
);
assertIncludes(
  skill,
  "body: `task_id`* (never title)",
  "endpoint table must require task_id and explicitly reject title as the agent start handle"
);
assertIncludes(
  skill,
  "GET /v1/tasks/query",
  "workflow must query tasks before timer start"
);
assertIncludes(
  skill,
  "GET /v1/tasks/{id}",
  "hard rule must verify target task detail before timer start"
);
assertIncludes(
  skill,
  "POST /v1/stopwatch/start with `task_id` + `pre_task_readiness`",
  "normal start workflow must include task_id in the start call"
);
assertIncludes(
  skill,
  "POST /v1/stopwatch/start with `task_id` + `pre_task_readiness` + `interruption_type`",
  "interruption start workflow must include task_id in the start call"
);
assertNotMatches(
  skill,
  /POST \/v1\/stopwatch\/start with `pre_task_readiness`/i,
  "workflow must not describe a title/memory-free start call that omits task_id"
);

console.log("openclaw stopwatch task-id contract passed");
