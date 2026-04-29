"use client";
/**
 * /pulse — Neural Noir dashboard prototype (2026-04-29 evening).
 *
 * Single-glance command surface for an active Lyra user. Composes 6
 * panels from existing endpoints — zero backend work, zero schema
 * changes. Designed as a rollback-safe alternative to /today: navigate
 * via the "PULSE (preview)" nav entry, react, then either promote
 * (rename → /today) or revert the single feature commit.
 *
 * Layout grammar (max-w-6xl center column inside AppShell):
 *   ┌── HERO BAND ─────────────────────────┐
 *   │  PulseHero (stats)  │  FocusTimerHero │
 *   ├── GRID ──────────────────────────────┤
 *   │  TodayPulse        │  DeadlinesPulse │
 *   │   (left,           │  IntegrationPulse│
 *   │    wider)          │  InsightsPulse  │
 *   ├── QUICK CAPTURE ─────────────────────┤
 *   │  → brain-dump on /today              │
 *   └──────────────────────────────────────┘
 *
 * All panels use the existing Neural Noir vocabulary:
 *   - .terminal-panel for calm panels
 *   - .terminal-panel-ember + .alert-bar-ember for the OVERDUE pile
 *   - font-display Chakra Petch + neon-cyan/-ember glow for hero numbers
 *   - bracketed [ EYEBROW ] labels in tracking-macro
 *   - .status-dot pulsing indicators
 *
 * No new backend endpoints. No new schema. No new APScheduler jobs.
 * No new dependencies. Single feat commit, `git revert <hash>` removes
 * everything in ~2 minutes.
 */
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { api } from "@/lib/api";
import { queryTasks, type TaskRow } from "@/lib/tasks";
import {
  listDeadlines,
  type DeadlineListResponse,
} from "@/lib/deadlines";
import {
  getIntegrations,
  type IntegrationsResponse,
} from "@/lib/integrations";

import { PulseHero } from "@/components/pulse/PulseHero";
import { FocusTimerHero } from "@/components/pulse/FocusTimerHero";
import { TodayPulse } from "@/components/pulse/TodayPulse";
import { DeadlinesPulse } from "@/components/pulse/DeadlinesPulse";
import { IntegrationPulse } from "@/components/pulse/IntegrationPulse";
import { InsightsPulse } from "@/components/pulse/InsightsPulse";
import { QuickCaptureStrip } from "@/components/pulse/QuickCaptureStrip";

interface MeLite {
  user_id: number;
  email: string;
  executed_session_count: number;
  has_active_task_history: boolean;
}

function todayKey(): string {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function greeting(hour: number): string {
  if (hour < 5) return "Up late";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  if (hour < 22) return "Good evening";
  return "Up late";
}

export default function PulsePage() {
  const today = todayKey();

  const meQ = useQuery<MeLite>({
    queryKey: ["me"],
    queryFn: () => api<MeLite>("/v1/users/me"),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });
  const tasksQ = useQuery<TaskRow[]>({
    queryKey: ["tasks", today],
    queryFn: () => queryTasks(today, 1),
    staleTime: 30_000,
  });
  const deadlinesQ = useQuery<DeadlineListResponse>({
    queryKey: ["deadlines"],
    queryFn: () => listDeadlines(),
    staleTime: 60_000,
  });
  const integrationsQ = useQuery<IntegrationsResponse>({
    queryKey: ["integrations"],
    queryFn: getIntegrations,
    staleTime: 60_000,
  });

  const tasks = tasksQ.data ?? [];
  const deadlines = deadlinesQ.data?.deadlines ?? [];
  const integrations = integrationsQ.data?.integrations ?? [];
  const sessionCount = meQ.data?.executed_session_count ?? 0;

  const now = useMemo(() => new Date(), []);
  const hourGreeting = greeting(now.getHours());
  const dateLabel = format(now, "EEEE, MMMM d");
  const firstName = meQ.data?.email
    ? meQ.data.email.split("@")[0].split(".")[0]
    : null;
  const displayName = firstName
    ? firstName.charAt(0).toUpperCase() + firstName.slice(1).toLowerCase()
    : null;

  const isLoading =
    meQ.isLoading || tasksQ.isLoading || deadlinesQ.isLoading;

  return (
    <div className="flex flex-col gap-5">
      {/* Page header — calm date readout + greeting. */}
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-signal/70">
            {">>"}{" "}
            <span className="text-signal">PULSE</span>{" "}
            <span className="text-dust-deep">// preview</span>
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-parchment">
            {hourGreeting}
            {displayName ? `, ${displayName}` : ""}.
          </h1>
          <div className="font-mono text-[11px] uppercase tracking-widest text-dust">
            {dateLabel}
          </div>
        </div>
      </div>

      {/* HERO BAND — stats + focus timer. Stack on narrow screens. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_minmax(280px,360px)]">
        <div>
          {isLoading ? (
            <div className="terminal-panel grid h-[148px] place-items-center text-xs text-dust">
              Reading the room…
            </div>
          ) : (
            <PulseHero
              tasks={tasks}
              deadlines={deadlines}
              executedSessionCount={sessionCount}
            />
          )}
        </div>
        <FocusTimerHero />
      </div>

      {/* GRID — today (wider, left) + right rail. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_minmax(280px,360px)]">
        <div>
          {tasksQ.isLoading ? (
            <div className="terminal-panel grid h-[200px] place-items-center text-xs text-dust">
              Loading today…
            </div>
          ) : (
            <TodayPulse tasks={tasks} />
          )}
        </div>
        <div className="flex flex-col gap-4">
          {deadlinesQ.isLoading ? (
            <div className="terminal-panel grid h-[140px] place-items-center text-xs text-dust">
              Loading deadlines…
            </div>
          ) : (
            <DeadlinesPulse deadlines={deadlines} />
          )}
          {!integrationsQ.isLoading && (
            <IntegrationPulse integrations={integrations} />
          )}
          {!meQ.isLoading && (
            <InsightsPulse executedSessionCount={sessionCount} />
          )}
        </div>
      </div>

      {/* QUICK CAPTURE FOOTER */}
      <QuickCaptureStrip />

      {/* Subtle preview-mode footer note. */}
      <div className="mt-2 text-center font-mono text-[10px] uppercase tracking-widest text-dust-deep">
        // /pulse is a preview surface · existing /today unchanged
      </div>
    </div>
  );
}
