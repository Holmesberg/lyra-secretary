"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { listDeadlines, type DeadlineResponse } from "@/lib/deadlines";

/**
 * Compact "upcoming deadlines" strip rendered on /today and /calendar.
 *
 * Surfaces the next N bindable deadlines (state ∈ {planned, active},
 * voided_at IS NULL, sorted by due_at_utc ascending). Each chip links
 * to /deadlines for management. Hidden entirely when empty so it
 * doesn't add visual chrome on a fresh account.
 *
 * The data is shared with the deadline-list page via React Query key
 * ["deadlines", "all"]; mutations there invalidate this strip too.
 */
interface Props {
  /** Maximum number of deadlines to surface. Default 4. */
  limit?: number;
  /** Compact variant for embedding next to other chips. */
  variant?: "default" | "compact";
}

function _humanDelta(due: string): { label: string; tone: string } {
  const now = Date.now();
  const t = new Date(due).getTime();
  const diff = t - now;
  const days = Math.round(diff / 86_400_000);
  const hours = Math.round(diff / 3_600_000);
  if (diff < 0) return { label: "overdue", tone: "text-ember" };
  if (hours < 24) return { label: `in ${Math.max(1, hours)}h`, tone: "text-ember" };
  if (days <= 3) return { label: `in ${days}d`, tone: "text-ember" };
  if (days <= 7) return { label: `in ${days}d`, tone: "text-signal" };
  return { label: `in ${days}d`, tone: "text-dust" };
}

export function UpcomingDeadlines({ limit = 4, variant = "default" }: Props) {
  const { data } = useQuery({
    queryKey: ["deadlines", "all"],
    queryFn: () => listDeadlines(),
    staleTime: 60_000,
  });

  const upcoming: DeadlineResponse[] = (data?.deadlines ?? [])
    .filter((d) => d.state === "planned" || d.state === "active")
    .sort(
      (a, b) =>
        new Date(a.due_at_utc).getTime() - new Date(b.due_at_utc).getTime()
    )
    .slice(0, limit);

  if (upcoming.length === 0) return null;

  return (
    <div
      className={
        variant === "compact"
          ? "mb-3 flex flex-wrap items-center gap-2"
          : "mb-4 rounded-sm border border-hairline bg-void-2/40 p-3"
      }
    >
      {variant === "default" && (
        <div className="mb-2 flex items-center justify-between">
          <span className="terminal-prefix font-mono text-[10px] font-medium uppercase tracking-widest text-dust">
            Upcoming deadlines
          </span>
          <Link
            href="/deadlines"
            className="font-mono text-[10px] uppercase tracking-widest text-dust-deep transition-colors hover:text-signal"
          >
            Manage →
          </Link>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {upcoming.map((d) => {
          const { label, tone } = _humanDelta(d.due_at_utc);
          return (
            <Link
              key={d.deadline_id}
              href="/deadlines"
              className="inline-flex items-center gap-2 rounded-sm border border-hairline bg-void-2 px-2.5 py-1 text-xs text-parchment transition-colors hover:border-signal/40"
              title={`Due ${new Date(d.due_at_utc).toLocaleString()}`}
            >
              <span className="truncate max-w-[12rem]">{d.title}</span>
              <span className={`font-mono text-[10px] uppercase tracking-widest ${tone}`}>
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
