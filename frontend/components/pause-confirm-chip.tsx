"use client";
/**
 * Retroactive pause-confirmation chip.
 *
 * Renders for a `pause_prediction_log` firing that reconciled as
 * `no_response`, within the CHIP_FRESHNESS_HOURS window, AND without
 * any pause_event landing within ±CHIP_SUPPRESSION_MIN of
 * predicted_at (backend applies all three gates — this component
 * renders whatever the endpoint returns).
 *
 * Two render modes depending on whether the firing is task-attached:
 *   - inline: attached to a task row on /today, matches the
 *     surrounding task-card visual weight
 *   - standalone: no matching task on the feed (active_task_id NULL
 *     or task not in the current viewed day), renders as a small
 *     full-width banner above the feed
 *
 * Three actions:
 *   ✓ Yes → POST /confirm with outcome=yes. Backend creates
 *     pause_event (if a session overlapped predicted_at) + flips
 *     user_response='self_reported_yes'.
 *   ✗ No → POST /confirm with outcome=no. Server flips
 *     user_response='self_reported_no', no pause_event created.
 *   × Dismiss → local-state only; hides chip for session. The
 *     backend still returns it in pending-confirmation until the
 *     freshness window closes or an answer is given.
 *
 * Operator feedback 2026-04-22: "should be one tap" — no modal, no
 * secondary question, no reason-picker. Yes defaults pause_reason
 * to intentional_break at the backend (dominant case for food
 * breaks). Reason editing is a v2 refinement.
 */
import { useState } from "react";
import { Check, X, HelpCircle } from "lucide-react";
import { confirmPrediction, type PendingConfirmation } from "@/lib/pause-predictions";

export interface PauseConfirmChipProps {
  prediction: PendingConfirmation;
  variant: "inline" | "standalone";
  onResolved: (firingId: string) => void;
}

export function PauseConfirmChip({
  prediction,
  variant,
  onResolved,
}: PauseConfirmChipProps) {
  const [busy, setBusy] = useState(false);
  const [acknowledged, setAcknowledged] = useState<"yes" | "no" | null>(null);

  async function handle(outcome: "yes" | "no") {
    if (busy) return;
    setBusy(true);
    setAcknowledged(outcome);
    try {
      await confirmPrediction(prediction.firing_id, outcome);
      // Brief confirmation pulse, then let parent remove us.
      setTimeout(() => onResolved(prediction.firing_id), 1100);
    } catch {
      // Server rejected (likely 409 if already reconciled) — clear
      // the chip anyway so the user isn't stuck on a stale firing.
      setTimeout(() => onResolved(prediction.firing_id), 400);
    } finally {
      setBusy(false);
    }
  }

  function dismiss() {
    onResolved(prediction.firing_id);
  }

  const timeLabel = formatLocalHm(prediction.predicted_at);
  const mechLabel =
    prediction.mechanism === "clock_anchor" ? "clock pattern" : "work rhythm";

  // Acknowledged state — brief "Got it" flash before parent removes us
  if (acknowledged) {
    return (
      <div
        className={
          variant === "inline"
            ? "flex items-center gap-2 rounded-sm border border-signal/30 bg-signal/5 px-2.5 py-1.5 text-[11px] text-signal"
            : "mb-2 flex items-center gap-2 rounded-sm border border-signal/30 bg-signal/5 px-3 py-2 text-xs text-signal"
        }
      >
        <Check className="h-3 w-3" />
        <span>
          {acknowledged === "yes"
            ? `Pause at ~${timeLabel} confirmed. Thanks.`
            : `Noted — no pause at ~${timeLabel}.`}
        </span>
      </div>
    );
  }

  const containerCls =
    variant === "inline"
      ? "flex flex-wrap items-center gap-2 rounded-sm border border-ember/30 bg-ember/5 px-2.5 py-1.5 text-[11px] text-ember"
      : "mb-2 flex flex-wrap items-center gap-2 rounded-sm border border-ember/30 bg-ember/5 px-3 py-2 text-xs text-ember";

  return (
    <div className={containerCls}>
      <HelpCircle className="h-3.5 w-3.5 shrink-0" />
      <span className="flex-1 leading-tight">
        <span className="font-medium text-parchment">
          Pause predicted around {timeLabel}
        </span>
        <span className="text-dust"> — did it happen?</span>
        <span className="ml-1.5 text-[10px] text-dust-deep">
          ({mechLabel}, {Math.round(prediction.confidence * 100)}%)
        </span>
      </span>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => handle("yes")}
          disabled={busy}
          className="inline-flex h-6 items-center gap-1 rounded-sm border border-signal/40 bg-signal/10 px-2 text-[11px] font-medium text-signal transition-colors hover:bg-signal/20 hover:text-signal-neon disabled:opacity-50"
        >
          <Check className="h-3 w-3" /> Yes
        </button>
        <button
          type="button"
          onClick={() => handle("no")}
          disabled={busy}
          className="inline-flex h-6 items-center gap-1 rounded-sm border border-hairline bg-void-2/60 px-2 text-[11px] text-dust transition-colors hover:bg-void-2 hover:text-parchment disabled:opacity-50"
        >
          <X className="h-3 w-3" /> No
        </button>
        <button
          type="button"
          onClick={dismiss}
          disabled={busy}
          aria-label="Dismiss"
          className="text-dust-deep transition-colors hover:text-parchment disabled:opacity-50"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function formatLocalHm(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return iso;
  }
}
