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
const undoToastHost = read("frontend/components/undo-toast-host.tsx");

assert(
  /export function invalidateUndoCaches\(queryClient: QueryClient\)/.test(queryKeys),
  "Undo invalidation must live in the central query-key authority"
);
assert(
  /queryKeys\.tasks[\s\S]*queryKeys\.tasksRange[\s\S]*queryKeys\.tasksEvidence[\s\S]*queryKeys\.pressureMap[\s\S]*queryKeys\.stopwatchStatus[\s\S]*queryKeys\.deadlines[\s\S]*queryKeys\.operatorDashboard[\s\S]*\["operator-dashboard"\][\s\S]*queryKeys\.me/.test(
    queryKeys
  ),
  "Undo invalidation must include task, range, evidence, Pressure Map, stopwatch, deadline, active operator, legacy operator, and user caches"
);
assert(
  undoToastHost.includes('import { invalidateUndoCaches } from "@/lib/query-keys";'),
  "Undo toast host must import the central undo invalidation helper"
);
assert(
  undoToastHost.includes("void invalidateUndoCaches(qc);"),
  "Undo toast host must call the central undo invalidation helper after successful undo"
);
assert(
  !/function invalidateAfterUndo/.test(undoToastHost),
  "Undo toast host must not keep a local duplicate invalidation list"
);

console.log(JSON.stringify({ ok: true, checked: "undo_invalidation_contract" }));
