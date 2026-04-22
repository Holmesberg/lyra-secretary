"use client";
/**
 * External calendar event row for the /today feed.
 *
 * Option 3 from the 2026-04-21 /today-integration design (see
 * docs/strategic_decisions_april_21.md §6): render Google Calendar
 * events as read-only, time-neutral ambient context alongside Lyra
 * tasks. External badge replaces the usual state badge (no PLANNED/
 * EXECUTED fiction — we don't know what happened).
 *
 * For PAST events without a stored outcome, offer a one-tap
 * "Did you attend?" control (✓ attended / ✗ skipped). The answer
 * lands in external_event_outcome (NOT `task`), preserving the H1
 * research-integrity separation. Once marked, the row locks in the
 * answer with a subtle indicator and a hover-to-revert affordance.
 *
 * Zero interaction for FUTURE events beyond visibility — attendance
 * can't be pre-declared; a forward-dated event is just "here's what
 * Google Calendar has on your schedule."
 */
import { useState } from "react";
import { format } from "date-fns";
import { Check, Ban } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  markEventAttendance,
  type ExternalCalendarEvent,
  type EventOutcome,
} from "@/lib/calendar";

interface Props {
  event: ExternalCalendarEvent;
  /** Current-time anchor used to decide past-vs-future rendering. */
  now: Date;
  /** Invalidates the parent TanStack Query key so the merged feed
   *  re-renders with the locked-in outcome. */
  onMutated?: () => void;
}

export function ExternalEventRow({ event, now, onMutated }: Props) {
  const [outcome, setOutcome] = useState<EventOutcome>(event.outcome ?? null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startDate = new Date(event.start);
  const endDate = new Date(event.end);
  // Valid event data is a prerequisite — if we can't parse, bail to
  // avoid rendering a broken row (defensive; backend normalization
  // should keep this off the happy path).
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
    return null;
  }

  const isPast = endDate.getTime() <= now.getTime();

  async function mark(next: "attended" | "skipped" | "unknown") {
    if (busy) return;
    setBusy(true);
    setError(null);
    // Optimistic flip — the backend is fast but the round-trip still
    // takes a beat; updating locally first lets the feedback feel
    // instant. Revert on error.
    const prev = outcome;
    setOutcome(next === "unknown" ? null : next);
    try {
      await markEventAttendance({
        external_id: event.id.replace(/^gcal-/, ""),
        outcome: next,
        event_title: event.title,
        event_start_utc: event.start,
        event_end_utc: event.end,
      });
      onMutated?.();
    } catch (e: unknown) {
      setOutcome(prev);
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className={cn(
        "group flex items-center gap-4 rounded-sm border border-hairline bg-void-2/40 px-4 py-3 transition-colors",
        // Subtle muted treatment vs Lyra task rows — this is CONTEXT,
        // not a task the user is tracking. Border stays hairline so
        // the layout rhythm matches; the interior tilts toward dust.
        "opacity-80 hover:opacity-100"
      )}
    >
      {/* Time range — same column as Lyra task rows for alignment. */}
      <div className="w-28 font-mono text-xs text-dust">
        {format(startDate, "h:mm a")}–{format(endDate, "h:mm a")}
      </div>

      <div className="min-w-0 flex-1">
        <div className="truncate text-sm text-parchment">{event.title}</div>
        {error && <div className="mt-0.5 text-[11px] text-ember">{error}</div>}
      </div>

      {/* External source badge — time-neutral, no state claim. Color
         picked to be distinct from every Lyra state badge (dust-deep
         on void-2 — readable but quiet). */}
      <span className="rounded-sm border border-hairline bg-void-2 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
        GCAL
      </span>

      {/* Attendance controls — only past events, and only until marked. */}
      <div className="flex items-center gap-1">
        {isPast && outcome === null && (
          <>
            <button
              type="button"
              onClick={() => mark("attended")}
              disabled={busy}
              title="Mark attended"
              className="rounded-sm border border-signal/30 bg-signal/5 px-2 py-1 text-xs text-signal transition-colors hover:bg-signal/10 disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => mark("skipped")}
              disabled={busy}
              title="Mark skipped"
              className="rounded-sm border border-ember/30 bg-ember/5 px-2 py-1 text-xs text-ember transition-colors hover:bg-ember/10 disabled:opacity-50"
            >
              <Ban className="h-3.5 w-3.5" />
            </button>
          </>
        )}
        {isPast && outcome === "attended" && (
          <button
            type="button"
            onClick={() => mark("unknown")}
            disabled={busy}
            title="Attended — tap to change"
            className="flex items-center gap-1 rounded-sm border border-signal/40 bg-signal/10 px-2 py-1 text-[11px] font-mono uppercase tracking-wide text-signal transition-colors hover:bg-signal/15 disabled:opacity-50"
          >
            <Check className="h-3 w-3" />
            attended
          </button>
        )}
        {isPast && outcome === "skipped" && (
          <button
            type="button"
            onClick={() => mark("unknown")}
            disabled={busy}
            title="Skipped — tap to change"
            className="flex items-center gap-1 rounded-sm border border-ember/40 bg-ember/10 px-2 py-1 text-[11px] font-mono uppercase tracking-wide text-ember transition-colors hover:bg-ember/15 disabled:opacity-50"
          >
            <Ban className="h-3 w-3" />
            skipped
          </button>
        )}
        {!isPast && (
          // Placeholder to keep row layout stable across past/future —
          // otherwise future events render with a smaller right cluster
          // and the feed feels jumpy when the day rolls over.
          <div className="w-8" />
        )}
      </div>
    </div>
  );
}
