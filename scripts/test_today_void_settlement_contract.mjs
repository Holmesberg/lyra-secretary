import assert from "node:assert/strict";
import fs from "node:fs";

const read = (path) => fs.readFileSync(path, "utf8");

const today = read("frontend/app/(app)/today/page.tsx");
const browser = read("scripts/browser_holmesberg_product_loop_dogfood.mjs");
const wrapper = read("scripts/run_holmesberg_product_loop_dogfood.ps1");

assert(
  today.includes("await qc.cancelQueries({ queryKey: tasksDayKey });")
    && today.includes("const snapshot = qc.getQueryData<TaskRowType[]>(tasksDayKey);")
    && today.includes("await refresh();"),
  "single-task deletion must snapshot, reconcile, and refetch canonical Today truth",
);
assert(
  today.includes("const results = await Promise.allSettled(")
    && today.includes("result is PromiseRejectedResult")
    && today.includes("tasks could not be voided"),
  "bulk void must settle independent writer outcomes instead of rolling all siblings back",
);
assert(
  browser.includes('const todayVoidSettlementProofOnly = args.get("today-void-settlement-proof-only") === "true"')
    && browser.includes('proof_scope: "today_delete_void_failure_settlement"')
    && browser.includes("Today partial bulk void preserves each canonical outcome"),
  "focused browser proof must exercise failed single deletion and partial bulk settlement",
);
assert(
  wrapper.includes("[switch]$TodayVoidSettlementProofOnly")
    && wrapper.includes('$args += "--today-void-settlement-proof-only"'),
  "PowerShell wrapper must expose the focused Today settlement proof",
);

console.log(JSON.stringify({ ok: true, checked: "today_void_settlement_contract" }));
