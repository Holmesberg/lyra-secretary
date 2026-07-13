"use client";
/* eslint-disable react/no-unescaped-entities */
/**
 * /pulse v2 — Neural Noir command surface (2026-04-29 evening).
 *
 * Reference image: docs/Screenshots/ChatGPT Image Apr 29, 2026,
 * 10_25_37 PM.png. The "absolute WOW" the operator pointed at.
 *
 * Layout grammar (max-w-[1400px] inside the new sidebar AppShell):
 *   ┌─ PulseGreeting (greeting + status pills + icon buttons) ─────┐
 *   ├─ HERO ROW (3 cols) ──────────────────────────────────────────┤
 *   │  Today's Plan │  Current Focus Session  │  Deadlines        │
 *   │   (3/12)      │      (5/12)             │   (4/12)          │
 *   ├─ BOTTOM ROW (3 cols) ────────────────────────────────────────┤
 *   │  System Insight │  Recovery rhythm  │   Integrations         │
 *   │   (5/12)        │     (4/12)        │     (3/12)             │
 *   └─ Quick Capture (full width) ─────────────────────────────────┘
 *
 * All charts are real-data: focusMinutesByDay() aggregates the past
 * 14 days of EXECUTED tasks client-side from /v1/tasks/query, fed
 * into Tremor's AreaChart (system insight) + BarChart (recovery).
 *
 * The radial focus timer is custom SVG (RadialFocusTimer.tsx) — cyan
 * progress arc with breathing pulse-glow, ember tone on pause/overflow.
 *
 * Zero new backend endpoints. Zero schema changes. All data sourced
 * from endpoints that existed before this commit.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import {
  queryTasks,
  queryTasksRange,
  type QueryResponse,
  type TaskRow,
} from "@/lib/tasks";
import {
  listDeadlines,
  type DeadlineListResponse,
} from "@/lib/deadlines";
import {
  getIntegrations,
  type IntegrationsResponse,
} from "@/lib/integrations";
import {
  getAcademicPressureMap,
  type AcademicPressureMapResponse,
} from "@/lib/academic";
import { registerPressureMapCandidate } from "@/lib/pressure-map-exposure";
import {
  focusMinutesToday,
  winsToday,
} from "@/lib/pulse-aggregations";
import { queryKeys } from "@/lib/query-keys";

import { PulseGreeting } from "@/components/pulse/PulseGreeting";
import { PulseTodaysPlanV2 } from "@/components/pulse/PulseTodaysPlanV2";
import { PulseFocusCard } from "@/components/pulse/PulseFocusCard";
import { PulseDeadlinesV2 } from "@/components/pulse/PulseDeadlinesV2";
import { PulseSystemInsight } from "@/components/pulse/PulseSystemInsight";
import { PulseAcademicPressureMap } from "@/components/pulse/PulseAcademicPressureMap";
import { PulseRecovery } from "@/components/pulse/PulseRecovery";
import { PulseIntegrationsV2 } from "@/components/pulse/PulseIntegrationsV2";
import { PulseQuickCaptureV2 } from "@/components/pulse/PulseQuickCaptureV2";
import { PulseReentryQueue } from "@/components/pulse/PulseReentryQueue";

interface MeLite {
  user_id: number;
  email: string;
  executed_session_count: number;
}

function todayKey(): string {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function fourteenDaysAgoKey(): string {
  return dateKeyOffset(-13); // inclusive of today = 14 days total
}

function dateKeyOffset(offsetDays: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const TASK_EVIDENCE_HISTORY_DAYS = 62;

function PulseUnavailablePanel({
  testId,
  label,
}: {
  testId: string;
  label: string;
}) {
  return (
    <div
      data-testid={testId}
      role="status"
      className="terminal-panel flex min-h-[180px] flex-col items-center justify-center gap-3 px-5 py-7 text-center"
    >
      <AlertTriangle className="h-5 w-5 text-ember" aria-hidden />
      <div>
        <div className="font-display text-[10px] uppercase tracking-macro text-ember">
          [ Unavailable ]
        </div>
        <p className="mt-2 max-w-xs text-sm text-parchment">
          {label} did not load.
        </p>
        <p className="mt-1 text-xs text-dust">Other Pulse tools are still usable.</p>
      </div>
    </div>
  );
}

export default function PulsePage() {
  const today = todayKey();
  const fortnightStart = fourteenDaysAgoKey();
  const { data: session } = useSession();
  const [pressureHorizonDays, setPressureHorizonDays] = useState(14);
  const taskEvidenceStart = dateKeyOffset(-TASK_EVIDENCE_HISTORY_DAYS);
  const taskEvidenceEnd = dateKeyOffset(pressureHorizonDays);

  const meQ = useQuery<MeLite>({
    queryKey: queryKeys.me,
    queryFn: () => api<MeLite>("/v1/users/me"),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
  const tasksTodayQ = useQuery<TaskRow[]>({
    queryKey: queryKeys.tasksDay(today),
    queryFn: () => queryTasks(today, 1),
    staleTime: 30_000,
  });
  // Two-week window for the recovery + system-insight charts. Backend
  // already collapses count + rows in one round trip (see the latency
  // sweep ship d7993d0), so this is a single Supabase query.
  const tasksRangeQ = useQuery<QueryResponse>({
    queryKey: queryKeys.tasksRangeWindow(fortnightStart, today),
    queryFn: () => queryTasksRange(fortnightStart, today),
    staleTime: 60_000,
  });
  const taskEvidenceQ = useQuery<QueryResponse>({
    queryKey: queryKeys.tasksEvidenceWindow(taskEvidenceStart, taskEvidenceEnd),
    queryFn: () => queryTasksRange(taskEvidenceStart, taskEvidenceEnd),
    staleTime: 60_000,
  });
  const deadlinesQ = useQuery<DeadlineListResponse>({
    queryKey: queryKeys.deadlines,
    queryFn: () => listDeadlines(),
    staleTime: 60_000,
  });
  const integrationsQ = useQuery<IntegrationsResponse>({
    queryKey: queryKeys.integrations,
    queryFn: getIntegrations,
    staleTime: 60_000,
  });
  const pressureQ = useQuery<AcademicPressureMapResponse>({
    queryKey: queryKeys.pressureMapHorizon(pressureHorizonDays),
    queryFn: async () => {
      const pressure = await getAcademicPressureMap(pressureHorizonDays);
      registerPressureMapCandidate(pressure);
      return pressure;
    },
    staleTime: 60_000,
  });

  const failedPulseReads = [
    { label: "account", failed: meQ.isError, fetching: meQ.isFetching, refetch: meQ.refetch },
    { label: "today's plan", failed: tasksTodayQ.isError, fetching: tasksTodayQ.isFetching, refetch: tasksTodayQ.refetch },
    { label: "recent sessions", failed: tasksRangeQ.isError, fetching: tasksRangeQ.isFetching, refetch: tasksRangeQ.refetch },
    { label: "planning evidence", failed: taskEvidenceQ.isError, fetching: taskEvidenceQ.isFetching, refetch: taskEvidenceQ.refetch },
    { label: "deadlines", failed: deadlinesQ.isError, fetching: deadlinesQ.isFetching, refetch: deadlinesQ.refetch },
    { label: "integrations", failed: integrationsQ.isError, fetching: integrationsQ.isFetching, refetch: integrationsQ.refetch },
    { label: "Pressure Map", failed: pressureQ.isError, fetching: pressureQ.isFetching, refetch: pressureQ.refetch },
  ].filter((read) => read.failed);
  const retryingFailedReads = failedPulseReads.some((read) => read.fetching);

  function retryFailedReads() {
    void Promise.allSettled(failedPulseReads.map((read) => read.refetch()));
  }

  const tasksToday = tasksTodayQ.data ?? [];
  const recentTasks = tasksRangeQ.data?.tasks ?? [];
  const taskEvidence = taskEvidenceQ.data?.tasks ?? recentTasks;
  const deadlines = deadlinesQ.data?.deadlines ?? [];
  const integrations = integrationsQ.data?.integrations ?? [];

  const overdueCount = useMemo(() => {
    const nowMs = Date.now();
    return deadlines.filter((d) => {
      if (d.voided_at) return false;
      if (d.state === "missed") return true;
      if (d.state === "planned" || d.state === "active") {
        return new Date(d.due_at_utc).getTime() < nowMs;
      }
      return false;
    }).length;
  }, [deadlines]);

  const todaysFocusMinutes = focusMinutesToday(tasksToday);
  const todaysWins = winsToday(tasksToday);

  // Prefer Google's display name from the NextAuth session ('Mohamed
  // El Hammady' → 'Mohamed') over parsing email-before-the-@ since
  // 'mohamed.elhammady25' isn't a name a human wants to be greeted by.
  // Falls back to email parse only if the session lacks a name.
  const sessionName = session?.user?.name?.trim() ?? null;
  const fallbackName = meQ.data?.email
    ? meQ.data.email.split("@")[0].split(".")[0]
    : null;
  const rawFirst = sessionName
    ? sessionName.split(/\s+/)[0]
    : fallbackName;
  const displayName = rawFirst
    ? rawFirst.charAt(0).toUpperCase() + rawFirst.slice(1).toLowerCase()
    : null;

  return (
    <div className="flex flex-col gap-6">
      <PulseGreeting
        displayName={displayName}
        focusMinutesToday={tasksTodayQ.isError ? null : todaysFocusMinutes}
        winsToday={tasksTodayQ.isError ? null : todaysWins}
        overdueCount={deadlinesQ.isError ? null : overdueCount}
      />

      <PulseQuickCaptureV2 />

      {failedPulseReads.length > 0 && (
        <div
          data-testid="pulse-partial-error"
          role="alert"
          className="flex flex-col gap-3 border border-ember/40 bg-ember/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex min-w-0 items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-ember" aria-hidden />
            <div className="min-w-0">
              <p className="text-sm font-medium text-parchment">Some live data is unavailable</p>
              <p className="mt-0.5 text-xs text-dust">
                {failedPulseReads.map((read) => read.label).join(", ")}
              </p>
            </div>
          </div>
          <button
            data-testid="pulse-partial-error-retry"
            type="button"
            onClick={retryFailedReads}
            disabled={retryingFailedReads}
            className="inline-flex min-h-[40px] shrink-0 items-center justify-center gap-2 border border-ember/40 px-3 font-mono text-[10px] uppercase tracking-widest text-ember transition-colors hover:bg-ember/10 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${retryingFailedReads ? "animate-spin" : ""}`} />
            Retry
          </button>
        </div>
      )}

      {taskEvidenceQ.isError ? (
        <PulseUnavailablePanel testId="pulse-unavailable-reentry" label="Re-entry" />
      ) : (
        <PulseReentryQueue tasks={taskEvidence} />
      )}

      {/* HERO ROW — Today's Plan | Focus Card | Deadlines */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-3">
          {tasksTodayQ.isError ? (
            <PulseUnavailablePanel testId="pulse-unavailable-today-plan" label="Today's plan" />
          ) : (
            <div data-testid="pulse-today-plan-section">
              <PulseTodaysPlanV2 tasks={tasksToday} />
            </div>
          )}
        </div>
        <div className="lg:col-span-5">
          {tasksTodayQ.isError ? (
            <PulseUnavailablePanel testId="pulse-unavailable-current-focus" label="Current focus" />
          ) : (
            <PulseFocusCard todaysTasks={tasksToday} />
          )}
        </div>
        <div className="lg:col-span-4">
          {deadlinesQ.isError ? (
            <PulseUnavailablePanel testId="pulse-unavailable-deadlines" label="Deadlines" />
          ) : (
            <div data-testid="pulse-deadlines-section">
              <PulseDeadlinesV2 deadlines={deadlines} />
            </div>
          )}
        </div>
      </div>

      {/* BOTTOM ROW — System Insight | Recovery | Integrations */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-4">
          {tasksRangeQ.isError ? (
            <PulseUnavailablePanel testId="pulse-unavailable-system-insight" label="System insight" />
          ) : (
            <PulseSystemInsight
              tasksToday={tasksToday}
              recentTasks={recentTasks}
            />
          )}
        </div>
        <div className="lg:col-span-4">
          {pressureQ.isError ? (
            <PulseUnavailablePanel testId="pulse-unavailable-pressure-map" label="Pressure Map" />
          ) : (
            <div data-testid="pulse-pressure-section">
              <PulseAcademicPressureMap
                pressure={pressureQ.data ?? null}
                loading={pressureQ.isLoading}
                horizonDays={pressureHorizonDays}
                onHorizonChange={setPressureHorizonDays}
                taskEvidence={taskEvidence}
              />
            </div>
          )}
        </div>
        <div className="grid gap-4 lg:col-span-4">
          <div>
            {tasksRangeQ.isError ? (
              <PulseUnavailablePanel testId="pulse-unavailable-recovery" label="Recovery rhythm" />
            ) : (
              <PulseRecovery recentTasks={recentTasks} />
            )}
          </div>
          <div>
            {integrationsQ.isError ? (
              <PulseUnavailablePanel testId="pulse-unavailable-integrations" label="Integrations" />
            ) : (
              <div data-testid="pulse-integrations-section">
                <PulseIntegrationsV2 integrations={integrations} />
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="text-center font-mono text-[10px] uppercase tracking-widest text-dust-deep">
        // /pulse v2 · Neural Noir command surface · {recentTasks.length}{" "}
        sessions analyzed across last 14 days
      </div>
    </div>
  );
}
