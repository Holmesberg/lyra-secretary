import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = process.cwd();
const defaultSkillPath = path.join(repoRoot, "openclaw", "skills", "lyra-secretary", "SKILL.md");
const skillPath = process.argv[2] || defaultSkillPath;

function fail(message) {
  console.error(`openclaw conflict-force contract failed: ${message}`);
  process.exit(1);
}

function assertIncludes(haystack, needle, message) {
  if (!haystack.includes(needle)) fail(message);
}

if (process.argv.includes("--self-test-negative")) {
  const original = fs.readFileSync(defaultSkillPath, "utf8");
  const broken = original
    .replace(
      'show conflicts and ask "Force anyway?", WAIT for an explicit "yes", and only then call with `force: true`',
      'retry automatically with `force: true`'
    )
    .replace(
      'If conflicts → show list → ask "Force anyway?" → WAIT for explicit "yes" → only then retry with `force: true`',
      "If conflicts → retry with force"
    );
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "openclaw-conflict-force-contract-"));
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
  console.log("openclaw conflict-force contract negative fixture failed as expected");
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
  "**NEVER auto-force a conflict.**",
  "hard rule must name conflict force consent"
);
assertIncludes(
  skill,
  'When `/v1/create` returns `created: false`',
  "hard rule must be bound to the create conflict response"
);
assertIncludes(
  skill,
  'show conflicts and ask "Force anyway?", WAIT for an explicit "yes", and only then call with `force: true`',
  "hard rule must require explicit yes before force=true"
);
assertIncludes(
  skill,
  "**POST /v1/create**",
  "endpoint reference must keep create as the scheduling command"
);
assertIncludes(
  skill,
  "returns: `task_id`, `created`, `conflicts[]`",
  "endpoint reference must preserve conflicts as response evidence"
);
assertIncludes(
  skill,
  'If conflicts → show list → ask "Force anyway?" → WAIT for explicit "yes" → only then retry with `force: true`',
  "schedule workflow must not retry force=true before explicit consent"
);

console.log("openclaw conflict-force contract passed");
