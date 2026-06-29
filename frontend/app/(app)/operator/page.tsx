"use client";
export const dynamic = "force-dynamic";

import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type ReadinessStatus = "red" | "yellow" | "green";

interface SectionMeta {
  basis?: string;
  confidence?: string;
  readiness_impact?: string;
  safe_to_ignore_when?: string;
}

interface CohortReadiness extends SectionMeta {
  status: ReadinessStatus;
  blockers: string[];
  warnings: string[];
  minimum_fix_set: string[];
  safe_to_invite_more_users: boolean;
  rationale: string;
}

interface Recommendation {
  severity: "critical" | "warning" | "info";
  message: string;
  suggested_action: string;
  related_section: string;
  blocks_cohort_expansion: boolean;
}

interface DynamicIssue extends Recommendation {
  id: string;
  readiness_impact: string;
  tags: string[];
}

interface OperatorUserRow {
  user_id: number;
  first_name: string | null;
  name_source: string | null;
  email_hash: string;
  created_at: string | null;
  last_meaningful_activity_at: string | null;
  active_days_7d: number;
  active_days_14d: number;
  task_count: number;
  executed_task_count: number;
  stopwatch_session_count: number;
  clean_trace_ratio: number | null;
  open_timer_count: number;
  paused_over_72h_count: number;
  last_loop_stage: string;
}

interface OperatorDashboard {
  generated_at: string;
  cohort_readiness: CohortReadiness;
  data_freshness: SectionMeta & {
    source_windows: Record<string, string | null>;
    stale_sources: string[];
  };
  metric_confidence: Record<string, string>;
  meaningful_activity_definition: SectionMeta & {
    included_events: string[];
    excluded_events: string[];
  };
  cohort_segments: SectionMeta & Record<string, number | string | undefined>;
  cohort: SectionMeta & Record<string, number | string | undefined>;
  retention: SectionMeta & Record<string, number | string | null | undefined>;
  activity_frequency: SectionMeta & Record<string, number | string | null | undefined>;
  activation_quality: SectionMeta & Record<string, number | string | null | undefined>;
  product_loop_funnel: SectionMeta & Record<string, number | string | string[] | null | undefined>;
  measurement_integrity: SectionMeta & {
    clean_trace_ratio: number | null;
    dirty_trace_count: number;
    dirty_reasons: Record<string, number>;
    dirty_reason_distribution?: Record<string, number>;
    clean_trace_ratio_basis?: Record<string, unknown>;
    dirty_session_reason_sample?: Record<string, string[]>;
    analytic_blockers: string[];
    calibration_safe: boolean;
    insights_safe: boolean;
  };
  state_invariants: SectionMeta & Record<string, number | string | string[] | null | undefined>;
  notification_lifecycle: SectionMeta & Record<string, unknown>;
  provider_integrity: SectionMeta & Record<string, number | string | undefined>;
  reliability: SectionMeta & Record<string, number | string | string[] | null | undefined>;
  privacy_boundary: SectionMeta & Record<string, boolean | string | undefined>;
  bug_watchlist: SectionMeta & Record<string, string | undefined>;
  users: OperatorUserRow[];
  operator_recommendations: Recommendation[];
  dynamic_issues: DynamicIssue[];
  derived_metrics: Record<string, number | boolean | null>;
}

const FORBIDDEN_KEYS = new Set([
  "basis",
  "confidence",
  "readiness_impact",
  "safe_to_ignore_when",
  "not_instrumented_fields",
  "redis_errors",
]);

function titleize(value: string) {
  return value.replaceAll("_", " ");
}

