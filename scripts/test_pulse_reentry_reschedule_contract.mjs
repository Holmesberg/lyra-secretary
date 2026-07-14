#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(relativePath) {
  return fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const queue = read("frontend/components/pulse/PulseReentryQueue.tsx");
const commands = read("frontend/lib/hooks/use-pulse-reentry-commands.ts");
const today = read("frontend/app/(app)/today/page.tsx");
const taskModal = read("frontend/components/new-task-modal.tsx");

assert(
  /new URLSearchParams\(\{ date, edit_task: taskId \}\)/.test(queue),
  "Re-entry must build a task-specific editor destination",
);
assert(
  (queue.match(/tasks\.find\(\(candidate\) => candidate\.task_id ===/g) || []).length === 2,
  "Paused re-entry destinations must preserve the task's planned day",
);
assert(
  /href=\{candidate\.rescheduleHref\}[\s\S]*Reschedule/.test(queue),
  "Every mounted re-entry card must expose an explicit Reschedule command",
);
assert(
  (commands.match(/rescheduleHref: string;/g) || []).length === 2,
  "Paused and missed-plan candidates must both carry the editor destination",
);
assert(
  !queue.includes("rescheduleTask("),
  "Pulse re-entry must not create a second reschedule writer",
);
assert(
  /searchParams\.get\("edit_task"\)/.test(today)
    && /params\.delete\("edit_task"\)/.test(today)
    && /candidate\.task_id === requestedTaskId/.test(today)
    && /setEditingTask\(task\)/.test(today),
  "Today must consume the task editor destination once and use the existing editor",
);
assert(
  /task\.voided_at[\s\S]*task\.state === "EXECUTED"[\s\S]*task\.state === "DELETED"/.test(today),
  "Unknown, voided, and immutable task destinations must not open the reschedule editor",
);
assert(
  taskModal.includes('className="max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] overflow-y-auto"'),
  "The shared task editor must stay inset and scrollable on mobile viewports",
);

console.log(JSON.stringify({ ok: true, checked: "pulse_reentry_reschedule_contract" }));
