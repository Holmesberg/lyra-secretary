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
const deadlinesPage = read("frontend/app/(app)/deadlines/page.tsx");
const calendarPage = read("frontend/app/(app)/calendar/page.tsx");
const integrationsSection = read("frontend/components/integrations-section.tsx");
const tablePage = read("frontend/app/(app)/table/page.tsx");
const todayPage = read("frontend/app/(app)/today/page.tsx");

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
assert(
  /export function invalidateTaskMutationCaches[\s\S]*queryKeys\.tasks,[\s\S]*queryKeys\.tasksRange,[\s\S]*queryKeys\.tasksEvidence,[\s\S]*queryKeys\.pressureMap,[\s\S]*queryKeys\.me,[\s\S]*?\n}/.test(queryKeys),
  "task mutation invalidation must cover task, range, evidence, Pressure Map, and user projections",
);
assert(
  /export function invalidateDeadlineMutationCaches[\s\S]*queryKeys\.deadlines,[\s\S]*queryKeys\.tasks,[\s\S]*queryKeys\.tasksRange,[\s\S]*queryKeys\.tasksEvidence,[\s\S]*queryKeys\.pressureMap,[\s\S]*queryKeys\.me,[\s\S]*?\n}/.test(queryKeys),
  "deadline mutation invalidation must cover deadline and dependent task projections",
);
assert(
  /export function invalidatePulseReentryCaches[\s\S]*invalidateTaskMutationCaches\(queryClient\)[\s\S]*queryKeys\.stopwatchStatus[\s\S]*?\n}/.test(queryKeys)
    && /export function invalidateTodayTaskCommandSurfaces[\s\S]*invalidateTaskMutationCaches\(queryClient\)[\s\S]*queryKeys\.stopwatchStatus[\s\S]*?\n}/.test(queryKeys),
  "Today and re-entry mutations must use the shared task recipe plus stopwatch truth",
);
assert(
  /export function invalidateBrainDumpCommitCaches[\s\S]*return invalidateDeadlineMutationCaches\(queryClient\)/.test(queryKeys)
    && /export function invalidatePressureRecoveryCommitCaches[\s\S]*return invalidateDeadlineMutationCaches\(queryClient\)/.test(queryKeys),
  "capture and Pressure Map commits must use the shared deadline-dependent recipe",
);
for (const [name, source] of [
  ["Deadlines", deadlinesPage],
  ["Calendar", calendarPage],
  ["Today", todayPage],
]) {
  assert(
    source.includes('invalidateDeadlineMutationCaches'),
    `${name} deadline mutations must use the shared deadline-dependent recipe`,
  );
  assert(
    !/invalidateQueries\(\{\s*queryKey:\s*queryKeys\.deadlines\s*}/.test(source),
    `${name} must not keep a deadline-only invalidation path`,
  );
}

for (const [name, source] of [
  ["Calendar", calendarPage],
  ["Table", tablePage],
]) {
  assert(
    source.includes("invalidateTaskMutationCaches"),
    `${name} task mutations must use the shared task-dependent recipe`,
  );
}
assert(
  !tablePage.includes("void refetchTasks();"),
  "Table correction must not refresh only its local task range",
);
assert(
  /export function invalidateCalendarIntegrationCaches[\s\S]*invalidateIntegrationAccountCaches\(queryClient\)[\s\S]*invalidateCalendarEventQueries\(queryClient\)[\s\S]*?\n}/.test(queryKeys),
  "calendar integration mutations must refresh account and Calendar event projections",
);
assert(
  /export function invalidateMoodleFeedSyncCaches[\s\S]*invalidateIntegrationStatusCaches\(queryClient\)[\s\S]*invalidateDeadlineMutationCaches\(queryClient\)[\s\S]*?\n}/.test(queryKeys)
    && /export function invalidateMoodleConnectCaches[\s\S]*return invalidateMoodleFeedSyncCaches\(queryClient\)/.test(queryKeys),
  "Moodle connect and sync must use integration status plus shared deadline-dependent invalidation",
);
assert(
  (integrationsSection.match(/invalidateCalendarIntegrationCaches/g) || []).length >= 3,
  "Google connect and integration disconnect must use Calendar-dependent invalidation",
);
assert(
  (integrationsSection.match(/invalidateMoodleFeedSyncCaches/g) || []).length >= 3,
  "both Moodle sync controls must use the shared feed invalidation recipe",
);

console.log(JSON.stringify({ ok: true, checked: "frontend_query_keys_contract" }));
