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

const onboarding = read("frontend/components/onboarding-flow.tsx");
const flow = read("frontend/lib/hooks/use-brain-dump-flow.ts");

assert(
  onboarding.includes("The items that worked are already saved.")
    && onboarding.includes("Only the rows below")
    && onboarding.includes("will be retried."),
  "onboarding must tell the user that successful rows stay saved and only failures retry",
);

for (const testId of [
  "onboarding-brain-dump-textarea",
  "onboarding-brain-dump-parse",
  "onboarding-brain-dump-lock-in",
  "onboarding-brain-dump-failures",
  "onboarding-brain-dump-edit-failed-items",
  "onboarding-brain-dump-move-failed-to-tomorrow",
  "onboarding-brain-dump-continue-saved",
]) {
  assert(
    onboarding.includes(`data-testid="${testId}"`),
    `onboarding recovery control is missing stable selector ${testId}`,
  );
}

assert(
  onboarding.includes("onboarding-brain-dump-item-title-${it.item_id}")
    && onboarding.includes("onboarding-brain-dump-item-when-${it.item_id}")
    && onboarding.includes("onboarding-brain-dump-item-duration-${it.item_id}"),
  "onboarding confirmation must expose editable title, date, and duration fields",
);

assert(
  onboarding.includes("updateItem(it.item_id")
    && onboarding.includes("removeItem(it.item_id)"),
  "onboarding review must route edits and discard through the shared flow owner",
);

assert(
  onboarding.includes("retryFailedItems({ movePastToTomorrow: true })")
    && onboarding.includes("onClick={() => retryFailedItems()}"),
  "onboarding partial recovery must expose bounded move and edit retry commands",
);

assert(
  onboarding.includes("onClick={onCompleted}")
    && !onboarding.includes("clearFailures();\n                  onCompleted();"),
  "continuing with saved items must not erase retry evidence before onboarding refetches",
);

assert(
  flow.includes("const failedIds = new Set(failures.map((failure) => failure.item_id))")
    && flow.includes(".filter((item) => failedIds.has(item.item_id))")
    && flow.includes("setItems(nextItems)"),
  "shared retry must retain only failed rows so successful rows are never resubmitted",
);

console.log(JSON.stringify({
  ok: true,
  checked: "onboarding_brain_dump_partial_recovery_contract",
}));
