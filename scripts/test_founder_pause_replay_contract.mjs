#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  assertAggregateOnly,
  assertNoPrivateValues,
} from "./pause_replay_artifact_contract.mjs";

assert.doesNotThrow(() => assertAggregateOnly({ status: "inconclusive", definitions_hash: "abc" }));
assert.throws(() => assertAggregateOnly({ task_id: "private" }), /forbidden row identifier/);
assert.throws(() => assertAggregateOnly({ nested: { email: "private@example.com" } }), /forbidden private field/);
assert.doesNotThrow(() => assertNoPrivateValues(
  { status: "complete" },
  { tasks: [{ task_id: "task-private-123", title: "Private founder task" }] },
));
assert.throws(() => assertNoPrivateValues(
  { accidental: "Private founder task" },
  { tasks: [{ task_id: "task-private-123", title: "Private founder task" }] },
), /repeats a private export value/);

const temp = mkdtempSync(path.join(os.tmpdir(), "lyra-pause-replay-"));
try {
  const output = path.join(temp, "result.json");
  writeFileSync(output, "do-not-overwrite\n");
  const completed = spawnSync(
    process.execPath,
    [
      path.resolve("scripts/browser_founder_pause_replay.mjs"),
      "--python", process.execPath,
      "--out-file", output,
      "--method-commit", "a".repeat(40),
    ],
    {
      cwd: path.resolve("."),
      env: { ...process.env, LYRA_COOKIE_ALINASSERSABRY: "x".repeat(301) },
      encoding: "utf8",
    },
  );
  assert.notEqual(completed.status, 0, "existing result artifact must fail closed");
  assert.equal(readFileSync(output, "utf8"), "do-not-overwrite\n");
} finally {
  rmSync(temp, { recursive: true, force: true });
}

const wrapper = readFileSync("scripts/run_founder_pause_replay.ps1", "utf8");
assert.match(wrapper, /git status --porcelain=v1 -- @methodFiles/);
assert.match(wrapper, /proof_preflight\.ps1/);
assert.match(wrapper, /-Account operator/);
assert.match(wrapper, /-Intent readonly/);

console.log(JSON.stringify({ ok: true, checked: "founder_pause_replay_contract" }));