function collectInstrumentationGaps(data: OperatorDashboard): string[] {
  const sections: Array<[string, Record<string, unknown>]> = [
    ["Product loop", data.product_loop_funnel],
    ["State invariants", data.state_invariants],
    ["Notification lifecycle", data.notification_lifecycle],
    ["Reliability", data.reliability],
    ["Activation quality", data.activation_quality],
  ];
  const gaps: string[] = [];
  for (const [sectionName, section] of sections) {
    const fields = section.not_instrumented_fields;
    if (Array.isArray(fields)) {
      for (const field of fields) {
        gaps.push(`${sectionName}: ${titleize(String(field))}`);
      }
    }
  }
  for (const source of data.data_freshness.stale_sources ?? []) {
    gaps.push(`Freshness: ${titleize(String(source))}`);
  }
  return Array.from(new Set(gaps));
}

function fmt(value: unknown): string {
  if (value === null || value === undefined) return "not instrumented";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") {
    if (value >= 0 && value <= 1 && !Number.isInteger(value)) {
      return `${Math.round(value * 100)}%`;
    }
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => fmt(item)).join(" / ") : "none";
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (!entries.length) return "none";
    return entries.map(([key, item]) => `${titleize(key)} ${fmt(item)}`).join(" / ");
  }
  return String(value);
}

function statusClass(status: ReadinessStatus) {
  if (status === "green") return "border-emerald-400/40 bg-emerald-400/10 text-emerald-200";
  if (status === "yellow") return "border-amber-400/40 bg-amber-400/10 text-amber-200";
  return "border-ember/50 bg-ember/10 text-ember";
}

