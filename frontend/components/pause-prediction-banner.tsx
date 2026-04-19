"use client";
import { useState } from "react";
import { Clock, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  respondToPausePrediction,
  type PausePredictionNotification,
} from "@/lib/tasks";

interface Props {
  prediction: PausePredictionNotification;
  onPauseNow: () => void;
  onDismissed: () => void;
}

export function PausePredictionBanner({ prediction, onPauseNow, onDismissed }: Props) {
  const [busy, setBusy] = useState(false);

  async function respond(action: "pause_now" | "dismiss" | "snooze") {
    setBusy(true);
    try {
      await respondToPausePrediction(prediction.firing_id, action);
    } catch {
      // Best-effort — log fires even if response endpoint fails.
    }
    if (action === "pause_now") {
      onPauseNow();
    } else {
      onDismissed();
    }
    setBusy(false);
  }

  const mechanism = prediction.mechanism === "clock_anchor"
    ? "clock pattern"
    : "work rhythm";

  return (
    <div className="mb-4 rounded-sm border border-ember/40 bg-ember/5 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <Clock className="mt-0.5 h-4 w-4 shrink-0 text-ember" />
          <div className="text-xs text-ember">
            <span className="font-medium text-parchment">Pause predicted</span>{" "}
            in ~{prediction.lead_minutes} min ({mechanism}).
            You usually break around now.
          </div>
        </div>
        <button
          type="button"
          onClick={() => respond("dismiss")}
          disabled={busy}
          aria-label="Dismiss"
          className="shrink-0 text-dust-deep transition-colors hover:text-parchment"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="mt-2 flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => respond("pause_now")}
          disabled={busy}
          className="text-xs"
        >
          Pause now
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => respond("snooze")}
          disabled={busy}
          className="text-xs text-dust"
        >
          Snooze
        </Button>
      </div>
    </div>
  );
}
