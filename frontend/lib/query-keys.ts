import type { QueryClient, QueryKey } from "@tanstack/react-query";

export const queryKeys = {
  adminDashboard: ["admin-dashboard"] as const,
  adminEmailEngagement: (campaignVersion: string, sinceDays: number) =>
    ["admin-email-engagement", campaignVersion, sinceDays] as const,
  archetypeProximity: (days: number) => ["proximity", days] as const,
  archetypeProximityTrend: (currentDays: number, priorDays: number) =>
    ["proximity-trend", currentDays, priorDays] as const,
  biasFactor: ["bias_factor"] as const,
  biasFactorLookup: (category: string, tod: string, plannedMinutes: number) =>
    ["bias_factor", category, tod, plannedMinutes] as const,
  calendarEvents: ["calendar-events"] as const,
  calendarEventsToday: (date: string) => ["calendar-events-today", date] as const,
  calendarEventsWindow: (dateFrom: string, dateTo: string) =>
    ["calendar-events", dateFrom, dateTo] as const,
  deadlines: ["deadlines"] as const,
  deadlineBindingCorrection: ["deadlines", "binding-correction"] as const,
  deadlinesBindable: ["deadlines", "bindable"] as const,
  deadlinesAll: ["deadlines", "all"] as const,
  insights: ["insights"] as const,
  integrations: ["integrations"] as const,
  me: ["me"] as const,
  notificationsWebPending: ["notifications-web-pending"] as const,
  operatorDashboard: ["operator-dashboard-v12"] as const,
  pausePredictionsPendingConfirmation: [
    "pause-predictions-pending-confirmation",
  ] as const,
  pressureMap: ["pressure-map"] as const,
  pressureMapHorizon: (horizonDays: number) =>
    ["pressure-map", horizonDays] as const,
  stopwatchStatus: ["stopwatch-status"] as const,
  tasks: ["tasks"] as const,
  tasksDay: (date: string) => ["tasks", date] as const,
  tasksEvidence: ["tasks-evidence"] as const,
  tasksEvidenceWindow: (dateFrom: string, dateTo: string) =>
    ["tasks-evidence", dateFrom, dateTo] as const,
  tasksRange: ["tasks-range"] as const,
  tasksRangeWindow: (dateFrom: string, dateTo: string, includeVoided = false) =>
    [
      "tasks-range",
      dateFrom,
      dateTo,
      includeVoided ? "include-voided" : "active",
    ] as const,
  userCategories: ["user-categories"] as const,
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

export function isCalendarEventsQueryKey(queryKey: QueryKey) {
  return (
    typeof queryKey[0] === "string" &&
    queryKey[0].startsWith(queryKeys.calendarEvents[0])
  );
}

export function isDeadlineQueryKey(queryKey: QueryKey) {
  return (
    typeof queryKey[0] === "string" &&
    queryKey[0].startsWith("deadline")
  );
}

export function isTaskQueryKey(queryKey: QueryKey) {
  return (
    typeof queryKey[0] === "string" &&
    (queryKey[0] === queryKeys.tasks[0] ||
      queryKey[0] === queryKeys.tasksRange[0])
  );
}

export function isBiasFactorQueryKey(queryKey: QueryKey) {
  return queryKey[0] === queryKeys.biasFactor[0];
}

export function isArchetypeProximityQueryKey(queryKey: QueryKey) {
  return (
    queryKey[0] === queryKeys.archetypeProximity(14)[0] ||
    queryKey[0] === queryKeys.archetypeProximityTrend(14, 14)[0]
  );
}

export function invalidateCalendarEventQueries(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => isCalendarEventsQueryKey(query.queryKey),
  });
}

export function invalidateDeadlineQueries(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => isDeadlineQueryKey(query.queryKey),
  });
}

export function invalidateTaskQueries(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => isTaskQueryKey(query.queryKey),
  });
}

export function invalidateBiasFactorQueries(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => isBiasFactorQueryKey(query.queryKey),
  });
}

export function invalidateArchetypeProximityQueries(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (query) => isArchetypeProximityQueryKey(query.queryKey),
  });
}

export function invalidateArchetypeDependentQueries(queryClient: QueryClient) {
  return Promise.all([
    invalidateKeys(queryClient, [queryKeys.insights, queryKeys.me]),
    invalidateBiasFactorQueries(queryClient),
    invalidateArchetypeProximityQueries(queryClient),
  ]);
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

export function invalidatePulseReentryCaches(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [
    queryKeys.stopwatchStatus,
    queryKeys.tasks,
    queryKeys.tasksRange,
    queryKeys.tasksEvidence,
    queryKeys.pressureMap,
  ]);
}

export function invalidateTodayTaskCommandSurfaces(
  queryClient: QueryClient,
  viewedDate: string,
  nextDate: string,
) {
  return invalidateKeys(queryClient, [
    queryKeys.tasksDay(viewedDate),
    queryKeys.tasksDay(nextDate),
    queryKeys.stopwatchStatus,
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

export function invalidateIntegrationAccountCaches(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [
    queryKeys.integrations,
    queryKeys.me,
  ]);
}

export function invalidateIntegrationStatusCaches(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [queryKeys.integrations]);
}

export function invalidateIntegrationDisconnectCaches(queryClient: QueryClient) {
  return Promise.all([
    invalidateIntegrationAccountCaches(queryClient),
    invalidateCalendarEventQueries(queryClient),
  ]);
}

export function invalidateMoodleFeedSyncCaches(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [
    queryKeys.integrations,
    queryKeys.deadlines,
  ]);
}

export function invalidateMoodleConnectCaches(queryClient: QueryClient) {
  return Promise.all([
    invalidateMoodleFeedSyncCaches(queryClient),
    invalidateDeadlineQueries(queryClient),
  ]);
}

export function invalidateUndoCaches(queryClient: QueryClient) {
  return invalidateKeys(queryClient, [
    queryKeys.tasks,
    queryKeys.tasksRange,
    queryKeys.tasksEvidence,
    queryKeys.stopwatchStatus,
    queryKeys.deadlines,
    queryKeys.operatorDashboard,
    ["operator-dashboard"],
    queryKeys.me,
  ]);
}
