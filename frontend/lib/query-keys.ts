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
  tasksRange: ["tasks-range"] as const,
} satisfies Record<string, QueryKey | ((...args: never[]) => QueryKey)>;

const domainKeys = {
  admin: [queryKeys.adminDashboard],
  operator: [queryKeys.operatorDashboard],
} satisfies Record<string, QueryKey[]>;

export type QueryDomain = keyof typeof domainKeys;

export function invalidateDomain(
  queryClient: QueryClient,
  domain: QueryDomain,
) {
  return Promise.all(
    domainKeys[domain].map((queryKey) =>
      queryClient.invalidateQueries({ queryKey }),
    ),
  );
}
