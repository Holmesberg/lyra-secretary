/**
 * Operator-Telegram mirror helper (2026-04-30).
 *
 * Forwards a single signal to the operator's OpenClaw Telegram chat
 * via POST /v1/notifications/operator. Backend is operator-gated
 * (returns 403 to non-operators), so calling this from a non-operator
 * session is a no-op — failures are caught + swallowed; the calling
 * site's toast/UI flow is never blocked.
 *
 * Per operator request 2026-04-30 — "make all notifications, toasts,
 * nudges, ALL go through my telegram openclaw bot."
 *
 * Usage convention:
 *   - Don't replace toast() — call BOTH so the in-browser surface
 *     still works for non-operator users (when alpha opens).
 *   - Use severity="error" for backend-down / session-expired class.
 *   - Use severity="alert" for user-facing event firings the operator
 *     wants to see live (timer overflow, pause prediction, etc.).
 *   - Use severity="info" for routine state changes.
 */
import { api, ApiError } from "@/lib/api";

export type OperatorNotifySeverity = "info" | "warn" | "error" | "alert";

export interface OperatorNotifyOptions {
  message: string;
  severity?: OperatorNotifySeverity;
  /** Short tag identifying the call site (e.g., "toast.task-saved",
   *  "error.session-expired"). Wraps the Telegram message in
   *  brackets — useful for at-a-glance scanning of the chat. */
  source?: string;
}

/**
 * Fire-and-forget mirror to operator Telegram. Always resolves;
 * never throws. Returns true if backend confirmed delivery.
 *
 * For non-operator users the backend returns 403; this helper
 * silently treats that as a no-op (no console noise), so it's safe
 * to call from generic UI code without gating.
 */
export async function notifyOperator(opts: OperatorNotifyOptions): Promise<boolean> {
  try {
    const res = await api<{ sent: boolean }>("/v1/notifications/operator", {
      method: "POST",
      body: JSON.stringify({
        message: opts.message,
        severity: opts.severity ?? "info",
        source: opts.source ?? "frontend",
      }),
    });
    return !!res.sent;
  } catch (e) {
    // 403 (non-operator) and 401 (unauth) are expected — silently
    // skip. Other failures log at debug level so an outage doesn't
    // spam the console.
    if (e instanceof ApiError && (e.status === 403 || e.status === 401)) {
      return false;
    }
    if (typeof console !== "undefined") {
      // eslint-disable-next-line no-console
      console.debug("notifyOperator: telegram mirror failed", e);
    }
    return false;
  }
}