function SectionGrid({
  title,
  section,
  highlightKeys = [],
}: {
  title: string;
  section: object;
  highlightKeys?: string[];
}) {
  const sectionRecord = section as Record<string, unknown>;
  const entries = Object.entries(sectionRecord).filter(([key]) => !FORBIDDEN_KEYS.has(key));
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between gap-3">
          <span>{title}</span>
          <span className="text-[10px] uppercase tracking-[0.22em] text-dust-deep">
            {sectionRecord.basis ? `${sectionRecord.basis}` : "derived"}
            {sectionRecord.confidence ? ` / ${sectionRecord.confidence}` : ""}
            {sectionRecord.readiness_impact ? ` / ${sectionRecord.readiness_impact}` : ""}
          </span>
        </CardTitle>
        {sectionRecord.safe_to_ignore_when ? (
          <p className="text-xs text-dust">
            Safe to ignore when: {String(sectionRecord.safe_to_ignore_when)}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {entries.map(([key, value]) => (
          <div
            key={key}
            className={`rounded-sm border border-cyan/10 bg-ink/40 p-3 ${
              highlightKeys.includes(key) ? "border-ember/40 bg-ember/5" : ""
            }`}
          >
            <div className="text-[10px] uppercase tracking-[0.18em] text-dust-deep">
              {titleize(key)}
            </div>
            <div className="mt-1 break-words text-sm font-semibold text-parchment">
              {fmt(value)}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function CompactStat({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-sm border border-cyan/10 bg-ink/40 p-3">
      <div className="text-[10px] uppercase tracking-[0.18em] text-dust-deep">
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold text-parchment">{fmt(value)}</div>
    </div>
  );
}

export default function OperatorDashboardPage() {
  const q = useQuery<OperatorDashboard>({
    queryKey: ["operator-dashboard-v12"],
    queryFn: () => api<OperatorDashboard>("/v1/operator/dashboard"),
    staleTime: 60_000,
    refetchInterval: 2 * 60_000,
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
          Operator Dashboard
        </h1>
        <Card>
          <CardContent className="p-6 text-sm text-dust">
            This surface is operator-only.
          </CardContent>
        </Card>
      </div>
    );
  }

  if (q.isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-dust">
        Loading operator readiness...
      </div>
    );
  }

  if (q.error || !q.data) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold tracking-tight text-parchment">
          Operator Dashboard
        </h1>
        <Card>
          <CardContent className="p-6 text-sm text-ember">
            Failed to load operator dashboard:{" "}
            {q.error instanceof Error ? q.error.message : "unknown error"}
          </CardContent>
        </Card>
      </div>
    );
  }

  const data = q.data;
  const readiness = data.cohort_readiness;
  const blockingIssues = data.dynamic_issues.filter((issue) => issue.blocks_cohort_expansion);
  const instrumentationGaps = collectInstrumentationGaps(data);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-[0.28em] text-cyan">
            Operator cockpit
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-parchment">
            Cohort readiness
          </h1>
          <p className="mt-1 text-sm text-dust">
            Can Lyra invite more trusted users today?
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => q.refetch()}
          disabled={q.isFetching}
        >
          {q.isFetching ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      <Card className={statusClass(readiness.status)}>
        <CardContent className="grid gap-4 p-5 md:grid-cols-[1.2fr_2fr]">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] opacity-80">
              Readiness
            </div>
            <div className="mt-2 text-4xl font-bold uppercase">{readiness.status}</div>
            <div className="mt-2 text-sm">{readiness.rationale}</div>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <CompactStat
              label="safe to invite"
              value={readiness.safe_to_invite_more_users}
            />
            <CompactStat label="blockers" value={readiness.blockers.length} />
            <CompactStat label="warnings" value={readiness.warnings.length} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Minimum Fix Set</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {readiness.minimum_fix_set.length ? (
              readiness.minimum_fix_set.map((item) => (
                <div
                  key={item}
                  className="rounded-sm border border-ember/30 bg-ember/5 px-3 py-2 text-sm text-parchment"
                >
                  {titleize(item)}
                </div>
              ))
            ) : (
              <div className="text-sm text-dust">No minimum fixes currently required.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Critical Dynamic Issues</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {blockingIssues.length ? (
              blockingIssues.slice(0, 6).map((issue) => (
                <div
                  key={issue.id}
                  className="rounded-sm border border-ember/30 bg-ember/5 px-3 py-2 text-sm"
                >
                  <div className="font-semibold text-parchment">{issue.message}</div>
                  <div className="mt-1 text-xs text-dust">{issue.suggested_action}</div>
                  {issue.tags.length ? (
                    <div className="mt-2 text-[10px] uppercase tracking-[0.18em] text-cyan">
                      Tags: {issue.tags.join(" / ")}
                    </div>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="text-sm text-dust">No cohort-blocking issues detected.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Instrumentation Gaps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {instrumentationGaps.length ? (
              instrumentationGaps.slice(0, 6).map((gap) => (
                <div
                  key={gap}
                  className="rounded-sm border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-sm text-parchment"
                >
                  {gap}
                </div>
              ))
            ) : (
              <div className="text-sm text-dust">No instrumentation gaps reported.</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Operator Recommendations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.operator_recommendations.length ? (
            data.operator_recommendations.slice(0, 8).map((rec, index) => (
              <div
                key={`${rec.related_section}-${index}`}
                className="rounded-sm border border-cyan/10 bg-ink/40 px-3 py-2 text-sm"
              >
                <div className="font-semibold text-parchment">{rec.message}</div>
                <div className="mt-1 text-xs text-dust">{rec.suggested_action}</div>
              </div>
            ))
          ) : (
            <div className="text-sm text-dust">No recommendations.</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All Dynamic Issues</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          {data.dynamic_issues.length ? (
            data.dynamic_issues.map((issue) => (
              <div
                key={issue.id}
                className={`rounded-sm border px-3 py-2 text-sm ${
                  issue.blocks_cohort_expansion
                    ? "border-ember/40 bg-ember/5"
                    : "border-cyan/10 bg-ink/40"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="font-semibold text-parchment">{issue.message}</div>
                  <div className="shrink-0 text-[10px] uppercase tracking-[0.18em] text-dust-deep">
                    {issue.severity}
                  </div>
                </div>
                <div className="mt-1 text-xs text-dust">{issue.suggested_action}</div>
                {issue.tags.length ? (
                  <div className="mt-2 text-[10px] uppercase tracking-[0.18em] text-cyan">
                    {issue.tags.join(" / ")}
                  </div>
                ) : null}
              </div>
            ))
          ) : (
            <div className="text-sm text-dust">No dynamic issues detected.</div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <CompactStat label="trusted users" value={data.cohort.trusted_users_total} />
        <CompactStat label="weekly active" value={data.cohort.weekly_active_users} />
        <CompactStat
          label="clean traces"
          value={data.measurement_integrity.clean_trace_ratio}
        />
        <CompactStat
          label="timer clean stop"
          value={data.derived_metrics.timer_start_to_clean_stop_rate}
        />
      </div>

      <SectionGrid title="Product Loop Funnel" section={data.product_loop_funnel} />
      <SectionGrid
        title="Measurement Integrity"
        section={{
          ...data.measurement_integrity,
          dirty_reasons: Object.entries(data.measurement_integrity.dirty_reasons)
            .map(([key, value]) => `${titleize(key)} ${value}`)
            .join(" / "),
        }}
        highlightKeys={["dirty_trace_count", "analytic_blockers"]}
      />
      <SectionGrid
        title="State Invariants"
        section={data.state_invariants}
        highlightKeys={[
          "duplicate_open_sessions",
          "executing_tasks_without_open_session",
          "paused_tasks_without_open_session",
          "executed_tasks_missing_start_or_end",
          "open_sessions_for_executed_tasks",
          "stale_reentry_candidates",
        ]}
      />
      <SectionGrid
        title="Notification Lifecycle"
        section={data.notification_lifecycle}
        highlightKeys={[
          "duplicate_prompt_count",
          "exposure_without_render_count",
          "web_lost_unrendered",
        ]}
      />
      <SectionGrid title="Provider Integrity" section={data.provider_integrity} />
      <SectionGrid title="Bug Watchlist" section={data.bug_watchlist} />
      <SectionGrid title="Privacy Boundary" section={data.privacy_boundary} />
      <SectionGrid title="Data Freshness" section={data.data_freshness} />

      <Card>
        <CardHeader>
          <CardTitle>User Rows</CardTitle>
          <p className="text-xs text-dust">
            Content-minimized operational rows. Emails are hashed; task titles are not exposed.
          </p>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-xs">
            <thead className="text-[10px] uppercase tracking-[0.18em] text-dust-deep">
              <tr>
                <th className="py-2 pr-4">User</th>
                <th className="py-2 pr-4">First name</th>
                <th className="py-2 pr-4">Last activity</th>
                <th className="py-2 pr-4">Active days 7d</th>
                <th className="py-2 pr-4">Tasks</th>
                <th className="py-2 pr-4">Sessions</th>
                <th className="py-2 pr-4">Clean trace</th>
                <th className="py-2 pr-4">Open timers</th>
                <th className="py-2 pr-4">Stale paused</th>
                <th className="py-2 pr-4">Loop stage</th>
              </tr>
            </thead>
            <tbody>
              {data.users.map((row) => (
                <tr key={row.user_id} className="border-t border-cyan/10 text-dust">
                  <td className="py-2 pr-4 text-parchment">
                    #{row.user_id} / {row.email_hash}
                  </td>
                  <td className="py-2 pr-4">
                    {row.first_name ? (
                      <span title={row.name_source ?? undefined}>{row.first_name}</span>
                    ) : (
                      "unknown"
                    )}
                  </td>
                  <td className="py-2 pr-4">
                    {row.last_meaningful_activity_at
                      ? new Date(row.last_meaningful_activity_at).toLocaleString()
                      : "none"}
                  </td>
                  <td className="py-2 pr-4">{row.active_days_7d}</td>
                  <td className="py-2 pr-4">{row.task_count}</td>
                  <td className="py-2 pr-4">{row.stopwatch_session_count}</td>
                  <td className="py-2 pr-4">{fmt(row.clean_trace_ratio)}</td>
                  <td className="py-2 pr-4">{row.open_timer_count}</td>
                  <td className="py-2 pr-4">{row.paused_over_72h_count}</td>
                  <td className="py-2 pr-4">{titleize(row.last_loop_stage)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
