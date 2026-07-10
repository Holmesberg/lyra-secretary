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

const queryKeys = read("frontend/lib/query-keys.ts");

assert(
  queryKeys.includes("operatorDashboard: [\"operator-dashboard-v12\"] as const"),
  "Operator cockpit query key must remain the active dashboard authority",
);
assert(
  !/adminDashboard\s*:/.test(queryKeys),
  "Removed admin dashboard must not keep a frontend query-key authority",
);
assert(
  !/adminEmailEngagement\s*:/.test(queryKeys),
  "Admin-only email engagement must not keep an app-dashboard query-key authority",
);
assert(
  !/admin\s*:\s*\[queryKeys\.adminDashboard\]/.test(queryKeys),
  "invalidateDomain must not keep a removed admin dashboard domain",
);
assert(
  /operator\s*:\s*\[queryKeys\.operatorDashboard\]/.test(queryKeys),
  "invalidateDomain must keep the operator cockpit domain",
);

console.log(JSON.stringify({ ok: true, checked: "frontend_query_keys_contract" }));
