/**
 * Feedback widget API client (alembic 040, 2026-04-28).
 *
 * Drops a row in the alpha-cohort feedback queue + fans notifications
 * to operator email + Telegram (best-effort, non-blocking on the
 * backend side).
 */
import { api } from "./api";

export type FeedbackKind = "bug" | "suggestion" | "confused" | "other";

export interface FeedbackInput {
  kind: FeedbackKind;
  body: string;
  pageUrl?: string;
  userAgent?: string;
  errorContext?: unknown[];
}

export interface FeedbackResult {
  feedback_id: string;
  submitted_at: string;
}

export function submitFeedback(input: FeedbackInput): Promise<FeedbackResult> {
  return api<FeedbackResult>("/v1/feedback", {
    method: "POST",
    body: JSON.stringify({
      kind: input.kind,
      body: input.body,
      page_url: input.pageUrl,
      user_agent: input.userAgent,
      error_context: input.errorContext,
    }),
  });
}

/** Read the rolling buffer of recent client-side errors (set by lib/api.ts). */
export function readRecentErrors(): unknown[] {
  if (typeof window === "undefined") return [];
  const buf = (window as unknown as { __lyraLastErrors?: unknown[] }).__lyraLastErrors;
  return Array.isArray(buf) ? buf.slice(0, 5) : [];
}
