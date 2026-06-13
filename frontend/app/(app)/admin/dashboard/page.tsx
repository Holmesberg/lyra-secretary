"use client";
// Force dynamic render — this page depends on session + backend state
// and must not be statically prerendered at build time (the prerender
// evaluates in a no-session, no-backend context and Next.js writes a
// 404 HTML for it, which then gets served at runtime). See
// Next.js static-vs-dynamic rendering docs.
export const dynamic = "force-dynamic";
/**
 * Operator retention dashboard.
 *
 * Closes the Apr 22 "retention data → product iteration" feedback loop
 * (see docs/feedback_loops_closure_plan.md §Loop 8). Replaces the
 * operator's manual psycopg2 queries with a single JSON fetch +
 * rendered table. Gated on `user.is_operator` backend-side; non-
 * operators receive 403 and see the access-denied state.
 *
 * Refetches every 5 minutes. Manual "Refresh now" button for when
 * the operator just shipped something and wants to see the effect.
 */
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface UserRow {
  user_id: number;
  email: string;
  is_operator: boolean;
  signed_up_at: string;
  onboarded_at: string | null;
  tutorial_status: "completed" | "skipped" | "pending";
  gcal_connected: boolean;
  task_total: number;
  active_task_count: number;
  skipped_count: number;
  far_future_planned_count: number;
  open_timer_count: number;
  executed_count: number;
  first_task_created_at: string | null;
  first_executed_at: string | null;
  last_activity_at: string | null;
  returning_today: boolean;
  returning_7d: boolean;
  activation_stage: string;
}

interface Totals {
  users_all: number;
  users_non_operator: number;
  returning_today: number;
  returning_7d: number;
}

interface Funnel {
  signed_up: number;
  onboarded: number;
  meaningful_plan: number;
  first_task: number;
  first_execution: number;
  returning_7d: number;
}

interface VtProgressEntry {
  label: string;
  threshold_users?: number;
  note: string;
  [key: string]: unknown;
}

interface DashboardData {
  calculated_at: string;
  totals: Totals;
  funnel: Funnel;
  users: UserRow[];
  vt_progress: Record<string, VtProgressEntry>;
}

interface EmailEngagementCampaign {
  campaign_version: string;
  opens: { events: number; distinct_recipients: number };
  clicks: { events: number; distinct_recipients: number };
}

interface EmailEngagementData {
  schema_version: string;
  since_days: number;
  read_note: string;
  campaigns: EmailEngagementCampaign[];
}

