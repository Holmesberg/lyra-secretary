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

const modal = read("frontend/components/new-task-modal.tsx");
const timeControls = read("frontend/lib/hooks/use-new-task-time-controls.ts");

assert(
  modal.includes("Fresh defaults every time modal opens for a new task."),
  "NewTaskModal must document the fresh-defaults-on-open contract"
);

assert(
  /useEffect\(\(\)\s*=>\s*{[\s\S]*?if\s*\(\s*open\s*&&\s*!editingTask\s*\)\s*{[\s\S]*?resetTimeDefaults\(\);[\s\S]*?setTitle\(""\);[\s\S]*?}\s*}\s*,\s*\[open,\s*editingTask\]\s*\)/.test(modal),
  "NewTaskModal must reset time defaults inside the open && !editingTask effect"
);

assert(
  !/useState\(\(\)\s*=>\s*defaultStart\(\)\)[\s\S]*\/\/\s*Fresh defaults every time modal opens/.test(modal),
  "NewTaskModal must not rely on mount-only defaultStart state for fresh open defaults"
);

assert(
  /const\s+nextDefaultStart\s*=\s*useCallback\(\(\)\s*=>\s*{[\s\S]*?defaultDate\s*\?\s*defaultStartForDate\(defaultDate,\s*now\)\s*:\s*defaultStart\(now\)[\s\S]*?}\s*,\s*\[defaultDate,\s*now\]\s*\)/.test(timeControls),
  "useNewTaskTimeControls must recompute default start from the current now/defaultDate"
);

assert(
  /const\s+resetTimeDefaults\s*=\s*useCallback\(\(\)\s*=>\s*{[\s\S]*?const\s+nextStart\s*=\s*nextDefaultStart\(\);[\s\S]*?setStart\(nextStart\);[\s\S]*?setEnd\(nextStart\);[\s\S]*?setDurHours\(0\);[\s\S]*?setDurMinutes\(0\);[\s\S]*?}\s*,\s*\[nextDefaultStart\]\s*\)/.test(timeControls),
  "resetTimeDefaults must reset start/end/duration from nextDefaultStart"
);

console.log(JSON.stringify({ ok: true, checked: "new_task_modal_fresh_defaults_contract" }));
