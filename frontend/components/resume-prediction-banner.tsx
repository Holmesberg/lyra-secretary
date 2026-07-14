"use client";
/**
 * ResumePredictionBanner — W2 magic-for-alpha (alembic 038, 2026-04-28).
 *
 * Sibling of PausePredictionBanner. Fires when a paused session's
 * paused-for duration approaches the user's historical p75 for the
 * (category, time_of_day) cell, OR when the cold-start 30-min flat cap
 * is hit (no training data yet).
 *
 * Copy is continuity support, not productivity pressure:
 *   "You left {task} paused {duration} ago. Pick it back up?"
 *
 * Two buttons:
 *   - [Resume]   → triggers /v1/stopwatch/resume + dismisses banner
 *   - [Snooze]   → dismisses local-only; predictor's 5-min cooldown
 *                  prevents re-fire so this is effectively "I'll deal
 *                  later"
 *
 * Plus dismiss × in corner.
 *
 * Per docs/manifesto_alignment_audit_2026_04_28.md item #4: VT-17
 * sibling instrument-intervention threats apply. The banner copy keeps
 * the surface in recovery-continuity language.
 */
import { useState } from "react";
import { Play, X, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ResumePredictionNotification } from "@/lib/tasks";

interface Props {
  prediction: ResumePredictionNotification;
  /** Fires when user clicks Resume — parent calls /v1/stopwatch/resume
   * and removes the banner. */
  onResume: () => void;
  /** Local-state dismiss (Snooze + ×). */
  onDismissed: () => void;
}

function formatPausedFor(minutes: number): string {
  const rounded = Math.max(0, Math.round(minutes));
  if (rounded >= 60) {
    const h = Math.floor(rounded / 60);
    const m = rounded % 60;
    return `${h}h ${String(m).padStart(2, "0")}m`;
  }
  return `${rounded} min`;
}

export function ResumePredictionBanner({ prediction, onResume, onDismissed }: Props) {
  const [busy, setBusy] = useState(false);

  const isColdStart = prediction.mechanism === "cold_start_synthetic";

  const pausedFor = Math.max(0, Math.round(prediction.paused_for_minutes));
  const headline = `You left ${prediction.task_title ?? "this task"} paused ${formatPausedFor(pausedFor)} ago. Pick it back up?`;
  const p75 = prediction.p75_pause_minutes
    ? Math.round(prediction.p75_pause_minutes)
    : null;
  const detail = isColdStart
    ? "Quiet check-in while LyraOS learns your resume rhythm."
    : p75 !== null
      ? `Usual resume point for similar pauses is about ${formatPausedFor(p75)}.`
      : "Resume timing came from similar pauses.";

  return (
    <div className="mb-4 rounded-sm border border-signal/30 bg-signal/5 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <Clock className="mt-0.5 h-4 w-4 shrink-0 text-signal" />
          <div className="text-xs text-signal">
            <span className="font-medium text-parchment">{headline}</span>
            <span className="ml-1.5 text-[10px] text-dust-deep">
              {detail}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => { if (!busy) onDismissed(); }}
          disabled={busy}
          aria-label="Dismiss"
          className="shrink-0 text-dust-deep transition-colors hover:text-parchment disabled:opacity-50"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button
          variant="default"
          size="sm"
          onClick={async () => {
            if (busy) return;
            setBusy(true);
            try {
              onResume();
            } finally {
              setBusy(false);
            }
          }}
          disabled={busy}
          className="text-xs"
        >
          <Play className="h-3 w-3 mr-1" />
          Resume
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => { if (!busy) onDismissed(); }}
          disabled={busy}
          className="text-xs text-dust"
        >
          Snooze
        </Button>
      </div>
    </div>
  );
}