export default function AdminDashboardPage() {
  const q = useQuery<DashboardData>({
    queryKey: ["admin-dashboard"],
    queryFn: () => api<DashboardData>("/v1/admin/dashboard"),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    retry: (count, error) => {
      // Don't retry 401 or 403 — those are terminal, not transient.
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        return false;
      }
      return count < 2;
    },
  });
  const emailQ = useQuery<EmailEngagementData>({
    queryKey: ["admin-email-engagement", "landing-html-v7"],
    queryFn: () =>
      api<EmailEngagementData>(
        "/v1/admin/email-engagement?campaign_version=landing-html-v7&since_days=30"
      ),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    retry: (count, error) => {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        return false;
      }
      return count < 2;
    },
  });

  if (q.error instanceof ApiError && q.error.status === 403) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Admin Dashboard
        </h1>
        <Card>
          <CardContent className="p-6 text-sm text-dust">
            This page is operator-only. If you believe you should have
            access, verify `is_operator` on your user row.
          </CardContent>
        </Card>
      </div>
    );
  }

  if (q.isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-dust">
        Loading cohort data…
      </div>
    );
  }

  if (q.error || !q.data) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Admin Dashboard
        </h1>
        <Card>
          <CardContent className="p-6 text-sm text-ember">
            Failed to load dashboard:{" "}
            {q.error instanceof Error ? q.error.message : "unknown error"}
          </CardContent>
        </Card>
      </div>
    );
  }

  const { calculated_at, totals, funnel, users, vt_progress } = q.data;
  const lastCalculated = new Date(calculated_at);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-parchment">
            Admin Dashboard
          </h1>
          <p className="mt-1 text-xs text-dust-deep">
            Last calculated {lastCalculated.toLocaleTimeString()}. Refreshes every 5 min.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => q.refetch()}
          disabled={q.isFetching}
        >
          {q.isFetching ? "Refreshing…" : "Refresh now"}
        </Button>
      </div>

      {/* Totals */}
      <Card>
        <CardHeader>
          <CardTitle>Totals</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Users (all)" value={totals.users_all} />
          <Stat label="Users (non-operator)" value={totals.users_non_operator} />
          <Stat label="Returning (today)" value={totals.returning_today} />
          <Stat label="Returning (7d)" value={totals.returning_7d} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Email Reactivation</CardTitle>
          <p className="text-xs text-dust">
            Opens are best-effort image loads. Clicks are the stronger signal.
          </p>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {emailQ.data?.campaigns[0] ? (
            <>
              <Stat
                label="Opened"
                value={emailQ.data.campaigns[0].opens.distinct_recipients}
                suffix="users"
              />
              <Stat
                label="Open events"
                value={emailQ.data.campaigns[0].opens.events}
              />
              <Stat
                label="Clicked"
                value={emailQ.data.campaigns[0].clicks.distinct_recipients}
                suffix="users"
              />
              <Stat
                label="Click events"
                value={emailQ.data.campaigns[0].clicks.events}
              />
            </>
          ) : (
            <div className="col-span-full text-sm text-dust">
              {emailQ.isLoading
                ? "Loading campaign telemetry..."
                : emailQ.error
                  ? "Email telemetry unavailable."
                  : "No engagement events recorded yet."}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Funnel */}
      <Card>
        <CardHeader>
          <CardTitle>Funnel (non-operator users)</CardTitle>
          <p className="text-xs text-dust">
            Each step counts users who reached that stage. Drop-offs reveal where onboarding fails.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <FunnelBar
            label="Signed up"
            value={funnel.signed_up}
            total={funnel.signed_up}
          />
          <FunnelBar
            label="Onboarded"
            value={funnel.onboarded}
            total={funnel.signed_up}
          />
          <FunnelBar
            label="Meaningful plan"
            value={funnel.meaningful_plan}
            total={funnel.signed_up}
          />
          <FunnelBar
            label="First task created"
            value={funnel.first_task}
            total={funnel.signed_up}
          />
          <FunnelBar
            label="First execution"
            value={funnel.first_execution}
            total={funnel.signed_up}
          />
          <FunnelBar
            label="Returning 7d"
            value={funnel.returning_7d}
            total={funnel.signed_up}
          />
        </CardContent>
      </Card>

      {/* Users */}
      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="border-b border-hairline text-left text-dust-deep">
              <tr>
                <th className="px-2 py-1 font-medium">#</th>
                <th className="px-2 py-1 font-medium">Email</th>
                <th className="px-2 py-1 font-medium">Stage</th>
                <th className="px-2 py-1 font-medium">Signup</th>
                <th className="px-2 py-1 font-medium">Onboarded</th>
                <th className="px-2 py-1 font-medium">Tour</th>
                <th className="px-2 py-1 font-medium">GCal</th>
                <th className="px-2 py-1 font-medium">Tasks</th>
                <th className="px-2 py-1 font-medium">Active</th>
                <th className="px-2 py-1 font-medium">Skipped</th>
                <th className="px-2 py-1 font-medium">Future</th>
                <th className="px-2 py-1 font-medium">Open</th>
                <th className="px-2 py-1 font-medium">Exec</th>
                <th className="px-2 py-1 font-medium">Last Active</th>
                <th className="px-2 py-1 font-medium">Return</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.user_id}
                  className={
                    u.is_operator
                      ? "border-b border-hairline/40 bg-signal/5"
                      : "border-b border-hairline/40"
                  }
                >
                  <td className="px-2 py-1.5 text-dust">{u.user_id}</td>
                  <td className="px-2 py-1.5 text-parchment">
                    {u.email}
                    {u.is_operator && (
                      <span className="ml-1 text-[10px] text-signal">op</span>
                    )}
                  </td>
                  <td className="px-2 py-1.5">
                    <StageChip stage={u.activation_stage} />
                  </td>
                  <td className="px-2 py-1.5 text-dust">
                    {shortDate(u.signed_up_at)}
                  </td>
                  <td className="px-2 py-1.5 text-dust">
                    {u.onboarded_at ? shortDate(u.onboarded_at) : "—"}
                  </td>
                  <td className="px-2 py-1.5">
                    <TourChip status={u.tutorial_status} />
                  </td>
                  <td className="px-2 py-1.5">
                    {u.gcal_connected ? (
                      <span className="text-signal">✓</span>
                    ) : (
                      <span className="text-dust-deep">—</span>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-parchment">
                    {u.task_total}
                  </td>
                  <td className="px-2 py-1.5 text-parchment">
                    {u.active_task_count}
                  </td>
                  <td className="px-2 py-1.5 text-parchment">
                    {u.skipped_count}
                  </td>
                  <td className="px-2 py-1.5">
                    {u.far_future_planned_count > 0 ? (
                      <span className="text-ember">
                        {u.far_future_planned_count}
                      </span>
                    ) : (
                      <span className="text-dust-deep">0</span>
                    )}
                  </td>
                  <td className="px-2 py-1.5">
                    {u.open_timer_count > 0 ? (
                      <span className="text-signal">{u.open_timer_count}</span>
                    ) : (
                      <span className="text-dust-deep">0</span>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-parchment">
                    {u.executed_count}
                  </td>
                  <td className="px-2 py-1.5 text-dust">
                    {u.last_activity_at ? relTime(u.last_activity_at) : "never"}
                  </td>
                  <td className="px-2 py-1.5">
                    <ReturnChip u={u} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* VT Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Research progress (VT coverage indicators)</CardTitle>
          <p className="text-xs text-dust">
            Coverage indicators — not kill-criterion evaluations. These show
            whether enough data exists to run each research question yet.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {Object.entries(vt_progress).map(([key, entry]) => (
            <VtBlock key={key} id={key} entry={entry} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({
  label,
  value,
  suffix,
}: {
  label: string;
  value: number;
  suffix?: string;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-dust-deep">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold text-parchment">
        {value}
        {suffix ? (
          <span className="ml-1 text-xs font-normal text-dust">{suffix}</span>
        ) : null}
      </div>
    </div>
  );
}

function FunnelBar({
  label,
  value,
  total,
}: {
  label: string;
  value: number;
  total: number;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-parchment">{label}</span>
        <span className="text-dust">
          {value} / {total} ({pct}%)
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-void-2">
        <div
          className="h-full rounded-full bg-signal/70 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function TourChip({
  status,
}: {
  status: "completed" | "skipped" | "pending";
}) {
  const cls =
    status === "completed"
      ? "bg-signal/15 text-signal"
      : status === "skipped"
      ? "bg-ember/15 text-ember"
      : "bg-void-2 text-dust-deep";
  return (
    <span
      className={`rounded-sm px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${cls}`}
    >
      {status}
    </span>
  );
}

function StageChip({ stage }: { stage: string }) {
  const severe = new Set([
    "brain_dump_not_completed",
    "onboarding_skipped_or_empty",
    "planned_far_future",
  ]);
  const warning = new Set([
    "all_tasks_skipped",
    "planned_no_timer",
    "timer_started_no_completion",
  ]);
  const cls =
    stage === "activated"
      ? "bg-signal/15 text-signal"
      : severe.has(stage)
      ? "bg-ember/15 text-ember"
      : warning.has(stage)
      ? "bg-amber-500/15 text-amber-300"
      : "bg-void-2 text-dust-deep";
  return (
    <span
      className={`whitespace-nowrap rounded-sm px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${cls}`}
    >
      {stage.replaceAll("_", " ")}
    </span>
  );
}

function ReturnChip({ u }: { u: UserRow }) {
  if (u.returning_today) {
    return (
      <span className="rounded-sm bg-signal/15 px-1.5 py-0.5 text-[10px] font-medium text-signal">
        today
      </span>
    );
  }
  if (u.returning_7d) {
    return (
      <span className="rounded-sm bg-signal/8 px-1.5 py-0.5 text-[10px] font-medium text-dust">
        7d
      </span>
    );
  }
  return <span className="text-dust-deep text-[11px]">—</span>;
}

function VtBlock({
  id,
  entry,
}: {
  id: string;
  entry: VtProgressEntry;
}) {
  const { label, threshold_users, note, ...rest } = entry;
  return (
    <div className="rounded-sm border border-hairline bg-void-2/40 p-3">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-mono text-[11px] text-dust-deep">{id}</span>
        <span className="text-xs text-parchment">{label}</span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-dust">
        {Object.entries(rest).map(([k, v]) => (
          <span key={k}>
            <span className="text-dust-deep">{k}:</span>{" "}
            <span className="text-parchment">{String(v)}</span>
          </span>
        ))}
        {threshold_users !== undefined && (
          <span>
            <span className="text-dust-deep">threshold_users:</span>{" "}
            <span className="text-parchment">{threshold_users}</span>
          </span>
        )}
      </div>
      <p className="mt-2 text-[11px] italic text-dust-deep">{note}</p>
    </div>
  );
}

function shortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function relTime(iso: string): string {
  const d = new Date(iso);
  const now = Date.now();
  const diffMs = now - d.getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
