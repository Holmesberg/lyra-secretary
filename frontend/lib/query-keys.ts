import type { QueryClient, QueryKey } from "@tanstack/react-query";

export const queryKeys = {
  adminDashboard: ["admin-dashboard"] as const,
  adminEmailEngagement: (campaignVersion: string, sinceDays: number) =>
    ["admin-email-engagement", campaignVersion, sinceDays] as const,
  deadlines: ["deadlines"] as const,
  me: ["me"] as const,
  operatorDashboard: ["operator-dashboard-v12"] as const,
  pressureMap: ["pressure-map"] as const,
  stopwatchStatus: ["stopwatch-status"] as const,
  tasks: ["tasks"] as const,
  tasksEvidence: ["tasks-evidence"] as const,
  tasksRange: ["tasks-range"] as const,
} satisfies Record<string, QueryKey | ((...args: never[]) => QueryKey)>;

const domainKeys = {
  admin: [queryKeys.adminDashboard],
  operator: [queryKeys.operatorDashboard],
} satisfies Record<string, QueryKey[]>;

export type QueryDomain = keyof typeof domainKeys;

function invalidateKeys(queryClient: QueryClient, keys: readonly QueryKey[]) {
  return Promise.all(
    keys.map((queryKey) => queryClient.invalidateQueries({ queryKey })),
  );
}

export function invalidateDomain(
  queryClient: QueryClient,
  domain: QueryDomain,
) {
  return invalidateKeys(queryClient, domainKeys[domain]);
}

export function invalidateTimerCommandSurfaces(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [
    queryKeys.stopwatchStatus,
    queryKeys.tasks,
    queryKeys.tasksRange,
    queryKeys.tasksEvidence,
    queryKeys.pressureMap,
    queryKeys.me,
  ]);
}

export function invalidateBrainDumpCommitCaches(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [
    queryKeys.tasks,
    queryKeys.deadlines,
    queryKeys.me,
    queryKeys.tasksRange,
    queryKeys.tasksEvidence,
    queryKeys.pressureMap,
  ]);
}

export function invalidatePressureRecoveryCommitCaches(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [
    queryKeys.tasks,
    queryKeys.tasksRange,
    queryKeys.tasksEvidence,
    queryKeys.pressureMap,
    queryKeys.deadlines,
  ]);
}
