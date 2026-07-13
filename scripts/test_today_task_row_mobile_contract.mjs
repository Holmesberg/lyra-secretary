import assert from "node:assert/strict";
import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");

const taskRow = read("frontend/components/task-row.tsx");
const browser = read("scripts/browser_holmesberg_product_loop_dogfood.mjs");
const wrapper = read("scripts/run_holmesberg_product_loop_dogfood.ps1");

assert(
  taskRow.includes("flex w-full min-w-0 flex-col items-stretch")
    && taskRow.includes("sm:flex-row sm:items-center"),
  "TaskRow must stack on narrow viewports and preserve the desktop row",
);
assert(
  taskRow.includes('className="flex min-w-0 items-center gap-2 sm:contents"')
    && taskRow.includes('className="flex min-w-0 flex-wrap items-center gap-2 sm:contents"'),
  "TaskRow must keep primary content bounded and allow metadata/actions to wrap",
);
assert(
  taskRow.includes("ml-auto flex flex-wrap items-center justify-end gap-1"),
  "TaskRow commands must remain mounted and wrap within the row",
);

assert(
  browser.includes('addCheck("Today task row and commands fit the mobile viewport"')
    && browser.includes("mobileDocumentOverflow <= 1")
    && browser.includes("mobileTaskButtonBoxes.every"),
  "focused Today proof must fail on document, row, or command overflow",
);
assert(
  wrapper.includes("[switch]$TodayStopwatchOutputProofOnly")
    && wrapper.includes('$args += "--stopwatch-output-proof-only"'),
  "PowerShell wrapper must expose the focused Today task-row proof",
);

console.log(JSON.stringify({ ok: true, checked: "today_task_row_mobile_contract" }));
