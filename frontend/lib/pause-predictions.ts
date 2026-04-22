/**
 * Pause-prediction client helpers.
 *
 * Covers the Apr 22 retroactive-confirmation chip flow:
 *   - listPendingConfirmations(): firings the operator hasn't confirmed yet
 *   - confirmPrediction(firing_id, outcome): retroactively mark yes/no
 *
 * The in-the-moment banner response (`pause_now`, `dismiss`, `snooze`)
 * lives in lib/tasks.ts alongside the rest of the stopwatch wiring;
 * this file is only the retroactive affordance.
 */
import { api } from "./api";

export type PauseMechanism = "clock_anchor" | "work_rhythm";

export interface PendingConfirmation {
  firing_id: string;
  active_task_id: string | null;
  fired_at: string;
  predicted_at: string;
  mechanism: PauseMechanism;
  confidence: number;
}

export interface PendingConfirmationsResponse {
  pending: PendingConfirmation[];
}

export async function listPendingConfirmations(): Promise<PendingConfirmationsResponse> {
  return api<PendingConfirmationsResponse>(
    "/v1/pause_predictions/pending-confirmation"
  );
}

export interface ConfirmResult {
  firing_id: string;
  user_response: "self_reported_yes" | "self_reported_no";
  response_at: string;
  pause_event_id: string | null;
}

export async function confirmPrediction(
  firingId: string,
  outcome: "yes" | "no"
): Promise<ConfirmResult> {
  return api<ConfirmResult>(
    `/v1/pause_predictions/${firingId}/confirm`,
    {
      method: "POST",
      body: JSON.stringify({ outcome }),
    }
  );
}
